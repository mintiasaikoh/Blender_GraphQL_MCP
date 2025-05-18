"""
モディファイア関連のGraphQLリゾルバを提供
"""

import bpy
import json
import logging
from typing import Dict, List, Any, Optional, Union
from .base import ResolverBase, handle_exceptions, ensure_object_exists

class ModifierResolver(ResolverBase):
    """モディファイア関連のGraphQLリゾルバクラス"""
    
    def __init__(self):
        super().__init__()
    
    @handle_exceptions
    def get_all(self, obj, info, objectName: str) -> List[Dict[str, Any]]:
        """
        指定されたオブジェクトのすべてのモディファイア情報を取得
        
        Args:
            obj: GraphQLのルートオブジェクト
            info: GraphQLの実行情報
            objectName: オブジェクト名
            
        Returns:
            List[Dict]: モディファイア情報のリスト
        """
        self.logger.debug(f"modifiers リゾルバが呼び出されました: object={objectName}")
        
        # オブジェクトの検索
        blender_obj = ensure_object_exists(objectName)
        if not blender_obj:
            return self.error_response(f"オブジェクト '{objectName}' が見つかりません")
        
        # モディファイア情報の収集
        modifiers = []
        for mod in blender_obj.modifiers:
            modifiers.append(self._get_modifier_data(mod))
        
        return modifiers
    
    def _get_modifier_data(self, modifier) -> Dict[str, Any]:
        """
        モディファイアデータを辞書形式で取得
        
        Args:
            modifier: Blenderモディファイア
            
        Returns:
            Dict: モディファイアデータ
        """
        data = {
            'name': modifier.name,
            'type': modifier.type,
            'show_viewport': modifier.show_viewport,
            'show_render': modifier.show_render,
            'show_in_editmode': modifier.show_in_editmode
        }
        
        # モディファイアタイプ別の情報追加
        if modifier.type == 'SUBSURF':
            data['levels'] = modifier.levels
            data['render_levels'] = modifier.render_levels
        elif modifier.type == 'SOLIDIFY':
            data['thickness'] = modifier.thickness
        elif modifier.type == 'ARRAY':
            data['count'] = modifier.count
            data['relative_offset_displace'] = [
                modifier.relative_offset_displace[0],
                modifier.relative_offset_displace[1],
                modifier.relative_offset_displace[2]
            ]
        elif modifier.type == 'BOOLEAN':
            data['operation'] = modifier.operation
            data['object'] = modifier.object.name if modifier.object else None
        elif modifier.type == 'BEVEL':
            data['width'] = modifier.width
            data['segments'] = modifier.segments
        elif modifier.type == 'MIRROR':
            data['use_axis'] = [
                modifier.use_axis[0],
                modifier.use_axis[1],
                modifier.use_axis[2]
            ]
        
        return data
    
    @handle_exceptions
    def add(self, obj, info, objectName: str, modType: str, modName: Optional[str] = None) -> Dict[str, Any]:
        """
        オブジェクトにモディファイアを追加
        
        Args:
            obj: GraphQLのルートオブジェクト
            info: GraphQLの実行情報
            objectName: オブジェクト名
            modType: モディファイアタイプ
            modName: モディファイア名（省略時は自動生成）
            
        Returns:
            Dict: 追加結果
        """
        self.logger.debug(f"add_modifier リゾルバが呼び出されました: object={objectName}, type={modType}")
        
        # オブジェクトの検索
        blender_obj = ensure_object_exists(objectName)
        if not blender_obj:
            return self.error_response(f"オブジェクト '{objectName}' が見つかりません")
        
        # モディファイアタイプの標準化と検証
        mod_type = modType.upper() if modType else None
        if not mod_type:
            return self.error_response("モディファイアタイプは必須です")
        
        # サポートされているモディファイアタイプのリスト
        valid_types = [
            'ARRAY', 'BEVEL', 'BOOLEAN', 'BUILD', 'DECIMATE', 'EDGE_SPLIT', 
            'MASK', 'MIRROR', 'MULTIRES', 'REMESH', 'SCREW', 'SKIN', 
            'SOLIDIFY', 'SUBSURF', 'TRIANGULATE', 'WIREFRAME'
        ]
        
        if mod_type not in valid_types:
            return self.error_response(f"無効なモディファイアタイプ: {mod_type}。サポートされているタイプ: {', '.join(valid_types)}")
        
        # モディファイア名の重複チェック
        if modName and modName in [mod.name for mod in blender_obj.modifiers]:
            return self.error_response(f"モディファイア名 '{modName}' は既に使用されています")
        
        # モディファイアを追加
        try:
            modifier = blender_obj.modifiers.new(name=modName or mod_type, type=mod_type)
            
            # デフォルト設定の適用（タイプ別）
            if mod_type == 'SUBSURF':
                modifier.levels = 2
                modifier.render_levels = 3
            elif mod_type == 'SOLIDIFY':
                modifier.thickness = 0.01
            elif mod_type == 'BEVEL':
                modifier.width = 0.1
                modifier.segments = 3
            
            return self.success_response(
                f"モディファイア '{modifier.name}' をオブジェクト '{objectName}' に追加しました",
                {'modifier': self._get_modifier_data(modifier)}
            )
        
        except Exception as e:
            self.logger.error(f"モディファイア追加エラー: {str(e)}")
            return self.error_response(f"モディファイア追加中にエラーが発生しました: {str(e)}")
    
    @handle_exceptions
    def update(self, obj, info, objectName: str, modName: str, params: str) -> Dict[str, Any]:
        """
        モディファイア設定を更新
        
        Args:
            obj: GraphQLのルートオブジェクト
            info: GraphQLの実行情報
            objectName: オブジェクト名
            modName: モディファイア名
            params: パラメータ辞書（JSON文字列）
            
        Returns:
            Dict: 更新結果
        """
        self.logger.debug(f"update_modifier リゾルバが呼び出されました: object={objectName}, modifier={modName}")
        
        # オブジェクトの検索
        blender_obj = ensure_object_exists(objectName)
        if not blender_obj:
            return self.error_response(f"オブジェクト '{objectName}' が見つかりません")
        
        # モディファイアの検索
        if modName not in blender_obj.modifiers:
            return self.error_response(f"モディファイア '{modName}' が見つかりません")
        
        modifier = blender_obj.modifiers[modName]
        
        # パラメータの解析
        try:
            param_dict = json.loads(params)
        except json.JSONDecodeError:
            return self.error_response("無効なJSONフォーマットです")
        
        if not isinstance(param_dict, dict):
            return self.error_response("パラメータは辞書形式である必要があります")
        
        # パラメータの更新
        changed = False
        errors = []
        
        for key, value in param_dict.items():
            if hasattr(modifier, key):
                try:
                    # 特別なケース（3次元配列など）の処理
                    if key == 'relative_offset_displace' and isinstance(value, list) and len(value) == 3:
                        for i in range(3):
                            modifier.relative_offset_displace[i] = value[i]
                        changed = True
                    elif key == 'use_axis' and isinstance(value, list) and len(value) == 3:
                        for i in range(3):
                            modifier.use_axis[i] = value[i]
                        changed = True
                    # オブジェクト参照の処理
                    elif key == 'object' and isinstance(value, str):
                        target_obj = ensure_object_exists(value)
                        if target_obj:
                            modifier.object = target_obj
                            changed = True
                        else:
                            errors.append(f"オブジェクト '{value}' が見つかりません")
                    # その他の一般的なプロパティ
                    else:
                        setattr(modifier, key, value)
                        changed = True
                except Exception as e:
                    errors.append(f"パラメータ '{key}' の設定中にエラー: {str(e)}")
            else:
                errors.append(f"無効なパラメータ: {key}")
        
        # 変更がなかった場合
        if not changed:
            if errors:
                return self.error_response(f"モディファイア更新エラー: {'; '.join(errors)}")
            else:
                return self.error_response("更新するパラメータが指定されていません")
        
        # 結果を返す
        result = self.success_response(
            f"モディファイア '{modName}' を更新しました",
            {'modifier': self._get_modifier_data(modifier)}
        )
        
        # エラーがあれば警告として追加
        if errors:
            result['warnings'] = errors
        
        return result
    
    @handle_exceptions
    def apply(self, obj, info, objectName: str, modName: str) -> Dict[str, Any]:
        """
        モディファイアを適用
        
        Args:
            obj: GraphQLのルートオブジェクト
            info: GraphQLの実行情報
            objectName: オブジェクト名
            modName: モディファイア名
            
        Returns:
            Dict: 適用結果
        """
        self.logger.debug(f"apply_modifier リゾルバが呼び出されました: object={objectName}, modifier={modName}")
        
        # オブジェクトの検索
        blender_obj = ensure_object_exists(objectName)
        if not blender_obj:
            return self.error_response(f"オブジェクト '{objectName}' が見つかりません")
        
        # モディファイアの検索
        if modName not in blender_obj.modifiers:
            return self.error_response(f"モディファイア '{modName}' が見つかりません")
        
        # モディファイアデータを取得（返却用）
        mod_data = self._get_modifier_data(blender_obj.modifiers[modName])
        
        # モディファイアを適用
        try:
            # 現在の選択状態とアクティブオブジェクトを保存
            original_selected_objects = [o for o in bpy.context.selected_objects]
            original_active_object = bpy.context.view_layer.objects.active
            
            # 対象オブジェクトを選択してアクティブに設定
            bpy.ops.object.select_all(action='DESELECT')
            blender_obj.select_set(True)
            bpy.context.view_layer.objects.active = blender_obj
            
            # モディファイアを適用
            bpy.ops.object.modifier_apply(modifier=modName)
            
            # 元の選択状態を復元
            bpy.ops.object.select_all(action='DESELECT')
            for o in original_selected_objects:
                o.select_set(True)
            bpy.context.view_layer.objects.active = original_active_object
            
            return self.success_response(
                f"モディファイア '{modName}' をオブジェクト '{objectName}' に適用しました",
                {'modifier': mod_data}
            )
            
        except Exception as e:
            self.logger.error(f"モディファイア適用エラー: {str(e)}")
            return self.error_response(f"モディファイア適用中にエラーが発生しました: {str(e)}")
    
    @handle_exceptions
    def delete(self, obj, info, objectName: str, modName: str) -> Dict[str, Any]:
        """
        モディファイアを削除
        
        Args:
            obj: GraphQLのルートオブジェクト
            info: GraphQLの実行情報
            objectName: オブジェクト名
            modName: モディファイア名
            
        Returns:
            Dict: 削除結果
        """
        self.logger.debug(f"delete_modifier リゾルバが呼び出されました: object={objectName}, modifier={modName}")
        
        # オブジェクトの検索
        blender_obj = ensure_object_exists(objectName)
        if not blender_obj:
            return self.error_response(f"オブジェクト '{objectName}' が見つかりません")
        
        # モディファイアの検索
        if modName not in blender_obj.modifiers:
            return self.error_response(f"モディファイア '{modName}' が見つかりません")
        
        # モディファイアデータを取得（返却用）
        mod_data = self._get_modifier_data(blender_obj.modifiers[modName])
        
        # モディファイアを削除
        blender_obj.modifiers.remove(blender_obj.modifiers[modName])
        
        return self.success_response(
            f"モディファイア '{modName}' をオブジェクト '{objectName}' から削除しました",
            {'modifier': mod_data}
        )
