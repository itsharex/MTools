# -*- coding: utf-8 -*-
"""人脸检测服务模块。

提供基于 RetinaFace 的人脸检测功能，支持 GPU 加速。
参考 HivisionIDPhotos 项目实现。
"""

import gc
from itertools import product
from math import ceil
from pathlib import Path
from typing import Optional, Tuple, List, TYPE_CHECKING

import cv2
import numpy as np

from utils import logger, create_onnx_session

if TYPE_CHECKING:
    from services import ConfigService


class PriorBox:
    """先验框生成器。
    
    用于 RetinaFace 模型的先验框计算。
    """
    
    def __init__(self, cfg: dict, image_size: Tuple[int, int]) -> None:
        """初始化先验框生成器。
        
        Args:
            cfg: 配置字典
            image_size: 图像尺寸 (height, width)
        """
        self.min_sizes = cfg["min_sizes"]
        self.steps = cfg["steps"]
        self.clip = cfg["clip"]
        self.image_size = image_size
        self.feature_maps = [
            [ceil(self.image_size[0] / step), ceil(self.image_size[1] / step)]
            for step in self.steps
        ]
    
    def forward(self) -> np.ndarray:
        """生成先验框。
        
        Returns:
            先验框数组，形状为 (N, 4)
        """
        anchors = []
        for k, f in enumerate(self.feature_maps):
            min_sizes = self.min_sizes[k]
            for i, j in product(range(f[0]), range(f[1])):
                for min_size in min_sizes:
                    s_kx = min_size / self.image_size[1]
                    s_ky = min_size / self.image_size[0]
                    dense_cx = [
                        x * self.steps[k] / self.image_size[1] for x in [j + 0.5]
                    ]
                    dense_cy = [
                        y * self.steps[k] / self.image_size[0] for y in [i + 0.5]
                    ]
                    for cy, cx in product(dense_cy, dense_cx):
                        anchors += [cx, cy, s_kx, s_ky]
        
        output = np.array(anchors).reshape(-1, 4)
        
        if self.clip:
            output = np.clip(output, 0, 1)
        
        return output


def decode(loc: np.ndarray, priors: np.ndarray, variances: List[float]) -> np.ndarray:
    """解码位置预测。
    
    Args:
        loc: 位置预测，形状为 (N, 4)
        priors: 先验框，形状为 (N, 4)
        variances: 方差列表
    
    Returns:
        解码后的边界框，形状为 (N, 4)
    """
    boxes = np.concatenate(
        (
            priors[:, :2] + loc[:, :2] * variances[0] * priors[:, 2:],
            priors[:, 2:] * np.exp(loc[:, 2:] * variances[1]),
        ),
        axis=1,
    )
    
    boxes[:, :2] -= boxes[:, 2:] / 2
    boxes[:, 2:] += boxes[:, :2]
    return boxes


def decode_landm(pre: np.ndarray, priors: np.ndarray, variances: List[float]) -> np.ndarray:
    """解码关键点预测。
    
    Args:
        pre: 关键点预测，形状为 (N, 10)
        priors: 先验框，形状为 (N, 4)
        variances: 方差列表
    
    Returns:
        解码后的关键点，形状为 (N, 10)
    """
    landms = np.concatenate(
        (
            priors[:, :2] + pre[:, :2] * variances[0] * priors[:, 2:],
            priors[:, :2] + pre[:, 2:4] * variances[0] * priors[:, 2:],
            priors[:, :2] + pre[:, 4:6] * variances[0] * priors[:, 2:],
            priors[:, :2] + pre[:, 6:8] * variances[0] * priors[:, 2:],
            priors[:, :2] + pre[:, 8:10] * variances[0] * priors[:, 2:],
        ),
        axis=1,
    )
    return landms


def py_cpu_nms(dets: np.ndarray, thresh: float) -> List[int]:
    """CPU 上的非极大值抑制。
    
    Args:
        dets: 检测结果，形状为 (N, 5)，最后一列为置信度
        thresh: NMS 阈值
    
    Returns:
        保留的索引列表
    """
    x1 = dets[:, 0]
    y1 = dets[:, 1]
    x2 = dets[:, 2]
    y2 = dets[:, 3]
    scores = dets[:, 4]
    
    areas = (x2 - x1 + 1) * (y2 - y1 + 1)
    order = scores.argsort()[::-1]
    
    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(i)
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        
        w = np.maximum(0.0, xx2 - xx1 + 1)
        h = np.maximum(0.0, yy2 - yy1 + 1)
        inter = w * h
        ovr = inter / (areas[i] + areas[order[1:]] - inter)
        
        inds = np.where(ovr <= thresh)[0]
        order = order[inds + 1]
    
    return keep


# RetinaFace 模型配置
RETINAFACE_CONFIG = {
    "name": "Resnet50",
    "min_sizes": [[16, 32], [64, 128], [256, 512]],
    "steps": [8, 16, 32],
    "variance": [0.1, 0.2],
    "clip": False,
    "loc_weight": 2.0,
}


class FaceDetectionResult:
    """人脸检测结果。
    
    Attributes:
        rectangle: 人脸矩形框 (x, y, width, height)
        landmarks: 5个关键点坐标 [(x1,y1), (x2,y2), ...]
        roll_angle: 人脸滚转角度
        confidence: 置信度
    """
    
    def __init__(
        self,
        rectangle: Tuple[float, float, float, float],
        landmarks: List[Tuple[float, float]],
        confidence: float
    ) -> None:
        """初始化人脸检测结果。
        
        Args:
            rectangle: 人脸矩形框 (x, y, width, height)
            landmarks: 5个关键点坐标
            confidence: 置信度
        """
        self.rectangle = rectangle
        self.landmarks = landmarks
        self.confidence = confidence
        
        # 计算滚转角度（基于双眼位置）
        if len(landmarks) >= 2:
            left_eye = np.array(landmarks[0])
            right_eye = np.array(landmarks[1])
            dy = right_eye[1] - left_eye[1]
            dx = right_eye[0] - left_eye[0]
            self.roll_angle = float(np.degrees(np.arctan2(dy, dx)))
        else:
            self.roll_angle = 0.0


class FaceDetector:
    """人脸检测器。
    
    使用 RetinaFace ONNX 模型进行人脸检测，支持 GPU 加速。
    """
    
    def __init__(
        self,
        model_path: Path,
        config_service: Optional['ConfigService'] = None,
        confidence_threshold: float = 0.8,
        nms_threshold: float = 0.2
    ) -> None:
        """初始化人脸检测器。
        
        Args:
            model_path: ONNX 模型路径
            config_service: 配置服务实例
            confidence_threshold: 置信度阈值
            nms_threshold: NMS 阈值
        """
        if not model_path.exists():
            raise FileNotFoundError(f"模型文件不存在: {model_path}")
        
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.nms_threshold = nms_threshold
        self.top_k = 5000
        self.keep_top_k = 750
        
        # 使用统一的工具函数创建会话
        self.sess = create_onnx_session(
            model_path=model_path,
            config_service=config_service
        )
        
        # 记录实际使用的提供者
        actual_provider = self.sess.get_providers()[0]
        self.using_gpu = actual_provider != 'CPUExecutionProvider'
        
        logger.info(f"人脸检测模型已加载: {model_path.name}")
        logger.info(f"使用设备: {actual_provider}")
    
    def get_device_info(self) -> str:
        """获取设备信息。
        
        Returns:
            设备信息字符串
        """
        providers = self.sess.get_providers()
        if "CUDAExecutionProvider" in providers:
            return "GPU (CUDA)"
        elif "DmlExecutionProvider" in providers:
            return "GPU (DirectML)"
        elif "CoreMLExecutionProvider" in providers:
            return "GPU (CoreML)"
        else:
            return "CPU"
    
    def detect(self, image: np.ndarray) -> List[FaceDetectionResult]:
        """检测图像中的人脸。
        
        Args:
            image: 输入图像 (BGR 格式)
        
        Returns:
            人脸检测结果列表
        """
        # 转换为 RGB
        img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        img = np.float32(img_rgb)
        
        im_height, im_width = img.shape[:2]
        scale = np.array([im_width, im_height, im_width, im_height])
        
        # 预处理：减去均值
        img -= (104, 117, 123)
        img = img.transpose(2, 0, 1)
        img = np.expand_dims(img, axis=0)
        
        # 推理
        inputs = {"input": img}
        loc, conf, landms = self.sess.run(None, inputs)
        
        # 生成先验框
        priorbox = PriorBox(RETINAFACE_CONFIG, image_size=(im_height, im_width))
        priors = priorbox.forward()
        prior_data = priors
        
        # 解码
        boxes = decode(np.squeeze(loc, axis=0), prior_data, RETINAFACE_CONFIG["variance"])
        boxes = boxes * scale
        scores = np.squeeze(conf, axis=0)[:, 1]
        
        landms_decoded = decode_landm(
            np.squeeze(landms, axis=0), prior_data, RETINAFACE_CONFIG["variance"]
        )
        
        scale1 = np.array([
            im_width, im_height, im_width, im_height,
            im_width, im_height, im_width, im_height,
            im_width, im_height,
        ])
        landms_decoded = landms_decoded * scale1
        
        # 过滤低置信度
        inds = np.where(scores > self.confidence_threshold)[0]
        boxes = boxes[inds]
        landms_decoded = landms_decoded[inds]
        scores = scores[inds]
        
        # 保留 top-K
        order = scores.argsort()[::-1][:self.top_k]
        boxes = boxes[order]
        landms_decoded = landms_decoded[order]
        scores = scores[order]
        
        # NMS
        dets = np.hstack((boxes, scores[:, np.newaxis])).astype(np.float32, copy=False)
        keep = py_cpu_nms(dets, self.nms_threshold)
        dets = dets[keep, :]
        landms_decoded = landms_decoded[keep]
        
        # 保留 top-K
        dets = dets[:self.keep_top_k, :]
        landms_decoded = landms_decoded[:self.keep_top_k, :]
        
        # 构建结果
        results = []
        for i in range(len(dets)):
            det = dets[i]
            landm = landms_decoded[i]
            
            # 计算矩形框 (x, y, width, height)
            x1, y1, x2, y2, conf = det
            rectangle = (x1, y1, x2 - x1, y2 - y1)
            
            # 提取关键点
            landmarks = [
                (landm[0], landm[1]),  # 左眼
                (landm[2], landm[3]),  # 右眼
                (landm[4], landm[5]),  # 鼻子
                (landm[6], landm[7]),  # 左嘴角
                (landm[8], landm[9]),  # 右嘴角
            ]
            
            results.append(FaceDetectionResult(
                rectangle=rectangle,
                landmarks=landmarks,
                confidence=float(conf)
            ))
        
        return results
    
    def detect_single(self, image: np.ndarray) -> Optional[FaceDetectionResult]:
        """检测图像中的单个人脸。
        
        Args:
            image: 输入图像 (BGR 格式)
        
        Returns:
            最大的人脸检测结果，如果没有检测到则返回 None
        
        Raises:
            ValueError: 如果检测到多个人脸
        """
        results = self.detect(image)
        
        if len(results) == 0:
            return None
        
        if len(results) > 1:
            # 返回最大的人脸（按面积）
            largest = max(results, key=lambda r: r.rectangle[2] * r.rectangle[3])
            return largest
        
        return results[0]
    
    def __del__(self) -> None:
        """析构函数，释放资源。"""
        if hasattr(self, 'sess'):
            del self.sess
            gc.collect()

