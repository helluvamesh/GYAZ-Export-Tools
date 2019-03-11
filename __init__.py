# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
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

bl_info = {   
 "name": "GYAZ Export Tools",   
 "author": "Andras Gyalog",
 "version": ('34'),
 "blender": (2, 79, 0),   
 "location": "View3d > Toolshelf > Export FBX",   
 "description": "Extension of Blender's FBX Exporter for exporting static meshes, skeletal meshes and animations",
 "warning": "",   
 "wiki_url": "",   
 "tracker_url": "",   
 "category": "Import-Export"}



import bpy
from bpy.types import AddonPreferences, PropertyGroup
from bpy.props import *


#extra bone            
class GYAZ_Export_Preset_ExtraBoneItem (PropertyGroup):
    name = StringProperty (name='', description="Name of new bone")
    source = StringProperty (name='', description="Create new bone by duplicating this bone")
    parent = StringProperty (name='', description="Parent new bone to this bone")                        
bpy.utils.register_class (GYAZ_Export_Preset_ExtraBoneItem)

#export bone        
class GYAZ_Export_Preset_ExportBoneItem (PropertyGroup):
    name = StringProperty (name='', description="Name of bone to export")                                            
bpy.utils.register_class (GYAZ_Export_Preset_ExportBoneItem)

#preset
class GYAZ_Export_BonePresetItem (PropertyGroup):
    preset_name = StringProperty (default='')
    root_mode = EnumProperty (items=(('BONE', 'Bone: root', ''), ('OBJECT', 'Object', '')), default='BONE')
    extra_bones = CollectionProperty(type=GYAZ_Export_Preset_ExtraBoneItem)
    export_bones = CollectionProperty(type=GYAZ_Export_Preset_ExportBoneItem)
    export_all_bones = BoolProperty (default=True)      
    constraint_extra_bones = BoolProperty (default=False)      
    rename_vert_groups_to_extra_bones = BoolProperty (default=False)      
bpy.utils.register_class (GYAZ_Export_BonePresetItem)    
    

class GYAZ_Export_Preferences (AddonPreferences):
    # this must match the addon name, use '__package__'
    # when defining this in a submodule of a python package.
    bl_idname = __name__

    bone_presets = CollectionProperty (type=GYAZ_Export_BonePresetItem)
    
    static_mesh_prefix = StringProperty (name='Static Mesh Prefix', default='SM_')
    skeletal_mesh_prefix = StringProperty (name='Skeletal Mesh Prefix', default='SK_')
    material_prefix = StringProperty (name='Material Prefix', default='M_')
    texture_prefix = StringProperty (name='Texture Prefix', default='T_')
    animation_prefix = StringProperty (name='Animation Prefix', default='A_')
    
    texture_format_mode = EnumProperty(
        name='Texture Format',
        items=(
            ('KEEP_IF_ANY', "Keep", ""),
            ('ALWAYS_OVERRIDE', "Override", "")
            ),
        default='ALWAYS_OVERRIDE')
        
    texture_format_override = EnumProperty(
        name='Override',
        items=(
            ('TARGA', 'TGA', ''),
            ('PNG', 'PNG', ''),
            ('TIFF', 'TIF', '')
            ),
        default='PNG')
        
    texture_compression = FloatProperty(name='Texture Compression', default=0.15, min=0, max=1)
        
    use_prefixes = BoolProperty (name='Add Prefixes', default=True, description="Add prefixes to asset names. Set up prefixes in User Preferences>Addons") 
    remove_boneless_vert_weights = BoolProperty (name='Clean Vert Groups', default=True, description="Remove vertex groups without a bone with the same name")
    add_end_bones = BoolProperty (name='Add End Bones', default=False, description='Add a bone to the end of bone chains')
    check_for_second_uv_map = BoolProperty (name='Check for 2nd UV Map', default=False, description='Check for 2nd uv map when exporting static meshes')
    detect_mirrored_uvs = BoolProperty (name='Detect Mirrored UVs', default=True, description='Look for mirrored uvs that cause incorrect shading. Slow with high-poly meshes with multiple uv maps')
        
    mesh_smoothing = EnumProperty (name='Smoothing',
        items=(
            ('OFF', 'Normals Only', ''),
            ('FACE', 'Face', ''),
            ('EDGE', 'Edge', '')
            ),
        default='FACE',
        description='Mesh smoothing data')
        
    allow_quads = BoolProperty (name='Allow Quads', default=False, description='Allow quads. Ngons are never allowed')
    
    skeletal_mesh_limit_bone_influences = EnumProperty (name='Max Bone Inflences', description="Limit bone influences by vertex",
    items=(
        ('1', '1 weight/vertex', ''),
        ('2', '2 weights/vertex', ''),
        ('4', '4 weights/vertex', ''),
        ('8', '8 weights/vertex', ''),
        ('unlimited', 'unlimited', '')
        ),
    default='4')
    
    texture_folder_name = StringProperty (name='Textures Folder', default='Textures')
    anim_folder_name = StringProperty (name='Animations Folder', default='Animations')
    
    def draw (self, context):
        lay = self.layout 
        lay.prop (self, "use_prefixes")
        
        col = lay.column (align=True)
        col.prop (self, "static_mesh_prefix")
        col.prop (self, "skeletal_mesh_prefix")
        col.prop (self, "material_prefix")       
        col.prop (self, "texture_prefix")       
        col.prop (self, "animation_prefix")
        
        col = lay.column (align=True)
        col.prop (self, 'texture_folder_name')
        col.prop (self, 'anim_folder_name')
        
        lay.separator ()
        lay.separator ()
        
        row = lay.row ()
        col = row.column ()
        col.prop (self, "texture_format_mode")
        col.prop (self, "texture_format_override")
        col.prop (self, "texture_compression", slider=True)
        col.label ('')
        col.prop (self, "mesh_smoothing")
        col.prop (self, "check_for_second_uv_map")
        col.prop (self, "detect_mirrored_uvs")
        col.prop (self, "allow_quads")
        col.label ('')
        col.prop (self, "add_end_bones")
        col.prop (self, "remove_boneless_vert_weights")
        col.prop (self, "skeletal_mesh_limit_bone_influences")
        col = row.column ()
        col.label ('')
        
        lay.label ('')      


# Registration
def register():
    bpy.utils.register_class(GYAZ_Export_Preferences)


def unregister():
    bpy.utils.unregister_class(GYAZ_Export_Preferences)


register()


 
modulesNames = ['export_tools', 'encode_shape_keys_in_uv_channels']
 
import sys
import importlib

modulesFullNames = []
modulesFullNames_values = []

for currentModuleName in modulesNames:
    modulesFullNames.append ([currentModuleName, __name__+'.'+currentModuleName])
    modulesFullNames_values.append (__name__+'.'+currentModuleName)
 
for currentModuleFullName in modulesFullNames_values:
    if currentModuleFullName in sys.modules:
        importlib.reload(sys.modules[currentModuleFullName])
    else:
        globals()[currentModuleFullName] = importlib.import_module(currentModuleFullName)
        setattr(globals()[currentModuleFullName], 'modulesNames', modulesFullNames)
 
def register():
    for currentModuleName in modulesFullNames_values:
        if currentModuleName in sys.modules:
            if hasattr(sys.modules[currentModuleName], 'register'):
                sys.modules[currentModuleName].register()
 
def unregister():
    for currentModuleName in modulesFullNames_values:
        if currentModuleName in sys.modules:
            if hasattr(sys.modules[currentModuleName], 'unregister'):
                sys.modules[currentModuleName].unregister()
 
if __name__ == "__main__":
    register()