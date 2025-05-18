"""
Blender GraphQL MCP - Addons GraphQL Resolvers
アドオン操作のためのGraphQLリゾルバー
"""

from typing import Dict, List, Any, Optional, Union
import strawberry
import bpy

from ...core.commands.addon_commands import (
    enable_addon, disable_addon, get_addon_info, 
    get_all_addons, install_addon_from_file,
    install_addon_from_url, update_addon, check_addon_updates
)
from ..common import APIResponse, ErrorCodes, MCPError
from .base import BaseResolver, resolver_error_handler

@strawberry.type
class AddonInfo:
    """アドオン情報を表すGraphQL型"""
    name: str
    is_enabled: bool
    description: Optional[str] = None
    author: Optional[str] = None
    version: Optional[str] = None
    category: Optional[str] = None
    blender_version: Optional[str] = None
    
@strawberry.type
class AddonStatus:
    """アドオン操作ステータスを表すGraphQL型"""
    status: str
    message: str
    addon_name: Optional[str] = None
    is_enabled: Optional[bool] = None

@strawberry.type
class AddonUpdateInfo:
    """アドオン更新情報を表すGraphQL型"""
    name: str
    current_version: str
    available_version: str
    has_update: bool

@strawberry.type
class AddonCategory:
    """アドオンカテゴリを表すGraphQL型"""
    category_name: str
    addons: List[str]

@strawberry.type
class AllAddonsResponse:
    """すべてのアドオン情報を表すGraphQL型"""
    supported_addons: List[str]
    categorized_addons: Dict[str, List[str]]
    total_enabled: int
    total_supported: int
    addons: List[AddonInfo]
    
class AddonResolver(BaseResolver):
    """アドオン操作関連のリゾルバー"""
    
    @resolver_error_handler
    def get_addon_info_resolver(self, addon_name: str) -> AddonInfo:
        """
        アドオン情報を取得するリゾルバー
        
        Args:
            addon_name: 情報を取得するアドオン名
            
        Returns:
            アドオン情報
        """
        result = get_addon_info(addon_name)
        
        if result["status"] != "success":
            raise MCPError(
                message=result.get("message", f"アドオン '{addon_name}' の情報取得に失敗しました"),
                code=ErrorCodes.NOT_FOUND if result["status"] == "error" else ErrorCodes.PARTIAL_SUCCESS,
                context={"addon_name": addon_name, "error": result.get("error")}
            )
        
        info = result.get("info", {})
        version_tuple = info.get("version", (0, 0, 0))
        version_str = ".".join([str(v) for v in version_tuple]) if isinstance(version_tuple, tuple) else str(version_tuple)
        
        blender_version_tuple = info.get("blender", (0, 0, 0))
        blender_version_str = ".".join([str(v) for v in blender_version_tuple]) if isinstance(blender_version_tuple, tuple) else str(blender_version_tuple)
        
        return AddonInfo(
            name=info.get("name", addon_name),
            is_enabled=result.get("is_enabled", False),
            description=info.get("description"),
            author=info.get("author"),
            version=version_str,
            category=info.get("category"),
            blender_version=blender_version_str
        )
    
    @resolver_error_handler
    def get_all_addons_resolver(self) -> AllAddonsResponse:
        """
        すべてのアドオン情報を取得するリゾルバー
        
        Returns:
            すべてのアドオン情報
        """
        result = get_all_addons()
        
        if result["status"] != "success":
            raise MCPError(
                message=result.get("message", "アドオン情報の取得に失敗しました"),
                code=ErrorCodes.INTERNAL_ERROR,
                context={"error": result.get("error")}
            )
        
        addon_details = result.get("addon_details", {})
        addons_list = []
        
        for addon_name, details in addon_details.items():
            version_value = details.get("version", (0, 0, 0))
            version_str = ".".join([str(v) for v in version_value]) if isinstance(version_value, tuple) else str(version_value)
            
            addons_list.append(AddonInfo(
                name=details.get("name", addon_name),
                is_enabled=details.get("is_enabled", False),
                description=details.get("description"),
                author=details.get("author"),
                version=version_str,
                category=details.get("category")
            ))
        
        return AllAddonsResponse(
            supported_addons=result.get("supported_addons", []),
            categorized_addons=result.get("categorized_addons", {}),
            total_enabled=result.get("total_enabled", 0),
            total_supported=result.get("total_supported", 0),
            addons=addons_list
        )
    
    @resolver_error_handler
    def enable_addon_resolver(self, addon_name: str) -> AddonStatus:
        """
        アドオンを有効化するミューテーションリゾルバー
        
        Args:
            addon_name: 有効化するアドオン名
            
        Returns:
            操作結果ステータス
        """
        result = enable_addon(addon_name)
        
        if result["status"] == "error":
            raise MCPError(
                message=result.get("message", f"アドオン '{addon_name}' の有効化に失敗しました"),
                code=ErrorCodes.OPERATION_FAILED,
                context={"addon_name": addon_name, "error": result.get("error")}
            )
        
        return AddonStatus(
            status=result["status"],
            message=result["message"],
            addon_name=result.get("addon_name"),
            is_enabled=result.get("is_enabled")
        )
    
    @resolver_error_handler
    def disable_addon_resolver(self, addon_name: str) -> AddonStatus:
        """
        アドオンを無効化するミューテーションリゾルバー
        
        Args:
            addon_name: 無効化するアドオン名
            
        Returns:
            操作結果ステータス
        """
        result = disable_addon(addon_name)
        
        if result["status"] == "error":
            raise MCPError(
                message=result.get("message", f"アドオン '{addon_name}' の無効化に失敗しました"),
                code=ErrorCodes.OPERATION_FAILED,
                context={"addon_name": addon_name, "error": result.get("error")}
            )
        
        return AddonStatus(
            status=result["status"],
            message=result["message"],
            addon_name=result.get("addon_name"),
            is_enabled=result.get("is_enabled")
        )
    
    @resolver_error_handler
    def install_addon_resolver(self, file_path: str) -> AddonStatus:
        """
        アドオンをファイルからインストールするミューテーションリゾルバー
        
        Args:
            file_path: インストールするアドオンZIPファイルパス
            
        Returns:
            操作結果ステータス
        """
        result = install_addon_from_file(file_path)
        
        if result["status"] == "error":
            raise MCPError(
                message=result.get("message", "アドオンのインストールに失敗しました"),
                code=ErrorCodes.OPERATION_FAILED,
                context={"file_path": file_path, "error": result.get("error")}
            )
        
        return AddonStatus(
            status=result["status"],
            message=result["message"],
            addon_name=result.get("addon_name"),
            is_enabled=result.get("is_enabled")
        )
    
    @resolver_error_handler
    def install_addon_from_url_resolver(self, url: str) -> AddonStatus:
        """
        アドオンをURLからインストールするミューテーションリゾルバー
        
        Args:
            url: アドオンZIPファイルのURL
            
        Returns:
            操作結果ステータス
        """
        result = install_addon_from_url(url)
        
        if result["status"] == "error":
            raise MCPError(
                message=result.get("message", "URLからのアドオンインストールに失敗しました"),
                code=ErrorCodes.OPERATION_FAILED,
                context={"url": url, "error": result.get("error")}
            )
        
        return AddonStatus(
            status=result["status"],
            message=result["message"],
            addon_name=result.get("addon_name"),
            is_enabled=result.get("is_enabled")
        )
    
    @resolver_error_handler
    def update_addon_resolver(self, addon_name: str) -> AddonStatus:
        """
        アドオンを更新するミューテーションリゾルバー
        
        Args:
            addon_name: 更新するアドオン名
            
        Returns:
            操作結果ステータス
        """
        result = update_addon(addon_name)
        
        if result["status"] == "error":
            raise MCPError(
                message=result.get("message", f"アドオン '{addon_name}' の更新に失敗しました"),
                code=ErrorCodes.OPERATION_FAILED,
                context={"addon_name": addon_name, "error": result.get("error")}
            )
        
        return AddonStatus(
            status=result["status"],
            message=result["message"],
            addon_name=result.get("addon_name"),
            is_enabled=result.get("is_enabled", None)
        )
    
    @resolver_error_handler
    def check_addon_updates_resolver(self) -> List[AddonUpdateInfo]:
        """
        更新可能なアドオンを確認するリゾルバー
        
        Returns:
            更新可能なアドオンのリスト
        """
        result = check_addon_updates()
        
        if result["status"] == "error":
            raise MCPError(
                message=result.get("message", "アドオン更新の確認に失敗しました"),
                code=ErrorCodes.OPERATION_FAILED,
                context={"error": result.get("error")}
            )
        
        update_infos = []
        for addon in result.get("updatable_addons", []):
            update_infos.append(AddonUpdateInfo(
                name=addon.get("name"),
                current_version=addon.get("current_version", "0.0.0"),
                available_version=addon.get("available_version", "0.0.0"),
                has_update=True
            ))
        
        return update_infos