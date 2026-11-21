# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Lida
"""Write what the Unity port needs from a blend that uses LidaAuroraToon.

blender -b <file.blend> --python tools/export_unity_spec.py -- <out_dir>

Reads only (nothing is saved). Writes
  <out_dir>/aurora_spec.json        every LidaAuroraToon material: preset, every input
                                    value, what feeds the image / normal / alpha inputs,
                                    attributes mapped onto inputs; the master levels,
                                    the time property and the glow settings
  <out_dir>/attr_<object>.json      per-vertex values of the attributes those
                                    materials read (position in Blender object space
                                    + value), so Unity can put them on its own vertices
  <out_dir>/other_materials.json    node graphs of materials without the shader
"""
import bpy, json, os, sys

out = sys.argv[sys.argv.index('--') + 1]
os.makedirs(out, exist_ok=True)
PROP = 'lida_aurora_toon_'


def val(v):
    try:
        return [round(float(x), 6) for x in v]
    except TypeError:
        return round(float(v), 6) if isinstance(v, float) else v


def trace(sock, depth=0):
    """Describe what feeds a socket (through simple pass-through nodes)."""
    if not sock.is_linked:
        return {'value': val(sock.default_value)}
    l = sock.links[0]
    n = l.from_node
    d = {'node': n.bl_idname, 'name': n.name, 'out': l.from_socket.name}
    if n.type == 'TEX_IMAGE':
        d['image'] = n.image.name if n.image else None
        d['colorspace'] = n.image.colorspace_settings.name if n.image else None
        d['interp'] = n.interpolation
        uv = n.inputs['Vector']
        if uv.is_linked:
            d['uv'] = trace(uv, depth + 1)
    elif n.type == 'NORMAL_MAP':
        d['strength'] = val(n.inputs['Strength'].default_value)
        d['space'] = n.space
        d['uv_map'] = n.uv_map
        d['color'] = trace(n.inputs['Color'], depth + 1)
    elif n.type == 'ATTRIBUTE':
        d['attribute'] = n.attribute_name
        d['attribute_type'] = n.attribute_type
    elif n.type == 'UVMAP':
        d['uv_map'] = n.uv_map
    elif n.type == 'MAP_RANGE':
        d['from_min'] = val(n.inputs['From Min'].default_value)
        d['from_max'] = val(n.inputs['From Max'].default_value)
        d['to_min'] = val(n.inputs['To Min'].default_value)
        d['to_max'] = val(n.inputs['To Max'].default_value)
        d['value'] = trace(n.inputs['Value'], depth + 1)
    elif depth < 6:
        d['inputs'] = {s.identifier: trace(s, depth + 1) for s in n.inputs if s.is_linked or s.type in ('VALUE', 'RGBA', 'VECTOR')}
    return d


def graph(mat):
    nt = mat.node_tree
    nodes = {}
    for n in nt.nodes:
        e = {'type': n.bl_idname, 'label': n.label}
        for k in ('operation', 'blend_type', 'data_type', 'attribute_name', 'attribute_type', 'uv_map', 'interpolation_type'):
            if hasattr(n, k):
                e[k] = getattr(n, k)
        if n.type == 'TEX_IMAGE' and n.image:
            e['image'] = n.image.name
        if n.type == 'VALTORGB':
            e['ramp'] = [(el.position, list(el.color)) for el in n.color_ramp.elements]
        e['inputs'] = {s.identifier: val(s.default_value) for s in n.inputs if hasattr(s, 'default_value') and not s.is_linked}
        nodes[n.name] = e
    links = [[l.from_node.name, l.from_socket.identifier, l.to_node.name, l.to_socket.identifier] for l in nt.links]
    return {'method': mat.surface_render_method, 'backface_culling': mat.use_backface_culling,
            'overlap': mat.use_transparency_overlap, 'nodes': nodes, 'links': links}


spec = {'blend': bpy.data.filepath, 'blender': bpy.app.version_string, 'materials': {}, 'objects': {}}
others = {}
attrs_needed = {}   # object -> set(attribute names)
for o in bpy.data.objects:
    if o.type != 'MESH':
        continue
    spec['objects'][o.name] = {'materials': [m.name if m else None for m in o.data.materials],
                               'matrix_world': [list(r) for r in o.matrix_world],
                               'uv_layers': [u.name for u in o.data.uv_layers],
                               'active_render_uv': next((u.name for u in o.data.uv_layers if u.active_render), None)}
    for m in o.data.materials:
        if m is None or not m.node_tree:
            continue
        toon = next((n for n in m.node_tree.nodes if n.type == 'GROUP' and n.node_tree
                     and n.node_tree.get(PROP + 'version')), None)
        active = next((n for n in m.node_tree.nodes if n.type == 'OUTPUT_MATERIAL' and n.is_active_output), None)
        if toon is None or active is None or not active.inputs['Surface'].is_linked:
            others[m.name] = graph(m)
            continue
        if m.name not in spec['materials']:
            d = {'preset': m.get(PROP + 'preset'), 'group': toon.node_tree.name,
                 'group_version': toon.node_tree.get(PROP + 'version'),
                 'method': m.surface_render_method, 'backface_culling': m.use_backface_culling,
                 'overlap': m.use_transparency_overlap, 'inputs': {}, 'links': {}}
            for s in toon.inputs:
                if s.is_linked:
                    d['links'][s.name] = trace(s)
                elif hasattr(s, 'default_value'):
                    d['inputs'][s.name] = val(s.default_value)
            spec['materials'][m.name] = d
            def collect(t):
                if isinstance(t, dict):
                    if t.get('attribute') and t.get('attribute_type', 'GEOMETRY') == 'GEOMETRY':
                        yield t['attribute']
                    for v in t.values():
                        yield from collect(v)
            for t in d['links'].values():
                for a in collect(t):
                    attrs_needed.setdefault(a, set())
            spec['materials'][m.name]['users'] = []
        spec['materials'][m.name]['users'].append(o.name)

# per-vertex attribute values for every object whose materials read one
for o in bpy.data.objects:
    if o.type != 'MESH':
        continue
    names = set()
    for m in o.data.materials:
        if m and m.name in spec['materials']:
            for t in spec['materials'][m.name]['links'].values():
                s = json.dumps(t)
                for a in attrs_needed:
                    if '"attribute": "%s"' % a in s:
                        names.add(a)
    if not names:
        continue
    me = o.data
    rec = {'object': o.name, 'count': len(me.vertices),
           'position': [round(c, 6) for v in me.vertices for c in v.co]}
    for a in sorted(names):
        at = me.attributes.get(a)
        if at is None or at.domain != 'POINT':
            rec.setdefault('missing', []).append(a)
            continue
        rec[a] = [round(x.value, 5) for x in at.data]
    json.dump(rec, open(os.path.join(out, 'attr_%s.json' % o.name), 'w'))

ctrl = bpy.data.objects.get('LidaAuroraToon Control')
spec['levels'] = {k: float(v) for k, v in ctrl.items() if isinstance(v, (int, float))} if ctrl else {}
sc = bpy.context.scene
spec['time_property'] = 'lida_aurora_time'
spec['fps'] = sc.render.fps
spec['view_transform'] = sc.view_settings.view_transform
ng = getattr(sc, 'compositing_node_group', None)
if ng is not None and 'Glow' in ng.nodes:
    gl = ng.nodes['Glow']
    spec['glow'] = {k: val(gl.inputs[k].default_value) for k in ('Highlights Threshold', 'Strength', 'Size') if k in gl.inputs}
lights = []
for o in sc.objects:
    if o.type == 'LIGHT':
        lights.append({'name': o.name, 'type': o.data.type, 'energy': o.data.energy, 'color': list(o.data.color),
                       'matrix_world': [list(r) for r in o.matrix_world]})
spec['lights'] = lights
json.dump(spec, open(os.path.join(out, 'aurora_spec.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
json.dump(others, open(os.path.join(out, 'other_materials.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print('SPEC', len(spec['materials']), 'materials,', len(others), 'others')
