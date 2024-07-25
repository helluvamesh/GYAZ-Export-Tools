import bpy, re
import numpy as np
from mathutils import Matrix, Vector


class POD:
    pass


def report (self, item, error_or_info):
    self.report({error_or_info}, item)


def popup (lines, icon, title):
    def draw(self, context):
        for line in lines:
            self.layout.label(text=line)
    bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)


def list_to_visual_list (list):
    return ", ".join(list)

    
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


def get_active_action (obj):
    if obj.animation_data is not None:
        return obj.animation_data.action


def is_str_blank (s):
    return s.replace (" ", "") == ""


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
    object.matrix_world = Matrix()


def _gather_images_from_nodes(node_tree, gathered_images, gathered_image_nodes):
    for node in node_tree.nodes:
        if node.type == 'TEX_IMAGE' or node.type == 'TEX_ENVIRONMENT':
            gathered_images.add(node.image)
            gathered_image_nodes.add(node)
        elif node.type == 'GROUP':
            _gather_images_from_nodes(node.node_tree, gathered_images, gathered_image_nodes)


def gather_images_from_material(material, gathered_images, gathered_image_nodes):
    node_tree = material.node_tree
    if node_tree is not None:
        _gather_images_from_nodes(node_tree, gathered_images, gathered_image_nodes)


def reset_all_pose_bones(rig):
    zero_vec = (0, 0, 0)
    zero_quat = (1, 0, 0, 0)
    one_vec = (1, 1, 1)
    zero_axis_angle = (0, 0, 1, 0)

    for pbone in rig.pose.bones:
        pbone.location = zero_vec
        rm = pbone.rotation_mode
        if rm == "QUATERNION":
            pbone.rotation_quaternion = zero_quat
        elif rm == "AXIS_ANGLE":
            pbone.rotation_axis_angle = zero_axis_angle
        else:
            pbone.rotation_euler = zero_vec
        pbone.scale = one_vec


def delete_object(obj):
    bpy.data.objects.remove(obj, do_unlink=True)


def clear_blender_collection(collection):
    for item in collection:
        collection.remove(item)


def set_active_action (obj, action):
    if getattr (obj, "animation_data") == None:
        obj.animation_data_create ()
    reset_all_pose_bones(obj)
    obj.animation_data.action = action


def can_be_converted_to_number (string):
    try:
        int(string)
        return True
    except:
        return False


def remove_dot_plus_three_numbers (name):
    if len(name) < 4:
        return name
    elif name[-4] == '.' and can_be_converted_to_number (name[-3:]):
        return name[:-4]
    else:
        return name
    

def remove_extension(path):
    dot_idx = path.rfind('.')
    if dot_idx >= 1:
        return path[0:dot_idx]


def make_lod_object_name_pattern():
    return re.compile("(.*)[_\\s]lod_?(\\d+)$", re.IGNORECASE)

def get_name_and_lod_index(lod_pattern, name):
    finds = re.findall(lod_pattern, name)
    if len(finds) == 1:
        info = finds[0]
        return (info[0], int(info[1]))
    else:
        return None


def set_bone_parent(ebones, name, parent_name):
    ebone = ebones.get(name)
    if ebone is not None:
        if parent_name == None:
            ebone.parent = None      
        else:
            ebone.parent = ebones.get(parent_name)


def get_bbox_and_dimensions (vectors):
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


def get_dimensions(vectors):
    x_vectors = [vec[0] for vec in vectors]
    y_vectors = [vec[1] for vec in vectors]
    z_vectors = [vec[2] for vec in vectors]
    
    x_min = min (x_vectors)
    x_max = max (x_vectors)
    y_min = min (y_vectors)
    y_max = max (y_vectors)
    z_min = min (z_vectors)
    z_max = max (z_vectors)
    
    return x_max - x_min, y_max - y_min, z_max - z_min


# remove rotation form selected collision objects keeping scale intact
def bake_collision_object(obj):
    mesh = obj.data
    vertices = mesh.vertices
    
    # calc vert positions as if rotation and scale was applied
    matrix = obj.matrix_world
    location = Vector(obj.location)
    original_vert_coords = [Vector(vert.co) for vert in vertices]
    applied_verts = [(matrix @ co) - location for co in original_vert_coords]
    obj.matrix_world.identity()
    obj.location = location
    
    # reapply scale
    dims = get_dimensions(applied_verts)
    for i in range(0, len(vertices)):
        vertices[i].co = original_vert_coords[i]
    obj.scale = dims
