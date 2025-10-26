"""图片背景移除视图模块。

提供图片背景移除功能的用户界面。
"""

import threading
import webbrowser
from pathlib import Path
from typing import Callable, List, Optional

import flet as ft

from constants import (
    BORDER_RADIUS_MEDIUM,
    PADDING_LARGE,
    PADDING_MEDIUM,
    PADDING_XLARGE,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)
from services import ConfigService, ImageService
from services.image_service import BackgroundRemover
from utils import format_file_size


class ImageBackgroundView(ft.Container):
    """图片背景移除视图类。
    
    提供图片背景移除功能，包括：
    - 单文件和批量处理
    - 自动下载ONNX模型
    - 处理进度显示
    - 导出为PNG格式（保留透明通道）
    """

    # 模型下载URL
    MODEL_URL = "https://www.modelscope.cn/models/AI-ModelScope/RMBG-2.0/resolve/master/onnx/model_q4.onnx"

    def __init__(
        self,
        page: ft.Page,
        config_service: ConfigService,
        image_service: ImageService,
        on_back: Optional[Callable] = None
    ) -> None:
        """初始化图片背景移除视图。
        
        Args:
            page: Flet页面对象
            config_service: 配置服务实例
            image_service: 图片服务实例
            on_back: 返回按钮回调函数
        """
        super().__init__()
        self.page: ft.Page = page
        self.config_service: ConfigService = config_service
        self.image_service: ImageService = image_service
        self.on_back: Optional[Callable] = on_back
        
        self.selected_files: List[Path] = []
        self.bg_remover: Optional[BackgroundRemover] = None
        self.is_model_loading: bool = False
        
        self.expand: bool = True
        # 右侧多留一些空间给滚动条
        self.padding: ft.padding = ft.padding.only(
            left=PADDING_XLARGE,
            right=PADDING_XLARGE + 16,
            top=PADDING_XLARGE,
            bottom=PADDING_XLARGE
        )
        
        # 获取模型路径
        self.model_path: Path = self._get_model_path()
        
        # 构建界面
        self._build_ui()
    
    def _get_model_path(self) -> Path:
        """获取模型文件路径。
        
        Returns:
            模型文件路径
        """
        # 使用数据目录（可以是用户自定义的）
        data_dir = self.config_service.get_data_dir()
        
        # 模型存储在 models/rmbg2.0 子目录
        models_dir = data_dir / "models" / "rmbg2.0"
        models_dir.mkdir(parents=True, exist_ok=True)
        
        return models_dir / "model_q4.onnx"
    
    def _build_ui(self) -> None:
        """构建用户界面。"""
        # 顶部：标题和返回按钮
        header: ft.Row = ft.Row(
            controls=[
                ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    tooltip="返回",
                    on_click=self._on_back_click,
                ),
                ft.Text("背景移除", size=28, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
            ],
            spacing=PADDING_MEDIUM,
        )
        
        # 文件选择区域
        self.file_list_view: ft.Column = ft.Column(
            spacing=PADDING_MEDIUM // 2,
            scroll=ft.ScrollMode.AUTO,
        )
        
        file_select_area: ft.Column = ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text("选择图片:", size=14, weight=ft.FontWeight.W_500),
                        ft.ElevatedButton(
                            "选择文件",
                            icon=ft.Icons.FILE_UPLOAD,
                            on_click=self._on_select_files,
                        ),
                        ft.ElevatedButton(
                            "选择文件夹",
                            icon=ft.Icons.FOLDER_OPEN,
                            on_click=self._on_select_folder,
                        ),
                        ft.TextButton(
                            "清空列表",
                            icon=ft.Icons.CLEAR_ALL,
                            on_click=self._on_clear_files,
                        ),
                    ],
                    spacing=PADDING_MEDIUM,
                ),
                # 支持格式说明
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.INFO_OUTLINE, size=16, color=TEXT_SECONDARY),
                            ft.Text(
                                "支持格式: JPG, PNG, WebP, BMP, TIFF, GIF 等 | 处理结果将保存为PNG格式（保留透明背景）",
                                size=12,
                                color=TEXT_SECONDARY,
                            ),
                        ],
                        spacing=8,
                    ),
                    margin=ft.margin.only(left=4, bottom=4),
                ),
                ft.Container(
                    content=self.file_list_view,
                    height=280,
                    border=ft.border.all(1, ft.Colors.OUTLINE),
                    border_radius=BORDER_RADIUS_MEDIUM,
                    padding=PADDING_MEDIUM,
                ),
            ],
            spacing=PADDING_MEDIUM,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )
        
        # 模型状态显示
        self.model_status_icon: ft.Icon = ft.Icon(
            ft.Icons.HOURGLASS_EMPTY,
            size=20,
            color=TEXT_SECONDARY,
        )
        
        self.model_status_text: ft.Text = ft.Text(
            "正在初始化...",
            size=13,
            color=TEXT_SECONDARY,
        )
        
        # 下载按钮（初始隐藏）
        self.download_model_button: ft.ElevatedButton = ft.ElevatedButton(
            text="下载模型",
            icon=ft.Icons.DOWNLOAD,
            on_click=self._start_download_model,
            visible=False,
        )
        
        model_status_row: ft.Row = ft.Row(
            controls=[
                self.model_status_icon,
                self.model_status_text,
                self.download_model_button,
            ],
            spacing=PADDING_MEDIUM // 2,
        )
        
        # 处理选项（右侧区域）
        self.output_mode_radio: ft.RadioGroup = ft.RadioGroup(
            content=ft.Column(
                controls=[
                    ft.Radio(value="new", label="保存为新文件（添加后缀 _no_bg）"),
                    ft.Radio(value="custom", label="自定义输出目录"),
                ],
                spacing=PADDING_MEDIUM // 2,
            ),
            value="new",
            on_change=self._on_output_mode_change,
        )
        
        self.custom_output_dir: ft.TextField = ft.TextField(
            label="输出目录",
            value=str(self.config_service.get_data_dir() / "background_removed"),
            disabled=True,
            expand=True,
        )
        
        self.browse_output_button: ft.IconButton = ft.IconButton(
            icon=ft.Icons.FOLDER_OPEN,
            tooltip="浏览",
            on_click=self._on_browse_output,
            disabled=True,
        )
        
        process_options: ft.Container = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("处理选项:", size=14, weight=ft.FontWeight.W_500),
                    model_status_row,
                    ft.Container(height=PADDING_MEDIUM),
                    ft.Text("输出设置:", size=14, weight=ft.FontWeight.W_500),
                    self.output_mode_radio,
                    ft.Row(
                        controls=[
                            self.custom_output_dir,
                            self.browse_output_button,
                        ],
                        spacing=PADDING_MEDIUM // 2,
                    ),
                ],
                spacing=PADDING_MEDIUM // 2,
            ),
            padding=PADDING_MEDIUM,
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=BORDER_RADIUS_MEDIUM,
            height=280,
        )
        
        # 左右分栏布局
        main_content: ft.Row = ft.Row(
            controls=[
                ft.Container(
                    content=file_select_area,
                    expand=3,
                ),
                ft.Container(
                    content=process_options,
                    expand=2,
                ),
            ],
            spacing=PADDING_LARGE,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )
        
        # 进度显示
        self.progress_bar: ft.ProgressBar = ft.ProgressBar(value=0, visible=False)
        self.progress_text: ft.Text = ft.Text("", size=12, color=TEXT_SECONDARY, visible=False)
        
        progress_container: ft.Container = ft.Container(
            content=ft.Column(
                controls=[
                    self.progress_bar,
                    self.progress_text,
                ],
                spacing=PADDING_MEDIUM // 2,
            ),
        )
        
        # 底部大按钮
        self.process_button: ft.Container = ft.Container(
            content=ft.ElevatedButton(
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.AUTO_FIX_HIGH, size=24),
                        ft.Text("开始移除背景", size=16, weight=ft.FontWeight.W_500),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=PADDING_MEDIUM,
                ),
                on_click=self._on_process,
                disabled=True,
                height=56,
            ),
            alignment=ft.alignment.center,
        )
        
        # 组装视图
        self.content = ft.Column(
            controls=[
                header,
                ft.Container(height=PADDING_LARGE),
                main_content,
                ft.Container(height=PADDING_LARGE),
                progress_container,
                ft.Container(height=PADDING_MEDIUM),
                self.process_button,
            ],
            spacing=0,
            scroll=ft.ScrollMode.AUTO,
        )
        
        # 检查模型状态
        self._check_model_status()
    
    def _check_model_status(self) -> None:
        """检查模型状态。"""
        if self.model_path.exists():
            # 模型存在，加载模型
            self._update_model_status("loading", "正在加载模型...")
            threading.Thread(target=self._load_model_async, daemon=True).start()
        else:
            # 模型不存在，显示下载按钮
            self._update_model_status("need_download", "需要下载模型才能使用")
    
    def _load_model_async(self) -> None:
        """异步加载模型。"""
        try:
            self.bg_remover = BackgroundRemover(self.model_path)
            self._on_model_loaded(True, None)
        except Exception as e:
            self._on_model_loaded(False, str(e))
    
    def _start_download_model(self, e: ft.ControlEvent = None) -> None:
        """开始下载模型文件。
        
        Args:
            e: 控件事件对象
        """
        if self.is_model_loading:
            return
        
        self.is_model_loading = True
        self._update_model_status("downloading", "正在下载模型（约350MB），请稍候...")
        
        # 显示下载进度条
        self.progress_bar.visible = True
        self.progress_bar.value = 0
        self.progress_text.visible = True
        self.progress_text.value = "准备下载..."
        try:
            self.progress_bar.update()
            self.progress_text.update()
        except:
            pass
        
        def download_task():
            try:
                import urllib.request
                
                # 下载文件并显示进度
                def report_progress(block_num, block_size, total_size):
                    downloaded = block_num * block_size
                    if total_size > 0:
                        percent = min(downloaded * 100 / total_size, 100)
                        progress = percent / 100
                        
                        # 格式化文件大小
                        downloaded_mb = downloaded / (1024 * 1024)
                        total_mb = total_size / (1024 * 1024)
                        
                        # 更新进度条和文本
                        self.progress_bar.value = progress
                        self.progress_text.value = f"下载中: {downloaded_mb:.1f}MB / {total_mb:.1f}MB ({percent:.1f}%)"
                        self.model_status_text.value = f"正在下载模型... {percent:.1f}%"
                        
                        try:
                            self.progress_bar.update()
                            self.progress_text.update()
                            self.model_status_text.update()
                        except:
                            pass
                
                urllib.request.urlretrieve(self.MODEL_URL, self.model_path, reporthook=report_progress)
                
                # 下载完成，隐藏进度条
                self.progress_bar.visible = False
                self.progress_text.visible = False
                try:
                    self.progress_bar.update()
                    self.progress_text.update()
                except:
                    pass
                
                # 加载模型
                self.bg_remover = BackgroundRemover(self.model_path)
                self._on_model_loaded(True, None)
            except Exception as e:
                # 下载失败，隐藏进度条
                self.progress_bar.visible = False
                self.progress_text.visible = False
                try:
                    self.progress_bar.update()
                    self.progress_text.update()
                except:
                    pass
                self._on_download_failed(str(e))
        
        threading.Thread(target=download_task, daemon=True).start()
    
    def _on_model_loaded(self, success: bool, error: Optional[str]) -> None:
        """模型加载完成回调。
        
        Args:
            success: 是否成功
            error: 错误信息
        """
        self.is_model_loading = False
        
        if success:
            self._update_model_status("ready", "模型就绪")
            self._update_process_button()
            self._show_snackbar("模型加载成功", ft.Colors.GREEN)
        else:
            self._update_model_status("error", f"模型加载失败: {error}")
            self._show_snackbar(f"模型加载失败: {error}", ft.Colors.RED)
    
    def _on_download_failed(self, error: str) -> None:
        """模型下载失败回调。
        
        Args:
            error: 错误信息
        """
        self.is_model_loading = False
        self._update_model_status("need_download", "下载失败，请重试")
        self._show_snackbar(f"模型下载失败: {error}", ft.Colors.RED)
        
        # 显示手动下载对话框
        self._show_manual_download_dialog(error)
    
    def _update_model_status(self, status: str, message: str) -> None:
        """更新模型状态显示。
        
        Args:
            status: 状态 ("loading", "downloading", "ready", "error", "need_download")
            message: 状态消息
        """
        if status == "loading":
            self.model_status_icon.name = ft.Icons.HOURGLASS_EMPTY
            self.model_status_icon.color = ft.Colors.BLUE
            self.download_model_button.visible = False
        elif status == "downloading":
            self.model_status_icon.name = ft.Icons.DOWNLOAD
            self.model_status_icon.color = ft.Colors.BLUE
            self.download_model_button.visible = False
        elif status == "ready":
            self.model_status_icon.name = ft.Icons.CHECK_CIRCLE
            self.model_status_icon.color = ft.Colors.GREEN
            self.download_model_button.visible = False
        elif status == "error":
            self.model_status_icon.name = ft.Icons.ERROR
            self.model_status_icon.color = ft.Colors.RED
            self.download_model_button.visible = False
        elif status == "need_download":
            self.model_status_icon.name = ft.Icons.WARNING
            self.model_status_icon.color = ft.Colors.ORANGE
            self.download_model_button.visible = True
        
        self.model_status_text.value = message
        
        # 只有控件已添加到页面时才更新
        try:
            self.model_status_icon.update()
            self.model_status_text.update()
            self.download_model_button.update()
        except:
            pass  # 控件还未添加到页面，忽略
    
    def _show_manual_download_dialog(self, error: str) -> None:
        """显示手动下载对话框。
        
        Args:
            error: 错误信息
        """
        def close_dialog(e: ft.ControlEvent) -> None:
            dialog.open = False
            self.page.update()
        
        def open_url_and_close(e: ft.ControlEvent) -> None:
            webbrowser.open(self.MODEL_URL)
            close_dialog(e)
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("自动下载失败"),
            content=ft.Column(
                controls=[
                    ft.Text(f"自动下载模型失败: {error}", color=ft.Colors.RED),
                    ft.Container(height=PADDING_MEDIUM),
                    ft.Text("请手动下载模型文件：", weight=ft.FontWeight.W_500),
                    ft.Container(height=PADDING_MEDIUM // 2),
                    ft.Text("1. 点击「打开下载链接」按钮"),
                    ft.Text("2. 在浏览器中下载模型文件 (model_q4.onnx)"),
                    ft.Text("3. 将下载的文件移动到以下位置："),
                    ft.Container(
                        content=ft.Text(
                            str(self.model_path),
                            size=11,
                            selectable=True,
                        ),
                        padding=PADDING_MEDIUM,
                        bgcolor=ft.Colors.SECONDARY_CONTAINER,
                        border_radius=BORDER_RADIUS_MEDIUM,
                    ),
                    ft.Container(height=PADDING_MEDIUM // 2),
                    ft.Text("4. 重新打开此界面即可使用", color=TEXT_SECONDARY, size=12),
                ],
                tight=True,
                spacing=PADDING_MEDIUM // 2,
            ),
            actions=[
                ft.TextButton("取消", on_click=close_dialog),
                ft.ElevatedButton("打开下载链接", icon=ft.Icons.OPEN_IN_BROWSER, on_click=open_url_and_close),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()
    
    def _on_back_click(self, e: ft.ControlEvent) -> None:
        """返回按钮点击事件。
        
        Args:
            e: 控件事件对象
        """
        if self.on_back:
            self.on_back()
    
    def _on_select_files(self, e: ft.ControlEvent) -> None:
        """选择文件按钮点击事件。
        
        Args:
            e: 控件事件对象
        """
        def on_result(result: ft.FilePickerResultEvent) -> None:
            if result.files:
                for file in result.files:
                    file_path = Path(file.path)
                    if file_path not in self.selected_files:
                        self.selected_files.append(file_path)
                
                self._update_file_list()
                self._update_process_button()
        
        picker: ft.FilePicker = ft.FilePicker(on_result=on_result)
        self.page.overlay.append(picker)
        self.page.update()
        
        picker.pick_files(
            dialog_title="选择图片文件",
            allowed_extensions=["jpg", "jpeg", "png", "bmp", "webp", "tiff", "gif"],
            allow_multiple=True,
        )
    
    def _on_select_folder(self, e: ft.ControlEvent) -> None:
        """选择文件夹按钮点击事件。
        
        Args:
            e: 控件事件对象
        """
        def on_result(result: ft.FilePickerResultEvent) -> None:
            if result.path:
                folder_path = Path(result.path)
                # 遍历文件夹中的所有图片文件
                image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff", ".tif", ".gif"}
                for file_path in folder_path.rglob("*"):
                    if file_path.is_file() and file_path.suffix.lower() in image_extensions:
                        if file_path not in self.selected_files:
                            self.selected_files.append(file_path)
                
                self._update_file_list()
                self._update_process_button()
                
                if self.selected_files:
                    self._show_snackbar(f"已添加 {len(self.selected_files)} 个文件", ft.Colors.GREEN)
        
        picker: ft.FilePicker = ft.FilePicker(on_result=on_result)
        self.page.overlay.append(picker)
        self.page.update()
        picker.get_directory_path(dialog_title="选择包含图片的文件夹")
    
    def _on_clear_files(self, e: ft.ControlEvent) -> None:
        """清空文件列表按钮点击事件。
        
        Args:
            e: 控件事件对象
        """
        self.selected_files.clear()
        self._update_file_list()
        self._update_process_button()
    
    def _update_file_list(self) -> None:
        """更新文件列表显示。"""
        self.file_list_view.controls.clear()
        
        if not self.selected_files:
            self.file_list_view.controls.append(
                ft.Text("还没有选择文件", color=TEXT_SECONDARY, italic=True)
            )
        else:
            for i, file_path in enumerate(self.selected_files):
                file_info = self.image_service.get_image_info(file_path)
                
                if 'error' in file_info:
                    info_text = f"错误: {file_info['error']}"
                    icon_color = ft.Colors.RED
                else:
                    size_str = format_file_size(file_info['file_size'])
                    info_text = f"{file_info['width']}×{file_info['height']} · {size_str}"
                    icon_color = ft.Colors.PRIMARY
                
                file_item: ft.Container = ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.IMAGE, size=20, color=icon_color),
                            ft.Column(
                                controls=[
                                    ft.Text(
                                        file_path.name,
                                        size=13,
                                        weight=ft.FontWeight.W_500,
                                        overflow=ft.TextOverflow.ELLIPSIS,
                                    ),
                                    ft.Text(info_text, size=11, color=TEXT_SECONDARY),
                                ],
                                spacing=2,
                                expand=True,
                            ),
                            ft.IconButton(
                                icon=ft.Icons.CLOSE,
                                icon_size=16,
                                tooltip="移除",
                                on_click=lambda e, idx=i: self._on_remove_file(idx),
                            ),
                        ],
                        spacing=PADDING_MEDIUM // 2,
                    ),
                    padding=PADDING_MEDIUM // 2,
                    border_radius=BORDER_RADIUS_MEDIUM,
                    bgcolor=ft.Colors.SECONDARY_CONTAINER,
                )
                
                self.file_list_view.controls.append(file_item)
        
        self.file_list_view.update()
    
    def _on_remove_file(self, index: int) -> None:
        """移除文件列表中的文件。
        
        Args:
            index: 文件索引
        """
        if 0 <= index < len(self.selected_files):
            self.selected_files.pop(index)
            self._update_file_list()
            self._update_process_button()
    
    def _on_output_mode_change(self, e: ft.ControlEvent) -> None:
        """输出模式改变事件。
        
        Args:
            e: 控件事件对象
        """
        is_custom = self.output_mode_radio.value == "custom"
        self.custom_output_dir.disabled = not is_custom
        self.browse_output_button.disabled = not is_custom
        self.custom_output_dir.update()
        self.browse_output_button.update()
    
    def _on_browse_output(self, e: ft.ControlEvent) -> None:
        """浏览输出目录按钮点击事件。
        
        Args:
            e: 控件事件对象
        """
        def on_result(result: ft.FilePickerResultEvent) -> None:
            if result.path:
                self.custom_output_dir.value = result.path
                self.custom_output_dir.update()
        
        picker: ft.FilePicker = ft.FilePicker(on_result=on_result)
        self.page.overlay.append(picker)
        self.page.update()
        picker.get_directory_path(dialog_title="选择输出目录")
    
    def _update_process_button(self) -> None:
        """更新处理按钮状态。"""
        # 只有当有文件且模型已加载时才启用按钮
        button = self.process_button.content
        button.disabled = not (self.selected_files and self.bg_remover)
        self.process_button.update()
    
    def _on_process(self, e: ft.ControlEvent) -> None:
        """开始处理按钮点击事件。
        
        Args:
            e: 控件事件对象
        """
        if not self.selected_files:
            self._show_snackbar("请先选择图片文件", ft.Colors.ORANGE)
            return
        
        if not self.bg_remover:
            self._show_snackbar("模型未加载，请稍候", ft.Colors.RED)
            return
        
        # 确定输出目录
        if self.output_mode_radio.value == "custom":
            output_dir = Path(self.custom_output_dir.value)
        else:
            output_dir = self.config_service.get_data_dir() / "background_removed"
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 禁用处理按钮
        button = self.process_button.content
        button.disabled = True
        self.process_button.update()
        
        # 显示进度
        self.progress_bar.visible = True
        self.progress_text.visible = True
        self.progress_bar.value = 0
        self.progress_text.value = "准备处理..."
        self.progress_bar.update()
        self.progress_text.update()
        
        # 在后台线程处理
        def process_task():
            total_files = len(self.selected_files)
            success_count = 0
            
            for i, file_path in enumerate(self.selected_files):
                try:
                    # 更新进度
                    progress = i / total_files
                    self._update_progress(progress, f"正在处理: {file_path.name} ({i+1}/{total_files})")
                    
                    # 读取图片
                    from PIL import Image
                    image = Image.open(file_path)
                    
                    # 移除背景
                    result = self.bg_remover.remove_background(image)
                    
                    # 生成输出文件名
                    if self.output_mode_radio.value == "new":
                        output_filename = f"{file_path.stem}_no_bg.png"
                        output_path = file_path.parent / output_filename
                    else:
                        output_filename = f"{file_path.stem}_no_bg.png"
                        output_path = output_dir / output_filename
                    
                    # 保存为PNG格式（保留透明通道）
                    result.save(output_path, "PNG", optimize=True)
                    
                    success_count += 1
                    
                except Exception as ex:
                    print(f"处理失败 {file_path.name}: {ex}")
            
            # 处理完成
            self._on_process_complete(success_count, total_files, output_dir)
        
        threading.Thread(target=process_task, daemon=True).start()
    
    def _update_progress(self, value: float, text: str) -> None:
        """更新进度显示。
        
        Args:
            value: 进度值 (0-1)
            text: 进度文本
        """
        self.progress_bar.value = value
        self.progress_text.value = text
        try:
            self.progress_bar.update()
            self.progress_text.update()
        except:
            pass
    
    def _on_process_complete(self, success_count: int, total: int, output_dir: Path) -> None:
        """处理完成回调。
        
        Args:
            success_count: 成功处理的数量
            total: 总数量
            output_dir: 输出目录
        """
        # 更新进度
        self.progress_bar.value = 1.0
        self.progress_text.value = f"处理完成! 成功: {success_count}/{total}"
        try:
            self.progress_bar.update()
            self.progress_text.update()
        except:
            pass
        
        # 显示成功消息
        if self.output_mode_radio.value == "new":
            self._show_snackbar(
                f"处理完成! 成功处理 {success_count} 个文件，保存在原文件旁边",
                ft.Colors.GREEN
            )
        else:
            self._show_snackbar(
                f"处理完成! 成功处理 {success_count} 个文件，保存到: {output_dir}",
                ft.Colors.GREEN
            )
        
        # 重新启用处理按钮
        button = self.process_button.content
        button.disabled = False
        try:
            self.process_button.update()
        except:
            pass
    
    def _show_snackbar(self, message: str, color: str) -> None:
        """显示提示消息。
        
        Args:
            message: 消息内容
            color: 消息颜色
        """
        snackbar: ft.SnackBar = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=color,
            duration=3000,
        )
        self.page.overlay.append(snackbar)
        snackbar.open = True
        try:
            self.page.update()
        except:
            pass
