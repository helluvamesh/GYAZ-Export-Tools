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
from bpy.types import Panel, Operator, UIList


class UI_UL_GYAZ_ExtraBones (UIList):
    def draw_item (self, context, layout, data, set, icon, active_data, active_propname, index):
        icon = 'BONE_DATA' if bpy.context.active_object.data.bones.get (set.source) is not None else 'ERROR'
        row = layout.row (align=True)
        row.prop (set, "name", icon=icon, emboss=False)
        if bpy.context.scene.gyaz_export.extra_bones_long_rows:
            row.separator ()
            row.prop (set, "parent", text='', icon='NODETREE', emboss=False)
            row.operator ('object.gyaz_export_set_parent_as_active_bone', text='', icon='EYEDROPPER', emboss=False).ui_index = index
            row.separator ()
            row.prop_search (set, "source", bpy.context.active_object.data, "bones", icon='GROUP_BONE')
            row.operator ('object.gyaz_export_set_source_as_active_bone', text='', icon='EYEDROPPER').ui_index = index


class UI_UL_GYAZ_ExportBones (UIList):
    def draw_item (self, context, layout, data, set, icon, active_data, active_propname, index):
        row = layout.row (align=True)
        row.prop_search (set, "name", bpy.context.active_object.data, "bones")
        row.operator ('object.gyaz_export_set_name_as_active_bone', text='', icon='EYEDROPPER').ui_index = index
        row.operator ('object.gyaz_export_remove_item_from_export_bones', text='', icon='REMOVE').ui_index = index                  


class UI_UL_GYAZ_ExportActions (UIList):
    def draw_item (self, context, layout, data, set, icon, active_data, active_propname, index):
        row = layout.row (align=True)
        row.prop_search (set, "name", bpy.data, "actions", text='')          
        row.operator ('object.gyaz_export_remove_item_from_actions', text='', icon='REMOVE').ui_index=index           


class SCENE_PT_GYAZ_Export_Bones (Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "FBX"
    bl_label = 'Export Bones'
    
    # add ui elements here
    def draw (self, context):
        
        if bpy.context.active_object.type == 'ARMATURE':
            
            scene = bpy.context.scene
            rig = bpy.context.active_object      
            lay = self.layout
            owner = scene.gyaz_export
            
            col = lay.column (align=True)
            col.label (text="Rig Mode:")
            col.row().prop (owner, "rig_mode", expand=True)
            if (owner.rig_mode == "BUILD"):
                col.label (text='Bone Presets:')
                row = col.row (align=True)
                row.prop (owner, "active_preset", text='')
                row.operator ('object.gyaz_export_save_preset', text='', icon='ADD')
                row.operator ('object.gyaz_export_remove_preset', text='', icon='REMOVE')
                
                col = lay.column (align=True)
                col.use_property_split = True
                col.use_property_decorate = False
                col.prop (owner, 'root_mode')
                if owner.root_mode == 'BONE':
                    col.prop_search (owner, 'root_bone_name', rig.data, "bones", icon='BONE_DATA', text='Bone')
                col = lay.column (align=True)
                row = col.row (align=True)
                row.label (text='Extra Bones:')
                row.prop (owner, "extra_bones")
                if len (owner.extra_bones) > 0:
                    col.prop (owner, 'constraint_extra_bones')
                    col.prop (owner, 'rename_vert_groups_to_extra_bones')
                    col.prop (owner, 'extra_bones_long_rows')
                extra_bones = owner.extra_bones
                col = lay.column (align=True)
                row = col.row (align=True)
                row.operator ('object.gyaz_export_functions', text='', icon='ADD').ui_mode = 'ADD_TO_EXTRA_BONES'
                row.operator ('object.gyaz_export_remove_item_from_extra_bones', text='', icon='REMOVE')
                row.separator ()
                op = row.operator ('object.gyaz_export_move_extra_bone_item', text='', icon='TRIA_UP').mode = 'UP'
                op = row.operator ('object.gyaz_export_move_extra_bone_item', text='', icon='TRIA_DOWN').mode = 'DOWN'
                row.separator ()
                row.operator ('object.gyaz_export_functions', text='', icon='X').ui_mode = 'REMOVE_ALL_FROM_EXTRA_BONES'
                row.separator ()
                row.operator ('object.gyaz_export_read_selected_pose_bones', text='', icon='EYEDROPPER').mode='EXTRA_BONES'
                if len (owner.extra_bones) > 0:
                    index = owner.extra_bones_active_index
                    item = extra_bones[index]
                    if len (owner.extra_bones) > 0:
                        lay.template_list ("UI_UL_GYAZ_ExtraBones", "",  # type and unique id
                            owner, "extra_bones",  # pointer to the CollectionProperty
                            owner, "extra_bones_active_index",  # pointer to the active identifier
                            rows = 1, maxrows = 1)
                        col = lay.column (align=True)
                        if not owner.extra_bones_long_rows:
                            col.label (text='Source, Parent:')
                            col = col.column (align=True)
                            row = col.row (align=True)
                            row.prop_search (item, "source", rig.data, "bones", icon='GROUP_BONE')
                            row.operator ('object.gyaz_export_set_source_as_active_bone', text='', icon='EYEDROPPER').ui_index = index
                            row = col.row (align=True)
                            row.prop (item, "parent", text='', icon='NODETREE')
                            row.operator ('object.gyaz_export_set_parent_as_active_bone', text='', icon='EYEDROPPER').ui_index = index
                        else:
                            col.label (text='(New Name, Parent, Source)')          

                col = lay.column (align=True)            
                row = col.row (align=True)
                row.label (text='Export Bones:')
                row.prop (owner, "export_bones")
                col.prop (owner, "export_all_bones")
                col.separator ()
                if not owner.export_all_bones:
                    row = col.row (align=True)
                    row.operator ('object.gyaz_export_functions', text='', icon='ADD').ui_mode = 'ADD_TO_EXPORT_BONES'
                    row.operator ('object.gyaz_export_functions', text='', icon='X').ui_mode = 'REMOVE_ALL_FROM_EXPORT_BONES'
                    row.separator ()
                    row.operator ('object.gyaz_export_read_selected_pose_bones', text='', icon='EYEDROPPER').mode='EXPORT_BONES'
                    row.separator ()
                    lay.template_list ("UI_UL_GYAZ_ExportBones", "",  # type and unique id
                        owner, "export_bones",  # pointer to the CollectionProperty
                        owner, "export_bones_active_index",  # pointer to the active identifier
                        rows = 1, maxrows = 1)        

    # when the buttons should show up    
    @classmethod
    def poll(cls, context):
        mode = bpy.context.mode
        obj = bpy.context.active_object
        good_to_go = False
        if obj is not None:
            if obj.type == 'ARMATURE':
                if mode == 'OBJECT' or mode == 'POSE':
                    good_to_go = True
        if good_to_go:
            return True
        else:
            return False


class SCENE_PT_GYAZ_Export_Animation (Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "FBX"
    bl_label = 'Export Animations'  
    
    # add ui elements here
    def draw (self, context):
        
        scene = bpy.context.scene
        owner = scene.gyaz_export        
        lay = self.layout
        
        lay.column().prop (owner, "action_export_mode", expand=True)        
        if owner.action_export_mode == 'BY_NAME':
            row = lay.row (align=True)
            row.operator ('object.gyaz_export_functions', text='', icon='ADD').ui_mode='ADD_TO_EXPORT_ACTIONS'
            row.operator ('object.gyaz_export_functions', text='', icon='X').ui_mode='REMOVE_ALL_FROM_EXPORT_ACTIONS'
            lay.template_list ("UI_UL_GYAZ_ExportActions", "",  # type and unique id
                owner, "actions",  # pointer to the CollectionProperty
                owner, "actions_active_index",  # pointer to the active identifier
                rows = 1, maxrows = 1)
                
    # when the buttons should show up    
    @classmethod
    def poll(cls, context):
        mode = bpy.context.mode
        obj = bpy.context.active_object
        good_to_go = False
        if obj is not None:
            if obj.type == 'ARMATURE':
                if mode == 'OBJECT' or mode == 'POSE':
                    good_to_go = True
        if good_to_go:
            return True
        else:
            return False
                

class SCENE_PT_GYAZ_Export (Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "FBX"
    bl_label = 'Export'
    
    # add ui elements here
    def draw (self, context):
        
        scene = bpy.context.scene
        owner = scene.gyaz_export        
        lay = self.layout
        
        row = lay.row (align=True)
        row.prop (owner, "show_options", text='', icon='TRIA_DOWN' if owner.show_options else 'TRIA_RIGHT', emboss=False)
        row.label (text='Options:')
            
        if owner.show_options:
            row.prop (owner, "show_debug_props", text='', icon='SOLO_OFF' if not owner.show_debug_props else 'SOLO_ON', emboss=False)
            col = lay.column (align=True)
            col.label (text="Texture Format:")
            tex_row = col.row (align=True)
            tex_row.prop (owner, "texture_format_mode", text="")
            tex_row.prop (owner, "texture_format_override", text='')
            col.separator ()
            col.prop (owner, "texture_compression", text='Compression')
            col = lay.column (align=True)    
            col.prop (owner, "use_prefixes")
            col.prop (owner, "check_for_second_uv_map")
            col.prop (owner, "detect_mirrored_uvs")
            col.prop (owner, "allow_quads")
            col.prop (owner, "add_end_bones")
            col.label (text="Smoothing:")
            col.prop (owner, "mesh_smoothing", text="")
            col = lay.column (align=True)
            col.prop (owner, "primary_bone_axis")
            col.prop (owner, "secondary_bone_axis")
            
            if owner.show_debug_props:
                col = lay.column ()
                col = lay.column (align=True)
                col.label (text='Debug:')
                col.prop (owner, "dont_reload_scene")
        
        obj = bpy.context.active_object
        if obj is not None:
            col = lay.column (align=True)
            col.label (text='Destination:')
            row = col.row (align=True)
            row.use_property_split = False
            row.prop (owner, 'export_folder_mode', expand=True)
            relative = owner.export_folder_mode == 'RELATIVE_FOLDER'
            path = '//' + owner.relative_folder_name if relative else owner.export_folder
            row.operator ('object.gyaz_export_open_folder_in_explorer', text='', icon='VIEWZOOM').path=path
            if relative:
                lay.prop (owner, "relative_folder_name")
            else:
                lay.prop (owner, "export_folder", text="")   
            lay.label (text='Asset Type:')
            col = lay.column (align=True)
            col.use_property_split = False
            if obj.type == 'ARMATURE':
                asset_type = owner.skeletal_asset_type
                col.prop (owner, 'skeletal_asset_type', expand=True)   
            else:
                asset_type = owner.rigid_asset_type
                col.prop (owner, 'rigid_asset_type', expand=True)
        
        col = lay.column (align=True)
        if asset_type == 'STATIC_MESHES':
            col.prop (owner, "static_mesh_gather_from_collection")
            if owner.static_mesh_gather_from_collection:
                col.prop (owner, "static_mesh_gather_nested")
            col.prop (owner, "static_mesh_clear_transforms")
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
            col.prop (owner, "skeletal_mesh_limit_bone_influences", text="")        
            col.prop (owner, "skeletal_clear_transforms")
            col.prop (owner, "skeletal_mesh_vcolors")
            col.prop (owner, "skeletal_shapes")
            col.prop (owner, "export_lods")
            col.prop (owner, "export_textures")
            if owner.export_textures:
                col.prop (owner, "export_only_textures")
            col.prop (owner, "skeletal_mesh_pack_objects")
            
        elif asset_type == 'ANIMATIONS':
            col.prop (owner, 'use_anim_object_name_override')
            if owner.use_anim_object_name_override:
                row = col.row (align=True)
                row.label (text='', icon='BLANK1')
                row.prop (owner, 'anim_object_name_override')
            col.prop (owner, "skeletal_clear_transforms")
            col.prop (owner, "skeletal_shapes")
            col.prop (owner, "export_lods")
            if owner.action_export_mode == "SCENE":
                col.label (text="Animation Name:")
                col.prop (owner, "global_anim_name", text="")
            elif owner.rig_mode == "AS_IS":
                col.prop (owner, "pack_actions")
                if owner.pack_actions:
                    row = col.row(align=True)
                    row.label (text="", icon="BLANK1")
                    row.prop (owner, "global_anim_name", text="")
            col.split()
            col.alignment = "RIGHT"
            col.label (text="{0} fps".format(scene.render.fps))
            col.alignment = "LEFT"
            
        elif asset_type == 'RIGID_ANIMATIONS':
            col.prop (owner, "rigid_anim_gather_from_collection")
            if owner.rigid_anim_gather_from_collection:
                col.prop (owner, "rigid_anim_gather_nested")
            col.prop (owner, "rigid_anim_vcolors")
            col.prop (owner, "rigid_anim_shapes")
            row = col.row ()
            row.enabled = True if not owner.rigid_anim_cubes or owner.rigid_anim_cubes and owner.rigid_anim_pack_objects else False
            row.prop (owner, "export_textures")
            row = col.row ()
            row.enabled = True if not owner.rigid_anim_pack_objects else False
            row.prop (owner, "rigid_anim_cubes")
            col.prop (owner, "rigid_anim_pack_objects")
            col.prop (owner, "export_lods")
            if owner.rigid_anim_pack_objects:
                row = col.row (align=True)
                row.label (icon='BLANK1')
                row.prop (owner, "rigid_anim_pack_name")
                message1 = True
            else:
                message1 = False
            col.label (text='Animation Name:')
            row = col.row (align=True)
            row.label (icon='BLANK1')
            row.prop (owner, "rigid_anim_name")
            if message1:
                col.label (text="Scene start-end forced", icon='INFO')
            col.split()
            col.alignment = "RIGHT"
            col.label (text="{0} fps".format(scene.render.fps))    
            col.alignment = "LEFT"
        
        col.label (text="Target App:")
        col.prop (owner, "target_app", text="")
        row = lay.row (align=True)
        row.scale_y = 2
        row.operator ('object.gyaz_export_export', text='EXPORT', icon='EXPORT')
        row.operator ('object.gyaz_export_select_file_in_explorer', text='', icon='VIEWZOOM').path=owner.path_to_last_export
        
    # when the buttons should show up    
    @classmethod
    def poll(cls, context):
        obj = bpy.context.active_object
        mode = bpy.context.mode
        if obj is not None:
            return mode == 'OBJECT' or mode == 'POSE' or mode == 'PAINT_TEXTURE' or mode == 'PAINT_VERTEX'


class SCENE_PT_GYAZ_Export_Mesh (Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "FBX"
    bl_label = 'Export Mesh'
    
    # add ui elements here
    def draw (self, context):
        lay = self.layout

        obj = bpy.context.active_object
        if obj and obj.type == "MESH":
            mesh = obj.data
            owner = mesh.gyaz_export

            if len(mesh.uv_layers) > 0:
                col = lay.column (align=True)
                col.label (text="UV Maps:")
                iv_idx = -1
                for uv_map in mesh.uv_layers:
                    iv_idx += 1
                    col.prop (owner, "uv_export", index=iv_idx, text=uv_map.name, toggle=True)

            if len(mesh.color_attributes) > 0:
                col = lay.column (align=True)
                col.label (text="Color Attributes:")
                vert_color_idx = -1
                for vert_color in mesh.color_attributes:
                    vert_color_idx += 1
                    col.prop (owner, "vert_color_export", index=vert_color_idx, text=vert_color.name, toggle=True)

            col = lay.column (align=True)
            col.prop (owner, 'merge_materials')
            if owner.merge_materials:
                row = col.row (align=True)
                row.label (icon='BLANK1')
                row.prop (owner, 'atlas_name', text="")   

            lay.operator("object.gyaz_export_generate_lods", text="Generate LODs")

    # when the buttons should show up    
    @classmethod
    def poll(cls, context):
        ao = bpy.context.active_object
        return ao is not None and ao.type == 'MESH'


class SCENE_PT_GYAZ_Export_Filter (Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "FBX"
    bl_label = 'Export Filter' 
    
    # add ui elements here
    def draw (self, context):
        
        scene = bpy.context.scene   
        owner = scene.gyaz_export     
        lay = self.layout
        obj = bpy.context.active_object
        asset_type = owner.skeletal_asset_type if obj.type == 'ARMATURE' else owner.rigid_asset_type
        
        # utility
        row = lay.row (align=True)
        row.scale_x = 1.5
        row.operator ('object.gyaz_export_mark_all_selected_for_export', text='', icon='CHECKBOX_HLT')
        row.operator ('object.gyaz_export_mark_all_selected_not_for_export', text='', icon='CHECKBOX_DEHLT')
        row.separator ()
        row.operator ('object.gyaz_export_mark_all_for_export', text='', icon='SCENE_DATA')
        row.operator ('object.gyaz_export_mark_all_not_for_export', text='', icon='CHECKBOX_DEHLT')
        row.separator ()
        row.operator ('object.gyaz_export_set_filter_type', text=owner.filter_type)
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
        if ao is not None:
            return mode == 'OBJECT' or mode == 'POSE' or mode == 'PAINT_TEXTURE' or mode == 'PAINT_VERTEX'
    

class SCENE_PT_GYAZ_Export_Extras (Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "FBX"
    bl_label = 'Export Extras'
    
    # add ui elements here
    def draw (self, context):      
        lay = self.layout     
        lay.operator ('import_scene.fbx', text='Import FBX')

        owner = bpy.context.scene.gyaz_export_shapes
        show = owner.show_props
        row = lay.row(align=True)
        row.prop (owner, 'show_props', icon='TRIA_DOWN' if show else 'TRIA_RIGHT', text="", emboss=False)
        row.label (text='Shape Keys in UVs')
        if show:
            lay.prop (owner, 'encode_normals')
            col = lay.column (align=True)
            col.label (text='Base:')
            col.prop (owner, 'base_mesh', text='')
            col = lay.column (align=True)
            col.label (text='Shape 1:')
            col.prop (owner, 'shape_key_mesh_1', text='')
            col = lay.column (align=True)
            col.label (text='Shape 2:')
            col.prop (owner, 'shape_key_mesh_2', text='')
            if not owner.encode_normals:
                col = lay.column (align=True)
                col.label (text='Shape 3:')
                col.prop (owner, 'shape_key_mesh_3', text='')   
                col = lay.column (align=True)
                col.label (text='Shape 4:')
                col.prop (owner, 'shape_key_mesh_4', text='')
                col = lay.column (align=True)
                col.label (text='Shape 5:')
                col.prop (owner, 'shape_key_mesh_5', text='')
            else:
                col = lay.column (align=True)
                col.label (text='Shape 3 (No Normals):')
                col.prop (owner, 'shape_key_mesh_3', text='')            
            col = lay.column (align=True)
            col.label (text='Shape Normal To Vert Color:')
            col.prop (owner, 'shape_nor_to_vert_col', text='')
            lay.separator ()
            lay.operator ('object.gyaz_export_encode_shape_keys_in_uv_channels', text='Encode', icon='SHAPEKEY_DATA')
            lay.separator ()
            row = lay.row (align=True)
            row.scale_y = 2
            row.operator ('object.gyaz_export_export', text='EXPORT', icon='EXPORT')
            row.operator ('object.gyaz_export_select_file_in_explorer', text='', icon='VIEWZOOM').path=bpy.context.scene.gyaz_export.path_to_last_export


def register():
    bpy.utils.register_class (UI_UL_GYAZ_ExtraBones)
    bpy.utils.register_class (UI_UL_GYAZ_ExportBones)
    bpy.utils.register_class (UI_UL_GYAZ_ExportActions)
    bpy.utils.register_class (SCENE_PT_GYAZ_Export_Bones)  
    bpy.utils.register_class (SCENE_PT_GYAZ_Export_Animation)   
    bpy.utils.register_class (SCENE_PT_GYAZ_Export)
    bpy.utils.register_class (SCENE_PT_GYAZ_Export_Mesh)
    bpy.utils.register_class (SCENE_PT_GYAZ_Export_Filter)
    bpy.utils.register_class (SCENE_PT_GYAZ_Export_Extras)
    
    
def unregister():
    bpy.utils.unregister_class (UI_UL_GYAZ_ExtraBones)
    bpy.utils.unregister_class (UI_UL_GYAZ_ExportBones)
    bpy.utils.unregister_class (UI_UL_GYAZ_ExportActions)
    bpy.utils.unregister_class (SCENE_PT_GYAZ_Export_Bones)
    bpy.utils.unregister_class (SCENE_PT_GYAZ_Export_Animation)
    bpy.utils.unregister_class (SCENE_PT_GYAZ_Export)
    bpy.utils.unregister_class (SCENE_PT_GYAZ_Export_Mesh)
    bpy.utils.unregister_class (SCENE_PT_GYAZ_Export_Filter)
    bpy.utils.unregister_class (SCENE_PT_GYAZ_Export_Extras)
    
    
if __name__ == "__main__":   
    register()   