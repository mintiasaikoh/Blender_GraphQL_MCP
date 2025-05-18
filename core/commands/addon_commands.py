"""
Blender GraphQL MCP - Addon操作コマンド
アドオンの有効化・無効化・インストールのためのコマンドを提供
"""

import bpy
import os
import zipfile
import tempfile
import urllib.request
from typing import Dict, List, Any, Optional, Union

from ..commands.base import register_command
from ...addons_bridge import SUPPORTED_ADDONS, AddonBridge

@register_command("enable_addon", "アドオンを有効化")
def enable_addon(addon_name: str) -> Dict[str, Any]:
    """
    アドオンを有効化する
    
    Args:
        addon_name: 有効化するアドオン名
        
    Returns:
        結果を含む辞書
    """
    if addon_name not in SUPPORTED_ADDONS:
        return {
            "status": "error",
            "message": f"アドオン '{addon_name}' はサポートされていません",
            "supported_addons": SUPPORTED_ADDONS
        }
    
    try:
        # アドオンが既に有効かチェック
        if addon_name in bpy.context.preferences.addons:
            return {
                "status": "warning",
                "message": f"アドオン '{addon_name}' は既に有効です",
                "addon_name": addon_name,
                "is_enabled": True
            }
        
        # アドオンを有効化
        bpy.ops.preferences.addon_enable(module=addon_name)
        
        # 有効化の確認
        if addon_name in bpy.context.preferences.addons:
            return {
                "status": "success",
                "message": f"アドオン '{addon_name}' を有効化しました",
                "addon_name": addon_name,
                "is_enabled": True
            }
        else:
            return {
                "status": "error",
                "message": f"アドオン '{addon_name}' の有効化に失敗しました",
                "addon_name": addon_name,
                "is_enabled": False,
                "reason": "アドオンが見つからないか、有効化できませんでした"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"アドオン '{addon_name}' の有効化中にエラーが発生しました: {str(e)}",
            "addon_name": addon_name,
            "error": str(e)
        }

@register_command("disable_addon", "アドオンを無効化")
def disable_addon(addon_name: str) -> Dict[str, Any]:
    """
    アドオンを無効化する
    
    Args:
        addon_name: 無効化するアドオン名
        
    Returns:
        結果を含む辞書
    """
    if addon_name not in SUPPORTED_ADDONS:
        return {
            "status": "error",
            "message": f"アドオン '{addon_name}' はサポートされていません",
            "supported_addons": SUPPORTED_ADDONS
        }
    
    try:
        # アドオンが有効かチェック
        if addon_name not in bpy.context.preferences.addons:
            return {
                "status": "warning",
                "message": f"アドオン '{addon_name}' は既に無効です",
                "addon_name": addon_name,
                "is_enabled": False
            }
        
        # アドオンを無効化
        bpy.ops.preferences.addon_disable(module=addon_name)
        
        # 無効化の確認
        if addon_name not in bpy.context.preferences.addons:
            return {
                "status": "success",
                "message": f"アドオン '{addon_name}' を無効化しました",
                "addon_name": addon_name,
                "is_enabled": False
            }
        else:
            return {
                "status": "error",
                "message": f"アドオン '{addon_name}' の無効化に失敗しました",
                "addon_name": addon_name,
                "is_enabled": True,
                "reason": "無効化処理が完了しませんでした"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"アドオン '{addon_name}' の無効化中にエラーが発生しました: {str(e)}",
            "addon_name": addon_name,
            "error": str(e)
        }

@register_command("get_addon_info", "アドオン情報を取得")
def get_addon_info(addon_name: str) -> Dict[str, Any]:
    """
    アドオンの詳細情報を取得する
    
    Args:
        addon_name: 情報を取得するアドオン名
        
    Returns:
        アドオン情報を含む辞書
    """
    try:
        # Blender 4.2以降のアドオン情報取得方法
        addon_modules = bpy.context.preferences.get_addon_modules()
        addon_infos = bpy.context.preferences.get_addon_infos()
        
        if addon_name in addon_infos:
            info = addon_infos[addon_name]
            is_enabled = addon_name in bpy.context.preferences.addons
            
            return {
                "status": "success",
                "addon_name": addon_name,
                "is_enabled": is_enabled,
                "info": {
                    "name": info.get("name", addon_name),
                    "version": info.get("version", (0, 0, 0)),
                    "author": info.get("author", "不明"),
                    "description": info.get("description", "説明なし"),
                    "category": info.get("category", "その他"),
                    "location": info.get("location", ""),
                    "blender": info.get("blender", (0, 0, 0)),
                    "support": info.get("support", "COMMUNITY"),
                    "warning": info.get("warning", ""),
                    "doc_url": info.get("doc_url", ""),
                    "tracker_url": info.get("tracker_url", ""),
                    "wiki_url": info.get("wiki_url", "")
                }
            }
        elif addon_name in SUPPORTED_ADDONS:
            # 情報は取得できないがサポート対象のアドオン
            is_enabled = addon_name in bpy.context.preferences.addons
            return {
                "status": "partial",
                "message": f"アドオン '{addon_name}' はサポートされていますが、詳細情報は利用できません",
                "addon_name": addon_name,
                "is_enabled": is_enabled,
                "info": {
                    "name": addon_name,
                    "supported": True
                }
            }
        else:
            return {
                "status": "error",
                "message": f"アドオン '{addon_name}' はサポートされていないか、インストールされていません",
                "addon_name": addon_name,
                "supported_addons": SUPPORTED_ADDONS
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"アドオン '{addon_name}' の情報取得中にエラーが発生しました: {str(e)}",
            "addon_name": addon_name,
            "error": str(e)
        }

@register_command("get_all_addons", "すべてのアドオン情報を取得")
def get_all_addons() -> Dict[str, Any]:
    """
    すべてのアドオン情報を取得する
    
    Returns:
        すべてのアドオン情報を含む辞書
    """
    try:
        # 既存のアドオン情報を取得
        addon_modules = bpy.context.preferences.get_addon_modules()
        addon_infos = bpy.context.preferences.get_addon_infos()
        enabled_addons = set(bpy.context.preferences.addons.keys())
        
        # サポート対象アドオンの詳細情報
        supported_addon_details = {}
        for addon_name in SUPPORTED_ADDONS:
            is_enabled = addon_name in enabled_addons
            
            if addon_name in addon_infos:
                info = addon_infos[addon_name]
                supported_addon_details[addon_name] = {
                    "name": info.get("name", addon_name),
                    "is_enabled": is_enabled,
                    "version": info.get("version", (0, 0, 0)),
                    "author": info.get("author", "不明"),
                    "description": info.get("description", "説明なし"),
                    "category": info.get("category", "その他"),
                    "supported": True
                }
            else:
                # 情報は取得できないがサポート対象のアドオン
                supported_addon_details[addon_name] = {
                    "name": addon_name,
                    "is_enabled": is_enabled,
                    "supported": True,
                    "installed": addon_name in addon_modules
                }
        
        # カテゴリ別アドオンリスト
        categorized_addons = {
            "standard": [addon for addon in SUPPORTED_ADDONS 
                        if not addon.startswith("VRM_") and "_" not in addon],
            "modeling": ["simple_deform_helper", "orient_and_origin", "place_helper"],
            "animation": ["animation_nodes"],
            "vtuber": ["VRM_Addon_for_Blender", "mmd_tools"],
            "materials": ["TexTools"],
            "simulation": ["molecular_nodes"],
            "misc": ["quick_groups"]
        }
        
        return {
            "status": "success",
            "supported_addons": SUPPORTED_ADDONS,
            "addon_details": supported_addon_details,
            "categorized_addons": categorized_addons,
            "total_enabled": len(enabled_addons),
            "total_supported": len(SUPPORTED_ADDONS)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"アドオン情報の取得中にエラーが発生しました: {str(e)}",
            "error": str(e)
        }

@register_command("install_addon_from_file", "ファイルからアドオンをインストール")
def install_addon_from_file(filepath: str, overwrite: bool = True) -> Dict[str, Any]:
    """
    ファイルからアドオンをインストールする
    
    Args:
        filepath: インストールするアドオンZIPファイルパス
        overwrite: 既存のアドオンを上書きするかどうか
        
    Returns:
        結果を含む辞書
    """
    if not os.path.exists(filepath):
        return {
            "status": "error",
            "message": f"ファイル '{filepath}' が見つかりません",
            "filepath": filepath
        }
    
    try:
        # ZIPファイルからアドオン名を推測
        addon_name = None
        with zipfile.ZipFile(filepath, 'r') as zip_ref:
            for file_info in zip_ref.infolist():
                if file_info.filename.endswith('/__init__.py'):
                    # /__init__.pyのパスから最後のディレクトリ名を取得
                    parts = file_info.filename.split('/')
                    if len(parts) >= 2:
                        addon_name = parts[-2]
                        break
        
        # アドオンをインストール
        if overwrite:
            result = bpy.ops.preferences.addon_install(
                overwrite=True,
                filepath=filepath
            )
        else:
            result = bpy.ops.preferences.addon_install(
                overwrite=False,
                filepath=filepath
            )
        
        if result == {'FINISHED'}:
            # インストールしたアドオンを有効化
            if addon_name:
                bpy.ops.preferences.addon_enable(module=addon_name)
                is_enabled = addon_name in bpy.context.preferences.addons
                
                return {
                    "status": "success",
                    "message": f"アドオン '{addon_name}' のインストールと有効化が完了しました",
                    "addon_name": addon_name,
                    "is_enabled": is_enabled,
                    "filepath": filepath
                }
            else:
                return {
                    "status": "partial",
                    "message": "アドオンのインストールは完了しましたが、自動有効化できませんでした",
                    "filepath": filepath,
                    "reason": "アドオン名を特定できませんでした"
                }
        else:
            return {
                "status": "error",
                "message": "アドオンのインストールに失敗しました",
                "result": str(result),
                "filepath": filepath
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"アドオンのインストール中にエラーが発生しました: {str(e)}",
            "filepath": filepath,
            "error": str(e)
        }

@register_command("install_addon_from_url", "URLからアドオンをインストール")
def install_addon_from_url(url: str, overwrite: bool = True) -> Dict[str, Any]:
    """
    URLからアドオンをダウンロードしてインストールする
    
    Args:
        url: アドオンZIPファイルのURL
        overwrite: 既存のアドオンを上書きするかどうか
        
    Returns:
        結果を含む辞書
    """
    try:
        # 一時ファイルを作成
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_file:
            temp_path = temp_file.name
        
        # URLからファイルをダウンロード
        try:
            urllib.request.urlretrieve(url, temp_path)
        except Exception as download_error:
            # 一時ファイルを削除して例外を再発生
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            return {
                "status": "error",
                "message": f"アドオンのダウンロード中にエラーが発生しました: {str(download_error)}",
                "url": url,
                "error": str(download_error)
            }
        
        # ダウンロードしたファイルからアドオンをインストール
        try:
            result = install_addon_from_file(temp_path, overwrite)
            result["url"] = url  # URLも結果に含める
            return result
        finally:
            # 一時ファイルを削除
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    except Exception as e:
        return {
            "status": "error",
            "message": f"URLからのアドオンインストール中にエラーが発生しました: {str(e)}",
            "url": url,
            "error": str(e)
        }

@register_command("update_addon", "アドオンを更新")
def update_addon(addon_name: str) -> Dict[str, Any]:
    """
    アドオンを更新する（Blender 4.2以降のExtensionsシステム用）
    
    Args:
        addon_name: 更新するアドオン名
        
    Returns:
        結果を含む辞書
    """
    if addon_name not in SUPPORTED_ADDONS:
        return {
            "status": "error",
            "message": f"アドオン '{addon_name}' はサポートされていません",
            "supported_addons": SUPPORTED_ADDONS
        }
    
    try:
        # Blender 4.2以降のExtensionsシステムでのアドオン更新
        # 注：このAPIはBlender 4.2以降で利用可能
        try:
            # 更新可能かチェック
            has_update = False
            
            # Blender 4.2以降 - extensions APIを使用
            if hasattr(bpy.ops.preferences, "extension_check_update"):
                result = bpy.ops.preferences.extension_check_update()
                
                if result == {'FINISHED'}:
                    # 更新を実行
                    if hasattr(bpy.ops.preferences, "extension_update"):
                        update_result = bpy.ops.preferences.extension_update(module=addon_name)
                        
                        if update_result == {'FINISHED'}:
                            return {
                                "status": "success",
                                "message": f"アドオン '{addon_name}' の更新が完了しました",
                                "addon_name": addon_name
                            }
                        else:
                            return {
                                "status": "error",
                                "message": f"アドオン '{addon_name}' の更新に失敗しました",
                                "addon_name": addon_name,
                                "result": str(update_result)
                            }
                    else:
                        return {
                            "status": "error",
                            "message": f"このバージョンのBlenderはextension_updateをサポートしていません",
                            "addon_name": addon_name,
                            "blender_version": bpy.app.version_string
                        }
                else:
                    return {
                        "status": "error",
                        "message": f"アドオン '{addon_name}' の更新確認に失敗しました",
                        "addon_name": addon_name,
                        "result": str(result)
                    }
            else:
                return {
                    "status": "error",
                    "message": f"このバージョンのBlenderはExtensionsシステムをサポートしていません",
                    "addon_name": addon_name,
                    "blender_version": bpy.app.version_string
                }
                
        except AttributeError:
            return {
                "status": "error",
                "message": f"このバージョンのBlenderはExtensionsシステムをサポートしていません",
                "addon_name": addon_name,
                "blender_version": bpy.app.version_string
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"アドオン '{addon_name}' の更新中にエラーが発生しました: {str(e)}",
            "addon_name": addon_name,
            "error": str(e)
        }

@register_command("check_addon_updates", "アドオンの更新を確認")
def check_addon_updates() -> Dict[str, Any]:
    """
    インストール済みのアドオンで更新可能なものを確認する
    
    Returns:
        更新可能なアドオンの情報を含む辞書
    """
    try:
        # Blender 4.2以降のExtensionsシステムでのアドオン更新確認
        # 注：このAPIはBlender 4.2以降で利用可能
        if hasattr(bpy.ops.preferences, "extension_check_update"):
            result = bpy.ops.preferences.extension_check_update()
            
            if result == {'FINISHED'}:
                # 更新可能なアドオンを取得
                updatable_addons = []
                
                # TODO: これは実際のBlender APIに合わせて調整が必要
                # Blender 4.2以降の正確なAPIがわかり次第、更新可能なアドオンのリストを取得
                
                return {
                    "status": "success",
                    "message": "アドオンの更新確認が完了しました",
                    "updatable_addons": updatable_addons,
                    "blender_version": bpy.app.version_string
                }
            else:
                return {
                    "status": "error",
                    "message": "アドオンの更新確認に失敗しました",
                    "result": str(result)
                }
        else:
            return {
                "status": "error",
                "message": "このバージョンのBlenderはExtensionsシステムをサポートしていません",
                "blender_version": bpy.app.version_string
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"アドオンの更新確認中にエラーが発生しました: {str(e)}",
            "error": str(e)
        }