# -*- coding: utf-8 -*-
"""文本对比工具视图模块。

提供文本差异对比功能，高亮显示差异。
"""

import difflib
from typing import Callable, Optional, List

import flet as ft

from constants import PADDING_MEDIUM, PADDING_SMALL


class TextDiffView(ft.Container):
    """文本对比工具视图类。"""
    
    def __init__(
        self,
        page: ft.Page,
        on_back: Optional[Callable] = None
    ):
        super().__init__()
        self.page = page
        self.on_back = on_back
        self.expand = True
        self.padding = ft.padding.only(
            left=PADDING_MEDIUM,
            right=PADDING_MEDIUM,
            top=PADDING_MEDIUM,
            bottom=PADDING_MEDIUM
        )
        
        # 控件引用
        self.text1 = ft.Ref[ft.TextField]()
        self.text2 = ft.Ref[ft.TextField]()
        self.ignore_whitespace = ft.Ref[ft.Checkbox]()
        self.ignore_case = ft.Ref[ft.Checkbox]()
        self.diff_list_left = ft.Ref[ft.ListView]()
        self.diff_list_right = ft.Ref[ft.ListView]()
        self.stats_text = ft.Ref[ft.Text]()
        
        # 输入/结果视图切换
        self.input_container = ft.Ref[ft.Container]()
        self.result_container = ft.Ref[ft.Container]()
        
        # 布局引用（拖动调整）
        self.left_panel_ref = ft.Ref[ft.Container]()
        self.right_panel_ref = ft.Ref[ft.Container]()
        self.divider_ref = ft.Ref[ft.Container]()
        self.ratio = 0.5
        self.left_flex = 500
        self.right_flex = 500
        self.is_dragging = False
        
        # 滚动同步
        self._syncing_scroll = False
        self._left_max_extent = 0.0
        self._right_max_extent = 0.0
        
        self._build_ui()
    
    def _build_ui(self):
        # 标题栏
        header = ft.Row(
            controls=[
                ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    tooltip="返回",
                    on_click=lambda _: self._on_back_click(),
                ),
                ft.Text("文本对比工具", size=28, weight=ft.FontWeight.BOLD),
                ft.Container(expand=True),
                ft.IconButton(
                    icon=ft.Icons.HELP_OUTLINE,
                    tooltip="使用说明",
                    on_click=self._show_help,
                ),
            ],
            spacing=PADDING_MEDIUM,
        )
        
        # 操作栏
        operation_bar = ft.Row(
            controls=[
                ft.Checkbox(
                    ref=self.ignore_whitespace,
                    label="忽略空格",
                    value=False,
                ),
                ft.Checkbox(
                    ref=self.ignore_case,
                    label="忽略大小写",
                    value=False,
                ),
                ft.Text(
                    ref=self.stats_text,
                    value="",
                    size=13,
                    color=ft.Colors.OUTLINE,
                ),
                ft.Container(expand=True),
                ft.ElevatedButton(
                    text="开始对比",
                    icon=ft.Icons.COMPARE_ARROWS,
                    on_click=self._compare,
                ),
                ft.OutlinedButton(
                    text="返回编辑",
                    icon=ft.Icons.EDIT,
                    on_click=self._back_to_input,
                    visible=False,
                ),
                ft.OutlinedButton(
                    text="清空",
                    icon=ft.Icons.CLEAR,
                    on_click=self._clear,
                ),
            ],
            spacing=PADDING_SMALL,
        )
        
        # 输入区域
        input_section = self._build_input_section()
        
        # 结果区域（并排对比视图）
        result_section = self._build_result_section()
        
        # 输入容器（初始显示）
        input_container = ft.Container(
            ref=self.input_container,
            content=input_section,
            visible=True,
            expand=True,
        )
        
        # 结果容器（初始隐藏）
        result_container = ft.Container(
            ref=self.result_container,
            content=result_section,
            visible=False,
            expand=True,
        )
        
        # 主内容区域（使用 Stack 叠加两个容器）
        content_stack = ft.Stack(
            controls=[
                input_container,
                result_container,
            ],
            expand=True,
        )
        
        self.content = ft.Column(
            controls=[
                header,
                ft.Divider(),
                ft.Container(height=PADDING_SMALL),
                operation_bar,
                ft.Container(height=PADDING_SMALL),
                content_stack,
            ],
            spacing=0,
            expand=True,
        )
    
    def _build_input_section(self) -> ft.Row:
        """构建输入区域。"""
        # 左侧文本输入
        text1_section = ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text("文本 1", weight=ft.FontWeight.BOLD, size=16),
                        ft.Container(expand=True),
                        ft.IconButton(
                            icon=ft.Icons.CONTENT_PASTE,
                            tooltip="粘贴",
                            icon_size=16,
                            on_click=lambda _: self._paste_text(self.text1),
                        ),
                    ],
                ),
                ft.Container(
                    content=ft.TextField(
                        ref=self.text1,
                        multiline=True,
                        min_lines=25,
                        hint_text="输入第一个文本...",
                        text_size=13,
                        border=ft.InputBorder.NONE,
                        text_style=ft.TextStyle(font_family="Consolas,Monospace"),
                    ),
                    border=ft.border.all(1, ft.Colors.OUTLINE),
                    border_radius=8,
                    padding=PADDING_SMALL,
                    expand=True,
                ),
            ],
            spacing=5,
            expand=True,
        )
        
        # 右侧文本输入
        text2_section = ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text("文本 2", weight=ft.FontWeight.BOLD, size=16),
                        ft.Container(expand=True),
                        ft.IconButton(
                            icon=ft.Icons.CONTENT_PASTE,
                            tooltip="粘贴",
                            icon_size=16,
                            on_click=lambda _: self._paste_text(self.text2),
                        ),
                    ],
                ),
                ft.Container(
                    content=ft.TextField(
                        ref=self.text2,
                        multiline=True,
                        min_lines=25,
                        hint_text="输入第二个文本...",
                        text_size=13,
                        border=ft.InputBorder.NONE,
                        text_style=ft.TextStyle(font_family="Consolas,Monospace"),
                    ),
                    border=ft.border.all(1, ft.Colors.OUTLINE),
                    border_radius=8,
                    padding=PADDING_SMALL,
                    expand=True,
                ),
            ],
            spacing=5,
            expand=True,
        )
        
        # 使用共享的分隔条引用，这样输入和结果界面共用同一比例
        left_panel_input = ft.Container(
            content=text1_section,
            expand=self.left_flex,
        )
        
        # 分隔条（输入界面）
        divider_input = ft.GestureDetector(
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Icon(ft.Icons.CIRCLE, size=4, color=ft.Colors.GREY_500),
                        ft.Icon(ft.Icons.CIRCLE, size=4, color=ft.Colors.GREY_500),
                        ft.Icon(ft.Icons.CIRCLE, size=4, color=ft.Colors.GREY_500),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=3,
                ),
                width=12,
                bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.ON_SURFACE),
                border_radius=6,
                alignment=ft.alignment.center,
                margin=ft.margin.only(top=40, bottom=6),
            ),
            mouse_cursor=ft.MouseCursor.RESIZE_LEFT_RIGHT,
            on_pan_start=self._on_divider_pan_start_input,
            on_pan_update=self._on_divider_pan_update_input,
            on_pan_end=self._on_divider_pan_end_input,
            drag_interval=10,
        )
        
        right_panel_input = ft.Container(
            content=text2_section,
            expand=self.right_flex,
        )
        
        # 保存输入面板的引用（用于拖动调整）
        self.left_panel_input_ref = left_panel_input
        self.right_panel_input_ref = right_panel_input
        self.divider_input_ref = divider_input.content
        
        return ft.Row(
            controls=[
                left_panel_input,
                divider_input,
                right_panel_input,
            ],
            spacing=0,
            expand=True,
        )
    
    def _build_result_section(self) -> ft.Row:
        """构建结果区域（并排对比视图）。"""
        # 左侧对比列表
        left_list = ft.ListView(
            ref=self.diff_list_left,
            spacing=0,
            padding=ft.padding.all(4),
            expand=True,
            auto_scroll=False,
            on_scroll=self._sync_scroll_from_left,
        )
        
        # 右侧对比列表
        right_list = ft.ListView(
            ref=self.diff_list_right,
            spacing=0,
            padding=ft.padding.all(4),
            expand=True,
            auto_scroll=False,
            on_scroll=self._sync_scroll_from_right,
        )
        
        left_section = ft.Column(
            controls=[
                ft.Text("文本 1", weight=ft.FontWeight.BOLD, size=16),
                ft.Container(
                    content=left_list,
                    border=ft.border.all(1, ft.Colors.OUTLINE),
                    border_radius=8,
                    expand=True,
                    clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                ),
            ],
            spacing=5,
            expand=True,
        )
        
        right_section = ft.Column(
            controls=[
                ft.Text("文本 2", weight=ft.FontWeight.BOLD, size=16),
                ft.Container(
                    content=right_list,
                    border=ft.border.all(1, ft.Colors.OUTLINE),
                    border_radius=8,
                    expand=True,
                    clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                ),
            ],
            spacing=5,
            expand=True,
        )
        
        # 左侧面板容器（可调整宽度）
        left_panel = ft.Container(
            ref=self.left_panel_ref,
            content=left_section,
            expand=self.left_flex,
        )
        
        # 分隔条
        divider = ft.GestureDetector(
            content=ft.Container(
                ref=self.divider_ref,
                content=ft.Column(
                    controls=[
                        ft.Icon(ft.Icons.CIRCLE, size=4, color=ft.Colors.GREY_500),
                        ft.Icon(ft.Icons.CIRCLE, size=4, color=ft.Colors.GREY_500),
                        ft.Icon(ft.Icons.CIRCLE, size=4, color=ft.Colors.GREY_500),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=3,
                ),
                width=12,
                bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.ON_SURFACE),
                border_radius=6,
                alignment=ft.alignment.center,
                margin=ft.margin.only(top=40, bottom=6),
            ),
            mouse_cursor=ft.MouseCursor.RESIZE_LEFT_RIGHT,
            on_pan_start=self._on_divider_pan_start,
            on_pan_update=self._on_divider_pan_update,
            on_pan_end=self._on_divider_pan_end,
            drag_interval=10,
        )
        
        # 右侧面板容器（可调整宽度）
        right_panel = ft.Container(
            ref=self.right_panel_ref,
            content=right_section,
            expand=self.right_flex,
        )
        
        return ft.Row(
            controls=[
                left_panel,
                divider,
                right_panel,
            ],
            spacing=0,
            expand=True,
        )
    
    def _on_divider_pan_start(self, e: ft.DragStartEvent):
        """开始拖动分隔条。"""
        self.is_dragging = True
        if self.divider_ref.current:
            self.divider_ref.current.bgcolor = ft.Colors.PRIMARY
            self.divider_ref.current.update()
    
    def _on_divider_pan_update(self, e: ft.DragUpdateEvent):
        """拖动分隔条时更新面板宽度。"""
        if not self.is_dragging:
            return
        
        # 获取容器宽度
        container_width = self.page.width - PADDING_MEDIUM * 2 - 12
        if container_width <= 0:
            return
        
        # 计算拖动产生的比例变化
        delta_ratio = e.delta_x / container_width
        self.ratio += delta_ratio
        
        # 限制比例范围 (0.2 到 0.8)
        self.ratio = max(0.2, min(0.8, self.ratio))
        
        # 更新 flex 值
        new_total_flex = 1000
        self.left_flex = int(self.ratio * new_total_flex)
        self.right_flex = new_total_flex - self.left_flex
        
        # 同时更新输入界面和结果界面的面板宽度
        if hasattr(self, 'left_panel_input_ref') and hasattr(self, 'right_panel_input_ref'):
            self.left_panel_input_ref.expand = self.left_flex
            self.right_panel_input_ref.expand = self.right_flex
            self.left_panel_input_ref.update()
            self.right_panel_input_ref.update()
        
        if self.left_panel_ref.current and self.right_panel_ref.current:
            self.left_panel_ref.current.expand = self.left_flex
            self.right_panel_ref.current.expand = self.right_flex
            self.left_panel_ref.current.update()
            self.right_panel_ref.current.update()
    
    def _on_divider_pan_end(self, e: ft.DragEndEvent):
        """结束拖动分隔条。"""
        self.is_dragging = False
        if self.divider_ref.current:
            self.divider_ref.current.bgcolor = ft.Colors.with_opacity(0.1, ft.Colors.ON_SURFACE)
            self.divider_ref.current.update()
    
    def _on_divider_pan_start_input(self, e: ft.DragStartEvent):
        """开始拖动输入界面分隔条。"""
        self.is_dragging = True
        if self.divider_input_ref:
            self.divider_input_ref.bgcolor = ft.Colors.PRIMARY
            self.divider_input_ref.update()
    
    def _on_divider_pan_update_input(self, e: ft.DragUpdateEvent):
        """拖动输入界面分隔条时更新面板宽度。"""
        if not self.is_dragging:
            return
        
        # 获取容器宽度
        container_width = self.page.width - PADDING_MEDIUM * 2 - 12
        if container_width <= 0:
            return
        
        # 计算拖动产生的比例变化
        delta_ratio = e.delta_x / container_width
        self.ratio += delta_ratio
        
        # 限制比例范围 (0.2 到 0.8)
        self.ratio = max(0.2, min(0.8, self.ratio))
        
        # 更新 flex 值
        new_total_flex = 1000
        self.left_flex = int(self.ratio * new_total_flex)
        self.right_flex = new_total_flex - self.left_flex
        
        # 同时更新输入界面和结果界面的面板宽度
        if hasattr(self, 'left_panel_input_ref') and hasattr(self, 'right_panel_input_ref'):
            self.left_panel_input_ref.expand = self.left_flex
            self.right_panel_input_ref.expand = self.right_flex
            self.left_panel_input_ref.update()
            self.right_panel_input_ref.update()
        
        if self.left_panel_ref.current and self.right_panel_ref.current:
            self.left_panel_ref.current.expand = self.left_flex
            self.right_panel_ref.current.expand = self.right_flex
            self.left_panel_ref.current.update()
            self.right_panel_ref.current.update()
    
    def _on_divider_pan_end_input(self, e: ft.DragEndEvent):
        """结束拖动输入界面分隔条。"""
        self.is_dragging = False
        if self.divider_input_ref:
            self.divider_input_ref.bgcolor = ft.Colors.with_opacity(0.1, ft.Colors.ON_SURFACE)
            self.divider_input_ref.update()
    
    def _sync_scroll_from_left(self, e: ft.OnScrollEvent):
        """从左侧列表同步滚动到右侧。"""
        if self._syncing_scroll:
            return
        if not hasattr(e, "pixels"):
            return
        
        self._left_max_extent = getattr(e, "max_scroll_extent", 0) or 0
        ratio = e.pixels / self._left_max_extent if self._left_max_extent > 0 else 0.0
        ratio = max(0.0, min(1.0, ratio))
        
        self._syncing_scroll = True
        try:
            if self.diff_list_right.current:
                target_extent = self._right_max_extent if self._right_max_extent > 0 else self._left_max_extent
                target_offset = ratio * target_extent
                self.diff_list_right.current.scroll_to(offset=target_offset, duration=0)
        finally:
            self._syncing_scroll = False
    
    def _sync_scroll_from_right(self, e: ft.OnScrollEvent):
        """从右侧列表同步滚动到左侧。"""
        if self._syncing_scroll:
            return
        if not hasattr(e, "pixels"):
            return
        
        self._right_max_extent = getattr(e, "max_scroll_extent", 0) or 0
        ratio = e.pixels / self._right_max_extent if self._right_max_extent > 0 else 0.0
        ratio = max(0.0, min(1.0, ratio))
        
        self._syncing_scroll = True
        try:
            if self.diff_list_left.current:
                target_extent = self._left_max_extent if self._left_max_extent > 0 else self._right_max_extent
                target_offset = ratio * target_extent
                self.diff_list_left.current.scroll_to(offset=target_offset, duration=0)
        finally:
            self._syncing_scroll = False
    
    async def _paste_text(self, text_ref: ft.Ref[ft.TextField]):
        """粘贴文本。"""
        try:
            clipboard_text = await self.page.get_clipboard_async()
            if clipboard_text:
                text_ref.current.value = clipboard_text
                text_ref.current.update()
                self._show_snack("已粘贴")
            else:
                self._show_snack("剪贴板为空", error=True)
        except Exception as e:
            self._show_snack(f"粘贴失败: {str(e)}", error=True)
    
    def _compare(self, e):
        """执行对比。"""
        text1 = self.text1.current.value or ""
        text2 = self.text2.current.value or ""
        
        if not text1 and not text2:
            self._show_snack("请输入要对比的文本", error=True)
            return
        
        try:
            # 处理选项
            if self.ignore_whitespace.current.value:
                text1 = " ".join(text1.split())
                text2 = " ".join(text2.split())
            
            if self.ignore_case.current.value:
                text1 = text1.lower()
                text2 = text2.lower()
            
            # 分行
            lines1 = text1.splitlines()
            lines2 = text2.splitlines()
            
            # 生成差异
            diff_result = self._generate_diff(lines1, lines2)
            
            # 显示结果
            self._display_diff(diff_result)
            
            # 切换到结果视图
            self.input_container.current.visible = False
            self.result_container.current.visible = True
            
            # 更新按钮
            operation_bar = self.content.controls[3]  # operation_bar
            operation_bar.controls[-2].visible = True  # "返回编辑"按钮
            
            self.update()
            self._show_snack("对比完成")
            
        except Exception as e:
            self._show_snack(f"对比失败: {str(e)}", error=True)
    
    def _generate_diff(self, lines1: List[str], lines2: List[str]) -> List[dict]:
        """生成差异数据。
        
        返回格式：
        [
            {'type': 'equal', 'left': '内容', 'right': '内容'},
            {'type': 'delete', 'left': '内容', 'right': None},
            {'type': 'insert', 'left': None, 'right': '内容'},
            {'type': 'replace', 'left': '旧内容', 'right': '新内容'},
        ]
        """
        result = []
        matcher = difflib.SequenceMatcher(None, lines1, lines2)
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                # 相同的行
                for i, j in zip(range(i1, i2), range(j1, j2)):
                    result.append({
                        'type': 'equal',
                        'left': lines1[i],
                        'right': lines2[j],
                    })
            elif tag == 'delete':
                # 只在左边（被删除）
                for i in range(i1, i2):
                    result.append({
                        'type': 'delete',
                        'left': lines1[i],
                        'right': None,
                    })
            elif tag == 'insert':
                # 只在右边（新增）
                for j in range(j1, j2):
                    result.append({
                        'type': 'insert',
                        'left': None,
                        'right': lines2[j],
                    })
            elif tag == 'replace':
                # 修改的行
                left_count = i2 - i1
                right_count = j2 - j1
                max_count = max(left_count, right_count)
                
                for k in range(max_count):
                    left_line = lines1[i1 + k] if k < left_count else None
                    right_line = lines2[j1 + k] if k < right_count else None
                    
                    if left_line is not None and right_line is not None:
                        result.append({
                            'type': 'replace',
                            'left': left_line,
                            'right': right_line,
                        })
                    elif left_line is not None:
                        result.append({
                            'type': 'delete',
                            'left': left_line,
                            'right': None,
                        })
                    else:
                        result.append({
                            'type': 'insert',
                            'left': None,
                            'right': right_line,
                        })
        
        return result
    
    def _display_diff(self, diff_result: List[dict]):
        """显示差异结果。"""
        left_controls = []
        right_controls = []
        
        added_count = 0
        removed_count = 0
        modified_count = 0
        
        left_line_num = 1
        right_line_num = 1
        
        for item in diff_result:
            diff_type = item['type']
            left_text = item.get('left', '')
            right_text = item.get('right', '')
            
            # 颜色方案
            if diff_type == 'equal':
                left_bg = None
                right_bg = None
            elif diff_type == 'delete':
                left_bg = ft.Colors.with_opacity(0.3, ft.Colors.RED)
                right_bg = ft.Colors.with_opacity(0.1, ft.Colors.GREY)
                removed_count += 1
            elif diff_type == 'insert':
                left_bg = ft.Colors.with_opacity(0.1, ft.Colors.GREY)
                right_bg = ft.Colors.with_opacity(0.3, ft.Colors.GREEN)
                added_count += 1
            elif diff_type == 'replace':
                left_bg = ft.Colors.with_opacity(0.3, ft.Colors.ORANGE)
                right_bg = ft.Colors.with_opacity(0.3, ft.Colors.BLUE)
                modified_count += 1
            else:
                left_bg = None
                right_bg = None
            
            # 左侧行号和内容
            if left_text is not None:
                left_line_content = ft.Row(
                    controls=[
                        ft.Text(
                            value=f"{left_line_num:4d}  ",
                            size=11,
                            color=ft.Colors.GREY_500,
                            font_family="Consolas,Monospace",
                        ),
                        ft.Text(
                            value=left_text,
                            size=12,
                            font_family="Consolas,Monospace",
                            selectable=True,
                            no_wrap=False,
                        ),
                    ],
                    spacing=0,
                    tight=True,
                )
                left_line_num += 1
            else:
                left_line_content = ft.Container(height=20)
            
            # 右侧行号和内容
            if right_text is not None:
                right_line_content = ft.Row(
                    controls=[
                        ft.Text(
                            value=f"{right_line_num:4d}  ",
                            size=11,
                            color=ft.Colors.GREY_500,
                            font_family="Consolas,Monospace",
                        ),
                        ft.Text(
                            value=right_text,
                            size=12,
                            font_family="Consolas,Monospace",
                            selectable=True,
                            no_wrap=False,
                        ),
                    ],
                    spacing=0,
                    tight=True,
                )
                right_line_num += 1
            else:
                right_line_content = ft.Container(height=20)
            
            # 左侧行容器
            left_line = ft.Container(
                content=left_line_content,
                bgcolor=left_bg,
                padding=ft.padding.symmetric(horizontal=4, vertical=4),
                border=ft.border.only(bottom=ft.border.BorderSide(0.5, ft.Colors.OUTLINE_VARIANT)),
            )
            
            # 右侧行容器
            right_line = ft.Container(
                content=right_line_content,
                bgcolor=right_bg,
                padding=ft.padding.symmetric(horizontal=4, vertical=4),
                border=ft.border.only(bottom=ft.border.BorderSide(0.5, ft.Colors.OUTLINE_VARIANT)),
            )
            
            left_controls.append(left_line)
            right_controls.append(right_line)
        
        # 更新列表
        self.diff_list_left.current.controls = left_controls
        self.diff_list_right.current.controls = right_controls
        
        # 更新统计
        total = len(diff_result)
        equal = total - added_count - removed_count - modified_count
        stats = f"总计 {total} 行 | 相同 {equal} | 新增 {added_count} | 删除 {removed_count} | 修改 {modified_count}"
        self.stats_text.current.value = stats
    
    def _back_to_input(self, e):
        """返回输入视图。"""
        self.input_container.current.visible = True
        self.result_container.current.visible = False
        
        # 隐藏"返回编辑"按钮
        operation_bar = self.content.controls[3]
        operation_bar.controls[-2].visible = False
        
        self.update()
    
    def _clear(self, e):
        """清空所有内容。"""
        self.text1.current.value = ""
        self.text2.current.value = ""
        self.diff_list_left.current.controls = []
        self.diff_list_right.current.controls = []
        self.stats_text.current.value = ""
        
        # 返回输入视图
        self.input_container.current.visible = True
        self.result_container.current.visible = False
        
        # 隐藏"返回编辑"按钮
        operation_bar = self.content.controls[3]
        operation_bar.controls[-2].visible = False
        
        self.update()
    
    def _on_back_click(self):
        if self.on_back:
            self.on_back()
    
    def _show_help(self, e):
        """显示使用说明。"""
        help_text = """
**文本对比工具使用说明**

**功能说明：**
- 并排对比两个文本的差异
- 用颜色高亮显示不同类型的差异
- 实时统计差异数量

**使用步骤：**
1. 在左右两侧输入框中粘贴要对比的文本
2. 可选：勾选"忽略空格"或"忽略大小写"
3. 点击"开始对比"
4. 查看并排对比结果

**颜色说明：**
- **红色背景**：该行仅在文本1中存在（被删除）
- **绿色背景**：该行仅在文本2中存在（新增）
- **橙色/蓝色背景**：该行在两个文本中都存在但内容不同（修改）
- **无背景色**：两个文本中该行完全相同

**使用场景：**
- 对比两个JSON响应的差异
- 检查配置文件的修改
- 对比代码片段
- 查看文档的改动

**提示：**
- 点击"返回编辑"可以回到输入界面修改文本
- 点击"清空"会清除所有内容并返回输入界面
        """
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("使用说明"),
            content=ft.Container(
                content=ft.Markdown(
                    help_text,
                    selectable=True,
                    extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                ),
                width=500,
                height=450,
            ),
            actions=[
                ft.TextButton("关闭", on_click=lambda _: self.page.close(dialog)),
            ],
        )
        
        self.page.open(dialog)
    
    def _show_snack(self, message: str, error: bool = False):
        self.page.snack_bar = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=ft.Colors.RED_400 if error else ft.Colors.GREEN_400,
        )
        self.page.snack_bar.open = True
        self.page.update()
