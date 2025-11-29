# -*- coding: utf-8 -*-
"""视图模块。

提供应用程序的所有视图组件。
"""

from views.main_view import MainView
from views.settings_view import SettingsView
from views.recommendations_view import RecommendationsView
from views.image import ImageView
from views.media import MediaView
from views.dev_tools import DevToolsView

__all__ = [
    'MainView',
    'SettingsView',
    'ImageView',
    'MediaView',
    'DevToolsView',
]

