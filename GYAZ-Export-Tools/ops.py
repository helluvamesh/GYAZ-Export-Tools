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

import bpy, os, subprocess
from bpy.props import StringProperty, EnumProperty, IntProperty
from .utils import report


# class Op_GYAZ_Export_SelectFileInWindowsFileExplorer (bpy.types.Operator):
       
#     bl_idname = "object.gyaz_export_select_file_in_explorer"  
#     bl_label = "GYAZ Export: Select File in Explorer"
#     bl_description = "Select File in file explorer"
    
#     path: StringProperty (default='', options={'SKIP_SAVE'})
    
#     # operator function
#     def execute(self, context):  
#         path = os.path.abspath ( bpy.path.abspath (self.path) )    
#         subprocess.Popen(r'explorer /select,'+path)
         
#         return {'FINISHED'}

    
class Op_GYAZ_Export_OpenFolderInWindowsFileExplorer (bpy.types.Operator):
       
    bl_idname = "object.gyaz_export_open_folder_in_explorer"  
    bl_label = "GYAZ Export: Open Folder in Explorer"
    bl_description = "Open folder in file explorer"
    
    path: StringProperty (default='', options={'SKIP_SAVE'})
    
    # operator function
    def execute(self, context):
        path = os.path.abspath ( bpy.path.abspath (self.path) )  
        subprocess.Popen ('explorer "'+path+'"')
          
        return {'FINISHED'}
    

class Op_GYAZ_Export_SavePreset (bpy.types.Operator):
    
    bl_idname = "object.gyaz_export_save_preset"  
    bl_label = "GYAZ Export: Save Preset"
    bl_description = "Save preset"
    
    ui_name: StringProperty (name = 'name', default = '')
    
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
            prefs = bpy.context.preferences.addons[__package__].preferences
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
            setattr (preset, 'root_bone_name', scene.gyaz_export.root_bone_name)
            setattr (preset, 'export_all_bones', scene.gyaz_export.export_all_bones)
            setattr (preset, 'constraint_extra_bones', scene.gyaz_export.constraint_extra_bones)
            setattr (preset, 'rename_vert_groups_to_extra_bones', scene.gyaz_export.rename_vert_groups_to_extra_bones)
            
            scene.gyaz_export.active_preset = preset.preset_name
            
            # save user preferences
            bpy.context.area.type = 'PREFERENCES'
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
        
        prefs = bpy.context.preferences.addons[__package__].preferences
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
                    scene.gyaz_export.property_unset ("root_bone_name")
                    scene.gyaz_export.property_unset ("constraint_extra_bones")
                    scene.gyaz_export.property_unset ("rename_vert_groups_to_extra_bones")
        
        # save user preferences
        bpy.context.area.type = 'PREFERENCES'
        bpy.ops.wm.save_userpref()
        bpy.context.area.type = 'VIEW_3D'      
            
        return {'FINISHED'}

    
class Op_GYAZ_Export_Functions (bpy.types.Operator):
       
    bl_idname = "object.gyaz_export_functions"  
    bl_label = "GYAZ Export: Functions"
    bl_description = ""
    
    ui_mode: EnumProperty(
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
            item.merge_to = ''
            scene.gyaz_export.extra_bones_active_index = len (scene_extra_bones) - 1
        elif mode == 'REMOVE_ALL_FROM_EXTRA_BONES':
            scene_extra_bones.clear ()    
            scene.gyaz_export.extra_bones_active_index = -1
            
        elif mode == 'ADD_TO_EXPORT_BONES':
            item = scene_export_bones.add ()
            item.name = ''
            item.merge_to = ''
        elif mode == 'REMOVE_ALL_FROM_EXPORT_BONES':
            scene_export_bones.clear ()
                                  
                
        elif mode == 'ADD_TO_EXPORT_ACTIONS':
            item = scene.gyaz_export.actions.add ()
            item.name = ''
            item.merge_to = ''
        elif mode == 'REMOVE_ALL_FROM_EXPORT_ACTIONS':
            scene.gyaz_export.actions.clear ()
            
        return {'FINISHED'}


class Op_GYAZ_Export_ReadSelectedPoseBones (bpy.types.Operator):
       
    bl_idname = "object.gyaz_export_read_selected_pose_bones"  
    bl_label = "GYAZ Export: Read Selected Pose Bones"
    bl_description = "Read selected pose bones"    
    
    mode: EnumProperty (items=(('EXPORT_BONES', 'Export Bones', ''), ('EXTRA_BONES', 'Extra Bones', '')), default='EXPORT_BONES')
    
    def execute(self, context):
        
        scene = bpy.context.scene
        rig = bpy.context.active_object
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
    
    ui_index: IntProperty (name='', default=0)
    
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
    
    ui_index: IntProperty (name='', default=0)
    
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
    
    ui_index: IntProperty (name='', default=0)
    
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
    
    ui_index: IntProperty (name='', default=0)
    
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
    
    ui_index: IntProperty (name='', default=0)
    
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
    
    mode: EnumProperty (items=(('UP', 'UP', ''), ('DOWN', 'DOWN', '')), default='UP')
    index: IntProperty (name='', default=0)
    
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
    

def register():
    bpy.utils.register_class (Op_GYAZ_Export_MarkAllSelectedForExport)      
    bpy.utils.register_class (Op_GYAZ_Export_MarkAllSelectedNotForExport)      
    bpy.utils.register_class (Op_GYAZ_Export_MarkAllForExport)      
    bpy.utils.register_class (Op_GYAZ_Export_MarkAllNotForExport)      
    #bpy.utils.register_class (Op_GYAZ_Export_SelectFileInWindowsFileExplorer)   
    bpy.utils.register_class (Op_GYAZ_Export_OpenFolderInWindowsFileExplorer)     
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
    bpy.utils.register_class (Op_GYAZ_Export_SetFilterType)  
    
    
def unregister():
    bpy.utils.unregister_class (Op_GYAZ_Export_MarkAllSelectedForExport)      
    bpy.utils.unregister_class (Op_GYAZ_Export_MarkAllSelectedNotForExport)      
    bpy.utils.unregister_class (Op_GYAZ_Export_MarkAllForExport)      
    bpy.utils.unregister_class (Op_GYAZ_Export_MarkAllNotForExport)      
    #bpy.utils.unregister_class (Op_GYAZ_Export_SelectFileInWindowsFileExplorer)   
    bpy.utils.unregister_class (Op_GYAZ_Export_OpenFolderInWindowsFileExplorer)    
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
    bpy.utils.unregister_class (Op_GYAZ_Export_SetFilterType)  
    
    
if __name__ == "__main__":   
    register()   