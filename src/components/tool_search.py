# -*- coding: utf-8 -*-
"""工具搜索组件。

提供全局工具搜索功能。
"""

from dataclasses import dataclass
from typing import Callable, List, Optional

import flet as ft

from constants import (
    BORDER_RADIUS_MEDIUM,
    PADDING_MEDIUM,
    PADDING_SMALL,
)


@dataclass
class ToolInfo:
    """工具信息类。"""
    name: str  # 工具名称
    description: str  # 工具描述
    category: str  # 分类（图片处理、音频处理、视频处理、开发工具）
    keywords: List[str]  # 关键词（用于搜索）
    icon: str  # 图标
    on_click: Callable  # 点击回调


class ToolSearchDialog(ft.AlertDialog):
    """工具搜索对话框类。"""

    def __init__(
        self,
        page: ft.Page,
        tools: List[ToolInfo],
    ) -> None:
        """初始化工具搜索对话框。
        
        Args:
            page: Flet页面对象
            tools: 工具列表
        """
        self.page = page
        self.tools = tools
        self.filtered_tools = tools.copy()
        
        # 搜索框
        self.search_field = ft.TextField(
            hint_text="搜索工具... (输入工具名称或关键词)",
            prefix_icon=ft.Icons.SEARCH,
            autofocus=True,
            on_change=self._on_search_change,
            border_radius=BORDER_RADIUS_MEDIUM,
        )
        
        # 结果列表
        self.results_list = ft.ListView(
            spacing=PADDING_SMALL,
            height=400,
            expand=True,
        )
        
        # 初始化对话框（不在这里调用 update）
        super().__init__(
            modal=True,
            title=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.SEARCH, size=28),
                    ft.Text("搜索工具", size=20, weight=ft.FontWeight.W_600),
                ],
                spacing=PADDING_SMALL,
            ),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        self.search_field,
                        ft.Divider(),
                        self.results_list,
                    ],
                    spacing=PADDING_MEDIUM,
                    tight=True,
                ),
                width=600,
                height=500,
            ),
            actions=[
                ft.TextButton("关闭", on_click=self._on_close),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            on_dismiss=lambda e: None,  # 添加关闭回调
        )
        
        # 在对话框初始化后更新结果（此时controls已经创建但还未添加到页面）
        self._populate_initial_results()
    
    def _on_search_change(self, e: ft.ControlEvent) -> None:
        """搜索文本改变事件。"""
        query = e.control.value.lower().strip()
        
        if not query:
            self.filtered_tools = self.tools.copy()
        else:
            self.filtered_tools = []
            for tool in self.tools:
                # 搜索工具名称、描述和关键词
                if (query in tool.name.lower() or
                    query in tool.description.lower() or
                    any(query in kw.lower() for kw in tool.keywords)):
                    self.filtered_tools.append(tool)
        
        self._update_results()
    
    def _populate_initial_results(self) -> None:
        """填充初始结果（不调用update）。"""
        self._build_results()
    
    def _update_results(self) -> None:
        """更新搜索结果显示。"""
        self.results_list.controls.clear()
        self._build_results()
        self.results_list.update()
    
    def _build_results(self) -> None:
        """构建结果列表。"""
        
        if not self.filtered_tools:
            # 无结果
            self.results_list.controls.append(
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Icon(ft.Icons.SEARCH_OFF, size=64, color=ft.Colors.ON_SURFACE_VARIANT),
                            ft.Text(
                                "未找到匹配的工具",
                                size=16,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                            ),
                            ft.Text(
                                "试试其他关键词",
                                size=12,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=PADDING_SMALL,
                    ),
                    alignment=ft.alignment.center,
                    expand=True,
                )
            )
        else:
            # 按分类分组显示
            categories = {}
            for tool in self.filtered_tools:
                if tool.category not in categories:
                    categories[tool.category] = []
                categories[tool.category].append(tool)
            
            for category, tools in categories.items():
                # 分类标题
                self.results_list.controls.append(
                    ft.Container(
                        content=ft.Text(
                            category,
                            size=14,
                            weight=ft.FontWeight.W_600,
                            color=ft.Colors.PRIMARY,
                        ),
                        padding=ft.padding.only(top=PADDING_SMALL, bottom=PADDING_SMALL // 2),
                    )
                )
                
                # 工具项
                for tool in tools:
                    self.results_list.controls.append(
                        self._create_tool_item(tool)
                    )
    
    def _create_tool_item(self, tool: ToolInfo) -> ft.Container:
        """创建工具项。"""
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(tool.icon, size=24),
                    ft.Column(
                        controls=[
                            ft.Text(
                                tool.name,
                                size=14,
                                weight=ft.FontWeight.W_500,
                            ),
                            ft.Text(
                                tool.description,
                                size=12,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                            ),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    ft.Icon(ft.Icons.ARROW_FORWARD_IOS, size=16, color=ft.Colors.ON_SURFACE_VARIANT),
                ],
                spacing=PADDING_MEDIUM,
            ),
            padding=PADDING_MEDIUM,
            border=ft.border.all(1, ft.Colors.OUTLINE),
            border_radius=BORDER_RADIUS_MEDIUM,
            ink=True,
            on_click=lambda e, t=tool: self._on_tool_click(t),
        )
    
    def _on_tool_click(self, tool: ToolInfo) -> None:
        """工具项点击事件。"""
        # 关闭对话框
        self.open = False
        self.page.update()
        
        # 执行工具回调
        if tool.on_click:
            tool.on_click()
    
    def _on_close(self, e: ft.ControlEvent) -> None:
        """关闭按钮点击事件。"""
        self.open = False
        self.page.update()


class ToolRegistry:
    """工具注册表类。
    
    用于管理所有可搜索的工具。
    """
    
    def __init__(self):
        """初始化工具注册表。"""
        self.tools: List[ToolInfo] = []
    
    def register(
        self,
        name: str,
        description: str,
        category: str,
        keywords: List[str],
        icon: str,
        on_click: Callable,
    ) -> None:
        """注册工具。
        
        Args:
            name: 工具名称
            description: 工具描述
            category: 分类
            keywords: 关键词列表
            icon: 图标
            on_click: 点击回调
        """
        tool = ToolInfo(
            name=name,
            description=description,
            category=category,
            keywords=keywords,
            icon=icon,
            on_click=on_click,
        )
        self.tools.append(tool)
    
    def get_tools(self) -> List[ToolInfo]:
        """获取所有工具。"""
        return self.tools.copy()
    
    def clear(self) -> None:
        """清空注册表。"""
        self.tools.clear()

