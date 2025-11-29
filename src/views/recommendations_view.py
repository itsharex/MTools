# -*- coding: utf-8 -*-
"""推荐视图模块。

基于用户使用历史智能推荐工具。
"""

from typing import Optional

import flet as ft

from components import FeatureCard
from constants import (
    PADDING_LARGE,
    PADDING_MEDIUM,
    PADDING_SMALL,
    BORDER_RADIUS_MEDIUM,
)
from services import ConfigService
from utils import get_all_tools, get_tool


class RecommendationsView(ft.Container):
    """推荐视图类。
    
    基于用户使用历史智能推荐工具，包括：
    - 根据使用频率推荐
    - 智能推荐常用工具
    """

    def __init__(
        self,
        page: ft.Page,
        config_service: Optional[ConfigService] = None,
        on_tool_click: Optional[callable] = None,
    ) -> None:
        """初始化推荐视图。
        
        Args:
            page: Flet页面对象
            config_service: 配置服务实例
            on_tool_click: 工具点击回调
        """
        super().__init__()
        self.page: ft.Page = page
        self.config_service: ConfigService = config_service if config_service else ConfigService()
        self.on_tool_click_handler: Optional[callable] = on_tool_click
        
        self.expand: bool = True
        self.padding: ft.padding = ft.padding.only(
            left=PADDING_MEDIUM,
            right=PADDING_MEDIUM,
            top=PADDING_MEDIUM,
            bottom=PADDING_MEDIUM
        )
        
        # 创建UI组件
        self._build_ui()
    
    def _build_ui(self) -> None:
        """构建用户界面。"""
        # 获取使用历史
        tool_usage_count = self.config_service.get_config_value("tool_usage_count", {})
        
        # 标题
        title_row = ft.Row(
            controls=[
                ft.Icon(ft.Icons.LIGHTBULB, size=32, color=ft.Colors.AMBER),
                ft.Text("推荐工具", size=28, weight=ft.FontWeight.BOLD),
            ],
            spacing=PADDING_MEDIUM,
        )
        
        # 推荐的工具卡片区域
        recommended_cards_container = ft.Container()
        
        if tool_usage_count:
            # 有使用历史，显示基于历史的推荐
            # 获取最常用的8个工具
            sorted_tools = sorted(tool_usage_count.items(), key=lambda x: x[1], reverse=True)
            recommended_tool_names = [name for name, count in sorted_tools[:8]]
            
            # 根据工具名称找到对应的tool_id
            all_tools_meta = get_all_tools()
            recommended_tool_ids = []
            for tool_meta in all_tools_meta:
                if tool_meta.name in recommended_tool_names:
                    recommended_tool_ids.append(tool_meta.tool_id)
            
            recommended_cards = self._build_tool_cards(recommended_tool_ids)
            
            recommended_cards_container.content = ft.Column(
                controls=[
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.Icon(ft.Icons.TRENDING_UP, size=20, color=ft.Colors.AMBER),
                                        ft.Text("根据使用历史为您推荐", size=18, weight=ft.FontWeight.W_600),
                                    ],
                                    spacing=PADDING_SMALL,
                                ),
                                ft.Text(
                                    "这些是您最常使用的工具",
                                    size=13,
                                    color=ft.Colors.ON_SURFACE_VARIANT,
                                ),
                            ],
                            spacing=PADDING_SMALL // 2,
                        ),
                        padding=PADDING_MEDIUM,
                        border=ft.border.all(1, ft.Colors.AMBER_200),
                        border_radius=BORDER_RADIUS_MEDIUM,
                        bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.AMBER),
                    ),
                    ft.Container(height=PADDING_MEDIUM),
                    ft.Row(
                        controls=recommended_cards if recommended_cards else [
                            ft.Text("暂无推荐", color=ft.Colors.ON_SURFACE_VARIANT)
                        ],
                        wrap=True,
                        spacing=PADDING_LARGE,
                        run_spacing=PADDING_LARGE,
                        alignment=ft.MainAxisAlignment.START,
                    ),
                ],
                spacing=0,
            )
        else:
            # 没有使用历史，显示智能推荐
            # 推荐一些常用工具
            smart_recommended = [
                "image.compress",    # 图片压缩
                "video.compress",    # 视频压缩
                "video.format",      # 视频格式转换
                "audio.format",      # 音频格式转换
                "dev.json_viewer",   # JSON查看器
                "dev.encoding",      # 编码转换
                "image.format",      # 图片格式转换
                "video.speed",       # 视频倍速
            ]
            
            smart_cards = self._build_tool_cards(smart_recommended)
            
            recommended_cards_container.content = ft.Column(
                controls=[
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.Icon(ft.Icons.TIPS_AND_UPDATES, size=24, color=ft.Colors.BLUE),
                                        ft.Text("为您推荐", size=18, weight=ft.FontWeight.W_600),
                                    ],
                                    spacing=PADDING_SMALL,
                                ),
                                ft.Text(
                                    "这些是最常用的工具，快来试试吧！",
                                    size=13,
                                    color=ft.Colors.ON_SURFACE_VARIANT,
                                ),
                            ],
                            spacing=PADDING_SMALL // 2,
                        ),
                        padding=PADDING_MEDIUM,
                        border=ft.border.all(1, ft.Colors.BLUE_200),
                        border_radius=BORDER_RADIUS_MEDIUM,
                        bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.BLUE),
                    ),
                    ft.Container(height=PADDING_MEDIUM),
                    ft.Row(
                        controls=smart_cards if smart_cards else [],
                        wrap=True,
                        spacing=PADDING_LARGE,
                        run_spacing=PADDING_LARGE,
                        alignment=ft.MainAxisAlignment.START,
                    ),
                ],
                spacing=0,
            )
        
        # 提示信息
        tip_card = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.INFO_OUTLINE, size=18, color=ft.Colors.BLUE),
                    ft.Text(
                        "💡 提示：使用工具后，系统会自动学习您的使用习惯，为您提供更精准的推荐",
                        size=13,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                ],
                spacing=PADDING_SMALL,
            ),
            padding=PADDING_MEDIUM,
            border=ft.border.all(1, ft.Colors.BLUE_200),
            border_radius=BORDER_RADIUS_MEDIUM,
            bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.BLUE),
            margin=ft.margin.only(top=PADDING_LARGE),
        )
        
        # 组装内容
        self.content = ft.Column(
            controls=[
                title_row,
                ft.Divider(),
                recommended_cards_container,
                tip_card,
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            spacing=PADDING_MEDIUM,
        )
    
    def _build_tool_cards(self, tool_ids: list) -> list:
        """构建工具卡片列表。
        
        Args:
            tool_ids: 工具ID列表
        
        Returns:
            工具卡片列表
        """
        cards = []
        for tool_id in tool_ids:
            tool_meta = get_tool(tool_id)
            if not tool_meta:
                continue
            
            # 获取图标
            icon = getattr(ft.Icons, tool_meta.icon, ft.Icons.HELP_OUTLINE)
            
            # 创建卡片（需要从分类获取渐变色）
            gradient_colors = self._get_gradient_for_category(tool_meta.category)
            
            card = FeatureCard(
                icon=icon,
                title=tool_meta.name,
                description=tool_meta.description,
                on_click=lambda e, tid=tool_id: self._on_tool_click(tid),
                gradient_colors=gradient_colors,
            )
            
            cards.append(card)
        
        return cards
    
    def _get_gradient_for_category(self, category: str) -> tuple:
        """根据分类获取渐变色。"""
        gradient_map = {
            "图片处理": ("#a8edea", "#fed6e3"),
            "媒体处理": ("#84fab0", "#8fd3f4"),
            "开发工具": ("#fbc2eb", "#a6c1ee"),
            "其他工具": ("#ffecd2", "#fcb69f"),
        }
        return gradient_map.get(category, ("#e0e0e0", "#f5f5f5"))
    
    def _on_tool_click(self, tool_id: str) -> None:
        """工具点击事件。"""
        if self.on_tool_click_handler:
            self.on_tool_click_handler(tool_id)
    
    def refresh(self) -> None:
        """刷新界面。"""
        self._build_ui()
        if self.page:
            self.page.update()

