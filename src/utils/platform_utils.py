# -*- coding: utf-8 -*-
"""平台相关工具函数。"""

import sys
from typing import Tuple


def get_windows_version() -> Tuple[int, int, int]:
    """获取 Windows 版本号。
    
    Returns:
        (major, minor, build) 版本号元组，非 Windows 返回 (0, 0, 0)
    """
    if sys.platform != "win32":
        return (0, 0, 0)
    
    try:
        version = sys.getwindowsversion()
        return (version.major, version.minor, version.build)
    except Exception:
        return (0, 0, 0)


def is_windows() -> bool:
    """检查是否为 Windows 系统。"""
    return sys.platform == "win32"


def is_windows_10_or_later() -> bool:
    """检查是否为 Windows 10 或更高版本。
    
    Windows 10 和 Windows 11 的 major 版本号都是 10。
    """
    if not is_windows():
        return False
    
    major, _, _ = get_windows_version()
    return major >= 10


def is_windows_11() -> bool:
    """检查是否为 Windows 11。
    
    Windows 11 的版本号为 10.0.22000 及以上。
    """
    if not is_windows():
        return False
    
    major, _, build = get_windows_version()
    return major >= 10 and build >= 22000


def is_macos() -> bool:
    """检查是否为 macOS 系统。"""
    return sys.platform == "darwin"


def is_linux() -> bool:
    """检查是否为 Linux 系统。"""
    return sys.platform.startswith("linux")


def supports_file_drop() -> bool:
    """检查当前系统是否支持文件拖放功能。
    
    目前只支持 Windows 10/11。
    """
    return is_windows_10_or_later()

