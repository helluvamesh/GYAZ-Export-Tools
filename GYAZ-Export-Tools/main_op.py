# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any laTter version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####


##########################################################################################################
##########################################################################################################

import bpy, os, bmesh
from mathutils import Vector, Matrix, Quaternion
from math import radians
from pathlib import Path
from bpy.props import EnumProperty
from .utils import report, popup, list_to_visual_list, make_active_only, sn, get_active_action, \
    is_str_blank, detect_mirrored_uvs, clear_transformation, clear_transformation_matrix, \
    gather_images_from_material, clear_blender_collection, set_active_action, POD, remove_dot_plus_three_numbers, \
    make_lod_object_name_pattern, get_name_and_lod_index, set_bone_parent, make_active, \
    bake_collision_object


prefs = bpy.context.preferences.addons[__package__].preferences

    
# main ops    
class Op_GYAZ_Export_Export (bpy.types.Operator):
       
    bl_idname = "object.gyaz_export_export"  
    bl_label = "GYAZ Export: Export"
    bl_description = "Export. STATIC MESHES: select one or multiple meshes, SKELETAL MESHES: select one armature, ANIMATIONS: select one armature, RIGID_ANIMATIONS: select one or multiple meshes"
    
    asset_type_override: EnumProperty (name='Asset Type', 
        items=(
            ('DO_NOT_OVERRIDE', 'DO NOT OVERRIDE', ""),
            ('STATIC_MESHES', 'STATIC MESHES', ""),
            ('RIGID_ANIMATIONS', 'RIGID ANIMATIONS', ""),
            ('SKELETAL_MESHES', 'SKELETAL MESHES', ""),
            ('ANIMATIONS', 'SKELETAL ANIMATIONS', "")
            ),
        default='DO_NOT_OVERRIDE', options={'SKIP_SAVE'})
    
    # operator function
    def execute (self, context):
        
        bpy.ops.object.mode_set (mode='OBJECT')
        
        scene = bpy.context.scene
        space = bpy.context.space_data
        scene_gyaz_export = scene.gyaz_export

        target_unreal = scene_gyaz_export.target_app == "UNREAL"
        target_unity = scene_gyaz_export.target_app == "UNITY"
        target_cm_scale_unit = target_unreal
        target_y_up_z_forward = target_unity
        
        scene_objects = scene.objects
        ori_ao = bpy.context.active_object
        ori_ao_ori_name = ori_ao.name
        
        asset_type = scene_gyaz_export.skeletal_asset_type if ori_ao.type == 'ARMATURE' else scene_gyaz_export.rigid_asset_type 

        mesh_children = [child for child in ori_ao.children if child.type == 'MESH' and child.gyaz_export.export]

        if asset_type == "ANIMATIONS":
            if scene_gyaz_export.skeletal_shapes:
                # don't export meshes with no shape keys
                for obj in mesh_children.copy():
                    if obj.data.shape_keys is None or len(obj.data.shape_keys.key_blocks) == 0:
                        mesh_children.remove(obj)
            else:
                # don't export meshes if shape key export is disabled
                mesh_children = []

        root_folder = scene_gyaz_export.export_folder

        if asset_type == 'STATIC_MESHES':
            pack_objects = scene_gyaz_export.static_mesh_pack_objects
            pack_name = scene_gyaz_export.static_mesh_pack_name
        elif asset_type == 'SKELETAL_MESHES' or asset_type == 'ANIMATIONS':
            pack_objects = scene_gyaz_export.skeletal_mesh_pack_objects
            pack_name = ori_ao_ori_name
        elif asset_type == 'RIGID_ANIMATIONS':
            pack_objects = scene_gyaz_export.rigid_anim_pack_objects
            pack_name = scene_gyaz_export.rigid_anim_pack_name
            
        if asset_type == 'STATIC_MESHES':
            export_vert_colors = scene_gyaz_export.static_mesh_vcolors
        elif asset_type == 'SKELETAL_MESHES':
            export_vert_colors = scene_gyaz_export.skeletal_mesh_vcolors
        elif asset_type == 'RIGID_ANIMATIONS':
            export_vert_colors = scene_gyaz_export.rigid_anim_vcolors
        else:
            export_vert_colors = False
            
        if asset_type == 'SKELETAL_MESHES' or asset_type == 'ANIMATIONS':
            export_shape_keys = scene_gyaz_export.skeletal_shapes
        elif asset_type == 'RIGID_ANIMATIONS':
            export_shape_keys = scene_gyaz_export.rigid_anim_shapes
        else:
            export_shape_keys = False
            
        action_export_mode = scene_gyaz_export.action_export_mode
        rigid_anim_cubes = scene_gyaz_export.rigid_anim_cubes and not pack_objects
        root_bone_name = scene_gyaz_export.root_bone_name

        ###############################################################
        # GATHER OBJECTS FROM COLLECTIONS
        ############################################################### 

        # gather all objects from active collection
        if asset_type == 'STATIC_MESHES' or asset_type == 'RIGID_ANIMATIONS':
            if asset_type == 'STATIC_MESHES':
                gather_from_collection = scene_gyaz_export.static_mesh_gather_from_collection
                gather_nested = scene_gyaz_export.static_mesh_gather_nested
            elif asset_type == 'RIGID_ANIMATIONS':
                gather_from_collection = scene_gyaz_export.rigid_anim_gather_from_collection
                gather_nested = scene_gyaz_export.rigid_anim_gather_nested            
            
            if not gather_from_collection:
                ori_sel_objs = [obj for obj in bpy.context.selected_objects if obj.gyaz_export.export]
            else:
                name = ori_ao.name
                collections = bpy.data.collections
                x = [col for col in collections if name in col.objects]
                if x:
                    active_collection = x[0]
                    if gather_nested:
                        ori_sel_objs = self.gather_objects_from_collection_recursive(active_collection)
                    else:
                        ori_sel_objs = self.gather_objects_from_collection(active_collection)
                else:
                    ori_sel_objs = [obj for obj in bpy.context.selected_objects if obj.gyaz_export.export]
        else:
            ori_sel_objs = [obj for obj in bpy.context.selected_objects if obj.gyaz_export.export]
                
        if asset_type == 'STATIC_MESHES' or asset_type == 'RIGID_ANIMATIONS':
            meshes_to_export = ori_sel_objs
        elif asset_type == 'SKELETAL_MESHES' or asset_type == 'ANIMATIONS':
            meshes_to_export = mesh_children        
        
        if self.asset_type_override != 'DO_NOT_OVERRIDE':
            asset_type = self.asset_type_override
                
        ###############################################################
        # GATHER LODs
        ############################################################### 
        
        asset_type_with_lod = False
        if target_unreal:
            # exporting skeletal mesh lods in the same file with lod0 results in 
            # lods being exported in the wrong order in Unreal 4 (lod0, lod3, lod2, lod1)
            # so skeletal mesh lods should be exported in separate files
            # and imported one by one
            asset_type_with_lod = asset_type == 'STATIC_MESHES'
        elif target_unity:
            asset_type_with_lod = True
        export_lods = asset_type_with_lod and scene_gyaz_export.export_lods

        lod_pattern = make_lod_object_name_pattern()

        # {obj_name_wo_lod: [(obj_ref, lod_idx)]}
        lod_level_map_with_name_key = {}

        # {obj: obj_name_wo_lod}
        obj_to_obj_name_wo_lod_map = {}

        for obj in scene.objects:
            info = get_name_and_lod_index(lod_pattern, obj.name)

            obj_name_wo_lod = ""
            lod_idx = 0

            if info is not None:
                obj_name_wo_lod = info[0]
                lod_idx = info[1]
            else:
                # not a lod obj
                obj_name_wo_lod = obj.name
                lod_idx = 0

            info_list = lod_level_map_with_name_key.get(obj_name_wo_lod)
            if info_list is None:
                info_list = []
                lod_level_map_with_name_key[obj_name_wo_lod] = info_list
            info_list.append((obj, lod_idx))

            obj_to_obj_name_wo_lod_map[obj] = obj_name_wo_lod

        # sort by lod_idx
        for lod_level_info in lod_level_map_with_name_key.values():
            lod_level_info.sort(key=lambda x: x[1])

        # {obj_ref: (lod_objs, obj_name_wo_lod)}
        lod_info = {}

        lod_set = set()

        for obj in meshes_to_export:
            obj_name_wo_lod = obj_to_obj_name_wo_lod_map[obj]
            lods = []
            for lod_level_info in lod_level_map_with_name_key[obj_name_wo_lod]:
                lod_obj = lod_level_info[0]
                lod_idx = lod_level_info[1]
                if obj is not lod_obj and lod_idx > 0:
                    lods.append(lod_obj)
                    lod_set.add(lod_obj)
            lod_info[obj] = (lods, obj_name_wo_lod)

        meshes_to_export += list(lod_set)
        
        ori_sel_objs = list(set(ori_sel_objs) - lod_set)
        mesh_children = list(set(mesh_children) - lod_set)
            
        ###############################################################
        # GATHER COLLISION & SOCKETS
        ############################################################### 

        export_collision = scene_gyaz_export.export_collision
        collision_info = {}
        collision_objs_ori = set ()
        
        if asset_type == 'STATIC_MESHES' and export_collision:
            prefixes = ['UBX', 'USP', 'UCP', 'UCX']
            for obj in meshes_to_export:                     
                name = obj.name
                obj_cols = set ()
                for prefix in prefixes:
                    col = scene_objects.get (prefix+'_'+name)
                    if col is not None:
                        obj_cols.add ((col, prefix+'_'+name+'_00'))
                        collision_objs_ori.add (scene_objects.get (col.name))
                    for n in range (1, 100):
                        suffix = '.00'+str(n) if n < 10 else '.0'+str(n)
                        col = scene_objects.get (prefix+'_'+name+suffix)
                        collision_objs_ori.add (col)
                        if col is not None:
                            suffix = '_0'+str(n) if n < 10 else '_'+str(n)
                            obj_cols.add ((col, prefix+'_'+name+suffix))
                            collision_objs_ori.add (scene_objects.get (col.name))
                if len (obj_cols) > 0:
                    collision_info[name] = obj_cols
                         
            ori_sel_objs = list ( set (ori_sel_objs) - collision_objs_ori )
            meshes_to_export = list ( set (meshes_to_export) - collision_objs_ori )

        export_sockets = scene_gyaz_export.export_sockets
        socket_info = {}

        if target_unreal:
            for obj in ori_sel_objs:
                name = obj.name
                for child in obj.children:
                    if child.type == 'EMPTY' and child.name.startswith ('SOCKET_'):
                        socket_objs = socket_info.get(name)
                        if socket_objs is None:
                            socket_objs = []
                            socket_info[name] = socket_objs
                        socket_objs.append(child)

        elif target_unity:
            if asset_type == 'STATIC_MESHES':
                for obj in ori_sel_objs:
                    name = obj.name
                    for child in obj.children:
                        if child.type == 'EMPTY' and child.name.startswith ('SOCKET_'):
                            socket_objs = socket_info.get(name)
                            if socket_objs is None:
                                socket_objs = []
                                socket_info[name] = socket_objs
                            socket_objs.append(child)

        ###############################################################
        # HIGH-LEVEL CHECKS
        ###############################################################
        
        if not bpy.context.blend_data.is_saved:
            report (self, 'Blend file has never been saved.', 'WARNING')
            return {"CANCELLED"}
            
        space = None
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                space = area.spaces[0]
                break
        if space is not None:
            if space.local_view is not None:
                report (self, "Leave local view.", "WARNING")
                return {"CANCELLED"}

        if asset_type == 'STATIC_MESHES' and pack_objects:
            if is_str_blank(pack_name):
                report (self, "Pack name is invalid.", "WARNING")
                return {"CANCELLED"}
            
        elif asset_type == 'RIGID_ANIMATIONS' and pack_objects:
            if is_str_blank(pack_name):
                report (self, "Pack name is invalid.", "WARNING")
                return {"CANCELLED"}

        if root_folder.startswith ('//'):
            root_folder = os.path.abspath ( bpy.path.abspath (root_folder) )
        if not os.path.isdir(root_folder):
            report (self, "Export folder (Destination) doesn't exist.", "WARNING")
            return {"CANCELLED"} 


        if asset_type == 'ANIMATIONS':
            actions_set_for_export = scene_gyaz_export.actions
            if ori_ao.type == 'ARMATURE':   
                if scene_gyaz_export.use_anim_object_name_override and is_str_blank(scene_gyaz_export.anim_object_name_override):
                    report (self, 'Object name override is invalid.', 'WARNING')
                    return {"CANCELLED"}
                else:
                    if action_export_mode == 'ACTIVE': 
                        if getattr (ori_ao, "animation_data") is not None:
                            if ori_ao.animation_data.action is not None:
                                if scene_gyaz_export.pack_actions and is_str_blank(scene_gyaz_export.global_anim_name):
                                    report (self, 'Action pack name is invalid.', 'WARNING')
                                    return {"CANCELLED"}
                            else:
                                report (self, 'Active object has no action assigned to it.', 'WARNING')
                                return {"CANCELLED"}
                        else:
                            report (self, 'Active object has no animation data.', 'WARNING')
                            return {"CANCELLED"}
                            
                            
                    elif action_export_mode == 'ALL':
                        if len (bpy.data.actions) > 0:
                            if scene_gyaz_export.pack_actions and is_str_blank(scene_gyaz_export.global_anim_name):
                                report (self, 'Action pack name is invalid.', 'WARNING')
                                return {"CANCELLED"}
                        else:
                            report (self, 'No actions found in this .blend file.', 'WARNING')
                            return {"CANCELLED"}

                            
                    elif action_export_mode == 'BY_NAME':
                        items_ok = []
                        for item in actions_set_for_export:
                            if item.name != '':
                                items_ok.append (True)
                                
                        if len (actions_set_for_export) > 0:
                            if len (actions_set_for_export) == len (items_ok):
                                if scene_gyaz_export.pack_actions and is_str_blank(scene_gyaz_export.global_anim_name):
                                    report (self, 'Action pack name is invalid.', 'WARNING')
                                    return {"CANCELLED"}
                            else:
                                report (self, 'One or more actions set to be exported are not found', 'WARNING') 
                                return {"CANCELLED"}
                        else:
                            report (self, 'No actions are set to be exported.', 'WARNING')
                            return {"CANCELLED"}

                    elif action_export_mode == "SCENE":
                        if getattr (ori_ao, "animation_data") is not None:
                            if is_str_blank(scene_gyaz_export.global_anim_name):
                                report (self, 'Animation name is invalid.', 'WARNING')
                                return {"CANCELLED"}
                        else:
                            report (self, 'Active object has no animation data.', 'WARNING')
                            return {"CANCELLED"}
                        
            else:
                report (self, 'Active object is not an armature.', 'WARNING')
                return {"CANCELLED"}

                    
        elif asset_type == 'SKELETAL_MESHES':
            if ori_ao.type == 'ARMATURE':
                if len (mesh_children) > 0:
                    if scene_gyaz_export.root_mode == 'BONE':    
                        if ori_ao.data.bones.get (root_bone_name) is None:
                            report (self, 'Root bone, called "' + root_bone_name + '", not found. Set object as root.', 'WARNING')
                            return {"CANCELLED"}
                else:
                    report (self, "Armature has no mesh children.", 'WARNING')
                    return {"CANCELLED"}
            else:
                report (self, "Active object is not an armature.", 'WARNING')
                return {"CANCELLED"}
                
                
        elif asset_type == 'STATIC_MESHES':      
            if len (ori_sel_objs) <= 0:
                report (self, 'No objects set for export.', 'WARNING')
                return {"CANCELLED"}
        
        elif asset_type == 'RIGID_ANIMATIONS':
            if len (ori_sel_objs) > 0:
                if is_str_blank(scene_gyaz_export.rigid_anim_name):
                    report (self, 'Animation name is invalid.', 'WARNING')
                    return {"CANCELLED"}
                else:
                    for obj in ori_sel_objs:
                        if getattr (obj, "animation_data") is not None:
                            if obj.animation_data.action is None:
                                report (self, 'Object "' + obj.name + '" has no action assigned to it.', 'WARNING')
                                return {"CANCELLED"}
                        else:
                            report (self, 'Object "' + obj.name + '" has no animation data.', 'WARNING')
                            return {"CANCELLED"}
            else:
                report (self, 'No objects set for export.', 'WARNING')
                return {"CANCELLED"}

        ###############################################################            
        # CONTENT CHECKS
        ###############################################################
        
        no_material_objects = []  
        no_uv_map_objects = []
        no_second_uv_map_objects = []
        bad_poly_objects = []
        ungrouped_vert_objects = []
        mirrored_uv_objects = []
        missing_textures = []
        missing_bones = []
        cant_create_extra_bones = []
        multiple_or_no_armature_mods = []
        shapes_and_mods = []
        
        image_info = {}
        image_nodes = set()

        max_face_vert_count = 0
        poly_warning = ""
        if scene_gyaz_export.allow_quads:
            max_face_vert_count = 4 
            poly_warning = 'Ngons found: '
        else:
            max_face_vert_count = 3
            poly_warning = 'Quads/ngons found: '
        
        def is_everything_fine():
            return len(no_material_objects)==0 and len(no_uv_map_objects)==0 and len(no_second_uv_map_objects)==0 and \
                len(bad_poly_objects)==0 and len(ungrouped_vert_objects)==0 and len(mirrored_uv_objects)==0 and \
                len(missing_textures)==0 and len(missing_bones)==0 and len(cant_create_extra_bones)==0 and \
                len(multiple_or_no_armature_mods)==0 and len(shapes_and_mods)==0

        # mesh checks
        for obj in meshes_to_export:
            
            if obj.type == 'MESH':
            
                # materials
                materials = []
                
                for slot in obj.material_slots:
                    if slot.material is not None:
                        materials.append (slot.material)
                        
                if len (materials) == 0:
                    no_material_objects.append (obj.name)
                        
                
                # uv maps
                uv_maps = []
                
                for index, uv_map in enumerate (obj.data.uv_layers):
                    if obj.data.gyaz_export.uv_export[index]:
                        uv_maps.append (uv_map)
                    
                if len (uv_maps) == 0:
                    no_uv_map_objects.append (obj.name)
                    
                if asset_type == 'STATIC_MESHES' and scene_gyaz_export.check_for_second_uv_map and not scene_gyaz_export.ignore_missing_second_uv_map:
                    if len (uv_maps) < 2:
                        no_second_uv_map_objects.append (obj.name)
                    
                # ngons and quads
                bm = bmesh.new ()
                bm.from_object (obj, bpy.context.evaluated_depsgraph_get(), cage=False, face_normals=False, vertex_normals=False)
                faces = bm.faces
                ngon_count = len ( [face for face in faces if len(face.verts)>max_face_vert_count] )
                bm.free ()

                if asset_type != 'ANIMATIONS':
                    if ngon_count > 0:
                        bad_poly_objects.append (obj.name)
                    
                # ungrouped verts
                if asset_type == 'SKELETAL_MESHES':
                    verts = obj.data.vertices
                    verts_wo_group = [vert.index for vert in verts if len (vert.groups) == 0]
                    if len (verts_wo_group) > 0:
                        ungrouped_vert_objects.append (obj.name)
                
        
                # mirrored uvs
                if scene_gyaz_export.detect_mirrored_uvs:
                    if asset_type != 'ANIMATIONS':
                        
                        mesh = obj.data
                        
                        bm = bmesh.new ()
                        bm.from_mesh (mesh)
                        
                        mirrored_uvs_found = False
                        mirrored_indices = []
                        for n in range (len(mesh.uv_layers)):
                            mirrored_uvs_found = detect_mirrored_uvs (bm, uv_index=n)
                            if mirrored_uvs_found:
                                mirrored_indices.append (str(n))
                            
                        if mirrored_uvs_found:
                            mirrored_uv_objects.append (obj.name + ' (' + list_to_visual_list(mirrored_indices) + ')')
                                
                        bm.free ()
                        
                if asset_type == "SKELETAL_MESHES" or asset_type == "ANIMATIONS":
                    count = 0
                    for m in obj.modifiers:
                        if m.type == "ARMATURE":
                            count += 1
                    if count != 1:
                        multiple_or_no_armature_mods.append(obj.name)
                        
                if export_shape_keys:
                    if obj.data.shape_keys is not None:
                        if len(obj.data.shape_keys.key_blocks) > 0:
                            count = 0
                            for m in obj.modifiers:
                                if m.type != "ARMATURE":
                                    count += 1
                            if count > 0:
                                shapes_and_mods.append(obj.name)
                    
                # textures
                # get list of texture images
                images = set()
                image_nodes = set()
                for material in materials:
                    if material is not None:
                        gather_images_from_material(material, images, image_nodes)

                if scene_gyaz_export.export_textures:
                    image_info[obj] = images
        
        image_set = set()
        for obj in image_info:
            for image in image_info[obj]:
                image_set.add(image)
        
        if asset_type != 'ANIMATIONS':
            if scene_gyaz_export.export_textures:           
                
                for image in image_set:
                    my_path = Path(os.path.abspath ( bpy.path.abspath (image.filepath_raw) ))
                    if not my_path.is_file() or image.source != 'FILE':
                        missing_textures.append (image.name)
                    
        if asset_type == 'SKELETAL_MESHES' or asset_type == 'ANIMATIONS':
            
            # delete empty items of export bones
            indices_to_remove = []
            for index, item in enumerate (scene_gyaz_export.export_bones):
                if item.name == '':
                    indices_to_remove.append (index)
            for item in reversed (indices_to_remove):
                scene_gyaz_export.export_bones.remove(item)
            
            # missing_bones
            rig_bone_names = [x.name for x in ori_ao.data.bones]
            export_bone_names = [x.name for x in scene_gyaz_export.export_bones]
            if not scene_gyaz_export.export_all_bones:
                missing_bones = [item.name for item in scene_gyaz_export.export_bones if item.name not in rig_bone_names and item.name != '']
            if len (scene_gyaz_export.extra_bones) > 0:
                for index, item in enumerate(scene_gyaz_export.extra_bones):
                    if is_str_blank(item.name):
                        cant_create_extra_bones.append (index)
                    if item.source not in rig_bone_names:
                        cant_create_extra_bones.append (index)
                    if item.name in export_bone_names:
                        cant_create_extra_bones.append (index)

        if not is_everything_fine():
            
            # popup with warnings
            
            vl1 = list_to_visual_list (no_material_objects)
            vl2 = list_to_visual_list (no_uv_map_objects)
            vl3 = list_to_visual_list (no_second_uv_map_objects)
            vl4 = list_to_visual_list (bad_poly_objects)
            vl5 = list_to_visual_list (ungrouped_vert_objects)
            vl6 = list_to_visual_list (mirrored_uv_objects)
            vl7 = list_to_visual_list (missing_textures)
            vl8 = list_to_visual_list (missing_bones)
            vl9 = list_to_visual_list (cant_create_extra_bones)
            vl10 = list_to_visual_list (multiple_or_no_armature_mods)
            vl11 = list_to_visual_list (shapes_and_mods)
            
            l1 = 'No materials: ' + vl1
            l2 = 'No uv maps: ' + vl2
            l3 = 'No 2nd uv map: ' + vl3
            l4 = poly_warning + vl4
            l5 = 'Ungrouped verts: ' + vl5
            l6 = 'Mirrored UVs: ' + vl6
            l7 = 'Missing/unsaved textures: ' + vl7
            l8 = 'Missing bones: ' + vl8
            l9 = "Can't create extra bones: " + vl9
            l10 = "Multiple or no armature modifiers: " + vl10
            l11 = "Shape keys with modifers: " + vl11
            
            lines = []
            if len (no_material_objects) > 0:
                lines.append (l1)
            if len (no_uv_map_objects) > 0:
                lines.append (l2)
            
            if len (no_second_uv_map_objects) > 0:
                lines.append (l3)
            
            if len (bad_poly_objects) > 0:
                lines.append (l4)
                            
            if len (ungrouped_vert_objects) > 0:
                lines.append (l5)
                    
            if len (mirrored_uv_objects) > 0:
                lines.append (l6)
                
            if len (missing_textures) > 0:
                lines.append (l7)
                
            if len (missing_bones) > 0:
                lines.append (l8)
                
            if len (cant_create_extra_bones) > 0:
                lines.append (l9)

            if len (multiple_or_no_armature_mods) > 0:
                lines.append (l10)
            
            if len (shapes_and_mods) > 0:
                lines.append (l11)   
            
            # popup
            if not len (lines) == 0:
                popup (lines=lines, icon='INFO', title='Checks')
            
                # console
                print ('')
                print ('________________________________________________')
                print ('')
                for line in lines:
                    print ('')
                    print (line)
                print ('')
                print ('________________________________________________')
                print ('')

            else:
                err = "Error when doing content checks"
                popup ([err], icon='INFO', title='Checks')
                print (err)

            return {"CANCELLED"}

        #######################################################
        # EXPORT OPERATOR PROPS
        #######################################################
        
        static_meshes_for_unity = target_unreal and (asset_type == "STATIC_MESHES" or asset_type == "RIGID_ANIMATIONS")

        fbx_settings = POD()
        # MAIN
        fbx_settings.use_selection = True
        fbx_settings.use_active_collection = False
        fbx_settings.global_scale = 1
        fbx_settings.apply_unit_scale = False
        fbx_settings.apply_scale_options = 'FBX_SCALE_NONE' if target_cm_scale_unit else 'FBX_SCALE_ALL'
        fbx_settings.axis_forward = "-X" if target_unreal else "-Z"
        fbx_settings.axis_up = "Z" if target_unreal else 'Y'
        fbx_settings.object_types = {'EMPTY', 'CAMERA', 'LIGHT', 'ARMATURE', 'MESH', 'OTHER'}
        fbx_settings.use_space_transform = target_unreal or static_meshes_for_unity
        fbx_settings.bake_space_transform = static_meshes_for_unity
        fbx_settings.use_custom_props = False
        
        # 'STRIP' is the only mode textures are not referenced in the fbx file (only referenced not copied - this is undesirable behavior)
        fbx_settings.path_mode = 'STRIP'
        
        fbx_settings.batch_mode = 'OFF'
        fbx_settings.embed_textures = False
        # GEOMETRIES
        fbx_settings.use_mesh_modifiers = True
        fbx_settings.use_mesh_modifiers_render = True
        fbx_settings.mesh_smooth_type = scene_gyaz_export.mesh_smoothing
        fbx_settings.use_mesh_edges = False
        fbx_settings.use_tspace = True
        # ARMATURES
        fbx_settings.use_armature_deform_only = False
        fbx_settings.add_leaf_bones = scene_gyaz_export.add_end_bones
        fbx_settings.primary_bone_axis = scene_gyaz_export.primary_bone_axis
        fbx_settings.secondary_bone_axis = scene_gyaz_export.secondary_bone_axis
        fbx_settings.armature_nodetype = 'NULL'
        # ANIMATION
        fbx_settings.bake_anim = False
        fbx_settings.bake_anim_use_all_bones = False
        fbx_settings.bake_anim_use_nla_strips = False
        fbx_settings.bake_anim_use_all_actions = False
        fbx_settings.bake_anim_force_startend_keying = False
        fbx_settings.bake_anim_step = 1
        fbx_settings.bake_anim_simplify_factor = 0
        
        # asset prefixes
        if scene_gyaz_export.use_prefixes:
            static_mesh_prefix = sn(prefs.static_mesh_prefix)
            skeletal_mesh_prefix = sn(prefs.skeletal_mesh_prefix)
            material_prefix = sn(prefs.material_prefix)
            texture_prefix = sn(prefs.texture_prefix)
            animation_prefix = sn(prefs.animation_prefix)
            
            # if prefix starts with an underscore, use a suffix instead
            if static_mesh_prefix.startswith('_'):
                static_mesh_suffix = static_mesh_prefix
                static_mesh_prefix = ''
            else:
                static_mesh_suffix = ''
                
            if skeletal_mesh_prefix.startswith('_'):
                skeletal_mesh_suffix = skeletal_mesh_prefix
                skeletal_mesh_prefix = ''
            else:
                skeletal_mesh_suffix = ''
                
            if material_prefix.startswith('_'):
                material_suffix = material_prefix
                material_prefix = ''
            else:
                material_suffix = ''
                
            if texture_prefix.startswith('_'):
                texture_suffix = texture_prefix
                texture_prefix = ''
            else:
                texture_suffix = ''
                
            if animation_prefix.startswith('_'):
                animation_suffix = animation_prefix
                animation_prefix = ''
            else:
                animation_suffix = ''           
            
        else:
            static_mesh_prefix = ''
            skeletal_mesh_prefix = ''
            material_prefix = ''
            texture_prefix = ''
            animation_prefix = ''
            
            static_mesh_suffix = ''
            skeletal_mesh_suffix = ''
            material_suffix = ''
            texture_suffix= ''
            animation_suffix = ''
  
        #######################################################
        # EXPORT DIR
        #######################################################
        
        anims_folder = sn(prefs.anim_folder_name)
        meshes_folder = sn(prefs.mesh_folder_name)

        if asset_type == "STATIC_MESHES" or asset_type == "SKELETAL_MESHES":
            dir = root_folder
        elif asset_type == "ANIMATIONS" or asset_type == "RIGID_ANIMATIONS":
            dir = os.path.join(root_folder, anims_folder)

        scene_gyaz_export.path_to_last_export = dir

        ###############################################################
        # SAVE .BLEND FILE BEFORE CHANGING ANYTHING
        ###############################################################        
        
        blend_data = bpy.context.blend_data
        blend_path = blend_data.filepath

        # make sure no images get deleted
        for image in bpy.data.images:
            if image.users == 0:
                image.use_fake_user = True

        bpy.ops.wm.save_as_mainfile (filepath=blend_path)
            
        ###############################################################

        self.make_every_collection_and_object_visible_in_scene(scene)
        
        # make list of bones to keep    
        if asset_type == 'SKELETAL_MESHES' or asset_type == 'ANIMATIONS':
            
            if not scene_gyaz_export.export_all_bones:
                export_bones = scene_gyaz_export.export_bones
            else:
                export_bones = ori_ao.data.bones
            export_bone_list = [item.name for item in export_bones]
            extra_bones = scene_gyaz_export.extra_bones
            extra_bone_list = [item.name for item in extra_bones]
            bone_list = export_bone_list + extra_bone_list
            if root_bone_name in bone_list:
                bone_list.remove (root_bone_name)
            if root_bone_name in export_bone_list:
                export_bone_list.remove (root_bone_name)
            if root_bone_name in extra_bone_list:
                extra_bone_list.remove (root_bone_name)
        
        
        # define clear transforms
        if asset_type == 'STATIC_MESHES':
            clear_transforms = scene_gyaz_export.static_mesh_clear_transforms
        elif asset_type == 'SKELETAL_MESHES' or asset_type == 'ANIMATIONS':
            clear_transforms = scene_gyaz_export.skeletal_clear_transforms
        
        
        # get root mode    
        if asset_type == 'SKELETAL_MESHES' or asset_type == 'ANIMATIONS':
            root_mode = scene_gyaz_export.root_mode

        
        length = len (scene_gyaz_export.extra_bones)    
        constraint_extra_bones = scene_gyaz_export.constraint_extra_bones if length > 0 else False
        rename_vert_groups_to_extra_bones = scene_gyaz_export.rename_vert_groups_to_extra_bones if length > 0 else False
        
        # file format
        exporter = scene_gyaz_export.exporter
        if exporter == 'FBX':
            format = '.fbx'
        
        ############################################################
        # GATHER COLLISION & SOCKETS
        ############################################################
        
        collision_objects = []
        sockets = []
        
        if asset_type == 'STATIC_MESHES':
            
            if export_collision:   
                
                # geather collision (mesh objects)
                collision_info_keys = collision_info.keys ()
                for obj in ori_sel_objs:
                    obj_name = obj.name

                    if obj_name in collision_info_keys:
                        cols = collision_info [obj_name]
                        for col, new_name in cols:
                            # rename collision object
                            col.name = new_name
                            col.name = new_name
                            collision_objects.append (col)
                            # remove uv maps from collision object
                            uv_maps = col.data.uv_layers
                            for i in range(len(uv_maps) - 1, -1, -1):
                                uv_maps.remove(uv_maps[i])
                                
            
                # parent collision to obj
                collision_info_keys = collision_info.keys ()
                for obj in ori_sel_objs:
                    obj_name = obj.name
                    if obj_name in collision_info_keys:
                        cols = collision_info [obj_name]
                        for col, new_name in cols:
                            collision = scene.objects.get (new_name)
                            if collision is not None:
                                collision.parent = obj
                                collision.matrix_parent_inverse = obj.matrix_world.inverted ()
            
            if export_sockets:
                
                for socket_objs in socket_info.values():
                    for socket_obj in socket_objs:
                        sockets.append(socket_obj)
            
            # clear lod transform
            if export_lods:
                    
                for obj in ori_sel_objs:
                    lod_info_tuple = lod_info.get(obj)
                    if lod_info_tuple is not None:
                        lods = lod_info_tuple[0]
                        for lod in lods:
                            if clear_transforms:
                                clear_transformation(lod)             

        #######################################################
        # REPLACE SKELETAL MESHES WITH CUBES
        # don't want to have high poly meshes in every animation file
        #######################################################
        
        if (asset_type == 'ANIMATIONS' and scene_gyaz_export.skeletal_shapes) or (asset_type == 'RIGID_ANIMATIONS' and rigid_anim_cubes):
            
            bpy.ops.object.mode_set (mode='OBJECT')                
            
            for obj in meshes_to_export:
                if obj.type == 'MESH':
                
                    # replace all mesh data with a cube (keeping the original mesh object)
                    mesh = obj.data
                    bm = bmesh.new ()
                    bm.from_mesh (mesh)
                    
                    bm.clear ()
                    bmesh.ops.create_cube(bm, size=0.1, calc_uvs=True)

                    bm.to_mesh (mesh)
                    bm.free ()
                    
                    up_vec = Vector ((0, 0, 1))
                    # you have to make the shapekeys modify the mesh otherwise the fbx exporter won't export it 
                    if obj.data.shape_keys is not None:
                        for key_index, key_block in enumerate(obj.data.shape_keys.key_blocks):
                            if key_index != 0:
                                for i in range (0, 8):
                                    key_block.data[i].co += up_vec
                                    
                    # remove materials
                    slots = obj.material_slots
                    for slot in slots:
                        slot.material = None  

        #######################################################
        # REMOVE ANIMATION AND CENTER OBJECTS
        #######################################################
        
        # remove actions from all objects that need to be exported
        bpy.ops.object.mode_set (mode='OBJECT')
        
            
        if asset_type == 'STATIC_MESHES':
            
            if clear_transforms:
                for obj in ori_sel_objs:
                    obj.animation_data_clear ()
                    clear_transformation (obj)
                    
        if asset_type == 'SKELETAL_MESHES':
            
            # remove action
            if hasattr (ori_ao, "animation_data"):
                if ori_ao.get ("animation_data") == True:
                    ori_ao.animation_data.action = None
            
            for obj in ori_sel_objs:
                obj.animation_data_clear ()
                
            clear_transformation_matrix (ori_ao)
            
            if clear_transforms:
                for obj in ori_ao.children:
                    clear_transformation_matrix (obj)
                    
            # remove bone constarints
            make_active_only (ori_ao)
            bpy.ops.object.mode_set (mode='POSE')
            for pbone in ori_ao.pose.bones:
                cs = pbone.constraints
                for c in cs:
                    cs.remove (c)
                    
            # reset bone transforms
            for pbone in ori_ao.pose.bones:
                pbone.location = [0, 0, 0]
                pbone.scale = [1, 1, 1]
                pbone.rotation_quaternion = [1, 0, 0, 0]
                pbone.rotation_euler = [0, 0, 0]
                pbone.rotation_axis_angle = [0, 0, 1, 0]
                                    
            
        elif asset_type == 'ANIMATIONS':
            
            if root_mode == 'BONE':
                
                clear_transformation_matrix (ori_ao)
                
            for obj in mesh_children:
                if clear_transforms:
                    clear_transformation_matrix (obj)
            
                if action_export_mode != 'ACTIVE':                    
                    obj.animation_data_clear ()

        #######################################################
        # BUILD FINAL RIG
        #######################################################
        
        final_rig = None

        if asset_type == 'SKELETAL_MESHES' or asset_type == 'ANIMATIONS':
            
            make_active_only (ori_ao)
            bpy.ops.object.mode_set (mode='EDIT')
            ebones = ori_ao.data.edit_bones
            
            # extra bone info
            extra_bone_info = []
            extra_bones = scene_gyaz_export.extra_bones
            for item in extra_bones:
                ebone = ebones.get (item.source)
                if ebone is not None:
                    info = {'name': item.name, 'head': ebone.head[:], 'tail': ebone.tail[:], 'roll': ebone.roll, 'parent': item.parent}
                    extra_bone_info.append (info)
            
            bpy.ops.object.mode_set (mode='OBJECT')
            
            # duplicate armature
            final_rig_data = ori_ao.data.copy ()
            
            # create new armature object
            final_rig = bpy.data.objects.new (name="root", object_data=final_rig_data)
            scene.collection.objects.link (final_rig)
            make_active_only (final_rig)

            final_rig.name = "root"
            final_rig.name = "root"
            final_rig.rotation_mode = "QUATERNION"
            
            # remove drivers
            if hasattr (final_rig_data, "animation_data") == True:
                if final_rig_data.animation_data is not None:
                    for driver in final_rig_data.animation_data.drivers:
                        final_rig_data.driver_remove (driver.data_path)
            
            # delete bones
            bpy.ops.object.mode_set (mode='EDIT')
            ebones = final_rig_data.edit_bones
            all_bones = set (bone.name for bone in final_rig_data.bones)
            bones_to_remove = all_bones - set (export_bone_list)
            bones_to_remove.add (root_bone_name)
            for name in bones_to_remove:
                ebone = ebones.get (name)
                if ebone is not None:
                    ebones.remove (ebone)
                
            # create extra bones
            for item in extra_bone_info:
                ebone = final_rig.data.edit_bones.new (name=item['name'])
                ebone.head = item['head']
                ebone.tail = item['tail']
                ebone.roll = item['roll']
                    
            for item in extra_bone_info:    
                set_bone_parent(ebones, name=item['name'], parent_name=item['parent'])  

            if asset_type == "ANIMATIONS":
                # create root bone
                root_ebone = final_rig.data.edit_bones.new (name=root_bone_name)
                root_ebone.tail = (0, .1, 0)
                root_ebone.roll = 0
                for ebone in final_rig.data.edit_bones:
                    if ebone.parent is None:
                        ebone.parent = root_ebone
                
            # delete constraints
            bpy.ops.object.mode_set (mode='POSE')
            for pbone in final_rig.pose.bones:
                for c in pbone.constraints:
                    pbone.constraints.remove (c)

            # make all bones visible
            for bone_collection in final_rig_data.collections:
                bone_collection.is_visible = True
            for bone in final_rig_data.bones:
                bone.hide = False
                    
            # make sure bones export with correct scale
            if target_cm_scale_unit:
                bpy.ops.object.mode_set (mode='OBJECT')
                final_rig.scale = (100, 100, 100)
                bpy.ops.object.transform_apply (location=False, rotation=False, scale=True, properties=False)
                final_rig.delta_scale = (0.01, 0.01, 0.01)
            
                for child in mesh_children:
                    child.delta_scale[0] *= 100
                    child.delta_scale[1] *= 100
                    child.delta_scale[2] *= 100

            # bind meshes to the final rig
            for child in mesh_children:
                child.parent = final_rig
                child.matrix_parent_inverse = final_rig.matrix_world.inverted ()
                child.parent_type = 'ARMATURE'
            
            # constraint final rig to the original armature    
            if asset_type == "ANIMATIONS":

                make_active_only (final_rig)
                bpy.ops.object.mode_set (mode='POSE')
            
                # constraint 'export bones'        
                for name in export_bone_list:
                    self.constraint_bone(final_rig, name, ori_ao, name, target_cm_scale_unit)
                
                # constraint 'extra bones'
                if constraint_extra_bones:                                                                                     
                    for item in scene_gyaz_export.extra_bones:
                        new_name = item.name
                        source_name = item.source    
                        self.constraint_bone(final_rig, new_name, ori_ao, source_name, target_cm_scale_unit)            
                
                # constraint root
                if root_mode == 'BONE':
                    if ori_ao.data.bones.get (root_bone_name) is not None:
                        subtarget = root_bone_name 
                else:
                    subtarget = ''

                root_pbone = final_rig.pose.bones[root_bone_name]
                c = root_pbone.constraints.new (type='COPY_LOCATION')
                c.target = ori_ao
                c.subtarget = subtarget
                
                c = root_pbone.constraints.new (type='COPY_ROTATION')
                c.target = ori_ao
                c.subtarget = subtarget
                c.owner_space = "LOCAL"
                c.target_space = "LOCAL_OWNER_ORIENT"
                
                if target_cm_scale_unit:
                    c = root_pbone.constraints.new (type='TRANSFORM')
                    c.target = ori_ao
                    c.subtarget = subtarget
                    c.use_motion_extrapolate = True
                    c.map_from = 'SCALE'
                    c.map_to = 'SCALE'
                    c.map_to_x_from = 'X'
                    c.map_to_y_from = 'Y'
                    c.map_to_z_from = 'Z'
                    c.from_min_x_scale = -1
                    c.from_max_x_scale = 1
                    c.from_min_y_scale = -1
                    c.from_max_y_scale = 1
                    c.from_min_z_scale = -1
                    c.from_max_z_scale = 1
                    c.to_min_x_scale = -0.01
                    c.to_max_x_scale = 0.01
                    c.to_min_y_scale = -0.01
                    c.to_max_y_scale = 0.01
                    c.to_min_z_scale = -0.01
                    c.to_max_z_scale = 0.01
                else:
                    c = final_rig.constraints.new (type='COPY_SCALE')
                    c.target = ori_ao
                    c.subtarget = subtarget
            
            # rename vert groups to match extra bone names
            if rename_vert_groups_to_extra_bones:   
                for mesh in mesh_children:
                    vgroups = mesh.vertex_groups
                    for item in scene_gyaz_export.extra_bones:
                        vgroup = vgroups.get (item.source)
                        if vgroup is not None:
                            vgroup.name = item.name
                            
            # make sure armature modifier points to the final rig
            for ob in mesh_children:
                for m in ob.modifiers:
                    if m.type == 'ARMATURE':
                        m.object = final_rig
        
        bpy.ops.object.mode_set (mode='OBJECT')
                                
        #######################################################
        # LIMIT BONE INFLUENCES BY VERTEX
        #######################################################  
        
        if asset_type == 'SKELETAL_MESHES':
            
            bpy.ops.object.mode_set (mode='OBJECT')
            
            limit_prop = scene_gyaz_export.skeletal_mesh_limit_bone_influences
            
            for child in mesh_children:
                if len (child.vertex_groups) > 0:
                    make_active_only (child)

                    bpy.ops.object.mode_set (mode='WEIGHT_PAINT')
                    child.data.use_paint_mask_vertex = True
                    bpy.ops.paint.vert_select_all (action='SELECT')
                        
                    if limit_prop != 'unlimited':
                        limit = int (limit_prop)
                        bpy.ops.object.vertex_group_limit_total (group_select_mode='ALL', limit=limit)
                
                    # clean vertex weights with 0 influence
                    bpy.ops.object.vertex_group_clean (group_select_mode='ALL', limit=0, keep_single=False)
        
        bpy.ops.object.mode_set (mode='OBJECT')
        bpy.ops.object.select_all (action='DESELECT')          
                    
        ############################################################
        # REMOVE VERT COLORS, SHAPE KEYS, UVMAPS AND MERGE MATERIALS 
        ############################################################
        
        # render meshes
        
        for obj in meshes_to_export:
            if obj.type == 'MESH':
                mesh = obj.data
                
                # vert colors
                if not export_vert_colors:
                    vcolors = mesh.color_attributes
                    for vc in vcolors:
                        vcolors.remove (vc)
                else:
                    vcolors = mesh.color_attributes
                    vcolors_to_remove = []
                    for index, vc in enumerate (vcolors):
                        if not mesh.gyaz_export.vert_color_export[index]:
                            vcolors_to_remove.append (vc)
                    
                    for vc in reversed (vcolors_to_remove):
                        vcolors.remove (vc)
                        
                # shape keys        
                if not export_shape_keys:
                    if mesh.shape_keys is not None:
                        for key in reversed(mesh.shape_keys.key_blocks):
                            obj.shape_key_remove (key)
                            
                # uv maps
                uvmaps = mesh.uv_layers     
                uvmaps_to_remove = []
                for index, uvmap in enumerate (uvmaps):
                    if not mesh.gyaz_export.uv_export[index]:
                        uvmaps_to_remove.append (uvmap)
                        
                for uvmap in reversed (uvmaps_to_remove):
                    uvmaps.remove (uvmap)
                                        
                # merge materials
                if obj.data.gyaz_export.merge_materials:
                
                    mats = obj.data.materials

                    not_excluded_material = None
                    not_excluded_material_idx = -1

                    deleted_mat_indices = []

                    for mat_idx, mat in enumerate(mats):
                        merge_excluded = obj.data.gyaz_export.merge_exclusions[mat_idx] if mat_idx <= 31 else False
                        if not merge_excluded:
                            not_excluded_material = mat
                            not_excluded_material_idx = mat_idx
                            break

                    if not_excluded_material is not None:
                        for mat_idx, mat in enumerate(mats):
                            merge_excluded = obj.data.gyaz_export.merge_exclusions[mat_idx] if mat_idx <= 31 else False
                            if mat is not not_excluded_material and not merge_excluded:
                                deleted_mat_indices.append(mat_idx)
                        
                        deleted_mat_indices_set = set(deleted_mat_indices)
                        for face in mesh.polygons:
                            if face.material_index in deleted_mat_indices_set:
                                face.material_index = not_excluded_material_idx
                        
                        for slot_idx in reversed(deleted_mat_indices):
                            mats.pop(index=slot_idx)
                                
                        atlas_name = obj.data.gyaz_export.atlas_name
                        atlas_material = bpy.data.materials.get (atlas_name)
                        if atlas_material is None:
                            atlas_material = bpy.data.materials.new (name=atlas_name)
                        obj.material_slots[not_excluded_material_idx].material = atlas_material

                mesh.update()

            
        # collision         
        for obj in collision_objects:
            if obj.type == 'MESH':
                mesh = obj.data
                
                vcolors = mesh.vertex_colors
                for vc in vcolors:
                    vcolors.remove (vc)
                    
                if mesh.shape_keys is not None:
                    for key in mesh.shape_keys.key_blocks:
                        obj.shape_key_remove (key)
                
                name = obj.name
                if name.startswith("UBX_") or name.startswith("UCP_"):
                    bake_collision_object(obj)


        ############################################################
        # REMOVE IMAGES FROM EXPORTED MATERIALS 
        ############################################################

        # don't want the fbx file to refrence images
        for image_node in image_nodes:
            image_node.image = None

        ###########################################################
        # TEXTURE FUNCTIONS
        ###########################################################       
        
        def export_images (texture_root):

            export_textures = scene_gyaz_export.export_textures

            if export_textures:
                
                # store current render settings
                settings = bpy.context.scene.render.image_settings
                set_format = settings.file_format
                set_mode = settings.color_mode
                set_depth = settings.color_depth
                set_compresssion = settings.compression     
                
                if len (image_set) > 0:
                    
                    texture_folder = os.path.join(texture_root, sn(prefs.texture_folder_name))
                    os.makedirs (texture_folder, exist_ok=True)
                    
                    image_constants = POD()

                    image_constants.format_map = {
                        'BMP': 'bmp',
                        'IRIS': 'rgb',
                        'PNG': 'png',
                        'JPEG': 'jpg',
                        'JPEG_2000': 'jp2',
                        'TARGA': 'tga',
                        'TARGA_RAW': 'tga',
                        'CINEON': 'cin',
                        'DPX': 'dpx',
                        'OPEN_EXR_MULTILAYER': 'exr',
                        'OPEN_EXR': 'exr',
                        'HDR': 'hdr',
                        'TIFF': 'tif'
                    }

                    image_constants._8_bits = (8, 24, 32)
                    image_constants._16_bits = (16, 48, 64)
                    image_constants._32_bits = (96, 128)
                     
                    image_constants._1_channel = (8, 16)
                    image_constants._3_channels = (24, 48, 96)
                    image_constants._4_channels = (32, 64, 128)

                    for image in image_set:
                        self.export_image (image, texture_folder, image_constants, texture_prefix, texture_suffix)


                # restore previous render settings
                scene.render.image_settings.file_format = set_format
                scene.render.image_settings.color_mode = set_mode
                scene.render.image_settings.color_depth = set_depth
                scene.render.image_settings.compression = set_compresssion
                
        ########################################################
        # EXPORT OBJECTS FUNCTION 
        ###########################################################       
            
        def export_objects (filepath, objects):
            bpy.ops.object.mode_set (mode='OBJECT')
            bpy.ops.object.select_all (action='DESELECT')

            if len (objects) > 0:            
                
                collision_objects = self.get_collision_objects_from_collision_info(objects, collision_info)
                sockets = self.get_socket_objects_from_socket_info(objects, socket_info)

                ex_tex = scene_gyaz_export.export_textures
                ex_tex_only = scene_gyaz_export.export_only_textures
                    
                final_selected_objects = objects + collision_objects + sockets
                
                # set up LOD Groups and select LOD objects
                if export_lods:
                    
                    for obj in objects:
                        lod_info_tuple = lod_info.get(obj)
                        if lod_info_tuple is not None:
                            lods = lod_info_tuple[0]
                            obj_name_wo_lod = lod_info_tuple[1]
                            if len(lods) > 0:
                                if target_unreal:
                                    empty = bpy.data.objects.new (name='LOD_' + obj_name_wo_lod, object_data=None)
                                    empty['fbx_type'] = 'LodGroup'
                                    scene.collection.objects.link (empty)
                                
                                    for lod in lods + [obj]:
                                        lod.parent = empty
                                        lod.matrix_parent_inverse = empty.matrix_world.inverted()
                                        final_selected_objects.append (lod)
                                        final_selected_objects.append (empty)

                                elif target_unity:
                                    for lod in lods + [obj]:
                                        final_selected_objects.append (lod)
                                    obj.name = obj_name_wo_lod + "_LOD0"

                            else:
                                final_selected_objects.append (obj)

                if export_sockets and target_unreal:
                    for socket in sockets:
                        socket.scale = (1, 1, 1)

                do_export = False
                if asset_type == 'STATIC_MESHES' or asset_type == 'SKELETAL_MESHES':
                    do_export = not ex_tex or ex_tex and not ex_tex_only
                else:
                    do_export = True

                if do_export:

                    bpy.ops.object.select_all(action='DESELECT')
                    
                    for obj in final_selected_objects:
                        obj.select_set(True) 
                    if len(final_selected_objects) > 0:
                        make_active(final_selected_objects[0])
                    
                    bpy.ops.export_scene.fbx(
                        filepath=filepath, 
                        use_selection=fbx_settings.use_selection,
                        use_active_collection=fbx_settings.use_active_collection, 
                        embed_textures=fbx_settings.embed_textures, 
                        global_scale=fbx_settings.global_scale, 
                        apply_unit_scale=fbx_settings.apply_unit_scale, 
                        apply_scale_options=fbx_settings.apply_scale_options, 
                        axis_forward=fbx_settings.axis_forward, 
                        axis_up=fbx_settings.axis_up, 
                        object_types=fbx_settings.object_types, 
                        use_space_transform=fbx_settings.use_space_transform,
                        bake_space_transform=fbx_settings.bake_space_transform, 
                        use_custom_props=fbx_settings.use_custom_props, 
                        path_mode=fbx_settings.path_mode, 
                        batch_mode=fbx_settings.batch_mode, 
                        use_mesh_modifiers=fbx_settings.use_mesh_modifiers, 
                        use_mesh_modifiers_render=fbx_settings.use_mesh_modifiers_render, 
                        mesh_smooth_type=fbx_settings.mesh_smooth_type, 
                        use_mesh_edges=fbx_settings.use_mesh_edges, 
                        use_tspace=fbx_settings.use_tspace, 
                        use_armature_deform_only=fbx_settings.use_armature_deform_only, 
                        add_leaf_bones=fbx_settings.add_leaf_bones, 
                        primary_bone_axis=fbx_settings.primary_bone_axis, 
                        secondary_bone_axis=fbx_settings.secondary_bone_axis, 
                        armature_nodetype=fbx_settings.armature_nodetype, 
                        bake_anim=fbx_settings.bake_anim, 
                        bake_anim_use_all_bones=fbx_settings.bake_anim_use_all_bones,
                        bake_anim_use_nla_strips=fbx_settings.bake_anim_use_nla_strips, 
                        bake_anim_use_all_actions=fbx_settings.bake_anim_use_all_actions, 
                        bake_anim_force_startend_keying=fbx_settings.bake_anim_force_startend_keying, 
                        bake_anim_step=fbx_settings.bake_anim_step, 
                        bake_anim_simplify_factor=fbx_settings.bake_anim_simplify_factor 
                    )               
                    report (self, 'Export has been successful.', 'INFO')
        
        ###########################################################
        # EXPORT BY ASSET TYPE
        ###########################################################

        bpy.ops.object.mode_set (mode='OBJECT')
        
        pack_name = sn(pack_name)
        
        if asset_type == 'STATIC_MESHES':
            
            self.rename_materials(meshes_to_export, material_prefix, material_suffix)
    
            if pack_objects:
                
                prefix = static_mesh_prefix if not pack_name.startswith(static_mesh_prefix) else ''
                suffix = static_mesh_suffix if not pack_name.endswith(static_mesh_suffix) else ''
                
                filename = prefix + pack_name + suffix + format
                folder_path = os.path.join(root_folder, meshes_folder)
                filepath = os.path.join(folder_path, filename)
                os.makedirs (folder_path, exist_ok=True)
                
                export_objects (filepath, objects = ori_sel_objs)   
                export_images (texture_root = root_folder)
                
            else:
                
                for obj in ori_sel_objs:

                    obj_name = sn(lod_info[obj][1])
                        
                    prefix = static_mesh_prefix if not obj_name.startswith (static_mesh_prefix) else ''
                    suffix = static_mesh_suffix if not obj_name.endswith (static_mesh_suffix) else ''
                    
                    filename = prefix + obj_name + suffix + format
                    folder_path = os.path.join(root_folder, meshes_folder)
                    filepath = os.path.join(folder_path, filename)
                    os.makedirs (folder_path, exist_ok=True)
                    
                    export_objects (filepath, objects = [obj])
                    export_images (texture_root = root_folder)
                    

        elif asset_type == 'SKELETAL_MESHES':
            self.rename_materials(meshes_to_export, material_prefix, material_suffix)
            
            if target_y_up_z_forward:
                self.rotate_rig(final_rig, meshes_to_export)

            if pack_objects:
                
                # export filter
                make_active_only (final_rig)
                if len (mesh_children) > 0:        
                
                    prefix = skeletal_mesh_prefix if not pack_name.startswith (skeletal_mesh_prefix) else ''
                    suffix = skeletal_mesh_suffix if not pack_name.endswith (skeletal_mesh_suffix) else ''
                    
                    filename = prefix + pack_name + suffix + format
                    folder_path = os.path.join(root_folder, meshes_folder)
                    filepath = os.path.join(folder_path + filename)
                    os.makedirs (folder_path, exist_ok=True)
                    
                    export_objects (filepath, objects = [final_rig] + mesh_children)
                    export_images (texture_root = root_folder)                
                
            else:
                if len (mesh_children) > 0:
                    for child in mesh_children:

                        child_name = sn(lod_info[child][1])
                            
                        prefix = skeletal_mesh_prefix if not child_name.startswith (skeletal_mesh_prefix) else ''
                        suffix = skeletal_mesh_suffix if not child_name.endswith (skeletal_mesh_suffix) else ''
                        
                        filename = prefix + child_name + suffix + format
                        folder_path = os.path.join(root_folder, meshes_folder)
                        filepath = os.path.join(folder_path, filename)
                        os.makedirs (folder_path, exist_ok=True)
                        
                        export_objects (filepath, objects = [final_rig, child])    
                        export_images (texture_root = root_folder)
                                        
                                
        elif asset_type == 'ANIMATIONS':

            use_override_character_name = scene_gyaz_export.use_anim_object_name_override
            override_character_name = scene_gyaz_export.anim_object_name_override

            character_name = ""
            if use_override_character_name:
                character_name = override_character_name
            else:
                character_name = ori_ao_ori_name
            character_name = sn(character_name)

            separator = "_" if character_name != "" else ""
            
            if action_export_mode == "SCENE":
                
                fbx_settings.bake_anim = True

                folder_path = os.path_join(root_folder, anims_folder)
                anim_name = sn(scene_gyaz_export.global_anim_name)
                filepath = os.path.join(folder_path, animation_prefix + character_name + "_" + anim_name + animation_suffix + format)
                os.makedirs (folder_path, exist_ok=True) 
                
                baked_action = self.bake_action_from_scene(final_rig, scene_gyaz_export.global_anim_name)
                if target_y_up_z_forward:
                    self.rotate_rig(final_rig, meshes_to_export)
                self.unconstraint_rig(final_rig)
                self.move_root_motion_from_bone_to_object(final_rig, root_bone_name, [baked_action])

                self.set_animation_name(scene_gyaz_export.global_anim_name)

                export_objects (filepath, objects = [final_rig] + mesh_children) 

            # actions
            else:
                actions_to_export = self.gather_actions_to_export(ori_ao)
                
                fbx_settings.bake_anim = True 

                baked_actions = self.bake_actions_from_ori_to_final_rig(ori_ao, final_rig, actions_to_export)
                if target_y_up_z_forward:
                    self.rotate_rig(final_rig, meshes_to_export)
                self.unconstraint_rig(final_rig) 
                self.move_root_motion_from_bone_to_object(final_rig, root_bone_name, baked_actions)
                set_active_action (ori_ao, None)
                
                if scene_gyaz_export.pack_actions:
                       
                    fbx_settings.bake_anim_use_all_actions = True

                    all_actions = bpy.data.actions
                    all_actions_list = [a for a in bpy.data.actions]
                    for action in all_actions_list:
                        if action not in baked_actions:
                            all_actions.remove(action)

                    folder_path = os.path.join(root_folder, anims_folder)
                    anim_name = sn(scene_gyaz_export.global_anim_name)
                    filepath = os.path.join(folder_path, animation_prefix + character_name + separator + anim_name + animation_suffix + format)
                    os.makedirs (folder_path, exist_ok=True) 

                    export_objects (filepath, objects = [final_rig] + mesh_children)

                else:
                    for baked_action in baked_actions:
                        
                        action_name = sn(baked_action.name)
                        folder_path = os.path.join(root_folder, anims_folder)
                        filepath = os.path.join(folder_path, animation_prefix + character_name + separator + action_name + animation_suffix + format)
                        os.makedirs (folder_path, exist_ok=True)
                        
                        set_active_action (final_rig, baked_action)
                        self.adjust_scene_to_action_length(baked_action)
                        self.set_animation_name(action_name)
                        
                        export_objects (filepath, objects = [final_rig] + mesh_children)
                        

        elif asset_type == 'RIGID_ANIMATIONS':
            
            fbx_settings.bake_anim = True
                
            # add animation data if not found
            for obj in ori_sel_objs:
                if getattr (ori_ao, "animation_data") == None:
                    ori_ao.animation_data_create ()
            
            anim_name = sn(scene_gyaz_export.rigid_anim_name)
            self.rename_materials(ori_sel_objs, material_prefix, material_suffix)             
            if rigid_anim_cubes:
                prefix_ = animation_prefix
                suffix_ = animation_suffix
            else:
                prefix_ = skeletal_mesh_prefix if scene_gyaz_export.target_app == "UNREAL" else static_mesh_prefix
                suffix_ = skeletal_mesh_suffix if scene_gyaz_export.target_app == "UNREAL" else static_mesh_suffix
                            
            if pack_objects:
                
                prefix = prefix_ if not pack_name.startswith(prefix_) else ''                            
                suffix = suffix_ if not pack_name.startswith(suffix_) else ''                            
                folder_path = os.path.join(root_folder, anims_folder)
                separator = "_" if pack_name != "" else ""
                filepath = os.path.join(folder_path, prefix + pack_name + separator + anim_name + suffix + format)
                
                os.makedirs(folder_path, exist_ok=True) 
                self.set_animation_name(anim_name)
                    
                export_objects (filepath, objects = ori_sel_objs)
                if not rigid_anim_cubes:
                    export_images (texture_root = root_folder)
                    
            else:
            
                for obj in ori_sel_objs:

                    obj_name = sn(lod_info[obj][1])

                    prefix = prefix_ if not obj.name.startswith(prefix_) else ''
                    suffix = suffix_ if not obj.name.startswith(suffix_) else ''
                    folder_path = os.path.join(root_folder, anims_folder)
                    separator = "_" if obj_name != "" else ""
                    filepath = os.path.join(folder_path, prefix + obj_name + separator + anim_name + suffix + format)
                    
                    self.adjust_scene_to_action_length(get_active_action(obj))
                    self.set_animation_name(anim_name)
                    
                    os.makedirs(folder_path, exist_ok=True)
                    
                    export_objects (filepath, objects = [obj])
                    if not rigid_anim_cubes:
                        export_images (texture_root = root_folder)
        
        ###############################################################
        # REOPEN LAST SAVED .BLEND FILE
        # to restore the scene to the state before the exporting
        ###############################################################        
        
        if not (scene_gyaz_export.show_debug_props and scene_gyaz_export.dont_reload_scene):
            bpy.ops.wm.open_mainfile (filepath=blend_path)
        
        return {'FINISHED'}

    def get_collision_objects_from_collision_info(self, objects, collision_info):
        collision_objects = []
        for object in objects:
            infos = collision_info.get(object.name)
            if infos is not None:
                for info in infos:
                    collision_objects.append(info[0])
        return collision_objects

    def get_socket_objects_from_socket_info(self, objects, socket_info):
        socket_objects = []
        for object in objects:
            sockets = socket_info.get(object.name)
            if sockets is not None:
                for socket in sockets:
                    socket_objects.append(socket)
        return socket_objects

    def make_every_collection_and_object_visible_in_scene(self, scene):
        for collection in bpy.context.view_layer.layer_collection.children:
            self.make_collection_visible_recursive(collection)

        # make sure all objects are selectable
        for obj in scene.objects:
            obj.hide_select = False
            obj.hide_viewport = False
            obj.hide_set(False)

    def make_collection_visible_recursive(self, collection):
        collection.exclude = False
        collection.hide_viewport = False
        for child in collection.children:
            self.make_collection_visible_recursive(child)


    def rename_materials(self, objects, material_prefix, material_suffix):
        scene = bpy.context.scene
        if scene.gyaz_export.use_prefixes:
        
            # get list of materials
            materials = set ()
            for obj in objects:
                slots = obj.material_slots
                for slot in slots:
                    material = slot.material
                    if material is not None:
                        materials.add (material)
                
            # add prefix to materials
            for material in materials:
                name = material.name
                prefix = material_prefix if not name.startswith(material_prefix) else ''
                suffix = material_suffix if not name.endswith(material_suffix) else ''
                material.name = prefix + name + suffix


    def export_image (self, image, texture_folder, image_constants, texture_prefix, texture_suffix):
        
        scene = bpy.context.scene
        scene_gyaz_export = scene.gyaz_export

        if image.name == '':
            image.name = 'texture'
            
        if image.source == 'FILE':
            
            image.name = remove_dot_plus_three_numbers (image.name)
            
            if scene_gyaz_export.texture_format_mode == 'ALWAYS_OVERRIDE':
                final_image_format = scene_gyaz_export.texture_format_override
            else:
                """KEEP_IF_ANY"""  
                final_image_format = image.file_format
            
            new_image = image.copy ()
            new_image.pack ()
            
            image_extension = image_constants.format_map[image.file_format]    
            image_name_ending = str.lower (image.name[-4:])
            
            if image_name_ending == '.'+image_extension:
                extension = ''
            else:
                extension = '.'+image_extension
            new_image.name = image.name + extension
            new_image.name = new_image.name [:-4]
            
            final_extension = image_constants.format_map[final_image_format]
            
            prefix = texture_prefix if not new_image.name.startswith (texture_prefix) else ''  
            suffix = texture_suffix if not new_image.name.endswith (texture_suffix) else ''  
                
            new_image.filepath = os.path.join(texture_folder, prefix + sn(new_image.name) + suffix + '.' + final_extension)
            new_image.filepath = os.path.abspath ( bpy.path.abspath (new_image.filepath) )

            # color depth
            if image.depth in image_constants._8_bits:
                final_color_depth = '8'
            elif image.depth in image_constants._16_bits:
                final_color_depth = '16'
            elif image.depth in image_constants._32_bits:
                final_color_depth = '32'
            else:  
                # fallback
                final_color_depth = '8'
            
            # color mode
            if image.depth in image_constants._1_channel:
                final_color_mode = 'BW'
            elif image.depth in image_constants._3_channels:
                final_color_mode = 'RGB'
            elif image.depth in image_constants._4_channels:
                final_color_mode = 'RGBA'
            else:
                # fallback
                final_color_mode = 'RGBA'
            
            # save image
            filepath = new_image.filepath

            # change render settings to target format
            settings = bpy.context.scene.render.image_settings
            settings.file_format = final_image_format
            settings.color_mode = final_color_mode
            settings.color_depth = final_color_depth
            settings.compression = int(scene_gyaz_export.texture_compression * 100)

            # save
            new_image.save_render (filepath)


    @staticmethod
    def constraint_bone(rig, bone_name, target_rig, target_bone_name, target_cm_scale_unit):
        pbones = rig.pose.bones
        pbone = pbones[bone_name]

        c = pbone.constraints.new (type='COPY_LOCATION')
        c.target = target_rig
        c.subtarget = target_bone_name
        
        c = pbone.constraints.new (type='COPY_ROTATION')
        c.target = target_rig
        c.subtarget = target_bone_name
        
        if target_cm_scale_unit:
            c = pbone.constraints.new (type='TRANSFORM')
            c.target = target_rig
            c.subtarget = target_bone_name
            c.use_motion_extrapolate = True
            c.map_from = 'SCALE'
            c.map_to = 'SCALE'
            c.map_to_x_from = 'X'
            c.map_to_y_from = 'Y'
            c.map_to_z_from = 'Z'
            c.from_min_x_scale = -1
            c.from_max_x_scale = 1
            c.from_min_y_scale = -1
            c.from_max_y_scale = 1
            c.from_min_z_scale = -1
            c.from_max_z_scale = 1
            c.to_min_x_scale = -0.01
            c.to_max_x_scale = 0.01
            c.to_min_y_scale = -0.01
            c.to_max_y_scale = 0.01
            c.to_min_z_scale = -0.01
            c.to_max_z_scale = 0.01
        else:
            c = pbone.constraints.new (type='COPY_SCALE')
            c.target = target_rig
            c.subtarget = target_bone_name


    def bake_actions_from_ori_to_final_rig(self, ori_rig, final_rig, actions):
        baked_actions = []
        scene = bpy.context.scene

        for action in actions:
            make_active_only (ori_rig)
            set_active_action (ori_rig, action)
            self.adjust_scene_to_action_length(action)
            make_active_only (final_rig)
            bpy.ops.nla.bake (frame_start=scene.frame_start, frame_end=scene.frame_end, only_selected=False, 
                              visual_keying=True, clear_constraints=False, clear_parents=False, use_current_action=False, 
                              bake_types={'POSE'})
            new_action = get_active_action (final_rig)
            action_name = action.name
            action.name = "GYAZ_Export_OLD_" + action_name
            new_action.name = action_name
            new_action.name = action_name
            baked_actions.append(new_action)

        return baked_actions


    def bake_action_from_scene(self, rig, new_action_name):
        scene = bpy.context.scene
        make_active_only (rig)
        bpy.ops.nla.bake (frame_start=scene.frame_start, frame_end=scene.frame_end, only_selected=False, 
                          visual_keying=True, clear_constraints=False, clear_parents=False, use_current_action=False, 
                          bake_types={'POSE'})
        new_action = get_active_action (rig)
        new_action.name = new_action_name
        new_action.name = new_action_name
        return new_action


    def gather_actions_to_export(self, obj):
        actions_to_export = []
        scene = bpy.context.scene
        action_export_mode = scene.gyaz_export.action_export_mode
        all_actions = bpy.data.actions

        if action_export_mode == 'ACTIVE':
            active_action = get_active_action(obj)
            if active_action is not None: 
                actions_to_export.append (active_action)
                
        elif action_export_mode == 'ALL':
            for action in bpy.data.actions:
                actions_to_export.append (all_actions[action.name])
                
        elif action_export_mode == 'BY_NAME':
            for item in scene.gyaz_export.actions:
                actions_to_export.append (all_actions[item.name])
                
        return actions_to_export
    
    
    def adjust_scene_to_action_length(self, action):
        scene = bpy.context.scene
        frame_start, frame_end = action.frame_range
        scene.frame_start = int(frame_start)
        scene.frame_end = int(frame_end)
        scene.frame_preview_start = int(frame_start)
        scene.frame_preview_end = int(frame_end)


    def set_animation_name(self, name):
        bpy.context.scene.name = name
        bpy.context.scene.name = name


    def unconstraint_rig(self, rig):
        for pbone in rig.pose.bones:
            clear_blender_collection(pbone.constraints)
        clear_blender_collection(rig.constraints)


    def rotate_rig(self, rig, meshes):
        bpy.ops.object.mode_set(mode='OBJECT')

        rot_mat = Matrix.Rotation(radians(-90.0), 4, "X")
        rig.matrix_world = rot_mat @ rig.matrix_world

        make_active_only(rig)
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        
        bpy.ops.object.select_all(action='DESELECT')
        for mesh in meshes:
            mesh.select_set(True)
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    def move_root_motion_from_bone_to_object(self, rig, root_bone_name, actions):
        
        scene = bpy.context.scene

        # craete root empty
        root_empty = bpy.data.objects.new(name="GYAZ_Exporter_root_empty", object_data=None)
        root_empty.rotation_mode = "QUATERNION"
        scene.collection.objects.link(root_empty)

        for action in actions:
            
            # constraint root_empty to rig's root bone
            cs = root_empty.constraints
            
            c = cs.new(type="COPY_LOCATION")
            c.target = rig
            c.subtarget = root_bone_name
            
            c = cs.new(type="COPY_ROTATION")
            c.target = rig
            c.subtarget = root_bone_name
            c.target_space = "LOCAL_OWNER_ORIENT"
            
            # bake root motion from rig's root bone to root_empty
            make_active_only(root_empty)
            set_active_action(rig, action)
            bpy.ops.nla.bake(frame_start=scene.frame_start, frame_end=scene.frame_end, only_selected=False, visual_keying=True, 
                            clear_constraints=True, clear_parents=False, use_current_action=False, bake_types={'OBJECT'})
            
            # constraint rig to root_empty
            cs = rig.constraints
            
            c = cs.new(type="COPY_LOCATION")
            c.target = root_empty
            
            c = cs.new(type="COPY_ROTATION")
            c.target = root_empty
            
            # remove root motion from rig's root bone
            root_bone_fcurve_data_path_prefix = 'pose.bones["' + root_bone_name + '"].'
            fcurves = action.fcurves
            for fcurve in fcurves:
                if fcurve.data_path.startswith(root_bone_fcurve_data_path_prefix):
                    fcurves.remove(fcurve)
            
            # bake root motion from root_empty to rig
            make_active_only(rig)
            bpy.ops.nla.bake(frame_start=scene.frame_start, frame_end=scene.frame_end, only_selected=False, visual_keying=True, 
                            clear_constraints=True, clear_parents=False, use_current_action=True, bake_types={'OBJECT'})
            
        # delete root_empty
        scene.collection.objects.unlink(root_empty)
        bpy.data.objects.remove(root_empty, do_unlink=True)

        # remove root bone from rig
        make_active_only(rig)
        bpy.ops.object.mode_set(mode="EDIT")
        rig.data.edit_bones.remove(rig.data.edit_bones[root_bone_name])
        bpy.ops.object.mode_set(mode="OBJECT")


    def _gather_objects_from_collection_recursive(self, collection, objects):
        objects.update(set(obj for obj in collection.objects if obj.gyaz_export.export))
        for col in collection.children:
            self._gather_objects_from_collection(col, objects)


    def gather_objects_from_collection_recursive(self, collection):
        objects = set()
        self._gather_objects_from_collection_recursive(collection, objects)
        return list(objects)


    def gather_objects_from_collection(self, collection):
        return list({obj for obj in collection.objects if obj.gyaz_export.export})

    
    # when the buttons should show up    
    @classmethod
    def poll(cls, context):
        ao =  bpy.context.active_object  
        return ao is not None


#######################################################
#######################################################

# REGISTER

def register():
    bpy.utils.register_class (Op_GYAZ_Export_Export) 
   

def unregister ():
    bpy.utils.unregister_class (Op_GYAZ_Export_Export)    

  
if __name__ == "__main__":   
    register()   