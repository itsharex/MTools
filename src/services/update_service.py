# -*- coding: utf-8 -*-
"""更新检测服务模块。

提供应用版本检测和更新功能。
"""

import platform
import re
from dataclasses import dataclass
from typing import Optional, Tuple
from enum import Enum

import httpx

from constants import APP_VERSION, GITHUB_API_URL, GITHUB_RELEASES_URL
from utils import get_proxied_url


class UpdateStatus(Enum):
    """更新状态枚举。"""
    CHECKING = "checking"           # 正在检查
    UP_TO_DATE = "up_to_date"       # 已是最新版本
    UPDATE_AVAILABLE = "update_available"  # 有新版本
    ERROR = "error"                 # 检查失败


@dataclass
class UpdateInfo:
    """更新信息数据类。"""
    status: UpdateStatus
    current_version: str
    latest_version: Optional[str] = None
    release_notes: Optional[str] = None
    download_url: Optional[str] = None
    release_url: Optional[str] = None
    error_message: Optional[str] = None


class UpdateService:
    """更新检测服务类。
    
    负责检查应用更新，包括：
    - 从 GitHub Releases 获取最新版本信息
    - 比较版本号
    - 提供更新下载链接
    - 自动为中国用户提供代理加速链接
    """
    
    # 请求超时时间（秒）
    REQUEST_TIMEOUT: int = 10
    
    def __init__(self) -> None:
        """初始化更新检测服务。"""
        self.current_version: str = APP_VERSION
    
    @staticmethod
    def get_platform_name() -> str:
        """获取平台相关的名称，与 build.py 保持一致。
        
        Returns:
            平台名称，例如 "Windows_amd64", "Darwin_arm64", "Linux_amd64"
        """
        system = platform.system()
        machine = platform.machine().upper()
        
        # 统一机器架构名称（与 build.py 保持一致）
        arch_map = {
            'X86_64': 'amd64',   # Linux/macOS 常用
            'AMD64': 'amd64',    # Windows 常用
            'ARM64': 'arm64',    # Apple Silicon
            'AARCH64': 'arm64',  # Linux ARM64
            'I386': 'x86',
            'I686': 'x86',
        }
        
        arch = arch_map.get(machine, machine.lower())
        
        return f"{system}_{arch}"
    
    @staticmethod
    def parse_version(version_str: str) -> Tuple[int, ...]:
        """解析版本号字符串为可比较的元组。
        
        支持格式：v1.0.0, 1.0.0, 1.0, 1.0.0-beta 等
        
        Args:
            version_str: 版本号字符串
        
        Returns:
            版本号元组，例如 (1, 0, 0)
        """
        # 移除开头的 'v' 或 'V'
        version_str = version_str.lstrip('vV')
        
        # 移除预发布标签（如 -beta, -alpha, -rc1 等）
        version_str = re.split(r'[-+]', version_str)[0]
        
        # 分割版本号并转换为整数
        parts = version_str.split('.')
        return tuple(int(part) for part in parts if part.isdigit())
    
    @staticmethod
    def compare_versions(version1: str, version2: str) -> int:
        """比较两个版本号。
        
        Args:
            version1: 第一个版本号
            version2: 第二个版本号
        
        Returns:
            -1: version1 < version2
             0: version1 == version2
             1: version1 > version2
        """
        v1 = UpdateService.parse_version(version1)
        v2 = UpdateService.parse_version(version2)
        
        # 补齐版本号长度
        max_len = max(len(v1), len(v2))
        v1 = v1 + (0,) * (max_len - len(v1))
        v2 = v2 + (0,) * (max_len - len(v2))
        
        if v1 < v2:
            return -1
        elif v1 > v2:
            return 1
        else:
            return 0
    
    def check_update(self) -> UpdateInfo:
        """检查更新。
        
        Returns:
            UpdateInfo: 更新信息对象
        """
        try:
            # 发送请求获取最新 Release 信息
            with httpx.Client(timeout=self.REQUEST_TIMEOUT, follow_redirects=True) as client:
                response = client.get(
                    GITHUB_API_URL,
                    headers={
                        "Accept": "application/vnd.github.v3+json",
                        "User-Agent": f"MTools/{self.current_version}"
                    }
                )
                
                if response.status_code == 404:
                    # 没有发布任何 Release
                    return UpdateInfo(
                        status=UpdateStatus.UP_TO_DATE,
                        current_version=self.current_version,
                        latest_version=self.current_version,
                        release_url=GITHUB_RELEASES_URL,
                    )
                
                response.raise_for_status()
                data = response.json()
            
            # 解析版本信息
            latest_version = data.get("tag_name", "").lstrip('vV')
            release_notes = data.get("body", "")
            release_url = data.get("html_url", GITHUB_RELEASES_URL)
            
            # 查找当前平台的下载链接
            download_url = None
            assets = data.get("assets", [])
            platform_name = self.get_platform_name()  # 例如 "Windows_amd64"
            
            for asset in assets:
                asset_name = asset.get("name", "")
                # 精确匹配当前平台的文件（例如 MTools_Windows_amd64.zip）
                if platform_name in asset_name and asset_name.endswith('.zip'):
                    download_url = asset.get("browser_download_url")
                    break
            
            # 备选：如果没找到精确匹配，尝试模糊匹配
            if not download_url:
                system = platform.system().lower()
                for asset in assets:
                    asset_name = asset.get("name", "").lower()
                    if system in asset_name and asset_name.endswith('.zip'):
                        download_url = asset.get("browser_download_url")
                        break
            
            # 比较版本
            comparison = self.compare_versions(self.current_version, latest_version)
            
            # 为中国大陆用户转换为代理下载链接
            if download_url:
                download_url = get_proxied_url(download_url)
            
            if comparison < 0:
                # 有新版本
                return UpdateInfo(
                    status=UpdateStatus.UPDATE_AVAILABLE,
                    current_version=self.current_version,
                    latest_version=latest_version,
                    release_notes=release_notes,
                    download_url=download_url,
                    release_url=release_url,
                )
            else:
                # 已是最新版本
                return UpdateInfo(
                    status=UpdateStatus.UP_TO_DATE,
                    current_version=self.current_version,
                    latest_version=latest_version,
                    release_url=release_url,
                )
        
        except httpx.TimeoutException:
            return UpdateInfo(
                status=UpdateStatus.ERROR,
                current_version=self.current_version,
                error_message="检查更新超时，请检查网络连接",
            )
        except httpx.HTTPStatusError as e:
            return UpdateInfo(
                status=UpdateStatus.ERROR,
                current_version=self.current_version,
                error_message=f"服务器返回错误: {e.response.status_code}",
            )
        except Exception as e:
            return UpdateInfo(
                status=UpdateStatus.ERROR,
                current_version=self.current_version,
                error_message=f"检查更新失败: {str(e)}",
            )
    
    async def check_update_async(self) -> UpdateInfo:
        """异步检查更新。
        
        Returns:
            UpdateInfo: 更新信息对象
        """
        try:
            async with httpx.AsyncClient(timeout=self.REQUEST_TIMEOUT, follow_redirects=True) as client:
                response = await client.get(
                    GITHUB_API_URL,
                    headers={
                        "Accept": "application/vnd.github.v3+json",
                        "User-Agent": f"MTools/{self.current_version}"
                    }
                )
                
                if response.status_code == 404:
                    return UpdateInfo(
                        status=UpdateStatus.UP_TO_DATE,
                        current_version=self.current_version,
                        latest_version=self.current_version,
                        release_url=GITHUB_RELEASES_URL,
                    )
                
                response.raise_for_status()
                data = response.json()
            
            latest_version = data.get("tag_name", "").lstrip('vV')
            release_notes = data.get("body", "")
            release_url = data.get("html_url", GITHUB_RELEASES_URL)
            
            # 查找当前平台的下载链接
            download_url = None
            assets = data.get("assets", [])
            platform_name = self.get_platform_name()
            
            for asset in assets:
                asset_name = asset.get("name", "")
                if platform_name in asset_name and asset_name.endswith('.zip'):
                    download_url = asset.get("browser_download_url")
                    break
            
            if not download_url:
                system = platform.system().lower()
                for asset in assets:
                    asset_name = asset.get("name", "").lower()
                    if system in asset_name and asset_name.endswith('.zip'):
                        download_url = asset.get("browser_download_url")
                        break
            
            comparison = self.compare_versions(self.current_version, latest_version)
            
            # 为中国大陆用户转换为代理下载链接
            if download_url:
                download_url = get_proxied_url(download_url)
            
            if comparison < 0:
                return UpdateInfo(
                    status=UpdateStatus.UPDATE_AVAILABLE,
                    current_version=self.current_version,
                    latest_version=latest_version,
                    release_notes=release_notes,
                    download_url=download_url,
                    release_url=release_url,
                )
            else:
                return UpdateInfo(
                    status=UpdateStatus.UP_TO_DATE,
                    current_version=self.current_version,
                    latest_version=latest_version,
                    release_url=release_url,
                )
        
        except httpx.TimeoutException:
            return UpdateInfo(
                status=UpdateStatus.ERROR,
                current_version=self.current_version,
                error_message="检查更新超时，请检查网络连接",
            )
        except httpx.HTTPStatusError as e:
            return UpdateInfo(
                status=UpdateStatus.ERROR,
                current_version=self.current_version,
                error_message=f"服务器返回错误: {e.response.status_code}",
            )
        except Exception as e:
            return UpdateInfo(
                status=UpdateStatus.ERROR,
                current_version=self.current_version,
                error_message=f"检查更新失败: {str(e)}",
            )
