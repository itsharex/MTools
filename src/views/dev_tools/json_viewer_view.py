# -*- coding: utf-8 -*-
"""JSON 查看器视图模块。

提供 JSON 格式化和树形查看功能。
"""

import ast
import json
from typing import Any, Callable, Dict, List, Optional

import flet as ft

from constants import PADDING_MEDIUM, PADDING_SMALL
from services import ConfigService


class JsonTreeNode(ft.Container):
    """JSON 树形节点组件。
    
    可展开/收起的 JSON 节点。
    """
    
    def __init__(self, key: str, value: Any, level: int = 0, is_last: bool = True, parent_path: str = ""):
        """初始化 JSON 树形节点。
        
        Args:
            key: 节点键名
            value: 节点值
            level: 缩进层级
            is_last: 是否是最后一个节点
            parent_path: 父节点路径
        """
        super().__init__()
        self.key = key
        self.value = value
        self.level = level
        self.is_last = is_last
        self.parent_path = parent_path
        
        # 计算完整路径
        if not parent_path:
            self.full_path = key
        else:
            if str(key).startswith("["):
                self.full_path = f"{parent_path}{key}"
            else:
                self.full_path = f"{parent_path}.{key}"

        self.expanded = True
        self.icon_ref = ft.Ref[ft.Icon]()
        self.content_ref = ft.Ref[ft.Column]()
        
        self.content = self._build_view()
        
    def toggle_expand(self, e):
        """切换展开/收起状态。"""
        self.expanded = not self.expanded
        self.icon_ref.current.name = (
            ft.Icons.KEYBOARD_ARROW_DOWN if self.expanded 
            else ft.Icons.KEYBOARD_ARROW_RIGHT
        )
        self.content_ref.current.visible = self.expanded
        self.update()
    
    def _get_value_preview(self, value: Any, truncate: bool = True) -> str:
        """获取值的预览文本。
        
        Args:
            value: 要预览的值
            truncate: 是否截断长字符串
            
        Returns:
            预览文本
        """
        if isinstance(value, dict):
            count = len(value)
            return f"{{...}} ({count} {'key' if count == 1 else 'keys'})"
        elif isinstance(value, list):
            count = len(value)
            return f"[...] ({count} {'item' if count == 1 else 'items'})"
        elif isinstance(value, str):
            if truncate and len(value) > 50:
                return f'"{value[:47]}..."'
            return f'"{value}"'
        elif value is None:
            return "null"
        elif isinstance(value, bool):
            return "true" if value else "false"
        else:
            return str(value)
    
    def _get_value_color(self, value: Any) -> str:
        """根据值类型返回颜色。
        
        Args:
            value: 值
            
        Returns:
            颜色代码
        """
        if isinstance(value, (dict, list)):
            return ft.Colors.BLUE_400
        elif isinstance(value, str):
            return ft.Colors.GREEN_400
        elif isinstance(value, (int, float)):
            return ft.Colors.ORANGE_400
        elif isinstance(value, bool):
            return ft.Colors.PURPLE_400
        elif value is None:
            return ft.Colors.GREY_400
        else:
            return ft.Colors.WHITE
    
    def _build_view(self):
        """构建节点视图。"""
        print(f"[DEBUG] JsonTreeNode._build_view() called for key: {self.key}, type: {type(self.value)}")
        indent = self.level * 20
        
        # 如果是字典
        if isinstance(self.value, dict):
            children = []
            items = list(self.value.items())
            
            for idx, (k, v) in enumerate(items):
                is_last_child = idx == len(items) - 1
                children.append(JsonTreeNode(k, v, self.level + 1, is_last_child, parent_path=self.full_path))
            
            result = ft.Container(
                content=ft.Column(
                    controls=[
                        # 头部（可点击展开/收起）
                        ft.GestureDetector(
                            content=ft.Container(
                                content=ft.Row(
                                    controls=[
                                        ft.Icon(
                                            ref=self.icon_ref,
                                            name=ft.Icons.KEYBOARD_ARROW_DOWN,
                                            size=16,
                                            color=ft.Colors.GREY_400,
                                        ),
                                        ft.Text(
                                            f'"{self.key}": ',
                                            weight=ft.FontWeight.BOLD,
                                        ),
                                        ft.Text(
                                            self._get_value_preview(self.value),
                                            color=self._get_value_color(self.value),
                                        ),
                                    ],
                                    spacing=5,
                                ),
                                padding=ft.padding.only(left=indent),
                                on_click=self.toggle_expand,
                                ink=True,
                                # 添加调试用的背景色和最小高度
                                bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.GREEN),
                                height=30,
                            ),
                            on_secondary_tap=self._on_right_click,
                        ),
                        # 子节点
                        ft.Column(
                            ref=self.content_ref,
                            controls=children,
                            spacing=2,
                            visible=self.expanded,
                        ),
                    ],
                    spacing=2,
                ),
            )
            print(f"[DEBUG] Built dict node for {self.key}, has {len(children)} children")
            return result
        
        # 如果是数组
        elif isinstance(self.value, list):
            children = []
            
            for idx, item in enumerate(self.value):
                is_last_child = idx == len(self.value) - 1
                children.append(JsonTreeNode(f"[{idx}]", item, self.level + 1, is_last_child, parent_path=self.full_path))
            
            result = ft.Container(
                content=ft.Column(
                    controls=[
                        # 头部
                        ft.GestureDetector(
                            content=ft.Container(
                                content=ft.Row(
                                    controls=[
                                        ft.Icon(
                                            ref=self.icon_ref,
                                            name=ft.Icons.KEYBOARD_ARROW_DOWN,
                                            size=16,
                                            color=ft.Colors.GREY_400,
                                        ),
                                        ft.Text(
                                            f'"{self.key}": ',
                                            weight=ft.FontWeight.BOLD,
                                        ),
                                        ft.Text(
                                            self._get_value_preview(self.value),
                                            color=self._get_value_color(self.value),
                                        ),
                                    ],
                                    spacing=5,
                                ),
                                padding=ft.padding.only(left=indent),
                                on_click=self.toggle_expand,
                                ink=True,
                                # 添加调试用的背景色和最小高度
                                bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.ORANGE),
                                height=30,
                            ),
                            on_secondary_tap=self._on_right_click,
                        ),
                        # 子节点
                        ft.Column(
                            ref=self.content_ref,
                            controls=children,
                            spacing=2,
                            visible=self.expanded,
                        ),
                    ],
                    spacing=2,
                ),
            )
            print(f"[DEBUG] Built list node for {self.key}, has {len(children)} items")
            return result
        
        # 如果是基本类型
        else:
            result = ft.GestureDetector(
                content=ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Container(width=16),  # 占位符，对齐
                            ft.Text(
                                f'"{self.key}": ',
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.Text(
                                self._get_value_preview(self.value, truncate=False),
                                color=self._get_value_color(self.value),
                                selectable=False,
                                expand=True,  # 允许自动换行
                            ),
                        ],
                        spacing=5,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    ),
                    padding=ft.padding.only(left=indent, top=2, bottom=2),
                    # 添加调试用的背景色
                    bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.BLUE),
                ),
                on_secondary_tap=self._on_right_click,
            )
            print(f"[DEBUG] Built leaf node for {self.key}")
            return result

    def _on_right_click(self, e):
        """右键点击事件处理。"""
        e.page.dialog = ft.AlertDialog(
            title=ft.Text("操作"),
            content=ft.Column([
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.COPY),
                    title=ft.Text("复制路径"),
                    subtitle=ft.Text(self.full_path, size=12, color=ft.Colors.GREY_400),
                    on_click=lambda _: self._copy_to_clipboard(e.page, self.full_path)
                ),
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.COPY),
                    title=ft.Text("复制键 (Key)"),
                    subtitle=ft.Text(str(self.key), size=12, color=ft.Colors.GREY_400),
                    on_click=lambda _: self._copy_to_clipboard(e.page, str(self.key))
                ),
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.COPY),
                    title=ft.Text("复制值 (Value)"),
                    subtitle=ft.Text(self._get_value_preview(self.value), size=12, color=ft.Colors.GREY_400),
                    on_click=lambda _: self._copy_value_to_clipboard(e.page)
                ),
            ], tight=True, width=400),
            actions=[ft.TextButton("关闭", on_click=lambda _: self._close_dialog(e.page))],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        e.page.dialog.open = True
        e.page.update()

    def _copy_to_clipboard(self, page, text):
        """复制文本到剪贴板。"""
        page.set_clipboard(text)
        page.show_snack_bar(ft.SnackBar(content=ft.Text(f"已复制: {text[:50]}...")))
        self._close_dialog(page)

    def _copy_value_to_clipboard(self, page):
        """复制值到剪贴板。"""
        if isinstance(self.value, (dict, list)):
            text = json.dumps(self.value, ensure_ascii=False, indent=2)
        else:
            text = str(self.value)
        self._copy_to_clipboard(page, text)

    def _close_dialog(self, page):
        """关闭对话框。"""
        page.dialog.open = False
        page.update()


class JsonViewerView(ft.Container):
    """JSON 查看器视图类。
    
    提供 JSON 格式化和树形查看功能。
    """
    
    def __init__(
        self,
        page: ft.Page,
        config_service: Optional[ConfigService] = None,
        on_back: Optional[Callable] = None
    ):
        """初始化 JSON 查看器视图。
        
        Args:
            page: Flet 页面对象
            config_service: 配置服务实例（可选）
            on_back: 返回回调函数（可选）
        """
        super().__init__()
        self.page = page
        self.config_service = config_service
        self.on_back = on_back
        self.expand = True
        self.padding = 0
        
        # 输入文本框引用
        self.input_text = ft.Ref[ft.TextField]()
        # 左侧格式化文本引用
        self.formatted_text = ft.Ref[ft.TextField]()
        # 右侧树形视图引用
        self.tree_view = ft.Ref[ft.Column]()
        # 错误提示引用
        self.error_text = ft.Ref[ft.Text]()
        
        self._build_ui()
    
    def _build_ui(self):
        """构建用户界面。"""
        # 返回按钮（如果提供了 on_back 回调）
        header_controls = []
        if self.on_back:
            back_button = ft.Container(
                content=ft.Row(
                    controls=[
                        ft.IconButton(
                            icon=ft.Icons.ARROW_BACK,
                            icon_color=ft.Colors.WHITE,
                            on_click=lambda _: self.on_back() if self.on_back else None,
                            tooltip="返回开发工具",
                        ),
                        ft.Text(
                            "JSON 查看器",
                            size=20,
                            weight=ft.FontWeight.BOLD,
                        ),
                    ],
                    spacing=PADDING_MEDIUM,
                ),
                padding=PADDING_MEDIUM,
            )
            header_controls.extend([back_button, ft.Divider(height=1)])
        
        # 输入区域
        input_section = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        "输入 JSON",
                        size=16,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.TextField(
                        ref=self.input_text,
                        multiline=True,
                        min_lines=10,
                        max_lines=20,
                        hint_text='粘贴或输入 JSON 数据...\n\n✅ 支持标准 JSON: {"name": "value"}\n✅ 支持单引号: {\'name\': \'value\'}\n✅ 支持 Python 字典格式\n\n自动修复格式并显示！',
                        border_color=ft.Colors.BLUE_400,
                        text_size=13,
                    ),
                ],
                spacing=PADDING_SMALL,
            ),
            padding=PADDING_MEDIUM,
        )
        
        # 操作按钮
        action_buttons = ft.Row(
            controls=[
                ft.ElevatedButton(
                    "格式化并查看",
                    icon=ft.Icons.AUTO_AWESOME,
                    on_click=self._on_format_click,
                ),
                ft.ElevatedButton(
                    "压缩 JSON",
                    icon=ft.Icons.COMPRESS,
                    on_click=self._on_compress_click,
                ),
                ft.ElevatedButton(
                    "全部展开",
                    icon=ft.Icons.UNFOLD_MORE,
                    on_click=self._on_expand_all_click,
                ),
                ft.ElevatedButton(
                    "全部收起",
                    icon=ft.Icons.UNFOLD_LESS,
                    on_click=self._on_collapse_all_click,
                ),
                ft.ElevatedButton(
                    "加载示例",
                    icon=ft.Icons.LIGHTBULB_OUTLINE,
                    on_click=self._on_load_example_click,
                ),
                ft.ElevatedButton(
                    "清空",
                    icon=ft.Icons.CLEAR,
                    on_click=self._on_clear_click,
                ),
            ],
            spacing=PADDING_SMALL,
            wrap=True,
        )
        
        # 错误提示
        error_section = ft.Container(
            content=ft.Text(
                ref=self.error_text,
                color=ft.Colors.RED_400,
                visible=False,
            ),
            padding=ft.padding.only(left=PADDING_MEDIUM),
        )
        
        # 左侧：格式化后的 JSON 文本
        left_panel = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        "格式化文本",
                        size=16,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.TextField(
                        ref=self.formatted_text,
                        multiline=True,
                        min_lines=20,
                        max_lines=30,
                        read_only=True,
                        border_color=ft.Colors.GREEN_400,
                        text_size=13,
                    ),
                ],
                spacing=PADDING_SMALL,
            ),
            padding=PADDING_MEDIUM,
            expand=1,
        )
        
        # 右侧：树形视图
        right_panel = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        "树形视图",
                        size=16,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Container(
                        content=ft.Column(
                            ref=self.tree_view,
                            controls=[
                                ft.Text(
                                    "格式化后将在此处显示树形结构",
                                    color=ft.Colors.GREY_400,
                                    italic=True,
                                ),
                            ],
                            spacing=2,
                            scroll=ft.ScrollMode.AUTO,
                            expand=True,
                        ),
                        border=ft.border.all(1, ft.Colors.PURPLE_400),
                        border_radius=5,
                        padding=PADDING_MEDIUM,
                        height=600,
                        bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.SURFACE_TINT),  # 添加背景色以便看到区域
                    ),
                ],
                spacing=PADDING_SMALL,
            ),
            padding=PADDING_MEDIUM,
            expand=1,
        )
        
        # 结果区域（左右分栏）
        result_section = ft.Row(
            controls=[left_panel, right_panel],
            spacing=PADDING_MEDIUM,
            expand=True,
        )
        
        # 主内容区域
        main_content = ft.Column(
            controls=[
                input_section,
                action_buttons,
                error_section,
                result_section,
            ],
            spacing=PADDING_MEDIUM,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )
        
        # 组装视图
        self.content = ft.Column(
            controls=header_controls + [main_content] if header_controls else [main_content],
            spacing=0,
            expand=True,
        )
    
    def _parse_json_smart(self, input_value: str) -> Any:
        """智能解析 JSON，支持多种格式。
        
        Args:
            input_value: 输入的 JSON 字符串
            
        Returns:
            解析后的 Python 对象
            
        Raises:
            ValueError: 解析失败时抛出
        """
        # 先尝试标准 JSON 解析
        try:
            return json.loads(input_value)
        except json.JSONDecodeError as e1:
            # 如果是单引号问题，尝试用 ast.literal_eval
            try:
                result = ast.literal_eval(input_value)
                # 确保结果是可以序列化为 JSON 的类型
                if isinstance(result, (dict, list, str, int, float, bool, type(None))):
                    return result
                raise ValueError("不支持的数据类型")
            except (ValueError, SyntaxError) as e2:
                # 尝试替换单引号为双引号
                try:
                    fixed_input = input_value.replace("'", '"')
                    return json.loads(fixed_input)
                except json.JSONDecodeError:
                    # 所有方法都失败，抛出原始错误
                    raise ValueError(f"JSON 解析失败 (行 {e1.lineno}, 列 {e1.colno}): {e1.msg}")
    
    def _on_format_click(self, e):
        """格式化按钮点击事件。"""
        input_value = self.input_text.current.value
        
        if not input_value or not input_value.strip():
            self._show_error("请输入 JSON 数据")
            return
        
        try:
            # 使用智能解析
            data = self._parse_json_smart(input_value)
            
            # 格式化文本
            formatted = json.dumps(data, indent=2, ensure_ascii=False)
            self.formatted_text.current.value = formatted
            
            # 构建树形视图
            self._build_tree_view(data)
            
            # 隐藏错误提示
            self.error_text.current.visible = False
            
            self.update()
            
        except ValueError as ex:
            error_msg = str(ex)
            
            # 提供常见错误的提示
            if "Expecting property name" in error_msg:
                error_msg += "\n💡 已自动尝试修复单引号，但仍然失败。请检查格式。"
            elif "Expecting value" in error_msg:
                error_msg += "\n💡 提示：检查是否有多余的逗号或缺少值"
            elif "Extra data" in error_msg:
                error_msg += "\n💡 提示：JSON 末尾有多余的内容"
            
            self._show_error(error_msg)
        except Exception as ex:
            self._show_error(f"发生错误: {str(ex)}")
    
    def _on_compress_click(self, e):
        """压缩按钮点击事件。"""
        input_value = self.input_text.current.value
        
        if not input_value or not input_value.strip():
            self._show_error("请输入 JSON 数据")
            return
        
        try:
            # 使用智能解析
            data = self._parse_json_smart(input_value)
            compressed = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
            self.formatted_text.current.value = compressed
            
            # 隐藏错误提示
            self.error_text.current.visible = False
            
            self.update()
            
        except ValueError as ex:
            self._show_error(str(ex))
        except Exception as ex:
            self._show_error(f"发生错误: {str(ex)}")
    
    def _on_expand_all_click(self, e):
        """全部展开按钮点击事件。"""
        self._toggle_all_nodes(True)
    
    def _on_collapse_all_click(self, e):
        """全部收起按钮点击事件。"""
        self._toggle_all_nodes(False)
    
    def _toggle_all_nodes(self, expand: bool):
        """递归展开/收起所有节点。
        
        Args:
            expand: True 为展开，False 为收起
        """
        def toggle_recursive(controls):
            for control in controls:
                if isinstance(control, JsonTreeNode):
                    control.expanded = expand
                    if hasattr(control, 'icon_ref') and control.icon_ref.current:
                        control.icon_ref.current.name = (
                            ft.Icons.KEYBOARD_ARROW_DOWN if expand 
                            else ft.Icons.KEYBOARD_ARROW_RIGHT
                        )
                    if hasattr(control, 'content_ref') and control.content_ref.current:
                        control.content_ref.current.visible = expand
                        toggle_recursive(control.content_ref.current.controls)
                    # 不要对单个控件调用 update，最后统一更新
                elif hasattr(control, 'controls'):
                    toggle_recursive(control.controls)
        
        if self.tree_view.current and self.tree_view.current.controls:
            toggle_recursive(self.tree_view.current.controls)
            # 统一更新整个树形视图
            self.tree_view.current.update()
    
    def _on_clear_click(self, e):
        """清空按钮点击事件。"""
        self.input_text.current.value = ""
        self.formatted_text.current.value = ""
        self.tree_view.current.controls = [
            ft.Text(
                "格式化后将在此处显示树形结构",
                color=ft.Colors.GREY_400,
                italic=True,
            ),
        ]
        self.error_text.current.visible = False
        self.update()
    
    def _on_load_example_click(self, e):
        """加载示例 JSON 点击事件。"""
        example_json = {
            "name": "张三",
            "age": 25,
            "email": "zhangsan@example.com",
            "isActive": True,
            "tags": ["开发", "Python", "前端"],
            "address": {
                "country": "中国",
                "province": "北京",
                "city": "北京市",
                "detail": "朝阳区xxx街道"
            },
            "projects": [
                {
                    "name": "项目A",
                    "status": "进行中",
                    "progress": 75
                },
                {
                    "name": "项目B",
                    "status": "已完成",
                    "progress": 100
                }
            ]
        }
        
        # 将示例填充到输入框
        self.input_text.current.value = json.dumps(example_json, indent=2, ensure_ascii=False)
        
        # 自动格式化
        self.formatted_text.current.value = json.dumps(example_json, indent=2, ensure_ascii=False)
        
        # 构建树形视图
        self._build_tree_view(example_json)
        
        # 隐藏错误提示
        self.error_text.current.visible = False
        
        self.update()
    
    def _build_tree_view(self, data: Any):
        """构建树形视图。
        
        Args:
            data: JSON 数据
        """
        print(f"[DEBUG] _build_tree_view called, tree_view ref: {self.tree_view}")
        print(f"[DEBUG] tree_view.current: {self.tree_view.current}")
        print(f"[DEBUG] Before clear, controls count: {len(self.tree_view.current.controls) if self.tree_view.current else 'None'}")
        
        self.tree_view.current.controls.clear()
        
        print(f"[DEBUG] After clear, controls count: {len(self.tree_view.current.controls)}")
        print(f"[DEBUG] Building tree view for data type: {type(data)}")
        
        if isinstance(data, dict):
            print(f"[DEBUG] Building {len(data)} dict items")
            for key, value in data.items():
                node = JsonTreeNode(key, value, level=0)
                print(f"[DEBUG] Adding node: {key} = {type(value)}")
                self.tree_view.current.controls.append(node)
        elif isinstance(data, list):
            print(f"[DEBUG] Building {len(data)} list items")
            for idx, item in enumerate(data):
                node = JsonTreeNode(f"[{idx}]", item, level=0)
                self.tree_view.current.controls.append(node)
        else:
            print(f"[DEBUG] Building simple value: {data}")
            self.tree_view.current.controls.append(
                ft.Text(f"值: {json.dumps(data, ensure_ascii=False)}")
            )
        
        print(f"[DEBUG] Total controls in tree view: {len(self.tree_view.current.controls)}")
        print(f"[DEBUG] Controls types: {[type(c).__name__ for c in self.tree_view.current.controls]}")
        
        # 更新树形视图
        self.tree_view.current.update()
        print(f"[DEBUG] Tree view updated")
    
    def _show_error(self, message: str):
        """显示错误提示。
        
        Args:
            message: 错误消息
        """
        self.error_text.current.value = message
        self.error_text.current.visible = True
        self.update()
