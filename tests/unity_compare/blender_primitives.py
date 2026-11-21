# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Lida
"""Blender side of the Blender-vs-Unity check on primitives (no character model).

blender -b --factory-startup --python tests/unity_compare/blender_primitives.py -- <out_dir>

Renders every sample (one sun, orthographic camera, no glow) at frames 1, 72, 144 and writes what the
Unity side needs to rebuild the same scene: each mesh as OBJ (rotation applied, object at its
location), the thickness attribute, the camera, the sun and the background (scene.json).
"""
import bpy, sys, os, math, json
sys.dont_write_bytecode = True
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'blender'))
from lida_aurora_toon import shader

out = os.path.abspath(sys.argv[sys.argv.index('--') + 1])
os.makedirs(out, exist_ok=True)
scene = bpy.context.scene
for o in list(scene.objects):
    bpy.data.objects.remove(o)
scene.render.engine = 'BLENDER_EEVEE'
scene.view_settings.view_transform = 'Standard'
scene.view_settings.look = 'None'
scene.render.fps = 24
scene.eevee.taa_render_samples = 32
BG = (0.035, 0.075, 0.13)
world = bpy.data.worlds.new('CmpWorld')
world.use_nodes = True
world.node_tree.nodes['Background'].inputs[0].default_value = (*BG, 1)
world.node_tree.nodes['Background'].inputs[1].default_value = 1.0
scene.world = world
sun = shader.ensure_sun(scene)
bpy.context.view_layer.update()

ITEMS = [('shell', (0.72, 0.62, 0.90)), ('scale', (0.78, 0.56, 0.88)), ('pearl', (0.95, 0.92, 0.96)),
         ('gem', (0.55, 0.75, 0.95)), ('fin', (0.80, 0.78, 0.95)), ('hair_softglow', (0.95, 0.62, 0.74)),
         ('skin', (0.95, 0.78, 0.72)), ('hair_aurora', (0.95, 0.70, 0.80))]
info = {'background_linear': list(BG), 'sun_to_light': list(sun.matrix_world.col[2].xyz.normalized()),
        'items': [], 'frames': [1, 72, 144], 'fps': 24}
for i, (preset, col) in enumerate(ITEMS):
    x = (i - (len(ITEMS) - 1) / 2) * 0.27
    if preset == 'fin':
        bpy.ops.mesh.primitive_torus_add(major_radius=0.075, minor_radius=0.032, major_segments=64, minor_segments=24, location=(x, 0, 0), rotation=(math.radians(70), 0, 0.3))
    elif preset.startswith('hair'):
        bpy.ops.mesh.primitive_torus_add(major_radius=0.07, minor_radius=0.045, major_segments=64, minor_segments=32, location=(x, 0, 0), rotation=(math.radians(90), 0, 0))
    else:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=0.1, location=(x, 0, 0))
    ob = bpy.context.object
    ob.name = 'Cmp_' + preset
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    bpy.ops.object.shade_smooth()
    mat = bpy.data.materials.new('Cmp_' + preset)
    mat.use_nodes = True
    next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED').inputs['Base Color'].default_value = (*col, 1)
    ob.data.materials.append(mat)
    kw = {}
    item = {'name': ob.name, 'preset': preset, 'base_linear': list(col), 'location': list(ob.location)}
    if preset == 'fin':
        shader.bake_thickness(ob, full_thickness=0.05)
        kw['thickness_attribute'] = shader.THICKNESS_ATTR
        me = ob.data
        json.dump({'object': ob.name, 'count': len(me.vertices), 'position': [c for v in me.vertices for c in v.co],
                   shader.THICKNESS_ATTR: [d.value for d in me.attributes[shader.THICKNESS_ATTR].data]},
                  open(os.path.join(out, 'attr_%s.json' % ob.name), 'w'))
        item['thickness'] = True
    shader.apply_material(mat, preset, sun, **kw)
    # OBJ of this object only, at the origin (Unity puts it at the location)
    loc = ob.location.copy()
    ob.location = (0, 0, 0)
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.ops.wm.obj_export(filepath=os.path.join(out, ob.name + '.obj'), export_selected_objects=True,
                          export_materials=False, export_uv=True, export_normals=True, apply_modifiers=True)
    ob.location = loc
    info['items'].append(item)

cd = bpy.data.cameras.new('CmpCam')
cam = bpy.data.objects.new('CmpCam', cd)
scene.collection.objects.link(cam)
scene.camera = cam
cd.type = 'ORTHO'
W, H = 2200, 330
cd.ortho_scale = 2.2
cam.location = (0, -3, 0.0)
cam.rotation_euler = (math.radians(90), 0, 0)
scene.render.resolution_x, scene.render.resolution_y = W, H
bpy.context.view_layer.update()
mw = cam.matrix_world
info['camera'] = {'position': list(cam.location), 'forward': list(-mw.col[2].xyz), 'up': list(mw.col[1].xyz),
                  'ortho_height': 2.2 * H / W, 'res': [W, H]}
for f in info['frames']:
    scene.frame_set(f)
    info.setdefault('time', {})[str(f)] = scene.get('lida_aurora_time', f / 24.0)
    scene.render.filepath = os.path.join(out, 'blender_f%03d.png' % f)
    bpy.ops.render.render(write_still=True)
json.dump(info, open(os.path.join(out, 'scene.json'), 'w'), indent=1)
print('PRIM_DONE')
