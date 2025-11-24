# -*- coding: utf-8 -*-
"""主视图模块。

提供应用的主界面，包含导航栏和各功能视图的切换。
"""

from typing import Optional

import flet as ft

from components import CustomTitleBar, ToolInfo, ToolSearchDialog
from services import ConfigService, EncodingService, ImageService, FFmpegService
from tool_registry import register_all_tools
from utils import get_all_tools
from views.media import AudioView, VideoView
from views.dev_tools import DevToolsView
from views.image import ImageView
from views.settings_view import SettingsView


class MainView(ft.Column):
    """主视图类。
    
    提供应用的主界面布局，包含：
    - 自定义标题栏
    - 侧边导航栏
    - 内容区域
    - 功能视图切换
    """

    def __init__(self, page: ft.Page) -> None:
        """初始化主视图。
        
        Args:
            page: Flet页面对象
        """
        super().__init__()
        self.page: ft.Page = page
        self.expand: bool = True
        self.spacing: int = 0
        
        # 创建服务
        self.config_service: ConfigService = ConfigService()
        self.image_service: ImageService = ImageService()
        self.encoding_service: EncodingService = EncodingService()
        self.ffmpeg_service: FFmpegService = FFmpegService(self.config_service)
        
        # 创建自定义标题栏（传递配置服务以保存窗口状态）
        self.title_bar: CustomTitleBar = CustomTitleBar(page, self.config_service)
        
        # 创建内容容器（稍后创建视图时需要）
        self.content_container: Optional[ft.Container] = None
        
        # 创建各功能视图
        self.image_view: Optional[ImageView] = None
        self.dev_tools_view: Optional[DevToolsView] = None
        self.audio_view: Optional[AudioView] = None
        self.video_view: VideoView = VideoView(page, self.config_service, self.ffmpeg_service)
        self.settings_view: SettingsView = SettingsView(page, self.config_service)
        
        # 创建UI组件
        self._build_ui()
    
    def _build_ui(self) -> None:
        """构建用户界面。"""
        # 创建导航栏
        self.navigation_rail: ft.NavigationRail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=100,
            min_extended_width=200,
            group_alignment=-0.9,
            expand=True,
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.Icons.IMAGE_OUTLINED,
                    selected_icon=ft.Icons.IMAGE_ROUNDED,
                    label="图片处理",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.AUDIOTRACK_OUTLINED,
                    selected_icon=ft.Icons.AUDIOTRACK_ROUNDED,
                    label="音频处理",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.VIDEO_LIBRARY_OUTLINED,
                    selected_icon=ft.Icons.VIDEO_LIBRARY_ROUNDED,
                    label="视频处理",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.DEVELOPER_MODE_OUTLINED,
                    selected_icon=ft.Icons.DEVELOPER_MODE_ROUNDED,
                    label="开发工具",
                ),
            ],
            on_change=self._on_navigation_change,
        )
        
        # 设置按钮（放在导航栏底部）
        settings_button: ft.Container = ft.Container(
            content=ft.IconButton(
                icon=ft.Icons.SETTINGS_OUTLINED,
                icon_size=24,
                tooltip="设置",
                on_click=self._open_settings,
            ),
            alignment=ft.alignment.center,
            padding=ft.padding.symmetric(vertical=16),
            width=100,  # 与导航栏宽度一致
        )
        
        # 导航栏区域（导航栏 + 设置按钮）
        navigation_column: ft.Column = ft.Column(
            controls=[
                self.navigation_rail,
                settings_button,
            ],
            spacing=0,
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            expand=True,
        )
        
        # 导航栏容器（添加阴影效果）
        self.navigation_container: ft.Container = ft.Container(
            content=navigation_column,
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=10,
                color=ft.Colors.with_opacity(0.05, ft.Colors.BLACK),
                offset=ft.Offset(2, 0),
            ),
        )
        
        # 创建内容容器（先创建占位容器）
        self.content_container = ft.Container(
            expand=True,
            alignment=ft.alignment.top_left,  # 内容从左上角开始
            width=float('inf'),  # 占满可用宽度
            height=float('inf'),  # 占满可用高度
        )
        
        # 创建图片视图、音频视图和开发工具视图，并传递容器引用
        self.image_view = ImageView(self.page, self.config_service, self.image_service, self.content_container)
        self.audio_view = AudioView(self.page, self.config_service, self.content_container)
        self.dev_tools_view = DevToolsView(self.page, self.config_service, self.encoding_service, self.content_container)
        
        # 设置初始内容
        self.content_container.content = self.image_view
        
        # 注册所有工具（自动注册）
        register_all_tools()
        
        # 注册键盘快捷键
        self.page.on_keyboard_event = self._on_keyboard
        
        # 主内容区域（导航栏 + 内容）
        main_content: ft.Row = ft.Row(
            controls=[
                self.navigation_container,
                self.content_container,
            ],
            spacing=0,
            expand=True,
        )
        
        # 创建悬浮搜索按钮
        self.fab_search = ft.FloatingActionButton(
            icon=ft.Icons.SEARCH,
            tooltip="搜索工具 (Ctrl+K)",
            on_click=self._open_search,
            bgcolor=ft.Colors.PRIMARY,
            foreground_color=ft.Colors.ON_PRIMARY,
        )
        
        # 组装主视图（标题栏 + 主内容）
        self.controls = [
            self.title_bar,
            main_content,
        ]
        
        # 注意：FAB需要添加到 page.overlay 或 page.floating_action_button
        # 我们将在初始化完成后添加
        self.page.floating_action_button = self.fab_search
    
    def _on_navigation_change(self, e: ft.ControlEvent) -> None:
        """导航变更事件处理。
        
        Args:
            e: 控件事件对象
        """
        selected_index: int = e.control.selected_index
        
        # 根据选中的索引切换视图
        if selected_index == 0:
            view = self.image_view
            # 尝试恢复图片处理页面的状态（如果之前在子视图中）
            restored = False
            if hasattr(view, 'restore_state'):
                restored = view.restore_state()
            
            # 如果没有恢复子视图，则显示主视图
            if not restored:
                self.content_container.content = view
                self.content_container.update()
        elif selected_index == 1:
            view = self.audio_view
            # 尝试恢复音频处理页面的状态
            restored = False
            if hasattr(view, 'restore_state'):
                restored = view.restore_state()
            
            if not restored:
                self.content_container.content = view
                self.content_container.update()
        elif selected_index == 2:
            view = self.video_view
            self.content_container.content = view
            self.content_container.update()
        elif selected_index == 3:
            view = self.dev_tools_view
            # 尝试恢复开发工具页面的状态
            restored = False
            if hasattr(view, 'restore_state'):
                restored = view.restore_state()
            
            if not restored:
                self.content_container.content = view
                self.content_container.update()
        else:
            return
    
    def _open_tool_by_id(self, tool_id: str) -> None:
        """根据工具ID打开工具。
        
        Args:
            tool_id: 工具ID，格式如 "image.compress", "audio.format"
        """
        # 解析工具ID
        parts = tool_id.split(".")
        if len(parts) < 2:
            return
        
        category = parts[0]
        tool_name = ".".join(parts[1:])  # 支持多级，如 "puzzle.merge"
        
        # 先切换到对应的分类
        if category == "image":
            self.navigation_rail.selected_index = 0
            self.content_container.content = self.image_view
            # 调用图片视图的方法打开子工具
            if hasattr(self.image_view, 'open_tool'):
                self.image_view.open_tool(tool_name)
        elif category == "audio":
            self.navigation_rail.selected_index = 1
            self.content_container.content = self.audio_view
            if hasattr(self.audio_view, 'open_tool'):
                self.audio_view.open_tool(tool_name)
        elif category == "video":
            self.navigation_rail.selected_index = 2
            self.content_container.content = self.video_view
            # 视频视图使用 _open_view 方法
            self.video_view._open_view(tool_name)
        elif category == "dev":
            self.navigation_rail.selected_index = 3
            self.content_container.content = self.dev_tools_view
            if hasattr(self.dev_tools_view, 'open_tool'):
                self.dev_tools_view.open_tool(tool_name)
        
        self.navigation_rail.update()
        self.content_container.update()
    
    def _open_search(self, e: ft.ControlEvent = None) -> None:
        """打开搜索对话框。"""
        # 从全局注册表获取工具并转换为ToolInfo
        tools_metadata = get_all_tools()
        tools = []
        for metadata in tools_metadata:
            # 获取图标对象
            icon = getattr(ft.Icons, metadata.icon, ft.Icons.HELP_OUTLINE)
            
            tool_info = ToolInfo(
                name=metadata.name,
                description=metadata.description,
                category=metadata.category,
                keywords=metadata.keywords,
                icon=icon,
                on_click=lambda tid=metadata.tool_id: self._open_tool_by_id(tid),
            )
            tools.append(tool_info)
        
        search_dialog = ToolSearchDialog(self.page, tools)
        self.page.overlay.append(search_dialog)
        search_dialog.open = True
        self.page.update()
    
    def _on_keyboard(self, e: ft.KeyboardEvent) -> None:
        """键盘事件处理。"""
        # Ctrl+K 打开搜索
        if e.key == "K" and e.ctrl and not e.shift and not e.alt:
            self._open_search()
    
    def _open_settings(self, e: ft.ControlEvent) -> None:
        """打开设置视图。
        
        Args:
            e: 控件事件对象
        """
        # 取消导航栏的选中状态
        self.navigation_rail.selected_index = None
        self.navigation_rail.update()
        
        # 切换到设置视图
        self.content_container.content = self.settings_view
        self.content_container.update()
