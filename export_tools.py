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

import bpy, os, bmesh, subprocess
from bpy.types import Panel, Operator, AddonPreferences, PropertyGroup, UIList, Scene, Object, Mesh, Menu
from bpy.props import *
from mathutils import Vector, Matrix
import numpy as np
from math import radians
from pathlib import Path

# BEFORE OR AFTER 2.8
_2_8 = True if bpy.app.version >= (2, 80, 0) else False

def get_uv_maps (mesh):
    if _2_8:
        return mesh.uv_layers
    else:
        return mesh.uv_textures
            
# popup
def popup (lines, icon, title):
    def draw(self, context):
        for line in lines:
            self.layout.label(line)
    bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)
    
def list_to_visual_list (list):
    line = ''
    for index, item in enumerate(list):
        if index > 0:
            line += ', '
        line += str(item)
    return line

# report
def report (self, item, error_or_info):
    self.report({error_or_info}, item)
    
def make_active_only (obj):
    bpy.ops.object.mode_set (mode='OBJECT')
    bpy.ops.object.select_all (action='DESELECT')
    obj.select = True
    bpy.context.scene.objects.active = obj 
    
def make_active (obj):
    bpy.context.scene.objects.active = obj    
    
def select_objects (objs):
    for obj in objs:
        obj.select = True
        
def select_object (obj):
    obj.select = True
    
def deselect_object (obj):
    obj.select = False

# safe name
def sn (line):
    for c in '/\:*?"<>|.,= '+"'":
        line = line.replace (c, '_')
    return (line)

# detect mirrored uvs
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

# rescale mesh
gyaz_stamp = 'gyaz_exporter_rescaled_me'

untransformed_matrix = Matrix (([1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1])) 

def rescale_meshes (objects):
    "disabled because it would cause problems with modifiers"
#    for obj in objects:
#        if obj.type == 'MESH':
#            
#            if gyaz_stamp not in obj.data:
#                verts = obj.data.vertices

#                verts_co = [0, 0, 0] * len(verts)    
#                verts.foreach_get ('co', verts_co)

#                array = np.array (verts_co)
#                array *= 100

#                verts.foreach_set ('co', array)
#                obj.data[gyaz_stamp] = 1
#            
#            if gyaz_stamp not in obj:
#                obj.delta_scale *= 0.01
#                obj[gyaz_stamp] = 1
                
                
def get_active_action (obj):
    if obj.animation_data != None:
        action = obj.animation_data.action
    else:
        action = None
    return action


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


def apply_transforms (obj, co):
    # get vert coords in world space
    m = np.array (obj.matrix_world)    
    mat = m[:3, :3].T # rotates backwards without T
    loc = m[:3, 3]
    return co @ mat + loc

def revert_transforms (obj, co):
    # set world coords on object, run before setting coords to deal with object transforms if using apply_transforms()
    m = np.linalg.inv (obj.matrix_world)    
    mat = m[:3, :3].T # rotates backwards without T
    loc = m[:3, 3]
    return co @ mat + loc
    

# object props
class PG_GYAZ_Export_ObjectProps (PropertyGroup):    
    export = BoolProperty (name='Export Mesh', default=True)


# extra bone            
class PG_GYAZ_Export_ExtraBoneItem (PropertyGroup):
    name = StringProperty (name='', description="Name of new bone")
    source = StringProperty (name='', description="Create new bone by duplicating this bone")
    parent = StringProperty (name='', description="Parent new bone to this bone")
    
#constraint_to_source = BoolProperty (name='', default=False, description='Constraint to source bone')               
#rename_vert_group = BoolProperty (name='', default=False, description='Rename vertex groups')               

class UL_GYAZ_ExtraBones (UIList):
    def draw_item (self, context, layout, data, set, icon, active_data, active_propname, index):
        icon = 'BONE_DATA' if bpy.context.object.data.bones.get (set.source) != None else 'ERROR'
        row = layout.row (align=True)
        row.prop (set, "name", icon=icon, emboss=False)
        if bpy.context.scene.gyaz_export.extra_bones_long_rows:
            row.separator ()
            row.prop (set, "parent", text='', icon='NODETREE', emboss=False)
            row.operator (Op_GYAZ_Export_SetParentAsActiveBone.bl_idname, text='', icon='EYEDROPPER', emboss=False).ui_index = index
            row.separator ()
            row.prop_search (set, "source", bpy.context.active_object.data, "bones", icon='GROUP_BONE')
            row.operator (Op_GYAZ_Export_SetSourceAsActiveBone.bl_idname, text='', icon='EYEDROPPER').ui_index = index


#row = layout.row (align=True)        
#icon = 'CONSTRAINT' if set.constraint_to_source else 'BLANK1'
#row.prop (set, "constraint_to_source", icon=icon)
#icon = 'GROUP_VERTEX' if set.rename_vert_group else 'BLANK1'
#row.prop (set, "rename_vert_group", icon=icon)

# export bone        
class PG_GYAZ_Export_ExportBoneItem (PropertyGroup):
    name = StringProperty (name='', description="Name of bone to export")
    
class UL_GYAZ_ExportBones (UIList):
    def draw_item (self, context, layout, data, set, icon, active_data, active_propname, index):
        row = layout.row (align=True)
        row.prop_search (set, "name", bpy.context.object.data, "bones")
        row.operator (Op_GYAZ_Export_SetNameAsActiveBone.bl_idname, text='', icon='EYEDROPPER').ui_index = index
        row.operator (Op_GYAZ_Export_RemoveItemFromExportBones.bl_idname, text='', icon='ZOOMOUT').ui_index = index                  

# preset names
prefs = bpy.context.user_preferences.addons[__package__].preferences

# actions to export
class PG_GYAZ_export_ExportActions(PropertyGroup):
    name = StringProperty (description='Name of action to import', default='')
    
class UL_GYAZ_ExportActions (UIList):
    def draw_item (self, context, layout, data, set, icon, active_data, active_propname, index):
        row = layout.row (align=True)
        row.prop_search (set, "name", bpy.data, "actions", text='')
        row.operator (Op_GYAZ_Export_SetActiveActionToExport.bl_idname, text='', icon='EYEDROPPER').ui_index=index           
        row.operator (Op_GYAZ_Export_RemoveItemFromActions.bl_idname, text='', icon='ZOOMOUT').ui_index=index           

# pointer property 
class PG_GYAZ_ExportProps (PropertyGroup):
    
    def load_active_preset (self, context):
        
        scene = bpy.context.scene
        
        scene_extra_bones = getattr (scene.gyaz_export, "extra_bones")
        scene_export_bones = getattr (scene.gyaz_export, "export_bones")
        scene_active_preset = getattr (scene.gyaz_export, "active_preset")
        
        preset = None
        for item in prefs.bone_presets:
            if item.preset_name == scene_active_preset:
                preset = item
        
        if preset != None:
            
            preset_extra_bones = getattr (preset, "extra_bones")
            preset_export_bones = getattr (preset, "export_bones")
            
            scene_extra_bones.clear ()
            scene_export_bones.clear ()
            
            for preset_item in preset_extra_bones:
                scene_item = scene_extra_bones.add ()
                scene_item.name = preset_item.name
                scene_item.source = preset_item.source
                scene_item.parent = preset_item.parent
                
            for preset_item in preset_export_bones:
                scene_item = scene_export_bones.add ()
                scene_item.name = preset_item.name
            
            setattr (scene.gyaz_export, 'root_mode', preset.root_mode)
            setattr (scene.gyaz_export, 'export_all_bones', preset.export_all_bones)
            setattr (scene.gyaz_export, 'constraint_extra_bones', preset.constraint_extra_bones)
            setattr (scene.gyaz_export, 'rename_vert_groups_to_extra_bones', preset.rename_vert_groups_to_extra_bones)
            
     
    def get_preset_names (self, context):
        return [(preset.preset_name, preset.preset_name, "") for preset in prefs.bone_presets]
         
    active_preset = EnumProperty (name = 'Active Preset', items = get_preset_names, default = None, update=load_active_preset)    
    
    root_mode = EnumProperty (name='Root', items=(('BONE', 'Bone: root', ''), ('OBJECT', 'Object', '')), default='OBJECT', description='Root Mode. Bone: top of hierarchy is the bone called "root", Object: top of hierarchy is the object (renamed as "root") and the root bone, if found, is removed.')
    
    extra_bones = CollectionProperty (type=PG_GYAZ_Export_ExtraBoneItem)
    
    constraint_extra_bones = BoolProperty (name='Constraint To Source', default=False)
    rename_vert_groups_to_extra_bones = BoolProperty (name='Rename Vert Groups', default=False)
    extra_bones_long_rows = BoolProperty (name='Long Rows', default=False)
    
    export_bones = CollectionProperty (type=PG_GYAZ_Export_ExportBoneItem)
    extra_bones_active_index = IntProperty (default=0)
    export_all_bones = BoolProperty (name='All Bones', default=True)
    export_bones_active_index = IntProperty (default=0)

    action_export_mode = EnumProperty (name='Export Actions',
        items=(
            ('ACTIVE', 'ACTIVE', ""),
            ('ALL', 'ALL', ""),
            ('BY_NAME', 'BY NAME', "")
            ),
        default='ACTIVE')
    
    actions = CollectionProperty (type=PG_GYAZ_export_ExportActions)
    actions_active_index = IntProperty (default=0)

    skeletal_mesh_limit_bone_influences = EnumProperty (name='max bone inflences', description="Limit bone influences by vertex",
        items=(
            ('1', '1 weight/vertex', ''),
            ('2', '2 weights/vertex', ''),
            ('4', '4 weights/vertex', ''),
            ('8', '8 weights/vertex', ''),
            ('unlimited', 'unlimited', '')
            ),
        default=prefs.skeletal_mesh_limit_bone_influences)
    
    use_scene_start_end = BoolProperty (name='Use Scene Start End', default=False, description="If False, frame range will be set according to first and last keyframes of the action")

    export_folder_mode = EnumProperty (
        items=(
            ('RELATIVE_FOLDER', 'RELATIVE', ''),
            ('PATH', 'PATH', '')
            ),
        default='PATH', description='Relative: export next to the blend file, Path: select a destination')
    
    def absolute_path__export_folder (self, context):
        scene = bpy.context.scene
        prop = getattr (bpy.context.scene.gyaz_export, "export_folder")
        new_path = os.path.abspath ( bpy.path.abspath (prop) )
        if prop.startswith ('//'):
            bpy.context.scene.gyaz_export.export_folder = new_path
    
    export_folder = StringProperty (default='', subtype='DIR_PATH', update=absolute_path__export_folder)
    
    relative_folder_name = StringProperty (default='assets', name='Folder', description="Name of relative folder")    
    
    use_anim_object_name_override = BoolProperty (name='Override Object Name', default=False, description="Override the object's name in exported skeletal animations: AnimationPrefix_ObjectName_ActionName")
    
    anim_object_name_override = StringProperty (name='', default='')
    
    static_mesh_pack_name = StringProperty (default='', name='', description="Pack name")
    skeletal_mesh_pack_name = StringProperty (default='', name='', description="Pack name")
    
    rigid_anim_pack_name = StringProperty (default='', name='', description="Pack's name")
    
    rigid_anim_name = StringProperty (default='', name='', description="Name of the animation")
    
    rigid_anim_cubes = BoolProperty (name='Export Cubes', default=False, description="Replace mesh objects' data with a simple cube")
    
    exporter = EnumProperty (name='Exporter',
        items=(
            ('FBX', 'Filmbox - .fbx', ''),
            ),
        default='FBX')
        
    rigid_asset_type = EnumProperty (name='Asset Type',
        items=(
            ('STATIC_MESHES', 'STATIC MESHES', "", 'GROUP', 0),
            ('RIGID_ANIMATIONS', 'RIGID ANIMATIONS', "", 'SCRIPTWIN', 3)
            ),
        default='STATIC_MESHES')
        
    skeletal_asset_type = EnumProperty (name='Asset Type',
        items=(
            ('SKELETAL_MESHES', 'SKELETAL MESHES', "", 'OUTLINER_DATA_ARMATURE', 1),
            ('ANIMATIONS', 'SKELETAL ANIMATIONS', "", 'POSE_HLT', 2)
            ),
        default='SKELETAL_MESHES')

    static_mesh_pack_objects = BoolProperty (name='Pack Objects', default=False, description='Whether to pack all objects into one file or export them as separate files. If true, sockets will not be exported')
    skeletal_mesh_pack_objects = BoolProperty (name='Pack Objects', default=False, description='Whether to pack all objects into one file or export them as separate files')
    rigid_anim_pack_objects = BoolProperty (name='Pack Objects', default=False, description="Whether to pack all objects into one file or export them as separate files. If checked, 'Use Scene Start End' is forced, 'Export Cubes' is not an option")
        
    use_static_mesh_organizing_folder = BoolProperty (name='Organizing Folder', default=False, description="Export objects into separate folders with the object's name. If 'Pack Objects' is true, export objects into a folder with the pack's name")
    use_rigid_anim_organizing_folder = BoolProperty (name='Organizing Folder', default=False, description="Export objects into separate folders with the object's name. If 'Pack Objects' is true, export objects into a folder with the pack's name")
    use_skeletal_organizing_folder = BoolProperty (name='Organizing Folder', default=False, description="Add an extra folder with the armature's name")

    static_mesh_clear_transforms = BoolProperty (default=True, name='Clear Transforms', description="Clear object transforms")
    skeletal_clear_transforms = BoolProperty (default=True, name='Clear Transforms', description="Clear object transforms. Armature transformation will always be cleared if root motion is calculated from a bone")
   
    texture_format_mode = EnumProperty(
        name='Texture Format',
        items=(
            ('KEEP_IF_ANY', "Keep Format", ""),
            ('ALWAYS_OVERRIDE', "Override Format", "")
            ),
        default=prefs.texture_format_mode)
        
    texture_format_override = EnumProperty(
        name='Override',
        items=(
            ('TARGA', 'TGA', ''),
            ('PNG', 'PNG', ''),
            ('TIFF', 'TIF', '')
            ),
        default=prefs.texture_format_override)
   
    texture_compression = FloatProperty(name='Texture Compression', default=prefs.texture_compression, min=0, max=1)
        
    export_textures = BoolProperty (default=False, name='Textures')
    
    export_only_textures = BoolProperty (default=False, name='Textures Only', description='Export only textures, no meshes')
    
    export_collision = BoolProperty (default=True, name='Collision', description='Prefixes: UBX (box), USP (sphere), UCP (capsule), UCX (convex). Example: Object --> UBX_Object, UBX_Object.001. Collision (mesh) objects are gathered automatically and should not be selected')
    
    export_sockets = BoolProperty (default=True, name='Sockets', description='Sockets need to be parented to the object and only work if a file only contains one object. Prefix: SOCKET_, Example: Object --> SOCKET_anything. Socket (armature) objects are gathered automatically and should not be selected. Scale is ignored')
    
    export_lods = BoolProperty (default=True, name='LODs', description='Suffix: Obj --> Obj_LOD1, Obj_LOD2 (LOD0 should not have a suffix). LODs are gathered automatically and should not be selected')
    
    ignore_missing_second_uv_map = BoolProperty (default=False, name='Ignore 2nd UV Check')
    
    show_options = BoolProperty (name='Show Options', default=True)
    
    use_prefixes = BoolProperty (name='Add Prefixes', default=prefs.use_prefixes, description="Add prefixes to asset names. Set up prefixes in User Preferences>Addons") 
    remove_boneless_vert_weights = BoolProperty (name='Clean Vert Groups', default=prefs.remove_boneless_vert_weights, description="Remove vertex groups without a bone with the same name")
    add_end_bones = BoolProperty (name='Add End Bones', default=prefs.add_end_bones, description='Add a bone to the end of bone chains')
    check_for_second_uv_map = BoolProperty (name='Check for 2nd UV Map', default=prefs.check_for_second_uv_map, description='Check for 2nd uv map when exporting static meshes')
    detect_mirrored_uvs = BoolProperty (name='Detect Mirrored UVs', default=prefs.detect_mirrored_uvs, description='Look for mirrored uvs that cause incorrect shading. Slow with high-poly meshes with multiple uv maps')
    
    mesh_smoothing = EnumProperty (name='Smoothing',
        items=(
            ('OFF', 'Normals Only', ''),
            ('FACE', 'Face', ''),
            ('EDGE', 'Edge', '')
            ),
        default=prefs.mesh_smoothing,
        description='Mesh smoothing data')
        
    allow_quads = BoolProperty (name='Allow Quads', default=prefs.allow_quads, description='Allow quads. Ngons are never allowed')

    filter_string = StringProperty (default='')
    
    filter_type = EnumProperty (items=(('START', 'START', ''), ('IN', 'IN', ''), ('END', 'END', '')), default='IN')
    
    static_mesh_apply_mods = BoolProperty (name='Apply Modifiers', default=False)
    skeletal_mesh_apply_mods = BoolProperty (name='Apply Modifiers', default=False, description='Shape keys will NOT be exported')
    rigid_anim_apply_mods = BoolProperty (name='Apply Modifiers', default=False, description='Shape keys will NOT be exported')
    
    static_mesh_vcolors = BoolProperty (name='Vertex Colors', default=True)
    skeletal_mesh_vcolors = BoolProperty (name='Vertex Colors', default=True)
    rigid_anim_vcolors = BoolProperty (name='Vertex Colors', default=True)
    
    skeletal_shapes = BoolProperty (name='Shape Keys', default=True)
    rigid_anim_shapes = BoolProperty (name='Shape Keys', default=True)
    
    path_to_last_export = StringProperty (name='path to last export', default='')
    
    # debug
    show_debug_props = BoolProperty (name='Developer', default=False, description="Show properties for debugging")
    
    dont_reload_scene = BoolProperty (name="Don't Reload Scene", default=False, description="Debugging, whether not to reload the scene saved before the export")
    
    
class Op_GYAZ_Export_SelectFileInWindowsFileExplorer (bpy.types.Operator):
       
    bl_idname = "object.gyaz_export_select_file_in_explorer"  
    bl_label = "GYAZ Export: Select File in Explorer"
    bl_description = "Select File in file explorer"
    
    path = StringProperty (default='', options={'SKIP_SAVE'})
    
    # operator function
    def execute(self, context):  
        path = os.path.abspath ( bpy.path.abspath (self.path) )    
        subprocess.Popen(r'explorer /select,'+path)
         
        return {'FINISHED'}

    
class Op_GYAZ_Export_OpenFolderInWindowsFileExplorer (bpy.types.Operator):
       
    bl_idname = "object.gyaz_export_open_folder_in_explorer"  
    bl_label = "GYAZ Export: Open Folder in Explorer"
    bl_description = "Open folder in file explorer"
    
    path = StringProperty (default='', options={'SKIP_SAVE'})
    
    # operator function
    def execute(self, context):
        path = os.path.abspath ( bpy.path.abspath (self.path) )  
        subprocess.Popen ('explorer "'+path+'"')
          
        return {'FINISHED'}
    
    
class Op_GYAZ_Export_PathInfo (bpy.types.Operator):
       
    bl_idname = "object.gyaz_export_path_info"  
    bl_label = "GYAZ Export: Path Info"
    bl_description = "Path info"
    
    path = StringProperty (default='', options={'SKIP_SAVE'})
    title = StringProperty (default='', options={'SKIP_SAVE'})
    
    # operator function
    def execute(self, context):
        path = os.path.abspath ( bpy.path.abspath (self.path) )
        popup (lines=[path], icon='INFO', title=self.title)
          
        return {'FINISHED'}
    

class Op_GYAZ_Export_SavePreset (bpy.types.Operator):
    
    bl_idname = "object.gyaz_export_save_preset"  
    bl_label = "GYAZ Export: Save Preset"
    bl_description = "Save preset"
    
    ui_name = StringProperty (name = 'name', default = '')
    
    # popup with properties
    def invoke(self, context, event):
        wm = bpy.context.window_manager
        return wm.invoke_props_dialog(self)
    
    # operator function
    def execute(self, context):
        preset_name = self.ui_name        
        scene = bpy.context.scene
        
        preset_name_no_whitespace = preset_name.replace (" ", "")
        if preset_name_no_whitespace == '-' or preset_name_no_whitespace == '':
            report (self, "Invalid name.", 'WARNING')
        else: 
            
            # check for existing preset with the same name
            presets = prefs.bone_presets
            preset_names = [preset.preset_name for preset in presets]
            if preset_name in preset_names:
                preset = presets[preset_name.index (preset_name)]
            else:
                # add preset
                preset = presets.add ()                
        
            scene_extra_bones = getattr (scene.gyaz_export, "extra_bones")
            scene_export_bones = getattr (scene.gyaz_export, "export_bones")
            scene_active_preset = getattr (scene.gyaz_export, "active_preset")
            
            preset_extra_bones = getattr (preset, "extra_bones")
            preset_export_bones = getattr (preset, "export_bones")
            
            preset_extra_bones.clear ()
            preset_export_bones.clear ()
            
            for scene_item in scene_extra_bones:
                preset_item = preset_extra_bones.add ()
                preset_item.name = scene_item.name
                preset_item.source = scene_item.source
                preset_item.parent = scene_item.parent
                
            for scene_item in scene_export_bones:
                preset_item = preset_export_bones.add ()
                preset_item.name = scene_item.name
            
            setattr (preset, 'preset_name', preset_name)
            
            setattr (preset, 'root_mode', scene.gyaz_export.root_mode)
            setattr (preset, 'export_all_bones', scene.gyaz_export.export_all_bones)
            setattr (preset, 'constraint_extra_bones', scene.gyaz_export.constraint_extra_bones)
            setattr (preset, 'rename_vert_groups_to_extra_bones', scene.gyaz_export.rename_vert_groups_to_extra_bones)
            
            scene.gyaz_export.active_preset = preset.preset_name
            
            # save user preferences
            bpy.context.area.type = 'USER_PREFERENCES'
            bpy.ops.wm.save_userpref()
            bpy.context.area.type = 'VIEW_3D'
            
        return {'FINISHED'}
    
    
class Op_GYAZ_Export_RemovePreset (bpy.types.Operator):
       
    bl_idname = "object.gyaz_export_remove_preset"  
    bl_label = "GYAZ Export: Remove Preset"
    bl_description = "Remove preset"
    
    # operator function
    def execute(self, context):     
        scene = bpy.context.scene
        
        scene_active_preset = getattr (scene.gyaz_export, "active_preset")
        presets = prefs.bone_presets
        preset_len = len (presets)
        
        if preset_len > 0:
            preset_names = [preset.preset_name for preset in presets]
            if scene_active_preset in preset_names:
                index = preset_names.index (scene_active_preset)
                presets.remove (index)
                if preset_len > 1:
                    preset_names = [preset.preset_name for preset in presets]
                    scene.gyaz_export.active_preset = preset_names[0]
                else:
                    scene.gyaz_export.property_unset ("extra_bones")
                    scene.gyaz_export.property_unset ("export_bones")
                    scene.gyaz_export.property_unset ("export_all_bones")
                    scene.gyaz_export.property_unset ("root_mode")
                    scene.gyaz_export.property_unset ("constraint_extra_bones")
                    scene.gyaz_export.property_unset ("rename_vert_groups_to_extra_bones")
        
        # save user preferences
        bpy.context.area.type = 'USER_PREFERENCES'
        bpy.ops.wm.save_userpref()
        bpy.context.area.type = 'VIEW_3D'      
            
        return {'FINISHED'}

    
class Op_GYAZ_Export_Functions (bpy.types.Operator):
       
    bl_idname = "object.gyaz_export_functions"  
    bl_label = "GYAZ Export: Functions"
    bl_description = ""
    
    ui_mode = EnumProperty(
        name = 'mode',
        items = (
            ('ADD_TO_EXTRA_BONES', '', ''),
            ('REMOVE_ALL_FROM_EXTRA_BONES', '', ''),
            ('ADD_TO_EXPORT_BONES', '', ''),
            ('REMOVE_ALL_FROM_EXPORT_BONES', '', ''),
            ('ADD_TO_EXPORT_ACTIONS', '', ''),
            ('REMOVE_ALL_FROM_EXPORT_ACTIONS', '', '')
            ),
        default = "ADD_TO_EXTRA_BONES")
    
    # operator function
    def execute(self, context):
        mode = self.ui_mode        
        scene = bpy.context.scene
        
        scene_extra_bones = getattr (scene.gyaz_export, "extra_bones")
        scene_export_bones = getattr (scene.gyaz_export, "export_bones")
            
        if mode == 'ADD_TO_EXTRA_BONES':
            item = scene_extra_bones.add ()
            item.name = ''
            item.marge_to = ''
            scene.gyaz_export.extra_bones_active_index = len (scene_extra_bones) - 1
        elif mode == 'REMOVE_ALL_FROM_EXTRA_BONES':
            scene_extra_bones.clear ()    
            scene.gyaz_export.extra_bones_active_index = -1
            
        elif mode == 'ADD_TO_EXPORT_BONES':
            item = scene_export_bones.add ()
            item.name = ''
            item.marge_to = ''
        elif mode == 'REMOVE_ALL_FROM_EXPORT_BONES':
            scene_export_bones.clear ()
                                  
                
        elif mode == 'ADD_TO_EXPORT_ACTIONS':
            item = scene.gyaz_export.actions.add ()
            item.name = ''
            item.marge_to = ''
        elif mode == 'REMOVE_ALL_FROM_EXPORT_ACTIONS':
            scene.gyaz_export.actions.clear ()
            
        return {'FINISHED'}


class Op_GYAZ_Export_ReadSelectedPoseBones (bpy.types.Operator):
       
    bl_idname = "object.gyaz_export_read_selected_pose_bones"  
    bl_label = "GYAZ Export: Read Selected Pose Bones"
    bl_description = "Read selected pose bones"    
    
    mode = EnumProperty (items=(('EXPORT_BONES', 'Export Bones', ''), ('EXTRA_BONES', 'Extra Bones', '')), default='EXPORT_BONES')
    
    def execute(self, context):
        
        scene = bpy.context.scene
        rig = bpy.context.object
        mode = self.mode
        
        if mode == 'EXPORT_BONES':
            collection = getattr (scene.gyaz_export, "export_bones")
            prop = 'name'
        elif mode == 'EXTRA_BONES':
            collection = getattr (scene.gyaz_export, "extra_bones")
            prop = 'source'
        
        if bpy.context.mode == 'POSE':
            selected_visible_bones = []
            bones = rig.data.bones

            selected_visible_bones = [pbone.name for pbone in bpy.context.selected_pose_bones]  
            names_already_in_collection = set ( getattr (item, prop) for item in collection )
      
            for name in selected_visible_bones:
                if name not in names_already_in_collection:
                    item = collection.add ()
                    setattr (item, prop, name)
                    
        return {'FINISHED'}
    

class Op_GYAZ_Export_MarkAllSelectedForExport (bpy.types.Operator):
       
    bl_idname = "object.gyaz_export_mark_all_selected_for_export"  
    bl_label = "GYAZ Export: Mark All Selected For Export"
    bl_description = "All selected objects for export"
    
    # operator function
    def execute(self, context):
        armature = bpy.context.active_object.type == 'ARMATURE'
        scene = bpy.context.scene
        selected_objects = bpy.context.selected_objects
        active_object = bpy.context.active_object
        
        if armature:
            for child in active_object.children:
                child.gyaz_export.export = True   
        else:
            for obj in selected_objects:
                obj.gyaz_export.export = True
            
        return {'FINISHED'}
 
    
class Op_GYAZ_Export_MarkAllSelectedNotForExport (bpy.types.Operator):
       
    bl_idname = "object.gyaz_export_mark_all_selected_not_for_export"  
    bl_label = "GYAZ Export: Mark All Selected Not For Export"
    bl_description = "All selected objects not for export"
    
    # operator function
    def execute(self, context):
        armature = bpy.context.active_object.type == 'ARMATURE'    
        scene = bpy.context.scene
        selected_objects = bpy.context.selected_objects
        active_object = bpy.context.active_object
                
        if not armature:
            for obj in selected_objects:
                obj.gyaz_export.export = False
        elif armature:
            for child in active_object.children:
                child.gyaz_export.export = False    
                
        return {'FINISHED'}
    
    
class Op_GYAZ_Export_MarkAllForExport (bpy.types.Operator):
       
    bl_idname = "object.gyaz_export_mark_all_for_export"  
    bl_label = "GYAZ Export: Mark All Objects For Export"
    bl_description = "All scene objects for export"
    
    # operator function
    def execute(self, context):   
        scene = bpy.context.scene

        for obj in scene.objects:
            obj.gyaz_export.export = True             
            
        return {'FINISHED'}
    
    
class Op_GYAZ_Export_MarkAllNotForExport (bpy.types.Operator):
       
    bl_idname = "object.gyaz_export_mark_all_not_for_export"  
    bl_label = "GYAZ Export: Mark All Not For Export"
    bl_description = "All scene objects not for export"
    
    # operator function
    def execute(self, context):   
        scene = bpy.context.scene

        for obj in scene.objects:
            obj.gyaz_export.export = False            
            
        return {'FINISHED'}


class Op_GYAZ_Export_RemoveItemFromExtraBones (bpy.types.Operator):
       
    bl_idname = "object.gyaz_export_remove_item_from_extra_bones"  
    bl_label = "GYAZ Export: Remove Item From Extra Bones"
    bl_description = "Remove item"
    
    # operator function
    def execute(self, context):
        scene = bpy.context.scene
        index = scene.gyaz_export.extra_bones_active_index
        
        scene.gyaz_export.extra_bones.remove (index)
        if len (scene.gyaz_export.extra_bones) < index + 1:
            scene.gyaz_export.extra_bones_active_index -= 1
            
        return {'FINISHED'}


class Op_GYAZ_Export_RemoveItemFromExportBones (bpy.types.Operator):
       
    bl_idname = "object.gyaz_export_remove_item_from_export_bones"  
    bl_label = "GYAZ Export: Remove Item From Export Bones"
    bl_description = "Remove item"
    
    ui_index = IntProperty (name='', default=0)
    
    # operator function
    def execute(self, context):
        index = self.ui_index        
        scene = bpy.context.scene
        
        scene.gyaz_export.export_bones.remove (index)
            
        return {'FINISHED'}
    

class Op_GYAZ_Export_RemoveItemFromActions (bpy.types.Operator):
       
    bl_idname = "object.gyaz_export_remove_item_from_actions"  
    bl_label = "GYAZ Export: Remove Item From Action Names"
    bl_description = "Remove item"
    
    ui_index = IntProperty (name='', default=0)
    
    # operator function
    def execute(self, context):
        index = self.ui_index        
        scene = bpy.context.scene
        
        scene.gyaz_export.actions.remove (index)
            
        return {'FINISHED'}


class Op_GYAZ_Export_SetSourceAsActiveBone (bpy.types.Operator):
       
    bl_idname = "object.gyaz_export_set_source_as_active_bone"  
    bl_label = "GYAZ Export: Set Source As Active Bone"
    bl_description = "Set active bone"
    
    ui_index = IntProperty (name='', default=0)
    
    # operator function
    def execute(self, context):
        index = self.ui_index        
        scene = bpy.context.scene
        
        if bpy.context.mode == 'POSE':        
            scene.gyaz_export.extra_bones[index].source = bpy.context.active_bone.name
            
        return {'FINISHED'}


class Op_GYAZ_Export_SetParentAsActiveBone (bpy.types.Operator):
       
    bl_idname = "object.gyaz_export_set_parent_as_active_bone"  
    bl_label = "GYAZ Export: Set Parent As Active Bone"
    bl_description = "Set active bone"
    
    ui_index = IntProperty (name='', default=0)
    
    # operator function
    def execute(self, context):
        index = self.ui_index        
        scene = bpy.context.scene
        
        if bpy.context.mode == 'POSE':        
            scene.gyaz_export.extra_bones[index].parent = bpy.context.active_bone.name
            
        return {'FINISHED'}

    
class Op_GYAZ_Export_SetNameAsActiveBone (bpy.types.Operator):
       
    bl_idname = "object.gyaz_export_set_name_as_active_bone"  
    bl_label = "GYAZ Export: Set Name As Active Bone"
    bl_description = "Set active bone"
    
    ui_index = IntProperty (name='', default=0)
    
    # operator function
    def execute(self, context):
        index = self.ui_index        
        scene = bpy.context.scene
        scene_export_bones = getattr (scene.gyaz_export, "export_bones")
        
        if bpy.context.mode == 'POSE':
            
            bone = bpy.context.active_bone
            print (bone)
            if bone == None:
                report (self, 'No active bone.', 'WARNING')
            
            else:
                name = bone.name                
                names_already_in_collection = []
                for item in scene_export_bones:
                    names_already_in_collection.append (item.name)
                
                # set name        
                if name not in names_already_in_collection:
                    scene_export_bones[index].name = name
                else:
                    report (self, 'Bone is already listed.', 'INFO')
                
            
        return {'FINISHED'}
    
    
class Op_GYAZ_Export_MoveExtraBoneItem (bpy.types.Operator):
       
    bl_idname = "object.gyaz_export_move_extra_bone_item"  
    bl_label = "GYAZ Export: Move Up/Down Extra Bone Item"
    bl_description = "Move up/down"
    
    mode = EnumProperty (items=(('UP', 'UP', ''), ('DOWN', 'DOWN', '')), default='UP')
    index = IntProperty (name='', default=0)
    
    # operator function
    def execute(self, context):
        
        mode = self.mode     
        scene = bpy.context.scene
        index = scene.gyaz_export.extra_bones_active_index  
        rig = bpy.context.active_object
        
        if mode == 'UP':
        
            if index >= 1:
                target_index = index-1
            else:
                target_index = 0
               
            scene.gyaz_export.extra_bones.move (index, target_index)
            if len (scene.gyaz_export.extra_bones) > 0:
                scene.gyaz_export.extra_bones_active_index -= 1
            
        elif mode == 'DOWN':
            
            scene_extra_bones = getattr (scene.gyaz_export, "extra_bones")
            
            length = len (scene_extra_bones.items ())
            last_index = length-1
            if index < last_index:
                target_index = index+1
            else:
                target_index = last_index
               
            scene_extra_bones.move (index, target_index)
            if len (scene.gyaz_export.extra_bones) > scene.gyaz_export.extra_bones_active_index + 1:
                scene.gyaz_export.extra_bones_active_index += 1          
            
            
        return {'FINISHED'}
    

class Op_GYAZ_Export_SetActiveActionToExport (bpy.types.Operator):
       
    bl_idname = "object.gyaz_export_set_active_action_to_export"  
    bl_label = "GYAZ Export: Set Active Action to Export"
    bl_description = "Set active action"
    
    ui_index = IntProperty (name='', default=0)
    
    # operator function
    def execute(self, context):
        index = self.ui_index     
        scene = bpy.context.scene
        
        # get active action's name
        obj = bpy.context.object
        action = get_active_action (obj)
        action_name = action.name if action != None else ''
        
        # make list of already listed actions
        already_listed_actions = []
        for item in scene.gyaz_export.actions:
            already_listed_actions.append (item.name)
        
        if action == None:
            report (self, 'No action found.', 'INFO')
        elif action_name in already_listed_actions:
            report (self, 'Action is already listed.', 'INFO')
        else:
            scene.gyaz_export.actions[index].name = action_name
            
        return {'FINISHED'}
    

class Op_GYAZ_Export_SetFilterType (bpy.types.Operator):
       
    bl_idname = "object.gyaz_export_set_filter_type"  
    bl_label = "GYAZ Export: Set Filter Type"
    bl_description = "Filter Type"
    
    # operator function
    def execute(self, context):
        owner = bpy.context.scene.gyaz_export
        value = owner.filter_type
        
        if value == 'START':
            owner.filter_type = 'IN'
        if value == 'IN':
            owner.filter_type = 'END'
        if value == 'END':
            owner.filter_type = 'START'        
            
        return {'FINISHED'}
    
    
class Op_GYAZ_Export_Export (bpy.types.Operator):
       
    bl_idname = "object.gyaz_export_export"  
    bl_label = "GYAZ Export: Export"
    bl_description = "Export. STATIC MESHES: select one or multiple meshes, SKELETAL MESHES: select one armature, ANIMATIONS: select one armature, RIGID_ANIMATIONS: select one or multiple meshes"
    
    asset_type_override = EnumProperty (name='Asset Type', 
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
        
        start_mode = bpy.context.mode[:]
        
        bpy.ops.object.mode_set (mode='OBJECT')
        
        scene = bpy.context.scene
        space = bpy.context.space_data
        owner = scene.gyaz_export
        
        scene_objects = scene.objects
        ori_ao = bpy.context.active_object
        ori_ao_name = bpy.context.active_object.name
        ori_sel_objs = [obj for obj in bpy.context.selected_objects if obj.gyaz_export.export]
        mesh_children = [child for child in ori_ao.children if child.type == 'MESH' and child.gyaz_export.export]

        asset_type = owner.skeletal_asset_type if ori_ao.type == 'ARMATURE' else owner.rigid_asset_type          
                
        if asset_type == 'STATIC_MESHES' or asset_type == 'RIGID_ANIMATIONS':
            meshes_to_export = ori_sel_objs
        elif asset_type == 'SKELETAL_MESHES' or asset_type == 'ANIMATIONS':
            meshes_to_export = mesh_children        
        
        if self.asset_type_override != 'DO_NOT_OVERRIDE':
            asset_type = self.asset_type_override
        
                
        # LODs
        
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
                        if lod_obj != None:
                            if lod_obj.type == 'MESH':
                                obj_lods.append (lod_obj)                  
                
                lods += obj_lods
                lod_info[obj.name] = obj_lods
            
            meshes_to_export += lods
            
            lods_set = set (lods)
            ori_sel_objs = list ( set (ori_sel_objs) - lods_set )
            

        # COLLISION (mesh)
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
                    if col != None:
                        obj_cols.add ((col, prefix+'_'+name+'_00'))
                        collision_objs_ori.add (scene_objects.get (col.name))
                    for n in range (1, 100):
                        suffix = '.00'+str(n) if n < 10 else '.0'+str(n)
                        col = scene_objects.get (prefix+'_'+name+suffix)
                        collision_objs_ori.add (col)
                        if col != None:
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
            pack_name = owner.skeletal_mesh_pack_name
        elif asset_type == 'RIGID_ANIMATIONS':
            pack_objects = owner.rigid_anim_pack_objects
            pack_name = owner.rigid_anim_pack_name
            
        action_export_mode = owner.action_export_mode
        
        rigid_anim_cubes = True if owner.rigid_anim_cubes and not pack_objects else False

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
                if ebone != None:
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
                if 'root' in bone_list:
                    bone_list.remove ('root')
                if 'root' in export_bone_list:
                    export_bone_list.remove ('root')
                if 'root' in extra_bone_list:
                    extra_bone_list.remove ('root')
            
            
            # define clear transforms
            if asset_type == 'STATIC_MESHES':
                clear_transforms = scene.gyaz_export.static_mesh_clear_transforms
            elif asset_type == 'SKELETAL_MESHES' or asset_type == 'ANIMATIONS':
                clear_transforms = scene.gyaz_export.skeletal_clear_transforms
            
            
            # get root mode    
            if asset_type == 'SKELETAL_MESHES' or asset_type == 'ANIMATIONS':
                root_mode = scene.gyaz_export.root_mode
                
            # make all layers visible
            for n in range (0, 20):
                scene.layers[n] = True
            
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
            # GATHER COLLISION & SOCKETS AND SCALE UP MESHES AND SOCKETS
            ############################################################
            
            collision_objects = []
            sockets = []
            
            if asset_type == 'STATIC_MESHES':
                
                # geather collision (should be mesh)
                if export_collision:   
                    
                    collision_info_keys = collision_info.keys ()
                    for obj in ori_sel_objs:
                        obj_name = obj.name
                        # snap cursor to obj
                        space.cursor_location = obj.matrix_world.translation
                        if obj_name in collision_info_keys:
                            cols = collision_info [obj_name]
                            for col, new_name in cols:
                                # rename collision object
                                col.name = new_name
                                col.name = new_name
                                collision_objects.append (col)
                
                # clear parents    
                bpy.ops.object.select_all (action='DESELECT')
                for col in ori_sel_objs + collision_objects:
                    select_objects ([col])
                make_active (ori_sel_objs[0])
                bpy.ops.object.parent_clear (type='CLEAR_KEEP_TRANSFORM') 
                
                if export_collision:
                    # bake collision
                    obj_names = collision_info.keys()
                    for obj_name in obj_names:
                        obj = bpy.data.objects[obj_name]
                        col_obj_info = collision_info[obj_name]
                        col_objs = [x[0] for x in col_obj_info]
                        for col_obj in col_objs:
                            verts = col_obj.data.vertices
                            for v in verts:
                                v.co = apply_transforms (col_obj, v.co)
                                v.co = revert_transforms (obj, v.co)
                            col_obj.matrix_world = obj.matrix_world
                    
                    # rescale collision
                    rescale_meshes (collision_objects)             
                
                # rescale objects
                rescale_meshes (meshes_to_export)
                
                # parent collision to objs
                if export_collision:
                    collision_info_keys = collision_info.keys ()
                    for obj in ori_sel_objs:
                        obj_name = obj.name
                        if obj_name in collision_info_keys:
                            bpy.ops.object.select_all (action='DESELECT')
                            cols = collision_info [obj_name]
                            for col, new_name in cols:
                                collision = scene.objects.get (new_name)
                                if collision != None:
                                    select_objects ([collision])
                            if len (cols) > 0:
                                make_active (obj)
                                bpy.ops.object.parent_set (type='OBJECT', keep_transform=True)
                    bpy.ops.object.select_all (action='DESELECT')
                
                    
                # gather and rescale sockets (single bone armature objects)
                export_sockets = owner.export_sockets
                if export_sockets:
                    
                    for obj in ori_sel_objs:
                        for child in obj.children:
                            if child.type == 'ARMATURE' and child.name.startswith ('SOCKET_'):
                                child.scale = (1, 1, 1)
                                child.location *= 100
                                sockets.append (child)
                            

            #######################################################
            # REPLACE SKELETAL MESHES WITH CUBES
            # don't want to have high poly meshes in every animation file
            #######################################################
            
            if asset_type == 'ANIMATIONS' or asset_type == 'RIGID_ANIMATIONS' and rigid_anim_cubes:
 
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
                        
                        # you have to make the shapekeys modify the mesh otherwise the fbx exporter won't export it 
                        if obj.data.shape_keys != None:
                            for key_index, key_block in enumerate(obj.data.shape_keys.key_blocks):
                                if key_index != 0:
                                    for i in range (0, 8):
                                        key_block.data[i].co += Vector ((0, 0, 1))
                                        
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
            
            if asset_type == 'SKELETAL_MESHES' or asset_type == 'ANIMATIONS':
                
                make_active_only (ori_ao)
                bpy.ops.object.mode_set (mode='EDIT')
                ebones = ori_ao.data.edit_bones
                bones = ori_ao.data.bones
                
                # extra bone info
                extra_bone_info = []
                extra_bones = scene.gyaz_export.extra_bones
                for item in extra_bones:
                    if item.name.replace (" ", "") != "":
                        ebone = ebones.get (item.source)
                        if ebone != None: 
                            info = {'name': item.name, 'head': ebone.head[:], 'tail': ebone.tail[:], 'roll': ebone.roll, 'parent': item.parent}
                            extra_bone_info.append (info)
                
                bpy.ops.object.mode_set (mode='OBJECT')
                
                # duplicate armature
                final_rig_data = ori_ao.data.copy ()
                
                # create new armature object
                final_rig = bpy.data.objects.new (name='root', object_data=final_rig_data)
                scene.objects.link (final_rig)
                make_active_only (final_rig)
                final_rig.name = 'root'
                final_rig.name = 'root'
                
                # remove drivers
                if hasattr (final_rig_data, "animation_data") == True:
                    if final_rig_data.animation_data != None:
                        for driver in final_rig_data.animation_data.drivers:
                            final_rig_data.driver_remove (driver.data_path)
                
                # delete bones
                bpy.ops.object.mode_set (mode='EDIT')
                all_bones = set (bone.name for bone in final_rig_data.bones)
                bones_to_remove = all_bones - set (export_bone_list)
                bones_to_remove.add ('root')
                for name in bones_to_remove:
                    ebones = final_rig_data.edit_bones
                    ebone = ebones.get (name)
                    if ebone != None:
                        ebones.remove (ebone)
                    
                # create extra bones
                for item in extra_bone_info:
                    ebone = final_rig.data.edit_bones.new (name = item['name'])
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
                bpy.ops.object.mode_set (mode='OBJECT')
                final_rig.scale = (100, 100, 100)
                bpy.ops.object.transform_apply (location=False, rotation=False, scale=True)
                final_rig.delta_scale = (0.01, 0.01, 0.01) 
                
                # bind meshes to the final rig
                
                for child in mesh_children:
                    mods = child.modifiers
                    for m in mods:
                        if m.type == 'ARMATURE':
                            mods.remove (m)   

                make_active_only (final_rig)
                select_objects (mesh_children)
                bpy.ops.object.parent_set (type='ARMATURE', keep_transform=True)
                
                # constarint final rig to the original armature    
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
                    if ori_ao.data.bones.get ('root') != None:
                        subtarget = 'root' 
                else:
                    subtarget = ''           
                    
                c = final_rig.constraints.new (type='COPY_LOCATION')
                c.target = ori_ao
                c.subtarget = subtarget
                
                c = final_rig.constraints.new (type='COPY_ROTATION')
                c.target = ori_ao
                c.subtarget = subtarget
                
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
                
                
                # rename vert groups to match extra bone names
                if rename_vert_groups_to_extra_bones:   
                    for mesh in mesh_children:
                        vgroups = mesh.vertex_groups
                        for item in scene.gyaz_export.extra_bones:
                            vgroup = vgroups.get (item.source)
                            if vgroup != None:
                                vgroup.name = item.name
                                
                
                # make sure armature modifier points to the final rig
                for ob in mesh_children:
                    for m in ob.modifiers:
                        if m.type == 'ARMATURE':
                            m.object = final_rig  

     
            #######################################################
            # CHECK FOR WEIGHTS WITHOUT A BONE
            #######################################################
                
            if asset_type == 'SKELETAL_MESHES' or asset_type == 'ANIMATIONS':
                
                remove_boneless_vert_weights = scene.gyaz_export.remove_boneless_vert_weights
                
                if remove_boneless_vert_weights:
                    
                    for child in mesh_children:
                        vgroups = child.vertex_groups
                        for vgroup in vgroups:
                            if vgroup.name not in bone_list:
                                vgroups.remove (vgroup)
                                    
                                    
            #######################################################
            # LIMIT BONE INFLUENCES BY VERTEX
            #######################################################
            
            if asset_type == 'SKELETAL_MESHES':
                
                limit_prop = scene.gyaz_export.skeletal_mesh_limit_bone_influences
                
                for child in mesh_children:
                    if len (child.vertex_groups) > 0:
                        make_active_only (child)
                        bpy.ops.object.mode_set (mode='WEIGHT_PAINT')
                        if limit_prop != 'unlimited':
                            limit = int (limit_prop)
                            bpy.ops.object.vertex_group_limit_total (group_select_mode='ALL', limit=limit)
                    
                        # clean vertex weights with 0 influence    
                        bpy.ops.object.vertex_group_clean (group_select_mode='ALL', limit=0, keep_single=False)
                        
                        
            ###########################################################
            # REMOVE VERT COLORS,SHAPE KEYS, UVMAPS AND MERGE MATERIALS 
            ###########################################################
            
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
            
            # render meshes
            
            for obj in meshes_to_export:
                mesh = obj.data
                
                # vert colors
                if not export_vert_colors:
                    vcolors = mesh.vertex_colors
                    for vc in vcolors:
                        vcolors.remove (vc)
                else:
                    vcolors = mesh.vertex_colors
                    vcolors_to_remove = []
                    for index, vc in enumerate (vcolors):
                        if not mesh.gyaz_export.vert_color_export[index]:
                            vcolors_to_remove.append (vc)
                    
                    for vc in reversed (vcolors_to_remove):
                        vcolors.remove (vc)
                      
                # shape keys        
                if not export_shape_keys:
                    if mesh.shape_keys != None:
                        for key in mesh.shape_keys.key_blocks:
                            obj.shape_key_remove (key)
                            
                # uv maps
                uvmaps = get_uv_maps (mesh)            
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
                            mats.pop (0)
                    
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
                        
                    if mesh.shape_keys != None:
                        for key in mesh.shape_keys.key_blocks:
                            obj.shape_key_remove (key)            
#                            
            
            #######################################################
            # EXPORT OPERATOR PROPS
            #######################################################
            
            if asset_type == 'STATIC_MESHES':
                apply_mods = owner.static_mesh_apply_mods
            elif asset_type == 'SKELETAL_MESHES':
                apply_mods = owner.skeletal_mesh_apply_mods
            elif asset_type == 'RIGID_ANIMATIONS':
                apply_mods = owner.rigid_anim_apply_mods
            else:
                apply_mods = False
                
            # FBX EXPORTER SETTINGS:
            # MAIN
            version = 'BIN7400'
            use_selection = True
            global_scale = 1
            apply_unit_scale = False
            apply_scale_options = 'FBX_SCALE_NONE'
            axis_forward = '-Z'
            axis_up = 'Y'
            object_types = {'EMPTY', 'MESH', 'ARMATURE'}
            bake_space_transform = False
            use_custom_props = False
            path_mode = 'ABSOLUTE'
            batch_mode = 'OFF'
            # GEOMETRIES
            use_mesh_modifiers = apply_mods
            use_mesh_modifiers_render = True
            mesh_smooth_type = owner.mesh_smoothing
            use_mesh_edges = False
            use_tspace = True
            # ARMATURES
            use_armature_deform_only = False
            add_leaf_bones = owner.add_end_bones
            primary_bone_axis = '-Y'
            secondary_bone_axis = 'X'
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
                
            else:
                static_mesh_prefix = ''
                skeletal_mesh_prefix = ''
                material_prefix = ''
                texture_prefix = ''
                animation_prefix = ''
                
            # folder names
            textures_folder = sn(prefs.texture_folder_name) + '/'
            anims_folder = sn(prefs.anim_folder_name) + '/'
 

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
                                
                            elif image_format_mode == 'KEEP_IF_ANY':
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
                            
                            texture_prefix = prefs.texture_prefix if not new_image.name.startswith (prefs.texture_prefix) else ''  
                                
                            new_image.filepath = texture_folder + texture_prefix + sn(new_image.name) + '.' + final_extension
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
                            settings.compression = scene.gyaz_export.texture_compression * 100

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
                            if material != None:
                                materials.add (material)
                        
                    # add prefix to materials
                    material_prefix = prefs.material_prefix
                    
                    for material in materials:
                        if not material.name.startswith (material_prefix):
                            material.name = material_prefix + material.name
 
 
            ###########################################################
            # ANIMATION FUNCTIONS
            ###########################################################
            
            if asset_type == 'ANIMATIONS' or asset_type == 'RIGID_ANIMATIONS':
            
                use_scene_start_end = scene.gyaz_export.use_scene_start_end            
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
                        
                        if active_action != None: 
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
                    if action != None:                            
                        frame_start, frame_end = action.frame_range
                        scene.frame_start = frame_start
                        scene.frame_end = frame_end
                
            
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
                                
                                empty = bpy.data.objects.new (name = 'LOD_' + obj_name, object_data = None)
                                empty['fbx_type'] = 'LodGroup'
                                scene.objects.link (empty)

#                                if asset_type == 'SKELETAL_MESHES':
#                                    empty.delta_rotation_euler[0] += radians(90)
#                                    empty.delta_scale *= 0.01

                                make_active_only (empty)
                                select_object (obj)
                                bpy.ops.object.parent_set (type='OBJECT', keep_transform=True)
                                for lod in lods:
                                    make_active_only (empty)
                                    select_object (lod)
                                    bpy.ops.object.parent_set (type='OBJECT', keep_transform=True)
                                    final_selected_objects.append (lod)

#                                if asset_type == 'SKELETAL_MESHES':
#                                    obs = [obj] + lods
#                                    for ob in obs:
#                                        for m in ob.modifiers:
#                                            if m.type == 'ARMATURE':
#                                                m.object = final_rig
                                    
                    values = [False] * len (scene.objects)
                    scene.objects.foreach_set ('select', values)
                    select_objects (final_selected_objects)
                    
                    def ex ():
                        bpy.ops.export_scene.fbx (filepath=filepath, version=version, use_selection=use_selection, global_scale=global_scale, apply_unit_scale=apply_unit_scale, apply_scale_options=apply_scale_options, axis_forward=axis_forward, axis_up=axis_up, object_types=object_types, bake_space_transform=bake_space_transform, use_custom_props=use_custom_props, path_mode=path_mode, batch_mode=batch_mode, use_mesh_modifiers=use_mesh_modifiers, use_mesh_modifiers_render=use_mesh_modifiers_render, mesh_smooth_type=mesh_smooth_type, use_mesh_edges=use_mesh_edges, use_tspace=use_tspace, use_armature_deform_only=use_armature_deform_only, add_leaf_bones=add_leaf_bones, primary_bone_axis=primary_bone_axis, secondary_bone_axis=secondary_bone_axis, armature_nodetype=armature_nodetype, bake_anim=bake_anim, bake_anim_use_all_bones=bake_anim_use_all_bones, bake_anim_use_nla_strips=bake_anim_use_nla_strips, bake_anim_use_all_actions=bake_anim_use_all_actions, bake_anim_force_startend_keying=bake_anim_force_startend_keying, bake_anim_step=bake_anim_step, bake_anim_simplify_factor=bake_anim_simplify_factor )               
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
            
            owner = scene.gyaz_export
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
                rename_materials (objects = ori_sel_objs)
     
                if pack_objects:
                    
                    static_mesh_prefix = static_mesh_prefix if not pack_name.startswith (static_mesh_prefix) else ''
                    organizing_folder = pack_name + '/' if use_organizing_folder else ''
                    
                    filename = static_mesh_prefix + pack_name + format                         
                    filepath = root_folder + organizing_folder + filename
                    os.makedirs (root_folder + organizing_folder, exist_ok=True)
                    
                    texture_root = root_folder + organizing_folder[:-1]
                    
                    export_info = export_objects (filepath, objects = ori_sel_objs)   
                    texture_export_info = export_images (objects = ori_sel_objs, texture_root = texture_root, all_images = True)

                else:

                    for obj in ori_sel_objs:
                            
                        static_mesh_prefix = static_mesh_prefix if not obj.name.startswith (static_mesh_prefix) else ''
                        organizing_folder = sn(obj.name) + '/' if use_organizing_folder else ''
                        
                        filename = static_mesh_prefix + sn(obj.name) + format
                        filepath = root_folder + organizing_folder + filename
                        os.makedirs (root_folder + organizing_folder, exist_ok=True)
                        
                        texture_root = root_folder + organizing_folder[:-1]
                        
                        export_info = export_objects (filepath, objects = [obj])
                        texture_export_info = export_images (objects = [obj], texture_root = texture_root, all_images = False)
                        
 
            elif asset_type == 'SKELETAL_MESHES':
                
                if pack_objects:
                    
                    # export filter
                    make_active_only (final_rig)
                    if len (mesh_children) > 0:        
                    
                        skeletal_mesh_prefix = skeletal_mesh_prefix if not pack_name.startswith (skeletal_mesh_prefix) else ''
                        organizing_folder = pack_name + '/' if use_organizing_folder else ''
                        
                        filename = skeletal_mesh_prefix + pack_name + format
                        filepath = root_folder + organizing_folder + filename
                        os.makedirs (root_folder + organizing_folder, exist_ok=True)
                        
                        texture_root = root_folder + organizing_folder[:-1]
                        
                        rename_materials (objects = meshes_to_export)
                        export_info = export_objects (filepath, objects = [final_rig] + mesh_children)
                        texture_export_info = export_images (objects = mesh_children, texture_root = texture_root, all_images = True)                
                    
                else:
                    
                    organizing_folder = sn(ori_ao.name) + '/' if use_organizing_folder else ''
                    texture_root = root_folder + organizing_folder[:-1]
                    
                    if len (mesh_children) > 0:
                        for child in mesh_children:
                                
                            skeletal_mesh_prefix = skeletal_mesh_prefix if not child.name.startswith (skeletal_mesh_prefix) else ''
                            
                            filename = skeletal_mesh_prefix + sn(child.name) + format
                            filepath = root_folder + organizing_folder + filename
                            os.makedirs (root_folder + organizing_folder, exist_ok=True)
                            
                            export_info = export_objects (filepath, objects = [final_rig, child])    
                            texture_export_info = export_images (objects = mesh_children, texture_root = texture_root, all_images = True)
                                          
                                    
            elif asset_type == 'ANIMATIONS':
                
                actions_to_export = get_actions_to_export (object = ori_ao)
                
                # fbx export settings
                bake_anim = True
                
                rename_materials (objects = mesh_children)
                use_override_character_name = owner.use_anim_object_name_override
                override_character_name = owner.anim_object_name_override
                organizing_folder = sn(ori_ao.name) + '/' if use_organizing_folder else ''
                texture_root = root_folder + organizing_folder[:-1]      
                
                for action in actions_to_export:
                    
                    name = sn(ori_ao_name) if not use_override_character_name else override_character_name
                    separator = '_' if not name == '' else ''
                    filepath = root_folder + organizing_folder + anims_folder + animation_prefix + name + separator + sn(action.name) + format
                    os.makedirs (root_folder + organizing_folder + anims_folder, exist_ok=True)
                    
                    set_active_action (action)
                    if not use_scene_start_end:
                        adjust_scene_to_action_length (object = ori_ao)
                        
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
                    skeletal_mesh_prefix = animation_prefix
                                
                if pack_objects:
                    
                    skeletal_mesh_prefix = skeletal_mesh_prefix if not pack_name.startswith (skeletal_mesh_prefix) else ''                            
                    organizing_folder = pack_name + '/' if use_organizing_folder else '/'
                    filepath = root_folder + organizing_folder + skeletal_mesh_prefix + pack_name + '_' + anim_name + format
                    texture_root = root_folder + organizing_folder
                    
                    os.makedirs(root_folder + organizing_folder, exist_ok=True) 
                        
                    export_info = export_objects (filepath, objects = ori_sel_objs)
                    if not rigid_anim_cubes:
                        texture_export_info = export_images (objects = ori_sel_objs, texture_root = texture_root, all_images = True)
                     
                else:
                
                    for obj in ori_sel_objs:

                        skeletal_mesh_prefix = skeletal_mesh_prefix if not obj.name.startswith (skeletal_mesh_prefix) else ''
                        organizing_folder = sn(obj.name) + '/' if use_organizing_folder else '/'
                        filepath = root_folder + organizing_folder + skeletal_mesh_prefix + sn(obj.name) + '_' + anim_name + format 
                        
                        texture_root = root_folder + organizing_folder
                        
                        if not use_scene_start_end:
                            adjust_scene_to_action_length (object = obj)
                        
                        os.makedirs(root_folder + organizing_folder, exist_ok=True)
                        
                        export_info = export_objects (filepath, objects = [obj])
                        if not rigid_anim_cubes:
                            texture_export_info = export_images (objects = [obj], texture_root = texture_root, all_images = False)

      
            # make sure no images get deleted (because aftert the export, the blend file is reloaded)
            # it should be called before and after reload
            for image in bpy.data.images:
                if image.users == 0:
                    image.use_fake_user = True
                    
            # clear stamp
            for obj in scene_objects:
                if gyaz_stamp in obj:
                    del obj[gyaz_stamp]
                if obj.type == 'MESH':
                    if obj.get ('data') != None:
                        if gyaz_stamp in obj.data:
                            del obj.data[gyaz_stamp]
            
            
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
            
                    
            # export_info: for opening last export in explorer
            info = None
            if 'export_info' in locals ():
                if export_info != None:
                    info = export_info
                elif 'texture_export_info' in locals ():
                    if texture_export_info != None:
                        info = texture_export_info[:-1]
            
            if info != None:  
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
            
            good_to_go = False
            report_cache = []
                                    
            #
            no_material_objects = []  
            no_uv_map_objects = []
            no_second_uv_map_objects = []
            bad_poly_objects = []
            ungrouped_vert_objects = []
            mirrored_uv_objects = []
            missing_textures = []
            
            image_info = {}
            
            missing_bones = []
            cant_create_extra_bones = []
            poly_warning = ''
            
            # mesh checks
            for obj in meshes_to_export:
                
                # materials
                materials = []
                
                for slot in obj.material_slots:
                    
                    if slot.material != None:
                        
                        materials.append (slot.material)
                        
                if len (materials) == 0:
                    
                    no_material_objects.append (obj.name)
                       
                
                # uv maps
                uv_maps = []
                
                for index, uv_map in enumerate (obj.data.uv_textures):
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
                bm.from_object (obj, scene=bpy.context.scene, deform=False, render=True, cage=False, face_normals=False)
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
                        for n in range (len(mesh.uv_textures)):
                            mirrored_uvs_found = detect_mirrored_uvs (bm, uv_index=n)
                            if mirrored_uvs_found:
                                mirrored_indices.append (n)
                            
                        if mirrored_uvs_found:
                            mirrored_uv_objects.append (obj.name + ' (' + list_to_visual_list(mirrored_indices) + ')')
                                
                        bm.free ()
                    
                # textures
                # get list of texture images
                if scene.gyaz_export.export_textures:
                    
                    images = set ()
                    for material in materials:
                        if material != None:
                            node_tree = material.node_tree
                            if node_tree != None:
                                nodes = node_tree.nodes
                                for node in nodes:
                                    if node.type == 'TEX_IMAGE':
                                        image = node.image
                                        images.add (image)
                                    elif node.type == 'GROUP':
                                        for node in node.node_tree.nodes:
                                            if node.type == 'TEX_IMAGE':
                                                images.add (node.image)
                                            elif node.type == 'GROUP':
                                                for node in node.node_tree.nodes:
                                                    if node.type == 'TEX_IMAGE':
                                                        images.add (node.image)
                                                    elif node.type == 'GROUP':
                                                        for node in node.node_tree.nodes:
                                                            if node.type == 'TEX_IMAGE':
                                                                images.add (node.image)
                                                            elif node.type == 'GROUP':
                                                                for node in node.node_tree.nodes:
                                                                    if node.type == 'TEX_IMAGE':
                                                                        images.add (node.image)
                                                                    elif node.type == 'GROUP':
                                                                        for node in node.node_tree.nodes:
                                                                            if node.type == 'TEX_IMAGE':
                                                                                images.add (node.image)
                                                                            elif node.type == 'GROUP':
                                                                                for node in node.node_tree.nodes:
                                                                                    if node.type == 'TEX_IMAGE':
                                                                                        images.add (node.image)
                                                                                    elif node.type == 'GROUP':                                                                                
                                                                                        for node in node.node_tree.nodes:
                                                                                            if node.type == 'TEX_IMAGE':
                                                                                                images.add (node.image)
                                                                                            elif node.type == 'GROUP':                                                                                 
                                                                                                for node in node.node_tree.nodes:
                                                                                                    if node.type == 'TEX_IMAGE':
                                                                                                        images.add (node.image)
                                                                                                    elif node.type == 'GROUP':                                                                                  
                                                                                                        for node in node.node_tree.nodes:
                                                                                                            if node.type == 'TEX_IMAGE':
                                                                                                                images.add (node.image)
                                                                                                            elif node.type == 'GROUP':                                                                                  
                                                                                                                for node in node.node_tree.nodes:
                                                                                                                    if node.type == 'TEX_IMAGE':
                                                                                                                        images.add (node.image)
                                                                                                                    elif node.type == 'GROUP':                                                                                  
                                                                                                                        for node in node.node_tree.nodes:
                                                                                                                            if node.type == 'TEX_IMAGE':
                                                                                                                                images.add (node.image)
                                                                                                                            elif node.type == 'GROUP':                                                                                 
                                                                                                                                for node in node.node_tree.nodes:
                                                                                                                                    if node.type == 'TEX_IMAGE':
                                                                                                                                        images.add (node.image)
                                                                                                                                    elif node.type == 'GROUP':                                                                                  
                                                                                                                                        for node in node.node_tree.nodes:
                                                                                                                                            if node.type == 'TEX_IMAGE':
                                                                                                                                                images.add (node.image)
                                                                                                                                            elif node.type == 'GROUP':                                                                                  
                                                                                                                                                for node in node.node_tree.nodes:
                                                                                                                                                    if node.type == 'TEX_IMAGE':
                                                                                                                                                        images.add (node.image)
                                                                                                                                                    elif node.type == 'GROUP':                                                                                  
                                                                                                                                                        for node in node.node_tree.nodes:
                                                                                                                                                            if node.type == 'TEX_IMAGE':
                                                                                                                                                                images.add (node.image)
                                                                                                                                                            elif node.type == 'GROUP':                                                                                  
                                                                                                                                                                for node in node.node_tree.nodes:
                                                                                                                                                                    if node.type == 'TEX_IMAGE':
                                                                                                                                                                        images.add (node.image)
                                                                                                                                                                    elif node.type == 'GROUP':                                                                                  
                                                                                                                                                                        for node in node.node_tree.nodes:
                                                                                                                                                                            if node.type == 'TEX_IMAGE':
                                                                                                                                                                                images.add (node.image)
                                                                                                                                                                            
                    images = set (i for i in images if i != None)
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
             
            # missing_bones            
            if asset_type == 'SKELETAL_MESHES' or asset_type == 'ANIMATIONS':
                rig_bone_names = [x.name for x in ori_ao.data.bones]
                export_bone_names = [x.name for x in scene.gyaz_export.export_bones]
                if not scene.gyaz_export.export_all_bones:
                    missing_bones = [item.name for item in scene.gyaz_export.export_bones if item.name not in rig_bone_names and item.name != '']
                if len (scene.gyaz_export.extra_bones) > 0:
                    for index, item in enumerate(scene.gyaz_export.extra_bones):
                        if item.name == '':
                            cant_create_extra_bones.append (index)
                        if item.source not in rig_bone_names:
                            cant_create_extra_bones.append (index)
                        if item.name in export_bone_names:
                            cant_create_extra_bones.append (index)
            
            # everythings ok?            
            if asset_type == 'STATIC_MESHES': 
                if len(no_material_objects)==0 and len(no_uv_map_objects)==0 and len(bad_poly_objects)==0 and len(missing_textures)==0 and len(mirrored_uv_objects)==0:
                    if len (no_second_uv_map_objects) == 0:
                        good_to_go = True
                        
                    else:
                        if scene.gyaz_export.check_for_second_uv_map:
                            if not scene.gyaz_export.ignore_missing_second_uv_map:
                                good_to_go = False
                                
                            else:
                                good_to_go = True
                                
                        else:
                            good_to_go = True
                
                else:
                    good_to_go = False
            
            else:
                """ SKELETAL MESHES, RIGID ANIMATIONS"""
                if len(no_material_objects)==0 and len(no_uv_map_objects)==0 and len(bad_poly_objects)==0 and len(missing_textures)== 0 and len(missing_bones)==0 and len(cant_create_extra_bones)==0 and len(ungrouped_vert_objects)==0 and len(mirrored_uv_objects)==0:
                    good_to_go = True
                    
                else:
                    good_to_go = False
            
            
            # if not...        
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
                
                l1 = 'No materials: ' + vl1
                l2 = 'No uv maps: ' + vl2
                l3 = 'No 2nd uv map: ' + vl3
                l4 = poly_warning + vl4
                l5 = 'Ungrouped verts: ' + vl5
                l6 = 'Mirrored UVs: ' + vl6
                l7 = 'Missing/unsaved textures: ' + vl7
                l8 = 'Missing bones: ' + vl8
                l9 = "Can't create extra bones: " + vl9
                
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
                
                # popup
                if len (lines) > 0:
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
                    good_to_go = True
                    
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
        
            def is_local (obj):
                if obj.layers_local_view[0]:
                    return True
                else:
                    return False
            
            if is_local(bpy.context.object):
                report (self, "Leave local view.", "WARNING")
                
            else:
                ok = True
                if asset_type == 'STATIC_MESHES' and pack_objects:
                    if pack_name.replace (" ", "") == "":
                        ok = False
                        report (self, "Pack name is invalid.", "WARNING")
                    
                elif asset_type == 'RIGID_ANIMATIONS' and pack_objects:
                    if pack_name.replace (" ", "") == "":
                        ok = False
                        report (self, "Pack name is invalid.", "WARNING")
                        
                if ok:
                    
                    path_ok = True
                    if owner.export_folder_mode == 'PATH':
                        if not os.path.isdir (root_folder):
                            report (self, "Export path doesn't exist.", "WARNING")
                            path_ok = False
                        
                    if path_ok:
                        
                        if asset_type == 'ANIMATIONS':
                            actions_set_for_export = scene.gyaz_export.actions
                            if ori_ao.type == 'ARMATURE':     
                                if action_export_mode == 'ACTIVE': 
                                    if getattr (ori_ao, "animation_data") != None:
                                        if ori_ao.animation_data.action != None:
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
                                        
                            else:
                                report (self, 'Active object is not an armature.', 'WARNING')

                                    
                        elif asset_type == 'SKELETAL_MESHES':
                            if ori_ao.type == 'ARMATURE':
                                if len (mesh_children) > 0:
                                    if scene.gyaz_export.root_mode == 'BONE':    
                                        if ori_ao.data.bones.get ('root') != None:
                                            checks_plus_main ()
                                            
                                        else:
                                            report (self, 'Armature has no "root" bone. Set object as root.', 'WARNING')
                                            
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
                                    checks_plus_main ()
                                else:
                                    report (self, 'No objects set for export.', 'WARNING')
        
        
        return {'FINISHED'}
    
    # when the buttons should show up    
    @classmethod
    def poll(cls, context):
        ao =  bpy.context.active_object  
        return ao != None

    
# UI
class Pa_GYAZ_Export_Bones (Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_category = 'Export FBX'
    bl_label = 'Export Bones'
    
    # add ui elements here
    def draw (self, context):
        
        if bpy.context.object.type == 'ARMATURE':
            
            scene = bpy.context.scene
            rig = bpy.context.active_object      
            lay = self.layout
            owner = scene.gyaz_export
            
            col = lay.column (align=True)
            col.label (text = 'Bone Presets:')
            row = col.row (align=True)
            row.prop (owner, "active_preset", text='')
            row.operator (Op_GYAZ_Export_SavePreset.bl_idname, text='', icon='ZOOMIN')
            row.operator (Op_GYAZ_Export_RemovePreset.bl_idname, text='', icon='ZOOMOUT')
            
            col = lay.column (align=True)
            col.label ('Root:')
            col.prop (owner, 'root_mode', text='')
            col = lay.column (align=True)
            row = col.row (align=True)
            row.label (text = 'Extra Bones:')
            row.prop (owner, "extra_bones")
            if len (owner.extra_bones) > 0:
                col.prop (owner, 'constraint_extra_bones')
                col.prop (owner, 'rename_vert_groups_to_extra_bones')
                col.prop (owner, 'extra_bones_long_rows')
            extra_bones = owner.extra_bones
            col = lay.column (align=True)
            row = col.row (align=True)
            row.operator (Op_GYAZ_Export_Functions.bl_idname, text='', icon='ZOOMIN').ui_mode = 'ADD_TO_EXTRA_BONES'
            row.operator (Op_GYAZ_Export_RemoveItemFromExtraBones.bl_idname, text='', icon='ZOOMOUT')
            row.separator ()
            op = row.operator (Op_GYAZ_Export_MoveExtraBoneItem.bl_idname, text='', icon='TRIA_UP').mode = 'UP'
            op = row.operator (Op_GYAZ_Export_MoveExtraBoneItem.bl_idname, text='', icon='TRIA_DOWN').mode = 'DOWN'
            row.separator ()
            row.operator (Op_GYAZ_Export_Functions.bl_idname, text='', icon='X').ui_mode = 'REMOVE_ALL_FROM_EXTRA_BONES'
            row.separator ()
            row.operator (Op_GYAZ_Export_ReadSelectedPoseBones.bl_idname, text='', icon='EYEDROPPER').mode='EXTRA_BONES'
            if len (owner.extra_bones) > 0:
                index = owner.extra_bones_active_index
                item = extra_bones[index]
                if len (owner.extra_bones) > 0:
                    lay.template_list ("UL_GYAZ_ExtraBones", "",  # type and unique id
                        owner, "extra_bones",  # pointer to the CollectionProperty
                        owner, "extra_bones_active_index",  # pointer to the active identifier
                        rows = 1, maxrows = 1)
                    col = lay.column (align=True)
                    if not owner.extra_bones_long_rows:
                        col.label ('Source, Parent:')
                        col = col.column (align=True)
                        row = col.row (align=True)
                        row.prop_search (item, "source", rig.data, "bones", icon='GROUP_BONE')
                        row.operator (Op_GYAZ_Export_SetSourceAsActiveBone.bl_idname, text='', icon='EYEDROPPER').ui_index = index
                        row = col.row (align=True)
                        row.prop (item, "parent", text='', icon='NODETREE')
                        row.operator (Op_GYAZ_Export_SetParentAsActiveBone.bl_idname, text='', icon='EYEDROPPER').ui_index = index
                    else:
                        col.label ('(New Name, Parent, Source)')          

            col = lay.column (align=True)            
            row = col.row (align=True)
            row.label ('Export Bones:')
            row.prop (owner, "export_bones")
            col.prop (owner, "export_all_bones")
            col.separator ()
            if not owner.export_all_bones:
                row = col.row (align=True)
                row.operator (Op_GYAZ_Export_Functions.bl_idname, text='', icon='ZOOMIN').ui_mode = 'ADD_TO_EXPORT_BONES'
                row.operator (Op_GYAZ_Export_Functions.bl_idname, text='', icon='X').ui_mode = 'REMOVE_ALL_FROM_EXPORT_BONES'
                row.separator ()
                row.operator (Op_GYAZ_Export_ReadSelectedPoseBones.bl_idname, text='', icon='EYEDROPPER').mode='EXPORT_BONES'
                row.separator ()
                lay.template_list ("UL_GYAZ_ExportBones", "",  # type and unique id
                    owner, "export_bones",  # pointer to the CollectionProperty
                    owner, "export_bones_active_index",  # pointer to the active identifier
                    rows = 1, maxrows = 1)        

    # when the buttons should show up    
    @classmethod
    def poll(cls, context):
        mode = bpy.context.mode
        ao = bpy.context.active_object
        good_to_go = False
        if ao != None:
            if ao.type == 'ARMATURE':
                if mode == 'OBJECT' or mode == 'POSE':
                    good_to_go = True
        if good_to_go:
            return True
        else:
            return False


class Pa_GYAZ_Export_Animation (Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_category = 'Export FBX'
    bl_label = 'Export Animations'  
    
    # add ui elements here
    def draw (self, context):
        
        scene = bpy.context.scene
        owner = scene.gyaz_export        
        lay = self.layout
        
        lay.row().prop (owner, "action_export_mode", expand=True)        
        if owner.action_export_mode == 'BY_NAME':
            row = lay.row (align=True)
            row.operator (Op_GYAZ_Export_Functions.bl_idname, text='', icon='ZOOMIN').ui_mode='ADD_TO_EXPORT_ACTIONS'
            row.operator (Op_GYAZ_Export_Functions.bl_idname, text='', icon='X').ui_mode='REMOVE_ALL_FROM_EXPORT_ACTIONS'
            lay.template_list ("UL_GYAZ_ExportActions", "",  # type and unique id
                owner, "actions",  # pointer to the CollectionProperty
                owner, "actions_active_index",  # pointer to the active identifier
                rows = 1, maxrows = 1)
                
    # when the buttons should show up    
    @classmethod
    def poll(cls, context):
        mode = bpy.context.mode
        ao = bpy.context.active_object
        good_to_go = False
        if ao != None:
            if ao.type == 'ARMATURE':
                if mode == 'OBJECT' or mode == 'POSE':
                    good_to_go = True
        if good_to_go:
            return True
        else:
            return False
                

class Pa_GYAZ_Export (Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_category = 'Export FBX'
    bl_label = 'Export'
    
    # add ui elements here
    def draw (self, context):
        
        scene = bpy.context.scene
        owner = scene.gyaz_export        
        lay = self.layout
        
        if owner.show_options:
            row = lay.row ()
            row.label (text='Options:')
            
            icon = 'SOLO_OFF' if not owner.show_debug_props else 'SOLO_ON'
            row.prop (owner, "show_debug_props", text='', icon=icon, emboss=False)
            col = lay.column (align=True)     
            col.prop (owner, "texture_format_mode", text='Texture')
            col.prop (owner, "texture_format_override", text='Override')
            lay.prop (owner, "texture_compression", slider=True)
            col = lay.column (align=True)    
            col.prop (owner, "use_prefixes")
            col.prop (owner, "remove_boneless_vert_weights")
            col.prop (owner, "add_end_bones")
            col.prop (owner, "check_for_second_uv_map")
            col.prop (owner, "detect_mirrored_uvs")
            col.prop (owner, "allow_quads")
            col.prop (owner, "mesh_smoothing")
            
            if owner.show_debug_props:
                col = lay.column ()
                col = lay.column (align=True)
                col.label ('Debug:')
                col.prop (owner, "dont_reload_scene")
                
            lay.prop (owner, "show_options", text='', icon='TRIA_UP', emboss=False)
                
        else:
            lay.prop (owner, "show_options", text='', icon='TRIA_DOWN', emboss=False)
        
        obj = bpy.context.active_object
        if obj != None:
            col = lay.column (align=True)
            col.label ('Destination:')
            row = col.row (align=True)
            row.prop (owner, 'export_folder_mode', expand=True)
            relative = owner.export_folder_mode == 'RELATIVE_FOLDER'
            path = '//' + owner.relative_folder_name if relative else owner.export_folder
            row.operator (Op_GYAZ_Export_OpenFolderInWindowsFileExplorer.bl_idname, text='', icon='VIEWZOOM').path=path
            if relative:
                lay.prop (owner, "relative_folder_name")
            else:
                lay.prop (owner, "export_folder", text="")   
            lay.label ('Asset Type:')
            col = lay.column (align=True)
            if obj.type == 'ARMATURE':
                asset_type = owner.skeletal_asset_type
                col.prop (owner, 'skeletal_asset_type', expand=True)   
            else:
                asset_type = owner.rigid_asset_type
                col.prop (owner, 'rigid_asset_type', expand=True)
        
        col = lay.column (align=True)
        if asset_type == 'STATIC_MESHES':
            col.prop (owner, "use_static_mesh_organizing_folder")
            col.prop (owner, "static_mesh_clear_transforms")
            col.prop (owner, "static_mesh_apply_mods")
            col.prop (owner, "static_mesh_vcolors")
            col.prop (owner, "export_collision")
            col.prop (owner, "export_sockets")
            col.prop (owner, "export_lods")
            if owner.check_for_second_uv_map:
                col.prop (owner, "ignore_missing_second_uv_map")
            col.prop (owner, "export_textures")
            if owner.export_textures:
                col.prop (owner, "export_only_textures")
            col.prop (owner, "static_mesh_pack_objects")
            if owner.static_mesh_pack_objects:
                row = col.row (align=True)
                row.label (icon='BLANK1')
                row.prop (owner, "static_mesh_pack_name")
            
        elif asset_type == 'SKELETAL_MESHES':
            col.prop (owner, "use_skeletal_organizing_folder")          
            col.prop (owner, "skeletal_clear_transforms")
            col.prop (owner, "skeletal_mesh_apply_mods")
            col.prop (owner, "skeletal_mesh_vcolors")
            col.prop (owner, "skeletal_shapes")
            row = col.row (align=True)
            row.label (icon='BLANK1')
            row.prop (owner, "skeletal_mesh_limit_bone_influences", text='')
            col.prop (owner, "export_textures")
            if owner.export_textures:
                col.prop (owner, "export_only_textures")
            col.prop (owner, "skeletal_mesh_pack_objects")
            if owner.skeletal_mesh_pack_objects:
                row = col.row (align=True)
                row.label (icon='BLANK1')
                row.prop (owner, "skeletal_mesh_pack_name")
            
        elif asset_type == 'ANIMATIONS':
            col.prop (owner, "use_skeletal_organizing_folder")
            col.prop (owner, 'use_anim_object_name_override')
            if owner.use_anim_object_name_override:
                row = col.row (align=True)
                row.label (text='', icon='BLANK1')
                row.prop (owner, 'anim_object_name_override')
            col.prop (owner, "skeletal_clear_transforms")
            col.prop (owner, "skeletal_shapes")
            col.prop (owner, "use_scene_start_end")

        elif asset_type == 'RIGID_ANIMATIONS':
            col.prop (owner, "use_rigid_anim_organizing_folder")
            col.prop (owner, "rigid_anim_apply_mods")
            col.prop (owner, "rigid_anim_vcolors")
            col.prop (owner, "rigid_anim_shapes")
            row = col.row ()
            row.enabled = True if not owner.rigid_anim_cubes or owner.rigid_anim_cubes and owner.rigid_anim_pack_objects else False
            row.prop (owner, "export_textures")
            row = col.row ()
            rule1 = True if not owner.rigid_anim_pack_objects else False
            row.enabled = rule1
            row.prop (owner, "rigid_anim_cubes")
            row = col.row ()
            row.enabled = rule1
            row.prop (owner, "use_scene_start_end")
            col.prop (owner, "rigid_anim_pack_objects")
            if owner.rigid_anim_pack_objects:
                row = col.row (align=True)
                row.label (icon='BLANK1')
                row.prop (owner, "rigid_anim_pack_name")
                message1 = True
            else:
                message1 = False
            col.label ('Animation Name:')
            row = col.row (align=True)
            row.label (icon='BLANK1')
            row.prop (owner, "rigid_anim_name")
            if message1:
                col.label (text="Scene start end forced", icon='INFO')      
        
        row = lay.row (align=True)
        row.scale_y = 2
        row.operator (Op_GYAZ_Export_Export.bl_idname, text='EXPORT', icon='EXPORT')
        row.operator (Op_GYAZ_Export_SelectFileInWindowsFileExplorer.bl_idname, text='', icon='VIEWZOOM').path=owner.path_to_last_export
        
    # when the buttons should show up    
    @classmethod
    def poll(cls, context):
        ao = bpy.context.active_object
        mode = bpy.context.mode
        if ao != None:
            return mode == 'OBJECT' or mode == 'POSE' or mode == 'PAINT_TEXTURE' or mode == 'PAINT_VERTEX'


class Pa_GYAZ_Export_Filter (Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_category = 'Export FBX'
    bl_label = 'Export Filter' 
    
    # add ui elements here
    def draw (self, context):
        
        scene = bpy.context.scene   
        owner = scene.gyaz_export     
        lay = self.layout
        obj = bpy.context.object
        asset_type = owner.skeletal_asset_type if obj.type == 'ARMATURE' else owner.rigid_asset_type
        
        # utility
        row = lay.row (align=True)
        row.scale_x = 1.5
        row.operator (Op_GYAZ_Export_MarkAllSelectedForExport.bl_idname, text='', icon='CHECKBOX_HLT')
        row.operator (Op_GYAZ_Export_MarkAllSelectedNotForExport.bl_idname, text='', icon='CHECKBOX_DEHLT')
        row.separator ()
        row.operator (Op_GYAZ_Export_MarkAllForExport.bl_idname, text='', icon='SCENE_DATA')
        row.operator (Op_GYAZ_Export_MarkAllNotForExport.bl_idname, text='', icon='CHECKBOX_DEHLT')
        row.separator ()
        row.operator (Op_GYAZ_Export_SetFilterType.bl_idname, text=owner.filter_type)
        col = lay.column (align=True)
        col.prop (owner, "filter_string", text='', icon='VIEWZOOM')   
        
        filter = str.lower (owner.filter_string)
        type = owner.filter_type
        
        if asset_type == 'STATIC_MESHES' or asset_type == 'RIGID_ANIMATIONS':
            col = lay.column (align=True)
            for obj in bpy.context.selected_objects:
                if obj.type == 'MESH':
                    show = False
                    name = str.lower (obj.name)
                    if type == 'IN':
                        if filter in name:
                            show = True
                    elif type == 'END':
                        if name.endswith (filter):
                            show = True
                    elif type == 'START':
                        if name.startswith (filter):
                            show = True
                    if show:
                        col.prop (obj.gyaz_export, "export", text=obj.name, emboss=True, toggle=True)
        
        elif asset_type == 'SKELETAL_MESHES' or asset_type == 'ANIMATIONS':
            col = lay.column (align=True)
            for child in bpy.context.active_object.children:
                if child.type == 'MESH':
                    show = False
                    name = str.lower (child.name)
                    if type == 'IN':
                        if filter in name:
                            show = True
                    elif type == 'END':
                        if name.endswith (filter):
                            show = True
                    elif type == 'START':
                        if name.startswith (filter):
                            show = True
                    if show:
                        col.prop (child.gyaz_export, "export", text=child.name, emboss=True, toggle=True)
                        
    # when the buttons should show up    
    @classmethod
    def poll(cls, context):
        ao = bpy.context.active_object
        mode = bpy.context.mode
        if ao != None:
            return mode == 'OBJECT' or mode == 'POSE' or mode == 'PAINT_TEXTURE' or mode == 'PAINT_VERTEX'
    

class Pa_GYAZ_Export_Extras (Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_category = 'Export FBX'
    bl_label = 'Extras'
    bl_context = 'objectmode'    
    
    # add ui elements here
    def draw (self, context):      
        lay = self.layout     
        lay.operator ('import_scene.fbx', text='Import FBX')
        
        
# merge materials ui
def ui_merge_materials (self, context):      
    lay = self.layout
    obj = context.object
    if obj.type == 'MESH':
        owner = obj.data.gyaz_export
        lay.prop (owner, 'merge_materials', toggle=True)
        lay.prop (owner, 'atlas_name')    
        

# uv utils        
class Op_GYAZ_MoveUVMap (bpy.types.Operator):
       
    bl_idname = "object.gyaz_utility_move_uv_map"  
    bl_label = "Move UV Map"
    bl_description = "Move active uv map"
    
    up = BoolProperty (default=False)

    #operator function
    def execute(self, context):
        
        mesh = bpy.context.mesh
        uvmaps = get_uv_maps (mesh)
        map_count = len (uvmaps)
                        
        if map_count >= 8:
            report (self, 'Cannot reorder 8 uv maps.', 'WARNING')
        else:
            
            if map_count > 0:

                def move_down ():
                    
                    save__export = list(mesh.gyaz_export.uv_export[:])
                    
                    ori_active_index = uvmaps.active_index
                    ori_active_name = uvmaps[ori_active_index].name
                    for uvm in uvmaps:
                        if uvm.active_render:
                            ori_active_render = uvm.name
                    
                    if ori_active_index != map_count-1:
                    
                        def move_to_bottom (skip):
                            active_index = ori_active_index + skip
                            uvmaps.active_index = active_index
                            active_name = uvmaps[uvmaps.active_index].name
                            new = uvmaps.new ()
                            uvmaps.remove (uvmaps[active_index])
                            uvmaps.active_index = 0
                            uvmaps[-1].name = active_name

                        move_to_bottom (skip=0)
                        for n in range (0, map_count-ori_active_index-2):
                            move_to_bottom (skip=1)        

                        uvmaps.get(ori_active_name).active = True
                        uvmaps.get(ori_active_render).active_render = True
                    
                    # update export bools
                    new_export = save__export.copy ()
                    new_export[ori_active_index] = save__export[uvmaps.active_index]
                    new_export[uvmaps.active_index] = save__export[ori_active_index]
                    mesh.gyaz_export.uv_export = new_export
                    
                def move_up ():
                    
                    ori_active_index = uvmaps.active_index
                    ori_active_name = uvmaps[ori_active_index].name
                    for uvm in uvmaps:
                        if uvm.active_render:
                            ori_active_render = uvm.name
                    
                    if ori_active_index != 0:
                    
                        uvmaps.active_index -= 1
                        
                        move_down ()
                        
                        uvmaps.get(ori_active_name).active = True
                        uvmaps.get(ori_active_render).active_render = True
                    

                if self.up:
                    move_up ()
                else:
                    move_down ()        

                              
        return {'FINISHED'}


class Op_GYAZ_BatchSetActiveUVMapByIndex (bpy.types.Operator):
       
    bl_idname = "object.gyaz_utility_batch_set_active_uv_map_by_index"  
    bl_label = "Batch Set Active UV Map by Index"
    bl_description = "Set uv map active on all selected objects by the index of the active object's active uv map"
    
    for_render = BoolProperty (default=False)

    #operator function
    def execute(self, context):
        scene = bpy.context.scene
        object = bpy.context.object
        selected_objects = bpy.context.selected_objects
        
        uvmaps = get_uv_maps (object.data)
        if len (uvmaps) > 0:
            active_uv_map_index = uvmaps.active_index
            
            for obj in selected_objects:
                if obj.type == 'MESH':
                    uv_maps = get_uv_maps (obj.data)
                    if len (uv_maps) > 0:
                        if active_uv_map_index < len(uv_maps):
                            if not self.for_render:
                                uv_maps.active_index = active_uv_map_index
                            else:
                                uv_maps[active_uv_map_index].active_render = True
                              
        return {'FINISHED'}
    

class Op_GYAZ_BatchSetActiveUVMapByName (bpy.types.Operator):
       
    bl_idname = "object.gyaz_utility_batch_set_active_uv_map_by_name"  
    bl_label = "Batch Set Active UV Map by Name"
    bl_description = "Set uv map active on all selected objects by the name of active object's active uv map"
    
    for_render = BoolProperty (default=False)

    #operator function
    def execute(self, context):
        scene = bpy.context.scene
        object = bpy.context.object
        selected_objects = bpy.context.selected_objects
        
        uvmaps = get_uv_maps (object.data)
        if len (uvmaps) > 0:
            active_uv_map_index = uvmaps.active_index
            active_uv_map_name = uvmaps[active_uv_map_index].name
            
            for obj in selected_objects:
                if obj.type == 'MESH':
                    uv_maps = get_uv_maps (obj.data)
                    if len (uv_maps) > 0:
                        for index, uv_map in enumerate(uv_maps):
                            if uv_map.name == active_uv_map_name:
                                if not self.for_render:
                                    uv_maps.active_index = index
                                else:
                                    uv_maps[active_uv_map_name].active_render = True
                              
        return {'FINISHED'}        
        
        
# Panel Overrides:

# uvmaps
class UL_GYAZ_UVMaps (UIList):
    def draw_item (self, context, layout, data, set, icon, active_data, active_propname, index):
        row = layout.row (align=True)
        owner = context.mesh.gyaz_export
        row.prop (owner, "uv_export", text='', emboss=False, index=index, icon='EXPORT' if owner.uv_export[index] else 'BLANK1')
        row.prop (set, "name", text='', emboss=False)
        row.prop (set, "active_render", text='', emboss=False, icon='RESTRICT_RENDER_OFF' if set.active_render else 'RESTRICT_RENDER_ON')

class Me_GYAZ_UVUtils (Menu):
    
    bl_label = 'UV Utils'
    
    def draw (self, context):
        lay = self.layout
        lay.operator_context = 'INVOKE_REGION_WIN'
        lay.operator (Op_GYAZ_BatchSetActiveUVMapByIndex.bl_idname).for_render=False
        lay.operator (Op_GYAZ_BatchSetActiveUVMapByIndex.bl_idname, text='For Render', icon='RESTRICT_RENDER_OFF').for_render=True
        lay.operator (Op_GYAZ_BatchSetActiveUVMapByName.bl_idname).for_render=False
        lay.operator (Op_GYAZ_BatchSetActiveUVMapByName.bl_idname, text='For Render', icon='RESTRICT_RENDER_OFF').for_render=True
            
class DATA_PT_uv_texture (Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'data'
    bl_label = 'UV Maps'  
    
    # add ui elements here
    def draw (self, context):      
        lay = self.layout
        mesh = bpy.context.mesh
        uv_count = len (mesh.uv_textures)
        row_count = 4 if uv_count > 1 else 2
        row = lay.row ()   
        row.template_list ("UL_GYAZ_UVMaps", "",  # type and unique id
            mesh, "uv_textures",  # pointer to the CollectionProperty
            mesh.uv_textures, "active_index",  # pointer to the active identifier
            rows = row_count, maxrows = row_count)
        col = row.column (align=True)
        col.enabled = True if not context.space_data.use_pin_id else False
        col.operator ('mesh.uv_texture_add', icon='ZOOMIN', text='')
        col.operator ('mesh.uv_texture_remove', icon='ZOOMOUT', text='')
        col.menu ('Me_GYAZ_UVUtils', text='', icon='DOWNARROW_HLT')
        if uv_count > 1:
            col.separator ()
            col.operator (Op_GYAZ_MoveUVMap.bl_idname, text='', icon='TRIA_UP').up = True
            col.operator (Op_GYAZ_MoveUVMap.bl_idname, text='', icon='TRIA_DOWN').up = False
    
    #when the buttons should show up    
    @classmethod
    def poll(cls, context):
        ob = bpy.context.object       
        return ob.type == 'MESH'
 
      
# vertex colors
class UL_GYAZ_VertexColorList (UIList):
    def draw_item (self, context, layout, data, set, icon, active_data, active_propname, index):
        row = layout.row (align=True)
        owner = context.mesh.gyaz_export
        row.prop (owner, "vert_color_export", text='', emboss=False, index=index, icon='EXPORT' if owner.vert_color_export[index] else 'BLANK1')
        row.prop (set, "name", text='', emboss=False)
        row.prop (set, "active_render", text='', emboss=False, icon='RESTRICT_RENDER_OFF' if set.active_render else 'RESTRICT_RENDER_ON')
            
class DATA_PT_vertex_colors (Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'data'
    bl_label = 'Vertex Colors'  
    
    # add ui elements here
    def draw (self, context):      
        lay = self.layout
        mesh = bpy.context.mesh
        row = lay.row ()   
        row.template_list ("UL_GYAZ_VertexColorList", "",  # type and unique id
            mesh, "vertex_colors",  # pointer to the CollectionProperty
            mesh.vertex_colors, "active_index",  # pointer to the active identifier
            rows = 1, maxrows = 1)
        col = row.column (align=True)
        col.enabled = True if not context.space_data.use_pin_id else False
        col.operator ('mesh.vertex_color_add', icon='ZOOMIN', text='')
        col.operator ('mesh.vertex_color_remove', icon='ZOOMOUT', text='')
    
    #when the buttons should show up    
    @classmethod
    def poll(cls, context):
        ob = bpy.context.object       
        return ob.type == 'MESH'
    
# mesh props
class PG_GYAZ_Export_MeshProps (PropertyGroup):
    uv_export = BoolVectorProperty (size=8, default=[True]*8, description='Whether the GYAZ Exporter keeps this uv map')
    vert_color_export = BoolVectorProperty (size=8, default=(True, False, False, False, False, False, False, False), description='Whether the GYAZ Exporter keeps this vertex color layer')
    merge_materials = BoolProperty (name='Merge Materials On Export', default=False, description='Whether the GYAZ Exporter merges materials on export or keeps them as they are')
    atlas_name = StringProperty (name='Atlas', default='Atlas', description='Name of the merged material')

#######################################################
#######################################################

# REGISTER

def register():
    
    # props
    bpy.utils.register_class (PG_GYAZ_Export_ExtraBoneItem)
    bpy.utils.register_class (PG_GYAZ_Export_ExportBoneItem)
    bpy.utils.register_class (PG_GYAZ_export_ExportActions)
    bpy.utils.register_class (PG_GYAZ_ExportProps)
    bpy.utils.register_class (PG_GYAZ_Export_ObjectProps)
    bpy.utils.register_class (PG_GYAZ_Export_MeshProps)
    Scene.gyaz_export = PointerProperty (type=PG_GYAZ_ExportProps)
    Object.gyaz_export = PointerProperty (type=PG_GYAZ_Export_ObjectProps)
    Mesh.gyaz_export = PointerProperty (type=PG_GYAZ_Export_MeshProps)

    # operators
    bpy.utils.register_class (Op_GYAZ_Export_MarkAllSelectedForExport)      
    bpy.utils.register_class (Op_GYAZ_Export_MarkAllSelectedNotForExport)      
    bpy.utils.register_class (Op_GYAZ_Export_MarkAllForExport)      
    bpy.utils.register_class (Op_GYAZ_Export_MarkAllNotForExport)      
    bpy.utils.register_class (Op_GYAZ_Export_SelectFileInWindowsFileExplorer)   
    bpy.utils.register_class (Op_GYAZ_Export_OpenFolderInWindowsFileExplorer)   
    bpy.utils.register_class (Op_GYAZ_Export_PathInfo)    
    bpy.utils.register_class (Op_GYAZ_Export_SavePreset)   
    bpy.utils.register_class (Op_GYAZ_Export_RemovePreset)   
    bpy.utils.register_class (Op_GYAZ_Export_Functions)  
    bpy.utils.register_class (Op_GYAZ_Export_ReadSelectedPoseBones)  
    bpy.utils.register_class (Op_GYAZ_Export_RemoveItemFromExtraBones)  
    bpy.utils.register_class (Op_GYAZ_Export_RemoveItemFromExportBones)   
    bpy.utils.register_class (Op_GYAZ_Export_SetSourceAsActiveBone)  
    bpy.utils.register_class (Op_GYAZ_Export_SetParentAsActiveBone)  
    bpy.utils.register_class (Op_GYAZ_Export_SetNameAsActiveBone)  
    bpy.utils.register_class (Op_GYAZ_Export_MoveExtraBoneItem)
    bpy.utils.register_class (Op_GYAZ_Export_RemoveItemFromActions) 
    bpy.utils.register_class (Op_GYAZ_Export_SetActiveActionToExport)  
    bpy.utils.register_class (Op_GYAZ_Export_SetFilterType)  
    bpy.utils.register_class (Op_GYAZ_Export_Export) 
    
    # ui
    bpy.utils.register_class (UL_GYAZ_ExtraBones)
    bpy.utils.register_class (UL_GYAZ_ExportBones)
    bpy.utils.register_class (UL_GYAZ_ExportActions)
    bpy.utils.register_class (Pa_GYAZ_Export_Bones)  
    bpy.utils.register_class (Pa_GYAZ_Export_Animation)   
    bpy.utils.register_class (Pa_GYAZ_Export)
    bpy.utils.register_class (Pa_GYAZ_Export_Filter)
    bpy.utils.register_class (Pa_GYAZ_Export_Extras)
    
    # merge materials ui
    bpy.types.Cycles_PT_context_material.append (ui_merge_materials)
    
    # uv utils
    bpy.utils.register_class (Op_GYAZ_MoveUVMap)
    bpy.utils.register_class (Op_GYAZ_BatchSetActiveUVMapByIndex)
    bpy.utils.register_class (Op_GYAZ_BatchSetActiveUVMapByName)
    bpy.utils.register_class (Me_GYAZ_UVUtils)
    
    # panel overrides
    bpy.utils.register_class (UL_GYAZ_UVMaps)
    bpy.utils.register_class (DATA_PT_uv_texture)
    bpy.utils.register_class (UL_GYAZ_VertexColorList)
    bpy.utils.register_class (DATA_PT_vertex_colors)
   

def unregister ():

    # props
    bpy.utils.unregister_class (PG_GYAZ_Export_ExtraBoneItem)
    bpy.utils.unregister_class (PG_GYAZ_Export_ExportBoneItem)
    bpy.utils.unregister_class (PG_GYAZ_export_ExportActions)
    bpy.utils.unregister_class (PG_GYAZ_ExportProps)
    bpy.utils.unregister_class (PG_GYAZ_Export_ObjectProps)
    bpy.utils.unregister_class (PG_GYAZ_Export_MeshProps)
    del Scene.gyaz_export
    del Object.gyaz_export
    del Mesh.gyaz_export
    
    # operators
    bpy.utils.unregister_class (Op_GYAZ_Export_MarkAllSelectedForExport)      
    bpy.utils.unregister_class (Op_GYAZ_Export_MarkAllSelectedNotForExport)      
    bpy.utils.unregister_class (Op_GYAZ_Export_MarkAllForExport)      
    bpy.utils.unregister_class (Op_GYAZ_Export_MarkAllNotForExport)    
    bpy.utils.unregister_class (Op_GYAZ_Export_SelectFileInWindowsFileExplorer)
    bpy.utils.unregister_class (Op_GYAZ_Export_OpenFolderInWindowsFileExplorer)
    bpy.utils.unregister_class (Op_GYAZ_Export_PathInfo)
    bpy.utils.unregister_class (Op_GYAZ_Export_SavePreset)
    bpy.utils.unregister_class (Op_GYAZ_Export_RemovePreset)
    bpy.utils.unregister_class (Op_GYAZ_Export_Functions)  
    bpy.utils.unregister_class (Op_GYAZ_Export_ReadSelectedPoseBones)  
    bpy.utils.unregister_class (Op_GYAZ_Export_RemoveItemFromExtraBones)  
    bpy.utils.unregister_class (Op_GYAZ_Export_RemoveItemFromExportBones)  
    bpy.utils.unregister_class (Op_GYAZ_Export_SetSourceAsActiveBone)  
    bpy.utils.unregister_class (Op_GYAZ_Export_SetParentAsActiveBone) 
    bpy.utils.unregister_class (Op_GYAZ_Export_SetNameAsActiveBone) 
    bpy.utils.unregister_class (Op_GYAZ_Export_MoveExtraBoneItem) 
    bpy.utils.unregister_class (Op_GYAZ_Export_RemoveItemFromActions)  
    bpy.utils.unregister_class (Op_GYAZ_Export_SetActiveActionToExport)  
    bpy.utils.unregister_class (Op_GYAZ_Export_SetFilterType)  
    bpy.utils.unregister_class (Op_GYAZ_Export_Export)    
    
    # ui
    bpy.utils.unregister_class (UL_GYAZ_ExtraBones)
    bpy.utils.unregister_class (UL_GYAZ_ExportBones)
    bpy.utils.unregister_class (UL_GYAZ_ExportActions)
    bpy.utils.unregister_class (Pa_GYAZ_Export_Bones)
    bpy.utils.unregister_class (Pa_GYAZ_Export_Animation)
    bpy.utils.unregister_class (Pa_GYAZ_Export)
    bpy.utils.unregister_class (Pa_GYAZ_Export_Filter)
    bpy.utils.unregister_class (Pa_GYAZ_Export_Extras)
    
    # merge materials ui
    bpy.types.Cycles_PT_context_material.remove (ui_merge_materials)
    
    # uv utils
    bpy.utils.unregister_class (Op_GYAZ_MoveUVMap)
    bpy.utils.unregister_class (Op_GYAZ_BatchSetActiveUVMapByIndex)
    bpy.utils.unregister_class (Op_GYAZ_BatchSetActiveUVMapByName)
    bpy.utils.unregister_class (Me_GYAZ_UVUtils)
    
    # panel overrides (the actual overrides can't be unregistered)
    # Blender needs to be restarted for the old panels to exist again
    bpy.utils.unregister_class (UL_GYAZ_UVMaps)
    bpy.utils.unregister_class (UL_GYAZ_VertexColorList)

  
if __name__ == "__main__":   
    register()   