# -*- coding: utf-8 -*-
"""屏幕录制视图模块。

使用 FFmpeg 实现屏幕录制功能。
"""

import gc
import os
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import flet as ft
import ffmpeg

from constants import (
    BORDER_RADIUS_MEDIUM,
    PADDING_LARGE,
    PADDING_MEDIUM,
    PADDING_SMALL,
)
from services import ConfigService, FFmpegService
from utils.logger import logger
from views.media.ffmpeg_install_view import FFmpegInstallView


class ScreenRecordView(ft.Container):
    """屏幕录制视图类。
    
    使用 FFmpeg 录制屏幕，支持：
    - 全屏录制
    - 指定窗口录制
    - 自定义区域录制
    - 音频设备选择
    - 多种输出格式
    - 帧率设置
    """

    def __init__(
        self,
        page: ft.Page,
        config_service: ConfigService,
        ffmpeg_service: FFmpegService,
        on_back: Optional[Callable] = None
    ) -> None:
        """初始化屏幕录制视图。
        
        Args:
            page: Flet页面对象
            config_service: 配置服务实例
            ffmpeg_service: FFmpeg服务实例
            on_back: 返回按钮回调函数
        """
        super().__init__()
        self.page: ft.Page = page
        self.config_service: ConfigService = config_service
        self.ffmpeg_service: FFmpegService = ffmpeg_service
        self.on_back: Optional[Callable] = on_back
        
        # 录制状态
        self.is_recording: bool = False
        self.is_paused: bool = False
        self.recording_process: Optional[subprocess.Popen] = None
        self.recording_start_time: Optional[float] = None
        self.pause_duration: float = 0.0
        self.pause_start_time: Optional[float] = None
        self.timer_thread: Optional[threading.Thread] = None
        self.should_stop_timer: bool = False
        
        # 输出文件
        self.output_file: Optional[Path] = None
        
        # 设备列表缓存
        self.audio_devices: List[Tuple[str, str]] = []  # (device_id, display_name)
        self.window_list: List[Tuple[str, str]] = []  # (window_id, title)
        
        self.expand: bool = True
        self.padding: ft.padding = ft.padding.only(
            left=PADDING_MEDIUM,
            right=PADDING_MEDIUM,
            top=PADDING_MEDIUM,
            bottom=PADDING_MEDIUM
        )
        
        # 快捷键处理
        self._keyboard_handler = None
        
        # 构建界面
        self._build_ui()
        
        # 注册快捷键
        self._setup_keyboard_shortcuts()
    
    def _get_platform(self) -> str:
        """获取当前平台。"""
        if sys.platform == 'win32':
            return 'windows'
        elif sys.platform == 'darwin':
            return 'macos'
        else:
            return 'linux'
    
    def _setup_keyboard_shortcuts(self) -> None:
        """设置键盘快捷键。"""
        def on_keyboard(e: ft.KeyboardEvent):
            # F9: 开始/停止录制
            if e.key == "F9":
                if self.is_recording:
                    self._stop_recording()
                else:
                    self._on_start_recording(None)
            # F10: 暂停/继续
            elif e.key == "F10":
                if self.is_recording:
                    self._on_pause_recording(None)
        
        self._keyboard_handler = on_keyboard
        self.page.on_keyboard_event = on_keyboard
    
    def _remove_keyboard_shortcuts(self) -> None:
        """移除键盘快捷键。"""
        if self._keyboard_handler and self.page.on_keyboard_event == self._keyboard_handler:
            self.page.on_keyboard_event = None
            self._keyboard_handler = None
    
    def _get_audio_devices(self) -> List[Tuple[str, str]]:
        """获取可用的音频设备列表。
        
        Returns:
            音频设备列表，每项为 (设备ID, 显示名称)
        """
        return self.ffmpeg_service.list_audio_devices()
    
    def _get_audio_devices_categorized(self) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
        """获取分类的音频设备列表。
        
        Returns:
            (麦克风设备列表, 系统音频设备列表)
        """
        all_devices = self._get_audio_devices()
        
        mic_devices = []
        system_devices = []
        
        # 系统音频设备的关键词（立体声混音等）
        system_audio_keywords = [
            '立体声混音', 'stereo mix', 'what u hear', 'wave out',
            'loopback', '混音', 'mix', 'wasapi', 'virtual cable',
            'vb-audio', 'voicemeeter', 'blackhole', 'soundflower',
        ]
        
        for device_id, display_name in all_devices:
            name_lower = display_name.lower()
            
            # 检查是否是系统音频设备
            is_system_audio = any(keyword in name_lower for keyword in system_audio_keywords)
            
            if is_system_audio:
                system_devices.append((device_id, display_name))
            else:
                mic_devices.append((device_id, display_name))
        
        logger.info(f"分类结果: {len(mic_devices)} 个麦克风, {len(system_devices)} 个系统音频设备")
        return mic_devices, system_devices
    
    def _get_window_list(self) -> List[Tuple[str, str]]:
        """获取可用的窗口列表（仅 Windows）。
        
        Returns:
            窗口列表，每项为 (窗口标题, 显示名称)
        """
        windows = []
        platform = self._get_platform()
        
        if platform != 'windows':
            return windows
        
        try:
            import ctypes
            from ctypes import wintypes
            
            user32 = ctypes.windll.user32
            
            # 枚举窗口回调
            EnumWindowsProc = ctypes.WINFUNCTYPE(
                wintypes.BOOL,
                wintypes.HWND,
                wintypes.LPARAM
            )
            
            def enum_windows_callback(hwnd, lParam):
                if user32.IsWindowVisible(hwnd):
                    length = user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buffer = ctypes.create_unicode_buffer(length + 1)
                        user32.GetWindowTextW(hwnd, buffer, length + 1)
                        title = buffer.value
                        if title and len(title) > 1:
                            # 过滤掉一些系统窗口
                            if title not in ['Program Manager', 'Windows Input Experience', 
                                           'Microsoft Text Input Application', 'Settings']:
                                windows.append((title, title[:50] + ('...' if len(title) > 50 else '')))
                return True
            
            user32.EnumWindows(EnumWindowsProc(enum_windows_callback), 0)
            
        except Exception as ex:
            logger.warning(f"获取窗口列表失败: {ex}")
        
        return windows
    
    def _build_ui(self) -> None:
        """构建用户界面。"""
        # 检查 FFmpeg 是否可用
        is_ffmpeg_available, _ = self.ffmpeg_service.is_ffmpeg_available()
        if not is_ffmpeg_available:
            self.padding = ft.padding.all(0)
            self.content = FFmpegInstallView(
                self.page,
                self.ffmpeg_service,
                on_back=self._on_back_click,
                tool_name="屏幕录制"
            )
            return

        # 顶部：标题和返回按钮
        header = ft.Row(
            controls=[
                ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    tooltip="返回",
                    on_click=self._on_back_click,
                ),
                ft.Text("屏幕录制", size=28, weight=ft.FontWeight.BOLD),
            ],
            spacing=PADDING_MEDIUM,
        )
        
        # 录制计时显示
        self.timer_text = ft.Text(
            "00:00:00",
            size=48,
            weight=ft.FontWeight.BOLD,
            text_align=ft.TextAlign.CENTER,
        )
        
        self.status_text = ft.Text(
            "准备就绪",
            size=14,
            color=ft.Colors.ON_SURFACE_VARIANT,
            text_align=ft.TextAlign.CENTER,
        )
        
        self.recording_indicator = ft.Container(
            content=ft.Icon(ft.Icons.FIBER_MANUAL_RECORD, color=ft.Colors.GREY, size=16),
            visible=True,
        )
        
        timer_area = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            self.recording_indicator,
                            self.timer_text,
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=PADDING_SMALL,
                    ),
                    self.status_text,
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=PADDING_SMALL,
            ),
            padding=PADDING_LARGE,
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=BORDER_RADIUS_MEDIUM,
            bgcolor=ft.Colors.with_opacity(0.02, ft.Colors.PRIMARY),
        )
        
        # ===== 录制源设置 =====
        platform = self._get_platform()
        
        # 录制目标选择
        area_options = [
            ft.dropdown.Option("fullscreen", "全屏"),
            ft.dropdown.Option("custom", "自定义区域"),
        ]
        
        # Windows 支持录制特定窗口
        if platform == 'windows':
            area_options.insert(1, ft.dropdown.Option("window", "指定窗口"))
        
        self.area_dropdown = ft.Dropdown(
            label="录制目标",
            value="fullscreen",
            options=area_options,
            width=200,
            on_change=self._on_area_change,
        )
        
        # 窗口选择（Windows 专用，初始隐藏）
        self.window_dropdown = ft.Dropdown(
            label="选择窗口",
            width=300,
            visible=False,
        )
        
        self.refresh_windows_btn = ft.IconButton(
            icon=ft.Icons.REFRESH,
            tooltip="刷新窗口列表",
            on_click=self._on_refresh_windows,
            visible=False,
        )
        
        self.window_row = ft.Row(
            controls=[
                self.window_dropdown,
                self.refresh_windows_btn,
            ],
            spacing=PADDING_SMALL,
            visible=False,
        )
        
        # 自定义区域设置（初始隐藏）
        self.offset_x = ft.TextField(
            label="X 偏移",
            value="0",
            width=90,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        self.offset_y = ft.TextField(
            label="Y 偏移",
            value="0",
            width=90,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        self.width_field = ft.TextField(
            label="宽度",
            value="1920",
            width=90,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        self.height_field = ft.TextField(
            label="高度",
            value="1080",
            width=90,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        
        self.custom_area_row = ft.Row(
            controls=[
                self.offset_x,
                self.offset_y,
                self.width_field,
                self.height_field,
            ],
            spacing=PADDING_SMALL,
            visible=False,
        )
        
        source_area = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("录制源", size=18, weight=ft.FontWeight.W_600),
                    ft.Row(
                        controls=[self.area_dropdown],
                        spacing=PADDING_MEDIUM,
                    ),
                    self.window_row,
                    self.custom_area_row,
                ],
                spacing=PADDING_MEDIUM,
            ),
            padding=PADDING_LARGE,
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=BORDER_RADIUS_MEDIUM,
            bgcolor=ft.Colors.with_opacity(0.01, ft.Colors.PRIMARY),
        )
        
        # ===== 音频设置 =====
        # 麦克风录制
        self.record_mic = ft.Checkbox(
            label="录制麦克风",
            value=False,
            on_change=self._on_mic_checkbox_change,
        )
        
        self.mic_device_dropdown = ft.Dropdown(
            label="麦克风设备",
            width=280,
            visible=False,
        )
        
        self.refresh_mic_btn = ft.IconButton(
            icon=ft.Icons.REFRESH,
            tooltip="刷新麦克风列表",
            on_click=self._on_refresh_audio_devices,
            visible=False,
        )
        
        self.mic_device_row = ft.Row(
            controls=[
                self.mic_device_dropdown,
                self.refresh_mic_btn,
            ],
            spacing=PADDING_SMALL,
            visible=False,
        )
        
        # 系统音频录制（立体声混音）
        self.record_system_audio = ft.Checkbox(
            label="录制系统音频",
            value=False,
            on_change=self._on_system_audio_checkbox_change,
        )
        
        self.system_audio_dropdown = ft.Dropdown(
            label="系统音频设备",
            width=280,
            visible=False,
        )
        
        self.refresh_system_audio_btn = ft.IconButton(
            icon=ft.Icons.REFRESH,
            tooltip="刷新系统音频列表",
            on_click=self._on_refresh_audio_devices,
            visible=False,
        )
        
        self.system_audio_row = ft.Row(
            controls=[
                self.system_audio_dropdown,
                self.refresh_system_audio_btn,
            ],
            spacing=PADDING_SMALL,
            visible=False,
        )
        
        # 系统音频提示
        self.system_audio_tip = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.INFO_OUTLINE, size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                    ft.Text(
                        "Windows: 需启用「立体声混音」。右键音量图标 → 声音设置 → 更多声音设置 → 录制 → 右键启用「立体声混音」",
                        size=11,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                ],
                spacing=6,
            ),
            visible=False,
        )
        
        # 兼容旧代码的属性别名
        self.record_audio = self.record_mic
        self.audio_device_dropdown = self.mic_device_dropdown
        
        audio_area = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("音频设置", size=18, weight=ft.FontWeight.W_600),
                    self.record_mic,
                    self.mic_device_row,
                    ft.Divider(height=1, color=ft.Colors.OUTLINE_VARIANT),
                    self.record_system_audio,
                    self.system_audio_row,
                    self.system_audio_tip,
                ],
                spacing=PADDING_MEDIUM,
            ),
            padding=PADDING_LARGE,
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=BORDER_RADIUS_MEDIUM,
            bgcolor=ft.Colors.with_opacity(0.01, ft.Colors.PRIMARY),
        )
        
        # ===== 视频设置 =====
        # 帧率选择 - 支持更高帧率
        self.fps_dropdown = ft.Dropdown(
            label="帧率 (FPS)",
            value="30",
            options=[
                ft.dropdown.Option("15", "15 FPS - 低"),
                ft.dropdown.Option("24", "24 FPS - 电影"),
                ft.dropdown.Option("30", "30 FPS - 标准"),
                ft.dropdown.Option("60", "60 FPS - 流畅"),
                ft.dropdown.Option("90", "90 FPS - 高刷"),
                ft.dropdown.Option("120", "120 FPS - 极高"),
                ft.dropdown.Option("144", "144 FPS - 电竞"),
                ft.dropdown.Option("240", "240 FPS - 专业"),
            ],
            width=180,
        )
        
        # 输出格式
        self.format_dropdown = ft.Dropdown(
            label="输出格式",
            value="mp4",
            options=[
                ft.dropdown.Option("mp4", "MP4 (推荐)"),
                ft.dropdown.Option("mkv", "MKV"),
                ft.dropdown.Option("avi", "AVI"),
                ft.dropdown.Option("mov", "MOV"),
                ft.dropdown.Option("webm", "WebM"),
            ],
            width=180,
        )
        
        # 视频编码器 - 检测 GPU 编码器
        encoder_options = [
            ft.dropdown.Option("libx264", "H.264 (CPU)"),
            ft.dropdown.Option("libx265", "H.265 (CPU)"),
            ft.dropdown.Option("libvpx-vp9", "VP9 (CPU)"),
        ]
        
        # 检测 GPU 编码器
        gpu_info = self.ffmpeg_service.detect_gpu_encoders()
        self.gpu_encoders_available = gpu_info.get("available", False)
        gpu_encoders = gpu_info.get("encoders", [])
        
        if self.gpu_encoders_available:
            if "h264_nvenc" in gpu_encoders:
                encoder_options.insert(0, ft.dropdown.Option("h264_nvenc", "H.264 (NVENC) - NVIDIA ⚡"))
            if "hevc_nvenc" in gpu_encoders:
                encoder_options.insert(1, ft.dropdown.Option("hevc_nvenc", "H.265 (NVENC) - NVIDIA ⚡"))
            if "h264_amf" in gpu_encoders:
                encoder_options.insert(0, ft.dropdown.Option("h264_amf", "H.264 (AMF) - AMD ⚡"))
            if "hevc_amf" in gpu_encoders:
                encoder_options.insert(1, ft.dropdown.Option("hevc_amf", "H.265 (AMF) - AMD ⚡"))
            if "h264_qsv" in gpu_encoders:
                encoder_options.insert(0, ft.dropdown.Option("h264_qsv", "H.264 (QSV) - Intel ⚡"))
            if "hevc_qsv" in gpu_encoders:
                encoder_options.insert(1, ft.dropdown.Option("hevc_qsv", "H.265 (QSV) - Intel ⚡"))
        
        # 默认选择 GPU 编码器（如果可用）
        default_encoder = "libx264"
        if "h264_nvenc" in gpu_encoders:
            default_encoder = "h264_nvenc"
        elif "h264_amf" in gpu_encoders:
            default_encoder = "h264_amf"
        elif "h264_qsv" in gpu_encoders:
            default_encoder = "h264_qsv"
        
        self.encoder_dropdown = ft.Dropdown(
            label="视频编码器",
            value=default_encoder,
            options=encoder_options,
            width=250,
            on_change=self._on_encoder_change,
        )
        
        # 编码预设 - 根据默认编码器初始化
        if default_encoder.endswith("_nvenc"):
            preset_options = [
                ft.dropdown.Option("p1", "P1 - 最快"),
                ft.dropdown.Option("p2", "P2 - 很快"),
                ft.dropdown.Option("p3", "P3 - 快"),
                ft.dropdown.Option("p4", "P4 - 中等 (推荐)"),
                ft.dropdown.Option("p5", "P5 - 慢"),
                ft.dropdown.Option("p6", "P6 - 较慢"),
                ft.dropdown.Option("p7", "P7 - 最慢 (质量最好)"),
            ]
            default_preset = "p4"
        elif default_encoder.endswith("_amf"):
            preset_options = [
                ft.dropdown.Option("speed", "速度优先"),
                ft.dropdown.Option("balanced", "平衡 (推荐)"),
                ft.dropdown.Option("quality", "质量优先"),
            ]
            default_preset = "balanced"
        elif default_encoder.endswith("_qsv"):
            preset_options = [
                ft.dropdown.Option("veryfast", "很快"),
                ft.dropdown.Option("faster", "较快"),
                ft.dropdown.Option("fast", "快"),
                ft.dropdown.Option("medium", "中等 (推荐)"),
                ft.dropdown.Option("slow", "慢"),
            ]
            default_preset = "medium"
        else:
            preset_options = [
                ft.dropdown.Option("ultrafast", "最快 (质量最低)"),
                ft.dropdown.Option("superfast", "超快"),
                ft.dropdown.Option("veryfast", "很快"),
                ft.dropdown.Option("faster", "较快"),
                ft.dropdown.Option("fast", "快 (推荐)"),
                ft.dropdown.Option("medium", "中等"),
                ft.dropdown.Option("slow", "慢 (质量更好)"),
            ]
            default_preset = "fast"
        
        self.preset_dropdown = ft.Dropdown(
            label="编码预设",
            value=default_preset,
            options=preset_options,
            width=200,
        )
        
        # 质量设置 (CRF/CQ)
        self.quality_slider = ft.Slider(
            min=15,
            max=35,
            value=23,
            divisions=20,
            label="{value}",
            on_change=self._on_quality_change,
            expand=True,
        )
        self.quality_text = ft.Text("质量: 23 (数值越小，质量越好，文件越大)", size=12)
        
        # GPU 状态提示
        gpu_status = ""
        if self.gpu_encoders_available:
            gpu_list = []
            if any("nvenc" in e for e in gpu_encoders):
                gpu_list.append("NVIDIA")
            if any("amf" in e for e in gpu_encoders):
                gpu_list.append("AMD")
            if any("qsv" in e for e in gpu_encoders):
                gpu_list.append("Intel")
            gpu_status = f"✅ 已检测到 GPU 加速: {', '.join(gpu_list)}"
        else:
            gpu_status = "⚠️ 未检测到 GPU 加速，将使用 CPU 编码"
        
        self.gpu_status_text = ft.Text(gpu_status, size=12, color=ft.Colors.ON_SURFACE_VARIANT)
        
        video_area = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("视频设置", size=18, weight=ft.FontWeight.W_600),
                    self.gpu_status_text,
                    ft.Row(
                        controls=[
                            self.fps_dropdown,
                            self.format_dropdown,
                        ],
                        spacing=PADDING_MEDIUM,
                        wrap=True,
                    ),
                    ft.Row(
                        controls=[
                            self.encoder_dropdown,
                            self.preset_dropdown,
                        ],
                        spacing=PADDING_MEDIUM,
                        wrap=True,
                    ),
                    ft.Column(
                        controls=[
                            self.quality_text,
                            self.quality_slider,
                        ],
                        spacing=0,
                    ),
                ],
                spacing=PADDING_MEDIUM,
            ),
            padding=PADDING_LARGE,
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=BORDER_RADIUS_MEDIUM,
            bgcolor=ft.Colors.with_opacity(0.01, ft.Colors.PRIMARY),
        )
        
        # ===== 输出设置 =====
        # 默认保存到 用户目录/Videos/MTools/录屏
        default_output = Path.home() / "Videos" / "MTools" / "录屏"
        try:
            default_output.mkdir(parents=True, exist_ok=True)
        except Exception:
            # 如果无法创建，使用用户视频目录
            default_output = Path.home() / "Videos"
            if not default_output.exists():
                default_output = Path.home()
        
        self.output_path_field = ft.TextField(
            label="保存位置",
            value=str(default_output),
            expand=True,
            read_only=True,
        )
        
        self.folder_picker = ft.FilePicker(
            on_result=self._on_folder_selected
        )
        self.page.overlay.append(self.folder_picker)
        
        output_area = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("输出设置", size=18, weight=ft.FontWeight.W_600),
                    ft.Row(
                        controls=[
                            self.output_path_field,
                            ft.IconButton(
                                icon=ft.Icons.FOLDER_OPEN,
                                tooltip="选择文件夹",
                                on_click=self._on_select_folder,
                            ),
                        ],
                        spacing=PADDING_SMALL,
                    ),
                ],
                spacing=PADDING_MEDIUM,
            ),
            padding=PADDING_LARGE,
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=BORDER_RADIUS_MEDIUM,
            bgcolor=ft.Colors.with_opacity(0.01, ft.Colors.PRIMARY),
        )
        
        # 控制按钮
        self.start_btn = ft.ElevatedButton(
            "开始录制",
            icon=ft.Icons.FIBER_MANUAL_RECORD,
            on_click=self._on_start_recording,
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.RED,
                color=ft.Colors.WHITE,
            ),
            height=48,
            width=160,
        )
        
        self.pause_btn = ft.ElevatedButton(
            "暂停",
            icon=ft.Icons.PAUSE,
            on_click=self._on_pause_recording,
            disabled=True,
            height=48,
            width=120,
        )
        
        self.stop_btn = ft.ElevatedButton(
            "停止",
            icon=ft.Icons.STOP,
            on_click=self._on_stop_recording,
            disabled=True,
            height=48,
            width=120,
        )
        
        self.open_folder_btn = ft.OutlinedButton(
            "打开文件夹",
            icon=ft.Icons.FOLDER_OPEN,
            on_click=self._on_open_folder,
            height=48,
            visible=False,
        )
        
        control_area = ft.Container(
            content=ft.Row(
                controls=[
                    self.start_btn,
                    self.pause_btn,
                    self.stop_btn,
                    self.open_folder_btn,
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=PADDING_MEDIUM,
            ),
            padding=PADDING_LARGE,
        )
        
        # 平台提示
        platform_info = {
            'windows': '当前系统: Windows - 使用 GDI 屏幕捕获，支持录制指定窗口',
            'macos': '当前系统: macOS - 使用 AVFoundation 屏幕捕获',
            'linux': '当前系统: Linux - 使用 X11 屏幕捕获',
        }
        
        platform_note = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.INFO_OUTLINE, size=16, color=ft.Colors.PRIMARY),
                    ft.Text(
                        platform_info.get(platform, '未知系统'),
                        size=12,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                ],
                spacing=6,
            ),
            padding=ft.padding.symmetric(horizontal=PADDING_MEDIUM),
        )
        
        # 快捷键提示
        shortcut_note = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.KEYBOARD, size=16, color=ft.Colors.PRIMARY),
                    ft.Text(
                        "快捷键: F9 开始/停止录制 | F10 暂停/继续",
                        size=12,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                ],
                spacing=6,
            ),
            padding=ft.padding.symmetric(horizontal=PADDING_MEDIUM),
        )
        
        # 组装界面
        self.content = ft.Column(
            controls=[
                header,
                timer_area,
                source_area,
                audio_area,
                video_area,
                output_area,
                control_area,
                platform_note,
                shortcut_note,
            ],
            scroll=ft.ScrollMode.AUTO,
            spacing=PADDING_MEDIUM,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )
    
    def _on_back_click(self, e=None) -> None:
        """处理返回按钮点击。"""
        # 如果正在录制，先停止
        if self.is_recording:
            self._stop_recording()
        
        # 移除快捷键
        self._remove_keyboard_shortcuts()
        
        if self.on_back:
            self.on_back()
    
    def _on_area_change(self, e) -> None:
        """处理录制目标选择变化。"""
        value = e.control.value
        
        # 窗口选择（仅 Windows）
        self.window_row.visible = (value == "window")
        self.window_dropdown.visible = (value == "window")
        self.refresh_windows_btn.visible = (value == "window")
        
        # 如果选择窗口，加载窗口列表
        if value == "window" and not self.window_dropdown.options:
            self._load_window_list()
        
        # 自定义区域
        self.custom_area_row.visible = (value == "custom")
        
        self.page.update()
    
    def _on_mic_checkbox_change(self, e) -> None:
        """处理麦克风复选框变化。"""
        self.mic_device_row.visible = e.control.value
        self.mic_device_dropdown.visible = e.control.value
        self.refresh_mic_btn.visible = e.control.value
        
        # 如果勾选录制麦克风，加载设备列表
        if e.control.value and not self.mic_device_dropdown.options:
            self._load_audio_devices()
        
        self.page.update()
    
    def _on_system_audio_checkbox_change(self, e) -> None:
        """处理系统音频复选框变化。"""
        self.system_audio_row.visible = e.control.value
        self.system_audio_dropdown.visible = e.control.value
        self.refresh_system_audio_btn.visible = e.control.value
        self.system_audio_tip.visible = e.control.value
        
        # 如果勾选录制系统音频，加载设备列表
        if e.control.value and not self.system_audio_dropdown.options:
            self._load_audio_devices()
        
        self.page.update()
    
    def _on_audio_checkbox_change(self, e) -> None:
        """兼容旧代码的回调。"""
        self._on_mic_checkbox_change(e)
    
    def _load_audio_devices(self) -> None:
        """加载音频设备列表。"""
        mic_devices, system_devices = self._get_audio_devices_categorized()
        
        # 麦克风设备
        mic_options = []
        for device_id, display_name in mic_devices:
            mic_options.append(ft.dropdown.Option(device_id, display_name))
        
        if mic_options:
            self.mic_device_dropdown.options = mic_options
            self.mic_device_dropdown.value = mic_options[0].key
        else:
            self.mic_device_dropdown.options = [
                ft.dropdown.Option("none", "未找到麦克风设备")
            ]
            self.mic_device_dropdown.value = "none"
        
        # 系统音频设备
        system_options = []
        for device_id, display_name in system_devices:
            system_options.append(ft.dropdown.Option(device_id, display_name))
        
        if system_options:
            self.system_audio_dropdown.options = system_options
            self.system_audio_dropdown.value = system_options[0].key
        else:
            self.system_audio_dropdown.options = [
                ft.dropdown.Option("none", "未找到系统音频设备 (需启用立体声混音)")
            ]
            self.system_audio_dropdown.value = "none"
        
        self.page.update()
    
    def _load_window_list(self) -> None:
        """加载窗口列表。"""
        self.window_list = self._get_window_list()
        
        options = []
        for window_id, display_name in self.window_list:
            options.append(ft.dropdown.Option(window_id, display_name))
        
        if options:
            self.window_dropdown.options = options
            self.window_dropdown.value = options[0].key
        else:
            self.window_dropdown.options = [
                ft.dropdown.Option("none", "未找到可用窗口")
            ]
            self.window_dropdown.value = "none"
        
        self.page.update()
    
    def _on_refresh_audio_devices(self, e) -> None:
        """刷新音频设备列表。"""
        self._load_audio_devices()
        self._show_message("音频设备列表已刷新", ft.Colors.GREEN)
    
    def _on_refresh_windows(self, e) -> None:
        """刷新窗口列表。"""
        self._load_window_list()
        self._show_message("窗口列表已刷新", ft.Colors.GREEN)
    
    def _on_encoder_change(self, e) -> None:
        """处理编码器选择变化。"""
        encoder = e.control.value
        
        # 根据编码器类型更新预设选项
        if encoder.endswith("_nvenc"):
            # NVIDIA 编码器预设
            self.preset_dropdown.options = [
                ft.dropdown.Option("p1", "P1 - 最快"),
                ft.dropdown.Option("p2", "P2 - 很快"),
                ft.dropdown.Option("p3", "P3 - 快"),
                ft.dropdown.Option("p4", "P4 - 中等 (推荐)"),
                ft.dropdown.Option("p5", "P5 - 慢"),
                ft.dropdown.Option("p6", "P6 - 较慢"),
                ft.dropdown.Option("p7", "P7 - 最慢 (质量最好)"),
            ]
            self.preset_dropdown.value = "p4"
        elif encoder.endswith("_amf"):
            # AMD 编码器预设
            self.preset_dropdown.options = [
                ft.dropdown.Option("speed", "速度优先"),
                ft.dropdown.Option("balanced", "平衡 (推荐)"),
                ft.dropdown.Option("quality", "质量优先"),
            ]
            self.preset_dropdown.value = "balanced"
        elif encoder.endswith("_qsv"):
            # Intel 编码器预设
            self.preset_dropdown.options = [
                ft.dropdown.Option("veryfast", "很快"),
                ft.dropdown.Option("faster", "较快"),
                ft.dropdown.Option("fast", "快"),
                ft.dropdown.Option("medium", "中等 (推荐)"),
                ft.dropdown.Option("slow", "慢"),
            ]
            self.preset_dropdown.value = "medium"
        else:
            # CPU 编码器预设
            self.preset_dropdown.options = [
                ft.dropdown.Option("ultrafast", "最快 (质量最低)"),
                ft.dropdown.Option("superfast", "超快"),
                ft.dropdown.Option("veryfast", "很快"),
                ft.dropdown.Option("faster", "较快"),
                ft.dropdown.Option("fast", "快 (推荐)"),
                ft.dropdown.Option("medium", "中等"),
                ft.dropdown.Option("slow", "慢 (质量更好)"),
            ]
            self.preset_dropdown.value = "fast"
        
        self.page.update()
    
    def _on_quality_change(self, e) -> None:
        """处理质量滑块变化。"""
        quality = int(e.control.value)
        self.quality_text.value = f"质量: {quality} (数值越小，质量越好，文件越大)"
        self.page.update()
    
    def _on_select_folder(self, e) -> None:
        """选择输出文件夹。"""
        self.folder_picker.get_directory_path(
            dialog_title="选择保存位置"
        )
    
    def _on_folder_selected(self, e: ft.FilePickerResultEvent) -> None:
        """处理文件夹选择结果。"""
        if e.path:
            self.output_path_field.value = e.path
            self.page.update()
    
    def _on_open_folder(self, e) -> None:
        """打开输出文件夹。"""
        import os
        output_path = self.output_path_field.value
        if output_path and Path(output_path).exists():
            if sys.platform == 'win32':
                os.startfile(output_path)
            elif sys.platform == 'darwin':
                subprocess.run(['open', output_path])
            else:
                subprocess.run(['xdg-open', output_path])
    
    def _build_ffmpeg_stream(self) -> Optional[Tuple]:
        """构建 FFmpeg 录制流。
        
        Returns:
            (stream, output_file) 元组，如果 FFmpeg 不可用则返回 None
        """
        platform = self._get_platform()
        
        # 生成输出文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(self.output_path_field.value)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_format = self.format_dropdown.value
        self.output_file = output_dir / f"screen_record_{timestamp}.{output_format}"
        
        fps = self.fps_dropdown.value
        encoder = self.encoder_dropdown.value
        preset = self.preset_dropdown.value
        quality = int(self.quality_slider.value)
        
        streams = []
        
        if platform == 'windows':
            area_mode = self.area_dropdown.value
            
            # 构建视频输入参数
            input_kwargs = {
                'format': 'gdigrab',
                'framerate': fps,
            }
            
            if area_mode == "window":
                window_title = self.window_dropdown.value
                if window_title and window_title != "none":
                    input_name = f'title={window_title}'
                else:
                    input_name = 'desktop'
            elif area_mode == "custom":
                offset_x = self.offset_x.value or "0"
                offset_y = self.offset_y.value or "0"
                width = self.width_field.value or "1920"
                height = self.height_field.value or "1080"
                input_kwargs['offset_x'] = offset_x
                input_kwargs['offset_y'] = offset_y
                input_kwargs['video_size'] = f'{width}x{height}'
                input_name = 'desktop'
            else:
                input_name = 'desktop'
            
            video_stream = ffmpeg.input(input_name, **input_kwargs)
            streams.append(video_stream)
            
            # 音频输入 - 支持麦克风和系统音频
            audio_inputs = []
            
            if self.record_mic.value:
                mic_device = self.mic_device_dropdown.value
                if mic_device and mic_device != "none":
                    audio_inputs.append(f'audio={mic_device}')
            
            if self.record_system_audio.value:
                sys_device = self.system_audio_dropdown.value
                if sys_device and sys_device != "none":
                    audio_inputs.append(f'audio={sys_device}')
            
            # 如果有多个音频源，需要使用 amix 混音
            if len(audio_inputs) == 1:
                audio_stream = ffmpeg.input(audio_inputs[0], format='dshow')
                streams.append(audio_stream)
            elif len(audio_inputs) > 1:
                # 多个音频源混音
                audio_streams = [ffmpeg.input(dev, format='dshow') for dev in audio_inputs]
                streams.extend(audio_streams)
                
        elif platform == 'macos':
            # macOS: 组合音频设备 ID
            audio_device = "none"
            if self.record_mic.value:
                mic_device = self.mic_device_dropdown.value
                if mic_device and mic_device != "none":
                    audio_device = mic_device
            elif self.record_system_audio.value:
                sys_device = self.system_audio_dropdown.value
                if sys_device and sys_device != "none":
                    audio_device = sys_device
            
            video_stream = ffmpeg.input(
                f'1:{audio_device}',
                format='avfoundation',
                framerate=fps,
            )
            streams.append(video_stream)
                
        else:
            # Linux 使用 x11grab
            display = ':0.0'
            area_mode = self.area_dropdown.value
            
            input_kwargs = {
                'format': 'x11grab',
                'framerate': fps,
            }
            
            if area_mode == "custom":
                offset_x = self.offset_x.value or "0"
                offset_y = self.offset_y.value or "0"
                width = self.width_field.value or "1920"
                height = self.height_field.value or "1080"
                input_kwargs['video_size'] = f'{width}x{height}'
                input_name = f'{display}+{offset_x},{offset_y}'
            else:
                input_name = display
            
            video_stream = ffmpeg.input(input_name, **input_kwargs)
            streams.append(video_stream)
            
            # Linux 音频使用 pulse
            if self.record_mic.value:
                mic_device = self.mic_device_dropdown.value or "default"
                audio_stream = ffmpeg.input(mic_device, format='pulse')
                streams.append(audio_stream)
            elif self.record_system_audio.value:
                sys_device = self.system_audio_dropdown.value or "default"
                audio_stream = ffmpeg.input(sys_device, format='pulse')
                streams.append(audio_stream)
        
        # 输出参数
        output_kwargs = {
            'vcodec': encoder,
            'pix_fmt': 'yuv420p',
        }
        
        # 根据编码器类型设置参数
        if encoder.endswith("_nvenc"):
            # NVENC 编码器 - 与项目其他地方保持一致
            output_kwargs['preset'] = preset
            output_kwargs['cq'] = quality
        elif encoder.endswith("_amf"):
            output_kwargs['quality'] = preset
            output_kwargs['rc'] = 'cqp'
            output_kwargs['qp_i'] = quality
            output_kwargs['qp_p'] = quality
        elif encoder.endswith("_qsv"):
            output_kwargs['preset'] = preset
            output_kwargs['global_quality'] = quality
        else:
            output_kwargs['preset'] = preset
            output_kwargs['crf'] = quality
        
        # 音频编码
        has_audio = self.record_mic.value or self.record_system_audio.value
        if has_audio and len(streams) > 1:
            output_kwargs['acodec'] = 'aac'
            output_kwargs['b:a'] = '192k'
            
            # 如果有多个音频流（麦克风+系统音频），需要混音
            if len(streams) > 2:
                # Windows 多音轨混音: 使用 filter_complex
                output_kwargs['filter_complex'] = f'[1:a][2:a]amix=inputs=2:duration=longest[aout]'
                output_kwargs['map'] = ['0:v', '[aout]']
        
        # 构建输出
        if len(streams) == 1:
            stream = ffmpeg.output(streams[0], str(self.output_file), **output_kwargs)
        else:
            stream = ffmpeg.output(*streams, str(self.output_file), **output_kwargs)
        
        return stream, self.output_file
    
    def _on_start_recording(self, e) -> None:
        """开始录制。"""
        try:
            # 再次检查 FFmpeg 可用性
            is_available, _ = self.ffmpeg_service.is_ffmpeg_available()
            if not is_available:
                self._show_message("FFmpeg 不可用，请先安装", ft.Colors.RED)
                return
            
            ffmpeg_path = self.ffmpeg_service.get_ffmpeg_path()
            if not ffmpeg_path:
                self._show_message("未找到 FFmpeg 路径", ft.Colors.RED)
                return
            
            result = self._build_ffmpeg_stream()
            if not result:
                self._show_message("无法构建 FFmpeg 命令", ft.Colors.RED)
                return
            
            stream, output_file = result
            
            # 获取完整命令用于日志
            cmd_args = ffmpeg.compile(stream, cmd=str(ffmpeg_path), overwrite_output=True)
            logger.info(f"开始录制，命令: {' '.join(cmd_args)}")
            
            # 使用 ffmpeg-python 启动异步进程
            self.recording_process = ffmpeg.run_async(
                stream,
                cmd=str(ffmpeg_path),
                pipe_stdin=True,
                pipe_stderr=True,
                overwrite_output=True,
            )
            
            # 启动线程监控 FFmpeg 输出
            self.stderr_output = []
            def read_stderr():
                try:
                    for line in iter(self.recording_process.stderr.readline, b''):
                        if line:
                            decoded = line.decode('utf-8', errors='replace').strip()
                            self.stderr_output.append(decoded)
                            if 'error' in decoded.lower() or 'failed' in decoded.lower():
                                logger.error(f"FFmpeg: {decoded}")
                except Exception:
                    pass
            
            stderr_thread = threading.Thread(target=read_stderr, daemon=True)
            stderr_thread.start()
            
            # 等待一小段时间检查进程是否正常启动
            time.sleep(0.5)
            if self.recording_process.poll() is not None:
                # 进程已结束，说明启动失败
                error_output = '\n'.join(self.stderr_output[-5:]) if self.stderr_output else "未知错误"
                logger.error(f"FFmpeg 启动失败: {error_output}")
                self._show_message(f"FFmpeg 启动失败: {error_output[:100]}", ft.Colors.RED)
                self.recording_process = None
                return
            
            self.is_recording = True
            self.is_paused = False
            self.recording_start_time = time.time()
            self.pause_duration = 0.0
            self.should_stop_timer = False
            
            # 更新 UI
            self._update_ui_state()
            
            # 启动计时器线程
            self.timer_thread = threading.Thread(target=self._timer_loop, daemon=True)
            self.timer_thread.start()
            
            self._show_message("录制已开始 (按 F9 停止)", ft.Colors.GREEN)
            
        except Exception as ex:
            logger.error(f"启动录制失败: {ex}", exc_info=True)
            self._show_message(f"启动录制失败: {ex}", ft.Colors.RED)
    
    def _on_pause_recording(self, e) -> None:
        """暂停/继续录制。"""
        # 注意：FFmpeg 的 gdigrab 不直接支持暂停
        # 这里通过向进程发送信号来模拟暂停（仅 Unix 系统支持）
        if self._get_platform() != 'windows':
            if self.recording_process:
                import signal
                if self.is_paused:
                    # 继续
                    self.recording_process.send_signal(signal.SIGCONT)
                    self.is_paused = False
                    self.pause_duration += time.time() - self.pause_start_time
                    self.pause_btn.text = "暂停"
                    self.pause_btn.icon = ft.Icons.PAUSE
                    self._show_message("录制已继续", ft.Colors.GREEN)
                else:
                    # 暂停
                    self.recording_process.send_signal(signal.SIGSTOP)
                    self.is_paused = True
                    self.pause_start_time = time.time()
                    self.pause_btn.text = "继续"
                    self.pause_btn.icon = ft.Icons.PLAY_ARROW
                    self._show_message("录制已暂停", ft.Colors.ORANGE)
                self.page.update()
        else:
            self._show_message("Windows 平台暂不支持暂停功能", ft.Colors.ORANGE)
    
    def _on_stop_recording(self, e) -> None:
        """停止录制。"""
        self._stop_recording()
    
    def _stop_recording(self) -> None:
        """停止录制进程。"""
        if self.recording_process:
            try:
                # 检查进程是否还在运行
                if self.recording_process.poll() is None:
                    # 方法1: 尝试发送 'q' 命令让 FFmpeg 正常退出
                    try:
                        if self.recording_process.stdin:
                            self.recording_process.stdin.write(b'q\n')
                            self.recording_process.stdin.flush()
                    except Exception as ex:
                        logger.debug(f"发送 q 命令失败: {ex}")
                    
                    # 等待进程结束
                    try:
                        self.recording_process.wait(timeout=3)
                        logger.info("FFmpeg 正常退出")
                    except subprocess.TimeoutExpired:
                        # 方法2: 如果 'q' 命令无效，使用 terminate
                        logger.info("发送 terminate 信号...")
                        self.recording_process.terminate()
                        try:
                            self.recording_process.wait(timeout=3)
                        except subprocess.TimeoutExpired:
                            # 方法3: 最后使用 kill 强制终止
                            logger.info("发送 kill 信号...")
                            self.recording_process.kill()
                            self.recording_process.wait(timeout=2)
                else:
                    # 进程已经结束
                    exit_code = self.recording_process.returncode
                    logger.warning(f"FFmpeg 进程已结束，退出码: {exit_code}")
                    # 输出收集到的错误信息
                    if hasattr(self, 'stderr_output') and self.stderr_output:
                        logger.error(f"FFmpeg 输出: {self.stderr_output[-10:]}")
                
            except Exception as ex:
                logger.warning(f"停止录制时出错: {ex}")
                try:
                    self.recording_process.kill()
                except Exception:
                    pass
            finally:
                # 关闭所有管道
                try:
                    if self.recording_process.stdin:
                        self.recording_process.stdin.close()
                    if self.recording_process.stdout:
                        self.recording_process.stdout.close()
                    if self.recording_process.stderr:
                        self.recording_process.stderr.close()
                except Exception:
                    pass
                self.recording_process = None
        
        self.is_recording = False
        self.is_paused = False
        self.should_stop_timer = True
        
        # 更新 UI
        self._update_ui_state()
        
        if self.output_file and self.output_file.exists():
            file_size = self.output_file.stat().st_size
            size_mb = file_size / (1024 * 1024)
            self._show_message(f"录制完成！文件大小: {size_mb:.1f} MB", ft.Colors.GREEN)
            self.open_folder_btn.visible = True
            self.page.update()
        else:
            self._show_message("录制已停止", ft.Colors.ORANGE)
    
    def _timer_loop(self) -> None:
        """计时器循环。"""
        while not self.should_stop_timer and self.is_recording:
            if not self.is_paused:
                elapsed = time.time() - self.recording_start_time - self.pause_duration
                hours = int(elapsed // 3600)
                minutes = int((elapsed % 3600) // 60)
                seconds = int(elapsed % 60)
                
                # 更新 UI（需要在主线程）
                self.timer_text.value = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                
                # 闪烁录制指示器
                if hasattr(self, 'recording_indicator'):
                    self.recording_indicator.content = ft.Icon(
                        ft.Icons.FIBER_MANUAL_RECORD,
                        color=ft.Colors.RED if int(elapsed) % 2 == 0 else ft.Colors.RED_200,
                        size=16,
                    )
                
                try:
                    self.page.update()
                except Exception:
                    break
            
            time.sleep(0.5)
    
    def _update_ui_state(self) -> None:
        """更新 UI 状态。"""
        if self.is_recording:
            self.start_btn.disabled = True
            self.pause_btn.disabled = (self._get_platform() == 'windows')  # Windows 不支持暂停
            self.stop_btn.disabled = False
            self.status_text.value = "正在录制..."
            self.status_text.color = ft.Colors.RED
            self.recording_indicator.content = ft.Icon(
                ft.Icons.FIBER_MANUAL_RECORD, color=ft.Colors.RED, size=16
            )
            # 禁用设置
            self.fps_dropdown.disabled = True
            self.format_dropdown.disabled = True
            self.encoder_dropdown.disabled = True
            self.preset_dropdown.disabled = True
            self.quality_slider.disabled = True
            self.area_dropdown.disabled = True
            self.record_mic.disabled = True
            self.mic_device_dropdown.disabled = True
            self.record_system_audio.disabled = True
            self.system_audio_dropdown.disabled = True
            self.window_dropdown.disabled = True
        else:
            self.start_btn.disabled = False
            self.pause_btn.disabled = True
            self.stop_btn.disabled = True
            self.status_text.value = "准备就绪"
            self.status_text.color = ft.Colors.ON_SURFACE_VARIANT
            self.recording_indicator.content = ft.Icon(
                ft.Icons.FIBER_MANUAL_RECORD, color=ft.Colors.GREY, size=16
            )
            # 启用设置
            self.fps_dropdown.disabled = False
            self.format_dropdown.disabled = False
            self.encoder_dropdown.disabled = False
            self.preset_dropdown.disabled = False
            self.quality_slider.disabled = False
            self.area_dropdown.disabled = False
            self.record_mic.disabled = False
            self.mic_device_dropdown.disabled = False
            self.record_system_audio.disabled = False
            self.system_audio_dropdown.disabled = False
            self.window_dropdown.disabled = False
        
        self.page.update()
    
    def _show_message(self, message: str, color: str = ft.Colors.PRIMARY) -> None:
        """显示消息提示。"""
        snack_bar = ft.SnackBar(
            content=ft.Text(message, color=ft.Colors.WHITE),
            bgcolor=color,
            duration=3000,
        )
        self.page.snack_bar = snack_bar
        snack_bar.open = True
        self.page.update()
    
    def cleanup(self) -> None:
        """清理视图资源，释放内存。"""
        # 停止录制
        if self.is_recording:
            self._stop_recording()
        
        self.should_stop_timer = True
        
        # 移除快捷键
        self._remove_keyboard_shortcuts()
        
        # 移除 file picker
        if hasattr(self, 'folder_picker') and self.folder_picker in self.page.overlay:
            self.page.overlay.remove(self.folder_picker)
        
        # 清除回调引用，打破循环引用
        self.on_back = None
        # 清除 UI 内容
        self.content = None
        
        gc.collect()
        logger.info("屏幕录制视图资源已清理")
