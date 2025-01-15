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


import bpy
from bpy.types import PropertyGroup, Scene, Object
from bpy.props import BoolProperty, StringProperty, EnumProperty, IntProperty, FloatProperty, CollectionProperty, PointerProperty


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
            setattr (scene.gyaz_export, 'root_bone_name', preset.root_bone_name)
            setattr (scene.gyaz_export, 'export_all_bones', preset.export_all_bones)
            setattr (scene.gyaz_export, 'constraint_extra_bones', preset.constraint_extra_bones)
            setattr (scene.gyaz_export, 'rename_vert_groups_to_extra_bones', preset.rename_vert_groups_to_extra_bones)
            
     
    def get_preset_names (self, context):
        return [(preset.preset_name, preset.preset_name, "") for preset in prefs.bone_presets]
         
    active_preset: EnumProperty (name = 'Active Preset', items = get_preset_names, default = None, update=load_active_preset)    

    root_mode: EnumProperty (name='Root Mode', 
                             items=(('BONE', 'Bone', ''), 
                                    ('OBJECT', 'Object', ''))
                                    , 
                             default='BONE', 
                             description='Root Mode. Bone: top of hierarchy is the specified bone,' \
                                       + 'Object: top of hierarchy is the object (renamed as "root") and the root bone, if found, is removed.'
                             )
    
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
            ('ACTIVE', 'ACTIVE ACTION', ""),
            ('ALL', 'ALL ACTIONS', ""),
            ('BY_NAME', 'ACTIONS BY NAME', ""),
            ('SCENE', 'SCENE ANIMATION', "")
            ),
        default='ACTIVE')
    
    actions: CollectionProperty (type=PG_GYAZ_export_ExportActions)
    actions_active_index: IntProperty (default=0)

    skeletal_mesh_limit_bone_influences: EnumProperty (name='Bone Weights', description="Limit bone influences by vertex",
        items=(
            ('2', 'Bone Weights: 2', ''),
            ('4', 'Bone Weights: 4', ''),
            ('8', 'Bone Weights: 8', ''),
            ('unlimited', 'Bone Weights: unlimited', '')
            ),
        default=prefs.skeletal_mesh_limit_bone_influences)
        
    root_bone_name: StringProperty(name='Root Bone Name', default='root')
    
    export_folder: StringProperty (default='', subtype='DIR_PATH', name='Export folder')
    
    use_skeleton_name_override: BoolProperty (default=False, description="Override the skeleton's name in the export file's name, otherwise use the armature object's name")
    
    skeleton_name_override: StringProperty (default='', description="Skeleton name override")
    
    global_anim_name: StringProperty (name='', default='')

    static_mesh_pack_name: StringProperty (default='', name='', description="Pack name")
    
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

    static_mesh_pack_objects: BoolProperty (name='Pack Objects', default=False, description='Whether to pack all objects into one file or export them as separate files. If true, sockets will not be imported in Unreal')
    skeletal_mesh_pack_objects: BoolProperty (name='Pack Objects', default=False, description='Whether to pack all objects into one file (name of the armature) or export them as separate files (names of mesh children)')
    rigid_anim_pack_objects: BoolProperty (name='Pack Objects', default=False, description="Whether to pack all objects into one file or export them as separate files. If checked, 'Use Scene Start End' is forced, 'Export Cubes' is not an option")
    pack_actions: BoolProperty (name='Pack Actions', default=False, description='Whether to pack all actions into one file or export them as separate files')

    static_mesh_clear_transforms: BoolProperty (default=True, name='Clear Transforms', description="Clear object transforms")
    skeletal_clear_transforms: BoolProperty (default=True, name='Clear Transforms', description="Clear object transforms. Armature transformation will always be cleared if root motion is calculated from a bone")
    
    static_mesh_gather_from_collection: BoolProperty (default=False, name='Active Collection', description="Gather objects from the active object's collection")
    rigid_anim_gather_from_collection: BoolProperty (default=False, name='Active Collection', description="Gather objects from the active object's collection")
    
    static_mesh_gather_nested: BoolProperty (default=True, name='Nested Collections', description="If 'Gather from Collection', also gather objects from nested collections")
    rigid_anim_gather_nested: BoolProperty (default=True, name='Nested Collections', description="If 'Gather from Collection', also gather objects from nested collections")
    
    texture_format_mode: EnumProperty(
        name='Texture Format',
        items=(
            ('KEEP_IF_ANY', "Keep", ""),
            ('ALWAYS_OVERRIDE', "Override", "")
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
    
    export_sockets: BoolProperty (default=True, name='Sockets', description='Sockets are empty objects parented to the object and only work if a file only contains one object. Scale is ignored. Prefix: SOCKET_, Example: Object --> SOCKET_anything. Sockets are gathered automatically and should not be selected')
    
    export_lods: BoolProperty (default=True, name='LODs', description='Suffix: Obj or Obj_LOD0 --> Obj_LOD1, Obj_LOD2. LODs are gathered automatically and should not be selected. Only static mesh LODs are exported')
    
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
    
    static_mesh_vcolors: BoolProperty (name='Color Attributes', default=True)
    skeletal_mesh_vcolors: BoolProperty (name='Color Attributes', default=True)
    rigid_anim_vcolors: BoolProperty (name='Color Attributes', default=True)
    
    skeletal_shapes: BoolProperty (name='Shape Keys', default=True, description="Not exported, if mesh has modifiers")
    rigid_anim_shapes: BoolProperty (name='Shape Keys', default=True, description="Not exported, if mesh has modifiers")
    
    path_to_last_export: StringProperty (name='path to last export', default='')
    
    primary_bone_axis: EnumProperty (name='',
        items=(
            ('X', 'Primary Bone Axis: X', ''),
            ('Y', 'Primary Bone Axis: Y', ''),
            ('Z', 'Primary Bone Axis: Z', ''),
            ('-X', 'Primary Bone Axis: -X', ''),
            ('-Y', 'Primary Bone Axis: -Y', ''),
            ('-Z', 'Primary Bone Axis: -Z', '')),
        default=prefs.primary_bone_axis)
        
    secondary_bone_axis: EnumProperty (name='',
        items=(
            ('X', 'Secondary Bone Axis: X', ''),
            ('Y', 'Secondary Bone Axis: Y', ''),
            ('Z', 'Secondary Bone Axis: Z', ''),
            ('-X', 'Secondary Bone Axis: -X', ''),
            ('-Y', 'Secondary Bone Axis: -Y', ''),
            ('-Z', 'Secondary Bone Axis: -Z', '')),
        default=prefs.secondary_bone_axis)

    collision_use_selection: BoolProperty(name="Use Selection", description="Add collision around selected vertices, otherwise around the entire object")

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