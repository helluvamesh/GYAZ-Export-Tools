import bpy
import numpy as np
from mathutils import Vector, Matrix, Quaternion


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


def _gather_images(node_tree, images):
    for node in node_tree.nodes:
        if node.type == 'TEX_IMAGE' or node.type == 'TEX_ENVIRONMENT':
            images.add(node.image)
        elif node.type == 'GROUP':
            _gather_images(node.node_tree, images)


# get set of texture images in node tree
def gather_images_from_nodes (node_tree):
    images = set()
    _gather_images(node_tree, images)
    return set (images)


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
