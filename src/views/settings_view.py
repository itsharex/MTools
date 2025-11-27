# -*- coding: utf-8 -*-
"""设置视图模块。

提供应用设置界面，包括数据目录设置、主题设置等。
"""

from pathlib import Path
from typing import Callable, Optional, List, Dict
import threading
import time

import flet as ft
import httpx

from constants import (
    BORDER_RADIUS_MEDIUM,
    PADDING_LARGE,
    PADDING_MEDIUM,
    PADDING_SMALL,
    PADDING_XLARGE,
    SURFACE_VARIANT,
)
from services import ConfigService


class SettingsView(ft.Container):
    """设置视图类。
    
    提供应用设置功能，包括：
    - 数据存储目录设置
    - 默认/自定义目录切换
    - 目录浏览和选择
    """

    def __init__(self, page: ft.Page, config_service: ConfigService) -> None:
        """初始化设置视图。
        
        Args:
            page: Flet页面对象
            config_service: 配置服务实例
        """
        super().__init__()
        self.page: ft.Page = page
        self._saved_page: ft.Page = page  # 保存页面引用,防止在布局重建后丢失
        self.config_service: ConfigService = config_service
        self.expand: bool = True
        # 左右边距使用 PADDING_LARGE
        self.padding: ft.padding = ft.padding.only(
            left=PADDING_MEDIUM,
            right=PADDING_MEDIUM,
            top=PADDING_MEDIUM,
            bottom=PADDING_MEDIUM
        )
        
        # 必应壁纸相关变量
        self.bing_wallpapers: List[Dict] = []  # 存储8张壁纸信息
        self.current_wallpaper_index: int = 0  # 当前壁纸索引
        self.auto_switch_timer: Optional[threading.Timer] = None  # 自动切换定时器
        
        # 创建UI组件
        self._build_ui()
        
        # 恢复自动切换状态（如果之前已启用）
        self._restore_auto_switch_state()
    
    def _restore_auto_switch_state(self) -> None:
        """恢复自动切换状态（在初始化时调用）。"""
        auto_switch_enabled = self.config_service.get_config_value("wallpaper_auto_switch", False)
        current_bg = self.config_service.get_config_value("background_image", None)
        
        # 检查当前背景是否是必应壁纸URL（包含bing.com）
        is_bing_wallpaper = current_bg and isinstance(current_bg, str) and "bing.com" in current_bg.lower()
        
        if auto_switch_enabled or is_bing_wallpaper:
            # 如果启用了自动切换，或者当前使用的是必应壁纸，则自动获取壁纸列表
            def fetch_wallpapers():
                wallpapers = self._fetch_bing_wallpaper()
                if wallpapers:
                    self.bing_wallpapers = wallpapers
                    
                    # 尝试找到当前壁纸在列表中的位置
                    if is_bing_wallpaper:
                        for i, wp in enumerate(wallpapers):
                            if wp["url"] == current_bg:
                                self.current_wallpaper_index = i
                                break
                    
                    # 更新UI
                    self._update_wallpaper_info_ui()
                    
                    # 如果启用了自动切换，启动定时器
                    if auto_switch_enabled:
                        interval = self.config_service.get_config_value("wallpaper_switch_interval", 30)
                        self._start_auto_switch(interval)
            
            # 使用后台线程获取，避免阻塞UI启动
            import threading
            thread = threading.Thread(target=fetch_wallpapers, daemon=True)
            thread.start()
    
    def _build_ui(self) -> None:
        """构建用户界面。"""
        # 页面标题
        title: ft.Text = ft.Text(
            "设置",
            size=32,
            weight=ft.FontWeight.BOLD,
        )
        
        # 数据目录设置部分
        data_dir_section: ft.Container = self._build_data_dir_section()
        
        # 主题模式设置部分
        theme_mode_section: ft.Container = self._build_theme_mode_section()
        
        # 主题色设置部分
        theme_color_section: ft.Container = self._build_theme_color_section()
        
        # 外观设置部分（透明度和背景图片）
        appearance_section: ft.Container = self._build_appearance_section()
        
        # GPU加速设置部分
        gpu_acceleration_section: ft.Container = self._build_gpu_acceleration_section()
        
        # 字体设置部分
        font_section: ft.Container = self._build_font_section()
        
        # 关于部分
        about_section: ft.Container = self._build_about_section()
        
        # 组装视图
        self.content = ft.Column(
            controls=[
                title,
                ft.Container(height=PADDING_LARGE),
                data_dir_section,
                ft.Container(height=PADDING_LARGE),
                theme_mode_section,
                ft.Container(height=PADDING_LARGE),
                theme_color_section,
                ft.Container(height=PADDING_LARGE),
                appearance_section,
                ft.Container(height=PADDING_LARGE),
                gpu_acceleration_section,
                ft.Container(height=PADDING_LARGE),
                font_section,
                ft.Container(height=PADDING_LARGE),
                about_section,
            ],
            spacing=0,
            scroll=ft.ScrollMode.HIDDEN,  # 隐藏滚动条
        )
    
    def _build_theme_mode_section(self) -> ft.Container:
        """构建主题模式设置部分。
        
        Returns:
            主题模式设置容器
        """
        # 分区标题
        section_title: ft.Text = ft.Text(
            "主题模式",
            size=20,
            weight=ft.FontWeight.W_600,
        )
        
        # 获取当前保存的主题模式
        saved_theme_mode = self.config_service.get_config_value("theme_mode", "system")
        
        # 主题模式单选按钮
        self.theme_mode_radio: ft.RadioGroup = ft.RadioGroup(
            content=ft.Row(
                controls=[
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Icon(ft.Icons.BRIGHTNESS_AUTO, size=32, ),
                                ft.Text("跟随系统", size=14, weight=ft.FontWeight.W_500),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=PADDING_MEDIUM // 2,
                        ),
                        data="system",
                        width=120,
                        height=100,
                        border_radius=BORDER_RADIUS_MEDIUM,
                        border=ft.border.all(2 if saved_theme_mode == "system" else 1, ft.Colors.PRIMARY if saved_theme_mode == "system" else ft.Colors.OUTLINE),
                        padding=PADDING_MEDIUM,
                        ink=True,
                        on_click=lambda e: self._on_theme_mode_container_click("system"),
                    ),
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Icon(ft.Icons.LIGHT_MODE, size=32, ),
                                ft.Text("浅色模式", size=14, weight=ft.FontWeight.W_500),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=PADDING_MEDIUM // 2,
                        ),
                        data="light",
                        width=120,
                        height=100,
                        border_radius=BORDER_RADIUS_MEDIUM,
                        border=ft.border.all(2 if saved_theme_mode == "light" else 1, ft.Colors.PRIMARY if saved_theme_mode == "light" else ft.Colors.OUTLINE),
                        padding=PADDING_MEDIUM,
                        ink=True,
                        on_click=lambda e: self._on_theme_mode_container_click("light"),
                    ),
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Icon(ft.Icons.DARK_MODE, size=32, ),
                                ft.Text("深色模式", size=14, weight=ft.FontWeight.W_500),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=PADDING_MEDIUM // 2,
                        ),
                        data="dark",
                        width=120,
                        height=100,
                        border_radius=BORDER_RADIUS_MEDIUM,
                        border=ft.border.all(2 if saved_theme_mode == "dark" else 1, ft.Colors.PRIMARY if saved_theme_mode == "dark" else ft.Colors.OUTLINE),
                        padding=PADDING_MEDIUM,
                        ink=True,
                        on_click=lambda e: self._on_theme_mode_container_click("dark"),
                    ),
                ],
                spacing=PADDING_LARGE,
            ),
            value=saved_theme_mode,
        )
        
        # 保存主题模式容器的引用，用于更新样式
        self.theme_mode_containers: list = [
            self.theme_mode_radio.content.controls[0],
            self.theme_mode_radio.content.controls[1],
            self.theme_mode_radio.content.controls[2],
        ]
        
        # 说明文字
        info_text: ft.Text = ft.Text(
            "主题模式会立即生效",
            size=12,
            color=ft.Colors.ON_SURFACE_VARIANT,
        )
        
        # 组装主题模式设置部分
        return ft.Container(
            content=ft.Column(
                controls=[
                    section_title,
                    ft.Container(height=PADDING_MEDIUM),
                    self.theme_mode_radio,
                    ft.Container(height=PADDING_MEDIUM // 2),
                    info_text,
                ],
                spacing=0,
            ),
            padding=PADDING_LARGE,
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=BORDER_RADIUS_MEDIUM,
        )
    
    def _on_theme_mode_container_click(self, mode: str) -> None:
        """主题模式容器点击事件处理。
        
        Args:
            mode: 主题模式 ("system", "light", "dark")
        """
        # 更新RadioGroup的值
        self.theme_mode_radio.value = mode
        
        # 保存到配置
        if self.config_service.set_config_value("theme_mode", mode):
            # 立即应用主题模式
            if mode == "system":
                self.page.theme_mode = ft.ThemeMode.SYSTEM
            elif mode == "light":
                self.page.theme_mode = ft.ThemeMode.LIGHT
            else:  # dark
                self.page.theme_mode = ft.ThemeMode.DARK
            
            # 更新所有容器的边框样式
            for container in self.theme_mode_containers:
                is_selected = container.data == mode
                container.border = ft.border.all(
                    2 if is_selected else 1,
                    ft.Colors.PRIMARY if is_selected else ft.Colors.OUTLINE
                )
                container.update()
            
            self.page.update()
            self._show_snackbar(f"已切换到{self._get_mode_name(mode)}", ft.Colors.GREEN)
        else:
            self._show_snackbar("主题模式更新失败", ft.Colors.RED)
    
    def _get_mode_name(self, mode: str) -> str:
        """获取主题模式的中文名称。
        
        Args:
            mode: 主题模式
        
        Returns:
            中文名称
        """
        mode_names = {
            "system": "跟随系统",
            "light": "浅色模式",
            "dark": "深色模式",
        }
        return mode_names.get(mode, mode)
    
    def _build_data_dir_section(self) -> ft.Container:
        """构建数据目录设置部分。
        
        Returns:
            数据目录设置容器
        """
        # 分区标题
        section_title: ft.Text = ft.Text(
            "数据存储",
            size=20,
            weight=ft.FontWeight.W_600,
        )
        
        # 当前数据目录显示
        current_dir: Path = self.config_service.get_data_dir()
        is_custom: bool = self.config_service.get_config_value("use_custom_dir", False)
        
        self.data_dir_text: ft.Text = ft.Text(
            str(current_dir),
            size=14,
            color=ft.Colors.ON_SURFACE_VARIANT,
            selectable=True,
        )
        
        # 目录类型单选按钮
        self.dir_type_radio: ft.RadioGroup = ft.RadioGroup(
            content=ft.Column(
                controls=[
                    ft.Radio(
                        value="default",
                        label="默认路径",
                    ),
                    ft.Radio(
                        value="custom",
                        label="自定义路径",
                    ),
                ],
                spacing=PADDING_MEDIUM,
            ),
            value="custom" if is_custom else "default",
            on_change=self._on_dir_type_change,
        )
        
        # 浏览按钮
        browse_button: ft.ElevatedButton = ft.ElevatedButton(
            text="浏览...",
            icon=ft.Icons.FOLDER_OPEN,
            on_click=self._on_browse_click,
            disabled=not is_custom,
        )
        
        self.browse_button: ft.ElevatedButton = browse_button
        
        # 打开目录按钮
        open_dir_button: ft.OutlinedButton = ft.OutlinedButton(
            text="打开数据目录",
            icon=ft.Icons.FOLDER,
            on_click=self._on_open_dir_click,
        )
        
        # 按钮行
        button_row: ft.Row = ft.Row(
            controls=[browse_button, open_dir_button],
            spacing=PADDING_MEDIUM,
        )
        
        # 目录路径容器
        dir_path_container: ft.Container = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("当前数据目录:", size=14, weight=ft.FontWeight.W_500),
                    self.data_dir_text,
                ],
                spacing=PADDING_MEDIUM // 2,
            ),
            padding=PADDING_MEDIUM,
            border=ft.border.all(1, ft.Colors.OUTLINE),
            border_radius=BORDER_RADIUS_MEDIUM,
        )
        
        # 说明文字
        info_text: ft.Text = ft.Text(
            "数据目录用于存储应用的处理结果和临时文件",
            size=12,
            color=ft.Colors.ON_SURFACE_VARIANT,
        )
        
        # 组装数据目录部分
        return ft.Container(
            content=ft.Column(
                controls=[
                    section_title,
                    ft.Container(height=PADDING_MEDIUM),
                    self.dir_type_radio,
                    ft.Container(height=PADDING_MEDIUM),
                    dir_path_container,
                    ft.Container(height=PADDING_MEDIUM),
                    button_row,
                    ft.Container(height=PADDING_MEDIUM // 2),
                    info_text,
                ],
                spacing=0,
            ),
            padding=PADDING_LARGE,
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=BORDER_RADIUS_MEDIUM,
        )
    
    def _get_gpu_device_options(self) -> list:
        """获取可用的GPU设备选项列表。
        
        Returns:
            GPU设备选项列表
        """
        gpu_options = []
        
        # 方法1: 尝试使用ONNX Runtime检测GPU
        try:
            import onnxruntime as ort
            available_providers = ort.get_available_providers()
            
            if 'CUDAExecutionProvider' in available_providers:
                # CUDA支持多GPU，但需要nvidia-smi来获取详细信息
                # 打包后可能没有nvidia-smi，所以提供通用选项
                gpu_options = [
                    ft.dropdown.Option("0", "🎮 GPU 0 - NVIDIA CUDA (主GPU)"),
                    ft.dropdown.Option("1", "GPU 1 - NVIDIA CUDA"),
                    ft.dropdown.Option("2", "GPU 2 - NVIDIA CUDA"),
                    ft.dropdown.Option("3", "GPU 3 - NVIDIA CUDA"),
                ]
                return gpu_options
            elif 'DmlExecutionProvider' in available_providers:
                # DirectML通常只能访问默认GPU
                gpu_options = [
                    ft.dropdown.Option("0", "🎮 GPU 0 - DirectML (默认GPU)"),
                ]
                return gpu_options
            elif 'ROCMExecutionProvider' in available_providers:
                # AMD ROCm支持多GPU
                gpu_options = [
                    ft.dropdown.Option("0", "🎮 GPU 0 - AMD ROCm (主GPU)"),
                    ft.dropdown.Option("1", "GPU 1 - AMD ROCm"),
                    ft.dropdown.Option("2", "GPU 2 - AMD ROCm"),
                ]
                return gpu_options
        except Exception:
            pass
        
        # 方法2: 默认选项（如果ONNX Runtime未检测到GPU）
        return [
            ft.dropdown.Option("0", "🎮 GPU 0 - 默认GPU"),
            ft.dropdown.Option("1", "GPU 1"),
            ft.dropdown.Option("2", "GPU 2"),
            ft.dropdown.Option("3", "GPU 3"),
        ]
    
    def _build_appearance_section(self) -> ft.Container:
        """构建外观设置部分（透明度和背景图片）。
        
        Returns:
            外观设置容器
        """
        section_title = ft.Text(
            "外观",
            size=20,
            weight=ft.FontWeight.W_600,
        )
        
        # 获取当前配置
        current_opacity = self.config_service.get_config_value("window_opacity", 1.0)
        current_bg_image = self.config_service.get_config_value("background_image", None)
        current_bg_fit = self.config_service.get_config_value("background_image_fit", "cover")
        
        # 不透明度滑块
        self.opacity_value_text = ft.Text(
            f"{int(current_opacity * 100)}%",
            size=13,
            text_align=ft.TextAlign.END,
            width=60,
        )
        
        self.opacity_slider = ft.Slider(
            min=0.3,
            max=1.0,
            value=current_opacity,
            divisions=14,
            # label 不使用,因为格式化不够灵活,使用右侧文本显示
            on_change=self._on_opacity_change,
        )
        
        opacity_row = ft.Row(
            controls=[
                ft.Text("窗口不透明度", size=13),  # 改为"不透明度"更准确
                self.opacity_value_text,
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )
        
        opacity_container = ft.Column(
            controls=[
                opacity_row,
                self.opacity_slider,
                ft.Text(
                    "调整窗口的不透明度（30%-100%，数值越低越透明）",
                    size=11,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
            ],
            spacing=PADDING_SMALL,
        )
        
        # 背景图片设置
        # 如果当前背景是必应壁纸，显示友好的提示文本
        bg_text_display = current_bg_image if current_bg_image else "未设置"
        if current_bg_image and isinstance(current_bg_image, str) and "bing.com" in current_bg_image.lower():
            bg_text_display = "必应壁纸"  # 先显示"必应壁纸"，等信息加载后再更新具体标题
        
        self.bg_image_text = ft.Text(
            bg_text_display,
            size=12,
            color=ft.Colors.ON_SURFACE_VARIANT,
            max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
            expand=True,
        )
        
        self.bg_image_picker = ft.FilePicker(
            on_result=self._on_bg_image_selected
        )
        self.page.overlay.append(self.bg_image_picker)
        
        bg_image_row = ft.Row(
            controls=[
                ft.Text("背景图片:", size=13),
                self.bg_image_text,
                ft.IconButton(
                    icon=ft.Icons.FOLDER_OPEN,
                    tooltip="选择背景图片",
                    on_click=lambda _: self.bg_image_picker.pick_files(
                        allowed_extensions=["png", "jpg", "jpeg", "webp", "bmp"],
                        dialog_title="选择背景图片"
                    ),
                ),
                ft.IconButton(
                    icon=ft.Icons.CLEAR,
                    tooltip="清除背景图片",
                    on_click=self._on_clear_bg_image,
                ),
            ],
            spacing=PADDING_SMALL,
        )
        
        # 背景图片适应模式
        self.bg_fit_dropdown = ft.Dropdown(
            width=220,
            value=current_bg_fit,
            options=[
                ft.dropdown.Option("cover", "覆盖 - 填满窗口(可能裁剪)"),
                ft.dropdown.Option("contain", "适应 - 完整显示(可能留白)"),
                ft.dropdown.Option("fill", "拉伸 - 填满窗口(可能变形)"),
                ft.dropdown.Option("none", "原始尺寸 - 不缩放"),
            ],
            dense=True,
            on_change=self._on_bg_fit_change,
        )
        
        bg_fit_row = ft.Row(
            controls=[
                ft.Text("适应模式:", size=13),
                self.bg_fit_dropdown,
            ],
            spacing=PADDING_SMALL,
        )
        
        # 创建壁纸计数和信息文本控件
        self.wallpaper_count_text = ft.Text(
            "0 / 0",
            size=12,
            weight=ft.FontWeight.W_500,
        )
        
        self.wallpaper_info_text = ft.Text(
            "点击「获取壁纸」从必应获取精美壁纸",
            size=11,
            color=ft.Colors.ON_SURFACE_VARIANT,
            max_lines=2,
            overflow=ft.TextOverflow.ELLIPSIS,
        )
        
        self.switch_interval_text = ft.Text(
            f"{self.config_service.get_config_value('wallpaper_switch_interval', 30)} 分钟",
            size=12,
        )
        
        bg_image_container = ft.Column(
            controls=[
                bg_image_row,
                bg_fit_row,
                ft.Divider(height=PADDING_MEDIUM),
                # 必应壁纸部分
                ft.Text("必应壁纸", size=14, weight=ft.FontWeight.W_500),
                ft.Row(
                    controls=[
                        ft.ElevatedButton(
                            text="获取壁纸",
                            icon=ft.Icons.CLOUD_DOWNLOAD,
                            on_click=self._on_random_wallpaper,
                            tooltip="从必应获取8张壁纸",
                        ),
                        ft.IconButton(
                            icon=ft.Icons.ARROW_BACK,
                            tooltip="上一张",
                            on_click=self._previous_wallpaper,
                        ),
                        ft.IconButton(
                            icon=ft.Icons.ARROW_FORWARD,
                            tooltip="下一张",
                            on_click=self._next_wallpaper,
                        ),
                    ],
                    spacing=PADDING_SMALL,
                ),
                # 壁纸信息显示
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Text("当前:", size=12),
                                    self.wallpaper_count_text,
                                ],
                                spacing=PADDING_SMALL,
                            ),
                            self.wallpaper_info_text,
                        ],
                        spacing=PADDING_SMALL // 2,
                    ),
                    padding=PADDING_SMALL,
                    border=ft.border.all(1, ft.Colors.OUTLINE),
                    border_radius=BORDER_RADIUS_MEDIUM,
                ),
                # 自动切换设置
                ft.Row(
                    controls=[
                        ft.Switch(
                            label="自动切换",
                            value=self.config_service.get_config_value("wallpaper_auto_switch", False),
                            on_change=self._on_auto_switch_change,
                        ),
                        self.switch_interval_text,
                    ],
                    spacing=PADDING_SMALL,
                ),
                ft.Slider(
                    min=5,
                    max=120,
                    divisions=23,
                    value=self.config_service.get_config_value("wallpaper_switch_interval", 30),
                    label="{value}分钟",
                    on_change=self._on_switch_interval_change,
                ),
                ft.Text(
                    "启用自动切换后，壁纸会按设定的时间间隔自动轮换（5-120分钟）",
                    size=11,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
            ],
            spacing=PADDING_SMALL,
        )
        
        return ft.Container(
            content=ft.Column(
                controls=[
                    section_title,
                    ft.Container(height=PADDING_MEDIUM),
                    opacity_container,
                    ft.Container(height=PADDING_MEDIUM),
                    bg_image_container,
                ],
                spacing=0,
            ),
            padding=PADDING_LARGE,
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=BORDER_RADIUS_MEDIUM,
        )
    
    def _on_opacity_change(self, e: ft.ControlEvent) -> None:
        """透明度改变事件。"""
        value = e.control.value
        self.opacity_value_text.value = f"{int(value * 100)}%"
        
        # 保存配置
        self.config_service.set_config_value("window_opacity", value)
        
        # 使用保存的页面引用
        page = getattr(self, '_saved_page', self.page)
        if not page:
            return
        
        # 立即应用透明度 - 使用 window.opacity
        page.window.opacity = value
        
        # 同时更新导航栏的透明度
        if hasattr(page, '_main_view') and hasattr(page._main_view, 'navigation_container'):
            # 根据窗口透明度调整导航栏背景透明度
            # 调整为与窗口透明度一致，避免视觉差异过大
            nav_opacity = 0.95 * value  # 从0.85改为0.95，让导航栏更接近窗口透明度
            page._main_view.navigation_container.bgcolor = ft.Colors.with_opacity(
                nav_opacity, 
                ft.Colors.SURFACE
            )
        
        # 同时更新 FAB 的透明度
        if hasattr(page, 'floating_action_button') and page.floating_action_button:
            fab_opacity = 0.9 * value  # FAB 保持较高的可见度
            page.floating_action_button.bgcolor = ft.Colors.with_opacity(
                fab_opacity,
                ft.Colors.PRIMARY
            )
        
        # 同时更新标题栏的透明度
        if hasattr(page, '_main_view') and hasattr(page._main_view, 'title_bar'):
            # 标题栏保持较高的不透明度以保持可读性
            title_bar_opacity = 0.95 * value
            theme_color = page._main_view.title_bar.theme_color
            page._main_view.title_bar.bgcolor = ft.Colors.with_opacity(
                title_bar_opacity,
                theme_color
            )
        
        page.update()
    
    def _on_bg_image_selected(self, e: ft.FilePickerResultEvent) -> None:
        """背景图片选择事件。"""
        if e.files and len(e.files) > 0:
            image_path = e.files[0].path
            self.bg_image_text.value = image_path
            
            # 保存配置
            self.config_service.set_config_value("background_image", image_path)
            
            # 立即应用背景图片
            self._apply_background_image(image_path, self.bg_fit_dropdown.value)
            
            # 更新页面
            if self.page:
                self.page.update()
    
    def _on_clear_bg_image(self, e: ft.ControlEvent) -> None:
        """清除背景图片事件。"""
        self.bg_image_text.value = "未设置"
        
        # 保存配置
        self.config_service.set_config_value("background_image", None)
        
        # 清除背景图片
        self._apply_background_image(None, None)
        
        # 更新页面
        if self.page:
            self.page.update()
    
    def _on_bg_fit_change(self, e: ft.ControlEvent) -> None:
        """背景图片适应模式改变事件。"""
        fit_mode = e.control.value
        
        # 保存配置
        self.config_service.set_config_value("background_image_fit", fit_mode)
        
        # 重新应用背景图片
        bg_image = self.config_service.get_config_value("background_image", None)
        if bg_image:
            self._apply_background_image(bg_image, fit_mode)
    
    def _apply_background_image(self, image_path: Optional[str], fit_mode: Optional[str]) -> None:
        """应用背景图片。"""
        # 通过 _saved_page 获取页面引用(因为 self.page 可能在布局重建后失效)
        page = getattr(self, '_saved_page', self.page)
        
        if not page:
            return
            
        # 应用背景图片
        if hasattr(page, '_main_view') and hasattr(page._main_view, 'apply_background'):
            page._main_view.apply_background(image_path, fit_mode)
            
        # 应用背景后,重新应用当前的窗口透明度和各组件的透明度
        current_opacity = self.config_service.get_config_value("window_opacity", 1.0)
        
        # 重新应用窗口透明度
        page.window.opacity = current_opacity
        
        # 重新应用导航栏透明度
        if hasattr(page, '_main_view') and hasattr(page._main_view, 'navigation_container'):
            nav_opacity = 0.85 * current_opacity
            page._main_view.navigation_container.bgcolor = ft.Colors.with_opacity(
                nav_opacity, 
                ft.Colors.SURFACE
            )
        
        # 重新应用 FAB 透明度
        if hasattr(page, 'floating_action_button') and page.floating_action_button:
            fab_opacity = 0.9 * current_opacity
            page.floating_action_button.bgcolor = ft.Colors.with_opacity(
                fab_opacity,
                ft.Colors.PRIMARY
            )
        
        # 重新应用标题栏透明度
        if hasattr(page, '_main_view') and hasattr(page._main_view, 'title_bar'):
            title_bar_opacity = 0.95 * current_opacity
            theme_color = page._main_view.title_bar.theme_color
            page._main_view.title_bar.bgcolor = ft.Colors.with_opacity(
                title_bar_opacity,
                theme_color
            )
        
        page.update()

    def _fetch_bing_wallpaper(self, n: int = 8) -> Optional[List[Dict]]:
        """使用 httpx 从必应壁纸 API 获取最近 n 张壁纸的信息。

        Args:
            n: 获取最近 n 张壁纸（默认8）

        Returns:
            壁纸信息列表，每项包含 url、title、copyright 等字段，失败时返回 None
        """
        try:
            api = f"https://www.bing.com/HPImageArchive.aspx?format=js&n={n}&mkt=zh-CN"
            resp = httpx.get(api, timeout=10.0)
            resp.raise_for_status()
            data = resp.json()
            images = data.get("images", [])
            if not images:
                return None
            
            # 处理图片URL，确保是完整的URL
            wallpapers = []
            for img in images:
                url = img.get("url", "")
                if url:
                    # 如果是相对路径，拼接主域名
                    if not url.startswith("http"):
                        url = "https://www.bing.com" + url
                    wallpapers.append({
                        "url": url,
                        "title": img.get("title", ""),
                        "copyright": img.get("copyright", ""),
                        "startdate": img.get("startdate", ""),
                    })
            
            return wallpapers if wallpapers else None
        except Exception:
            return None

    def _on_random_wallpaper(self, e: ft.ControlEvent) -> None:
        """事件处理：从必应获取随机壁纸并应用。"""
        # 显示提示
        self._show_snackbar("正在从必应获取壁纸...", ft.Colors.BLUE)

        # 直接同步请求（请求较快），若担心阻塞可改为后台线程
        wallpapers = self._fetch_bing_wallpaper()
        if wallpapers:
            # 保存壁纸列表
            self.bing_wallpapers = wallpapers
            self.current_wallpaper_index = 0
            
            # 应用第一张壁纸
            self._apply_wallpaper(0)
            
            # 更新UI
            self._update_wallpaper_info_ui()
            
            self._show_snackbar(f"已获取{len(wallpapers)}张必应壁纸", ft.Colors.GREEN)
            
            # 如果自动切换已启用，启动定时器
            auto_switch_enabled = self.config_service.get_config_value("wallpaper_auto_switch", False)
            if auto_switch_enabled:
                interval = self.config_service.get_config_value("wallpaper_switch_interval", 30)
                self._start_auto_switch(interval)
        else:
            self._show_snackbar("获取壁纸失败，请检查网络或稍后重试", ft.Colors.RED)
    
    def _apply_wallpaper(self, index: int) -> None:
        """应用指定索引的壁纸。
        
        Args:
            index: 壁纸索引
        """
        if not self.bing_wallpapers or index < 0 or index >= len(self.bing_wallpapers):
            return
        
        wallpaper = self.bing_wallpapers[index]
        url = wallpaper["url"]
        
        # 更新UI文本（背景图片显示友好的标题）
        try:
            self.bg_image_text.value = f"必应壁纸: {wallpaper['title']}"
            self.bg_image_text.update()
        except Exception:
            pass
        
        # 保存配置
        self.config_service.set_config_value("background_image", url)
        self.current_wallpaper_index = index
        
        # 立即应用
        self._apply_background_image(url, self.bg_fit_dropdown.value)
    
    def _next_wallpaper(self, e: Optional[ft.ControlEvent] = None) -> None:
        """切换到下一张壁纸。"""
        if not self.bing_wallpapers:
            self._show_snackbar("请先获取必应壁纸", ft.Colors.ORANGE)
            return
        
        self.current_wallpaper_index = (self.current_wallpaper_index + 1) % len(self.bing_wallpapers)
        self._apply_wallpaper(self.current_wallpaper_index)
        self._update_wallpaper_info_ui()
    
    def _previous_wallpaper(self, e: Optional[ft.ControlEvent] = None) -> None:
        """切换到上一张壁纸。"""
        if not self.bing_wallpapers:
            self._show_snackbar("请先获取必应壁纸", ft.Colors.ORANGE)
            return
        
        self.current_wallpaper_index = (self.current_wallpaper_index - 1) % len(self.bing_wallpapers)
        self._apply_wallpaper(self.current_wallpaper_index)
        self._update_wallpaper_info_ui()
    
    def _update_wallpaper_info_ui(self) -> None:
        """更新壁纸信息UI。"""
        if not self.bing_wallpapers:
            return
        
        try:
            wallpaper = self.bing_wallpapers[self.current_wallpaper_index]
            
            # 更新壁纸计数显示
            if hasattr(self, 'wallpaper_count_text'):
                self.wallpaper_count_text.value = f"{self.current_wallpaper_index + 1} / {len(self.bing_wallpapers)}"
                self.wallpaper_count_text.update()
            
            # 更新壁纸信息
            if hasattr(self, 'wallpaper_info_text'):
                self.wallpaper_info_text.value = f"{wallpaper['title']}\n{wallpaper['copyright']}"
                self.wallpaper_info_text.update()
            
            # 更新背景图片文本显示（显示友好的标题而不是URL）
            if hasattr(self, 'bg_image_text'):
                self.bg_image_text.value = f"必应壁纸: {wallpaper['title']}"
                self.bg_image_text.update()
        except Exception as e:
            # 如果更新失败，至少确保不显示"加载中"
            print(f"更新壁纸UI信息失败: {e}")
            if hasattr(self, 'bg_image_text'):
                # 如果更新失败，显示通用的"必应壁纸"
                if "加载中" in self.bg_image_text.value or self.bg_image_text.value.startswith("http"):
                    self.bg_image_text.value = "必应壁纸"
                    try:
                        self.bg_image_text.update()
                    except:
                        pass
    
    def _on_auto_switch_change(self, e: ft.ControlEvent) -> None:
        """自动切换开关改变事件。"""
        enabled = e.control.value
        self.config_service.set_config_value("wallpaper_auto_switch", enabled)
        
        if enabled:
            # 启动自动切换
            interval = self.config_service.get_config_value("wallpaper_switch_interval", 30)
            self._start_auto_switch(interval)
            self._show_snackbar(f"已启用自动切换壁纸，间隔{interval}分钟", ft.Colors.GREEN)
        else:
            # 停止自动切换
            self._stop_auto_switch()
            self._show_snackbar("已关闭自动切换壁纸", ft.Colors.ORANGE)
    
    def _on_switch_interval_change(self, e: ft.ControlEvent) -> None:
        """切换间隔改变事件。"""
        interval = int(e.control.value)
        self.config_service.set_config_value("wallpaper_switch_interval", interval)
        
        # 如果自动切换已启用，重新启动定时器
        if self.config_service.get_config_value("wallpaper_auto_switch", False):
            self._start_auto_switch(interval)
        
        # 更新显示
        if hasattr(self, 'switch_interval_text'):
            self.switch_interval_text.value = f"{interval} 分钟"
            self.switch_interval_text.update()
    
    def _start_auto_switch(self, interval_minutes: int) -> None:
        """启动自动切换定时器。
        
        Args:
            interval_minutes: 切换间隔（分钟）
        """
        # 先停止现有定时器
        self._stop_auto_switch()
        
        # 创建新定时器
        def switch_task():
            if self.bing_wallpapers:
                self._next_wallpaper()
            # 递归调用，继续下一次定时
            self._start_auto_switch(interval_minutes)
        
        interval_seconds = interval_minutes * 60
        self.auto_switch_timer = threading.Timer(interval_seconds, switch_task)
        self.auto_switch_timer.daemon = True
        self.auto_switch_timer.start()
    
    def _stop_auto_switch(self) -> None:
        """停止自动切换定时器。"""
        if self.auto_switch_timer:
            self.auto_switch_timer.cancel()
            self.auto_switch_timer = None
    
    def _build_gpu_acceleration_section(self) -> ft.Container:
        """构建GPU加速设置部分，包括高级参数配置。"""

        # 标题与当前配置
        section_title = ft.Text(
            "GPU加速",
            size=20,
            weight=ft.FontWeight.W_600,
        )

        gpu_enabled = self.config_service.get_config_value("gpu_acceleration", True)
        gpu_memory_limit = self.config_service.get_config_value("gpu_memory_limit", 2048)
        gpu_device_id = self.config_service.get_config_value("gpu_device_id", 0)
        enable_memory_arena = self.config_service.get_config_value("gpu_enable_memory_arena", True)

        # GPU开关
        self.gpu_acceleration_switch = ft.Switch(
            label="启用GPU加速",
            value=gpu_enabled,
            on_change=self._on_gpu_acceleration_change,
        )

        # 检测ONNX Runtime的GPU支持（用于AI功能：智能抠图、人声分离）
        try:
            import onnxruntime as ort
            available_providers = ort.get_available_providers()
            
            gpu_providers = []
            if 'CUDAExecutionProvider' in available_providers:
                gpu_providers.append("NVIDIA CUDA")
            if 'DmlExecutionProvider' in available_providers:
                gpu_providers.append("DirectML")
            if 'ROCMExecutionProvider' in available_providers:
                gpu_providers.append("AMD ROCm")
            if 'CoreMLExecutionProvider' in available_providers:
                gpu_providers.append("Apple CoreML")
            
            if gpu_providers:
                provider_text = "、".join(gpu_providers)
                status_text = ft.Text(
                    f"检测到GPU加速支持: {provider_text}",
                    size=12,
                    color=ft.Colors.GREEN,
                )
            else:
                status_text = ft.Text(
                    "未检测到GPU加速支持，将使用CPU模式",
                    size=12,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                )
        except Exception:
            status_text = ft.Text(
                "未检测到GPU加速支持，将使用CPU模式",
                size=12,
                color=ft.Colors.ON_SURFACE_VARIANT,
            )

        # 高级设置控件
        self.gpu_memory_value_text = ft.Text(
            f"{gpu_memory_limit} MB",
            size=13,
            text_align=ft.TextAlign.END,
            width=80,
        )

        memory_label_row = ft.Row(
            controls=[
                ft.Text("GPU内存限制", size=13, ),
                self.gpu_memory_value_text,
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        self.gpu_memory_slider = ft.Slider(
            min=512,
            max=8192,
            divisions=15,
            value=gpu_memory_limit,
            label=None,
            on_change=self._on_gpu_memory_change,
        )

        # 动态检测GPU设备数量
        gpu_device_options = self._get_gpu_device_options()

        self.gpu_device_dropdown = ft.Dropdown(
            label="GPU设备",
            hint_text="在多GPU系统中选择一个设备",
            value=str(gpu_device_id),
            options=gpu_device_options,
            on_change=self._on_gpu_device_change,
            width=500,
        )

        self.memory_arena_switch = ft.Switch(
            label="启用内存池优化",
            value=enable_memory_arena,
            on_change=self._on_memory_arena_change,
        )

        advanced_content = ft.Column(
            controls=[
                memory_label_row,
                self.gpu_memory_slider,
                self.gpu_device_dropdown,
                self.memory_arena_switch,
            ],
            spacing=16,
        )

        self.gpu_advanced_title = ft.Text(
            "高级参数",
            size=14,
            weight=ft.FontWeight.W_500,
        )

        self.gpu_advanced_container = ft.Container(
            content=advanced_content,
            padding=ft.padding.all(PADDING_MEDIUM),
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=BORDER_RADIUS_MEDIUM,
            bgcolor=ft.Colors.with_opacity(0.03, ft.Colors.ON_SURFACE),
        )

        info_text = ft.Text(
            "启用GPU加速可显著提升图像与视频处理速度。如遇兼容性或显存不足问题，可在此调整参数。",
            size=12,
            color=ft.Colors.ON_SURFACE_VARIANT,
        )

        # 初始状态同步
        if not gpu_enabled:
            for ctrl in (self.gpu_memory_slider, self.gpu_device_dropdown, self.memory_arena_switch):
                ctrl.disabled = True
            self.gpu_memory_value_text.opacity = 0.6
            self.gpu_advanced_container.opacity = 0.6
        else:
            self.gpu_memory_value_text.opacity = 1.0
            self.gpu_advanced_container.opacity = 1.0

        return ft.Container(
            content=ft.Column(
                controls=[
                    section_title,
                    ft.Container(height=PADDING_MEDIUM),
                    self.gpu_acceleration_switch,
                    ft.Container(height=PADDING_SMALL),
                    status_text,
                    ft.Container(height=PADDING_MEDIUM),
                    self.gpu_advanced_title,
                    ft.Container(height=PADDING_SMALL),
                    self.gpu_advanced_container,
                    ft.Container(height=PADDING_MEDIUM // 2),
                    info_text,
                ],
                spacing=0,
            ),
            padding=PADDING_LARGE,
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=BORDER_RADIUS_MEDIUM,
        )
    
    def _on_gpu_acceleration_change(self, e: ft.ControlEvent) -> None:
        """GPU加速开关改变事件处理。
        
        Args:
            e: 控件事件对象
        """
        enabled = e.control.value
        if self.config_service.set_config_value("gpu_acceleration", enabled):
            status = "已启用" if enabled else "已禁用"
            self._show_snackbar(f"GPU加速{status}", ft.Colors.GREEN)
            self._update_gpu_controls_state(enabled)
        else:
            self._show_snackbar("GPU加速设置更新失败", ft.Colors.RED)
    
    def _on_gpu_memory_change(self, e: ft.ControlEvent) -> None:
        """GPU内存限制改变事件处理。
        
        Args:
            e: 控件事件对象
        """
        memory_limit = int(e.control.value)
        if self.config_service.set_config_value("gpu_memory_limit", memory_limit):
            self.gpu_memory_value_text.value = f"{memory_limit} MB"
            self.gpu_memory_value_text.update()
            self._show_snackbar(f"GPU内存限制已设置为 {memory_limit} MB", ft.Colors.GREEN)
        else:
            self._show_snackbar("GPU内存限制设置更新失败", ft.Colors.RED)
    
    def _on_gpu_device_change(self, e: ft.ControlEvent) -> None:
        """GPU设备ID改变事件处理。
        
        Args:
            e: 控件事件对象
        """
        device_id = int(e.control.value)
        if self.config_service.set_config_value("gpu_device_id", device_id):
            self._show_snackbar(f"GPU设备已设置为 GPU {device_id}", ft.Colors.GREEN)
        else:
            self._show_snackbar("GPU设备设置更新失败", ft.Colors.RED)
    
    def _on_memory_arena_change(self, e: ft.ControlEvent) -> None:
        """内存池优化开关改变事件处理。
        
        Args:
            e: 控件事件对象
        """
        enabled = e.control.value
        if self.config_service.set_config_value("gpu_enable_memory_arena", enabled):
            status = "已启用" if enabled else "已禁用"
            self._show_snackbar(f"内存池优化{status}", ft.Colors.GREEN)
        else:
            self._show_snackbar("内存池优化设置更新失败", ft.Colors.RED)

    def _update_gpu_controls_state(self, enabled: bool) -> None:
        """根据GPU加速开关更新高级参数控件的可用状态。"""

        for ctrl in (self.gpu_memory_slider, self.gpu_device_dropdown, self.memory_arena_switch):
            ctrl.disabled = not enabled
            ctrl.opacity = 1.0 if enabled else 0.6
            ctrl.update()

        self.gpu_advanced_container.opacity = 1.0 if enabled else 0.5
        self.gpu_advanced_container.update()

        self.gpu_memory_value_text.opacity = 1.0 if enabled else 0.6
        self.gpu_memory_value_text.update()

        self.gpu_advanced_title.opacity = 1.0 if enabled else 0.6
        self.gpu_advanced_title.update()
    
    def _build_theme_color_section(self) -> ft.Container:
        """构建主题色设置部分。
        
        Returns:
            主题色设置容器
        """
        # 分区标题
        section_title: ft.Text = ft.Text(
            "主题颜色",
            size=20,
            weight=ft.FontWeight.W_600,
        )
        
        # 预定义的主题色
        theme_colors = [
            ("#667EEA", "蓝紫色", "默认"),
            ("#6366F1", "靛蓝色", "科技感"),
            ("#8B5CF6", "紫色", "优雅"),
            ("#EC4899", "粉红色", "活力"),
            ("#F43F5E", "玫瑰红", "激情"),
            ("#EF4444", "红色", "热烈"),
            ("#F97316", "橙色", "温暖"),
            ("#F59E0B", "琥珀色", "明亮"),
            ("#10B981", "绿色", "清新"),
            ("#14B8A6", "青色", "自然"),
            ("#06B6D4", "天蓝色", "清爽"),
            ("#0EA5E9", "天空蓝", "开阔"),
            ("#6B7280", "灰色", "稳重"),
            ("#1F2937", "深灰", "专业"),
            ("#000000", "黑色", "经典"),
        ]
        
        # 获取当前主题色
        current_theme_color = self.config_service.get_config_value("theme_color", "#667EEA")
        
        # 创建主题色卡片
        self.theme_color_cards: list = []
        
        theme_cards_row: ft.Row = ft.Row(
            controls=[],
            wrap=True,
            spacing=PADDING_MEDIUM,
            run_spacing=PADDING_MEDIUM,
        )
        
        for color, name, desc in theme_colors:
            card = self._create_theme_color_card(color, name, desc, color == current_theme_color)
            self.theme_color_cards.append(card)
            theme_cards_row.controls.append(card)
        
        # 添加自定义颜色选项
        custom_color_card = self._create_custom_color_card(current_theme_color)
        self.theme_color_cards.append(custom_color_card)
        theme_cards_row.controls.append(custom_color_card)
        
        # 说明文字
        info_text: ft.Text = ft.Text(
            "主题色会立即生效，包括标题栏和所有界面元素。点击「自定义」可以使用调色盘选择任意颜色",
            size=12,
            color=ft.Colors.ON_SURFACE_VARIANT,
        )
        
        # 组装主题色设置部分
        return ft.Container(
            content=ft.Column(
                controls=[
                    section_title,
                    ft.Container(height=PADDING_MEDIUM),
                    theme_cards_row,
                    ft.Container(height=PADDING_MEDIUM // 2),
                    info_text,
                ],
                spacing=0,
            ),
            padding=PADDING_LARGE,
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=BORDER_RADIUS_MEDIUM,
        )
    
    def _create_theme_color_card(self, color: str, name: str, desc: str, is_selected: bool) -> ft.Container:
        """创建主题色选择卡片。
        
        Args:
            color: 颜色值
            name: 颜色名称
            desc: 颜色描述
            is_selected: 是否选中
        
        Returns:
            主题色卡片容器
        """
        # 颜色圆圈
        color_circle = ft.Container(
            width=40,
            height=40,
            border_radius=20,
            bgcolor=color,
            border=ft.border.all(3, ft.Colors.WHITE) if is_selected else ft.border.all(1, ft.Colors.OUTLINE),
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=8,
                color=ft.Colors.with_opacity(0.3, color),
                offset=ft.Offset(0, 2),
            ) if is_selected else None,
        )
        
        # 选中标记
        check_icon = ft.Icon(
            ft.Icons.CHECK_CIRCLE,
            size=16,
            color=color,
        ) if is_selected else None
        
        card = ft.Container(
            content=ft.Column(
                controls=[
                    color_circle,
                    ft.Container(height=4),
                    ft.Text(
                        name,
                        size=12,
                        weight=ft.FontWeight.W_600 if is_selected else ft.FontWeight.NORMAL,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        desc,
                        size=10,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    check_icon if check_icon else ft.Container(height=16),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=2,
            ),
            width=90,
            height=110,
            padding=PADDING_MEDIUM // 2,
            border_radius=BORDER_RADIUS_MEDIUM,
            bgcolor=ft.Colors.with_opacity(0.05, color) if is_selected else None,
            border=ft.border.all(
                2 if is_selected else 1,
                color if is_selected else ft.Colors.OUTLINE
            ),
            data=color,  # 存储颜色值
            on_click=self._on_theme_color_click,
            ink=True,
            animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
        )
        
        return card
    
    def _create_custom_color_card(self, current_theme_color: str) -> ft.Container:
        """创建自定义颜色卡片。
        
        Args:
            current_theme_color: 当前主题色
        
        Returns:
            自定义颜色卡片容器
        """
        card: ft.Container = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Icon(
                        ft.Icons.COLOR_LENS,
                        size=32,
                    ),
                    ft.Container(height=4),
                    ft.Text(
                        "自定义",
                        size=12,
                        weight=ft.FontWeight.W_600,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        "点击选择",
                        size=10,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=4,
            ),
            width=90,
            height=110,
            padding=PADDING_MEDIUM // 2,
            border_radius=BORDER_RADIUS_MEDIUM,
            border=ft.border.all(1, ft.Colors.OUTLINE),
            data="custom",
            on_click=self._open_color_picker,
            ink=True,
        )
        
        return card
    
    def _hex_to_rgb(self, hex_color: str) -> tuple:
        """将十六进制颜色转换为RGB值。
        
        Args:
            hex_color: 十六进制颜色值（如#667EEA）
        
        Returns:
            RGB元组 (r, g, b)
        """
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def _rgb_to_hex(self, r: int, g: int, b: int) -> str:
        """将RGB值转换为十六进制颜色。
        
        Args:
            r: 红色值 (0-255)
            g: 绿色值 (0-255)
            b: 蓝色值 (0-255)
        
        Returns:
            十六进制颜色值（如#667EEA）
        """
        return f"#{r:02x}{g:02x}{b:02x}".upper()
    
    def _open_color_picker(self, e: ft.ControlEvent) -> None:
        """打开调色盘对话框。
        
        Args:
            e: 控件事件对象
        """
        # 当前主题色
        current_color_hex = self.config_service.get_config_value("theme_color", "#667EEA")
        current_color_rgb = self._hex_to_rgb(current_color_hex)
        
        # 颜色预览框
        preview_box = ft.Container(
            width=100,
            height=100,
            bgcolor=current_color_hex,
            border_radius=12,
            border=ft.border.all(2, ft.Colors.OUTLINE),
        )
        
        # RGB文本显示
        rgb_text = ft.Text(
            f"RGB({current_color_rgb[0]}, {current_color_rgb[1]}, {current_color_rgb[2]})",
            size=14,
            weight=ft.FontWeight.W_500,
        )
        
        # 颜色代码输入框
        color_input = ft.TextField(
            label="颜色代码",
            hint_text="#667EEA",
            value=current_color_hex,
            width=200,
        )
        
        # RGB 滑块
        r_slider = ft.Slider(
            min=0,
            max=255,
            divisions=255,
            value=current_color_rgb[0],
            label="{value}",
            on_change=lambda e: self._update_color_preview_in_dialog(
                int(r_slider.value),
                int(g_slider.value),
                int(b_slider.value),
                preview_box,
                rgb_text,
                color_input
            ),
        )
        
        g_slider = ft.Slider(
            min=0,
            max=255,
            divisions=255,
            value=current_color_rgb[1],
            label="{value}",
            on_change=lambda e: self._update_color_preview_in_dialog(
                int(r_slider.value),
                int(g_slider.value),
                int(b_slider.value),
                preview_box,
                rgb_text,
                color_input
            ),
        )
        
        b_slider = ft.Slider(
            min=0,
            max=255,
            divisions=255,
            value=current_color_rgb[2],
            label="{value}",
            on_change=lambda e: self._update_color_preview_in_dialog(
                int(r_slider.value),
                int(g_slider.value),
                int(b_slider.value),
                preview_box,
                rgb_text,
                color_input
            ),
        )
        
        # 常用颜色预设
        preset_colors = [
            ("#667EEA", "蓝紫色", "默认"),
            ("#6366F1", "靛蓝色", "科技感"),
            ("#8B5CF6", "紫色", "优雅"),
            ("#EC4899", "粉红色", "活力"),
            ("#F43F5E", "玫瑰红", "激情"),
            ("#EF4444", "红色", "热烈"),
            ("#F97316", "橙色", "温暖"),
            ("#F59E0B", "琥珀色", "明亮"),
            ("#10B981", "绿色", "清新"),
            ("#14B8A6", "青色", "自然"),
            ("#06B6D4", "天蓝色", "清爽"),
            ("#0EA5E9", "天空蓝", "开阔"),
            ("#6B7280", "灰色", "稳重"),
            ("#1F2937", "深灰", "专业"),
            ("#000000", "黑色", "经典"),
            ("#FFFFFF", "白色", "纯净"),
        ]
        
        preset_buttons = []
        for hex_color, name, desc in preset_colors:
            rgb = self._hex_to_rgb(hex_color)
            preset_buttons.append(
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Container(
                                width=50,
                                height=50,
                                bgcolor=hex_color,
                                border_radius=8,
                                border=ft.border.all(2, ft.Colors.OUTLINE),
                                ink=True,
                                on_click=lambda e, c=hex_color, r=rgb[0], g=rgb[1], b=rgb[2]: self._apply_preset_color(
                                    c, r, g, b, r_slider, g_slider, b_slider, preview_box, rgb_text, color_input
                                ),
                            ),
                            ft.Text(name, size=10, text_align=ft.TextAlign.CENTER),
                        ],
                        spacing=4,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=4,
                )
            )
        
        # 颜色输入框变化事件
        def on_color_input_change(e: ft.ControlEvent):
            color_value = e.control.value.strip()
            if color_value and not color_value.startswith("#"):
                color_value = "#" + color_value
            
            # 验证颜色格式并更新
            import re
            if re.match(r'^#[0-9A-Fa-f]{6}$', color_value):
                rgb = self._hex_to_rgb(color_value)
                r_slider.value = rgb[0]
                g_slider.value = rgb[1]
                b_slider.value = rgb[2]
                r_slider.update()
                g_slider.update()
                b_slider.update()
                self._update_color_preview_in_dialog(
                    rgb[0], rgb[1], rgb[2], preview_box, rgb_text, color_input
                )
        
        color_input.on_change = on_color_input_change
        
        # 对话框内容
        dialog_content = ft.Container(
            content=ft.Column(
                controls=[
                    # 预览区域
                    ft.Row(
                        controls=[
                            preview_box,
                            ft.Column(
                                controls=[
                                    rgb_text,
                                    color_input,
                                    ft.Text("调整RGB值或输入颜色代码", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                                ],
                                spacing=PADDING_SMALL,
                            ),
                        ],
                        spacing=PADDING_LARGE,
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    ft.Divider(),
                    # RGB滑块
                    ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Text("R:", width=20, color=ft.Colors.RED),
                                    ft.Container(content=r_slider, expand=True),
                                ],
                                spacing=PADDING_SMALL,
                            ),
                            ft.Row(
                                controls=[
                                    ft.Text("G:", width=20, color=ft.Colors.GREEN),
                                    ft.Container(content=g_slider, expand=True),
                                ],
                                spacing=PADDING_SMALL,
                            ),
                            ft.Row(
                                controls=[
                                    ft.Text("B:", width=20, color=ft.Colors.BLUE),
                                    ft.Container(content=b_slider, expand=True),
                                ],
                                spacing=PADDING_SMALL,
                            ),
                        ],
                        spacing=PADDING_SMALL,
                    ),
                    ft.Divider(),
                    # 常用颜色
                    ft.Text("常用颜色:", size=12, weight=ft.FontWeight.W_500),
                    ft.Row(
                        controls=preset_buttons,
                        wrap=True,
                        spacing=PADDING_SMALL,
                        run_spacing=PADDING_SMALL,
                    ),
                ],
                spacing=PADDING_MEDIUM,
                scroll=ft.ScrollMode.AUTO,
            ),
            width=500,
            height=500,
        )
        
        # 创建对话框
        def close_dialog(apply: bool = False):
            if apply:
                color_value = color_input.value.strip()
                if color_value:
                    self._apply_custom_color(color_value)
            self.color_picker_dialog.open = False
            self.page.update()
        
        self.color_picker_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("选择自定义颜色"),
            content=dialog_content,
            actions=[
                ft.TextButton("取消", on_click=lambda e: close_dialog(False)),
                ft.ElevatedButton("应用", on_click=lambda e: close_dialog(True)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        self.page.overlay.append(self.color_picker_dialog)
        self.color_picker_dialog.open = True
        self.page.update()
    
    def _update_color_preview_in_dialog(
        self,
        r: int,
        g: int,
        b: int,
        preview_box: ft.Container,
        rgb_text: ft.Text,
        color_input: ft.TextField
    ) -> None:
        """更新对话框中的颜色预览。
        
        Args:
            r: 红色值
            g: 绿色值
            b: 蓝色值
            preview_box: 预览框容器
            rgb_text: RGB文本控件
            color_input: 颜色输入框
        """
        hex_color = self._rgb_to_hex(r, g, b)
        preview_box.bgcolor = hex_color
        rgb_text.value = f"RGB({r}, {g}, {b})"
        color_input.value = hex_color
        preview_box.update()
        rgb_text.update()
        color_input.update()
    
    def _apply_preset_color(
        self,
        hex_color: str,
        r: int,
        g: int,
        b: int,
        r_slider: ft.Slider,
        g_slider: ft.Slider,
        b_slider: ft.Slider,
        preview_box: ft.Container,
        rgb_text: ft.Text,
        color_input: ft.TextField
    ) -> None:
        """应用预设颜色。
        
        Args:
            hex_color: 十六进制颜色值
            r: 红色值
            g: 绿色值
            b: 蓝色值
            r_slider: R滑块
            g_slider: G滑块
            b_slider: B滑块
            preview_box: 预览框容器
            rgb_text: RGB文本控件
            color_input: 颜色输入框
        """
        r_slider.value = r
        g_slider.value = g
        b_slider.value = b
        r_slider.update()
        g_slider.update()
        b_slider.update()
        self._update_color_preview_in_dialog(r, g, b, preview_box, rgb_text, color_input)
    
    
    def _apply_custom_color(self, color_value: str) -> None:
        """应用自定义颜色。
        
        Args:
            color_value: 颜色值
        """
        # 确保以#开头
        if not color_value.startswith("#"):
            color_value = "#" + color_value
        
        # 验证颜色格式
        import re
        if not re.match(r'^#[0-9A-Fa-f]{6}$', color_value):
            self._show_snackbar("颜色格式错误，请使用#RRGGBB格式（如#667EEA）", ft.Colors.RED)
            return
        
        # 保存并应用颜色
        if self.config_service.set_config_value("theme_color", color_value.upper()):
            # 立即更新页面主题色
            if self.page.theme:
                self.page.theme.color_scheme_seed = color_value
            if self.page.dark_theme:
                self.page.dark_theme.color_scheme_seed = color_value
            
            # 更新标题栏颜色
            self._update_title_bar_color(color_value)
            
            # 更新所有预定义颜色卡片为未选中状态
            for card in self.theme_color_cards:
                if card.data != "custom":
                    card.border = ft.border.all(1, ft.Colors.OUTLINE)
                    card.bgcolor = None
                    
                    if card.content and isinstance(card.content, ft.Column):
                        color_circle = card.content.controls[0]
                        if isinstance(color_circle, ft.Container):
                            color_circle.border = ft.border.all(1, ft.Colors.OUTLINE)
                            color_circle.shadow = None
                        
                        name_text = card.content.controls[2]
                        if isinstance(name_text, ft.Text):
                            name_text.weight = ft.FontWeight.NORMAL
                        
                        if len(card.content.controls) > 4:
                            card.content.controls[4] = ft.Container(height=16)
                    
                    card.update()
            
            # 更新整个页面
            self.page.update()
            self._show_snackbar(f"自定义主题色已应用: {color_value}", ft.Colors.GREEN)
        else:
            self._show_snackbar("主题色更新失败", ft.Colors.RED)
    
    def _on_theme_color_click(self, e: ft.ControlEvent) -> None:
        """主题色卡片点击事件处理。
        
        Args:
            e: 控件事件对象
        """
        clicked_color: str = e.control.data
        current_color = self.config_service.get_config_value("theme_color", "#667EEA")
        
        if clicked_color == current_color:
            return  # 已选中，无需更新
        
        # 保存主题色设置
        if self.config_service.set_config_value("theme_color", clicked_color):
            # 立即更新页面主题色
            if self.page.theme:
                self.page.theme.color_scheme_seed = clicked_color
            if self.page.dark_theme:
                self.page.dark_theme.color_scheme_seed = clicked_color
            
            # 更新标题栏颜色（如果标题栏存在）
            self._update_title_bar_color(clicked_color)
            
            # 更新所有卡片的样式
            for card in self.theme_color_cards:
                # 跳过自定义颜色卡片（它的结构不同）
                if card.data == "custom":
                    continue
                
                is_selected = card.data == clicked_color
                color = card.data
                
                # 更新边框和背景
                card.border = ft.border.all(
                    2 if is_selected else 1,
                    color if is_selected else ft.Colors.OUTLINE
                )
                card.bgcolor = ft.Colors.with_opacity(0.05, color) if is_selected else None
                
                # 更新内容
                if card.content and isinstance(card.content, ft.Column):
                    # 更新颜色圆圈
                    color_circle = card.content.controls[0]
                    if isinstance(color_circle, ft.Container):
                        color_circle.border = ft.border.all(3, ft.Colors.WHITE) if is_selected else ft.border.all(1, ft.Colors.OUTLINE)
                        color_circle.shadow = ft.BoxShadow(
                            spread_radius=0,
                            blur_radius=8,
                            color=ft.Colors.with_opacity(0.3, color),
                            offset=ft.Offset(0, 2),
                        ) if is_selected else None
                    
                    # 更新名称文字粗细
                    name_text = card.content.controls[2]
                    if isinstance(name_text, ft.Text):
                        name_text.weight = ft.FontWeight.W_600 if is_selected else ft.FontWeight.NORMAL
                    
                    # 更新选中标记（只有预定义颜色卡片有这个元素）
                    if len(card.content.controls) > 4:
                        if is_selected:
                            card.content.controls[4] = ft.Icon(
                                ft.Icons.CHECK_CIRCLE,
                                size=16,
                                color=color,
                            )
                        else:
                            card.content.controls[4] = ft.Container(height=16)
                
                card.update()
            
            # 更新整个页面
            self.page.update()
            self._show_snackbar("主题色已更新", ft.Colors.GREEN)
        else:
            self._show_snackbar("主题色更新失败", ft.Colors.RED)
    
    def _update_title_bar_color(self, color: str) -> None:
        """更新标题栏颜色。
        
        Args:
            color: 新的主题色
        """
        # 尝试找到标题栏组件并更新颜色
        try:
            # 从页面的controls中查找标题栏
            for control in self.page.controls:
                if hasattr(control, 'controls'):
                    for sub_control in control.controls:
                        # 检查是否是标题栏（通过类名或属性判断）
                        if hasattr(sub_control, 'gradient'):
                            # 更新渐变色
                            sub_control.gradient = ft.LinearGradient(
                                begin=ft.alignment.center_left,
                                end=ft.alignment.center_right,
                                colors=[color, color],
                            )
                            sub_control.update()
                            break
        except Exception:
            pass  # 如果更新失败也不影响其他功能
    
    def _build_font_section(self) -> ft.Container:
        """构建字体设置部分。
        
        Returns:
            字体设置容器
        """
        # 分区标题
        section_title: ft.Text = ft.Text(
            "字体设置",
            size=20,
            weight=ft.FontWeight.W_600,
        )
        
        # 常用字体列表
        common_fonts = [
            ("System", "系统默认"),
            ("Microsoft YaHei", "微软雅黑"),
            ("SimSun", "宋体"),
            ("SimHei", "黑体"),
            ("KaiTi", "楷体"),
            ("FangSong", "仿宋"),
            ("Arial", "Arial"),
            ("Consolas", "Consolas"),
            ("Courier New", "Courier New"),
            ("Times New Roman", "Times New Roman"),
            ("Verdana", "Verdana"),
        ]
        
        # 获取当前字体
        current_font = self.config_service.get_config_value("font_family", "System")
        current_scale = self.config_service.get_config_value("font_scale", 1.0)
        
        # 字体下拉选择
        self.font_dropdown = ft.Dropdown(
            label="选择字体",
            options=[
                ft.dropdown.Option(key=font[0], text=font[1])
                for font in common_fonts
            ],
            value=current_font,
            on_change=self._on_font_change,
            width=300,
        )
        
        # 字体大小滑块
        self.font_scale_text = ft.Text(
            f"字体大小: {int(current_scale * 100)}%",
            size=14,
            weight=ft.FontWeight.W_500,
        )
        
        self.font_scale_slider = ft.Slider(
            min=80,
            max=150,
            divisions=14,
            value=current_scale * 100,
            label="{value}%",
            on_change=self._on_font_scale_change,
        )
        
        # 字体大小容器
        font_size_container = ft.Column(
            controls=[
                self.font_scale_text,
                self.font_scale_slider,
                ft.Text(
                    "80% (较小) - 100% (标准) - 150% (特大)",
                    size=11,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
            ],
            spacing=PADDING_MEDIUM // 2,
        )
        
        # 预览文本
        base_preview_size = 16
        preview_size = int(base_preview_size * current_scale)
        self.font_preview_text = ft.Text(
            "字体预览文本 Font Preview Text 0123456789",
            size=preview_size,
            font_family=current_font,
        )
        
        # 预览容器
        preview_container: ft.Container = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("预览:", size=14, weight=ft.FontWeight.W_500),
                    self.font_preview_text,
                ],
                spacing=PADDING_MEDIUM // 2,
            ),
            padding=PADDING_MEDIUM,
            border=ft.border.all(1, ft.Colors.OUTLINE),
            border_radius=BORDER_RADIUS_MEDIUM,
        )
        
        # 说明文字
        info_text: ft.Text = ft.Text(
            "更改字体和字体大小后需要重启应用才能完全生效",
            size=12,
            color=ft.Colors.ON_SURFACE_VARIANT,
        )
        
        # 组装字体设置部分
        return ft.Container(
            content=ft.Column(
                controls=[
                    section_title,
                    ft.Container(height=PADDING_MEDIUM),
                    self.font_dropdown,
                    ft.Container(height=PADDING_MEDIUM),
                    font_size_container,
                    ft.Container(height=PADDING_MEDIUM),
                    preview_container,
                    ft.Container(height=PADDING_MEDIUM // 2),
                    info_text,
                ],
                spacing=0,
            ),
            padding=PADDING_LARGE,
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=BORDER_RADIUS_MEDIUM,
        )
    
    def _build_about_section(self) -> ft.Container:
        """构建关于部分。
        
        Returns:
            关于部分容器
        """
        section_title: ft.Text = ft.Text(
            "关于",
            size=20,
            weight=ft.FontWeight.W_600,
        )
        import webbrowser
        app_info: ft.Column = ft.Column(
            controls=[
                ft.Text("MyTools - 多功能工具箱", size=16, weight=ft.FontWeight.W_500),
                ft.Text("版本: 0.1.0", size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                ft.Text("By：一铭"),
                ft.Text("QQ交流群：1029212047"),
                ft.Container(height=PADDING_MEDIUM // 2),
                ft.Text(
                    "一个集成了图片处理、音视频处理、编码转换、代码格式化等功能的桌面应用",
                    size=14,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
                # 点击访问软件发布页，用浏览器打开
                ft.TextButton(
                    "软件发布页",
                    on_click=lambda e: webbrowser.open("https://openlist.wer.plus/MyTools"),
                    icon=ft.Icons.LINK,
                    tooltip="软件发布页",
                ),
                ft.TextButton(
                    "GIthub",
                    on_click=lambda e: webbrowser.open("https://github.com/HG-ha"),
                    icon=ft.Icons.LINK,
                    tooltip="Github",
                ),
            ],
            spacing=PADDING_MEDIUM // 2,
        )
        
        # 重置窗口按钮
        reset_window_button: ft.OutlinedButton = ft.OutlinedButton(
            text="重置窗口位置和大小",
            icon=ft.Icons.RESTORE,
            on_click=self._on_reset_window_position,
            tooltip="将窗口位置和大小重置为默认值",
        )
        
        return ft.Container(
            content=ft.Column(
                controls=[
                    section_title,
                    ft.Container(height=PADDING_MEDIUM),
                    app_info,
                    ft.Container(height=PADDING_MEDIUM),
                    reset_window_button,
                ],
                spacing=0,
            ),
            padding=PADDING_LARGE,
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=BORDER_RADIUS_MEDIUM,
        )
    
    def _on_dir_type_change(self, e: ft.ControlEvent) -> None:
        """目录类型切换事件处理。
        
        Args:
            e: 控件事件对象
        """
        is_custom: bool = e.control.value == "custom"
        self.browse_button.disabled = not is_custom
        self.browse_button.update()
        
        if not is_custom:
            # 切换到默认目录
            if self.config_service.reset_to_default_dir():
                self.data_dir_text.value = str(self.config_service.get_data_dir())
                self.data_dir_text.update()
                self._show_snackbar("已切换到默认数据目录", ft.Colors.GREEN)
            else:
                self._show_snackbar("切换失败", ft.Colors.RED)
    
    def _on_browse_click(self, e: ft.ControlEvent) -> None:
        """浏览按钮点击事件处理。
        
        Args:
            e: 控件事件对象
        """
        # 创建文件选择器
        def on_result(result: ft.FilePickerResultEvent) -> None:
            if result.path:
                if self.config_service.set_data_dir(result.path, is_custom=True):
                    self.data_dir_text.value = result.path
                    self.data_dir_text.update()
                    self._show_snackbar("数据目录已更新", ft.Colors.GREEN)
                else:
                    self._show_snackbar("更新数据目录失败", ft.Colors.RED)
        
        picker: ft.FilePicker = ft.FilePicker(on_result=on_result)
        self.page.overlay.append(picker)
        self.page.update()
        picker.get_directory_path(dialog_title="选择数据存储目录")
    
    def _on_open_dir_click(self, e: ft.ControlEvent) -> None:
        """打开目录按钮点击事件处理。
        
        Args:
            e: 控件事件对象
        """
        import subprocess
        import platform
        
        data_dir: Path = self.config_service.get_data_dir()
        
        try:
            system: str = platform.system()
            if system == "Windows":
                subprocess.run(["explorer", str(data_dir)])
            elif system == "Darwin":
                subprocess.run(["open", str(data_dir)])
            else:
                subprocess.run(["xdg-open", str(data_dir)])
        except Exception as ex:
            self._show_snackbar(f"打开目录失败: {ex}", ft.Colors.RED)
    
    def _on_font_change(self, e: ft.ControlEvent) -> None:
        """字体更改事件处理。
        
        Args:
            e: 控件事件对象
        """
        selected_font = e.control.value
        
        # 保存字体设置
        if self.config_service.set_config_value("font_family", selected_font):
            # 更新预览文本字体
            self.font_preview_text.font_family = selected_font
            self.font_preview_text.update()
            
            # 尝试更新页面字体（部分生效）
            if self.page.theme:
                self.page.theme.font_family = selected_font
            if self.page.dark_theme:
                self.page.dark_theme.font_family = selected_font
            self.page.update()
            
            self._show_snackbar("字体已更新，重启应用后完全生效", ft.Colors.GREEN)
        else:
            self._show_snackbar("字体更新失败", ft.Colors.RED)
    
    def _on_font_scale_change(self, e: ft.ControlEvent) -> None:
        """字体大小更改事件处理。
        
        Args:
            e: 控件事件对象
        """
        scale_percent = int(e.control.value)
        scale = scale_percent / 100.0
        
        # 更新文本显示
        self.font_scale_text.value = f"字体大小: {scale_percent}%"
        self.font_scale_text.update()
        
        # 保存字体大小设置
        if self.config_service.set_config_value("font_scale", scale):
            # 更新预览文本大小
            base_size = 16
            new_size = int(base_size * scale)
            self.font_preview_text.size = new_size
            self.font_preview_text.update()
            
            self._show_snackbar(f"字体大小已设置为 {scale_percent}%，重启应用后完全生效", ft.Colors.GREEN)
        else:
            self._show_snackbar("字体大小更新失败", ft.Colors.RED)
    
    def _on_reset_window_position(self, e: ft.ControlEvent) -> None:
        """重置窗口位置和大小事件处理。
        
        Args:
            e: 控件事件对象
        """
        from constants import WINDOW_WIDTH, WINDOW_HEIGHT
        
        # 清除保存的窗口位置和大小
        self.config_service.set_config_value("window_left", None)
        self.config_service.set_config_value("window_top", None)
        self.config_service.set_config_value("window_width", None)
        self.config_service.set_config_value("window_height", None)
        
        # 重置窗口大小为默认值
        self.page.window.width = WINDOW_WIDTH
        self.page.window.height = WINDOW_HEIGHT
        
        # 将窗口移动到屏幕中央
        self.page.window.center()
        self.page.update()
        
        self._show_snackbar("窗口位置和大小已重置为默认值", ft.Colors.GREEN)
    
    def _show_snackbar(self, message: str, color: str) -> None:
        """显示提示消息。
        
        Args:
            message: 消息内容
            color: 消息颜色
        """
        try:
            snackbar: ft.SnackBar = ft.SnackBar(
                content=ft.Text(message),
                bgcolor=color,
                duration=2000,
            )
            # 使用保存的页面引用作为回退（有时候 self.page 在后台线程中为 None）
            page = getattr(self, '_saved_page', None) or getattr(self, 'page', None)
            if not page:
                return
            # 将 snackbar 添加到 overlay 并刷新页面
            try:
                page.overlay.append(snackbar)
                snackbar.open = True
                page.update()
            except Exception:
                # 如果 overlay 不可用或在后台线程中引发错误，则尝试安全地设置一个简单替代：
                # 将消息打印到控制台（避免抛出未捕获异常）
                print(f"Snackbar show failed: {message}")
        except Exception:
            # 最后兜底，避免线程未捕获异常终止程序
            try:
                print(f"_show_snackbar error: {message}")
            except Exception:
                pass

