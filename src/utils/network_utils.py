# -*- coding: utf-8 -*-
"""网络工具模块。

提供网络相关的工具函数，如代理检测、地区判断等。
"""

from dataclasses import dataclass
from typing import Optional

import httpx

from constants import GITHUB_PROXY_URL


# 缓存代理检测结果
_needs_proxy_cache: Optional[bool] = None

# 缓存 IP 地理位置信息
_location_cache: Optional["LocationInfo"] = None


@dataclass
class LocationInfo:
    """IP 地理位置信息。"""
    country_code: str = ""
    city: str = ""
    region: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None


def contains_cjk(text: str) -> bool:
    """检查字符串是否包含中日韩文字符。
    
    Args:
        text: 要检查的字符串
    
    Returns:
        是否包含 CJK 字符
    """
    if not text:
        return False
    try:
        return any('\u4e00' <= ch <= '\u9fff' for ch in text)
    except Exception:
        return False


def get_location_by_ip() -> Optional[LocationInfo]:
    """通过 IP 获取地理位置信息。
    
    会缓存结果，避免重复请求。
    
    Returns:
        LocationInfo 对象，失败返回 None
    """
    global _location_cache
    
    # 使用缓存
    if _location_cache is not None:
        return _location_cache
    
    # 尝试 ipapi.co
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(
                "https://ipapi.co/json/",
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                _location_cache = LocationInfo(
                    country_code=data.get("country_code", "").upper(),
                    city=data.get("city", ""),
                    region=data.get("region", ""),
                    latitude=data.get("latitude"),
                    longitude=data.get("longitude"),
                )
                return _location_cache
    except Exception:
        pass
    
    # 备用：ipwhois.app
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(
                "https://ipwhois.app/json/",
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    _location_cache = LocationInfo(
                        country_code=data.get("country_code", "").upper(),
                        city=data.get("city", ""),
                        region=data.get("region", ""),
                        latitude=data.get("latitude"),
                        longitude=data.get("longitude"),
                    )
                    return _location_cache
    except Exception:
        pass
    
    return None


def check_needs_proxy() -> bool:
    """检测是否需要使用代理（判断是否为中国大陆用户）。
    
    通过 IP 地理位置 API 获取用户所在地区，
    如果是中国大陆用户（country_code 为 CN），则需要代理。
    
    Returns:
        是否需要代理
    """
    global _needs_proxy_cache
    
    # 使用缓存结果
    if _needs_proxy_cache is not None:
        return _needs_proxy_cache
    
    # 默认不需要代理
    _needs_proxy_cache = False
    
    # 使用统一的位置获取函数
    location = get_location_by_ip()
    if location:
        # 如果是中国大陆用户，需要代理
        if location.country_code == "CN":
            _needs_proxy_cache = True
    else:
        # 如果获取地区信息失败，尝试通过访问 GitHub 来判断
        try:
            with httpx.Client(timeout=3.0) as client:
                client.head(
                    "https://api.github.com",
                    headers={"User-Agent": "MTools"}
                )
                # 能快速访问，不需要代理
                _needs_proxy_cache = False
        except Exception:
            # 无法访问 GitHub，需要代理
            _needs_proxy_cache = True
    
    return _needs_proxy_cache


def get_proxied_url(url: str) -> str:
    """将 GitHub 链接转换为代理加速链接。
    
    Args:
        url: 原始 GitHub 链接
    
    Returns:
        代理加速链接（如果需要代理），否则返回原链接
    """
    if not url:
        return url
    
    # 检查是否需要代理
    if not check_needs_proxy():
        return url
    
    # 检查是否是 GitHub 链接
    if "github.com" in url or "githubusercontent.com" in url:
        # 使用代理
        return f"{GITHUB_PROXY_URL}{url}"
    
    return url


def clear_location_cache() -> None:
    """清除所有缓存，下次会重新获取位置信息。"""
    global _needs_proxy_cache, _location_cache
    _needs_proxy_cache = None
    _location_cache = None

