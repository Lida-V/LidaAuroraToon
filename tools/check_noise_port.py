# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Lida
"""Check the noise port of the Unity shader against Blender's Noise Texture.

blender -b --factory-startup --python tools/check_noise_port.py

Evaluates the Noise Texture node (4D fBm) on 4000 random points with Geometry Nodes and compares it with
a straight port of Blender's Perlin noise (the same code as unity/.../LidaAuroraToonNoise.hlsl).
Prints NOISECMP with the largest difference per scale/detail (measured with Blender 5.3: up to 1.5e-5).
"""
import bpy, numpy as np, sys, json
rng = np.random.default_rng(3)
N = 4000
pts = rng.uniform(-3, 3, (N, 3)).astype(np.float32)
ws = rng.uniform(-2, 2, N).astype(np.float32)
cases = [(3.0, 1.0), (0.7, 1.0), (25.0, 2.0), (1.0, 3.0), (90.0, 2.0)]
me = bpy.data.meshes.new('pts'); me.from_pydata(pts.tolist(), [], []); me.update()
me.attributes.new('w', 'FLOAT', 'POINT').data.foreach_set('value', ws)
ob = bpy.data.objects.new('pts', me); bpy.context.scene.collection.objects.link(ob)
ng = bpy.data.node_groups.new('n', 'GeometryNodeTree')
ng.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
ng.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
gi = ng.nodes.new('NodeGroupInput'); go = ng.nodes.new('NodeGroupOutput')
pos = ng.nodes.new('GeometryNodeInputPosition')
wat = ng.nodes.new('GeometryNodeInputNamedAttribute'); wat.data_type = 'FLOAT'; wat.inputs['Name'].default_value = 'w'
geo = gi.outputs[0]
for k, (sc, det) in enumerate(cases):
    nz = ng.nodes.new('ShaderNodeTexNoise'); nz.noise_dimensions = '4D'
    ng.links.new(pos.outputs[0], nz.inputs['Vector']); ng.links.new(wat.outputs[0], nz.inputs['W'])
    nz.inputs['Scale'].default_value = sc; nz.inputs['Detail'].default_value = det; nz.inputs['Roughness'].default_value = 0.5
    st = ng.nodes.new('GeometryNodeStoreNamedAttribute'); st.data_type = 'FLOAT'; st.inputs['Name'].default_value = 'n%d' % k
    ng.links.new(geo, st.inputs['Geometry']); ng.links.new(nz.outputs['Fac'], st.inputs['Value']); geo = st.outputs[0]
ng.links.new(geo, go.inputs[0])
md = ob.modifiers.new('g', 'NODES'); md.node_group = ng
dg = bpy.context.evaluated_depsgraph_get(); ev = ob.evaluated_get(dg).data
ref = {}
for k in range(len(cases)):
    a = np.zeros(N, np.float32); ev.attributes['n%d' % k].data.foreach_get('value', a); ref[k] = a

# ---- port (uint32 arithmetic) ----
M = np.uint64(0xFFFFFFFF)
def rot(x, k): return ((x << np.uint64(k)) | (x >> np.uint64(32 - k))) & M
def hash4(kx, ky, kz, kw):
    a = b = c = np.full(kx.shape, (0xdeadbeef + (4 << 2) + 13) & 0xFFFFFFFF, np.uint64)
    a = (a + kx) & M; b = (b + ky) & M; c = (c + kz) & M
    # mix
    a = (a - c) & M; a ^= rot(c, 4); c = (c + b) & M
    b = (b - a) & M; b ^= rot(a, 6); a = (a + c) & M
    c = (c - b) & M; c ^= rot(b, 8); b = (b + a) & M
    a = (a - c) & M; a ^= rot(c, 16); c = (c + b) & M
    b = (b - a) & M; b ^= rot(a, 19); a = (a + c) & M
    c = (c - b) & M; c ^= rot(b, 4); b = (b + a) & M
    a = (a + kw) & M
    # final
    c ^= b; c = (c - rot(b, 14)) & M
    a ^= c; a = (a - rot(c, 11)) & M
    b ^= a; b = (b - rot(a, 25)) & M
    c ^= b; c = (c - rot(b, 16)) & M
    a ^= c; a = (a - rot(c, 4)) & M
    b ^= a; b = (b - rot(a, 14)) & M
    c ^= b; c = (c - rot(b, 24)) & M
    return c
def u(i): return (i.astype(np.int64) & 0xFFFFFFFF).astype(np.uint64)
def grad(h, x, y, z, w):
    h = h & np.uint64(31)
    uu = np.where(h < 24, x, y); vv = np.where(h < 16, y, z); ss = np.where(h < 8, z, w)
    return np.where(h & 1, -uu, uu) + np.where(h & 2, -vv, vv) + np.where(h & 4, -ss, ss)
def fade(t): return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)
def perlin(p):
    I = np.floor(p).astype(np.int64); f = (p - np.floor(p)).astype(np.float32)
    X, Y, Z, W = I[:, 0], I[:, 1], I[:, 2], I[:, 3]; fx, fy, fz, fw = f[:, 0], f[:, 1], f[:, 2], f[:, 3]
    v = []
    for dw in (0, 1):
        for dz in (0, 1):
            for dy in (0, 1):
                for dx in (0, 1):
                    v.append(grad(hash4(u(X + dx), u(Y + dy), u(Z + dz), u(W + dw)), fx - dx, fy - dy, fz - dz, fw - dw))
    U, V_, T, S = fade(fx), fade(fy), fade(fz), fade(fw)
    def lerp(a, b, t): return (1 - t) * a + t * b
    def bi(o): return lerp(lerp(v[o], v[o + 1], U), lerp(v[o + 2], v[o + 3], U), V_)
    def tri(o): return lerp(bi(o), bi(o + 4), T)
    return lerp(tri(0), tri(8), S)
def fbm(p, detail):
    fs, amp, mx, s = 1.0, 1.0, 0.0, 0.0
    for i in range(int(detail) + 1):
        s = s + 0.8344 * perlin(fs * p) * amp; mx += amp; amp *= 0.5; fs *= 2.0
    return 0.5 * s / mx + 0.5
res = {}
for k, (sc, det) in enumerate(cases):
    p = np.concatenate([pts, ws[:, None]], 1).astype(np.float64) * sc
    mine = fbm(p, det)
    d = np.abs(mine - ref[k])
    res['scale%g_detail%g' % (sc, det)] = {'max_abs': float(d.max()), 'mean_abs': float(d.mean()), 'ref_range': [float(ref[k].min()), float(ref[k].max())]}
print('NOISECMP', json.dumps(res))
