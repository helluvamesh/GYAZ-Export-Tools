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


import bpy, os
from bpy.types import PropertyGroup, UIList, Scene, Object, Mesh
from bpy.props import *


# object props
class PG_GYAZ_Export_ObjectProps (PropertyGroup):    
    export: BoolProperty (name='Export Mesh', default=True)


# extra bone            
class PG_GYAZ_Export_ExtraBoneItem (PropertyGroup):
    name: StringProperty (name='', description="Name of new bone")
    source: StringProperty (name='', description="Create new bone by duplicating this bone")
    parent: StringProperty (name='', description="Parent new bone to this bone")
    

# export bone        
class PG_GYAZ_Export_ExportBoneItem (PropertyGroup):
    name: StringProperty (name='', description="Name of bone to export")
    

prefs = bpy.context.preferences.addons[__package__].preferences


# actions to export
class PG_GYAZ_export_ExportActions(PropertyGroup):
    name: StringProperty (description='Name of action to import', default='')
    

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
        
        if preset is not None:
            
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
         
    active_preset: EnumProperty (name = 'Active Preset', items = get_preset_names, default = None, update=load_active_preset)    
    
    root_mode: EnumProperty (name='Root', items=(('BONE', 'Bone: root', ''), ('OBJECT', 'Object', '')), default='OBJECT', description='Root Mode. Bone: top of hierarchy is the bone called "root", Object: top of hierarchy is the object (renamed as "root") and the root bone, if found, is removed.')
    
    extra_bones: CollectionProperty (type=PG_GYAZ_Export_ExtraBoneItem)
    
    constraint_extra_bones: BoolProperty (name='Constraint To Source', default=False)
    rename_vert_groups_to_extra_bones: BoolProperty (name='Rename Vert Groups', default=False)
    extra_bones_long_rows: BoolProperty (name='Long Rows', default=False)
    
    export_bones: CollectionProperty (type=PG_GYAZ_Export_ExportBoneItem)
    extra_bones_active_index: IntProperty (default=0)
    export_all_bones: BoolProperty (name='All Bones', default=True)
    export_bones_active_index: IntProperty (default=0)

    action_export_mode: EnumProperty (name='Export Actions',
        items=(
            ('ACTIVE', 'ACTIVE', ""),
            ('ALL', 'ALL', ""),
            ('BY_NAME', 'BY NAME', "")
            ),
        default='ACTIVE')
    
    actions: CollectionProperty (type=PG_GYAZ_export_ExportActions)
    actions_active_index: IntProperty (default=0)

    skeletal_mesh_limit_bone_influences: EnumProperty (name='Max Bone Inflences', description="Limit bone influences by vertex",
        items=(
            ('1', '1 Bone Weight / Vertex', ''),
            ('2', '2 Bone Weights / Vertex', ''),
            ('4', '4 Bone Weights / Vertex', ''),
            ('8', '8 Bone Weights / Vertex', ''),
            ('unlimited', 'Unlimited Bone Weights / Vertex', '')
            ),
        default=prefs.skeletal_mesh_limit_bone_influences)
    
    use_scene_start_end: BoolProperty (name='Use Scene Start End', default=False, description="If False, frame range will be set according to first and last keyframes of the action")

    export_folder_mode: EnumProperty (
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
    
    export_folder: StringProperty (default='', subtype='DIR_PATH', update=absolute_path__export_folder)
    
    relative_folder_name: StringProperty (default='assets', name='Folder', description="Name of relative folder")    
    
    use_anim_object_name_override: BoolProperty (name='Override Object Name', default=False, description="Override the object's name in exported skeletal animations: AnimationPrefix_ObjectName_ActionName")
    
    anim_object_name_override: StringProperty (name='', default='')
    
    static_mesh_pack_name: StringProperty (default='', name='', description="Pack name")
    skeletal_mesh_pack_name: StringProperty (default='', name='', description="Pack name")
    
    rigid_anim_pack_name: StringProperty (default='', name='', description="Pack's name")
    
    rigid_anim_name: StringProperty (default='', name='', description="Name of the animation")
    
    rigid_anim_cubes: BoolProperty (name='Export Cubes', default=False, description="Replace mesh objects' data with a simple cube")
    
    exporter: EnumProperty (name='Exporter',
        items=(
            ('FBX', 'Filmbox - .fbx', ''),
            ),
        default='FBX')
        
    rigid_asset_type: EnumProperty (name='Asset Type',
        items=(
            ('STATIC_MESHES', 'STATIC MESHES', "", 'MESH_CUBE', 0),
            ('RIGID_ANIMATIONS', 'RIGID ANIMATIONS', "", 'PREFERENCES', 3)
            ),
        default='STATIC_MESHES')
        
    skeletal_asset_type: EnumProperty (name='Asset Type',
        items=(
            ('SKELETAL_MESHES', 'SKELETAL MESHES', "", 'MOD_ARMATURE', 1),
            ('ANIMATIONS', 'SKELETAL ANIMATIONS', "", 'ARMATURE_DATA', 2)
            ),
        default='SKELETAL_MESHES')

    static_mesh_pack_objects: BoolProperty (name='Pack Objects', default=False, description='Whether to pack all objects into one file or export them as separate files. If true, sockets will not be exported')
    skeletal_mesh_pack_objects: BoolProperty (name='Pack Objects', default=False, description='Whether to pack all objects into one file or export them as separate files')
    rigid_anim_pack_objects: BoolProperty (name='Pack Objects', default=False, description="Whether to pack all objects into one file or export them as separate files. If checked, 'Use Scene Start End' is forced, 'Export Cubes' is not an option")
        
    use_static_mesh_organizing_folder: BoolProperty (name='Organizing Folder', default=False, description="Export objects into separate folders with the object's name. If 'Pack Objects' is true, export objects into a folder with the pack's name")
    use_rigid_anim_organizing_folder: BoolProperty (name='Organizing Folder', default=False, description="Export objects into separate folders with the object's name. If 'Pack Objects' is true, export objects into a folder with the pack's name")
    use_skeletal_organizing_folder: BoolProperty (name='Organizing Folder', default=False, description="Add an extra folder with the armature's name")

    static_mesh_clear_transforms: BoolProperty (default=True, name='Clear Transforms', description="Clear object transforms")
    skeletal_clear_transforms: BoolProperty (default=True, name='Clear Transforms', description="Clear object transforms. Armature transformation will always be cleared if root motion is calculated from a bone")
   
    texture_format_mode: EnumProperty(
        name='Texture Format',
        items=(
            ('KEEP_IF_ANY', "Keep Format", ""),
            ('ALWAYS_OVERRIDE', "Override Format", "")
            ),
        default=prefs.texture_format_mode)
        
    texture_format_override: EnumProperty(
        name='Override',
        items=(
            ('TARGA', 'TGA', ''),
            ('PNG', 'PNG', ''),
            ('TIFF', 'TIF', '')
            ),
        default=prefs.texture_format_override)
   
    texture_compression: FloatProperty(name='Texture Compression', default=prefs.texture_compression, min=0, max=1)
        
    export_textures: BoolProperty (default=False, name='Textures')
    
    export_only_textures: BoolProperty (default=False, name='Textures Only', description='Export only textures, no meshes')
    
    export_collision: BoolProperty (default=True, name='Collision', description='Prefixes: UBX (box), USP (sphere), UCP (capsule), UCX (convex). Example: Object --> UBX_Object, UBX_Object.001. Collision (mesh) objects are gathered automatically and should not be selected')
    
    export_sockets: BoolProperty (default=True, name='Sockets', description='Sockets need to be parented to the object and only work if a file only contains one object. Prefix: SOCKET_, Example: Object --> SOCKET_anything. Socket (armature) objects are gathered automatically and should not be selected. Scale is ignored')
    
    export_lods: BoolProperty (default=True, name='LODs', description='Suffix: Obj --> Obj_LOD1, Obj_LOD2 (LOD0 should not have a suffix). LODs are gathered automatically and should not be selected')
    
    ignore_missing_second_uv_map: BoolProperty (default=False, name='Ignore 2nd UV Check')
    
    show_options: BoolProperty (name='Show Options', default=True)
    
    use_prefixes: BoolProperty (name='Add Prefixes', default=prefs.use_prefixes, description="Add prefixes to asset names. Set up prefixes in User Preferences>Addons") 
    add_end_bones: BoolProperty (name='Add End Bones', default=prefs.add_end_bones, description='Add a bone to the end of bone chains')
    check_for_second_uv_map: BoolProperty (name='Check for 2nd UV Map', default=prefs.check_for_second_uv_map, description='Check for 2nd uv map when exporting static meshes')
    detect_mirrored_uvs: BoolProperty (name='Detect Mirrored UVs', default=prefs.detect_mirrored_uvs, description='Look for mirrored uvs that cause incorrect shading. Slow with high-poly meshes with multiple uv maps')
    
    mesh_smoothing: EnumProperty (name='Smoothing',
        items=(
            ('OFF', 'Normals Only', ''),
            ('FACE', 'Face', ''),
            ('EDGE', 'Edge', '')
            ),
        default=prefs.mesh_smoothing,
        description='Mesh smoothing data')
        
    allow_quads: BoolProperty (name='Allow Quads', default=prefs.allow_quads, description='Allow quads. Ngons are never allowed')

    filter_string: StringProperty (default='')
    
    filter_type: EnumProperty (items=(('START', 'START', ''), ('IN', 'IN', ''), ('END', 'END', '')), default='IN')
    
    static_mesh_vcolors: BoolProperty (name='Vertex Colors', default=True)
    skeletal_mesh_vcolors: BoolProperty (name='Vertex Colors', default=True)
    rigid_anim_vcolors: BoolProperty (name='Vertex Colors', default=True)
    
    skeletal_shapes: BoolProperty (name='Shape Keys', default=True)
    rigid_anim_shapes: BoolProperty (name='Shape Keys', default=True)
    
    path_to_last_export: StringProperty (name='path to last export', default='')
    
    # debug
    show_debug_props: BoolProperty (name='Developer', default=False, description="Show properties for debugging")
    
    dont_reload_scene: BoolProperty (name="Don't Reload Scene", default=False, description="Debugging, whether not to reload the scene saved before the export")


def register():
    bpy.utils.register_class (PG_GYAZ_Export_ExtraBoneItem)
    bpy.utils.register_class (PG_GYAZ_Export_ExportBoneItem)
    bpy.utils.register_class (PG_GYAZ_export_ExportActions)
    bpy.utils.register_class (PG_GYAZ_ExportProps)
    bpy.utils.register_class (PG_GYAZ_Export_ObjectProps)
    Scene.gyaz_export = PointerProperty (type=PG_GYAZ_ExportProps)
    Object.gyaz_export = PointerProperty (type=PG_GYAZ_Export_ObjectProps)
    
    
def unregister():
    bpy.utils.unregister_class (PG_GYAZ_Export_ExtraBoneItem)
    bpy.utils.unregister_class (PG_GYAZ_Export_ExportBoneItem)
    bpy.utils.unregister_class (PG_GYAZ_export_ExportActions)
    bpy.utils.unregister_class (PG_GYAZ_ExportProps)
    bpy.utils.unregister_class (PG_GYAZ_Export_ObjectProps)
    del Scene.gyaz_export
    del Object.gyaz_export
    
    
if __name__ == "__main__":   
    register()  