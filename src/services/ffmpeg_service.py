# -*- coding: utf-8 -*-
"""FFmpeg 安装和管理服务模块。

提供FFmpeg的检测、下载、安装功能。
"""

import os
import subprocess
import zipfile
from pathlib import Path
from typing import Callable, Optional, Tuple, Dict

import ffmpeg
import httpx
import re
import shutil
import shlex

from utils.file_utils import get_app_root


class FFmpegService:
    """FFmpeg 安装和管理服务类。
    
    提供FFmpeg的检测、下载、安装功能：
    - 检测系统ffmpeg和本地ffmpeg
    - 自动下载ffmpeg
    - 安装到应用程序目录
    """
    
    # FFmpeg Windows下载链接（使用gyan.dev提供的精简版本）
    FFMPEG_DOWNLOAD_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    
    def __init__(self, config_service=None) -> None:
        """初始化FFmpeg服务。
        
        Args:
            config_service: 配置服务实例（可选）
        """
        self.config_service = config_service
        
        # 获取应用程序根目录
        self.app_root = get_app_root()
        
        # ffmpeg 本地安装目录
        self.ffmpeg_dir = self.app_root / "bin" / "windows" / "ffmpeg"
        self.ffmpeg_bin = self.ffmpeg_dir / "bin"
        self.ffmpeg_exe = self.ffmpeg_bin / "ffmpeg.exe"
        self.ffprobe_exe = self.ffmpeg_bin / "ffprobe.exe"
    
    def _get_temp_dir(self) -> Path:
        """获取临时目录。
        
        Returns:
            临时目录路径
        """
        if self.config_service:
            return self.config_service.get_temp_dir()
        
        # 回退到默认临时目录
        temp_dir = self.app_root / "storage" / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        return temp_dir
    
    def is_ffmpeg_available(self) -> Tuple[bool, str]:
        """检查FFmpeg是否可用。
        
        Returns:
            (是否可用, ffmpeg路径或错误信息)
        """
        # 首先检查本地ffmpeg
        if self.ffmpeg_exe.exists():
            try:
                result = subprocess.run(
                    [str(self.ffmpeg_exe), "-version"],
                    capture_output=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                if result.returncode == 0:
                    return True, str(self.ffmpeg_exe)
            except Exception:
                pass
        
        # 检查系统环境变量中的ffmpeg
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                encoding='utf-8',
                errors='replace',
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            if result.returncode == 0:
                return True, "系统ffmpeg"
        except Exception:
            pass
        
        return False, "未安装"
    
    def get_ffmpeg_path(self) -> Optional[str]:
        """获取可用的ffmpeg路径。
        
        Returns:
            ffmpeg可执行文件路径，如果不可用则返回None
        """
        # 优先使用本地ffmpeg
        if self.ffmpeg_exe.exists():
            return str(self.ffmpeg_exe)
        
        # 使用系统ffmpeg
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                encoding='utf-8',
                errors='replace',
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            if result.returncode == 0:
                return "ffmpeg"  # 系统PATH中的ffmpeg
        except Exception:
            pass
        
        return None
    
    def get_ffprobe_path(self) -> Optional[str]:
        """获取可用的ffprobe路径。
        
        Returns:
            ffprobe可执行文件路径，如果不可用则返回None
        """
        # 优先使用本地ffprobe
        if self.ffprobe_exe.exists():
            return str(self.ffprobe_exe)
        
        # 使用系统ffprobe
        try:
            result = subprocess.run(
                ["ffprobe", "-version"],
                capture_output=True,
                encoding='utf-8',
                errors='replace',
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            if result.returncode == 0:
                return "ffprobe"  # 系统PATH中的ffprobe
        except Exception:
            pass
        
        return None
    
    def download_ffmpeg(
        self,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> Tuple[bool, str]:
        """下载并安装FFmpeg到本地目录。
        
        Args:
            progress_callback: 进度回调函数，接收(进度0-1, 状态消息)
        
        Returns:
            (是否成功, 消息)
        """
        try:
            # 获取临时下载目录
            temp_dir = self._get_temp_dir()
            
            zip_path = temp_dir / "ffmpeg.zip"
            
            # 下载ffmpeg
            if progress_callback:
                progress_callback(0.0, "开始下载FFmpeg...")
            
            with httpx.stream("GET", self.FFMPEG_DOWNLOAD_URL, follow_redirects=True) as response:
                response.raise_for_status()
                
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                
                with open(zip_path, 'wb') as f:
                    for chunk in response.iter_bytes(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            if progress_callback and total_size > 0:
                                progress = downloaded / total_size * 0.7  # 下载占70%进度
                                size_mb = downloaded / (1024 * 1024)
                                total_mb = total_size / (1024 * 1024)
                                progress_callback(
                                    progress,
                                    f"下载中: {size_mb:.1f}/{total_mb:.1f} MB"
                                )
            
            if progress_callback:
                progress_callback(0.7, "下载完成，开始解压...")
            
            # 解压到临时目录
            extract_dir = temp_dir / "ffmpeg_extracted"
            if extract_dir.exists():
                import shutil
                shutil.rmtree(extract_dir)
            extract_dir.mkdir(parents=True, exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            if progress_callback:
                progress_callback(0.85, "解压完成，正在安装...")
            
            # 查找解压后的ffmpeg目录（通常在一个子目录中）
            ffmpeg_folders = list(extract_dir.glob("ffmpeg-*"))
            if not ffmpeg_folders:
                return False, "下载的文件格式不正确"
            
            source_dir = ffmpeg_folders[0]
            
            # 创建目标目录
            self.ffmpeg_dir.mkdir(parents=True, exist_ok=True)
            
            # 复制文件到目标目录
            import shutil
            
            # 复制 bin 目录
            source_bin = source_dir / "bin"
            if source_bin.exists():
                if self.ffmpeg_bin.exists():
                    shutil.rmtree(self.ffmpeg_bin)
                shutil.copytree(source_bin, self.ffmpeg_bin)
            
            # 复制其他目录（可选）
            for item in source_dir.iterdir():
                if item.is_dir() and item.name not in ["bin"]:
                    dest = self.ffmpeg_dir / item.name
                    if dest.exists():
                        shutil.rmtree(dest)
                    shutil.copytree(item, dest)
                elif item.is_file():
                    shutil.copy2(item, self.ffmpeg_dir / item.name)
            
            if progress_callback:
                progress_callback(0.95, "清理临时文件...")
            
            # 清理临时文件
            try:
                zip_path.unlink()
                shutil.rmtree(extract_dir)
            except Exception:
                pass  # 清理失败不影响安装结果
            
            if progress_callback:
                progress_callback(1.0, "安装完成!")
            
            # 验证安装
            if self.ffmpeg_exe.exists() and self.ffprobe_exe.exists():
                return True, f"FFmpeg 已成功安装到: {self.ffmpeg_dir}"
            else:
                return False, "安装失败：文件未正确复制"
        
        except httpx.HTTPError as e:
            return False, f"下载失败: {str(e)}"
        except zipfile.BadZipFile:
            return False, "下载的文件损坏，请重试"
        except Exception as e:
            return False, f"安装失败: {str(e)}"

    def get_video_duration(self, video_path: Path) -> float:
        """获取视频时长（秒）。"""
        ffprobe_path = self.get_ffprobe_path()
        if not ffprobe_path:
            return 0.0
        try:
            probe = ffmpeg.probe(str(video_path), cmd=ffprobe_path)
            return float(probe['format']['duration'])
        except (ffmpeg.Error, KeyError):
            return 0.0

    def compress_video(
        self,
        input_path: Path,
        output_path: Path,
        params: Dict,
        progress_callback: Optional[Callable[[float, str, str], None]] = None
    ) -> Tuple[bool, str]:
        """压缩视频。

        Args:
            input_path: 输入视频路径
            output_path: 输出视频路径
            params: 压缩参数字典
            progress_callback: 进度回调 (progress, speed, remaining_time)

        Returns:
            (是否成功, 消息)
        """
        ffmpeg_path = self.get_ffmpeg_path()
        if not ffmpeg_path:
            return False, "未找到 FFmpeg"

        try:
            duration = self.get_video_duration(input_path)
            
            stream = ffmpeg.input(str(input_path))
            
            # 构建视频滤镜（分辨率缩放和帧率）
            video_filters = []
            scale = params.get("scale", "original")
            if scale == "custom":
                custom_width = params.get("custom_width")
                custom_height = params.get("custom_height")
                if custom_width and custom_height:
                    try:
                        width = int(custom_width)
                        height = int(custom_height)
                        video_filters.append(f'scale={width}:{height}')
                    except ValueError:
                        pass
            elif scale != 'original':
                height_map = {
                    '4k': 2160,
                    '2k': 1440,
                    '1080p': 1080,
                    '720p': 720,
                    '480p': 480,
                    '360p': 360,
                }
                height = height_map.get(scale)
                if height:
                    video_filters.append(f'scale=-2:{height}')
            
            # 帧率控制
            fps_mode = params.get("fps_mode", "original")
            if fps_mode == "custom":
                fps = params.get("fps")
                if fps:
                    try:
                        fps_value = float(fps)
                        video_filters.append(f'fps={fps_value}')
                    except ValueError:
                        pass
            
            # 根据模式构建参数
            if params.get("mode") == "advanced":
                # 高级模式：使用详细参数
                vcodec = params.get("vcodec", "libx264")
                
                # 如果使用默认编码器，尝试使用GPU加速
                if vcodec == "libx264":
                    gpu_encoder = self.get_preferred_gpu_encoder()
                    if gpu_encoder:
                        vcodec = gpu_encoder
                
                output_params = {
                    'vcodec': vcodec,
                    'pix_fmt': params.get("pix_fmt", "yuv420p"),
                }
                
                # 预设（某些编码器可能不支持）
                preset = params.get("preset", "medium")
                if vcodec in ["libx264", "libx265"]:
                    output_params['preset'] = preset
                elif vcodec.startswith("h264_nvenc") or vcodec.startswith("hevc_nvenc"):
                    # NVIDIA编码器使用p1-p7预设（p4是平衡）
                    preset_map = {
                        "ultrafast": "p1", "superfast": "p2", "veryfast": "p3",
                        "faster": "p4", "fast": "p4", "medium": "p4",
                        "slow": "p5", "slower": "p6", "veryslow": "p7"
                    }
                    output_params['preset'] = preset_map.get(preset, "p4")
                elif vcodec.startswith("h264_amf") or vcodec.startswith("hevc_amf") or vcodec.startswith("av1_amf"):
                    # AMF编码器使用quality参数
                    quality_map = {
                        "ultrafast": "speed", "superfast": "speed", "veryfast": "speed",
                        "faster": "balanced", "fast": "balanced", "medium": "balanced",
                        "slow": "quality", "slower": "quality", "veryslow": "quality"
                    }
                    output_params['quality'] = quality_map.get(preset, "balanced")
                elif vcodec.startswith("h264_qsv") or vcodec.startswith("hevc_qsv"):
                    # Intel QSV编码器
                    output_params['preset'] = preset if preset in ["veryfast", "faster", "fast", "medium", "slow"] else "medium"
                
                # 比特率控制
                bitrate_mode = params.get("bitrate_mode", "crf")
                if bitrate_mode == "crf":
                    # CRF模式（质量优先）
                    if vcodec in ["libx264", "libx265"]:
                        output_params['crf'] = params.get("crf", 23)
                    elif vcodec.startswith("libvpx") or vcodec.startswith("libaom"):
                        output_params['crf'] = params.get("crf", 30)
                    elif vcodec.startswith("h264_nvenc") or vcodec.startswith("hevc_nvenc"):
                        # NVIDIA编码器使用cq参数（类似CRF）
                        output_params['cq'] = params.get("crf", 23)
                    elif vcodec.startswith("h264_amf") or vcodec.startswith("hevc_amf") or vcodec.startswith("av1_amf"):
                        # AMD编码器使用rc参数
                        output_params['rc'] = "vbr_peak"
                        output_params['qmin'] = params.get("crf", 18)
                        output_params['qmax'] = params.get("crf", 28)
                    elif vcodec.startswith("h264_qsv") or vcodec.startswith("hevc_qsv"):
                        # Intel QSV编码器
                        output_params['global_quality'] = params.get("crf", 23)
                elif bitrate_mode == "vbr":
                    # VBR模式（可变比特率）
                    video_bitrate = params.get("video_bitrate")
                    max_bitrate = params.get("max_bitrate")
                    if video_bitrate:
                        output_params['b:v'] = f"{video_bitrate}k"
                    if max_bitrate:
                        output_params['maxrate'] = f"{max_bitrate}k"
                        output_params['bufsize'] = f"{int(max_bitrate) * 2}k"
                elif bitrate_mode == "cbr":
                    # CBR模式（恒定比特率）
                    video_bitrate = params.get("video_bitrate")
                    if video_bitrate:
                        output_params['b:v'] = f"{video_bitrate}k"
                        output_params['minrate'] = f"{video_bitrate}k"
                        output_params['maxrate'] = f"{video_bitrate}k"
                        output_params['bufsize'] = f"{int(video_bitrate) * 2}k"
                
                # 关键帧间隔（GOP）
                gop = params.get("gop")
                if gop:
                    try:
                        output_params['g'] = int(gop)
                    except ValueError:
                        pass
                
                # 音频编码
                acodec = params.get("acodec", "copy")
                output_params['acodec'] = acodec
                if acodec != "copy":
                    output_params['b:a'] = params.get("audio_bitrate", "192k")
                
                # 应用视频滤镜
                if video_filters:
                    vf_string = ','.join(video_filters)
                    output_params['vf'] = vf_string
                
                # 根据输出格式设置容器格式
                output_format = params.get("output_format", "same")
                if output_format != "same":
                    # 设置输出格式
                    output_params['format'] = output_format
                
                stream = ffmpeg.output(stream, str(output_path), **output_params)

            else:
                # 常规模式
                crf = params.get("crf", 23)
                
                # 尝试使用GPU加速编码器
                vcodec = 'libx264'
                preset = 'medium'
                gpu_encoder = self.get_preferred_gpu_encoder()
                if gpu_encoder:
                    vcodec = gpu_encoder
                    # GPU编码器可能需要不同的预设
                    if gpu_encoder.startswith("h264_nvenc") or gpu_encoder.startswith("hevc_nvenc"):
                        preset = "p4"  # NVIDIA的平衡预设
                    elif gpu_encoder.startswith("h264_amf") or gpu_encoder.startswith("hevc_amf"):
                        preset = "balanced"  # AMD的平衡预设（实际使用quality参数）
                    elif gpu_encoder.startswith("h264_qsv") or gpu_encoder.startswith("hevc_qsv"):
                        preset = "medium"  # Intel QSV
                
                output_params = {
                    'vcodec': vcodec,
                    'acodec': 'copy'
                }
                
                # 根据编码器类型设置参数
                if vcodec in ["libx264", "libx265"]:
                    output_params['crf'] = crf
                    output_params['preset'] = preset
                elif vcodec.startswith("h264_nvenc") or vcodec.startswith("hevc_nvenc"):
                    output_params['cq'] = crf
                    output_params['preset'] = preset
                elif vcodec.startswith("h264_amf") or vcodec.startswith("hevc_amf"):
                    output_params['rc'] = "vbr_peak"
                    output_params['quality'] = preset
                    output_params['qmin'] = max(18, crf - 5)
                    output_params['qmax'] = min(28, crf + 5)
                elif vcodec.startswith("h264_qsv") or vcodec.startswith("hevc_qsv"):
                    output_params['global_quality'] = crf
                    output_params['preset'] = preset
                
                # 应用视频滤镜
                if video_filters:
                    vf_string = ','.join(video_filters)
                    output_params['vf'] = vf_string
                
                # 根据输出格式设置容器格式
                output_format = params.get("output_format", "same")
                if output_format != "same":
                    output_params['format'] = output_format

                stream = ffmpeg.output(stream, str(output_path), **output_params)

            # 添加全局参数以确保进度输出
            stream = stream.global_args('-stats', '-loglevel', 'info', '-progress', 'pipe:2')
            
            # 使用 ffmpeg-python 的 run_async 运行
            process = ffmpeg.run_async(
                stream,
                cmd=ffmpeg_path,
                pipe_stderr=True,
                pipe_stdout=True,
                overwrite_output=True
            )
            
            if progress_callback and duration > 0:
                # 实时读取 stderr 获取进度
                import threading
                
                def read_stderr():
                    for line in iter(process.stderr.readline, b''):
                        try:
                            line_str = line.decode('utf-8', errors='ignore').strip()
                            
                            # 解析时间进度
                            time_match = re.search(r"time=(\d{2}):(\d{2}):(\d{2})\.\d{2}", line_str)
                            speed_match = re.search(r"speed=\s*([\d.]+)x", line_str)
                            
                            if time_match:
                                hours = int(time_match.group(1))
                                minutes = int(time_match.group(2))
                                seconds = int(time_match.group(3))
                                current_time = hours * 3600 + minutes * 60 + seconds
                                
                                progress = min(current_time / duration, 0.99) if duration > 0 else 0
                                
                                speed_str = f"{speed_match.group(1)}x" if speed_match else "N/A"
                                
                                if speed_match and float(speed_match.group(1)) > 0:
                                    remaining_seconds = (duration - current_time) / float(speed_match.group(1))
                                    remaining_time_str = f"{int(remaining_seconds // 60)}m {int(remaining_seconds % 60)}s"
                                else:
                                    remaining_time_str = "计算中..."
                                
                                progress_callback(progress, speed_str, remaining_time_str)
                        except Exception:
                            pass
                    process.stderr.close()
                
                stderr_thread = threading.Thread(target=read_stderr, daemon=True)
                stderr_thread.start()
                
                # 等待进程结束
                process.wait()
                stderr_thread.join(timeout=1)
            else:
                # 没有回调时直接等待
                process.wait()
            
            # 检查返回码
            if process.returncode != 0:
                stderr_output = ""
                try:
                    if process.stderr:
                        stderr_output = process.stderr.read().decode('utf-8', errors='ignore')
                except Exception:
                    pass
                return False, f"FFmpeg 执行失败，退出码: {process.returncode}\n{stderr_output}"
            
            return True, "压缩成功"

        except ffmpeg.Error as e:
            return False, f"FFmpeg 错误: {e.stderr.decode()}"
        except Exception as e:
            return False, f"压缩失败: {e}"

    def detect_gpu_encoders(self) -> dict:
        """检测可用的GPU编码器。
        
        Returns:
            包含可用GPU编码器信息的字典
        """
        ffmpeg_path = self.get_ffmpeg_path()
        if not ffmpeg_path:
            return {"available": False, "encoders": []}
        
        try:
            # 获取FFmpeg支持的编码器列表
            result = subprocess.run(
                [ffmpeg_path, "-encoders"],
                capture_output=True,
                encoding='utf-8',
                errors='replace',
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            if result.returncode != 0:
                return {"available": False, "encoders": []}
            
            output = result.stdout
            available_encoders = []
            
            # 检测NVIDIA编码器
            if "h264_nvenc" in output:
                available_encoders.append("h264_nvenc")
            if "hevc_nvenc" in output:
                available_encoders.append("hevc_nvenc")
            
            # 检测AMD编码器
            if "h264_amf" in output:
                available_encoders.append("h264_amf")
            if "hevc_amf" in output:
                available_encoders.append("hevc_amf")
            if "av1_amf" in output:
                available_encoders.append("av1_amf")
            
            # 检测Intel编码器（QSV）
            if "h264_qsv" in output:
                available_encoders.append("h264_qsv")
            if "hevc_qsv" in output:
                available_encoders.append("hevc_qsv")
            
            return {
                "available": len(available_encoders) > 0,
                "encoders": available_encoders,
                "preferred": available_encoders[0] if available_encoders else None
            }
        except Exception:
            return {"available": False, "encoders": []}
    
    def get_preferred_gpu_encoder(self) -> Optional[str]:
        """获取首选的GPU编码器。
        
        Returns:
            首选的GPU编码器名称，如果没有则返回None
        """
        # 检查GPU加速开关
        if self.config_service:
            gpu_enabled = self.config_service.get_config_value("gpu_acceleration", True)
            if not gpu_enabled:
                return None
        
        gpu_info = self.detect_gpu_encoders()
        if gpu_info.get("available"):
            preferred = gpu_info.get("preferred")
            if preferred:
                return preferred
            # 如果没有首选，按优先级选择
            encoders = gpu_info.get("encoders", [])
            # 优先选择NVIDIA，然后是AMD，最后是Intel
            for encoder in ["h264_nvenc", "hevc_nvenc", "h264_amf", "hevc_amf", "h264_qsv", "hevc_qsv"]:
                if encoder in encoders:
                    return encoder
        return None
    
    def get_install_info(self) -> dict:
        """获取FFmpeg安装信息。
        
        Returns:
            包含安装状态、路径等信息的字典
        """
        is_available, location = self.is_ffmpeg_available()
        
        info = {
            "available": is_available,
            "location": location,
            "local_exists": self.ffmpeg_exe.exists(),
            "local_path": str(self.ffmpeg_dir) if self.ffmpeg_exe.exists() else None,
        }
        
        # 获取版本信息
        if is_available:
            try:
                ffmpeg_cmd = self.get_ffmpeg_path()
                if ffmpeg_cmd:
                    result = subprocess.run(
                        [ffmpeg_cmd, "-version"],
                        capture_output=True,
                        encoding='utf-8',
                        errors='replace',
                        timeout=5,
                        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                    )
                    if result.returncode == 0:
                        # 提取版本号（第一行）
                        version_line = result.stdout.split('\n')[0]
                        info["version"] = version_line
            except Exception:
                pass
        
        return info

