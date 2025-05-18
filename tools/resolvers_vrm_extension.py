"""
VRM機能拡張のためのGraphQLリゾルバ

Blender GraphQL MCPのVRM関連リゾルバを拡張します。
新しいテンプレートタイプとエクスポート機能のリゾルバを定義します。
"""

import bpy
import os
import logging
import traceback
from typing import Dict, List, Any, Optional, Union

from .resolvers.base import ResolverBase, handle_exceptions, dict_to_vector, vector_to_dict, ensure_object_exists

logger = logging.getLogger("blender_graphql_mcp.tools.handlers_vrm_extension")

# 新しいVRMテンプレートとエクスポーターのインポート
try:
    from ..new_vrm_templates import (
        apply_template, get_template_types, 
        export_vrm, check_vrm_addon
    )
    NEW_VRM_TEMPLATES_AVAILABLE = True
    logger.info("新しいVRMテンプレートモジュールを読み込みました")
except ImportError:
    NEW_VRM_TEMPLATES_AVAILABLE = False
    logger.warning("新しいVRMテンプレートモジュールが見つかりません")

class VrmExtendedResolver(ResolverBase):
    """VRM拡張機能のGraphQLリゾルバクラス"""
    
    def __init__(self):
        super().__init__()
    
    @handle_exceptions
    def vrm_template_info(self, obj, info) -> Dict[str, Any]:
        """
        利用可能なVRMテンプレート情報を取得
        
        Args:
            obj: GraphQLのルートオブジェクト
            info: GraphQLの実行情報
            
        Returns:
            Dict: テンプレート情報
        """
        self.logger.debug("vrm_template_info リゾルバが呼び出されました")
        
        templates = []
        categories = set()
        
        # 基本テンプレート情報
        templates.append({
            "type": "HUMANOID",
            "description": "標準的な人型モデル",
            "categoryName": "Basic",
            "features": ["基本的な人型リグ", "標準的なメッシュ構造", "簡単な表情設定"]
        })
        
        categories.add("Basic")
        
        # 新しいVRMテンプレートモジュールが利用可能な場合
        if NEW_VRM_TEMPLATES_AVAILABLE:
            template_types = get_template_types()
            
            for template_type, description in template_types.items():
                if template_type == "HUMANOID":
                    continue  # 基本テンプレートは既に追加済み
                
                if template_type.startswith("FANTASY_"):
                    category = "Fantasy"
                    features = ["ファンタジー設定に適したメッシュ", "種族特有の体型", "ゲームやアニメ向けのデザイン"]
                elif template_type.startswith("SCIFI_"):
                    category = "SciFi"
                    features = ["SF/サイバー設定に適したメッシュ", "機械的な部品や未来的なデザイン", "ハードSF向けの構造"]
                else:
                    category = "Other"
                    features = ["カスタムテンプレート", "特殊な用途向け"]
                
                templates.append({
                    "type": template_type,
                    "description": description,
                    "categoryName": category,
                    "features": features
                })
                
                categories.add(category)
        
        return {
            "templates": templates,
            "count": len(templates),
            "categories": list(categories)
        }
    
    @handle_exceptions
    def apply_vrm_template(self, obj, info, modelId: str, templateType: str) -> Dict[str, Any]:
        """
        VRMテンプレートを適用
        
        Args:
            obj: GraphQLのルートオブジェクト
            info: GraphQLの実行情報
            modelId: モデルID（コレクション名）
            templateType: テンプレートタイプ
            
        Returns:
            Dict: 適用結果
        """
        self.logger.debug(f"apply_vrm_template リゾルバが呼び出されました: modelId={modelId}, templateType={templateType}")
        
        # コレクションの存在確認
        vrm_collection = bpy.data.collections.get(modelId)
        if not vrm_collection:
            return self.error_response(f"VRMモデル '{modelId}' が見つかりません")
        
        # VRMモデルかどうかの確認
        if not vrm_collection.get("vrm_model", False):
            return self.error_response(f"コレクション '{modelId}' はVRMモデルではありません")
        
        # 新しいVRMテンプレートモジュールが利用可能な場合
        if NEW_VRM_TEMPLATES_AVAILABLE and templateType != "HUMANOID":
            result = apply_template(modelId, templateType)
            
            if not result.get("success", False):
                return self.error_response(result.get("message", f"テンプレート '{templateType}' の適用に失敗しました"))
            
            return self.success_response(
                result.get("message", f"テンプレート '{templateType}' を適用しました"),
                {
                    "success": True,
                    "message": result.get("message", f"テンプレート '{templateType}' を適用しました"),
                    "model": {
                        "id": modelId,
                        "name": vrm_collection.name,
                        "version": vrm_collection.get("vrm_version", "1.0")
                    }
                }
            )
        
        # 基本テンプレート（HUMANOID）または新しいVRMテンプレートモジュールが利用できない場合は
        # 既存の実装を呼び出す
        from .resolvers.vrm import VrmResolver
        vrm_resolver = VrmResolver()
        return vrm_resolver.apply_template(obj, info, modelId, "HUMANOID")
    
    @handle_exceptions
    def export_vrm_extended(self, obj, info, modelId: str, filepath: str, 
                          metadata: Optional[Dict[str, Any]] = None, 
                          options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        拡張VRMエクスポート
        
        Args:
            obj: GraphQLのルートオブジェクト
            info: GraphQLの実行情報
            modelId: モデルID（コレクション名）
            filepath: エクスポート先ファイルパス
            metadata: VRMメタデータ（オプション）
            options: エクスポートオプション
            
        Returns:
            Dict: エクスポート結果
        """
        self.logger.debug(f"export_vrm_extended リゾルバが呼び出されました: modelId={modelId}, filepath={filepath}")
        
        # コレクションの存在確認
        vrm_collection = bpy.data.collections.get(modelId)
        if not vrm_collection:
            return self.error_response(f"VRMモデル '{modelId}' が見つかりません")
        
        # VRMモデルかどうかの確認
        if not vrm_collection.get("vrm_model", False):
            return self.error_response(f"コレクション '{modelId}' はVRMモデルではありません")
        
        # 新しいVRMエクスポート機能が利用可能な場合
        if NEW_VRM_TEMPLATES_AVAILABLE:
            # VRMアドオンの有無を確認
            has_vrm_addon = check_vrm_addon()
            
            # エクスポートオプションの処理
            if not options:
                options = {}
            
            # メタデータの処理
            if not metadata:
                metadata = {}
            
            # エクスポート実行
            result = export_vrm(modelId, filepath, metadata)
            
            if not result.get("success", False):
                return self.error_response(result.get("message", f"VRMエクスポートに失敗しました: {filepath}"))
            
            # FBXフォールバックが使用されたかどうかを確認
            fallback_to_fbx = "json_filepath" in result
            
            return {
                "success": True,
                "message": result.get("message", f"VRMエクスポートが完了しました: {filepath}"),
                "filepath": result.get("filepath", filepath),
                "metadata": {
                    "title": metadata.get("title", ""),
                    "author": metadata.get("author", ""),
                    "version": metadata.get("version", "1.0")
                },
                "usedVrmAddon": has_vrm_addon,
                "fallbackToFbx": fallback_to_fbx,
                "jsonFilepath": result.get("json_filepath", None)
            }
        
        # 新しいVRMエクスポート機能が利用できない場合は既存の実装を呼び出す
        from .resolvers.vrm import VrmResolver
        vrm_resolver = VrmResolver()
        result = vrm_resolver.export_vrm(obj, info, modelId, filepath, metadata)
        
        return {
            "success": result.get("success", False),
            "message": result.get("message", ""),
            "filepath": result.get("filepath", filepath),
            "metadata": result.get("metadata", {}),
            "usedVrmAddon": False,
            "fallbackToFbx": False,
            "jsonFilepath": None
        }

# リゾルバモジュールにメソッドを追加する関数
def register_vrm_extension_resolvers(resolver_module):
    """
    VRM拡張リゾルバをリゾルバモジュールに登録します
    
    Args:
        resolver_module: リゾルバモジュール
    """
    resolver = VrmExtendedResolver()
    
    setattr(resolver_module, 'vrm_template_info', resolver.vrm_template_info)
    setattr(resolver_module, 'apply_vrm_template', resolver.apply_vrm_template)
    setattr(resolver_module, 'export_vrm_extended', resolver.export_vrm_extended)
    
    logger.info("VRM拡張リゾルバを登録しました")