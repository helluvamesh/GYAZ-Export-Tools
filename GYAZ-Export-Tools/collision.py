import bpy, bmesh
from mathutils import Vector, Matrix
from math import radians
from bpy.types import Operator
from bpy.props import *
from .utils import make_active_only


class Op_GYAZ_Export_AddCollision (Operator):

    bl_idname = "object.gyaz_export_add_collision"  
    bl_label = "GYAZ Export: Add Collision"
    bl_description = "Add a collider shape to the object."

    shape: EnumProperty(
        name="Shape",
        items=(
            ("BOX", "Box", ""),
            ("SPHERE", "Sphere", "")
        ),
        default="BOX"
    )


    def execute (self, context):
        obj = context.object
        scene = context.scene
        
        collision = None

        if self.shape == "BOX":
            collision = self.generate_box_collision_from_obj_bbox(obj, scene)

        elif self.shape == "SPHERE":
            collision = self.generate_sphere_collision_from_obj_bbox(obj, scene)

        self.select_collision_obj(collision)

        return {'FINISHED'}


    def generate_box_collision_from_obj_bbox(self, obj, scene):
        obj_name = obj.name
        
        bbox, dimensions = self.get_bbox_and_dimensions_from_obj(obj)
        
        return self.generate_box_collision(
            bbox, dimensions, scene, obj,
            collision_name="UBX_" + obj_name, 
            collection_name=obj_name + "_Collision"
        )
        
    
    def generate_sphere_collision_from_obj_bbox(self, obj, scene):
        obj_name = obj.name
        
        bbox, dimensions = self.get_bbox_and_dimensions_from_obj(obj)
        
        return self.generate_sphere_collision(
            bbox, dimensions, scene, obj,
            collision_name="USP_" + obj_name, 
            collection_name=obj_name + "_Collision"
        )
    
    
    def generate_box_collision(self, bbox, dimensions, scene, obj, collision_name, collection_name):    
        box_mesh = bpy.data.meshes.new(name="BoxCollision")
              
        bm = bmesh.new()
        
        bmesh.ops.create_cube(bm, size=1, calc_uvs=False)
        
        bmesh.ops.delete(bm, geom=[face for face in bm.faces], context="FACES_ONLY")
        
        bm.to_mesh(box_mesh)
        bm.free()
        
        box_obj = bpy.data.objects.new(name=collision_name, object_data=box_mesh)
        
        bbox_center = self.vector_mean(bbox)
        box_obj.matrix_world = obj.matrix_world @ Matrix.LocRotScale(bbox_center, None, dimensions)
        
        self.link_collision_obj_to_scene(scene, box_obj, obj, collection_name)
        self.set_collision_obj_display(box_obj)

        return box_obj
        
        
    def generate_sphere_collision(self, bbox, dimensions, scene, obj, collision_name, collection_name):    
        sphere_mesh = bpy.data.meshes.new(name="SphereCollision")
              
        bm = bmesh.new()
        
        bmesh.ops.create_circle(bm, segments=32, radius=.5)
        bmesh.ops.create_circle(bm, segments=32, radius=.5, matrix=Matrix.Rotation(radians(90), 4, "X"))
        bmesh.ops.create_circle(bm, segments=32, radius=.5, matrix=Matrix.Rotation(radians(90), 4, "Y"))
        
        bm.to_mesh(sphere_mesh)
        bm.free()
        
        sphere_obj = bpy.data.objects.new(name=collision_name, object_data=sphere_mesh)
        
        bbox_center = self.vector_mean(bbox)
        longest_dim = max([d for d in dimensions])
        sphere_obj.matrix_world = obj.matrix_world @ Matrix.LocRotScale(bbox_center, None, Vector((longest_dim, longest_dim, longest_dim)))
        
        self.link_collision_obj_to_scene(scene, sphere_obj, obj, collection_name)
        self.set_collision_obj_display(sphere_obj)

        return sphere_obj
    
    
    def get_bbox_and_dimensions_from_obj(self, obj):
        bm = bmesh.new()
        bm.from_object(obj, bpy.context.evaluated_depsgraph_get(), cage=False, face_normals=False, vertex_normals=False)
        
        positions = [vert.co for vert in bm.verts]
        bbox, dimensions = self.get_bbox_and_dimensions(positions)

        bm.free()
        return bbox, dimensions
        
    
    def get_bbox_and_dimensions (self, vectors):
        x_vectors = [vec[0] for vec in vectors]
        y_vectors = [vec[1] for vec in vectors]
        z_vectors = [vec[2] for vec in vectors]
        
        x_min = min (x_vectors)
        x_max = max (x_vectors)
        y_min = min (y_vectors)
        y_max = max (y_vectors)
        z_min = min (z_vectors)
        z_max = max (z_vectors)
        
        bbox = (Vector ((x_min, y_min, z_min)),
                Vector ((x_min, y_min, z_max)),
                Vector ((x_min, y_max, z_max)),
                Vector ((x_min, y_max, z_min)),
                Vector ((x_max, y_min, z_min)),
                Vector ((x_max, y_min, z_max)),
                Vector ((x_max, y_max, z_max)),
                Vector ((x_max, y_max, z_min))
               )
        
        dimensions = Vector((x_max - x_min, y_max - y_min, z_max - z_min))
        
        return bbox, dimensions
        
    
    def link_collision_obj_to_scene(self, scene, coll_obj, main_obj, coll_collection_name):
        coll_collection_parent = None
        main_obj_collections = main_obj.users_collection
        if len(main_obj_collections) > 0:
            coll_collection_parent = main_obj_collections[-1]
        else:
            coll_collection_parent = scene.collection

        coll_collection = coll_collection_parent.children.get(coll_collection_name)
        if coll_collection is None:
            coll_collection = bpy.data.collections.new(name=coll_collection_name)
            coll_collection_parent.children.link(coll_collection)
        
        coll_collection.objects.link(coll_obj)
        
        
    def vector_mean(self, vectors):
        if len(vectors) == 0: 
            return Vector()
        sum = Vector()
        for vec in vectors:
            sum += vec
        return sum / len(vectors)


    def set_collision_obj_display(self, obj):
        obj.show_in_front = True


    def select_collision_obj(self, obj):
        make_active_only(obj)


    #when the buttons should show up    
    @classmethod
    def poll(cls, context):
        ao = context.active_object
        return ao and ao.type == "MESH" and context.mode == 'OBJECT'


def register():
    bpy.utils.register_class (Op_GYAZ_Export_AddCollision)


def unregister():
    bpy.utils.unregister_class (Op_GYAZ_Export_AddCollision)
