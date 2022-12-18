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
from bpy.types import AddonPreferences, UIList, Scene, Object, Mesh, Menu
from mathutils import Vector, Matrix, Quaternion
import numpy as np
from math import radians
from pathlib import Path
from bpy.props import *


def popup (lines, icon, title):
    def draw(self, context):
        for line in lines:
            self.layout.label(text=line)
    bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)
    
def list_to_visual_list (list):
    return ", ".join(list)


def report (self, item, error_or_info):
    self.report({error_or_info}, item)

    
def make_active_only (obj):
    bpy.ops.object.mode_set (mode='OBJECT')
    bpy.ops.object.select_all (action='DESELECT')
    obj.select_set (True)
    bpy.context.view_layer.objects.active = obj

    
def make_active (obj):
    bpy.context.view_layer.objects.active = obj   


# safe name
def sn (line):
    for c in '/\:*?"<>|.,= '+"'":
        line = line.replace (c, '_')
    return (line)


def detect_mirrored_uvs (bm, uv_index):
    uv_layer = bm.loops.layers.uv[uv_index]
    mirrored_face_count = 0
    for face in bm.faces:
        uvs = [tuple(loop[uv_layer].uv) for loop in face.loops]
        x_coords, y_coords = zip (*uvs)
        result = 0.5 * np.array (np.dot(x_coords, np.roll(y_coords, 1)) - np.dot(y_coords, np.roll(x_coords, 1)))
        if result > 0:
            mirrored_face_count += 1
            break
    if mirrored_face_count > 0:
        return True
    else:
        return False   


untransformed_matrix = Matrix (([1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1])) 
 
                
def get_active_action (obj):
    if obj.animation_data is not None:
        return obj.animation_data.action


def clear_transformation (object):
    for c in object.constraints:
        c.mute = True
    object.location = [0, 0, 0]
    object.scale = [1, 1, 1]
    object.rotation_quaternion = [1, 0, 0, 0]
    object.rotation_euler = [0, 0, 0]
    object.rotation_axis_angle = [0, 0, 1, 0]

    
def clear_transformation_matrix (object):
    for c in object.constraints:
        c.mute = True
    object.matrix_world = untransformed_matrix
    

def _gather_images(node_tree, images):
    for node in node_tree.nodes:
        if node.type == 'TEX_IMAGE' or node.type == 'TEX_ENVIRONMENT':
            if node is not None:
                images.add(node.image)
        elif node.type == 'GROUP':
            _gather_images(node.node_tree, images)


# get set of texture images in node tree
def gather_images_from_nodes (node_tree):
    images = set()
    _gather_images(node_tree, images)
    return set (images)


def is_str_blank (s):
    return s.replace (" ", "") == ""
    

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
        owner = scene.gyaz_export

        target_cm_scale_unit = owner.target_app == "UNREAL"
        target_y_up_z_forward = owner.target_app == "UNITY"
        lod_setup_mode = "FBX_LOD_GROUP" if owner.target_app == "UNREAL" else "BY_NAME_WITH_0"
        
        scene_objects = scene.objects
        ori_ao = bpy.context.active_object
        ori_ao_name = bpy.context.active_object.name
        
        asset_type = owner.skeletal_asset_type if ori_ao.type == 'ARMATURE' else owner.rigid_asset_type 

        mesh_children = [child for child in ori_ao.children if child.type == 'MESH' and child.gyaz_export.export]

        if asset_type == "ANIMATIONS":
            if owner.skeletal_shapes:
                # don't export meshes with no shape keys
                for obj in mesh_children.copy():
                    if obj.data.shape_keys is None or len(obj.data.shape_keys.key_blocks) == 0:
                        mesh_children.remove(obj)
            else:
                # don't export meshes if shape key export is disabled
                mesh_children = []

        ###############################################################
        # GATHER OBJECTS COLLECTIONS
        ############################################################### 

        # gather all objects from active collection
        if asset_type == 'STATIC_MESHES' or asset_type == 'RIGID_ANIMATIONS':
            if asset_type == 'STATIC_MESHES':
                gather_from_collection = owner.static_mesh_gather_from_collection
                gather_nested = owner.static_mesh_gather_nested
            elif asset_type == 'RIGID_ANIMATIONS':
                gather_from_collection = owner.rigid_anim_gather_from_collection
                gather_nested = owner.rigid_anim_gather_nested            
            
            if not gather_from_collection:
                ori_sel_objs = [obj for obj in bpy.context.selected_objects if obj.gyaz_export.export]
            else:
                name = ori_ao_name
                collections = bpy.data.collections
                x = [col for col in collections if name in col.objects]
                if x:
                    active_collection = x[0]
                    
                    objects_ = {obj for obj in active_collection.objects if obj.gyaz_export.export}
                    if gather_nested:
                        def gather(collection):
                            objects_.update(set(obj for obj in collection.objects if obj.gyaz_export.export))
                            for col in collection.children:
                                gather(col)
                        for col in active_collection.children:
                            gather(col)
                    
                    ori_sel_objs = list(objects_)
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
        
        export_lods = owner.export_lods if asset_type == 'STATIC_MESHES' else False
        lod_info = {}
        lods = []
        if export_lods:
            scene_objs_info = {str.lower(obj.name).replace(' ', '').replace('.', '').replace('_', ''): obj.name for obj in scene_objects}

            # gather lods
            for obj in meshes_to_export:

                obj_lods = []
                name = str.lower(obj.name).replace(' ', '').replace('.', '').replace('_', '')
                for n in range (1, 10):
                    suffix = 'lod' + str(n)
                    lod_name_candidate = name + suffix
 
                    if lod_name_candidate in scene_objs_info.keys ():
                        lod_obj_name = scene_objs_info[lod_name_candidate]
                        lod_obj = scene_objects.get (lod_obj_name)
                        if lod_obj is not None:
                            if lod_obj.type == 'MESH':
                                obj_lods.append (lod_obj)
                
                lods += obj_lods
                lod_info[obj.name] = obj_lods
            
            meshes_to_export += lods
            
            lods_set = set (lods)
            ori_sel_objs = list ( set (ori_sel_objs) - lods_set )
            
        ###############################################################
        # GATHER COLLISION
        ############################################################### 

        export_collision = owner.export_collision
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
        

        root_folder = owner.export_folder
        
        if asset_type == 'STATIC_MESHES':
            pack_objects = owner.static_mesh_pack_objects
            pack_name = owner.static_mesh_pack_name
        elif asset_type == 'SKELETAL_MESHES' or asset_type == 'ANIMATIONS':
            pack_objects = owner.skeletal_mesh_pack_objects
            pack_name = ori_ao_name
        elif asset_type == 'RIGID_ANIMATIONS':
            pack_objects = owner.rigid_anim_pack_objects
            pack_name = owner.rigid_anim_pack_name
            
        if asset_type == 'STATIC_MESHES':
            export_vert_colors = owner.static_mesh_vcolors
        elif asset_type == 'SKELETAL_MESHES':
            export_vert_colors = owner.skeletal_mesh_vcolors
        elif asset_type == 'RIGID_ANIMATIONS':
            export_vert_colors = owner.rigid_anim_vcolors
        else:
            export_vert_colors = False
            
        if asset_type == 'SKELETAL_MESHES' or asset_type == 'ANIMATIONS':
            export_shape_keys = owner.skeletal_shapes
        elif asset_type == 'RIGID_ANIMATIONS':
            export_shape_keys = owner.rigid_anim_shapes
        else:
            export_shape_keys = False
            
        action_export_mode = owner.action_export_mode
        
        rigid_anim_cubes = True if owner.rigid_anim_cubes and not pack_objects else False
        
        # root bone name
        root_bone_name = owner.root_bone_name

        def main (asset_type, image_info, image_set, ori_ao, ori_ao_name, ori_sel_objs, mesh_children, meshes_to_export, root_folder, pack_objects, action_export_mode, pack_name, lod_info, lods, export_collision, collision_info, export_sockets):
            
            ###############################################################
            #SAVE .BLEND FILE BEFORE DOING ANYTHING
            ###############################################################        
            
            file_is_saved = False
            blend_data = bpy.context.blend_data
            blend_path = blend_data.filepath

            if blend_data.is_saved:
                bpy.ops.wm.save_as_mainfile (filepath=blend_path)
                file_is_saved = True

            else:
                report (self, 'File has never been saved.', 'WARNING')
                file_is_saved = False
             
                
            ###############################################################

            def set_bone_parent (name, parent_name):
                ebones = bpy.context.active_object.data.edit_bones
                
                ebone = ebones.get (name)
                if ebone is not None:
                    if parent_name == None:
                        ebone.parent = None      
                    else:
                        ebone.parent = ebones.get (parent_name)                     
            
            ######################################################
            # MAIN VARIABLES
            ######################################################

            scene_objects = bpy.context.scene.objects
            owner = scene.gyaz_export
                
            # make sure all objects are selectable
            values = [False] * len (scene_objects)
            scene_objects.foreach_set ('hide_select', values)
            
            # make list of bones to keep    
            if asset_type == 'SKELETAL_MESHES' or asset_type == 'ANIMATIONS':
                
                if not scene.gyaz_export.export_all_bones:
                    export_bones = scene.gyaz_export.export_bones
                else:
                    export_bones = ori_ao.data.bones
                export_bone_list = [item.name for item in export_bones]
                extra_bones = scene.gyaz_export.extra_bones
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
                clear_transforms = scene.gyaz_export.static_mesh_clear_transforms
            elif asset_type == 'SKELETAL_MESHES' or asset_type == 'ANIMATIONS':
                clear_transforms = scene.gyaz_export.skeletal_clear_transforms
            
            
            # get root mode    
            if asset_type == 'SKELETAL_MESHES' or asset_type == 'ANIMATIONS':
                root_mode = scene.gyaz_export.root_mode
                
                
            # make all collectios visible
            for collection in bpy.context.scene.collection.children:
                # collection.exclude doesn't work
                try:
                    #collection.exclude = False
                    collection.hide_viewport = False
                    collection.hide_select = False
                    for obj in collection.objects:
                        obj.hide_viewport, obj.hide_select = False, False
                        obj.hide_set (False)
                except:
                    ''
                
            
            length = len (scene.gyaz_export.extra_bones)    
            constraint_extra_bones = scene.gyaz_export.constraint_extra_bones if length > 0 else False
            rename_vert_groups_to_extra_bones = scene.gyaz_export.rename_vert_groups_to_extra_bones if length > 0 else False
            
            # file format
            exporter = scene.gyaz_export.exporter
            if exporter == 'FBX':
                format = '.fbx'
                
            #######################################################
            # EXPORT FOLDER
            #######################################################
            
            export_folder_mode = scene.gyaz_export.export_folder_mode
            relative_folder_name = scene.gyaz_export.relative_folder_name
            export_folder = scene.gyaz_export.export_folder

            #export folder
            if export_folder_mode == 'RELATIVE_FOLDER':
                relative_folder_path = "//" + relative_folder_name
                #make sure it is an absolute path
                root_folder = os.path.abspath ( bpy.path.abspath (relative_folder_path) )
                #create relative folder
                os.makedirs(root_folder, exist_ok=True)
            
            elif export_folder_mode == 'PATH':    
                #make sure it is an absolute path
                root_folder = os.path.abspath ( bpy.path.abspath (export_folder) )
                
            
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
                
                    
                # gather and rescale sockets (single bone armature objects)
                export_sockets = owner.export_sockets
                if export_sockets:
                    
                    for obj in ori_sel_objs:
                        for child in obj.children:
                            if child.type == 'ARMATURE' and child.name.startswith ('SOCKET_'):
                                if target_cm_scale_unit:
                                    child.scale *= .01
                                if child.rotation_mode != 'QUATERNION':
                                    child.rotation_mode = 'QUATERNION'
                                child.rotation_quaternion = child.rotation_quaternion @ Quaternion((0.707, 0.707, .0, .0))
                                sockets.append (child)
                                
                
                # clear lod transform
                if export_lods:
                        
                    lod_info_keys = set (lod_info.keys ())
                    for obj in ori_sel_objs:
                        obj_name = obj.name
                        if obj_name in lod_info_keys:
                            lods = lod_info[obj_name]
                            
                            for lod in lods:
                                if clear_transforms:
                                    clear_transformation(lod)             
                            

            #######################################################
            # REPLACE SKELETAL MESHES WITH CUBES
            # don't want to have high poly meshes in every animation file
            #######################################################
            
            if (asset_type == 'ANIMATIONS' and owner.skeletal_shapes) or (asset_type == 'RIGID_ANIMATIONS' and rigid_anim_cubes):

                bpy.ops.object.mode_set (mode='OBJECT')                
                            
                objs = mesh_children if asset_type == 'ANIMATIONS' else ori_sel_objs
                for obj in objs:
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
            # AXIS ORIENTATION
            #######################################################

            if asset_type == "STATIC_MESHES" and target_y_up_z_forward:

                bpy.ops.object.mode_set (mode='OBJECT')
                
                final_mats = []

                rot_mat = Matrix.Rotation(radians(-90.0), 4, "X")
                inverse_rot_mat = Matrix.Rotation(radians(90.0), 4, "X")

                for obj in meshes_to_export:
                    ori_mat = obj.matrix_world.copy()
                    parent = obj.parent
                    if parent is not None:
                        obj.parent = None
                        obj.matrix_world = ori_mat
                    final_mat = rot_mat @ ori_mat @ inverse_rot_mat
                    final_mats.append(final_mat)

                    obj.matrix_world = Matrix()
                    obj.matrix_world = rot_mat @ obj.matrix_world

                ctx = bpy.context.copy()
                ctx['selected_objects'] = meshes_to_export
                ctx['selected_editable_objects'] = meshes_to_export
                bpy.ops.object.transform_apply(ctx, location=True, rotation=True, scale=True)

                obj_idx = -1
                for obj in meshes_to_export:
                    obj_idx += 1
                    print(final_mats[obj_idx])
                    obj.matrix_world = final_mats[obj_idx]

            if (asset_type == "SKELETAL_MESHES" or asset_type == "ANIMATIONS") and target_y_up_z_forward:

                bpy.ops.object.mode_set (mode='OBJECT')
                
                final_mats = []

                rot_mat = Matrix.Rotation(radians(-90.0), 4, "X")
                
                ori_ao.matrix_world = rot_mat @ ori_ao.matrix_world

                inverse_rot_mat = Matrix.Rotation(radians(90.0), 4, "X")

                ctx = bpy.context.copy()
                ctx['selected_objects'] = ctx['selected_editable_objects'] = [ori_ao]
                bpy.ops.object.transform_apply(ctx, location=True, rotation=True, scale=True)

                ctx = bpy.context.copy()
                ctx['selected_objects'] = ctx['selected_editable_objects'] = meshes_to_export
                bpy.ops.object.transform_apply(ctx, location=True, rotation=True, scale=True)

            #######################################################
            # BUILD FINAL RIG
            #######################################################
            
            final_rig = None

            if asset_type == 'SKELETAL_MESHES' or asset_type == 'ANIMATIONS':
                
                if scene.gyaz_export.rig_mode == "AS_IS":
                    final_rig = ori_ao
                    # renaming just once may not be enough
                    final_rig.name = root_bone_name
                    final_rig.name = root_bone_name

                elif scene.gyaz_export.rig_mode == "BUILD":
                    make_active_only (ori_ao)
                    bpy.ops.object.mode_set (mode='EDIT')
                    ebones = ori_ao.data.edit_bones
                    
                    # extra bone info
                    extra_bone_info = []
                    extra_bones = scene.gyaz_export.extra_bones
                    for item in extra_bones:
                        ebone = ebones.get (item.source)
                        if ebone is not None:
                            info = {'name': item.name, 'head': ebone.head[:], 'tail': ebone.tail[:], 'roll': ebone.roll, 'parent': item.parent}
                            extra_bone_info.append (info)
                    
                    bpy.ops.object.mode_set (mode='OBJECT')
                    
                    # duplicate armature
                    final_rig_data = ori_ao.data.copy ()
                    
                    # create new armature object
                    final_rig = bpy.data.objects.new (name=root_bone_name, object_data=final_rig_data)
                    scene.collection.objects.link (final_rig)
                    make_active_only (final_rig)
                    # renaming just once may not be enough
                    final_rig.name = root_bone_name
                    final_rig.name = root_bone_name
                    final_rig.rotation_mode = "QUATERNION"
                    
                    # remove drivers
                    if hasattr (final_rig_data, "animation_data") == True:
                        if final_rig_data.animation_data is not None:
                            for driver in final_rig_data.animation_data.drivers:
                                final_rig_data.driver_remove (driver.data_path)
                    
                    # delete bones
                    bpy.ops.object.mode_set (mode='EDIT')
                    all_bones = set (bone.name for bone in final_rig_data.bones)
                    bones_to_remove = all_bones - set (export_bone_list)
                    bones_to_remove.add (root_bone_name)
                    for name in bones_to_remove:
                        ebones = final_rig_data.edit_bones
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
                        set_bone_parent (item['name'], item['parent'] )    
                        
                    # delete constraints
                    bpy.ops.object.mode_set (mode='POSE')
                    for pbone in final_rig.pose.bones:
                        for c in pbone.constraints:
                            pbone.constraints.remove (c)

                    # make all bones visible
                    for n in range (0, 32):
                        final_rig_data.layers[n] = True
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
                    make_active_only (final_rig)
                    bpy.ops.object.mode_set (mode='POSE')
                    
                    def constraint_bones (source_bone, target_bone, source_obj, target_obj):
                        pbones = target_obj.pose.bones
                        pbone = pbones[target_bone]

                        c = pbone.constraints.new (type='COPY_LOCATION')
                        c.target = source_obj
                        c.subtarget = source_bone
                        
                        c = pbone.constraints.new (type='COPY_ROTATION')
                        c.target = source_obj
                        c.subtarget = source_bone
                        
                        if target_cm_scale_unit:
                            c = pbone.constraints.new (type='TRANSFORM')
                            c.target = source_obj
                            c.subtarget = source_bone
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
                            c.target = source_obj
                            c.subtarget = source_bone
                
                    # constraint 'export bones'        
                    for name in export_bone_list:
                        constraint_bones (name, name, ori_ao, final_rig)
                    
                    # constraint 'extra bones'
                    if constraint_extra_bones:                                                                                     
                        for item in scene.gyaz_export.extra_bones:
                            new_name = item.name
                            source_name = item.source
                            parent_name = item.parent     
                            constraint_bones (source_name, new_name, ori_ao, final_rig)            
                    
                    # constraint root 
                    if root_mode == 'BONE':
                        if ori_ao.data.bones.get (root_bone_name) is not None:
                            subtarget = root_bone_name 
                    else:
                        subtarget = ''           
                        
                    c = final_rig.constraints.new (type='COPY_LOCATION')
                    c.target = ori_ao
                    c.subtarget = subtarget
                    
                    c = final_rig.constraints.new (type='COPY_ROTATION')
                    c.target = ori_ao
                    c.subtarget = subtarget
                    c.target_space = "LOCAL"
                    
                    if target_cm_scale_unit:
                        c = final_rig.constraints.new (type='TRANSFORM')
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
                            for item in scene.gyaz_export.extra_bones:
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
                
                limit_prop = scene.gyaz_export.skeletal_mesh_limit_bone_influences
                
                for child in mesh_children:
                    if len (child.vertex_groups) > 0:
                        make_active_only (child)
                        
                        ctx = bpy.context.copy ()
                        ctx['object'] = child

                        bpy.ops.object.mode_set (mode='WEIGHT_PAINT')
                        child.data.use_paint_mask_vertex = True
                        bpy.ops.paint.vert_select_all (action='SELECT')
                            
                        if limit_prop != 'unlimited':
                            limit = int (limit_prop)
                            bpy.ops.object.vertex_group_limit_total (ctx, group_select_mode='ALL', limit=limit)
                    
                        # clean vertex weights with 0 influence
                        bpy.ops.object.vertex_group_clean (ctx, group_select_mode='ALL', limit=0, keep_single=False)
            
            
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
                        for mat in mats:
                            if len (mats) > 1:
                                mats.pop (index=0)
                        
                        atlas_name = obj.data.gyaz_export.atlas_name
                        atlas_material = bpy.data.materials.get (atlas_name)
                        if atlas_material == None:
                            atlas_material = bpy.data.materials.new (name=atlas_name)
                        obj.material_slots[0].material = atlas_material    
                    
                
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

            #######################################################
            # EXPORT OPERATOR PROPS
            #######################################################
            
            # FBX EXPORTER SETTINGS:
            # MAIN
            use_selection = True
            use_active_collection = False
            global_scale = 1
            apply_unit_scale = False
            apply_scale_options = 'FBX_SCALE_NONE' if target_cm_scale_unit else 'FBX_SCALE_ALL'
            axis_forward = '-Z'
            axis_up = 'Y'
            object_types = {'EMPTY', 'CAMERA', 'LIGHT', 'ARMATURE', 'MESH', 'OTHER'}
            bake_space_transform = False
            use_custom_props = False
            use_space_transform = False
            
            # 'STRIP' is the only mode textures are not referenced in the fbx file (only referenced not copied - this is undesirable behavior)
            path_mode = 'STRIP'
            
            batch_mode = 'OFF'
            embed_textures = False
            # GEOMETRIES
            use_mesh_modifiers = True
            use_mesh_modifiers_render = True
            mesh_smooth_type = owner.mesh_smoothing
            use_mesh_edges = False
            use_tspace = True
            # ARMATURES
            use_armature_deform_only = False
            add_leaf_bones = owner.add_end_bones
            primary_bone_axis = owner.primary_bone_axis
            secondary_bone_axis = owner.secondary_bone_axis
            armature_nodetype = 'NULL'
            # ANIMATION
            bake_anim = False
            bake_anim_use_all_bones = False
            bake_anim_use_nla_strips = False
            bake_anim_use_all_actions = False
            bake_anim_force_startend_keying = False
            bake_anim_step = 1
            bake_anim_simplify_factor = 0
            
            # asset prefixes
            use_prefixes = scene.gyaz_export.use_prefixes
            
            if use_prefixes:
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
                
            # folder names
            textures_folder = sn(prefs.texture_folder_name) + '/'
            anims_folder = sn(prefs.anim_folder_name) + '/'
            meshes_folder = sn(prefs.mesh_folder_name) + '/'
 

            ###########################################################
            # TEXTURE FUNCTIONS
            ###########################################################       
            
            # remove dot plus three numbers from the end of image names
            def remove_dot_plus_three_numbers (name):

                def endswith_numbers (string):
                    try:
                        int(string)
                        return True
                    except:
                        return False
                    
                if endswith_numbers ( name[-3:] ) == True and name[-4] == '.':
                    return name[:-4]
                else:
                    return name
                
            
            # texture export function
            def export_images (objects, texture_root, all_images):
                # options: 'KEEP_IF_ANY', 'ALWAYS_OVERRIDE'
                image_format_mode = scene.gyaz_export.texture_format_mode
                override_format = scene.gyaz_export.texture_format_override
                export_textures = scene.gyaz_export.export_textures

                if export_textures:
                    
                    # store current render settings
                    settings = bpy.context.scene.render.image_settings
                    set_format = settings.file_format
                    set_mode = settings.color_mode
                    set_depth = settings.color_depth
                    set_compresssion = settings.compression

                    def export_image (image, texture_folder):
                                                    
                        # give image a name if it doesn't have any
                        if image.name == '':
                            image.name = 'texture'
                            
                        # save image    
                        if image.source == 'FILE':
                            
                            image.name = remove_dot_plus_three_numbers (image.name)
                            
                            if image_format_mode == 'ALWAYS_OVERRIDE':
                                final_image_format = override_format
                            else:
                                """'KEEP_IF_ANY'"""  
                                final_image_format = image.file_format
                            
                            new_image = image.copy ()
                            new_image.pack ()
                            
                            image_formats_raw = [
                                ['BMP', 'bmp'],
                                ['IRIS', 'rgb'],
                                ['PNG', 'png'],
                                ['JPEG', 'jpg'],
                                ['JPEG_2000', 'jp2'],
                                ['TARGA', 'tga'],
                                ['TARGA_RAW', 'tga'],
                                ['CINEON', 'cin'],
                                ['DPX', 'dpx'],
                                ['OPEN_EXR_MULTILAYER', 'exr'],
                                ['OPEN_EXR', 'exr'],
                                ['HDR', 'hdr'],
                                ['TIFF', 'tif']
                                ]
                                
                            image_formats = [x[0] for x in image_formats_raw]
                            image_extensions = [x[1] for x in image_formats_raw]
                            
                            image_extension = image_extensions [image_formats.index (image.file_format)]    
                            image_name_ending = str.lower (image.name[-4:])
                            
                            if image_name_ending == '.'+image_extension:
                                extension = ''
                            else:
                                extension = '.'+image_extension
                            new_image.name = image.name + extension
                            new_image.name = new_image.name [:-4]
                            
                            final_extension_index = image_formats.index (final_image_format)
                            final_extension = image_extensions [final_extension_index]
                            
                            prefix = texture_prefix if not new_image.name.startswith (texture_prefix) else ''  
                            suffix = texture_suffix if not new_image.name.endswith (texture_suffix) else ''  
                                
                            new_image.filepath = texture_folder + prefix + sn(new_image.name) + suffix + '.' + final_extension
                            new_image.filepath = os.path.abspath ( bpy.path.abspath (new_image.filepath) )
        
                                
                            # color depth
                            _8_bits = [8, 24, 32]
                            _16_bits = [16, 48, 64]
                            _32_bits = [96, 128]
                            
                            if image.depth in _8_bits:
                                final_color_depth = '8'
                            elif image.depth in _16_bits:
                                final_color_depth = '16'
                            elif image.depth in _32_bits:
                                final_color_depth = '32'
                            
                            # fall back    
                            if 'final_color_depth' not in locals():
                                final_color_depth = '8'
                            
                            
                            # color mode    
                            _1_channel = [8, 16]
                            _3_channels = [24, 48, 96]
                            _4_channels = [32, 64, 128]
                            
                            if image.depth in _1_channel:
                                final_color_mode = 'BW'
                            elif image.depth in _3_channels:
                                final_color_mode = 'RGB'
                            elif image.depth in _4_channels:
                                final_color_mode = 'RGBA'
                                
                            # fall back
                            if 'final_color_mode' not in locals():
                                final_color_mode = 'RGBA'
                            
                            
                            # save image
                            filepath = new_image.filepath

                            # change render settings to target format
                            settings.file_format = final_image_format
                            settings.color_mode = final_color_mode
                            settings.color_depth = final_color_depth
                            settings.compression = int(scene.gyaz_export.texture_compression * 100)

                            # save
                            new_image.save_render (filepath)
                            
                    
                    if len (image_set) > 0:
                        
                        texture_folder = texture_root + '/' + textures_folder
                        
                        os.makedirs (texture_folder, exist_ok=True)
                        
                        if all_images:
                            for image in image_set:
                                export_image (image, texture_folder)
                                
                        else:
                            for obj in objects:
                                if obj.name in image_info.keys ():
                                    images = image_info[obj.name]
                                    for image in images:
                                        export_image (image, texture_folder)


                    # restore previous render settings
                    scene.render.image_settings.file_format = set_format
                    scene.render.image_settings.color_mode = set_mode
                    scene.render.image_settings.color_depth = set_depth
                    scene.render.image_settings.compression = set_compresssion
                    
                    # texture export info
                    if len (image_set) > 0:
                        return texture_folder
                    

            ###########################################################
            # MATERIAL FUNCTIONS
            ###########################################################
            
            # rename materials function
            def rename_materials (objects):
                
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

 
            ###########################################################
            # ANIMATION FUNCTIONS
            ###########################################################
            
            if asset_type == 'ANIMATIONS' or asset_type == 'RIGID_ANIMATIONS':
            
                actions_names = scene.gyaz_export.actions
                
                def set_active_action (action):
                    if getattr (ori_ao, "animation_data") == None:
                        ori_ao.animation_data_create ()
                        
                    ori_ao.animation_data.action = action
                    
                    
                def get_actions_to_export (object):
                
                    actions_to_export = []

                    #make list of actions to export
                    if action_export_mode == 'ACTIVE':
                        
                        active_action = get_active_action (object)
                        
                        if active_action is not None: 
                            actions_to_export.append ( active_action )
                         
                    elif action_export_mode == 'ALL':
                        
                        for action in bpy.data.actions:
                            actions_to_export.append (bpy.data.actions[action.name])
                            
                    elif action_export_mode == 'BY_NAME':
                        
                        for item in actions_names:
                            actions_to_export.append (bpy.data.actions[item.name])
                            
                    return actions_to_export
                
                
                def adjust_scene_to_action_length (object):
                    action = get_active_action (object)
                    if action is not None:
                        if action.use_frame_range:
                            scene.frame_start = int(action.frame_start)
                            scene.frame_end = int(action.frame_end)
                        else:
                            frame_start, frame_end = action.frame_range
                            scene.frame_start = int(frame_start)
                            scene.frame_end = int(frame_end)

                def set_animation_name (name):
                    bpy.context.scene.name = name
                    bpy.context.scene.name = name
            
            ########################################################
            # EXPORT OBJECTS FUNCTION 
            ###########################################################       
                
            # export objects
            def export_objects (filepath, objects, collision_objects=collision_objects, sockets=sockets):
                bpy.ops.object.mode_set (mode='OBJECT')
                bpy.ops.object.select_all (action='DESELECT')
                
                if len (objects) > 0:            
                    
                    ex_tex = scene.gyaz_export.export_textures
                    ex_tex_only = scene.gyaz_export.export_only_textures
                        
                    final_selected_objects = objects + collision_objects + sockets
                    
                    # set up LOD Groups and select LOD objects
                    # exporting skeletal mesh lod in the same file with lod0 results in 
                    # lods being exported in the wrong order in Unreal 4 (lod0, lod3, lod2, lod1)
                    # so skeletal mesh lods should be exported in separate files
                    # and imported one by one
                    if export_lods and asset_type == 'STATIC_MESHES':
                        
                        lod_info_keys = set (lod_info.keys ())
                        for obj in objects:
                            obj_name = obj.name
                            if obj_name in lod_info_keys:
                                lods = lod_info[obj_name]
                                if len(lods) > 0:
                                    if lod_setup_mode == "FBX_LOD_GROUP":
                                        empty = bpy.data.objects.new (name='LOD_' + obj_name, object_data=None)
                                        empty['fbx_type'] = 'LodGroup'
                                        scene.collection.objects.link (empty)
                                    
                                        for lod in lods + [obj]:
                                            lod.parent = empty
                                            lod.matrix_parent_inverse = empty.matrix_world.inverted()
                                            final_selected_objects.append (lod)
                                            final_selected_objects.append (empty)

                                    elif lod_setup_mode == "BY_NAME_WITH_0":
                                        for lod in lods + [obj]:
                                            final_selected_objects.append (lod)
                                        obj.name = obj.name + "_LOD0"

                                else:
                                    final_selected_objects.append (obj)
                    
                    for obj in scene.collection.objects:
                        obj.select_set (False)
                        
                    for obj in final_selected_objects:
                        obj.select_set (True)
                    
                    def ex ():
                        ctx = bpy.context.copy()
                        ctx['selected_objects'] = final_selected_objects
                        
                        bpy.ops.export_scene.fbx (
                            ctx, 
                            filepath=filepath, 
                            use_selection=use_selection,
                            use_active_collection=use_active_collection, 
                            embed_textures=embed_textures, 
                            global_scale=global_scale, 
                            apply_unit_scale=apply_unit_scale, 
                            apply_scale_options=apply_scale_options, 
                            axis_forward=axis_forward, 
                            axis_up=axis_up, 
                            object_types=object_types, 
                            use_space_transform=use_space_transform,
                            bake_space_transform=bake_space_transform, 
                            use_custom_props=use_custom_props, 
                            path_mode=path_mode, 
                            batch_mode=batch_mode, 
                            use_mesh_modifiers=use_mesh_modifiers, 
                            use_mesh_modifiers_render=use_mesh_modifiers_render, 
                            mesh_smooth_type=mesh_smooth_type, 
                            use_mesh_edges=use_mesh_edges, 
                            use_tspace=use_tspace, 
                            use_armature_deform_only=use_armature_deform_only, 
                            add_leaf_bones=add_leaf_bones, 
                            primary_bone_axis=primary_bone_axis, 
                            secondary_bone_axis=secondary_bone_axis, 
                            armature_nodetype=armature_nodetype, 
                            bake_anim=bake_anim, 
                            bake_anim_use_all_bones=bake_anim_use_all_bones,
                            bake_anim_use_nla_strips=bake_anim_use_nla_strips, 
                            bake_anim_use_all_actions=bake_anim_use_all_actions, 
                            bake_anim_force_startend_keying=bake_anim_force_startend_keying, 
                            bake_anim_step=bake_anim_step, 
                            bake_anim_simplify_factor=bake_anim_simplify_factor 
                        )               
                        report (self, 'Export has been successful.', 'INFO')     
                    
                    if asset_type == 'STATIC_MESHES' or asset_type == 'SKELETAL_MESHES':
                    
                        if ex_tex == False or ex_tex == True and ex_tex_only == False:
                            ex ()
                                    
                    else:
                        ex ()
                
                    # export_info    
                    if ex_tex and ex_tex_only:
                        ""
                    else:    
                        return texture_root if use_organizing_folder else filepath
    
            
            ###########################################################
            # EXPORT BY ASSET TYPE
            ###########################################################
            
            bpy.ops.object.mode_set (mode='OBJECT')
            
            pack_name = sn(pack_name)
            root_folder += '/'
            
            if asset_type == 'STATIC_MESHES':
                use_organizing_folder = owner.use_static_mesh_organizing_folder
            if asset_type == 'SKELETAL_MESHES' or asset_type == 'ANIMATIONS':
                use_organizing_folder = owner.use_skeletal_organizing_folder
            if asset_type == 'RIGID_ANIMATIONS':
                use_organizing_folder = owner.use_rigid_anim_organizing_folder
            
            if asset_type == 'STATIC_MESHES':
                
                # remove materials
                rename_materials (objects = meshes_to_export)
     
                if pack_objects:
                    
                    prefix = static_mesh_prefix if not pack_name.startswith(static_mesh_prefix) else ''
                    suffix = static_mesh_suffix if not pack_name.endswith(static_mesh_suffix) else ''
                    organizing_folder = pack_name + '/' if use_organizing_folder else ''
                    
                    filename = prefix + pack_name + suffix + format
                    folder_path = root_folder + organizing_folder + meshes_folder
                    filepath = folder_path + filename
                    os.makedirs (folder_path, exist_ok=True)
                    
                    texture_root = root_folder + organizing_folder[:-1]
                    
                    export_info = export_objects (filepath, objects = ori_sel_objs)   
                    texture_export_info = export_images (objects = ori_sel_objs, texture_root = texture_root, all_images = True)

                else:
                    
                    for obj in ori_sel_objs:
                            
                        prefix = static_mesh_prefix if not obj.name.startswith (static_mesh_prefix) else ''
                        suffix = static_mesh_suffix if not obj.name.endswith (static_mesh_suffix) else ''
                        organizing_folder = sn(obj.name) + '/' if use_organizing_folder else ''
                        
                        filename = prefix + sn(obj.name) + suffix + format
                        folder_path = root_folder + organizing_folder + meshes_folder
                        filepath = folder_path + filename
                        os.makedirs (folder_path, exist_ok=True)
                        
                        texture_root = root_folder + organizing_folder[:-1]
                        
                        export_info = export_objects (filepath, objects = [obj])
                        texture_export_info = export_images (objects = [obj], texture_root = texture_root, all_images = False)
                        
 
            elif asset_type == 'SKELETAL_MESHES':
                
                rename_materials (objects = meshes_to_export)
                
                if pack_objects:
                    
                    # export filter
                    make_active_only (final_rig)
                    if len (mesh_children) > 0:        
                    
                        prefix = skeletal_mesh_prefix if not pack_name.startswith (skeletal_mesh_prefix) else ''
                        suffix = skeletal_mesh_suffix if not pack_name.endswith (skeletal_mesh_suffix) else ''
                        organizing_folder = pack_name + '/' if use_organizing_folder else ''
                        
                        filename = prefix + pack_name + suffix + format
                        folder_path = root_folder + organizing_folder + meshes_folder
                        filepath = folder_path + filename
                        os.makedirs (folder_path, exist_ok=True)
                        
                        texture_root = root_folder + organizing_folder[:-1]
                        
                        export_info = export_objects (filepath, objects = [final_rig] + mesh_children)
                        texture_export_info = export_images (objects = mesh_children, texture_root = texture_root, all_images = True)                
                    
                else:
                    
                    organizing_folder = sn(ori_ao_name) + '/' if use_organizing_folder else ''
                    texture_root = root_folder + organizing_folder[:-1]
                    
                    if len (mesh_children) > 0:
                        for child in mesh_children:
                                
                            prefix = skeletal_mesh_prefix if not child.name.startswith (skeletal_mesh_prefix) else ''
                            suffix = skeletal_mesh_suffix if not child.name.endswith (skeletal_mesh_suffix) else ''
                            
                            filename = prefix + sn(child.name) + suffix + format
                            folder_path = root_folder + organizing_folder + meshes_folder
                            filepath = folder_path + filename
                            os.makedirs (folder_path, exist_ok=True)
                            
                            export_info = export_objects (filepath, objects = [final_rig, child])    
                            texture_export_info = export_images (objects = mesh_children, texture_root = texture_root, all_images = True)
                                          
                                    
            elif asset_type == 'ANIMATIONS':
                
                if action_export_mode == "SCENE":
                    
                    # fbx export settings
                    bake_anim = True

                    use_override_character_name = owner.use_anim_object_name_override
                    override_character_name = owner.anim_object_name_override
                    organizing_folder = sn(ori_ao_name) + '/' if use_organizing_folder else '' 

                    name = sn(ori_ao_name) if not use_override_character_name else override_character_name
                    separator = '_' if not name == '' else ''
                    folder_path = root_folder + organizing_folder + anims_folder
                    anim_name = sn(owner.global_anim_name)
                    filepath = folder_path + animation_prefix + name + separator + anim_name + animation_suffix + format
                    os.makedirs (folder_path, exist_ok=True) 
                    
                    set_animation_name (owner.global_anim_name)

                    export_objects (filepath, objects = [final_rig] + mesh_children)
                    export_info = filepath   

                # actions
                else:
                    actions_to_export = get_actions_to_export (object = ori_ao)
                    
                    # fbx export settings
                    bake_anim = True
                    
                    use_override_character_name = owner.use_anim_object_name_override
                    override_character_name = owner.anim_object_name_override
                    organizing_folder = sn(ori_ao_name) + '/' if use_organizing_folder else ''     
                    
                    if owner.rig_mode == "AS_IS" and owner.pack_actions:
                        
                        # fbx export settings   
                        bake_anim_use_all_actions = True

                        all_actions = bpy.data.actions
                        all_actions_list = [a for a in bpy.data.actions]
                        for action in all_actions_list:
                            if action not in actions_to_export:
                                all_actions.remove(action)

                        name = sn(ori_ao_name) if not use_override_character_name else override_character_name
                        separator = '_' if not name == '' else ''
                        folder_path = root_folder + organizing_folder + anims_folder
                        anim_name = sn(owner.global_anim_name)
                        filepath = folder_path + animation_prefix + name + separator + anim_name + animation_suffix + format
                        os.makedirs (folder_path, exist_ok=True) 

                        export_objects (filepath, objects = [final_rig] + mesh_children)
                        export_info = filepath   

                    else:

                        for action in actions_to_export:
                            
                            action_name = sn(action.name)
                            name = sn(ori_ao_name) if not use_override_character_name else override_character_name
                            separator = '_' if not name == '' else ''
                            folder_path = root_folder + organizing_folder + anims_folder
                            filepath = folder_path + animation_prefix + name + separator + action_name + animation_suffix + format
                            os.makedirs (folder_path, exist_ok=True)
                            
                            set_active_action (action)
                            adjust_scene_to_action_length (object = ori_ao)
                            set_animation_name (action_name)

                            export_objects (filepath, objects = [final_rig] + mesh_children)
                            export_info = filepath
                            

            elif asset_type == 'RIGID_ANIMATIONS':
                
                # fbx exporter setting
                bake_anim = True
                    
                # add animation data if not found
                for obj in ori_sel_objs:
                    if getattr (ori_ao, "animation_data") == None:
                        ori_ao.animation_data_create ()
                
                anim_name = sn(owner.rigid_anim_name)
                rename_materials (objects = ori_sel_objs)               
                if rigid_anim_cubes:
                    prefix_ = animation_prefix
                    suffix_ = animation_suffix
                else:
                    prefix_ = skeletal_mesh_prefix
                    suffix_ = skeletal_mesh_suffix
                                
                if pack_objects:
                    
                    prefix = prefix_ if not pack_name.startswith(prefix_) else ''                            
                    suffix = suffix_ if not pack_name.startswith(suffix_) else ''                            
                    organizing_folder = pack_name + '/' if use_organizing_folder else '/'
                    folder_path = root_folder + organizing_folder + anims_folder
                    filepath = folder_path + prefix + pack_name + '_' + anim_name + suffix + format
                    texture_root = root_folder + organizing_folder
                    
                    os.makedirs(folder_path, exist_ok=True) 
                    set_animation_name (anim_name)
                        
                    export_info = export_objects (filepath, objects = ori_sel_objs)
                    if not rigid_anim_cubes:
                        texture_export_info = export_images (objects = ori_sel_objs, texture_root = texture_root, all_images = True)
                     
                else:
                
                    for obj in ori_sel_objs:

                        prefix = prefix_ if not obj.name.startswith(prefix_) else ''
                        suffix = suffix_ if not obj.name.startswith(suffix_) else ''
                        organizing_folder = sn(obj.name) + '/' if use_organizing_folder else '/'
                        folder_path = root_folder + organizing_folder + anims_folder
                        filepath = folder_path + prefix + sn(obj.name) + '_' + anim_name + suffix + format 
                        
                        texture_root = root_folder + organizing_folder
                        
                        adjust_scene_to_action_length (object = obj)
                        set_animation_name (anim_name)
                        
                        os.makedirs(folder_path, exist_ok=True)
                        
                        export_info = export_objects (filepath, objects = [obj])
                        if not rigid_anim_cubes:
                            texture_export_info = export_images (objects = [obj], texture_root = texture_root, all_images = False)

      
            # make sure no images get deleted (because aftert the export, the blend file is reloaded)
            # it should be called before and after reload
            for image in bpy.data.images:
                if image.users == 0:
                    image.use_fake_user = True
            
            
            ###############################################################
            # REOPEN LAST SAVED .BLEND FILE
            # to restore the scene to the state before the exporting
            ###############################################################        
            
            if file_is_saved:
                show_debug_props = owner.show_debug_props
                
                if not show_debug_props:    
                    owner.dont_reload_scene = False
                if not owner.dont_reload_scene:        
                    bpy.ops.wm.open_mainfile (filepath=blend_path) 
                    
            # make sure no images get deleted (because aftert the export, the blend file is reloaded)
            # it should be called before and after reload
            for image in bpy.data.images:
                if image.users == 0:
                    image.use_fake_user = True
            
            
            if not owner.dont_reload_scene:
                # export_info: for opening last export in explorer
                info = None
                if 'export_info' in locals ():
                    if export_info is not None:
                        info = export_info
                    elif 'texture_export_info' in locals ():
                        if texture_export_info is not None:
                            info = texture_export_info[:-1]
                
                if info is not None:  
                    info = os.path.abspath ( bpy.path.abspath (info) )
                    bpy.context.scene.gyaz_export.path_to_last_export = info
                
                # the blend file is saved once before changing anything, everything is saved besides the path to last export
                # because it's saved after reloading the blend file
                # so save blend file again to save the path to last export, too
                bpy.ops.wm.save_as_mainfile (filepath=blend_path)  


        ###############################################################            
        # CONTENT CHECKS
        ###############################################################
        
        def content_checks (scene_objects, meshes_to_export):
                                    
            no_material_objects = []  
            no_uv_map_objects = []
            no_second_uv_map_objects = []
            bad_poly_objects = []
            ungrouped_vert_objects = []
            mirrored_uv_objects = []
            missing_textures = []
            missing_bones = []
            cant_create_extra_bones = []
            poly_warning = ""
            multiple_or_no_armature_mods = []
            shapes_and_mods = []
            
            image_info = {}
            
            def everything_fine():
                return len(no_material_objects)==0 and len(no_uv_map_objects)==0 and len(no_second_uv_map_objects)==0 and \
                    len(bad_poly_objects)==0 and len(ungrouped_vert_objects)==0 and len(mirrored_uv_objects)==0 and \
                    len(missing_textures)==0 and len(missing_bones)==0 and len(cant_create_extra_bones)==0 and \
                    poly_warning == "" and len(multiple_or_no_armature_mods)==0 and len(shapes_and_mods)==0
            
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
                        
                    if len (uv_maps) < 2:
                        no_second_uv_map_objects.append (obj.name)
                        
                    
                    # ngons and quads
                    if scene.gyaz_export.allow_quads:
                        max_face_vert_count = 4 
                        poly_warning = 'Ngons found: '
                    else:
                        max_face_vert_count = 3
                        poly_warning = 'Quads/ngons found: '
                    
                    bm = bmesh.new ()
                    bm.from_object (obj, bpy.context.evaluated_depsgraph_get(), cage=False, face_normals=False, vertex_normals=False)
                    faces = bm.faces
                    ngon_count = len ( [face for face in faces if len(face.verts)>max_face_vert_count] )
                    
                    if ngon_count > 0:
                        bad_poly_objects.append (obj.name)
                    
                    bm.free ()
                        
                    # ungrouped verts
                    if asset_type == 'SKELETAL_MESHES':
                        verts = obj.data.vertices
                        verts_wo_group = [vert.index for vert in verts if len (vert.groups) == 0]
                        if len (verts_wo_group) > 0:
                            ungrouped_vert_objects.append (obj.name)
                    
            
                    # mirrored uvs
                    if scene.gyaz_export.detect_mirrored_uvs:
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
                    if scene.gyaz_export.export_textures:
                        
                        images = set()
                        for material in materials:
                            if material is not None:
                                node_tree = material.node_tree
                                if node_tree is not None:
                                    images = images.union( gather_images_from_nodes(node_tree) )
                                                                                                                                                                                
                        image_info[obj.name] = images
            
            
            image_set = set ()
            for item in image_info:
                image_set = image_set.union (image_info[item])
            
            if asset_type != 'ANIMATIONS':
                if scene.gyaz_export.export_textures:           
                    
                    for image in image_set:
                        my_path = Path(os.path.abspath ( bpy.path.abspath (image.filepath_raw) ))
                        if not my_path.is_file() or image.source != 'FILE':
                            missing_textures.append (image.name)
                        
            if asset_type == 'SKELETAL_MESHES' or asset_type == 'ANIMATIONS':
                
                # delete empty items of export bones
                indices_to_remove = []
                for index, item in enumerate (scene.gyaz_export.export_bones):
                    if item.name == '':
                        indices_to_remove.append (index)
                for item in reversed (indices_to_remove):
                    scene.gyaz_export.export_bones.remove(item)
                
                # missing_bones
                rig_bone_names = [x.name for x in ori_ao.data.bones]
                export_bone_names = [x.name for x in scene.gyaz_export.export_bones]
                if not scene.gyaz_export.export_all_bones and owner.rig_mode != "AS_IS":
                    missing_bones = [item.name for item in scene.gyaz_export.export_bones if item.name not in rig_bone_names and item.name != '']
                if len (scene.gyaz_export.extra_bones) > 0:
                    for index, item in enumerate(scene.gyaz_export.extra_bones):
                        if is_str_blank(item.name):
                            cant_create_extra_bones.append (index)
                        if item.source not in rig_bone_names:
                            cant_create_extra_bones.append (index)
                        if item.name in export_bone_names:
                            cant_create_extra_bones.append (index)
            
            good_to_go = everything_fine()      
            if not good_to_go:
                
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
                
                if scene.gyaz_export.check_for_second_uv_map and not scene.gyaz_export.ignore_missing_second_uv_map:
                    if asset_type == 'STATIC_MESHES':
                        if len (no_second_uv_map_objects) > 0:
                            lines.append (l3)
                
                if asset_type != 'ANIMATIONS':
                    if len (bad_poly_objects) > 0:
                        lines.append (l4)
                        
                if asset_type == 'SKELETAL_MESHES':               
                    if len (ungrouped_vert_objects) > 0:
                        lines.append (l5)
                        
                if asset_type != 'ANIMATIONS':
                    if len (mirrored_uv_objects) > 0:
                        lines.append (l6)
                    
                if len (missing_textures) > 0:
                    lines.append (l7)
                    
                if len (missing_bones) > 0:
                    lines.append (l8)
                    
                if asset_type == 'SKELETAL_MESHES' or asset_type == 'ANIMATIONS':
                    if len (cant_create_extra_bones) > 0:
                        lines.append (l9)
                    if len (multiple_or_no_armature_mods) > 0:
                        lines.append (l10)
                
                if export_shape_keys:
                    if len (shapes_and_mods) > 0:
                        lines.append (l11)   
                
                good_to_go = len (lines) == 0
                
                # popup
                if not good_to_go:
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
                  
            return good_to_go, image_info, image_set, lod_info, lods
        
        
        def checks_plus_main ():
            
            safe, image_info, image_set, lod_info, lods = content_checks (scene_objects, meshes_to_export)
            
            if safe:
                
                export_sockets = owner.export_sockets
                
                main (asset_type, image_info, image_set, ori_ao, ori_ao_name, ori_sel_objs, mesh_children, meshes_to_export, root_folder, pack_objects, action_export_mode, pack_name, lod_info, lods, export_collision, collision_info, export_sockets)
        
            
        ###############################################################
        # PREVENT ERRORS
        ###############################################################
        
        if not bpy.context.blend_data.is_saved:
            report (self, 'Blend file has never been saved.', 'WARNING')
        else:
            
            good_to_go = True
            space = None
            for area in bpy.context.screen.areas:
                if area.type == 'VIEW_3D':
                    space = area.spaces[0]
            if space is not None:
                if space.local_view is not None:
                    report (self, "Leave local view.", "WARNING")
                    good_to_go = False
                    
            if good_to_go:
                ok = True
                if asset_type == 'STATIC_MESHES' and pack_objects:
                    if is_str_blank(pack_name):
                        ok = False
                        report (self, "Pack name is invalid.", "WARNING")
                    
                elif asset_type == 'RIGID_ANIMATIONS' and pack_objects:
                    if is_str_blank(pack_name):
                        ok = False
                        report (self, "Pack name is invalid.", "WARNING")
                        
                if ok:
                    
                    path_ok = True
                    if owner.export_folder_mode == 'PATH':
                        if root_folder.startswith ('//'):
                            report (self, "Use an absolute path for export folder instead of a relative path.", "WARNING")
                            path_ok = False
                        elif not os.path.isdir (root_folder):
                            report (self, "Export path doesn't exist.", "WARNING")
                            path_ok = False

                        
                    if path_ok:
                        
                        if asset_type == 'ANIMATIONS':
                            actions_set_for_export = scene.gyaz_export.actions
                            if ori_ao.type == 'ARMATURE':   
                                if owner.use_anim_object_name_override and is_str_blank(owner.anim_object_name_override):
                                    report (self, 'Object name override is invalid.', 'WARNING')
                                
                                if action_export_mode == 'ACTIVE': 
                                    if getattr (ori_ao, "animation_data") is not None:
                                        if ori_ao.animation_data.action is not None:
                                            checks_plus_main ()
                                        else:
                                            report (self, 'Active object has no action assigned to it.', 'WARNING')
                                    else:
                                        report (self, 'Active object has no animation data.', 'WARNING')

                                        
                                elif action_export_mode == 'ALL':
                                    if len (bpy.data.actions) > 0:
                                        checks_plus_main ()
                                    else:
                                        report (self, 'No actions found in this .blend file.', 'WARNING')

                                        
                                elif action_export_mode == 'BY_NAME':
                                    items_ok = []
                                    for item in actions_set_for_export:
                                        if item.name != '':
                                            items_ok.append (True)
                                            
                                    if len (actions_set_for_export) > 0:
                                        if len (actions_set_for_export) == len (items_ok):
                                            checks_plus_main ()
                                        else:
                                            report (self, 'One or more actions set to be exported are not found', 'WARNING') 
                                    else:
                                        report (self, 'No actions are set to be exported.', 'WARNING')

                                elif action_export_mode == "SCENE":
                                    if getattr (ori_ao, "animation_data") is not None:
                                        if is_str_blank(owner.global_anim_name):
                                            report (self, 'Animation name is invalid.', 'WARNING')
                                        else:
                                            checks_plus_main ()
                                    else:
                                        report (self, 'Active object has no animation data.', 'WARNING')
                                        
                            else:
                                report (self, 'Active object is not an armature.', 'WARNING')

                                    
                        elif asset_type == 'SKELETAL_MESHES':
                            if ori_ao.type == 'ARMATURE':
                                if len (mesh_children) > 0:
                                    if scene.gyaz_export.root_mode == 'BONE':    
                                        if ori_ao.data.bones.get (root_bone_name) is not None:
                                            checks_plus_main ()
                                            
                                        else:
                                            report (self, 'Root bone, called "' + root_bone_name + '", not found. Set object as root.', 'WARNING')
                                            
                                    else:
                                        checks_plus_main ()
                                    
                                else:
                                    report (self, "Armature has no mesh children.", 'WARNING')
                                    
                            else:
                                report (self, "Active object is not an armature.", 'WARNING')
                                
                                
                        elif asset_type == 'STATIC_MESHES':      
                            if len (ori_sel_objs) > 0:
                                checks_plus_main ()
                            else:
                                report (self, 'No objects set for export.', 'WARNING')
                        
                        elif asset_type == 'RIGID_ANIMATIONS':
                            if len (ori_sel_objs) > 0:
                                if is_str_blank(owner.rigid_anim_name):
                                    report (self, 'Animation name is invalid.', 'WARNING')
                                else:
                                    checks_plus_main ()
                            else:
                                report (self, 'No objects set for export.', 'WARNING')
        
        
        return {'FINISHED'}
    
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