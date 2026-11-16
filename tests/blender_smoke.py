# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Lida
"""Smoke test on primitives only: blender -b --factory-startup --python tests/blender_smoke.py"""
import bpy, sys, os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'blender'))
from lida_aurora_toon import shader
from lida_aurora_toon.presets import PRESETS, TRANSLUCENT

scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
sun = shader.ensure_sun(scene)
names = {s[0] for s in shader.GROUP_INPUTS}
for preset, values in PRESETS.items():
    assert set(values) <= names, (preset, set(values) - names)
    bpy.ops.mesh.primitive_uv_sphere_add()
    obj = bpy.context.object
    mat = bpy.data.materials.new('T_' + preset)
    mat.use_nodes = True
    obj.data.materials.append(mat)
    before_method = mat.surface_render_method
    before_out = next(n for n in mat.node_tree.nodes if n.type == 'OUTPUT_MATERIAL' and n.is_active_output).name
    thick = ''
    if preset in TRANSLUCENT:
        lo, mean, hi = shader.bake_thickness(obj, full_thickness=0.5)
        assert 0.0 <= lo <= hi <= 1.0
        thick = shader.THICKNESS_ATTR
    toon = shader.apply_material(mat, preset, sun, thickness_attribute=thick, lighting='DRIVER')
    shader.apply_material(mat, preset, sun, thickness_attribute=thick, lighting='DRIVER')   # applying twice must not stack nodes
    assert sum(1 for n in mat.node_tree.nodes if n.type == 'GROUP') == 1
    assert (mat.surface_render_method == 'BLENDED') == (preset in TRANSLUCENT)
    shader.link_attribute(mat, shader.THICKNESS_ATTR, 'Aurora Strength', 0.5, 0.1)
    assert shader.restore_material(mat)
    assert mat.surface_render_method == before_method
    act = [n for n in mat.node_tree.nodes if n.type == 'OUTPUT_MATERIAL' and n.is_active_output]
    assert len(act) == 1 and act[0].name == before_out
    assert shader.restore_material(mat, remove_nodes=True) is True
    shader.apply_material(mat, preset, None)                             # default = Blender 5.3 lighting nodes
    assert mat['lida_aurora_toon_lighting'] == 'NODES'
    assert shader.find_toon_node(mat).node_tree.name == shader.GROUP_LIGHTS
    assert shader.restore_material(mat, remove_nodes=True) is True
    assert not any(n.get(shader.PROP + 'owned') for n in mat.node_tree.nodes)
    assert not any(k.startswith(shader.PROP) for k in mat.keys())
# one material stays applied so the group is part of the evaluated scene
shader.apply_material(mat, 'fin', sun, lighting='DRIVER')
group = bpy.data.node_groups[shader.GROUP]
drv = group.animation_data.drivers
assert len(drv) == 15, len(drv)         # 3 direction + 3 colour + energy + 8 master levels (the clock is on the scene)
assert all(d.driver.is_valid for d in drv)
scene.frame_set(49)
dg = bpy.context.evaluated_depsgraph_get()
# drivers write to the evaluated copy, not to the original datablock
t = scene.evaluated_get(dg)[shader.TIME_PROP]
assert abs(t - 49 / 24.0) < 1e-3, t
shader.set_level('Aurora', 0.25)
dg = bpy.context.evaluated_depsgraph_get()
lv = group.evaluated_get(dg).nodes['AuroraLevel'].outputs[0].default_value
assert abs(lv - 0.25) < 1e-4, lv
shader.unbind_time(group)
assert len(group.animation_data.drivers) == 15
assert scene[shader.TIME_PROP] == 0.0 and not (scene.animation_data and scene.animation_data.drivers)
shader.bind_time(group)
lg = bpy.data.node_groups[shader.GROUP_LIGHTS]
assert not any(n.type == 'SHADERTORGB' for n in lg.nodes)
assert len(lg.animation_data.drivers) == 8, len(lg.animation_data.drivers)   # time + 5 levels, no sun drivers
print('SMOKE OK presets=%d inputs=%d' % (len(PRESETS), len(shader.GROUP_INPUTS)))
