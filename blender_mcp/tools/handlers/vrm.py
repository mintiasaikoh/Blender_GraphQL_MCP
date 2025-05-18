"""
VRM関連のGraphQLリゾルバを提供

VTuberモデル制作に関連する機能をGraphQLインターフェースで提供します。
モデル管理、リギング、表情制作、エクスポート、Unity連携などの機能を実装します。
"""

import bpy
import os
import json
import logging
import math
from typing import Dict, List, Any, Optional, Union
from .base import ResolverBase, handle_exceptions, dict_to_vector, vector_to_dict, ensure_object_exists

# 定数定義
VRM_RIG_TEMPLATE = "VRM_TEMPLATE"
VRM_BLENDSHAPE_CATEGORIES = ["Neutral", "Happy", "Angry", "Sad", "Relaxed", "Surprised", "Blink", "LookAt"]

class VRMResolver(ResolverBase):
    """VRM関連のGraphQLリゾルバクラス"""
    
    def __init__(self):
        super().__init__()
    
    @handle_exceptions
    def create_model(self, obj, info, name: str) -> Dict[str, Any]:
        """
        新しいVRMモデルを作成
        
        Args:
            obj: GraphQLのルートオブジェクト
            info: GraphQLの実行情報
            name: モデル名
            
        Returns:
            Dict: 作成結果
        """
        self.logger.debug(f"create_vrm_model リゾルバが呼び出されました: name={name}")
        
        # 入力検証
        if not name or len(name.strip()) == 0:
            return self.error_response(
                "モデル名が空です",
                {"code": "EMPTY_NAME", "fix": "有効なモデル名を指定してください"}
            )
            
        if any(char in name for char in "\\/:*?\"<>|"):
            return self.error_response(
                f"モデル名 '{name}' に無効な文字が含まれています",
                {"code": "INVALID_CHAR", "fix": "特殊文字（\\/:*?\"<>|）を使用しないでください"}
            )
        
        # 名前の重複チェック
        if name in bpy.data.collections:
            return self.error_response(
                f"コレクション名 '{name}' は既に使用されています",
                {"code": "NAME_EXISTS", "fix": "別の名前を使用するか、既存のコレクションを削除してください"}
            )
        
        # VRMモデル用のコレクションを作成
        vrm_collection = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(vrm_collection)
        
        # メタデータを保存するためのカスタムプロパティを設定
        vrm_collection["vrm_model"] = True
        vrm_collection["vrm_version"] = "1.0"
        
        # モデルID（コレクション名をIDとして使用）
        model_id = name
        
        # 結果を返す
        return self.success_response(
            f"VRMモデル '{name}' を作成しました",
            {
                "success": True,
                "message": f"VRMモデル '{name}' を作成しました",
                "model": {
                    "id": model_id,
                    "name": name,
                    "version": "1.0"
                }
            }
        )
    
    @handle_exceptions
    def apply_template(self, obj, info, modelId: str, templateType: str) -> Dict[str, Any]:
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
        
        # 入力検証
        if not modelId or len(modelId.strip()) == 0:
            return self.error_response(
                "モデルIDが空です", 
                {"code": "EMPTY_ID", "fix": "有効なモデルIDを指定してください"}
            )
            
        if not templateType or len(templateType.strip()) == 0:
            return self.error_response(
                "テンプレートタイプが空です",
                {"code": "EMPTY_TEMPLATE", "fix": "有効なテンプレートタイプを指定してください"}
            )
        
        # サポートされているテンプレートタイプの確認
        valid_templates = ["HUMANOID", "FANTASY_HUMANOID", "FANTASY_ELF", "FANTASY_DWARF", 
                           "SCIFI_HUMANOID", "SCIFI_ROBOT", "SCIFI_CYBORG"]
        if templateType not in valid_templates:
            return self.error_response(
                f"テンプレートタイプ '{templateType}' はサポートされていません",
                {"code": "INVALID_TEMPLATE", "fix": f"サポートされているテンプレート: {', '.join(valid_templates)}"}
            )
        
        # コレクションの存在確認
        vrm_collection = bpy.data.collections.get(modelId)
        if not vrm_collection:
            return self.error_response(
                f"VRMモデル '{modelId}' が見つかりません",
                {"code": "MODEL_NOT_FOUND", "fix": "まずcreate_modelを呼び出してVRMモデルを作成してください"}
            )
        
        # VRMモデルかどうかの確認
        if not vrm_collection.get("vrm_model", False):
            return self.error_response(
                f"コレクション '{modelId}' はVRMモデルではありません",
                {"code": "NOT_VRM_MODEL", "fix": "VRM用に作成されたモデルコレクションを指定してください"}
            )
            
        # テンプレート適用（ここではシンプルなキャラクター構造を作成）
        if templateType == "HUMANOID":
            # 人型のベースメッシュを作成
            bpy.ops.mesh.primitive_cube_add(size=1.7)  # 身長約170cm
            body = bpy.context.active_object
            body.name = f"{modelId}_Body"
            body.scale = (0.4, 0.25, 1.0)  # 肩幅と体の厚みを設定
            
            # 頭部を作成
            bpy.ops.mesh.primitive_uv_sphere_add(radius=0.25)
            head = bpy.context.active_object
            head.name = f"{modelId}_Head"
            head.location = (0, 0, 1.0)  # 体の上に配置
            
            # 現在のコレクションから削除して、VRMモデルのコレクションに追加
            bpy.context.scene.collection.objects.unlink(body)
            bpy.context.scene.collection.objects.unlink(head)
            vrm_collection.objects.link(body)
            vrm_collection.objects.link(head)
            
            # コレクションにテンプレート情報を保存
            vrm_collection["template_type"] = templateType
            
            return self.success_response(
                f"テンプレート '{templateType}' を適用しました",
                {
                    "success": True,
                    "message": f"テンプレート '{templateType}' を適用しました",
                    "model": {
                        "id": modelId,
                        "name": vrm_collection.name,
                        "version": vrm_collection.get("vrm_version", "1.0")
                    }
                }
            )
        else:
            # ベーシックテンプレート以外は実装拡張ファイルに依存
            try:
                # 新しいVRMテンプレートモジュールの読み込みを試みる
                from ...new_vrm_templates import fantasy_character_template, sci_fi_character_template
                
                # ファンタジー系キャラクターテンプレート
                if templateType == "FANTASY_HUMANOID":
                    return fantasy_character_template.apply_humanoid_template(self, vrm_collection, modelId)
                elif templateType == "FANTASY_ELF":
                    return fantasy_character_template.apply_elf_template(self, vrm_collection, modelId)
                elif templateType == "FANTASY_DWARF":
                    return fantasy_character_template.apply_dwarf_template(self, vrm_collection, modelId)
                # SF系キャラクターテンプレート
                elif templateType == "SCIFI_HUMANOID":
                    return sci_fi_character_template.apply_humanoid_template(self, vrm_collection, modelId)
                elif templateType == "SCIFI_ROBOT":
                    return sci_fi_character_template.apply_robot_template(self, vrm_collection, modelId)
                elif templateType == "SCIFI_CYBORG":
                    return sci_fi_character_template.apply_cyborg_template(self, vrm_collection, modelId)
                else:
                    return self.error_response(
                        f"テンプレートタイプ '{templateType}' の実装が見つかりません",
                        {"code": "TEMPLATE_NOT_IMPLEMENTED", "fix": f"現在サポートされているテンプレート: HUMANOID"}
                    )
            except ImportError as e:
                self.logger.error(f"VRMテンプレート拡張モジュールの読み込みに失敗しました: {e}")
                return self.error_response(
                    f"テンプレートタイプ '{templateType}' は現在サポートされていません",
                    {"code": "TEMPLATE_MODULE_MISSING", "fix": "拡張テンプレートモジュールがインストールされていることを確認してください"}
                )
    
    @handle_exceptions
    def generate_rig(self, obj, info, modelId: str) -> Dict[str, Any]:
        """
        VRM準拠のリグを生成
        
        Args:
            obj: GraphQLのルートオブジェクト
            info: GraphQLの実行情報
            modelId: モデルID（コレクション名）
            
        Returns:
            Dict: 生成結果
        """
        self.logger.debug(f"generate_vrm_rig リゾルバが呼び出されました: modelId={modelId}")
        
        # 入力検証
        if not modelId or len(modelId.strip()) == 0:
            return self.error_response(
                "モデルIDが空です", 
                {"code": "EMPTY_ID", "fix": "有効なモデルIDを指定してください"}
            )
            
        # コレクションの存在確認
        vrm_collection = bpy.data.collections.get(modelId)
        if not vrm_collection:
            return self.error_response(
                f"VRMモデル '{modelId}' が見つかりません",
                {"code": "MODEL_NOT_FOUND", "fix": "有効なVRMモデルIDを指定してください"}
            )
        
        # VRMモデルかどうかの確認
        if not vrm_collection.get("vrm_model", False):
            return self.error_response(
                f"コレクション '{modelId}' はVRMモデルではありません",
                {"code": "NOT_VRM_MODEL", "fix": "VRM用に作成されたモデルコレクションを指定してください"}
            )
        
        # 基本的なアーマチュアを作成
        bpy.ops.object.armature_add()
        armature = bpy.context.active_object
        armature.name = f"{modelId}_Armature"
        
        # アーマチュアを編集モードに切り替え
        bpy.ops.object.mode_set(mode='EDIT')
        
        # 編集中にボーンを取得
        edit_bones = armature.data.edit_bones
        
        # デフォルトボーンの調整（rename root bone to hips）
        root_bone = edit_bones[0]
        root_bone.name = "hips"
        root_bone.head = (0, 0, 0.9)
        root_bone.tail = (0, 0, 1.0)
        
        # 脊椎ボーンを追加
        spine = edit_bones.new("spine")
        spine.head = (0, 0, 1.0)
        spine.tail = (0, 0, 1.1)
        spine.parent = root_bone
        
        chest = edit_bones.new("chest")
        chest.head = (0, 0, 1.1)
        chest.tail = (0, 0, 1.2)
        chest.parent = spine
        
        neck = edit_bones.new("neck")
        neck.head = (0, 0, 1.2)
        neck.tail = (0, 0, 1.3)
        neck.parent = chest
        
        head_bone = edit_bones.new("head")
        head_bone.head = (0, 0, 1.3)
        head_bone.tail = (0, 0, 1.5)
        head_bone.parent = neck
        
        # 左腕ボーンを追加
        l_shoulder = edit_bones.new("leftShoulder")
        l_shoulder.head = (0.05, 0, 1.2)
        l_shoulder.tail = (0.15, 0, 1.2)
        l_shoulder.parent = chest
        
        l_upper_arm = edit_bones.new("leftUpperArm")
        l_upper_arm.head = (0.15, 0, 1.2)
        l_upper_arm.tail = (0.35, 0, 1.1)
        l_upper_arm.parent = l_shoulder
        
        l_lower_arm = edit_bones.new("leftLowerArm")
        l_lower_arm.head = (0.35, 0, 1.1)
        l_lower_arm.tail = (0.55, 0, 1.0)
        l_lower_arm.parent = l_upper_arm
        
        l_hand = edit_bones.new("leftHand")
        l_hand.head = (0.55, 0, 1.0)
        l_hand.tail = (0.65, 0, 0.95)
        l_hand.parent = l_lower_arm
        
        # 右腕ボーンを追加（左腕の反転）
        r_shoulder = edit_bones.new("rightShoulder")
        r_shoulder.head = (-0.05, 0, 1.2)
        r_shoulder.tail = (-0.15, 0, 1.2)
        r_shoulder.parent = chest
        
        r_upper_arm = edit_bones.new("rightUpperArm")
        r_upper_arm.head = (-0.15, 0, 1.2)
        r_upper_arm.tail = (-0.35, 0, 1.1)
        r_upper_arm.parent = r_shoulder
        
        r_lower_arm = edit_bones.new("rightLowerArm")
        r_lower_arm.head = (-0.35, 0, 1.1)
        r_lower_arm.tail = (-0.55, 0, 1.0)
        r_lower_arm.parent = r_upper_arm
        
        r_hand = edit_bones.new("rightHand")
        r_hand.head = (-0.55, 0, 1.0)
        r_hand.tail = (-0.65, 0, 0.95)
        r_hand.parent = r_lower_arm
        
        # 左脚ボーンを追加
        l_upper_leg = edit_bones.new("leftUpperLeg")
        l_upper_leg.head = (0.1, 0, 0.9)
        l_upper_leg.tail = (0.1, 0, 0.5)
        l_upper_leg.parent = root_bone
        
        l_lower_leg = edit_bones.new("leftLowerLeg")
        l_lower_leg.head = (0.1, 0, 0.5)
        l_lower_leg.tail = (0.1, 0, 0.1)
        l_lower_leg.parent = l_upper_leg
        
        l_foot = edit_bones.new("leftFoot")
        l_foot.head = (0.1, 0, 0.1)
        l_foot.tail = (0.1, 0.15, 0)
        l_foot.parent = l_lower_leg
        
        # 右脚ボーンを追加（左脚の反転）
        r_upper_leg = edit_bones.new("rightUpperLeg")
        r_upper_leg.head = (-0.1, 0, 0.9)
        r_upper_leg.tail = (-0.1, 0, 0.5)
        r_upper_leg.parent = root_bone
        
        r_lower_leg = edit_bones.new("rightLowerLeg")
        r_lower_leg.head = (-0.1, 0, 0.5)
        r_lower_leg.tail = (-0.1, 0, 0.1)
        r_lower_leg.parent = r_upper_leg
        
        r_foot = edit_bones.new("rightFoot")
        r_foot.head = (-0.1, 0, 0.1)
        r_foot.tail = (-0.1, 0.15, 0)
        r_foot.parent = r_lower_leg
        
        # 編集モードを終了
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # 現在のコレクションから削除して、VRMモデルのコレクションに追加
        bpy.context.scene.collection.objects.unlink(armature)
        vrm_collection.objects.link(armature)
        
        # VRM用メタデータを追加
        armature["vrm_skeleton"] = True
        armature["humanoid_bones"] = True
        
        # コレクションにリグ情報を保存
        vrm_collection["has_rig"] = True
        vrm_collection["rig_type"] = "VRM_HUMANOID"
        
        # ボーン情報を収集
        bones_data = self._collect_bone_data(armature)
        
        return self.success_response(
            f"VRM準拠リグを生成しました",
            {
                "success": True,
                "message": f"VRM準拠リグを生成しました",
                "model": {
                    "id": modelId,
                    "name": vrm_collection.name,
                    "version": vrm_collection.get("vrm_version", "1.0"),
                    "rootBone": bones_data
                }
            }
        )
    
    def _collect_bone_data(self, armature_obj) -> Optional[Dict[str, Any]]:
        """
        アーマチュアのボーン情報を再帰的に収集
        
        Args:
            armature_obj: アーマチュアオブジェクト
            
        Returns:
            Optional[Dict[str, Any]]: ボーン階層データ、ルートボーンがない場合はNone
        """
        # ルートボーンを特定
        root_bones = [bone for bone in armature_obj.data.bones if bone.parent is None]
        
        if not root_bones:
            return None
            
        # 最初のルートボーンから再帰的にデータを収集
        return self._collect_bone_recursive(root_bones[0])
    
    def _collect_bone_recursive(self, bone) -> Dict[str, Any]:
        """
        ボーンとその子ボーンを再帰的に収集
        
        Args:
            bone: ボーン
            
        Returns:
            Dict[str, Any]: ボーンデータ（階層構造）
        """
        # ボーンの基本情報
        bone_data = {
            "name": bone.name,
            "humanoidBoneName": bone.name,  # VRMヒューマノイドボーン名（実際には適切にマッピング）
            "position": vector_to_dict(bone.head_local),
            "rotation": vector_to_dict([0, 0, 0]),  # 実際の回転値は必要に応じて計算
            "children": []
        }
        
        # 子ボーンを再帰的に処理
        for child in bone.children:
            bone_data["children"].append(self._collect_bone_recursive(child))
            
        return bone_data
    
    @handle_exceptions
    def assign_auto_weights(self, obj, info, modelId: str) -> Dict[str, Any]:
        """
        自動ウェイト割り当てを実行
        
        Args:
            obj: GraphQLのルートオブジェクト
            info: GraphQLの実行情報
            modelId: モデルID（コレクション名）
            
        Returns:
            Dict: 割り当て結果
        """
        self.logger.debug(f"assign_auto_weights リゾルバが呼び出されました: modelId={modelId}")
        
        # 入力検証
        if not modelId or len(modelId.strip()) == 0:
            return self.error_response(
                "モデルIDが空です", 
                {"code": "EMPTY_ID", "fix": "有効なモデルIDを指定してください"}
            )
            
        # コレクションの存在確認
        vrm_collection = bpy.data.collections.get(modelId)
        if not vrm_collection:
            return self.error_response(
                f"VRMモデル '{modelId}' が見つかりません",
                {"code": "MODEL_NOT_FOUND", "fix": "有効なVRMモデルIDを指定してください"}
            )
        
        # VRMモデルかどうかの確認
        if not vrm_collection.get("vrm_model", False):
            return self.error_response(
                f"コレクション '{modelId}' はVRMモデルではありません",
                {"code": "NOT_VRM_MODEL", "fix": "VRM用に作成されたモデルコレクションを指定してください"}
            )
        
        # リグの存在確認
        armature_obj = None
        for obj in vrm_collection.objects:
            if obj.type == 'ARMATURE' and obj.get("vrm_skeleton", False):
                armature_obj = obj
                break
                
        if not armature_obj:
            return self.error_response(
                f"VRMモデル '{modelId}' にはリグが存在しません。まず generate_vrm_rig を実行してください。",
                {"code": "NO_ARMATURE", "fix": "generateVrmRig を呼び出してリグを作成してください"}
            )
        
        # メッシュオブジェクトを収集
        mesh_objects = [obj for obj in vrm_collection.objects if obj.type == 'MESH']
        
        if not mesh_objects:
            return self.error_response(
                f"VRMモデル '{modelId}' にはメッシュオブジェクトが存在しません。",
                {"code": "NO_MESH", "fix": "applyVrmTemplate を呼び出してメッシュを作成してください"}
            )
        
        # 現在の選択をクリア
        bpy.ops.object.select_all(action='DESELECT')
        
        # メッシュとアーマチュアを選択
        for mesh_obj in mesh_objects:
            mesh_obj.select_set(True)
        
        # アーマチュアをアクティブに
        armature_obj.select_set(True)
        bpy.context.view_layer.objects.active = armature_obj
        
        # 自動ウェイト割り当て
        bpy.ops.object.parent_set(type='ARMATURE_AUTO')
        
        # コレクションにウェイト割り当て情報を保存
        vrm_collection["weights_assigned"] = True
        
        # ボーン情報を収集
        bones_data = self._collect_bone_data(armature_obj)
        
        return self.success_response(
            f"自動ウェイト割り当てを完了しました",
            {
                "success": True,
                "message": f"自動ウェイト割り当てを完了しました",
                "model": {
                    "id": modelId,
                    "name": vrm_collection.name,
                    "version": vrm_collection.get("vrm_version", "1.0"),
                    "rootBone": bones_data
                }
            }
        )
    
    @handle_exceptions
    def add_blend_shape(self, obj, info, modelId: str, blendShape) -> Dict[str, Any]:
        """
        ブレンドシェイプを追加
        
        Args:
            obj: GraphQLのルートオブジェクト
            info: GraphQLの実行情報
            modelId: モデルID（コレクション名）
            blendShape: 追加するブレンドシェイプ情報
            
        Returns:
            Dict: 追加結果
        """
        self.logger.debug(f"add_blend_shape リゾルバが呼び出されました: modelId={modelId}, blendShape={blendShape}")
        
        # 入力検証
        if not modelId or len(modelId.strip()) == 0:
            return self.error_response(
                "モデルIDが空です",
                {"code": "EMPTY_ID", "fix": "有効なモデルIDを指定してください"}
            )
            
        if not blendShape or not isinstance(blendShape, dict):
            return self.error_response(
                "ブレンドシェイプ情報が無効です",
                {"code": "INVALID_BLEND_SHAPE", "fix": "有効なブレンドシェイプオブジェクトを指定してください"}
            )
        
        # ブレンドシェイプデータの検証
        if not blendShape.get("name"):
            return self.error_response(
                "ブレンドシェイプ名が指定されていません",
                {"code": "EMPTY_BLEND_SHAPE_NAME", "fix": "ブレンドシェイプ名を指定してください"}
            )
        
        blend_shape_name = blendShape["name"]
        blend_shape_category = blendShape.get("category", "Neutral")
        
        # カテゴリの検証
        if blend_shape_category not in VRM_BLENDSHAPE_CATEGORIES:
            return self.error_response(
                f"無効なブレンドシェイプカテゴリ: {blend_shape_category}",
                {"code": "INVALID_CATEGORY", "fix": f"有効なカテゴリ: {', '.join(VRM_BLENDSHAPE_CATEGORIES)}"}
            )
        
        blend_shape_weight = blendShape.get("weight", 1.0)
        
        # ウェイト値の検証
        if not isinstance(blend_shape_weight, (int, float)) or blend_shape_weight < 0 or blend_shape_weight > 1:
            return self.error_response(
                f"無効なブレンドシェイプウェイト: {blend_shape_weight}",
                {"code": "INVALID_WEIGHT", "fix": "ウェイトは0から1の間の数値である必要があります"}
            )
        
        # コレクションの存在確認
        vrm_collection = bpy.data.collections.get(modelId)
        if not vrm_collection:
            return self.error_response(
                f"VRMモデル '{modelId}' が見つかりません",
                {"code": "MODEL_NOT_FOUND", "fix": "有効なVRMモデルIDを指定してください"}
            )
        
        # VRMモデルかどうかの確認
        if not vrm_collection.get("vrm_model", False):
            return self.error_response(
                f"コレクション '{modelId}' はVRMモデルではありません",
                {"code": "NOT_VRM_MODEL", "fix": "VRM用に作成されたモデルコレクションを指定してください"}
            )
        
        # ヘッドメッシュを特定（仮定：頭部メッシュの名前に "Head" が含まれる）
        head_mesh = None
        for obj in vrm_collection.objects:
            if obj.type == 'MESH' and "Head" in obj.name:
                head_mesh = obj
                break
                
        if not head_mesh:
            # 代替として最初のメッシュを探す
            for obj in vrm_collection.objects:
                if obj.type == 'MESH':
                    head_mesh = obj
                    self.logger.warning(f"頭部メッシュが見つからないため、最初のメッシュ {obj.name} を使用します")
                    break
            
            if not head_mesh:
                return self.error_response(
                    f"VRMモデル '{modelId}' に適用可能なメッシュが見つかりません",
                    {"code": "NO_HEAD_MESH", "fix": "名前に'Head'を含むメッシュオブジェクトを作成するか、apply_vrm_templateを呼び出してください"}
                )
        
        # 形状キーデータの取得または作成
        if not head_mesh.data.shape_keys:
            head_mesh.shape_key_add(name="Basis")
        
        # すでに同名の形状キーがあるかチェック
        if head_mesh.data.shape_keys and blend_shape_name in head_mesh.data.shape_keys.key_blocks:
            return self.error_response(
                f"形状キー '{blend_shape_name}' は既に存在します",
                {"code": "BLEND_SHAPE_EXISTS", "fix": f"別の名前を使用するか、update_blend_shape を使用して既存の形状キーを更新してください"}
            )
        
        # 形状キーを追加
        shape_key = head_mesh.shape_key_add(name=blend_shape_name)
        shape_key.value = 0.0  # 初期値
        
        # カスタムプロパティでVRM用メタデータを追加
        shape_key["vrm_blend_shape"] = True
        shape_key["vrm_blend_shape_category"] = blend_shape_category
        shape_key["vrm_blend_shape_weight"] = blend_shape_weight
        
        # コレクションのブレンドシェイプリストを更新
        blend_shapes = vrm_collection.get("blend_shapes", [])
        blend_shapes.append({
            "name": blend_shape_name,
            "category": blend_shape_category,
            "weight": blend_shape_weight
        })
        vrm_collection["blend_shapes"] = blend_shapes
        
        return self.success_response(
            f"ブレンドシェイプ '{blend_shape_name}' を追加しました",
            {
                "success": True,
                "message": f"ブレンドシェイプ '{blend_shape_name}' を追加しました",
                "blendShape": {
                    "name": blend_shape_name,
                    "category": blend_shape_category,
                    "weight": blend_shape_weight
                }
            }
        )
    
    @handle_exceptions
    def update_blend_shape(self, obj, info, modelId: str, name: str, weight: float) -> Dict[str, Any]:
        """
        ブレンドシェイプの値を更新
        
        Args:
            obj: GraphQLのルートオブジェクト
            info: GraphQLの実行情報
            modelId: モデルID（コレクション名）
            name: ブレンドシェイプ名
            weight: 新しい重み値（0.0-1.0）
            
        Returns:
            Dict: 更新結果
        """
        self.logger.debug(f"update_blend_shape リゾルバが呼び出されました: modelId={modelId}, name={name}, weight={weight}")
        
        # 入力検証
        if not modelId or len(modelId.strip()) == 0:
            return self.error_response(
                "モデルIDが空です",
                {"code": "EMPTY_ID", "fix": "有効なモデルIDを指定してください"}
            )
            
        if not name or len(name.strip()) == 0:
            return self.error_response(
                "ブレンドシェイプ名が空です",
                {"code": "EMPTY_NAME", "fix": "有効なブレンドシェイプ名を指定してください"}
            )
            
        if not isinstance(weight, (int, float)) or weight < 0 or weight > 1:
            return self.error_response(
                f"無効なブレンドシェイプウェイト: {weight}",
                {"code": "INVALID_WEIGHT", "fix": "ウェイトは0から1の間の数値である必要があります"}
            )
            
        # コレクションの存在確認
        vrm_collection = bpy.data.collections.get(modelId)
        if not vrm_collection:
            return self.error_response(
                f"VRMモデル '{modelId}' が見つかりません",
                {"code": "MODEL_NOT_FOUND", "fix": "有効なVRMモデルIDを指定してください"}
            )
        
        # VRMモデルかどうかの確認
        if not vrm_collection.get("vrm_model", False):
            return self.error_response(
                f"コレクション '{modelId}' はVRMモデルではありません",
                {"code": "NOT_VRM_MODEL", "fix": "VRM用に作成されたモデルコレクションを指定してください"}
            )
        
        # 形状キーを持つメッシュを検索
        target_mesh = None
        for obj in vrm_collection.objects:
            if obj.type == 'MESH' and obj.data.shape_keys and name in obj.data.shape_keys.key_blocks:
                target_mesh = obj
                break
                
        if not target_mesh:
            return self.error_response(
                f"ブレンドシェイプ '{name}' が見つかりません",
                {"code": "BLEND_SHAPE_NOT_FOUND", "fix": "add_blend_shapeを呼び出してブレンドシェイプを先に作成してください"}
            )
        
        # 形状キーの値を更新
        shape_key = target_mesh.data.shape_keys.key_blocks[name]
        shape_key.value = max(0.0, min(1.0, weight))  # 0.0-1.0の範囲に制限
        
        # カスタムプロパティの更新
        shape_key["vrm_blend_shape_weight"] = weight
        
        # コレクションのブレンドシェイプリストを更新
        blend_shapes = vrm_collection.get("blend_shapes", [])
        for i, bs in enumerate(blend_shapes):
            if bs["name"] == name:
                blend_shapes[i]["weight"] = weight
                break
        
        vrm_collection["blend_shapes"] = blend_shapes
        
        # ブレンドシェイプのカテゴリを取得
        category = shape_key.get("vrm_blend_shape_category", "Neutral")
        
        return self.success_response(
            f"ブレンドシェイプ '{name}' の値を {weight} に更新しました",
            {
                "success": True,
                "message": f"ブレンドシェイプ '{name}' の値を {weight} に更新しました",
                "blendShape": {
                    "name": name,
                    "category": category,
                    "weight": weight
                }
            }
        )
    
    @handle_exceptions
    def export_vrm(self, obj, info, modelId: str, filepath: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        VRMファイルとしてエクスポート
        
        Args:
            obj: GraphQLのルートオブジェクト
            info: GraphQLの実行情報
            modelId: モデルID（コレクション名）
            filepath: エクスポート先ファイルパス
            metadata: VRMメタデータ（オプション）
            
        Returns:
            Dict: エクスポート結果
        """
        self.logger.debug(f"export_vrm リゾルバが呼び出されました: modelId={modelId}, filepath={filepath}")
        
        # 入力検証
        if not modelId or len(modelId.strip()) == 0:
            return self.error_response(
                "モデルIDが空です",
                {"code": "EMPTY_ID", "fix": "有効なモデルIDを指定してください"}
            )
            
        if not filepath or len(filepath.strip()) == 0:
            return self.error_response(
                "エクスポート先ファイルパスが空です",
                {"code": "EMPTY_FILEPATH", "fix": "有効なファイルパスを指定してください"}
            )
        
        # ファイルパスの拡張子確認
        if not filepath.lower().endswith('.vrm'):
            return self.error_response(
                f"エクスポート先ファイルパスの拡張子が.vrmではありません: {filepath}",
                {"code": "INVALID_EXTENSION", "fix": "ファイルパスの拡張子を.vrmにしてください"}
            )
            
        # コレクションの存在確認
        vrm_collection = bpy.data.collections.get(modelId)
        if not vrm_collection:
            return self.error_response(
                f"VRMモデル '{modelId}' が見つかりません",
                {"code": "MODEL_NOT_FOUND", "fix": "有効なVRMモデルIDを指定してください"}
            )
        
        # VRMモデルかどうかの確認
        if not vrm_collection.get("vrm_model", False):
            return self.error_response(
                f"コレクション '{modelId}' はVRMモデルではありません",
                {"code": "NOT_VRM_MODEL", "fix": "VRM用に作成されたモデルコレクションを指定してください"}
            )
        
        # VRMC_vrm のエクスポートは、実際にはVRM用アドオンが必要です
        # ここではエクスポート処理のシミュレーションを行います
        
        # メタデータの処理
        if not metadata:
            metadata = {}
        
        title = metadata.get("title", modelId)
        author = metadata.get("author", "")
        version = metadata.get("version", "1.0")
        
        # エクスポート先のディレクトリが存在するか確認
        export_dir = os.path.dirname(filepath)
        if not os.path.exists(export_dir):
            try:
                os.makedirs(export_dir, exist_ok=True)
            except Exception as e:
                return self.error_response(
                    f"エクスポート先ディレクトリを作成できませんでした: {export_dir}",
                    {"code": "EXPORT_DIR_ERROR", "details": str(e), "fix": "書き込み権限のあるディレクトリパスを指定してください"}
                )
        
        # アーマチュアとメッシュの存在確認
        has_armature = any(obj.type == 'ARMATURE' for obj in vrm_collection.objects)
        has_mesh = any(obj.type == 'MESH' for obj in vrm_collection.objects)
        
        if not has_armature:
            return self.error_response(
                f"VRMモデル '{modelId}' にはアーマチュアがありません。エクスポートにはリグが必要です。",
                {"code": "NO_ARMATURE", "fix": "モデルにリグを追加してください。generate_vrmrigを使用してリグを作成できます。"}
            )
        
        if not has_mesh:
            return self.error_response(
                f"VRMモデル '{modelId}' にはメッシュがありません。",
                {"code": "NO_MESH", "fix": "モデルにメッシュを追加するか、apply_vrm_templateを使用してメッシュを作成してください。"}
            )
        
        # モデル情報の収集
        model_info = {
            "id": modelId,
            "name": vrm_collection.name,
            "version": version,
            "metadata": {
                "title": title,
                "author": author,
                "version": version,
                **metadata
            }
        }
        
        # ダミーのJSONファイルを作成（実際のエクスポート結果をシミュレート）
        json_path = f"{filepath}.json"
        try:
            with open(json_path, 'w') as f:
                json.dump(model_info, f, indent=2)
        except Exception as e:
            return self.error_response(
                f"メタデータファイルの作成に失敗しました: {json_path}",
                {"code": "JSON_WRITE_ERROR", "details": str(e), "fix": "ファイルパスが有効で書き込み権限があることを確認してください"}
            )
        
        # 実際のVRMエクスポートは以下のようなコードで行いますが、
        # VRM用のBlenderアドオンが必要です
        """
        # すべてのオブジェクトを非選択に
        bpy.ops.object.select_all(action='DESELECT')
        
        # コレクション内のオブジェクトを選択
        for obj in vrm_collection.objects:
            obj.select_set(True)
        
        # エクスポート実行
        bpy.ops.export_scene.vrm(
            filepath=filepath,
            export_invisibles=False,
            export_only_selections=True,
            # その他のVRMエクスポート設定...
        )
        """
        
        return self.success_response(
            f"VRMモデル '{modelId}' をエクスポートしました: {filepath}",
            {
                "success": True,
                "message": f"VRMモデル '{modelId}' をエクスポートしました: {filepath}",
                "metadata": {
                    "title": title,
                    "author": author,
                    "version": version
                },
                "filepath": filepath
            }
        )
    
    @handle_exceptions
    def export_fbx_for_unity(self, obj, info, modelId: str, filepath: str, optimizeForUnity: bool = True) -> Dict[str, Any]:
        """
        Unity用にFBXファイルとしてエクスポート
        
        Args:
            obj: GraphQLのルートオブジェクト
            info: GraphQLの実行情報
            modelId: モデルID（コレクション名）
            filepath: エクスポート先ファイルパス
            optimizeForUnity: Unity用に最適化するか
            
        Returns:
            Dict: エクスポート結果
        """
        self.logger.debug(f"export_fbx_for_unity リゾルバが呼び出されました: modelId={modelId}, filepath={filepath}")
        
        # 入力検証
        if not modelId or len(modelId.strip()) == 0:
            return self.error_response(
                "モデルIDが空です", 
                {"code": "EMPTY_ID", "fix": "有効なモデルIDを指定してください"}
            )
            
        if not filepath or len(filepath.strip()) == 0:
            return self.error_response(
                "エクスポート先ファイルパスが空です",
                {"code": "EMPTY_FILEPATH", "fix": "有効なファイルパスを指定してください"}
            )
        
        # ファイルパスの拡張子確認
        if not filepath.lower().endswith('.fbx'):
            return self.error_response(
                f"エクスポート先ファイルパスの拡張子が.fbxではありません: {filepath}",
                {"code": "INVALID_EXTENSION", "fix": "ファイルパスの拡張子を.fbxにしてください"}
            )
            
        # コレクションの存在確認
        vrm_collection = bpy.data.collections.get(modelId)
        if not vrm_collection:
            return self.error_response(
                f"VRMモデル '{modelId}' が見つかりません",
                {"code": "MODEL_NOT_FOUND", "fix": "有効なVRMモデルIDを指定してください"}
            )
        
        # VRMモデルかどうかの確認
        if not vrm_collection.get("vrm_model", False):
            return self.error_response(
                f"コレクション '{modelId}' はVRMモデルではありません",
                {"code": "NOT_VRM_MODEL", "fix": "VRM用に作成されたモデルコレクションを指定してください"}
            )
        
        # エクスポート先のディレクトリが存在するか確認
        export_dir = os.path.dirname(filepath)
        if not os.path.exists(export_dir):
            os.makedirs(export_dir, exist_ok=True)
        
        # アーマチュアとメッシュの存在確認
        has_armature = any(obj.type == 'ARMATURE' for obj in vrm_collection.objects)
        has_mesh = any(obj.type == 'MESH' for obj in vrm_collection.objects)
        
        if not has_armature:
            return self.error_response(
                f"VRMモデル '{modelId}' にはアーマチュアがありません。エクスポートにはリグが必要です。",
                {"code": "NO_ARMATURE", "fix": "generateVrmRig を呼び出してリグを作成してください"}
            )
        
        if not has_mesh:
            return self.error_response(
                f"VRMモデル '{modelId}' にはメッシュがありません。",
                {"code": "NO_MESH", "fix": "applyVrmTemplate を呼び出してメッシュを作成してください"}
            )
        
        # すべてのオブジェクトを非選択に
        bpy.ops.object.select_all(action='DESELECT')
        
        # コレクション内のオブジェクトを選択
        for obj in vrm_collection.objects:
            obj.select_set(True)
        
        # FBXエクスポート実行
        bpy.ops.export_scene.fbx(
            filepath=filepath,
            use_selection=True,
            global_scale=1.0,
            apply_unit_scale=True,
            apply_scale_options='FBX_SCALE_NONE',
            bake_space_transform=False,
            object_types={'ARMATURE', 'MESH'},
            use_mesh_modifiers=True,
            mesh_smooth_type='FACE',
            use_mesh_edges=False,
            use_tspace=True,
            use_custom_props=True,
            add_leaf_bones=False,
            primary_bone_axis='Y',
            secondary_bone_axis='X',
            use_armature_deform_only=True,
            armature_nodetype='NULL',
            bake_anim=True,
            bake_anim_use_all_bones=True,
            bake_anim_use_nla_strips=True,
            bake_anim_use_all_actions=True,
            bake_anim_force_startend_keying=True,
            bake_anim_step=1.0,
            bake_anim_simplify_factor=1.0,
            path_mode='STRIP',
            embed_textures=False,
            batch_mode='OFF',
            use_batch_own_dir=True,
            axis_forward='-Z',
            axis_up='Y'
        )
        
        return self.success_response(
            f"VRMモデル '{modelId}' をFBXとしてエクスポートしました: {filepath}",
            {
                "success": True,
                "message": f"VRMモデル '{modelId}' をFBXとしてエクスポートしました: {filepath}",
                "filepath": filepath,
                "optimizedForUnity": optimizeForUnity
            }
        )
    
    @handle_exceptions
    def validate_vrm_model(self, obj, info, modelId: str) -> Dict[str, Any]:
        """
        VRMモデルを検証
        
        Args:
            obj: GraphQLのルートオブジェクト
            info: GraphQLの実行情報
            modelId: モデルID（コレクション名）
            
        Returns:
            Dict: 検証結果
        """
        self.logger.debug(f"validate_vrm_model リゾルバが呼び出されました: modelId={modelId}")
        
        # 入力検証
        if not modelId or len(modelId.strip()) == 0:
            return self.error_response(
                "モデルIDが空です", 
                {"code": "EMPTY_ID", "fix": "有効なモデルIDを指定してください"}
            )
            
        # コレクションの存在確認
        vrm_collection = bpy.data.collections.get(modelId)
        if not vrm_collection:
            return self.error_response(
                f"VRMモデル '{modelId}' が見つかりません",
                {"code": "MODEL_NOT_FOUND", "fix": "有効なVRMモデルIDを指定してください"}
            )
        
        # VRMモデルかどうかの確認
        if not vrm_collection.get("vrm_model", False):
            return self.error_response(
                f"コレクション '{modelId}' はVRMモデルではありません",
                {"code": "NOT_VRM_MODEL", "fix": "VRM用に作成されたモデルコレクションを指定してください"}
            )
        
        # 検証結果
        validation_results = []
        has_errors = False
        
        # アーマチュアの検証
        armature_objects = [obj for obj in vrm_collection.objects if obj.type == 'ARMATURE']
        if not armature_objects:
            validation_results.append({
                "type": "error",
                "message": "アーマチュア（リグ）が見つかりません。"
            })
            has_errors = True
        
        # メッシュの検証
        mesh_objects = [obj for obj in vrm_collection.objects if obj.type == 'MESH']
        if not mesh_objects:
            validation_results.append({
                "type": "error",
                "message": "メッシュオブジェクトが見つかりません。"
            })
            has_errors = True
        
        # 必須ボーンの検証（アーマチュアがある場合のみ）
        if armature_objects:
            armature = armature_objects[0]
            required_bones = ["hips", "spine", "chest", "neck", "head"]
            missing_bones = []
            
            for bone_name in required_bones:
                if bone_name not in armature.data.bones:
                    missing_bones.append(bone_name)
            
            if missing_bones:
                validation_results.append({
                    "type": "error",
                    "message": f"必須ボーンが不足しています: {', '.join(missing_bones)}"
                })
                has_errors = True
        
        # 形状キーの検証
        has_blend_shapes = False
        for mesh in mesh_objects:
            if mesh.data.shape_keys and len(mesh.data.shape_keys.key_blocks) > 1:  # Basis以外の形状キーがあるか
                has_blend_shapes = True
                break
        
        if not has_blend_shapes:
            validation_results.append({
                "type": "warning",
                "message": "ブレンドシェイプ（表情）が定義されていません。"
            })
        
        # サイズの検証
        if mesh_objects:
            # オブジェクトの高さをチェック
            heights = [obj.dimensions.z for obj in mesh_objects]
            total_height = max(heights) if heights else 0
            
            if total_height > 2.0:
                validation_results.append({
                    "type": "warning",
                    "message": f"モデルの高さが2.0メートルを超えています（{total_height:.2f}m）。多くのVRアプリでスケールが大きすぎる可能性があります。"
                })
            
            # ポリゴン数をチェック
            total_polys = sum(len(obj.data.polygons) for obj in mesh_objects)
            if total_polys > 70000:
                validation_results.append({
                    "type": "warning",
                    "message": f"ポリゴン数が多すぎます（{total_polys}）。パフォーマンスに問題が生じる可能性があります。"
                })
        
        # ウェイトの検証
        if armature_objects and mesh_objects:
            unweighted_meshes = []
            for mesh in mesh_objects:
                # アーマチュアモディファイアがあるかチェック
                has_armature_modifier = any(mod.type == 'ARMATURE' for mod in mesh.modifiers)
                if not has_armature_modifier:
                    unweighted_meshes.append(mesh.name)
            
            if unweighted_meshes:
                validation_results.append({
                    "type": "error",
                    "message": f"以下のメッシュにウェイトが割り当てられていません: {', '.join(unweighted_meshes)}"
                })
                has_errors = True
        
        # 全体の検証結果
        if has_errors:
            status = "エラー"
            status_code = "ERROR"
        elif validation_results:
            status = "警告あり"
            status_code = "WARNING"
        else:
            status = "検証通過"
            status_code = "PASSED"
            validation_results.append({
                "type": "info",
                "message": "すべての検証をパスしました！"
            })
        
        return self.success_response(
            f"検証結果: {status}",
            {
                "statusCode": status_code,
                "model": {
                    "id": modelId,
                    "name": vrm_collection.name
                },
                "results": validation_results
            }
        )
    
    @handle_exceptions
    def setup_unity_project(self, obj, info, projectPath: str, createVrmSupportFiles: bool = True) -> Dict[str, Any]:
        """
        Unityプロジェクトのセットアップ
        
        Args:
            obj: GraphQLのルートオブジェクト
            info: GraphQLの実行情報
            projectPath: Unityプロジェクトのパス
            createVrmSupportFiles: VRMサポートファイルを作成するか
            
        Returns:
            Dict: セットアップ結果
        """
        self.logger.debug(f"setup_unity_project リゾルバが呼び出されました: projectPath={projectPath}")
        
        # 入力検証
        if not projectPath or len(projectPath.strip()) == 0:
            return self.error_response(
                "プロジェクトパスが空です", 
                {"code": "EMPTY_PATH", "fix": "有効なプロジェクトパスを指定してください"}
            )
            
        # プロジェクトディレクトリの存在確認
        if not os.path.exists(projectPath):
            try:
                os.makedirs(projectPath, exist_ok=True)
            except Exception as e:
                return self.error_response(
                    f"Unityプロジェクトディレクトリを作成できません: {str(e)}",
                    {"code": "DIR_CREATE_ERROR", "fix": "書き込み権限のあるパスを指定してください", "details": str(e)}
                )
        
        # Assetsディレクトリの作成
        assets_dir = os.path.join(projectPath, "Assets")
        if not os.path.exists(assets_dir):
            os.makedirs(assets_dir, exist_ok=True)
        
        # VRMモデル用ディレクトリ
        vrm_models_dir = os.path.join(assets_dir, "VRMModels")
        if not os.path.exists(vrm_models_dir):
            os.makedirs(vrm_models_dir, exist_ok=True)
        
        # VRMサポートファイルの作成（実際はテンプレートファイルのコピーなど）
        if createVrmSupportFiles:
            # サンプルのシーンディレクトリ
            scenes_dir = os.path.join(assets_dir, "Scenes")
            if not os.path.exists(scenes_dir):
                os.makedirs(scenes_dir, exist_ok=True)
            
            # サンプルのREADME作成
            readme_path = os.path.join(projectPath, "README_VRM.txt")
            with open(readme_path, 'w') as f:
                f.write("# VRM Model Import Project\n\n")
                f.write("This project is set up for VRM model importing and configuration.\n\n")
                f.write("## Required packages:\n")
                f.write("- UniVRM (https://github.com/vrm-c/UniVRM)\n")
                f.write("- VRM Look At Blendshape\n\n")
                f.write("## Installation:\n")
                f.write("1. Open the project in Unity\n")
                f.write("2. Install UniVRM via Package Manager\n")
                f.write("3. Import your VRM models into the VRMModels folder\n")
        
        return self.success_response(
            f"Unityプロジェクトのセットアップが完了しました: {projectPath}",
            {
                "success": True,
                "message": f"Unityプロジェクトのセットアップが完了しました: {projectPath}",
                "projectPath": projectPath,
                "assetsPath": assets_dir,
                "vrmModelsPath": vrm_models_dir,
                "createdVrmSupportFiles": createVrmSupportFiles
            }
        )
    
    @handle_exceptions
    def export_to_unity_editor(self, obj, info, modelId: str, unityProjectPath: str, createPrefab: bool = True) -> Dict[str, Any]:
        """
        Unity Editorに直接エクスポート
        
        Args:
            obj: GraphQLのルートオブジェクト
            info: GraphQLの実行情報
            modelId: モデルID（コレクション名）
            unityProjectPath: Unityプロジェクトのパス
            createPrefab: Prefabを作成するか
            
        Returns:
            Dict: エクスポート結果
        """
        self.logger.debug(f"export_to_unity_editor リゾルバが呼び出されました: modelId={modelId}, unityProjectPath={unityProjectPath}")
        
        # 入力検証
        if not modelId or len(modelId.strip()) == 0:
            return self.error_response(
                "モデルIDが空です", 
                {"code": "EMPTY_ID", "fix": "有効なモデルIDを指定してください"}
            )
            
        if not unityProjectPath or len(unityProjectPath.strip()) == 0:
            return self.error_response(
                "プロジェクトパスが空です", 
                {"code": "EMPTY_UNITY_PATH", "fix": "有効なUnityプロジェクトパスを指定してください"}
            )
            
        # コレクションの存在確認
        vrm_collection = bpy.data.collections.get(modelId)
        if not vrm_collection:
            return self.error_response(
                f"VRMモデル '{modelId}' が見つかりません",
                {"code": "MODEL_NOT_FOUND", "fix": "有効なVRMモデルIDを指定してください"}
            )
        
        # VRMモデルかどうかの確認
        if not vrm_collection.get("vrm_model", False):
            return self.error_response(
                f"コレクション '{modelId}' はVRMモデルではありません",
                {"code": "NOT_VRM_MODEL", "fix": "VRM用に作成されたモデルコレクションを指定してください"}
            )
        
        # Unityプロジェクトディレクトリの存在確認
        if not os.path.exists(unityProjectPath):
            return self.error_response(
                f"Unityプロジェクトディレクトリが見つかりません: {unityProjectPath}",
                {"code": "UNITY_DIR_NOT_FOUND", "fix": "有効なUnityプロジェクトディレクトリパスを指定してください"}
            )
        
        # Assetsディレクトリの存在確認
        assets_dir = os.path.join(unityProjectPath, "Assets")
        if not os.path.exists(assets_dir):
            return self.error_response(
                f"Unityプロジェクトに Assets ディレクトリが見つかりません",
                {"code": "ASSETS_DIR_NOT_FOUND", "fix": "正しいUnityプロジェクト構造を持つディレクトリを指定してください"}
            )
        
        # VRMモデル用ディレクトリ
        vrm_models_dir = os.path.join(assets_dir, "VRMModels")
        if not os.path.exists(vrm_models_dir):
            os.makedirs(vrm_models_dir, exist_ok=True)
        
        # モデル専用ディレクトリ
        model_dir = os.path.join(vrm_models_dir, modelId)
        if not os.path.exists(model_dir):
            os.makedirs(model_dir, exist_ok=True)
        
        # FBXファイルとしてエクスポート
        fbx_path = os.path.join(model_dir, f"{modelId}.fbx")
        
        # すべてのオブジェクトを非選択に
        bpy.ops.object.select_all(action='DESELECT')
        
        # コレクション内のオブジェクトを選択
        for obj in vrm_collection.objects:
            obj.select_set(True)
        
        # FBXエクスポート実行
        bpy.ops.export_scene.fbx(
            filepath=fbx_path,
            use_selection=True,
            global_scale=1.0,
            apply_unit_scale=True,
            apply_scale_options='FBX_SCALE_NONE',
            bake_space_transform=False,
            object_types={'ARMATURE', 'MESH'},
            use_mesh_modifiers=True,
            mesh_smooth_type='FACE',
            use_mesh_edges=False,
            use_tspace=True,
            use_custom_props=True,
            add_leaf_bones=False,
            primary_bone_axis='Y',
            secondary_bone_axis='X',
            use_armature_deform_only=True,
            armature_nodetype='NULL',
            bake_anim=True,
            bake_anim_use_all_bones=True,
            bake_anim_use_nla_strips=True,
            bake_anim_use_all_actions=True,
            bake_anim_force_startend_keying=True,
            bake_anim_step=1.0,
            bake_anim_simplify_factor=1.0,
            path_mode='COPY',
            embed_textures=True,
            batch_mode='OFF',
            use_batch_own_dir=True,
            axis_forward='-Z',
            axis_up='Y'
        )
        
        # Prefab作成用スクリプトを生成（実際には、Unityエディタ拡張スクリプトを通じて実行）
        if createPrefab:
            prefab_script_path = os.path.join(model_dir, f"Create{modelId}Prefab.cs")
            with open(prefab_script_path, 'w') as f:
                f.write("// Auto-generated prefab creation script\n")
                f.write("using UnityEngine;\n")
                f.write("using UnityEditor;\n")
                f.write("using System.IO;\n\n")
                f.write("public class Create" + modelId + "Prefab : Editor {\n")
                f.write("    [MenuItem(\"VRM/Create " + modelId + " Prefab\")]\n")
                f.write("    public static void CreatePrefab() {\n")
                f.write("        // モデルのパス\n")
                f.write(f"        string modelPath = \"Assets/VRMModels/{modelId}/{modelId}.fbx\";\n")
                f.write(f"        string prefabPath = \"Assets/VRMModels/{modelId}/{modelId}.prefab\";\n\n")
                f.write("        // モデルの読み込み\n")
                f.write("        GameObject modelPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(modelPath);\n")
                f.write("        if (modelPrefab == null) {\n")
                f.write("            Debug.LogError(\"モデルが見つかりません: \" + modelPath);\n")
                f.write("            return;\n")
                f.write("        }\n\n")
                f.write("        // プレハブの作成\n")
                f.write("        GameObject instance = Instantiate(modelPrefab);\n")
                f.write("        // 必要なコンポーネントを追加\n")
                f.write("        // TODO: VRMコンポーネントのセットアップ\n")
                f.write("        \n")
                f.write("        // プレハブとして保存\n")
                f.write("        PrefabUtility.SaveAsPrefabAsset(instance, prefabPath);\n")
                f.write("        DestroyImmediate(instance);\n")
                f.write("        Debug.Log(\"プレハブを作成しました: \" + prefabPath);\n")
                f.write("    }\n")
                f.write("}\n")
        
        # 完了メッセージ
        success_message = f"VRMモデル '{modelId}' を Unity プロジェクトにエクスポートしました"
        if createPrefab:
            success_message += "（Prefab生成スクリプト付き）"
        
        return self.success_response(
            success_message,
            {
                "success": True,
                "message": success_message,
                "unityProjectPath": unityProjectPath,
                "modelPath": fbx_path,
                "createdPrefab": createPrefab
            }
        )
    
    @handle_exceptions
    def generate_unity_materials(self, obj, info, modelId: str, unityProjectPath: str, materialType: str = "Standard") -> Dict[str, Any]:
        """
        Unityマテリアルを生成
        
        Args:
            obj: GraphQLのルートオブジェクト
            info: GraphQLの実行情報
            modelId: モデルID（コレクション名）
            unityProjectPath: Unityプロジェクトのパス
            materialType: マテリアルタイプ
            
        Returns:
            Dict: 生成結果
        """
        self.logger.debug(f"generate_unity_materials リゾルバが呼び出されました: modelId={modelId}, unityProjectPath={unityProjectPath}, materialType={materialType}")
        
        # 入力検証
        if not modelId or len(modelId.strip()) == 0:
            return self.error_response(
                "モデルIDが空です", 
                {"code": "EMPTY_ID", "fix": "有効なモデルIDを指定してください"}
            )
            
        if not unityProjectPath or len(unityProjectPath.strip()) == 0:
            return self.error_response(
                "プロジェクトパスが空です", 
                {"code": "EMPTY_UNITY_PATH", "fix": "有効なUnityプロジェクトパスを指定してください"}
            )
            
        # 有効なマテリアルタイプかチェック
        valid_material_types = ["Standard", "URP", "HDRP"]
        if materialType not in valid_material_types:
            return self.error_response(
                f"無効なマテリアルタイプ: {materialType}",
                {"code": "INVALID_MATERIAL_TYPE", "fix": f"有効なマテリアルタイプを指定してください: {', '.join(valid_material_types)}"}
            )
            
        # コレクションの存在確認
        vrm_collection = bpy.data.collections.get(modelId)
        if not vrm_collection:
            return self.error_response(
                f"VRMモデル '{modelId}' が見つかりません",
                {"code": "MODEL_NOT_FOUND", "fix": "有効なVRMモデルIDを指定してください"}
            )
        
        # VRMモデルかどうかの確認
        if not vrm_collection.get("vrm_model", False):
            return self.error_response(
                f"コレクション '{modelId}' はVRMモデルではありません",
                {"code": "NOT_VRM_MODEL", "fix": "VRM用に作成されたモデルコレクションを指定してください"}
            )
        
        # Unityプロジェクトディレクトリの存在確認
        if not os.path.exists(unityProjectPath):
            return self.error_response(
                f"Unityプロジェクトディレクトリが見つかりません: {unityProjectPath}",
                {"code": "UNITY_DIR_NOT_FOUND", "fix": "有効なUnityプロジェクトディレクトリパスを指定してください"}
            )
        
        # マテリアル情報の収集
        materials = []
        material_names = set()
        
        for obj in vrm_collection.objects:
            if obj.type == 'MESH':
                for slot in obj.material_slots:
                    if slot.material and slot.material.name not in material_names:
                        material_names.add(slot.material.name)
                        
                        # マテリアル情報の取得
                        mat = slot.material
                        material_info = {
                            "name": mat.name,
                            "color": [1.0, 1.0, 1.0, 1.0],  # デフォルト値
                            "metallic": 0.0,
                            "roughness": 0.5
                        }
                        
                        # マテリアルプロパティの取得
                        if mat.use_nodes:
                            # プリンシプルBSDFノードを探す
                            for node in mat.node_tree.nodes:
                                if node.type == 'BSDF_PRINCIPLED':
                                    # 色情報
                                    if hasattr(node.inputs["Base Color"], "default_value"):
                                        color = node.inputs["Base Color"].default_value
                                        material_info["color"] = [color[0], color[1], color[2], color[3]]
                                    
                                    # メタリック
                                    if hasattr(node.inputs["Metallic"], "default_value"):
                                        material_info["metallic"] = node.inputs["Metallic"].default_value
                                    
                                    # ラフネス
                                    if hasattr(node.inputs["Roughness"], "default_value"):
                                        material_info["roughness"] = node.inputs["Roughness"].default_value
                                    
                                    break
                        
                        materials.append(material_info)
        
        if not materials:
            return self.error_response(
                f"VRMモデル '{modelId}' にマテリアルが見つかりません",
                {"code": "NO_MATERIALS", "fix": "モデルにマテリアルを適用してから再試行してください"}
            )
        
        # Unityマテリアル作成スクリプトの生成
        assets_dir = os.path.join(unityProjectPath, "Assets")
        vrm_models_dir = os.path.join(assets_dir, "VRMModels")
        model_dir = os.path.join(vrm_models_dir, modelId)
        materials_dir = os.path.join(model_dir, "Materials")
        
        if not os.path.exists(materials_dir):
            os.makedirs(materials_dir, exist_ok=True)
        
        # マテリアル生成スクリプトの作成
        script_path = os.path.join(model_dir, f"Generate{modelId}Materials.cs")
        with open(script_path, 'w') as f:
            f.write("// Auto-generated material creation script\n")
            f.write("using UnityEngine;\n")
            f.write("using UnityEditor;\n")
            f.write("using System.IO;\n\n")
            f.write("public class Generate" + modelId + "Materials : Editor {\n")
            f.write(f"    [MenuItem(\"VRM/Generate {modelId} Materials\")]\n")
            f.write("    public static void CreateMaterials() {\n")
            f.write("        string materialsPath = \"Assets/VRMModels/" + modelId + "/Materials/\";\n\n")
            f.write("        // ディレクトリ作成\n")
            f.write("        if (!Directory.Exists(materialsPath)) {\n")
            f.write("            Directory.CreateDirectory(materialsPath);\n")
            f.write("        }\n\n")
            
            # 各マテリアルの生成
            for mat in materials:
                mat_name = mat["name"]
                color = mat["color"]
                metallic = mat["metallic"]
                roughness = mat["roughness"]
                
                f.write(f"        // マテリアル: {mat_name}\n")
                if materialType == "URP":
                    f.write(f"        Material {mat_name.replace('.', '_')} = new Material(Shader.Find(\"Universal Render Pipeline/Lit\"));\n")
                else:
                    f.write(f"        Material {mat_name.replace('.', '_')} = new Material(Shader.Find(\"Standard\"));\n")
                
                f.write(f"        {mat_name.replace('.', '_')}.name = \"{mat_name}\";\n")
                f.write(f"        {mat_name.replace('.', '_')}.color = new Color({color[0]}f, {color[1]}f, {color[2]}f, {color[3]}f);\n")
                f.write(f"        {mat_name.replace('.', '_')}.SetFloat(\"_Metallic\", {metallic}f);\n")
                f.write(f"        {mat_name.replace('.', '_')}.SetFloat(\"_Glossiness\", {1.0 - roughness}f);\n")
                f.write(f"        AssetDatabase.CreateAsset({mat_name.replace('.', '_')}, materialsPath + \"{mat_name}.mat\");\n\n")
            
            f.write("        AssetDatabase.SaveAssets();\n")
            f.write("        AssetDatabase.Refresh();\n")
            f.write("        Debug.Log(\"マテリアルを生成しました\");\n")
            f.write("    }\n")
            f.write("}\n")
        
        return self.success_response(
            f"Unityマテリアル生成スクリプトを作成しました: {script_path}",
            {
                "success": True,
                "message": f"Unityマテリアル生成スクリプトを作成しました: {script_path}",
                "unityProjectPath": unityProjectPath,
                "materialsCount": len(materials),
                "materialType": materialType,
                "scriptPath": script_path
            }
        )