# -*- coding: utf-8 -*-
"""AI证件照视图模块。

提供AI证件照生成功能的用户界面。
"""

import gc
import threading
import uuid
from pathlib import Path
from typing import Optional, List, Callable, Tuple, TYPE_CHECKING

import cv2
import numpy as np
from PIL import Image
import flet as ft

from constants import (
    BACKGROUND_REMOVAL_MODELS,
    FACE_DETECTION_MODELS,
    BORDER_RADIUS_MEDIUM,
    DEFAULT_MODEL_KEY,
    DEFAULT_FACE_DETECTION_MODEL_KEY,
    PADDING_LARGE,
    PADDING_MEDIUM,
    PADDING_SMALL,
)
from services import IDPhotoService, IDPhotoParams, IDPhotoResult
from utils import logger

if TYPE_CHECKING:
    from services.config_service import ConfigService


# 预设尺寸列表 (名称, 高度px, 宽度px)
PRESET_SIZES: List[tuple] = [
    ("一寸", 413, 295),
    ("二寸", 626, 413),
    ("小一寸", 378, 260),
    ("小二寸", 531, 413),
    ("大一寸", 567, 390),
    ("大二寸", 626, 413),
    ("五寸", 1499, 1050),
    ("教师资格证", 413, 295),
    ("国家公务员考试", 413, 295),
    ("初级会计考试", 413, 295),
    ("英语四六级考试", 192, 144),
    ("计算机等级考试", 567, 390),
    ("研究生考试", 709, 531),
    ("社保卡", 441, 358),
    ("电子驾驶证", 378, 260),
    ("美国签证", 600, 600),
    ("日本签证", 413, 295),
    ("韩国签证", 531, 413),
]

# 预设背景颜色
PRESET_COLORS: List[tuple] = [
    ("蓝色", (67, 142, 219)),
    ("白色", (255, 255, 255)),
    ("红色", (255, 0, 0)),
]


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """将 HEX 颜色转换为 RGB。"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


class IDPhotoView(ft.Container):
    """AI证件照视图类。"""

    def __init__(
        self,
        page: ft.Page,
        config_service: Optional['ConfigService'] = None,
        on_back: Optional[Callable] = None
    ) -> None:
        super().__init__()
        self.page: ft.Page = page
        self.config_service = config_service
        self.on_back: Optional[Callable] = on_back
        
        # 服务实例
        self.id_photo_service = IDPhotoService(config_service)
        
        # 状态变量
        self.selected_file: Optional[Path] = None
        self.is_processing: bool = False
        self.is_model_loading: bool = False
        
        # 当前选择的背景移除模型
        saved_bg_model = DEFAULT_MODEL_KEY
        if config_service:
            saved_bg_model = config_service.get_config_value("id_photo_bg_model", DEFAULT_MODEL_KEY)
        self.current_bg_model_key: str = saved_bg_model
        
        # 处理结果
        self.result: Optional[IDPhotoResult] = None
        self.result_temp_dir: Optional[Path] = None
        
        # 设置容器属性
        self.expand = True
        self.padding = ft.padding.only(
            left=PADDING_MEDIUM,
            right=PADDING_MEDIUM,
            top=PADDING_MEDIUM,
            bottom=PADDING_MEDIUM
        )
        
        self._ui_built: bool = False
        self._build_loading_ui()
        threading.Thread(target=self._build_ui_async, daemon=True).start()
    
    def _build_loading_ui(self) -> None:
        """构建加载界面。"""
        self.content = ft.Container(
            content=ft.Column(
                controls=[
                    ft.ProgressRing(),
                    ft.Text("正在加载AI证件照功能...", size=16, color=ft.Colors.ON_SURFACE_VARIANT),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=PADDING_LARGE,
            ),
            expand=True,
            alignment=ft.alignment.center,
        )
    
    def _build_ui_async(self) -> None:
        import time
        time.sleep(0.05)
        self._build_ui()
        self._ui_built = True
        try:
            self.update()
        except:
            pass
        threading.Thread(target=self._check_model_status_async, daemon=True).start()
    
    def _get_model_path(self, model_type: str, model_key: str = None) -> Path:
        """获取模型文件路径。"""
        if self.config_service:
            data_dir = self.config_service.get_data_dir()
        else:
            from utils.file_utils import get_app_root
            data_dir = get_app_root() / "storage" / "data"
        
        if model_type == "background":
            key = model_key or self.current_bg_model_key
            model_info = BACKGROUND_REMOVAL_MODELS[key]
            return data_dir / "models" / "background_removal" / model_info.version / model_info.filename
        elif model_type == "face":
            model_info = FACE_DETECTION_MODELS[DEFAULT_FACE_DETECTION_MODEL_KEY]
            return data_dir / "models" / "face_detection" / model_info.version / model_info.filename
        else:
            raise ValueError(f"未知模型类型: {model_type}")
    
    def _build_ui(self) -> None:
        """构建用户界面。"""
        # ==================== 顶部标题 ====================
        header = ft.Row(
            controls=[
                ft.IconButton(icon=ft.Icons.ARROW_BACK, tooltip="返回", on_click=self._on_back_click),
                ft.Text("AI证件照", size=28, weight=ft.FontWeight.BOLD),
            ],
            spacing=PADDING_MEDIUM,
        )
        
        # ==================== 图片选择和结果预览 ====================
        # 左侧：选择照片
        self.image_preview = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Icon(ft.Icons.ADD_PHOTO_ALTERNATE_OUTLINED, size=64, color=ft.Colors.ON_SURFACE_VARIANT),
                    ft.Text("点击选择照片", size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                    ft.Text("支持 JPG、PNG、WebP、BMP、TIFF、HEIC 等格式", size=11, color=ft.Colors.OUTLINE),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=8,
            ),
            width=280,
            height=480,
            bgcolor=ft.Colors.with_opacity(0.04, ft.Colors.ON_SURFACE),
            border_radius=BORDER_RADIUS_MEDIUM,
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            alignment=ft.alignment.center,
            on_click=self._on_select_file,
            ink=True,
        )
        
        self.clear_file_btn = ft.TextButton("清空照片", icon=ft.Icons.CLEAR, on_click=self._on_clear_file, visible=False)
        
        # 右侧上方：标准照和高清照（横向并排）
        self.standard_preview = self._create_result_card("标准照", 170, 220)
        self.hd_preview = self._create_result_card("高清照", 170, 220)
        
        self.standard_save_btn = ft.IconButton(ft.Icons.SAVE_ALT, tooltip="保存标准照", on_click=lambda _: self._save_result("standard"), disabled=True, icon_size=18)
        self.hd_save_btn = ft.IconButton(ft.Icons.SAVE_ALT, tooltip="保存高清照", on_click=lambda _: self._save_result("hd"), disabled=True, icon_size=18)
        
        # 右侧下方：排版照
        self.layout_preview = self._create_result_card("排版照（六寸）", 380, 240)
        self.layout_save_btn = ft.IconButton(ft.Icons.SAVE_ALT, tooltip="保存排版照", on_click=lambda _: self._save_result("layout"), disabled=True, icon_size=18)
        
        # 右侧整体布局
        right_panel = ft.Column(
            controls=[
                ft.Text("生成结果:", size=14, weight=ft.FontWeight.W_500),
                ft.Container(height=PADDING_SMALL // 2),
                # 上方：标准照和高清照横向并排
                ft.Row(
                    controls=[
                        ft.Column([self.standard_preview, self.standard_save_btn], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4),
                        ft.Column([self.hd_preview, self.hd_save_btn], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4),
                    ],
                    spacing=PADDING_MEDIUM,
                    alignment=ft.MainAxisAlignment.START,
                ),
                ft.Container(height=PADDING_SMALL),
                # 下方：排版照
                ft.Column([self.layout_preview, self.layout_save_btn], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4),
            ],
            spacing=0,
        )
        
        # 图片区域：左右布局
        image_area = ft.Row(
            controls=[
                # 左侧：原始照片
                ft.Column(
                    controls=[
                        ft.Text("原始照片:", size=14, weight=ft.FontWeight.W_500),
                        self.image_preview,
                        self.clear_file_btn,
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=PADDING_SMALL,
                ),
                # 右侧：结果预览
                right_panel,
            ],
            spacing=PADDING_LARGE,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )
        
        # ==================== 模型管理区域 ====================
        # 背景移除模型选择
        bg_model_options = []
        for key, model in BACKGROUND_REMOVAL_MODELS.items():
            size_text = f"{model.size_mb}MB" if model.size_mb < 100 else f"{model.size_mb}MB"
            option_text = f"{model.display_name}  |  {size_text}"
            bg_model_options.append(ft.dropdown.Option(key=key, text=option_text))
        
        self.bg_model_selector = ft.Dropdown(
            options=bg_model_options,
            value=self.current_bg_model_key,
            label="背景移除模型",
            hint_text="选择背景移除模型",
            on_change=self._on_bg_model_change,
            width=320,
            dense=True,
            text_size=13,
        )
        
        self.bg_model_info = ft.Text(
            f"质量: {BACKGROUND_REMOVAL_MODELS[self.current_bg_model_key].quality} | 性能: {BACKGROUND_REMOVAL_MODELS[self.current_bg_model_key].performance}",
            size=11,
            color=ft.Colors.ON_SURFACE_VARIANT,
        )
        
        # 背景模型状态
        self.bg_status_icon = ft.Icon(ft.Icons.HOURGLASS_EMPTY, size=20, color=ft.Colors.ON_SURFACE_VARIANT)
        self.bg_status_text = ft.Text("正在检查模型...", size=13, color=ft.Colors.ON_SURFACE_VARIANT)
        self.download_bg_btn = ft.ElevatedButton("下载模型", icon=ft.Icons.DOWNLOAD, on_click=lambda _: self._start_download_model("background"), visible=False)
        self.load_bg_btn = ft.ElevatedButton("加载模型", icon=ft.Icons.PLAY_ARROW, on_click=lambda _: self._on_load_model("background"), visible=False)
        self.unload_bg_btn = ft.IconButton(icon=ft.Icons.POWER_SETTINGS_NEW, icon_color=ft.Colors.ORANGE, tooltip="卸载模型", on_click=lambda _: self._on_unload_model("background"), visible=False)
        
        bg_status_row = ft.Row(
            controls=[self.bg_status_icon, self.bg_status_text, self.download_bg_btn, self.load_bg_btn, self.unload_bg_btn],
            spacing=PADDING_SMALL,
        )
        
        # 人脸检测模型
        face_info = FACE_DETECTION_MODELS[DEFAULT_FACE_DETECTION_MODEL_KEY]
        self.face_model_text = ft.Text(f"人脸检测模型: {face_info.display_name}", size=13)
        self.face_status_icon = ft.Icon(ft.Icons.HOURGLASS_EMPTY, size=20, color=ft.Colors.ON_SURFACE_VARIANT)
        self.face_status_text = ft.Text("正在检查模型...", size=13, color=ft.Colors.ON_SURFACE_VARIANT)
        self.download_face_btn = ft.ElevatedButton(f"下载模型 ({face_info.size_mb}MB)", icon=ft.Icons.DOWNLOAD, on_click=lambda _: self._start_download_model("face"), visible=False)
        self.load_face_btn = ft.ElevatedButton("加载模型", icon=ft.Icons.PLAY_ARROW, on_click=lambda _: self._on_load_model("face"), visible=False)
        self.unload_face_btn = ft.IconButton(icon=ft.Icons.POWER_SETTINGS_NEW, icon_color=ft.Colors.ORANGE, tooltip="卸载模型", on_click=lambda _: self._on_unload_model("face"), visible=False)
        
        face_status_row = ft.Row(
            controls=[self.face_status_icon, self.face_status_text, self.download_face_btn, self.load_face_btn, self.unload_face_btn],
            spacing=PADDING_SMALL,
        )
        
        # 自动加载选项
        auto_load = True
        if self.config_service:
            auto_load = self.config_service.get_config_value("id_photo_auto_load_model", True)
        self.auto_load_checkbox = ft.Checkbox(
            label="自动加载模型",
            value=auto_load,
            on_change=self._on_auto_load_change,
        )
        
        model_area = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("模型管理:", size=14, weight=ft.FontWeight.W_500),
                    self.bg_model_selector,
                    self.bg_model_info,
                    ft.Container(height=PADDING_SMALL // 2),
                    bg_status_row,
                    ft.Container(height=PADDING_MEDIUM),
                    self.face_model_text,
                    ft.Container(height=PADDING_SMALL // 2),
                    face_status_row,
                    ft.Container(height=PADDING_SMALL),
                    self.auto_load_checkbox,
                ],
                spacing=PADDING_SMALL,
            ),
            padding=PADDING_MEDIUM,
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=BORDER_RADIUS_MEDIUM,
        )
        
        # ==================== 参数设置区域 ====================
        # 尺寸设置
        self.size_mode_radio = ft.RadioGroup(
            content=ft.Column(
                controls=[
                    ft.Radio(value="preset", label="预设尺寸"),
                    ft.Radio(value="custom", label="自定义尺寸"),
                    ft.Radio(value="only_matting", label="仅换底色"),
                ],
                spacing=PADDING_SMALL // 2,
            ),
            value="preset",
            on_change=self._on_size_mode_change,
        )
        
        self.preset_size_dropdown = ft.Dropdown(
            options=[ft.dropdown.Option(text=f"{name} ({w}×{h})", key=name) for name, h, w in PRESET_SIZES],
            value="一寸",
            dense=True,
            width=200,
            text_size=12,
        )
        
        self.custom_width = ft.TextField(label="宽(px)", value="295", width=90, dense=True, text_size=12)
        self.custom_height = ft.TextField(label="高(px)", value="413", width=90, dense=True, text_size=12)
        self.custom_size_row = ft.Row([self.custom_width, self.custom_height], spacing=PADDING_SMALL, visible=False)
        
        size_section = ft.Column(
            controls=[
                ft.Text("尺寸规格:", size=14, weight=ft.FontWeight.W_500),
                self.size_mode_radio,
                self.preset_size_dropdown,
                self.custom_size_row,
            ],
            spacing=PADDING_SMALL,
        )
        
        # 背景设置
        self.bg_color_radio = ft.RadioGroup(
            content=ft.Row(
                controls=[
                    ft.Radio(value="蓝色", label="蓝色"),
                    ft.Radio(value="白色", label="白色"),
                    ft.Radio(value="红色", label="红色"),
                    ft.Radio(value="custom", label="自定义"),
                ],
                spacing=PADDING_SMALL,
            ),
            value="蓝色",
            on_change=self._on_bg_color_change,
        )
        
        self.custom_color_input = ft.TextField(label="HEX颜色", value="438edb", prefix_text="#", width=120, dense=True, text_size=12, visible=False)
        
        self.render_mode_dropdown = ft.Dropdown(
            label="渲染模式",
            options=[
                ft.dropdown.Option("solid", "纯色"),
                ft.dropdown.Option("gradient_up", "向上渐变"),
                ft.dropdown.Option("gradient_down", "向下渐变"),
            ],
            value="solid",
            dense=True,
            width=140,
            text_size=12,
        )
        
        bg_section = ft.Column(
            controls=[
                ft.Text("背景设置:", size=14, weight=ft.FontWeight.W_500),
                self.bg_color_radio,
                ft.Row([self.custom_color_input, self.render_mode_dropdown], spacing=PADDING_MEDIUM),
            ],
            spacing=PADDING_SMALL,
        )
        
        # 美颜和其他选项
        self.whitening_slider = ft.Slider(min=0, max=15, value=2, divisions=15, label="{value}", width=180)
        self.brightness_slider = ft.Slider(min=-5, max=25, value=0, divisions=30, label="{value}", width=180)
        self.face_alignment_checkbox = ft.Checkbox(label="自动矫正人脸", value=False)
        self.layout_checkbox = ft.Checkbox(label="生成排版照（六寸）", value=True)
        
        beauty_section = ft.Column(
            controls=[
                ft.Text("美颜和选项:", size=14, weight=ft.FontWeight.W_500),
                ft.Row([ft.Text("美白强度", size=12, width=60), self.whitening_slider], spacing=PADDING_SMALL),
                ft.Row([ft.Text("亮度调整", size=12, width=60), self.brightness_slider], spacing=PADDING_SMALL),
                self.face_alignment_checkbox,
                self.layout_checkbox,
            ],
            spacing=PADDING_SMALL,
        )
        
        # 参数设置区域布局
        settings_area = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(content=size_section, expand=True),
                    ft.Container(content=bg_section, expand=True),
                    ft.Container(content=beauty_section, expand=True),
                ],
                spacing=PADDING_LARGE,
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
            padding=PADDING_MEDIUM,
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=BORDER_RADIUS_MEDIUM,
        )
        
        # ==================== 进度和生成按钮 ====================
        self.progress_bar = ft.ProgressBar(value=0, visible=False)
        self.progress_text = ft.Text("", size=12, color=ft.Colors.ON_SURFACE_VARIANT, visible=False)
        
        progress_container = ft.Container(
            content=ft.Column(
                controls=[self.progress_bar, self.progress_text],
                spacing=PADDING_SMALL // 2,
            ),
        )
        
        self.generate_button = ft.ElevatedButton(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.AUTO_AWESOME, size=20),
                    ft.Text("生成证件照", size=16, weight=ft.FontWeight.W_600),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=PADDING_SMALL,
            ),
            on_click=self._on_generate_click,
            disabled=True,
            style=ft.ButtonStyle(
                padding=ft.padding.symmetric(horizontal=PADDING_LARGE * 2, vertical=PADDING_MEDIUM),
                shape=ft.RoundedRectangleBorder(radius=BORDER_RADIUS_MEDIUM),
            ),
        )
        
        # ==================== 组装界面 ====================
        # 可滚动内容区域
        scrollable_content = ft.Column(
            controls=[
                image_area,
                ft.Container(height=PADDING_MEDIUM),
                model_area,
                ft.Container(height=PADDING_MEDIUM),
                settings_area,
                ft.Container(height=PADDING_LARGE),
                progress_container,
                ft.Container(height=PADDING_MEDIUM),
                ft.Container(
                    content=self.generate_button,
                    alignment=ft.alignment.center,
                ),
                ft.Container(height=PADDING_LARGE),  # 底部间距
            ],
            spacing=0,
            scroll=ft.ScrollMode.ADAPTIVE,
            expand=True,
        )
        
        # 组装主界面 - 标题固定，分隔线固定，内容可滚动
        self.content = ft.Column(
            controls=[
                header,  # 固定在顶部
                ft.Divider(),  # 固定的分隔线
                scrollable_content,  # 可滚动内容
            ],
            spacing=0,
        )
    
    def _create_result_card(self, label: str, width: int, height: int) -> ft.Container:
        """创建结果预览卡片。"""
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Icon(ft.Icons.IMAGE_OUTLINED, size=32, color=ft.Colors.ON_SURFACE_VARIANT),
                    ft.Text(label, size=11, color=ft.Colors.ON_SURFACE_VARIANT, text_align=ft.TextAlign.CENTER),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=PADDING_SMALL,
            ),
            width=width,
            height=height,
            bgcolor=ft.Colors.with_opacity(0.02, ft.Colors.ON_SURFACE),
            border_radius=BORDER_RADIUS_MEDIUM,
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            alignment=ft.alignment.center,
        )
    
    # ==================== 模型管理 ====================
    
    def _check_model_status_async(self) -> None:
        import time
        time.sleep(0.05)
        self._check_model_status()
    
    def _check_model_status(self) -> None:
        """检查模型状态。"""
        bg_exists = self._get_model_path("background").exists()
        face_exists = self._get_model_path("face").exists()
        
        # 背景模型状态
        bg_loaded = self.id_photo_service.is_background_model_loaded()
        if bg_loaded:
            self.bg_status_icon.name = ft.Icons.CHECK_CIRCLE
            self.bg_status_icon.color = ft.Colors.GREEN
            self.bg_status_text.value = "模型已加载"
            self.bg_status_text.color = ft.Colors.GREEN
            self.download_bg_btn.visible = False
            self.load_bg_btn.visible = False
            self.unload_bg_btn.visible = True
        elif bg_exists:
            self.bg_status_icon.name = ft.Icons.DOWNLOAD_DONE
            self.bg_status_icon.color = ft.Colors.BLUE
            self.bg_status_text.value = "模型已下载，需加载"
            self.bg_status_text.color = ft.Colors.BLUE
            self.download_bg_btn.visible = False
            self.load_bg_btn.visible = True
            self.unload_bg_btn.visible = False
        else:
            self.bg_status_icon.name = ft.Icons.CLOUD_DOWNLOAD
            self.bg_status_icon.color = ft.Colors.ORANGE
            self.bg_status_text.value = "需要下载模型"
            self.bg_status_text.color = ft.Colors.ORANGE
            self.download_bg_btn.visible = True
            self.load_bg_btn.visible = False
            self.unload_bg_btn.visible = False
        
        # 人脸模型状态
        face_loaded = self.id_photo_service.is_face_model_loaded()
        if face_loaded:
            self.face_status_icon.name = ft.Icons.CHECK_CIRCLE
            self.face_status_icon.color = ft.Colors.GREEN
            self.face_status_text.value = "模型已加载"
            self.face_status_text.color = ft.Colors.GREEN
            self.download_face_btn.visible = False
            self.load_face_btn.visible = False
            self.unload_face_btn.visible = True
        elif face_exists:
            self.face_status_icon.name = ft.Icons.DOWNLOAD_DONE
            self.face_status_icon.color = ft.Colors.BLUE
            self.face_status_text.value = "模型已下载，需加载"
            self.face_status_text.color = ft.Colors.BLUE
            self.download_face_btn.visible = False
            self.load_face_btn.visible = True
            self.unload_face_btn.visible = False
        else:
            self.face_status_icon.name = ft.Icons.CLOUD_DOWNLOAD
            self.face_status_icon.color = ft.Colors.ORANGE
            self.face_status_text.value = "需要下载模型"
            self.face_status_text.color = ft.Colors.ORANGE
            self.download_face_btn.visible = True
            self.load_face_btn.visible = False
            self.unload_face_btn.visible = False
        
        # 自动加载
        if bg_exists and face_exists and not bg_loaded and not face_loaded:
            if self.auto_load_checkbox.value:
                self._on_load_model("both")
        
        self._update_generate_button()
        self._safe_update()
    
    def _on_bg_model_change(self, e: ft.ControlEvent) -> None:
        """背景模型选择变化。"""
        new_key = e.control.value
        if new_key == self.current_bg_model_key:
            return
        
        if self.id_photo_service.is_background_model_loaded():
            self.id_photo_service.unload_background_model()
        
        self.current_bg_model_key = new_key
        if self.config_service:
            self.config_service.set_config_value("id_photo_bg_model", new_key)
        
        # 更新模型信息
        model = BACKGROUND_REMOVAL_MODELS[new_key]
        self.bg_model_info.value = f"质量: {model.quality} | 性能: {model.performance}"
        
        self._check_model_status()
    
    def _start_download_model(self, model_type: str) -> None:
        """开始下载模型。"""
        if self.is_model_loading:
            return
        
        self.is_model_loading = True
        
        if model_type == "background":
            model_info = BACKGROUND_REMOVAL_MODELS[self.current_bg_model_key]
            model_path = self._get_model_path("background")
        else:
            model_info = FACE_DETECTION_MODELS[DEFAULT_FACE_DETECTION_MODEL_KEY]
            model_path = self._get_model_path("face")
        
        self.progress_text.value = f"正在下载 {model_info.display_name}..."
        self.progress_text.visible = True
        self.progress_bar.visible = True
        self.progress_bar.value = 0
        self._safe_update()
        
        def download_task():
            try:
                import httpx
                model_path.parent.mkdir(parents=True, exist_ok=True)
                
                with httpx.stream("GET", model_info.url, follow_redirects=True, timeout=120.0) as response:
                    response.raise_for_status()
                    total_size = int(response.headers.get('content-length', 0))
                    downloaded = 0
                    
                    with open(model_path, 'wb') as f:
                        for chunk in response.iter_bytes(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                                if total_size > 0:
                                    self.progress_bar.value = downloaded / total_size
                                    self.progress_text.value = f"下载中: {downloaded / 1024 / 1024:.1f} / {total_size / 1024 / 1024:.1f} MB"
                                    self._safe_update()
                
                self.progress_bar.visible = False
                self.progress_text.visible = False
                self.is_model_loading = False
                self._show_snackbar(f"{model_info.display_name} 下载完成", ft.Colors.GREEN)
                self._check_model_status()
                
            except Exception as e:
                self.progress_bar.visible = False
                self.progress_text.visible = False
                self.is_model_loading = False
                self._show_snackbar(f"下载失败: {e}", ft.Colors.RED)
                self._check_model_status()
        
        threading.Thread(target=download_task, daemon=True).start()
    
    def _on_load_model(self, model_type: str, e: ft.ControlEvent = None) -> None:
        """加载模型。"""
        if self.is_model_loading:
            return
        
        self.is_model_loading = True
        self.progress_text.value = "正在加载模型..."
        self.progress_text.visible = True
        self._safe_update()
        
        def load_task():
            try:
                if model_type in ["background", "both"]:
                    bg_path = self._get_model_path("background")
                    if bg_path.exists() and not self.id_photo_service.is_background_model_loaded():
                        self.id_photo_service.load_background_model(self.current_bg_model_key)
                
                if model_type in ["face", "both"]:
                    face_path = self._get_model_path("face")
                    if face_path.exists() and not self.id_photo_service.is_face_model_loaded():
                        self.id_photo_service.load_face_model()
                
                self.is_model_loading = False
                self.progress_text.visible = False
                self._show_snackbar("模型加载成功", ft.Colors.GREEN)
                self._check_model_status()
                
            except Exception as ex:
                self.is_model_loading = False
                self.progress_text.visible = False
                self._show_snackbar(f"模型加载失败: {ex}", ft.Colors.RED)
                self._check_model_status()
        
        threading.Thread(target=load_task, daemon=True).start()
    
    def _on_unload_model(self, model_type: str, e: ft.ControlEvent = None) -> None:
        """卸载模型。"""
        if model_type == "background":
            self.id_photo_service.unload_background_model()
        elif model_type == "face":
            self.id_photo_service.unload_face_model()
        
        self._show_snackbar("模型已卸载", ft.Colors.GREEN)
        self._check_model_status()
    
    def _on_auto_load_change(self, e: ft.ControlEvent) -> None:
        """自动加载选项变化。"""
        if self.config_service:
            self.config_service.set_config_value("id_photo_auto_load_model", e.control.value)
    
    # ==================== 文件操作 ====================
    
    def _on_select_file(self, e: ft.ControlEvent = None) -> None:
        """选择文件。"""
        def on_result(result: ft.FilePickerResultEvent) -> None:
            if result.files and len(result.files) > 0:
                self.selected_file = Path(result.files[0].path)
                self._update_image_preview()
                self._update_generate_button()
        
        picker = ft.FilePicker(on_result=on_result)
        self.page.overlay.append(picker)
        self.page.update()
        picker.pick_files(
            dialog_title="选择人像照片",
            allowed_extensions=["jpg", "jpeg", "png", "webp", "bmp", "tiff", "tif", "heic", "heif"],
            allow_multiple=False,
        )
    
    def _on_clear_file(self, e: ft.ControlEvent = None) -> None:
        """清空文件。"""
        self.selected_file = None
        self._update_image_preview()
        self._update_generate_button()
    
    def _update_image_preview(self) -> None:
        """更新图片预览。"""
        if self.selected_file and self.selected_file.exists():
            self.image_preview.content = ft.Image(
                src=str(self.selected_file),
                width=280,
                height=480,
                fit=ft.ImageFit.CONTAIN,
                border_radius=BORDER_RADIUS_MEDIUM,
            )
            self.clear_file_btn.visible = True
        else:
            self.image_preview.content = ft.Column(
                controls=[
                    ft.Icon(ft.Icons.ADD_PHOTO_ALTERNATE_OUTLINED, size=64, color=ft.Colors.ON_SURFACE_VARIANT),
                    ft.Text("点击选择照片", size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                    ft.Text("支持 JPG、PNG、WebP、BMP、TIFF、HEIC 等格式", size=11, color=ft.Colors.OUTLINE),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=8,
            )
            self.clear_file_btn.visible = False
        self._safe_update()
    
    # ==================== 参数变更 ====================
    
    def _on_size_mode_change(self, e: ft.ControlEvent) -> None:
        mode = e.control.value
        self.preset_size_dropdown.visible = (mode == "preset")
        self.custom_size_row.visible = (mode == "custom")
        self._safe_update()
    
    def _on_bg_color_change(self, e: ft.ControlEvent) -> None:
        self.custom_color_input.visible = (e.control.value == "custom")
        self._safe_update()
    
    def _on_back_click(self, e: ft.ControlEvent) -> None:
        if self.on_back:
            self.on_back()
    
    # ==================== 生成证件照 ====================
    
    def _update_generate_button(self) -> None:
        """更新生成按钮状态。"""
        models_ready = (
            self.id_photo_service.is_background_model_loaded() and 
            self.id_photo_service.is_face_model_loaded()
        )
        self.generate_button.disabled = not (self.selected_file and models_ready)
        self._safe_update()
    
    def _get_params(self) -> Tuple[IDPhotoParams, Tuple[int, int, int], str]:
        """获取当前参数。"""
        size_mode = self.size_mode_radio.value
        if size_mode == "preset":
            preset_name = self.preset_size_dropdown.value
            name_only = preset_name.split(" ")[0] if " " in preset_name else preset_name
            size = next((h, w) for name, h, w in PRESET_SIZES if name == name_only)
        elif size_mode == "custom":
            try:
                width = int(self.custom_width.value)
                height = int(self.custom_height.value)
                size = (height, width)
            except ValueError:
                size = (413, 295)
        else:
            size = (413, 295)
        
        bg_color_name = self.bg_color_radio.value
        if bg_color_name == "custom":
            try:
                bg_color = hex_to_rgb(self.custom_color_input.value)
            except:
                bg_color = (67, 142, 219)
        else:
            bg_color = next((c for name, c in PRESET_COLORS if name == bg_color_name), (67, 142, 219))
        
        render_mode = self.render_mode_dropdown.value or "solid"
        
        params = IDPhotoParams(
            size=size,
            change_bg_only=(size_mode == "only_matting"),
            head_measure_ratio=0.2,
            head_height_ratio=0.45,
            head_top_range=(0.12, 0.10),
            whitening_strength=int(self.whitening_slider.value),
            brightness_strength=int(self.brightness_slider.value),
            face_alignment=self.face_alignment_checkbox.value,
        )
        
        return params, bg_color, render_mode
    
    def _on_generate_click(self, e: ft.ControlEvent) -> None:
        """生成证件照。"""
        if not self.selected_file or self.is_processing:
            return
        
        self.is_processing = True
        self.generate_button.disabled = True
        self.progress_text.value = "正在处理..."
        self.progress_text.visible = True
        self.progress_bar.visible = True
        self.progress_bar.value = 0
        self._safe_update()
        
        params, bg_color, render_mode = self._get_params()
        generate_layout = self.layout_checkbox.value
        
        def process_task():
            try:
                # 检查文件是否存在
                if not self.selected_file.exists():
                    raise ValueError(f"文件不存在: {self.selected_file}")
                
                # 检查是否是 HEIC/HEIF 格式，需要先转换
                file_ext = self.selected_file.suffix.lower()
                if file_ext in ['.heic', '.heif']:
                    try:
                        # 使用 PIL 读取 HEIC/HEIF
                        from PIL import Image as PILImage
                        pil_image = PILImage.open(self.selected_file)
                        # 转换为 RGB
                        if pil_image.mode != 'RGB':
                            pil_image = pil_image.convert('RGB')
                        # 转换为 numpy 数组
                        image = np.array(pil_image)
                        # 转换为 BGR（OpenCV 格式）
                        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
                    except Exception as heic_error:
                        raise ValueError(f"无法读取 HEIC/HEIF 格式图片，请安装 pillow-heif 库或使用其他格式: {heic_error}")
                else:
                    # 使用 numpy 和 cv2.imdecode 来支持中文路径
                    # cv2.imread 在 Windows 上不支持 Unicode 路径
                    # 读取文件为字节流
                    with open(self.selected_file, 'rb') as f:
                        file_data = f.read()
                    
                    # 转换为numpy数组
                    file_array = np.frombuffer(file_data, dtype=np.uint8)
                    
                    # 使用cv2.imdecode解码图像
                    image = cv2.imdecode(file_array, cv2.IMREAD_COLOR)
                
                if image is None:
                    raise ValueError("无法读取图片文件，请检查文件格式是否正确")
                
                def progress_callback(value: float, message: str):
                    self.progress_bar.value = value
                    self.progress_text.value = message
                    self._safe_update()
                
                result = self.id_photo_service.process(
                    image=image,
                    params=params,
                    bg_color=bg_color,
                    render_mode=render_mode,
                    generate_layout=generate_layout,
                    progress_callback=progress_callback,
                )
                
                self.result = result
                self._on_process_complete(True, None)
                
            except Exception as ex:
                logger.error(f"证件照生成失败: {ex}")
                self._on_process_complete(False, str(ex))
        
        threading.Thread(target=process_task, daemon=True).start()
    
    def _on_process_complete(self, success: bool, error: Optional[str]) -> None:
        """处理完成。"""
        self.is_processing = False
        self.generate_button.disabled = False
        self.progress_bar.visible = False
        
        if success:
            self.progress_text.value = "✓ 生成完成"
            self._update_result_preview()
            self._show_snackbar("证件照生成成功！", ft.Colors.GREEN)
        else:
            self.progress_text.value = f"✗ 失败: {error}"
            self._show_snackbar(f"生成失败: {error}", ft.Colors.RED)
        
        self._safe_update()
    
    def _update_result_preview(self) -> None:
        """更新结果预览。"""
        if not self.result:
            return
        
        if self.config_service:
            temp_dir = self.config_service.get_temp_dir()
        else:
            from utils.file_utils import get_app_root
            temp_dir = get_app_root() / "storage" / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        self.result_temp_dir = temp_dir
        
        session_id = str(uuid.uuid4())[:8]
        
        # 标准照 - 使用 imencode 支持中文路径
        standard_path = temp_dir / f"id_standard_{session_id}.png"
        is_success, buffer = cv2.imencode('.png', self.result.standard)
        if is_success:
            with open(standard_path, 'wb') as f:
                f.write(buffer)
            self.standard_preview.content = ft.Image(
                src=str(standard_path), width=170, height=220, fit=ft.ImageFit.CONTAIN, border_radius=BORDER_RADIUS_MEDIUM
            )
            self.standard_save_btn.disabled = False
        
        # 高清照 - 使用 imencode 支持中文路径
        hd_path = temp_dir / f"id_hd_{session_id}.png"
        is_success, buffer = cv2.imencode('.png', self.result.hd)
        if is_success:
            with open(hd_path, 'wb') as f:
                f.write(buffer)
            self.hd_preview.content = ft.Image(
                src=str(hd_path), width=170, height=220, fit=ft.ImageFit.CONTAIN, border_radius=BORDER_RADIUS_MEDIUM
            )
            self.hd_save_btn.disabled = False
        
        # 排版照 - 使用 imencode 支持中文路径
        if self.result.layout is not None:
            layout_path = temp_dir / f"id_layout_{session_id}.png"
            is_success, buffer = cv2.imencode('.png', self.result.layout)
            if is_success:
                with open(layout_path, 'wb') as f:
                    f.write(buffer)
                self.layout_preview.content = ft.Image(
                    src=str(layout_path), width=380, height=240, fit=ft.ImageFit.CONTAIN, border_radius=BORDER_RADIUS_MEDIUM
                )
                self.layout_save_btn.disabled = False
        else:
            self.layout_save_btn.disabled = True
        
        self._safe_update()
    
    def _save_result(self, result_type: str) -> None:
        """保存结果。"""
        if not self.result:
            return
        
        def on_result(result: ft.FilePickerResultEvent) -> None:
            if result.path:
                try:
                    # 使用 cv2.imencode 支持中文路径
                    if result_type == "standard":
                        is_success, buffer = cv2.imencode('.png', self.result.standard)
                    elif result_type == "hd":
                        is_success, buffer = cv2.imencode('.png', self.result.hd)
                    elif result_type == "layout" and self.result.layout is not None:
                        is_success, buffer = cv2.imencode('.png', self.result.layout)
                    else:
                        is_success = False
                    
                    if is_success:
                        with open(result.path, 'wb') as f:
                            f.write(buffer)
                        self._show_snackbar(f"保存成功", ft.Colors.GREEN)
                    else:
                        self._show_snackbar(f"保存失败：编码图像失败", ft.Colors.RED)
                except Exception as ex:
                    self._show_snackbar(f"保存失败: {ex}", ft.Colors.RED)
        
        picker = ft.FilePicker(on_result=on_result)
        self.page.overlay.append(picker)
        self.page.update()
        
        base_name = self.selected_file.stem if self.selected_file else "id_photo"
        picker.save_file(
            dialog_title=f"保存{result_type}照",
            file_name=f"{base_name}_{result_type}.png",
            allowed_extensions=["png"],
        )
    
    # ==================== 工具方法 ====================
    
    def _safe_update(self) -> None:
        """安全更新UI。"""
        try:
            self.update()
        except:
            pass
    
    def _show_snackbar(self, message: str, color: str = None) -> None:
        """显示提示消息。"""
        snackbar = ft.SnackBar(content=ft.Text(message), bgcolor=color, duration=3000)
        self.page.overlay.append(snackbar)
        snackbar.open = True
        try:
            self.page.update()
        except:
            pass
