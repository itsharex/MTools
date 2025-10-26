"""图片处理服务模块。

提供图片格式转换、压缩、尺寸调整等功能。
"""

import gc
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np
from PIL import Image


class ImageService:
    """图片处理服务类。
    
    提供图片处理相关功能，包括：
    - 格式转换
    - 图片压缩（Pillow、mozjpeg、pngquant）
    - 尺寸调整
    - 批量处理
    """
    
    def __init__(self) -> None:
        """初始化图片处理服务。"""
        self._init_tools_path()
    
    def _init_tools_path(self) -> None:
        """初始化压缩工具路径。"""
        # 获取项目根目录
        if getattr(sys, 'frozen', False):
            # 打包后的可执行文件
            base_path = Path(sys._MEIPASS)
        else:
            # 开发环境
            base_path = Path(__file__).parent.parent.parent
        
        system = platform.system()
        
        if system == "Windows":
            bin_dir = base_path / "bin" / "windows"
            self.mozjpeg_path = bin_dir / "mozjpeg" / "shared" / "Release" / "cjpeg.exe"
            self.pngquant_path = bin_dir / "pngquant" / "pngquant" / "pngquant.exe"
        elif system == "Darwin":
            bin_dir = base_path / "bin" / "macos"
            self.mozjpeg_path = bin_dir / "mozjpeg" / "cjpeg"
            self.pngquant_path = bin_dir / "pngquant" / "pngquant"
        else:  # Linux
            bin_dir = base_path / "bin" / "linux"
            self.mozjpeg_path = bin_dir / "mozjpeg" / "cjpeg"
            self.pngquant_path = bin_dir / "pngquant" / "pngquant"
    
    def _is_tool_available(self, tool_name: str) -> bool:
        """检查压缩工具是否可用。
        
        Args:
            tool_name: 工具名称（'mozjpeg' 或 'pngquant'）
        
        Returns:
            是否可用
        """
        if tool_name == "mozjpeg":
            return self.mozjpeg_path.exists()
        elif tool_name == "pngquant":
            return self.pngquant_path.exists()
        return False
    
    def get_image_info(self, image_path: Path) -> dict:
        """获取图片信息。
        
        Args:
            image_path: 图片路径
        
        Returns:
            包含图片信息的字典，包括：
            - width: 宽度
            - height: 高度
            - format: 格式
            - mode: 颜色模式
            - size: 文件大小（字节）
            如果读取失败，返回包含 'error' 键的字典
        """
        try:
            with Image.open(image_path) as img:
                info = {
                    'width': img.width,
                    'height': img.height,
                    'format': img.format,
                    'mode': img.mode,
                    'size': image_path.stat().st_size,
                }
                return info
        except Exception as e:
            return {'error': str(e)}
    
    def convert_format(
        self,
        input_path: Path,
        output_path: Path,
        quality: int = 85
    ) -> bool:
        """转换图片格式。
        
        Args:
            input_path: 输入图片路径
            output_path: 输出图片路径
            quality: 输出质量（1-100）
        
        Returns:
            是否成功
        """
        try:
            with Image.open(input_path) as img:
                ext = output_path.suffix.lower()
                save_kwargs = {}
                
                # 根据目标格式处理图片模式和参数
                if ext in ['.jpg', '.jpeg']:
                    # JPEG 不支持透明通道
                    if img.mode in ('RGBA', 'LA', 'P'):
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                        img = background
                    save_kwargs = {'quality': quality, 'optimize': True, 'progressive': True}
                
                elif ext == '.png':
                    save_kwargs = {'optimize': True, 'compress_level': 9}
                
                elif ext == '.webp':
                    save_kwargs = {'quality': quality, 'method': 6, 'optimize': True}
                
                elif ext == '.gif':
                    # GIF 需要调色板模式
                    if img.mode != 'P':
                        img = img.convert('P', palette=Image.Palette.ADAPTIVE, colors=256)
                    save_kwargs = {'optimize': True, 'save_all': True}
                
                elif ext in ['.tiff', '.tif']:
                    save_kwargs = {'quality': quality, 'compression': 'tiff_lzw', 'optimize': True}
                
                elif ext == '.bmp':
                    # BMP 通常不支持压缩
                    save_kwargs = {}
                
                elif ext == '.ico':
                    save_kwargs = {}
                
                elif ext in ['.avif', '.heic', '.heif']:
                    save_kwargs = {'quality': quality, 'optimize': True}
                
                else:
                    save_kwargs = {'quality': quality, 'optimize': True}
                
                img.save(output_path, **save_kwargs)
            
            return True
        except Exception as e:
            print(f"格式转换失败: {e}")
            return False
    
    def compress_image(
        self,
        input_path: Path,
        output_path: Path,
        mode: str = 'balanced',
        quality: int = 85
    ) -> Tuple[bool, str]:
        """压缩图片。
        
        Args:
            input_path: 输入图片路径
            output_path: 输出图片路径
            mode: 压缩模式 ('fast', 'balanced', 'max')
            quality: 质量参数（1-100）
        
        Returns:
            (是否成功, 消息)
        """
        ext = input_path.suffix.lower()
        
        try:
            if mode == 'fast':
                # 快速压缩 - 使用 Pillow
                return self._compress_with_pillow(input_path, output_path, quality)
            
            elif mode == 'balanced':
                # 标准压缩 - 使用专业工具
                if ext in ['.jpg', '.jpeg']:
                    if self._is_tool_available('mozjpeg'):
                        return self._compress_with_mozjpeg(input_path, output_path, quality)
                    else:
                        return self._compress_with_pillow(input_path, output_path, quality)
                
                elif ext == '.png':
                    if self._is_tool_available('pngquant'):
                        return self._compress_with_pngquant(input_path, output_path, quality)
                    else:
                        return self._compress_with_pillow(input_path, output_path, quality)
                
                else:
                    return self._compress_with_pillow(input_path, output_path, quality)
            
            elif mode == 'max':
                # 极限压缩 - 两次压缩
                if ext in ['.jpg', '.jpeg'] and self._is_tool_available('mozjpeg'):
                    return self._compress_with_mozjpeg(input_path, output_path, quality - 5)
                elif ext == '.png' and self._is_tool_available('pngquant'):
                    return self._compress_with_pngquant(input_path, output_path, quality - 10)
                else:
                    return self._compress_with_pillow(input_path, output_path, quality - 10)
            
            else:
                return False, f"未知的压缩模式: {mode}"
        
        except Exception as e:
            return False, f"压缩失败: {e}"
    
    def _compress_with_pillow(
        self,
        input_path: Path,
        output_path: Path,
        quality: int
    ) -> Tuple[bool, str]:
        """使用 Pillow 压缩图片。
        
        Args:
            input_path: 输入图片路径
            output_path: 输出图片路径
            quality: 质量参数
        
        Returns:
            (是否成功, 消息)
        """
        try:
            with Image.open(input_path) as img:
                ext = output_path.suffix.lower()
                save_kwargs = {}
                
                # 根据不同格式设置压缩参数
                if ext == '.png':
                    save_kwargs = {
                        'optimize': True,
                        'compress_level': 9
                    }
                elif ext in ['.jpg', '.jpeg']:
                    save_kwargs = {
                        'quality': quality,
                        'optimize': True,
                        'progressive': True
                    }
                    # JPEG 不支持透明通道，需要转换
                    if img.mode in ('RGBA', 'LA', 'P'):
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                        img = background
                elif ext == '.webp':
                    save_kwargs = {
                        'quality': quality,
                        'method': 6,  # 最慢但最好的压缩
                        'optimize': True
                    }
                elif ext == '.gif':
                    # GIF 需要保持调色板模式
                    if img.mode != 'P':
                        img = img.convert('P', palette=Image.Palette.ADAPTIVE, colors=256)
                    save_kwargs = {
                        'optimize': True,
                        'save_all': True,  # 保存所有帧（动图）
                    }
                elif ext in ['.tiff', '.tif']:
                    save_kwargs = {
                        'quality': quality,
                        'compression': 'tiff_lzw',  # 使用 LZW 压缩
                        'optimize': True
                    }
                elif ext == '.ico':
                    # ICO 格式通常用于小图标
                    save_kwargs = {}
                elif ext in ['.avif', '.heic', '.heif']:
                    # 现代格式，高效压缩
                    save_kwargs = {
                        'quality': quality,
                        'optimize': True
                    }
                else:
                    # 默认设置
                    save_kwargs = {
                        'quality': quality,
                        'optimize': True
                    }
                
                img.save(output_path, **save_kwargs)
            
            # 计算压缩率
            original_size = input_path.stat().st_size
            compressed_size = output_path.stat().st_size
            ratio = (1 - compressed_size / original_size) * 100
            
            return True, f"压缩成功 (Pillow): 减小 {ratio:.1f}%"
        
        except Exception as e:
            return False, f"Pillow 压缩失败: {e}"
    
    def _compress_with_mozjpeg(
        self,
        input_path: Path,
        output_path: Path,
        quality: int
    ) -> Tuple[bool, str]:
        """使用 mozjpeg 压缩 JPEG 图片。
        
        Args:
            input_path: 输入图片路径
            output_path: 输出图片路径
            quality: 质量参数
        
        Returns:
            (是否成功, 消息)
        """
        try:
            # 构建命令
            cmd = [
                str(self.mozjpeg_path),
                '-quality', str(quality),
                '-optimize',
                '-progressive',
                '-outfile', str(output_path),
                str(input_path)
            ]
            
            # 执行压缩
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
            )
            
            if result.returncode != 0:
                return False, f"mozjpeg 执行失败: {result.stderr}"
            
            # 计算压缩率
            original_size = input_path.stat().st_size
            compressed_size = output_path.stat().st_size
            ratio = (1 - compressed_size / original_size) * 100
            
            return True, f"压缩成功 (mozjpeg): 减小 {ratio:.1f}%"
        
        except Exception as e:
            return False, f"mozjpeg 压缩失败: {e}"
    
    def _compress_with_pngquant(
        self,
        input_path: Path,
        output_path: Path,
        quality: int
    ) -> Tuple[bool, str]:
        """使用 pngquant 压缩 PNG 图片。
        
        Args:
            input_path: 输入图片路径
            output_path: 输出图片路径
            quality: 质量参数
        
        Returns:
            (是否成功, 消息)
        """
        try:
            # pngquant 的质量范围
            min_quality = max(0, quality - 15)
            max_quality = quality
            
            # 构建命令
            cmd = [
                str(self.pngquant_path),
                '--quality', f'{min_quality}-{max_quality}',
                '--speed', '3',  # 1=最慢最好, 11=最快
                '--force',
                '--output', str(output_path),
                str(input_path)
            ]
            
            # 执行压缩
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
            )
            
            # pngquant 在质量不满足时会返回 99
            if result.returncode not in [0, 99]:
                # 如果失败，尝试用 Pillow 兜底
                return self._compress_with_pillow(input_path, output_path, quality)
            
            # 计算压缩率
            original_size = input_path.stat().st_size
            compressed_size = output_path.stat().st_size
            ratio = (1 - compressed_size / original_size) * 100
            
            return True, f"压缩成功 (pngquant): 减小 {ratio:.1f}%"
        
        except Exception as e:
            return False, f"pngquant 压缩失败: {e}"
    
    def resize_image(
        self,
        input_path: Path,
        output_path: Path,
        width: Optional[int] = None,
        height: Optional[int] = None,
        keep_aspect: bool = True
    ) -> bool:
        """调整图片尺寸。
        
        Args:
            input_path: 输入图片路径
            output_path: 输出图片路径
            width: 目标宽度
            height: 目标高度
            keep_aspect: 是否保持宽高比
        
        Returns:
            是否成功
        """
        try:
            with Image.open(input_path) as img:
                original_width, original_height = img.size
                
                if keep_aspect:
                    # 保持宽高比
                    if width and not height:
                        height = int(original_height * width / original_width)
                    elif height and not width:
                        width = int(original_width * height / original_height)
                    elif width and height:
                        # 按照最小缩放比例
                        ratio = min(width / original_width, height / original_height)
                        width = int(original_width * ratio)
                        height = int(original_height * ratio)
                
                if not width or not height:
                    return False
                
                # 使用高质量重采样
                resized = img.resize((width, height), Image.Resampling.LANCZOS)
                resized.save(output_path, quality=95, optimize=True)
            
            return True
        except Exception as e:
            print(f"尺寸调整失败: {e}")
            return False
    
    def get_image_info(self, image_path: Path) -> dict:
        """获取图片信息。
        
        Args:
            image_path: 图片路径
        
        Returns:
            图片信息字典
        """
        try:
            with Image.open(image_path) as img:
                return {
                    'format': img.format,
                    'mode': img.mode,
                    'size': img.size,
                    'width': img.width,
                    'height': img.height,
                    'file_size': image_path.stat().st_size,
                }
        except Exception as e:
            return {'error': str(e)}


class BackgroundRemover:
    """背景移除器类。
    
    使用ONNX模型进行图像背景移除。
    """
    
    def __init__(self, model_path: Path) -> None:
        """初始化背景移除器。
        
        Args:
            model_path: ONNX模型路径
        """
        try:
            import onnxruntime as ort
        except ImportError:
            raise ImportError("需要安装 onnxruntime 库。请运行: pip install onnxruntime")
        
        if not model_path.exists():
            raise FileNotFoundError(f"模型文件不存在: {model_path}")
        
        # 配置会话选项，启用内存优化
        sess_options = ort.SessionOptions()
        sess_options.enable_mem_pattern = True   # 启用内存模式优化
        sess_options.enable_mem_reuse = True     # 启用内存重用
        sess_options.enable_cpu_mem_arena = True # 启用CPU内存池
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        
        try:
            self.sess = ort.InferenceSession(
                str(model_path),
                sess_options=sess_options,
                providers=['CPUExecutionProvider']  # 只使用CPU
            )
        except Exception as e:
            raise RuntimeError(f"加载ONNX模型失败: {e}")
        
        self.input_name: str = self.sess.get_inputs()[0].name
        self.output_name: str = self.sess.get_outputs()[0].name
        self.model_input_size: Tuple[int, int] = (1024, 1024)
    
    def _preprocess_image(self, im: np.ndarray, model_input_size: Tuple[int, int]) -> np.ndarray:
        """预处理图像，优化内存使用和性能。
        
        Args:
            im: 输入图像数组
            model_input_size: 模型输入尺寸
        
        Returns:
            预处理后的图像张量
        """
        if len(im.shape) < 3:
            im = im[:, :, np.newaxis]
        
        # 直接使用 cv2.resize，避免多次转换
        resized_im = cv2.resize(im, (model_input_size[1], model_input_size[0]))
        
        # 一次性完成类型转换、归一化和维度变换
        im_tensor = resized_im.astype(np.float32).transpose(2, 0, 1) / 255.0
        
        # 归一化
        im_tensor = (im_tensor - 0.5) / 0.5
        
        # 添加批次维度
        return np.expand_dims(im_tensor, axis=0)
    
    def _postprocess_image(self, result: np.ndarray, im_size: Tuple[int, int]) -> np.ndarray:
        """后处理图像，优化性能。
        
        Args:
            result: 模型输出结果
            im_size: 原始图像尺寸
        
        Returns:
            处理后的掩码图像
        """
        # 如果是3维或4维，取第一个通道作为掩码
        if len(result.shape) > 2:
            if len(result.shape) == 4:  # [B, C, H, W]
                result = result[0, 0]  # 取第一个批次的第一个通道
            elif len(result.shape) == 3:  # [C, H, W]
                result = result[0]  # 取第一个通道
        
        # 确保结果在有效范围内并转换类型
        result_image = np.clip(result * 255, 0, 255).astype(np.uint8)
        
        # 调整图像大小 - 掩码应该是2D的
        if result_image.shape != im_size:
            result_image = cv2.resize(result_image, (im_size[1], im_size[0]))
        
        return result_image
    
    def _clear_memory(self) -> None:
        """清理内存。"""
        try:
            # 强制垃圾回收
            gc.collect()
        except Exception:
            pass  # 静默处理清理异常
    
    def remove_background(self, image: Image.Image) -> Image.Image:
        """处理图像并去除背景，返回RGBA格式的PIL图像。
        
        Args:
            image: 输入的PIL图像
        
        Returns:
            去除背景后的RGBA图像
        """
        try:
            if image.mode != "RGB":
                orig_im = image.convert("RGB")
            else:
                orig_im = image
            
            orig_im_size = orig_im.size[::-1]  # PIL size 是 (width, height)，需要反转为 (height, width)
            
            # 将 PIL 图像转换为 numpy 数组
            image_np = np.array(orig_im)
            
            # 预处理图像
            image_tensor = self._preprocess_image(image_np, self.model_input_size)
            
            # 模型推理
            try:
                result = self.sess.run([self.output_name], {self.input_name: image_tensor})[0]
            except Exception as e:
                raise RuntimeError(f"模型推理失败: {e}")
            
            # 后处理图像
            mask = self._postprocess_image(result, orig_im_size)
            
            # 创建RGBA图像
            rgba_image = Image.new("RGBA", orig_im.size)
            rgba_image.paste(orig_im, (0, 0))
            
            # 应用掩码
            mask_pil = Image.fromarray(mask, mode='L')
            rgba_image.putalpha(mask_pil)
            
            return rgba_image
        finally:
            # 确保每次处理后都清理内存
            self._clear_memory()
    
    def remove_background_batch(self, images: list[Image.Image]) -> list[Image.Image]:
        """批量处理多个图像。
        
        Args:
            images: 输入的PIL图像列表
        
        Returns:
            去除背景后的RGBA图像列表
        """
        results = []
        try:
            for img in images:
                # 单独处理每张图片
                if img.mode != "RGB":
                    orig_im = img.convert("RGB")
                else:
                    orig_im = img
                
                orig_im_size = orig_im.size[::-1]
                image_np = np.array(orig_im)
                image_tensor = self._preprocess_image(image_np, self.model_input_size)
                
                try:
                    result = self.sess.run([self.output_name], {self.input_name: image_tensor})[0]
                except Exception as e:
                    raise RuntimeError(f"模型推理失败: {e}")
                
                mask = self._postprocess_image(result, orig_im_size)
                rgba_image = Image.new("RGBA", orig_im.size)
                rgba_image.paste(orig_im, (0, 0))
                mask_pil = Image.fromarray(mask, mode='L')
                rgba_image.putalpha(mask_pil)
                results.append(rgba_image)
                
                # 每处理一张图片后进行一次轻量级清理
                gc.collect()
        finally:
            # 批量处理完成后进行完整的内存清理
            self._clear_memory()
        
        return results

