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


import bpy, bmesh
from bpy.props import *
from bpy.types import Operator, Panel, PropertyGroup, UIList, Menu, Mesh, Scene
from mathutils import Vector


# report
def report (self, item, error_or_info):
    self.report({error_or_info}, item)


# merge materials ui
def ui_merge_materials (self, context):      
    lay = self.layout
    obj = context.active_object
    if obj.type == 'MESH':
        owner = obj.data.gyaz_export
        lay.prop (owner, 'merge_materials', toggle=True)
        lay.prop (owner, 'atlas_name')    
        

# uv utils        
class Op_GYAZ_MoveUVMap (bpy.types.Operator):
       
    bl_idname = "object.gyaz_move_uv_map"  
    bl_label = "Move UV Map"
    bl_description = "Move active uv map"
    
    up: BoolProperty (default=False)

    #operator function
    def execute(self, context):
        
        mesh = bpy.context.mesh
        uvmaps = mesh.uv_layers
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
       
    bl_idname = "object.gyaz_batch_set_active_uv_map_by_index"  
    bl_label = "Batch Set Active UV Map by Index"
    bl_description = "Set uv map active on all selected objects by the index of the active object's active uv map"
    
    for_render: BoolProperty (default=False)

    #operator function
    def execute(self, context):
        scene = bpy.context.scene
        object = bpy.context.active_object
        selected_objects = bpy.context.selected_objects
        
        uvmaps = object.data.uv_layers
        if len (uvmaps) > 0:
            active_uv_map_index = uvmaps.active_index
            
            for obj in selected_objects:
                if obj.type == 'MESH':
                    uv_maps = obj.data.uv_layers
                    if len (uv_maps) > 0:
                        if active_uv_map_index < len(uv_maps):
                            if not self.for_render:
                                uv_maps.active_index = active_uv_map_index
                            else:
                                uv_maps[active_uv_map_index].active_render = True
                              
        return {'FINISHED'}
    

class Op_GYAZ_BatchSetActiveUVMapByName (bpy.types.Operator):
       
    bl_idname = "object.gyaz_batch_set_active_uv_map_by_name"  
    bl_label = "Batch Set Active UV Map by Name"
    bl_description = "Set uv map active on all selected objects by the name of active object's active uv map"
    
    for_render: BoolProperty (default=False)

    #operator function
    def execute(self, context):
        scene = bpy.context.scene
        object = bpy.context.active_object
        selected_objects = bpy.context.selected_objects
        
        uvmaps = object.data.uv_layers
        if len (uvmaps) > 0:
            active_uv_map_index = uvmaps.active_index
            active_uv_map_name = uvmaps[active_uv_map_index].name
            
            for obj in selected_objects:
                if obj.type == 'MESH':
                    uv_maps = obj.data.uv_layers
                    if len (uv_maps) > 0:
                        for index, uv_map in enumerate(uv_maps):
                            if uv_map.name == active_uv_map_name:
                                if not self.for_render:
                                    uv_maps.active_index = index
                                else:
                                    uv_maps[active_uv_map_name].active_render = True
                              
        return {'FINISHED'}
    
    
class Op_GYAZ_BatchAddUVMap (bpy.types.Operator):
       
    bl_idname = "object.gyaz_batch_add_uv_map"  
    bl_label = "Batch Add UV Map"
    bl_description = "Add new uv map to all selected objects"
    
    name: StringProperty (name='Name')
    
    # confirm popup
    def invoke (self, context, event):
        wm = bpy.context.window_manager
        return  wm.invoke_props_dialog (self)

    #operator function
    def execute(self, context):
        name = self.name if self.name != '' else 'UVMap'
        
        meshes = {obj.data for obj in bpy.context.selected_objects if obj.type == 'MESH'}
        for mesh in meshes:
            mesh.uv_layers.new (name=name)
                              
        return {'FINISHED'}                
        
        
# Panel Overrides:

# uvmaps
class UI_UL_GYAZ_UVMaps (UIList):
    def draw_item (self, context, layout, data, set, icon, active_data, active_propname, index):
        row = layout.row (align=True)
        owner = context.mesh.gyaz_export
        row.prop (owner, "uv_export", text='', emboss=False, index=index, icon='EXPORT' if owner.uv_export[index] else 'BLANK1')
        row.prop (set, "name", text='', emboss=False)
        row.prop (set, "active_render", text='', emboss=False, icon='RESTRICT_RENDER_OFF' if set.active_render else 'RESTRICT_RENDER_ON')

class DATA_MT_GYAZ_UVUtils (Menu):
    
    bl_label = 'UV Utils'
    
    def draw (self, context):
        lay = self.layout
        lay.operator_context = 'INVOKE_REGION_WIN'
        lay.operator (Op_GYAZ_BatchSetActiveUVMapByIndex.bl_idname).for_render=False
        lay.operator (Op_GYAZ_BatchSetActiveUVMapByIndex.bl_idname, text='For Render', icon='RESTRICT_RENDER_OFF').for_render=True
        lay.operator (Op_GYAZ_BatchSetActiveUVMapByName.bl_idname).for_render=False
        lay.operator (Op_GYAZ_BatchSetActiveUVMapByName.bl_idname, text='For Render', icon='RESTRICT_RENDER_OFF').for_render=True
        lay.operator (Op_GYAZ_BatchAddUVMap.bl_idname)
            
class DATA_PT_uv_texture (Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'data'
    bl_label = 'UV Maps'  
    
    # add ui elements here
    def draw (self, context):      
        lay = self.layout
        mesh = bpy.context.mesh
        uv_count = len (mesh.uv_layers)
        row_count = 4 if uv_count > 1 else 2
        row = lay.row ()   
        row.template_list ("UI_UL_GYAZ_UVMaps", "",  # type and unique id
            mesh, "uv_layers",  # pointer to the CollectionProperty
            mesh.uv_layers, "active_index",  # pointer to the active identifier
            rows = row_count, maxrows = row_count)
        col = row.column (align=True)
        col.enabled = True if not context.space_data.use_pin_id else False
        col.operator ('mesh.uv_texture_add', icon='ADD', text='')
        col.operator ('mesh.uv_texture_remove', icon='REMOVE', text='')
        col.separator ()
        col.menu ('DATA_MT_GYAZ_UVUtils', text='', icon='DOWNARROW_HLT')
        if uv_count > 1:
            col.separator ()
            col.operator (Op_GYAZ_MoveUVMap.bl_idname, text='', icon='TRIA_UP').up = True
            col.operator (Op_GYAZ_MoveUVMap.bl_idname, text='', icon='TRIA_DOWN').up = False
    
    #when the buttons should show up    
    @classmethod
    def poll(cls, context):
        ob = bpy.context.active_object       
        return ob.type == 'MESH'
 
      
# vertex colors
class UI_UL_GYAZ_VertexColorList (UIList):
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
        row.template_list ("UI_UL_GYAZ_VertexColorList", "",  # type and unique id
            mesh, "vertex_colors",  # pointer to the CollectionProperty
            mesh.vertex_colors, "active_index",  # pointer to the active identifier
            rows = 1, maxrows = 1)
        col = row.column (align=True)
        col.enabled = True if not context.space_data.use_pin_id else False
        col.operator ('mesh.vertex_color_add', icon='ADD', text='')
        col.operator ('mesh.vertex_color_remove', icon='REMOVE', text='')
    
    #when the buttons should show up    
    @classmethod
    def poll(cls, context):
        ob = bpy.context.active_object       
        return ob.type == 'MESH'
    

class PG_GYAZ_Export_EncodeShapeKeysInUVChannel (PropertyGroup):

    def update_base_mesh (self, context):
        prop = bpy.context.scene.gyaz_export_shapes.base_mesh
        if prop is not None:
            if prop.type != 'MESH':
                bpy.context.scene.gyaz_export_shapes.base_mesh = None
                
    def update_shape_mesh_1 (self, context):
        prop = bpy.context.scene.gyaz_export_shapes.shape_key_mesh_1
        if prop is not None:
            if prop.type != 'MESH':
                bpy.context.scene.gyaz_export_shapes.shape_key_mesh_1 = None
                
    def update_shape_mesh_2 (self, context):
        prop = bpy.context.scene.gyaz_export_shapes.shape_key_mesh_2
        if prop is not None:
            if prop.type != 'MESH':
                bpy.context.scene.gyaz_export_shapes.shape_key_mesh_2 = None
                
    def update_shape_mesh_3 (self, context):
        prop = bpy.context.scene.gyaz_export_shapes.shape_key_mesh_3
        if prop is not None:
            if prop.type != 'MESH':
                bpy.context.scene.gyaz_export_shapes.shape_key_mesh_3 = None
                
    def update_shape_mesh_4 (self, context):
        prop = bpy.context.scene.gyaz_export_shapes.shape_key_mesh_4
        if prop is not None:
            if prop.type != 'MESH':
                bpy.context.scene.gyaz_export_shapes.shape_key_mesh_4 = None
                
    def update_shape_mesh_5 (self, context):
        prop = bpy.context.scene.gyaz_export_shapes.shape_key_mesh_5
        if prop is not None:
            if prop.type != 'MESH':
                bpy.context.scene.gyaz_export_shapes.shape_key_mesh_5 = None
    
    show_props: BoolProperty (name='Shape Keys In UVs')
    base_mesh: PointerProperty (type = bpy.types.Object, name='Base Mesh', update=update_base_mesh)
    shape_key_mesh_1: PointerProperty (type = bpy.types.Object, name='Shape Mesh 1', update=update_shape_mesh_1)
    shape_key_mesh_2: PointerProperty (type = bpy.types.Object, name='Shape Mesh 2', update=update_shape_mesh_2)
    shape_key_mesh_3: PointerProperty (type = bpy.types.Object, name='Shape Mesh 3', update=update_shape_mesh_3)
    shape_key_mesh_4: PointerProperty (type = bpy.types.Object, name='Shape Mesh 4', update=update_shape_mesh_4)
    shape_key_mesh_5: PointerProperty (type = bpy.types.Object, name='Shape Mesh 5', update=update_shape_mesh_5)
    shape_nor_to_vert_col: EnumProperty (name='Shape Normal To Vert Color', items=(('None', 'None', ''), ('0', 'Shape 1', ''), ('1', 'Shape 2', ''), ('2', 'Shape 3', ''), ('3', 'Shape 4', ''), ('4', 'Shape 5', '')), default='None')    
    encode_normals: BoolProperty (name='Normals', description='Whether to encode normals, too for higher quality')
    
    
class Op_GYAZ_Export_EncodeShapeKeysInUVChannels (Operator):
    
    bl_idname = "object.gyaz_export_encode_shape_keys_in_uv_channels"  
    bl_label = "Encode Shape Keys In UV Channels"
    bl_description = "UV1-UV3: World Position Offset, Normal"
    bl_options = {'REGISTER', 'UNDO'}
            
    # operator function
    def execute(self, context):
        
        owner = bpy.context.scene.gyaz_export_shapes
        
        base_mesh = owner.base_mesh
        shape_1 = owner.shape_key_mesh_1
        shape_2 = owner.shape_key_mesh_2
        shape_3 = owner.shape_key_mesh_3
        shape_4 = owner.shape_key_mesh_4
        shape_5 = owner.shape_key_mesh_5
        
        if base_mesh is not None:
            base_mesh = base_mesh.data
        if shape_1 is not None:
            shape_1 = shape_1.data
        if shape_2 is not None:
            shape_2 = shape_2.data
        if shape_3 is not None:
            shape_3 = shape_3.data
        if shape_4 is not None:
            shape_4 = shape_4.data
        if shape_5 is not None:
            shape_5 = shape_5.data

        def main (uv_maps):

            def set_uvs_by_vert (vert, co, uv_layer):
                for loop in vert.link_loops:
                    loop[uv_layer].uv = co
            
            if owner.encode_normals and shape_3 == None or not owner.encode_normals and shape_5 == None:
                if len (uv_maps) == 0:
                    uv_maps.new (name='UVMap')
            
            if owner.encode_normals:
                
                uv_map_1 = uv_maps.new (name='Shape1_WPOxy')
                uv_map_2 = uv_maps.new (name='Shape1_WPOz_NORx')
                uv_map_3 = uv_maps.new (name='Shape1_NORyz')
                
                if shape_2 is not None:
                    uv_map_4 = uv_maps.new (name='Shape2_WPOxy')
                    uv_map_5 = uv_maps.new (name='Shape2_WPOz_NORx')
                    uv_map_6 = uv_maps.new (name='Shape2_NORyz')
                    
                if shape_3 is not None:
                    uv_map_7 = uv_maps.new (name='Shape3_WPOxy')
                    uv_map_8 = uv_maps.new (name='Shape3_WPOz')                    
                
                bm = bmesh.new ()
                bm.from_mesh (base_mesh)
                
                verts = bm.verts                
                        
                uv_layer_1 = bm.loops.layers.uv[uv_map_1.name]
                uv_layer_2 = bm.loops.layers.uv[uv_map_2.name]
                uv_layer_3 = bm.loops.layers.uv[uv_map_3.name]
                
                if shape_2 is not None:
                    uv_layer_4 = bm.loops.layers.uv[uv_map_4.name]
                    uv_layer_5 = bm.loops.layers.uv[uv_map_5.name]
                    uv_layer_6 = bm.loops.layers.uv[uv_map_6.name]
                    
                if shape_3 is not None:
                    uv_layer_7 = bm.loops.layers.uv[uv_map_7.name]
                    uv_layer_8 = bm.loops.layers.uv[uv_map_8.name]
                    

                def pack_data (shape_key_mesh, vert_index, vert, uv_layer_1, uv_layer_2, uv_layer_3):
                    vec = (shape_key_mesh.vertices[vert_index].co - vert.co) * 100
                    nor = ( shape_key_mesh.vertices[vert_index].normal + Vector ((1, 1, 1)) ) * 0.5
                    set_uvs_by_vert (vert, (-vec[1], vec[0]), uv_layer_1)
                    set_uvs_by_vert (vert, (vec[2], nor[1]), uv_layer_2)
                    set_uvs_by_vert (vert, (1-nor[0], 1-nor[2]), uv_layer_3)
                
                pack_shape_2 = True if shape_2 is not None else False
                pack_shape_3 = True if shape_3 is not None else False
                
                for vert_index, vert in enumerate (verts):
                    pack_data (shape_1, vert_index, vert, uv_layer_1, uv_layer_2, uv_layer_3)
                    if pack_shape_2:
                        pack_data (shape_2, vert_index, vert, uv_layer_4, uv_layer_5, uv_layer_6)
                    if pack_shape_3:                   
                        vec = (shape_3.vertices[vert_index].co - vert.co) * 100
                        set_uvs_by_vert (vert, (-vec[1], vec[0]), uv_layer_7)
                        set_uvs_by_vert (vert, (vec[2], 0), uv_layer_8)
                        
            else:
                
                uv_map_1 = uv_maps.new (name='Shape1_WPOxy')
                uv_map_2 = uv_maps.new (name='Shape1_WPOz')         
                
                if shape_2 is not None:
                    uv_map_2.name = 'Shape1_WPOz_Shape2_WPOx'
                    uv_map_3 = uv_maps.new (name='Shape2_WPOyz')
                
                    if shape_3 is not None:
                        uv_map_4 = uv_maps.new (name='Shape3_WPOxy')
                        uv_map_5 = uv_maps.new (name='Shape3_WPOz')
                        
                        if shape_4 is not None:
                            uv_map_5.name = 'Shape3_WPOz_Shape4_WPOx'
                            uv_map_6 = uv_maps.new (name='Shape4_WPOyz')
                            
                            if shape_5 is not None:
                                uv_map_7 = uv_maps.new (name='Shape5_WPOxy')   
                                uv_map_8 = uv_maps.new (name='Shape5_WPOz')                                
                            
                bm = bmesh.new ()
                bm.from_mesh (base_mesh)
                
                verts = bm.verts
                
                uv_layer_1 = bm.loops.layers.uv[uv_map_1.name]
                uv_layer_2 = bm.loops.layers.uv[uv_map_2.name]             
                
                if shape_2 is not None:
                    uv_layer_3 = bm.loops.layers.uv[uv_map_3.name]  
                
                    if shape_3 is not None:
                        uv_layer_4 = bm.loops.layers.uv[uv_map_4.name]
                        uv_layer_5 = bm.loops.layers.uv[uv_map_5.name] 
                        
                        if shape_4 is not None:
                            uv_layer_6 = bm.loops.layers.uv[uv_map_6.name]
                            
                            if shape_5 is not None:
                                uv_layer_7 = bm.loops.layers.uv[uv_map_7.name]
                                uv_layer_8 = bm.loops.layers.uv[uv_map_8.name]                                               
                
                
                if shape_2 == None:
                
                    for vert_index, vert in enumerate (verts):
                        vec = (shape_1.vertices[vert_index].co - vert.co) * 100
                        set_uvs_by_vert (vert, (-vec[1], vec[0]), uv_layer_1)
                        set_uvs_by_vert (vert, (vec[2], 0), uv_layer_2)
                        
                else:
                    
                    for vert_index, vert in enumerate (verts):
                        vec = (shape_1.vertices[vert_index].co - vert.co) * 100
                        vec2 = (shape_2.vertices[vert_index].co - vert.co) * 100
                        set_uvs_by_vert (vert, (-vec[1], vec[0]), uv_layer_1)
                        set_uvs_by_vert (vert, (vec[2], vec2[1]), uv_layer_2)                    
                        set_uvs_by_vert (vert, (-vec2[0], -vec2[2]), uv_layer_3)                    
                
                    if shape_3 and not shape_4:
                        
                        for vert_index, vert in enumerate (verts):
                            vec = (shape_3.vertices[vert_index].co - vert.co) * 100
                            set_uvs_by_vert (vert, (-vec[1], vec[0]), uv_layer_4)
                            set_uvs_by_vert (vert, (vec[2], 0), uv_layer_5)
                            
                    if shape_3 and shape_4:
                        
                        for vert_index, vert in enumerate (verts):
                            vec = (shape_3.vertices[vert_index].co - vert.co) * 100
                            vec2 = (shape_4.vertices[vert_index].co - vert.co) * 100
                            set_uvs_by_vert (vert, (-vec[1], vec[0]), uv_layer_4)
                            set_uvs_by_vert (vert, (vec[2], vec2[1]), uv_layer_5)                    
                            set_uvs_by_vert (vert, (-vec2[0], -vec2[2]), uv_layer_6)
                            
                    if shape_5:
                        
                        for vert_index, vert in enumerate (verts):
                            vec = (shape_5.vertices[vert_index].co - vert.co) * 100
                            set_uvs_by_vert (vert, (-vec[1], vec[0]), uv_layer_7)
                            set_uvs_by_vert (vert, (vec[2], 0), uv_layer_8)                        
                
             
            nor_to_vc = owner.shape_nor_to_vert_col           
            if nor_to_vc != 'None':
                
                shape_mesh = None    
                shapes = [shape_1, shape_2, shape_3, shape_4, shape_5]
                shape_mesh = shapes[int(nor_to_vc)]    
                
                if shape_mesh is not None:
                    
                    color_layer = bm.loops.layers.color.new ('Shape'+str(int(nor_to_vc)+1)+'_NOR')
                    
                    for vert_index, vert in enumerate (verts):
                        nor = ( shape_mesh.vertices[vert_index].normal + Vector ((1, 1, 1)) ) * 0.5
                        for loop in vert.link_loops:
                            loop[color_layer] = 1-nor[1], 1-nor[0], nor[2]                   
                        
                
            bm.to_mesh (base_mesh)
            bm.free ()
        
            
        def call (limit):
            if len (uv_maps) > limit:
                report (self, 'Base Mesh has more than ' +str(limit)+ ' uv maps.', 'WARNING')
            else:
                
                nor_to_vc = owner.shape_nor_to_vert_col
                if nor_to_vc != 'None':
                    if len (base_mesh.vertex_colors) >= 8:
                        report (self, 'No empty vertex color slot.', 'WARNING')
                    else:
                        main (uv_maps)
                else:
                    main (uv_maps)
        
        if base_mesh is not None and shape_1 is not None:
            
            uv_maps = base_mesh.uv_layers
        
            if owner.encode_normals:
            
                if shape_2 is not None:
                    limit = 2
                    if shape_3 is not None:
                        limit = 0        
                else:
                    limit = 5
                        
            else:
                
                limit = 6
                if shape_2 is not None:
                    limit = 5
                    if shape_3 is not None:
                        limit = 3
                        if shape_4 is not None:
                            limit = 2
                            if shape_5 is not None:
                                limit = 0
                            
            call (limit)
                
        else:
            report (self, 'Base Mesh and Shape Mesh 1 always have to be set.', 'WARNING')
                
                                                   
        return {'FINISHED'}
    
    #when the buttons should show up    
    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.mode == 'OBJECT'

    
# mesh props
class PG_GYAZ_Export_MeshProps (PropertyGroup):
    uv_export: BoolVectorProperty (size=8, default=[True]*8, description='Whether the GYAZ Exporter keeps this uv map')
    vert_color_export: BoolVectorProperty (size=8, default=(True, False, False, False, False, False, False, False), description='Whether the GYAZ Exporter keeps this vertex color layer')
    merge_materials: BoolProperty (name='Merge Materials On Export', default=False, description='Whether the GYAZ Exporter merges materials on export or keeps them as they are')
    atlas_name: StringProperty (name='Atlas', default='Atlas', description='Name of the merged material')
    

def register():
    bpy.utils.register_class (PG_GYAZ_Export_MeshProps)
    Mesh.gyaz_export = PointerProperty (type=PG_GYAZ_Export_MeshProps)
    
    bpy.utils.register_class (PG_GYAZ_Export_EncodeShapeKeysInUVChannel)
    Scene.gyaz_export_shapes = PointerProperty (type=PG_GYAZ_Export_EncodeShapeKeysInUVChannel)
    
    bpy.utils.register_class (Op_GYAZ_Export_EncodeShapeKeysInUVChannels)
    
    # merge materials ui
    bpy.types.CYCLES_PT_context_material.append (ui_merge_materials)
    bpy.types.EEVEE_MATERIAL_PT_context_material.append (ui_merge_materials)
    
    # uv utils
    bpy.utils.register_class (Op_GYAZ_MoveUVMap)
    bpy.utils.register_class (Op_GYAZ_BatchSetActiveUVMapByIndex)
    bpy.utils.register_class (Op_GYAZ_BatchSetActiveUVMapByName)
    bpy.utils.register_class (Op_GYAZ_BatchAddUVMap)
    bpy.utils.register_class (DATA_MT_GYAZ_UVUtils)
    
    # panel overrides
    bpy.utils.register_class (UI_UL_GYAZ_UVMaps)
    bpy.utils.register_class (UI_UL_GYAZ_VertexColorList)
    bpy.utils.register_class (DATA_PT_uv_texture)
    bpy.utils.register_class (DATA_PT_vertex_colors)


def unregister():
    bpy.utils.unregister_class (PG_GYAZ_Export_MeshProps)
    del Mesh.gyaz_export
    
    bpy.utils.unregister_class (PG_GYAZ_Export_EncodeShapeKeysInUVChannel)
    del Scene.gyaz_export_shapes
    
    bpy.utils.unregister_class (Op_GYAZ_Export_EncodeShapeKeysInUVChannels)
    
    # merge materials ui
    bpy.types.CYCLES_PT_context_material.remove (ui_merge_materials)
    bpy.types.EEVEE_MATERIAL_PT_context_material.remove (ui_merge_materials)
    
    # uv utils
    bpy.utils.unregister_class (Op_GYAZ_MoveUVMap)
    bpy.utils.unregister_class (Op_GYAZ_BatchSetActiveUVMapByIndex)
    bpy.utils.unregister_class (Op_GYAZ_BatchSetActiveUVMapByName)
    bpy.utils.unregister_class (Op_GYAZ_BatchAddUVMap)
    bpy.utils.unregister_class (DATA_MT_GYAZ_UVUtils)
    
    # panel overrides (the actual overrides can't be unregistered)
    # Blender needs to be restarted for the old panels to exist again
    bpy.utils.unregister_class (UI_UL_GYAZ_UVMaps)
    bpy.utils.unregister_class (UI_UL_GYAZ_VertexColorList)
    bpy.utils.unregister_class (DATA_PT_uv_texture)
    bpy.utils.unregister_class (DATA_PT_vertex_colors)
