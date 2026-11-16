# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Lida
"""LidaAuroraToon: soft toon + nacre iridescence + aurora glow + translucency.

Derived from LidaAngelToon 0.2.1 (blender/lida_angel_toon/shader.py, node
group version 0.1.0, GPL-3.0-or-later, by the same author). The two-step toon
math is copied unchanged; the iridescence, aurora and translucency blocks are
new. No model names, geometry, textures or motion data are required.
"""
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from .presets import PRESETS, TRANSLUCENT

GROUP = "LidaAuroraToon"
GROUP_LIGHTS = "LidaAuroraToon Lights"
LIGHTING = ("DRIVER", "NODES")


def default_lighting():
    """NODES where the Material Lighting nodes exist (Blender 5.3+), else DRIVER."""
    return 'NODES' if hasattr(bpy.types, 'ShaderNodeLightAccumulation') else 'DRIVER'
VERSION = "0.3.6"
CONTROL = "LidaAuroraToon Control"
# slider name on the control object -> (value node in the group, default, max)
LEVELS = {"Aurora": ("AuroraLevel", 1.0, 3.0),
          "Aurora Speed": ("AuroraSpeedLevel", 1.0, 5.0),
          "Iridescence": ("IriLevel", 1.0, 3.0),
          "Glint": ("GlintLevel", 1.0, 3.0),
          # 0 = white light, 1 = as the material says, 2 = more colour
          "Glint Color": ("GlintColorLevel", 1.0, 2.0),
          # moves the whole glint palette (0..1 is one turn)
          "Glint Hue": ("GlintHueLevel", 0.0, 1.0),
          "Glint Speed": ("GlintSpeedLevel", 1.0, 5.0),
          # 0 = each material decides (Receive Shadow), 1 = every material receives cast shadows
          "Shadows": ("ShadowLevel", 0.0, 1.0)}
PROBE_CAL = 0.25464
PROP = "lida_aurora_toon_"
THICKNESS_ATTR = "lida_aurora_thickness"


def _sock(sockets, ident):
    for s in sockets:
        if s.identifier == ident:
            return s
    for s in sockets:
        if s.name == ident:
            return s
    raise KeyError(ident)


class NB:
    """node builder for one node tree"""

    def __init__(self, nt):
        self.nt = nt
        self.x = 0

    def node(self, typ, label=None, **kw):
        n = self.nt.nodes.new(typ)
        for k, v in kw.items():
            setattr(n, k, v)
        if label:
            n.label = label
            n.name = label
        n.location = (self.x, 0)
        self.x += 40
        return n

    def link(self, a, b):
        self.nt.links.new(a, b)

    def put(self, sock, v):
        if v is None:
            return
        if isinstance(v, bpy.types.NodeSocket):
            self.link(v, sock)
        else:
            sock.default_value = v

    def math(self, op, a, b=None, clamp=False, label=None):
        n = self.node('ShaderNodeMath', label, operation=op, use_clamp=clamp)
        self.put(n.inputs[0], a)
        if b is not None:
            self.put(n.inputs[1], b)
        return n.outputs[0]

    def vmath(self, op, a, b=None, scale=None, label=None):
        n = self.node('ShaderNodeVectorMath', label, operation=op)
        self.put(n.inputs[0], a)
        if b is not None:
            self.put(n.inputs[1], b)
        if scale is not None:
            self.put(n.inputs[3], scale)
        return n

    def mix(self, fac, a, b, blend='MIX', clamp=False, label=None):
        n = self.node('ShaderNodeMix', label, data_type='RGBA', blend_type=blend, clamp_result=clamp)
        self.put(_sock(n.inputs, 'Factor_Float'), fac)
        self.put(_sock(n.inputs, 'A_Color'), a)
        self.put(_sock(n.inputs, 'B_Color'), b)
        return _sock(n.outputs, 'Result_Color')

    def fmix(self, fac, a, b, label=None):
        n = self.node('ShaderNodeMix', label, data_type='FLOAT')
        self.put(_sock(n.inputs, 'Factor_Float'), fac)
        self.put(_sock(n.inputs, 'A_Float'), a)
        self.put(_sock(n.inputs, 'B_Float'), b)
        return _sock(n.outputs, 'Result_Float')

    def smooth(self, val, lo, hi, label=None):
        """smoothstep(lo, hi, val) -> 0..1"""
        n = self.node('ShaderNodeMapRange', label, data_type='FLOAT', interpolation_type='SMOOTHSTEP', clamp=True)
        self.put(_sock(n.inputs, 'Value'), val)
        self.put(_sock(n.inputs, 'From Min'), lo)
        self.put(_sock(n.inputs, 'From Max'), hi)
        _sock(n.inputs, 'To Min').default_value = 0.0
        _sock(n.inputs, 'To Max').default_value = 1.0
        return _sock(n.outputs, 'Result')

    def noise(self, vec, w, scale, detail=1.0, label=None):
        n = self.node('ShaderNodeTexNoise', label, noise_dimensions='4D')
        self.put(n.inputs['Vector'], vec)
        self.put(n.inputs['W'], w)
        self.put(n.inputs['Scale'], scale)
        n.inputs['Detail'].default_value = detail
        n.inputs['Roughness'].default_value = 0.5
        return n.outputs[0]


C = 'NodeSocketColor'
F = 'NodeSocketFloat'
V3 = 'NodeSocketVector'

# --- copied from LidaAngelToon (toon part; MatCap inputs are not carried over) ---
TOON_INPUTS = [
    ('Base Color', C, (1, 1, 1, 1), '基本色（元の材質の基本色の画像をそのままつなぐ）'),
    ('Shade Texture', C, (1, 1, 1, 1), '影色の画像（ある時だけ）'),
    ('Use Shade Texture', F, 0.0, '1＝影色を画像から、0＝基本色から'),
    ('Shade Tint 1', C, (0.82, 0.8, 0.9, 1), '1 段目の影の色味（基本色に掛ける）'),
    ('Shade Shift 1', F, 0.0, '1 段目の影の境目の位置（N·L、−1〜1）。大きいほど影が広い'),
    ('Shade Soft 1', F, 0.25, '1 段目の境目のやわらかさ'),
    ('Shade Tint 2', C, (0.88, 0.88, 0.94, 1), '2 段目の影の色味（1 段目にさらに掛ける）'),
    ('Shade Shift 2', F, -0.5, '2 段目の境目の位置'),
    ('Shade Soft 2', F, 0.3, '2 段目の境目のやわらかさ'),
    ('Receive Shadow', F, 0.0, '落ち影を受ける強さ（0＝受けない）'),
    ('Normal Override', V3, (0, 0, 0), '向きの差し替え（使うときだけ）'),
    ('Normal Override Mix', F, 0.0, '向きの差し替えの割合'),
    ('Lit Tint', C, (1, 1, 1, 1), '明るい所の色味'),
    ('Rim Color', C, (0.9, 0.92, 1.0, 1), '縁の光の色'),
    ('Rim Strength', F, 0.0, '縁の光の強さ（足す）'),
    ('Rim Width', F, 0.25, '縁の光の幅'),
    ('Rim Soft', F, 0.15, '縁の光のやわらかさ'),
    ('Rim Lit Bias', F, 0.5, '縁の光を明るい側だけに寄せる割合（0＝全周）'),
    ('Spec Color', C, (1, 1, 1, 1), 'つやの色'),
    ('Spec Strength', F, 0.0, 'つやの強さ（足す）'),
    ('Spec Size', F, 0.97, 'つやの大きさ（1 に近いほど小さい）'),
    ('Spec Soft', F, 0.02, 'つやの縁のやわらかさ'),
    ('Unlit', F, 0.0, '光に関係なく基本色を見せる割合（目など）'),
    ('Highlight Knee', F, 0.85, '明るすぎる所を 1.0 へなだらかに寄せ始める明るさ（1＝しない）'),
    ('Occlusion', F, 1.0, '奥の暗さ（焼いた AO、1＝開いている）'),
    ('Occlusion Shift', F, 0.0, '奥まった所で光を下げる量'),
    ('Occlusion Darken', F, 0.0, '奥まった所に影 2 の色味をさらに掛ける割合'),
    ('Terminator Color', C, (1.0, 0.75, 0.73, 1), '明るい所から影へ移る所の細い帯の色（掛ける）'),
    ('Terminator Strength', F, 0.0, 'その帯の強さ'),
    ('Terminator Width', F, 0.1, 'その帯の幅'),
    ('Base Lift', F, 0.0, '基本色を Base Lift Color へ寄せる割合'),
    ('Base Lift Color', C, (1.0, 0.97, 0.96, 1), '寄せる先の色'),
    ('Base Saturation', F, 1.0, '基本色の彩度（1＝そのまま）'),
]

# --- new in LidaAuroraToon ---
AURORA_INPUTS = [
    ('Effect Mask', F, 1.0, '真珠層とオーロラを出す場所の割合（画像や頂点の値をつなぐ。1＝全部）'),
    # nacre iridescence
    ('Iri Strength', F, 0.0, '真珠層の虹色で色味を染める強さ（明るさはほぼ変えない）'),
    ('Iri Add', F, 0.0, '真珠層の虹色を光として足す強さ（縁ほど強い）'),
    ('Iri Scale', F, 1.2, '色の幅：正面から縁までに色相が何周するか'),
    ('Iri Shift', F, 0.0, '色のずれ：色相の出発点（0＝赤、0.33＝緑、0.5＝水色、0.66＝青、0.83＝桃紫）'),
    ('Iri Hue Range', F, 1.0, '色の範囲：出発点からどこまで色相を進めるか（1＝虹の全部、0.4＝となりの色まで）'),
    ('Iri Saturation', F, 0.55, '虹色のあざやかさ'),
    ('Iri Edge Bias', F, 0.3, '0＝面全体に出す、1＝縁（斜めに見る所）だけに出す'),
    ('Iri Base Phase', F, 0.0, '基本色の明るさで色相をずらす量（うろこ 1 枚ずつ色を変える）'),
    ('Iri Grain', F, 0.0, '粗さ：細かいむらで色相をゆらす量'),
    ('Iri Grain Scale', F, 60.0, 'むらの細かさ'),
    ('Iri Shade Keep', F, 0.35, '影の中に虹色を残す割合（0＝影では消す）'),
    # aurora
    ('Aurora Strength', F, 0.0, 'オーロラの光の強さ（自分で光る。影でも消えない）'),
    ('Aurora Coord', V3, (0, 0, 0), '帯を作る座標（物体座標か UV をつなぐ）'),
    ('Aurora Direction', V3, (0, 0, 1), '帯が流れる向き（座標の中の向き）'),
    ('Aurora Band Scale', F, 3.0, '帯の細かさ（向きに沿って 1 単位に何本か）'),
    ('Aurora Streak Scale', F, 25.0, 'すじの細かさ（流れに沿う細いすじ）'),
    ('Aurora Streak', F, 0.6, 'すじの濃さ（0＝帯だけ）'),
    ('Aurora Distort', F, 0.6, '帯のゆらぎの大きさ'),
    ('Aurora Curtain', F, 0.0, '流れ方：0＝帯が向きに沿って流れる、1＝縦のひだが横へはためく（カーテン）'),
    ('Aurora Sway', F, 0.5, 'カーテンのはためきの大きさ'),
    ('Aurora Noise', F, 0.0, '不ぞろいさ（0＝規則的な波、1＝ノイズでひだの形と濃さがばらつく）'),
    ('Aurora Sharpness', F, 2.0, '帯の細さ（大きいほど細い帯）'),
    ('Aurora Speed', F, 0.15, '流れる速さ（1 秒に何本ぶん進むか）'),
    ('Aurora Phase', F, 0.0, '流れの位置（キーやドライバーで動かせる）'),
    ('Aurora Hue Shift', F, 0.0, '色の出発点（色の帯の中の位置、0〜1）'),
    ('Aurora Hue Spread', F, 0.5, '向きに沿って色がどれだけ移るか'),
    ('Aurora Tint', C, (1, 1, 1, 1), 'オーロラの色に掛ける色'),
    ('Aurora Edge Boost', F, 0.5, '縁でオーロラを強める量'),
    # translucency
    ('Alpha', F, 1.0, '元の材質の不透明度（画像の Alpha）'),
    ('Opacity', F, 1.0, '正面から見た薄い所の不透明度（1＝透けない）'),
    ('Edge Opacity', F, 1.0, '縁（斜めに見る所）の不透明度'),
    ('Thickness', F, 0.0, '厚み（0＝薄い、1＝厚い＝透けない）。頂点の値 lida_aurora_thickness'),
    ('Transmit Color', C, (1.0, 0.85, 0.95, 1), '裏から抜ける光の色（基本色に掛ける）'),
    ('Transmit Strength', F, 0.0, '裏から光が抜ける強さ（薄い所の影が明るくなる）'),
    ('Aurora Alpha', F, 0.5, 'オーロラが光っている所を不透明に寄せる量'),
    # glint: a thin light that moves with the viewing angle (hair)
    ('Glint Strength', F, 0.0, '角度で動く光の筋の強さ（自分で光る。0＝出さない）'),
    ('Glint Height', F, 0.3, '光の帯の位置：面がカメラから見てどれだけ上を向いた所に出すか（−1〜1）'),
    ('Glint Width', F, 0.1, '光の帯の幅'),
    ('Glint Streak', F, 0.85, '筋への分かれ方（0＝帯のまま、1＝細い筋だけ）'),
    ('Glint Streak Scale', F, 70.0, '筋の細かさ'),
    ('Glint Coverage', F, 0.45, '光る束の割合（0＝どこも光らない、1＝全部）'),
    ('Glint Patch Scale', F, 6.0, '光る束のまとまりの細かさ'),
    ('Glint Band', F, 1.0, '面の中に出る光の帯の量（0＝帯を出さず輪郭だけ）'),
    ('Glint Edge', F, 0.25, '輪郭（斜めに見る所）に光を出す量'),
    ('Glint Edge Width', F, 0.4, '輪郭の光の幅（大きいほど内側まで広がる）'),
    ('Glint Hue Shift', F, 0.62, '光の色の出発点（色の帯の中の位置、0〜1）'),
    ('Glint Hue Spread', F, 0.3, '見る角度で色がどれだけ移るか'),
    ('Glint Softness', F, 0.0, '光の境目のやわらかさ（0＝くっきり、1＝広くぼかす）'),
    ('Glint Flow', F, 0.0, '光る場所が時間で移る速さ（0＝動かない）'),
    ('Glint Hue Vary', F, 0.0, '場所ごとの色のばらつき（オーロラのように色が流れて見える量）'),
    ('Glint Hue Speed', F, 0.0, '時間で色が移る速さ（1 秒に色の帯を何周するか）'),
    ('Glint White', F, 0.4, '光を白へ寄せる量（1＝ほぼ白い光、0＝色の光）'),
    ('Glint Glow', F, 0.0, '光の明るさの上乗せ（1 を超えた分がにじみ（グロー）になる）'),
]

GROUP_INPUTS = TOON_INPUTS + AURORA_INPUTS

# glint palette: pink -> lavender -> sky -> aqua -> lavender -> pink (wraps)
GLINT_RAMP = [
    (0.00, (1.00, 0.42, 0.74)),
    (0.22, (0.76, 0.48, 1.00)),
    (0.45, (0.42, 0.62, 1.00)),
    (0.62, (0.36, 0.95, 0.92)),
    (0.82, (0.70, 0.55, 1.00)),
    (1.00, (1.00, 0.42, 0.74)),
]

# aurora palette: green -> cyan -> blue -> violet -> pink -> green (wraps)
AURORA_RAMP = [
    (0.00, (0.25, 1.00, 0.62)),
    (0.22, (0.20, 0.85, 1.00)),
    (0.45, (0.38, 0.48, 1.00)),
    (0.65, (0.72, 0.42, 1.00)),
    (0.85, (1.00, 0.52, 0.82)),
    (1.00, (0.25, 1.00, 0.62)),
]


def group_name(lighting='DRIVER'):
    if lighting not in LIGHTING:
        raise ValueError('lighting must be DRIVER or NODES')
    return GROUP if lighting == 'DRIVER' else GROUP_LIGHTS


def build_group(lighting='DRIVER'):
    """Build (or return) the node group.

    lighting='DRIVER': one sun, read through drivers (bind_sun); works on Blender 5.2.
    lighting='NODES' : Blender 5.3 Material Lighting nodes. Every light of the
        scene (sun, point, spot, area; colour and falloff) shades the toon
        steps, cast shadows come from Shadow Raycast, and no driver is needed.
    """
    name = group_name(lighting)
    if name in bpy.data.node_groups:
        group = bpy.data.node_groups[name]
        if group.get(PROP + 'version') != VERSION:
            raise ValueError('A different %s node group already exists; rename it before applying' % name)
        return group
    if lighting == 'NODES' and not hasattr(bpy.types, 'ShaderNodeLightAccumulation'):
        raise ValueError('lighting=NODES needs the Material Lighting nodes of Blender 5.3 or newer')
    nt = bpy.data.node_groups.new(name, 'ShaderNodeTree')
    nt.description = 'LidaAuroraToon %s: soft toon with nacre iridescence, aurora glow and translucency.' % VERSION
    nt[PROP + 'version'] = VERSION
    nt[PROP + 'lighting'] = lighting
    for sname, typ, dv, desc in GROUP_INPUTS:
        s = nt.interface.new_socket(sname, in_out='INPUT', socket_type=typ)
        s.description = desc
        try:
            s.default_value = dv
        except Exception:
            pass
        if typ == F:
            s.min_value, s.max_value = (-1000.0, 1000.0)
    nt.interface.new_socket('Shader', in_out='OUTPUT', socket_type='NodeSocketShader')
    nt.interface.new_socket('Color', in_out='OUTPUT', socket_type=C)
    nt.interface.new_socket('Lit', in_out='OUTPUT', socket_type=F)
    nt.interface.new_socket('Alpha', in_out='OUTPUT', socket_type=F)
    b = NB(nt)
    gi = b.node('NodeGroupInput', 'In')
    go = b.node('NodeGroupOutput', 'Out')
    I = {s.name: s for s in gi.outputs}
    # clock: a scene custom property read as a View Layer attribute (a uniform;
    # a driven value node here would rebuild the materials on every frame)
    tm = b.node('ShaderNodeAttribute', 'AuroraTime')
    tm.attribute_type = 'VIEW_LAYER'
    tm.attribute_name = 'lida_aurora_time'
    LV = {}
    for _name, (_node, _default, _max) in LEVELS.items():
        _n = b.node('ShaderNodeValue', _node)
        _n.outputs[0].default_value = _default
        LV[_name] = _n.outputs[0]
    geo = b.node('ShaderNodeNewGeometry', 'Geometry')

    nmix = b.node('ShaderNodeMix', 'NormalMix', data_type='VECTOR')
    b.put(_sock(nmix.inputs, 'Factor_Float'), I['Normal Override Mix'])
    b.put(_sock(nmix.inputs, 'A_Vector'), geo.outputs['Normal'])
    b.put(_sock(nmix.inputs, 'B_Vector'), I['Normal Override'])
    N = b.vmath('NORMALIZE', _sock(nmix.outputs, 'Result_Vector'), label='N').outputs[0]
    V = b.vmath('NORMALIZE', geo.outputs['Incoming'], label='V').outputs[0]

    # ---------- things that do not depend on a light ----------
    occ = b.smooth(b.math('SUBTRACT', 1.0, I['Occlusion']), 0.05, 0.9, label='Occ')
    open_ = b.math('SUBTRACT', 1.0, occ, label='Open')
    base = b.mix(I['Base Lift'], I['Base Color'], I['Base Lift Color'], label='BaseLift')
    bbw = b.node('ShaderNodeRGBToBW', 'BaseGray')
    b.link(base, bbw.inputs[0])
    base_lum = bbw.outputs[0]
    base = b.mix(I['Base Saturation'], base_lum, base, label='BaseSaturation')
    shade_src = b.mix(I['Use Shade Texture'], base, I['Shade Texture'], label='ShadeSource')
    shade1 = b.mix(1.0, shade_src, I['Shade Tint 1'], blend='MULTIPLY', label='Shade1')
    shade2 = b.mix(1.0, shade1, I['Shade Tint 2'], blend='MULTIPLY', label='Shade2')
    lit0 = b.mix(1.0, base, I['Lit Tint'], blend='MULTIPLY', label='LitA')
    # two-sided view term: a thin membrane seen from behind behaves like its front
    nv = b.math('ABSOLUTE', b.vmath('DOT_PRODUCT', N, V).outputs[1], label='NdotV')
    fres = b.math('SUBTRACT', 1.0, nv, clamp=True, label='Fresnel')
    thin = b.math('SUBTRACT', 1.0, I['Thickness'], clamp=True, label='Thin')
    edge = b.smooth(fres, 0.15, 0.85, label='IriEdge')

    # nacre colour
    grain = b.noise(geo.outputs['Position'], 0.0, I['Iri Grain Scale'], detail=2.0, label='IriGrainNoise')
    ph = b.math('MULTIPLY', fres, I['Iri Scale'])
    ph = b.math('ADD', ph, b.math('MULTIPLY', base_lum, I['Iri Base Phase']))
    ph = b.math('ADD', ph, b.math('MULTIPLY', b.math('SUBTRACT', grain, 0.5), I['Iri Grain']))
    # triangle wave: the hue walks Shift -> Shift+Range and back, never jumping
    tri = b.math('ABSOLUTE', b.math('SUBTRACT', b.math('MULTIPLY', b.math('FRACT', ph), 2.0), 1.0))
    tri = b.math('SUBTRACT', 1.0, tri, label='IriTriangle')
    hue = b.math('FRACT', b.math('ADD', I['Iri Shift'], b.math('MULTIPLY', tri, I['Iri Hue Range'])), label='IriHue')
    hsv = b.node('ShaderNodeCombineColor', 'IriColor', mode='HSV')
    b.put(hsv.inputs[0], hue)
    b.put(hsv.inputs[1], I['Iri Saturation'])
    hsv.inputs[2].default_value = 1.0
    iri = hsv.outputs[0]
    # keep brightness: divide by the mean of the three channels
    mean = b.vmath('DOT_PRODUCT', iri, (0.3333, 0.3333, 0.3333)).outputs[1]
    iri_n = b.vmath('SCALE', iri, scale=b.math('DIVIDE', 1.0, b.math('MAXIMUM', mean, 0.05))).outputs[0]
    iri_where = b.fmix(I['Iri Edge Bias'], 1.0, edge, label='IriEdgeBias')
    iri_gate = b.math('MULTIPLY', b.math('MULTIPLY', open_, I['Effect Mask']), LV['Iridescence'], label='IriGate')

    # rim shape
    rlo = b.math('SUBTRACT', b.math('SUBTRACT', 1.0, I['Rim Width']), I['Rim Soft'])
    rhi = b.math('ADD', b.math('SUBTRACT', 1.0, I['Rim Width']), I['Rim Soft'])
    rim = b.smooth(fres, rlo, rhi, label='Rim')

    # aurora
    D = b.vmath('NORMALIZE', I['Aurora Direction'], label='AuroraDir').outputs[0]
    P = I['Aurora Coord']
    s = b.vmath('DOT_PRODUCT', P, D, label='AuroraAlong').outputs[1]
    phase = b.math('ADD', b.math('MULTIPLY', b.math('MULTIPLY', tm.outputs['Fac'], LV['Aurora Speed']), I['Aurora Speed']), I['Aurora Phase'], label='AuroraPhase')
    # slow, large wobble that bends the bands
    wob = b.noise(P, b.math('MULTIPLY', phase, 0.35), b.math('MULTIPLY', I['Aurora Band Scale'], 0.7), detail=1.0, label='AuroraWobble')
    wobc = b.math('MULTIPLY', b.math('SUBTRACT', wob, 0.5), I['Aurora Distort'])
    u_flow = b.math('ADD', b.math('SUBTRACT', b.math('MULTIPLY', s, I['Aurora Band Scale']), phase), wobc, label='AuroraUFlow')
    # curtain: the folds run along the direction and sway sideways; nothing travels along it
    side = b.vmath('NORMALIZE', b.vmath('CROSS_PRODUCT', D, (0.35, 0.94, 0.12)).outputs[0], label='AuroraSide').outputs[0]
    cs = b.vmath('DOT_PRODUCT', P, side, label='AuroraAcross').outputs[1]
    tsw = b.math('MULTIPLY', phase, 6.2831853)
    # the sway is bigger further down the cloth, like a hanging curtain, and travels as a wave
    sw1 = b.math('SINE', b.math('SUBTRACT', b.math('MULTIPLY', s, 2.0), b.math('MULTIPLY', tsw, 0.35)))
    sw2 = b.math('SINE', b.math('ADD', b.math('MULTIPLY', s, 4.5), b.math('MULTIPLY', tsw, 0.2)))
    swn = b.noise(b.vmath('SCALE', P, scale=0.6).outputs[0], b.math('MULTIPLY', phase, 0.5), 1.0, detail=1.0, label='AuroraSwayNoise')
    sway = b.math('ADD', b.math('ADD', b.math('MULTIPLY', sw1, 0.6), b.math('MULTIPLY', sw2, 0.15)), b.math('MULTIPLY', b.math('SUBTRACT', swn, 0.5), 1.0))
    # irregularity: the regular waves give way to a slow noise that bends the folds
    anz = I['Aurora Noise']
    sway = b.math('MULTIPLY', sway, b.math('SUBTRACT', 1.0, b.math('MULTIPLY', anz, 0.7), clamp=True))
    wn1 = b.noise(b.vmath('SCALE', P, scale=1.3).outputs[0], b.math('MULTIPLY', phase, 0.3), 1.0, detail=3.0, label='AuroraWarpNoise')
    wn2 = b.noise(b.vmath('ADD', b.vmath('SCALE', P, scale=3.1).outputs[0], (7.3, 2.1, 4.7)).outputs[0], b.math('MULTIPLY', phase, 0.45), 1.0, detail=2.0, label='AuroraWarpNoise2')
    warp = b.math('ADD', b.math('MULTIPLY', b.math('SUBTRACT', wn1, 0.5), 3.0), b.math('MULTIPLY', b.math('SUBTRACT', wn2, 0.5), 0.9))
    u_curt = b.math('ADD', b.math('MULTIPLY', cs, b.math('MULTIPLY', I['Aurora Band Scale'], 1.4)), b.math('MULTIPLY', sway, I['Aurora Sway']))
    u_curt = b.math('ADD', u_curt, b.math('MULTIPLY', warp, anz), label='AuroraUCurtain')
    gn = b.noise(b.vmath('ADD', b.vmath('SCALE', P, scale=0.9).outputs[0], (3.7, 9.2, 1.4)).outputs[0], b.math('MULTIPLY', phase, 0.22), 1.0, detail=2.0, label='AuroraGapNoise')
    agate = b.fmix(b.math('MULTIPLY', anz, 1.0, clamp=True), 1.0, b.math('ADD', 0.4, b.math('MULTIPLY', b.smooth(gn, 0.3, 0.7), 1.3)), label='AuroraGate')
    u = b.fmix(I['Aurora Curtain'], u_flow, u_curt, label='AuroraU')
    wave = b.math('ADD', 0.5, b.math('MULTIPLY', 0.5, b.math('SINE', b.math('MULTIPLY', u, 6.2831853))))
    bandv = b.math('POWER', wave, b.math('MAXIMUM', I['Aurora Sharpness'], 0.05), label='AuroraBand')
    # fine streaks that run along the flow: sample noise mostly across the direction
    across = b.vmath('SUBTRACT', P, b.vmath('SCALE', D, scale=b.math('MULTIPLY', s, 0.94)).outputs[0]).outputs[0]
    stn = b.noise(across, b.math('MULTIPLY', phase, b.fmix(I['Aurora Curtain'], 0.6, 0.08)), I['Aurora Streak Scale'], detail=2.0, label='AuroraStreakNoise')
    streak = b.fmix(I['Aurora Streak'], 1.0, b.smooth(stn, 0.3, 0.75), label='AuroraStreak')
    a_edge = b.math('ADD', 1.0, b.math('MULTIPLY', edge, I['Aurora Edge Boost']))
    a_int = b.math('MULTIPLY', b.math('MULTIPLY', b.math('MULTIPLY', bandv, streak), a_edge), agate, label='AuroraIntensity')
    a_amt = b.math('MULTIPLY', b.math('MULTIPLY', a_int, I['Aurora Strength']), I['Effect Mask'])
    a_amt = b.math('MULTIPLY', a_amt, LV['Aurora'], label='AuroraAmount')
    hidx = b.math('ADD', b.math('ADD', b.math('MULTIPLY', s, I['Aurora Hue Spread']), b.math('MULTIPLY', wob, 0.6)), I['Aurora Hue Shift'])
    hidx = b.math('FRACT', b.math('ADD', hidx, b.math('MULTIPLY', phase, 0.12)), label='AuroraHue')
    ramp = b.node('ShaderNodeValToRGB', 'AuroraRamp')
    cr = ramp.color_ramp
    cr.interpolation = 'LINEAR'
    while len(cr.elements) < len(AURORA_RAMP):
        cr.elements.new(0.5)
    for el, (pos, col) in zip(cr.elements, AURORA_RAMP):
        el.position = pos
        el.color = (*col, 1.0)
    b.link(hidx, ramp.inputs[0])
    acol = b.mix(1.0, ramp.outputs[0], I['Aurora Tint'], blend='MULTIPLY', label='AuroraColor')

    # glint: a band where the surface tilts a fixed amount upward as seen from the
    # camera, so it slides over the hair when the head or the camera turns.
    # Broken into strands and limited to some locks; independent of the lights.
    vt = b.node('ShaderNodeVectorTransform', 'GlintViewN')
    vt.vector_type = 'NORMAL'
    vt.convert_from = 'WORLD'
    vt.convert_to = 'CAMERA'
    b.link(N, vt.inputs['Vector'])   # inputs[0] is a hidden socket in Blender 5.3
    vsep = b.node('ShaderNodeSeparateXYZ', 'GlintViewNSep')
    b.link(vt.outputs[0], vsep.inputs[0])
    gy = b.math('ABSOLUTE', b.math('SUBTRACT', vsep.outputs[1], I['Glint Height']))
    gband = b.math('SUBTRACT', 1.0, b.smooth(gy, 0.0, b.math('MAXIMUM', I['Glint Width'], 0.001)), label='GlintBand')
    gstn = b.noise(across, 0.0, I['Glint Streak Scale'], detail=2.0, label='GlintStreakNoise')
    gstreak = b.fmix(I['Glint Streak'], 1.0, b.smooth(gstn, 0.5, 0.68), label='GlintStreak')
    gclock = b.math('MULTIPLY', tm.outputs['Fac'], LV['Glint Speed'], label='GlintClock')
    gsoft = b.math('MAXIMUM', I['Glint Softness'], 0.0)
    gpn = b.noise(P, b.math('MULTIPLY', gclock, I['Glint Flow']), I['Glint Patch Scale'], detail=1.0, label='GlintPatchNoise')
    gth = b.math('SUBTRACT', 0.75, b.math('MULTIPLY', I['Glint Coverage'], 0.5))
    gcw = b.math('ADD', 0.08, b.math('MULTIPLY', gsoft, 0.22))
    gcov = b.smooth(gpn, b.math('SUBTRACT', gth, gcw), b.math('ADD', gth, gcw), label='GlintCoverage')
    # the outline uses the mesh normal, not the normal map: a normal map makes
    # 'edge' patches in the middle of a lock
    gnv = b.math('ABSOLUTE', b.vmath('DOT_PRODUCT', b.vmath('NORMALIZE', geo.outputs['Normal']).outputs[0], V).outputs[1])
    gfres = b.math('SUBTRACT', 1.0, gnv, clamp=True, label='GlintFresnel')
    gelo = b.math('SUBTRACT', 1.0, I['Glint Edge Width'])
    gelo2 = b.math('SUBTRACT', gelo, b.math('MULTIPLY', gsoft, 0.25))
    gehi = b.math('ADD', gelo, b.math('ADD', 0.35, b.math('MULTIPLY', gsoft, 0.25)))
    gedge = b.math('MULTIPLY', b.math('POWER', b.smooth(gfres, gelo2, gehi), b.math('ADD', 1.0, gsoft)), I['Glint Edge'], label='GlintEdge')
    gband_k = b.math('MULTIPLY', gband, I['Glint Band'])
    g_int = b.math('MULTIPLY', b.math('MULTIPLY', b.math('ADD', gband_k, gedge), gstreak), gcov, label='GlintIntensity')
    g_amt = b.math('MULTIPLY', b.math('MULTIPLY', g_int, I['Glint Strength']), b.math('MULTIPLY', I['Effect Mask'], open_))
    g_amt = b.math('MULTIPLY', g_amt, LV['Glint'], label='GlintAmount')
    ghi = b.math('ADD', I['Glint Hue Shift'], b.math('MULTIPLY', b.math('MULTIPLY', vsep.outputs[0], 0.5), I['Glint Hue Spread']))
    ghn = b.noise(P, b.math('MULTIPLY', gclock, 0.25), 2.5, detail=1.0, label='GlintHueNoise')
    ghi = b.math('ADD', ghi, b.math('MULTIPLY', b.math('SUBTRACT', ghn, 0.5), I['Glint Hue Vary']))
    ghi = b.math('ADD', ghi, b.math('ADD', LV['Glint Hue'], b.math('MULTIPLY', gclock, I['Glint Hue Speed'])))
    ghi = b.math('FRACT', b.math('ADD', b.math('ADD', ghi, b.math('MULTIPLY', fres, 0.15)), 2.0), label='GlintHue')
    gramp = b.node('ShaderNodeValToRGB', 'GlintRamp')
    gcr = gramp.color_ramp
    gcr.interpolation = 'LINEAR'
    while len(gcr.elements) < len(GLINT_RAMP):
        gcr.elements.new(0.5)
    for el, (pos, col) in zip(gcr.elements, GLINT_RAMP):
        el.position = pos
        el.color = (*col, 1.0)
    b.link(ghi, gramp.inputs[0])
    gwhite = b.math('SUBTRACT', 1.0, b.math('MULTIPLY', b.math('SUBTRACT', 1.0, I['Glint White']), LV['Glint Color']), clamp=True, label='GlintWhite')
    gcore = b.math('MULTIPLY', b.math('MULTIPLY', g_int, 1.0, clamp=True), gwhite, clamp=True)
    # the aurora palette is pale; a glint needs a deeper colour to read on light hair
    gsat = b.node('ShaderNodeHueSaturation', 'GlintSaturate')
    gsat.inputs['Saturation'].default_value = 1.25
    gsat.inputs['Value'].default_value = 1.0
    b.link(gramp.outputs[0], gsat.inputs['Color'])
    gcol = b.mix(gcore, gsat.outputs[0], (1.0, 1.0, 1.0, 1.0), label='GlintColor')
    # on pale hair an added light only clips to white: pull the colour towards
    # the glint colour first, then add a little light on top
    # soft shoulder instead of a hard clip, so the light fades into the hair
    g_hard = b.math('MULTIPLY', g_amt, 1.0, clamp=True)
    g_sat = b.math('SUBTRACT', 1.0, b.math('EXPONENT', b.math('MULTIPLY', g_amt, -1.1)))
    g_mix = b.fmix(b.math('MINIMUM', gsoft, 1.0), g_hard, g_sat, label='GlintMix')
    g_keep = b.math('SUBTRACT', 1.0, g_mix, label='GlintKeep')
    g_rgb = b.vmath('SCALE', gcol, scale=b.math('MULTIPLY', g_amt, b.math('ADD', 0.3, I['Glint Glow'])), label='GlintLight').outputs[0]

    def add_glint(col):
        return b.vmath('ADD', b.mix(g_mix, col, gcol, label='GlintTint'), g_rgb, label='AddGlint').outputs[0]

    def surface(tag, Ls0, L, kcol):
        """The whole look for one light. Ls0 = N.L after cast shadows (None = no light at all)."""
        lit = lit0 if kcol is None else b.mix(1.0, lit0, kcol, blend='MULTIPLY', label='LitB' + tag)
        if Ls0 is None:
            t1 = t2 = 0.0
            c = shade2
            band = 0.0
        else:
            Ls = b.math('SUBTRACT', Ls0, b.math('MULTIPLY', occ, I['Occlusion Shift']), label='Ls_occ' + tag)
            t1 = b.smooth(Ls, b.math('SUBTRACT', I['Shade Shift 1'], I['Shade Soft 1']), b.math('ADD', I['Shade Shift 1'], I['Shade Soft 1']), label='t1_lit' + tag)
            t2 = b.smooth(Ls, b.math('SUBTRACT', I['Shade Shift 2'], I['Shade Soft 2']), b.math('ADD', I['Shade Shift 2'], I['Shade Soft 2']), label='t2_shade1' + tag)
            c = b.mix(t2, shade2, shade1, label='Shade12' + tag)
            c = b.mix(t1, c, lit, label='LitShade' + tag)
            s1 = I['Shade Shift 1']
            band = b.math('MULTIPLY', b.smooth(Ls, b.math('SUBTRACT', s1, I['Terminator Width']), s1), b.math('SUBTRACT', 1.0, b.smooth(Ls, s1, b.math('ADD', s1, I['Terminator Width']))), label='TermBand' + tag)
            c = b.mix(b.math('MULTIPLY', band, I['Terminator Strength']), c, b.mix(1.0, c, I['Terminator Color'], blend='MULTIPLY'), label='Terminator' + tag)
        c = b.mix(b.math('MULTIPLY', occ, I['Occlusion Darken']), c, b.mix(1.0, c, I['Shade Tint 2'], blend='MULTIPLY'), label='OccDarken' + tag)

        # translucency: the unlit side of a thin membrane glows instead of going
        # dark, stronger when the camera looks towards the light
        if L is None:
            vl = 0.0
        else:
            vl = b.math('MAXIMUM', b.vmath('DOT_PRODUCT', V, b.vmath('SCALE', L, scale=-1.0).outputs[0]).outputs[1], 0.0, label='VdotNegL' + tag)
        back = b.math('SUBTRACT', 1.0, t1, label='BackSide' + tag)
        trn = b.math('MULTIPLY', back, b.math('ADD', 0.45, b.math('MULTIPLY', vl, 0.55)))
        trn = b.math('MULTIPLY', b.math('MULTIPLY', trn, thin), I['Transmit Strength'], clamp=True, label='TransmitAmount' + tag)
        c = b.mix(trn, c, b.mix(1.0, lit, I['Transmit Color'], blend='MULTIPLY'), label='Transmit' + tag)

        # nacre: weaker inside the shade so the toon steps stay readable
        iri_lit = b.fmix(t1, I['Iri Shade Keep'], 1.0, label='IriShadeKeep' + tag)
        iri_mask = b.math('MULTIPLY', b.math('MULTIPLY', iri_where, iri_lit), iri_gate, label='IriMask' + tag)
        c = b.mix(b.math('MULTIPLY', iri_mask, I['Iri Strength'], clamp=True), c, b.mix(1.0, c, iri_n, blend='MULTIPLY'), label='IriTint' + tag)
        iri_add = b.math('MULTIPLY', b.math('MULTIPLY', iri_lit, iri_gate), b.math('MULTIPLY', edge, I['Iri Add']), label='IriAddAmount' + tag)
        c = b.mix(iri_add, c, iri, blend='ADD', label='IriAdd' + tag)

        rbias = b.fmix(I['Rim Lit Bias'], 1.0, t1, label='RimBias' + tag)
        rimk = b.math('MULTIPLY', b.math('MULTIPLY', b.math('MULTIPLY', rim, rbias), I['Rim Strength']), open_, label='RimAmount' + tag)
        c = b.mix(rimk, c, I['Rim Color'], blend='ADD', label='AddRim' + tag)
        if L is None:
            spk = 0.0
        else:
            H = b.vmath('NORMALIZE', b.vmath('ADD', L, V).outputs[0]).outputs[0]
            nh = b.math('MAXIMUM', b.vmath('DOT_PRODUCT', N, H).outputs[1], 0.0, label='NdotH' + tag)
            sp = b.smooth(nh, b.math('SUBTRACT', I['Spec Size'], I['Spec Soft']), b.math('ADD', I['Spec Size'], I['Spec Soft']), label='Spec' + tag)
            spk = b.math('MULTIPLY', b.math('MULTIPLY', b.math('MULTIPLY', sp, t1), I['Spec Strength']), open_, label='SpecAmount' + tag)
            c = b.mix(spk, c, I['Spec Color'], blend='ADD', label='AddSpec' + tag)

        # aurora: on a pale base an additive glow only turns white, so first pull
        # the surface colour towards the aurora colour, then add a little light
        c = b.mix(b.math('MULTIPLY', a_amt, 1.0, clamp=True), c, acol, label='AuroraTint' + tag)
        c = b.mix(b.math('MULTIPLY', a_amt, 0.35), c, acol, blend='ADD', label='AddAurora' + tag)
        c = b.mix(I['Unlit'], c, base, label='Unlit' + tag)

        # highlight knee
        sep = b.node('ShaderNodeSeparateColor', 'KneeSep' + tag)
        b.link(c, sep.inputs[0])
        m = b.math('MAXIMUM', b.math('MAXIMUM', sep.outputs[0], sep.outputs[1]), sep.outputs[2], label='MaxCh' + tag)
        k = I['Highlight Knee']
        over = b.math('MAXIMUM', b.math('SUBTRACT', m, k), 0.0)
        rng = b.math('MAXIMUM', b.math('SUBTRACT', 1.0, k), 0.001)
        y = b.math('ADD', b.math('MINIMUM', m, k), b.math('MULTIPLY', rng, b.math('SUBTRACT', 1.0, b.math('EXPONENT', b.math('MULTIPLY', b.math('DIVIDE', over, rng), -1.0)))))
        sc = b.math('DIVIDE', y, b.math('MAXIMUM', m, 0.0001), label='KneeScale' + tag)
        cv = b.vmath('SCALE', c, scale=sc).outputs[0]
        return {'cv': cv, 't1': t1, 'rimk': rimk, 'spk': spk}

    def opacity(res):
        face_op = b.fmix(I['Thickness'], I['Opacity'], 1.0, label='FaceOpacity')
        edge_op = b.math('MAXIMUM', face_op, I['Edge Opacity'])
        op = b.fmix(b.math('MULTIPLY', fres, fres), face_op, edge_op, label='ViewOpacity')
        op = b.math('ADD', op, b.math('MULTIPLY', b.math('MULTIPLY', a_amt, I['Aurora Alpha']), b.math('SUBTRACT', 1.0, op)))
        glint = b.math('ADD', res['rimk'], res['spk'])
        op = b.math('ADD', op, b.math('MULTIPLY', glint, b.math('SUBTRACT', 1.0, op)))
        # where the aurora is lit it also fills the image alpha (thin fin tips), but
        # never a cut-out (alpha near 0 stays a hole)
        fill = b.math('MULTIPLY', b.math('MULTIPLY', a_amt, I['Aurora Alpha'], clamp=True), b.smooth(I['Alpha'], 0.02, 0.2))
        img_a = b.math('ADD', I['Alpha'], b.math('MULTIPLY', b.math('SUBTRACT', 1.0, I['Alpha']), fill), label='AlphaFilled')
        return b.math('MULTIPLY', op, img_a, clamp=True, label='AlphaOut')

    if lighting == 'DRIVER':
        kd = b.node('ShaderNodeCombineXYZ', 'KeyDir')
        kd.inputs[2].default_value = 1.0
        kc = b.node('ShaderNodeRGB', 'KeyColor')
        kc.outputs[0].default_value = (1, 1, 1, 1)
        ke = b.node('ShaderNodeValue', 'KeyEnergy')
        ke.outputs[0].default_value = 1.0
        L = b.vmath('NORMALIZE', kd.outputs[0], label='L').outputs[0]
        NL = b.vmath('DOT_PRODUCT', N, L, label='NdotL').outputs[1]
        dif = b.node('ShaderNodeBsdfDiffuse', 'Probe')
        dif.inputs['Color'].default_value = (1, 1, 1, 1)
        dif.inputs['Roughness'].default_value = 0.0
        b.link(N, dif.inputs['Normal'])
        s2r = b.node('ShaderNodeShaderToRGB', 'ProbeRGB')
        b.link(dif.outputs[0], s2r.inputs[0])
        bw = b.node('ShaderNodeRGBToBW', 'ProbeBW')
        b.link(s2r.outputs[0], bw.inputs[0])
        kscale = b.math('MULTIPLY', ke.outputs[0], PROBE_CAL, label='ProbeScale')
        kcl = b.node('ShaderNodeRGBToBW', 'KeyColorBW')
        b.link(kc.outputs[0], kcl.inputs[0])
        kscale2 = b.math('MULTIPLY', kscale, kcl.outputs[0])
        probe = b.math('DIVIDE', bw.outputs[0], b.math('MAXIMUM', kscale2, 0.0001), label='ProbeNL')
        nls = b.math('MINIMUM', NL, probe, label='NL_shadowed')
        Ls0 = b.fmix(b.math('MAXIMUM', I['Receive Shadow'], LV['Shadows']), NL, nls, label='ReceiveShadowMix')
        res = surface('', Ls0, L, kc.outputs[0])
        alpha = opacity(res)
        em = b.node('ShaderNodeEmission', 'ToonEmission')
        em.inputs['Strength'].default_value = 1.0
        b.link(add_glint(res['cv']), em.inputs['Color'])
        final = em.outputs[0]
        b.link(res['cv'], go.inputs['Color'])
        b.link(res['t1'], go.inputs['Lit'])
    else:
        # Blender 5.3 Material Lighting nodes. Negative light is clamped by the
        # accumulation and its result cannot go back through Shader to RGB, so:
        #   emission  = unlit look * (1 - UnlitDarkness)
        #   each light adds (look under that light - emission) * light weight
        # One sun of strength 1 gives exactly the DRIVER look; without any
        # light the surface keeps a dimmed shade colour.
        ev = b.node('ShaderNodeLightEvaluation', 'LightEval', mode='DIFFUSE')
        b.link(N, ev.inputs['Normal'])
        info = b.node('ShaderNodeLightInfo', 'LightInfo')
        shd = b.node('ShaderNodeShadowRaycast', 'LightShadow')
        dark = b.node('ShaderNodeValue', 'UnlitDarkness')
        dark.outputs[0].default_value = 0.5
        lclamp = b.node('ShaderNodeValue', 'LightClamp')
        lclamp.outputs[0].default_value = 1.0
        L = b.vmath('NORMALIZE', ev.outputs['Direction'], label='L').outputs[0]
        NL = b.vmath('DOT_PRODUCT', N, L, label='NdotL').outputs[1]
        sbw = b.node('ShaderNodeRGBToBW', 'ShadowBW')
        b.link(shd.outputs['Color'], sbw.inputs[0])
        shadowed = b.math('MINIMUM', NL, b.math('SUBTRACT', b.math('MULTIPLY', sbw.outputs[0], 2.0), 1.0), label='NL_shadowed')
        Ls0 = b.fmix(b.math('MAXIMUM', I['Receive Shadow'], LV['Shadows']), NL, shadowed, label='ReceiveShadowMix')
        # light weight: sun of strength 1 -> 1; local lights fall off with distance
        d2 = b.math('MAXIMUM', b.math('MULTIPLY', ev.outputs['Distance'], ev.outputs['Distance']), 0.0001)
        wgt = b.math('DIVIDE', b.math('MULTIPLY', info.outputs['Power'], 3.14159265), d2)
        wgt = b.math('MULTIPLY', wgt, ev.outputs['Mask'])
        wgt = b.math('MINIMUM', b.math('MAXIMUM', wgt, 0.0), lclamp.outputs[0], label='LightWeight')
        amb = surface('_unlit', None, None, None)
        res = surface('_light', Ls0, L, info.outputs['Color'])
        floor_c = b.vmath('SCALE', amb['cv'], scale=b.math('SUBTRACT', 1.0, dark.outputs[0]), label='UnlitColor').outputs[0]
        diff = b.vmath('MAXIMUM', b.vmath('SUBTRACT', res['cv'], floor_c).outputs[0], (0.0, 0.0, 0.0)).outputs[0]
        term = b.vmath('SCALE', diff, scale=b.math('MULTIPLY', wgt, g_keep), label='LightTerm').outputs[0]
        alpha = opacity(amb)
        em = b.node('ShaderNodeEmission', 'ToonEmission')
        em.inputs['Strength'].default_value = 1.0
        b.link(add_glint(floor_c), em.inputs['Color'])
        acc = b.node('ShaderNodeLightAccumulation', 'LightSum')
        acc.inputs['Diffuse Color'].default_value = (1, 1, 1, 1)
        b.link(term, acc.inputs['Diffuse Light'])
        add = b.node('ShaderNodeAddShader', 'UnlitPlusLights')
        b.link(em.outputs[0], add.inputs[0])
        b.link(acc.outputs[0], add.inputs[1])
        final = add.outputs[0]
        b.link(amb['cv'], go.inputs['Color'])
        go.inputs['Lit'].default_value = 0.0

    tr = b.node('ShaderNodeBsdfTransparent', 'Clear')
    ms = b.node('ShaderNodeMixShader', 'AlphaMix')
    b.link(alpha, ms.inputs[0])
    b.link(tr.outputs[0], ms.inputs[1])
    b.link(final, ms.inputs[2])
    b.link(ms.outputs[0], go.inputs['Shader'])
    b.link(alpha, go.inputs['Alpha'])
    return nt


def ensure_sun(scene, sun=None):
    """Use an explicitly chosen or existing sun; create one only when absent."""
    if sun is not None:
        if sun.type != 'LIGHT' or sun.data.type != 'SUN':
            raise ValueError('Main light must be a Sun')
        return sun
    sun = next((o for o in scene.objects if o.type == 'LIGHT' and o.data.type == 'SUN'), None)
    if sun:
        return sun
    data = bpy.data.lights.new('LidaAuroraToon Sun', 'SUN')
    data.energy = 1.0
    data.angle = 0.10472
    sun = bpy.data.objects.new('LidaAuroraToon Sun', data)
    scene.collection.objects.link(sun)
    sun.rotation_euler = Vector((-0.45, -0.70, 0.70)).to_track_quat('Z', 'Y').to_euler()
    return sun


def _single_driver(group, path, index=None):
    if index is None:
        group.driver_remove(path)
        fc = group.driver_add(path)
    else:
        group.driver_remove(path, index)
        fc = group.driver_add(path, index)
    driver = fc.driver
    for variable in list(driver.variables):
        driver.variables.remove(variable)
    while fc.keyframe_points:
        fc.keyframe_points.remove(fc.keyframe_points[0])
    return fc


def bind_sun(group, sun):
    """All materials share one scene sun. Replace only these owned drivers."""
    paths = [('nodes["KeyDir"].inputs[%d].default_value' % i, None,
              sun, 'OBJECT', 'matrix_world[2][%d]' % i) for i in range(3)]
    paths += [('nodes["KeyColor"].outputs[0].default_value', i,
               sun.data, 'LIGHT', 'color[%d]' % i) for i in range(3)]
    paths += [('nodes["KeyEnergy"].outputs[0].default_value', None,
               sun.data, 'LIGHT', 'energy')]
    for path, index, target, id_type, data_path in paths:
        fc = _single_driver(group, path, index)
        fc.driver.type = 'AVERAGE'
        variable = fc.driver.variables.new()
        variable.name = 'light_value'
        variable.type = 'SINGLE_PROP'
        variable.targets[0].id_type = id_type
        variable.targets[0].id = target
        variable.targets[0].data_path = data_path
        fc.update()


TIME_PROP = "lida_aurora_time"


def bind_time(group=None, fps=24.0, scene=None):
    """Drive the aurora clock with the scene frame (seconds = frame / fps).

    The clock is a custom property on the scene, read in the shader by a
    View Layer attribute node. A driver on the node group itself made EEVEE
    rebuild every material on every frame (measured: 0.34 s instead of 0.10 s
    per frame); a scene property is only a uniform.
    'frame / 24.0' is a simple driver expression: it runs without the
    auto-run-Python permission. Call unbind_time() and key 'Aurora Phase' on
    the material instead when a hand-made motion is wanted.
    """
    for sc in ([scene] if scene is not None else list(bpy.data.scenes)):
        if TIME_PROP not in sc:
            sc[TIME_PROP] = 0.0
        fc = _single_driver(sc, '["%s"]' % TIME_PROP)
        fc.driver.type = 'SCRIPTED'
        fc.driver.expression = 'frame / %.4f' % float(fps)
        fc.update()


def unbind_time(group=None, scene=None):
    for sc in ([scene] if scene is not None else list(bpy.data.scenes)):
        if TIME_PROP in sc:
            sc.driver_remove('["%s"]' % TIME_PROP)
            sc[TIME_PROP] = 0.0


def migrate_old_groups():
    """Make node groups of an older LidaAuroraToon version harmless.

    An older group keeps its materials working, but (1) it blocks building the
    current group under the same name and (2) up to 0.3.0 its clock was a driven
    value node, which made EEVEE rebuild all materials on every frame.
    Renames such groups to '<name> <version>' and moves their clock to the scene
    property. Returns the names of the groups that were changed.
    """
    done = []
    for g in list(bpy.data.node_groups):
        if g.bl_idname != 'ShaderNodeTree' or not g.get(PROP + 'version') or g.get(PROP + 'version') == VERSION:
            continue
        if g.name in (GROUP, GROUP_LIGHTS):
            g.name = '%s %s' % (g.name, g.get(PROP + 'version'))
        tm = g.nodes.get('AuroraTime')
        if tm is not None and tm.bl_idname == 'ShaderNodeValue':
            if g.animation_data:
                for fc in list(g.animation_data.drivers):
                    if 'AuroraTime' in fc.data_path:
                        g.animation_data.drivers.remove(fc)
            at = g.nodes.new('ShaderNodeAttribute')
            at.attribute_type = 'VIEW_LAYER'
            at.attribute_name = TIME_PROP
            at.location = tm.location
            for l in list(tm.outputs[0].links):
                g.links.new(at.outputs['Fac'], l.to_socket)
            g.nodes.remove(tm)
            at.name = at.label = 'AuroraTime'
        done.append(g.name)
    if done:
        bind_time()
    return done


def ensure_control(scene):
    """One empty that carries the master sliders as custom properties.

    Object Properties > Custom Properties shows them as sliders, so they work
    in a saved blend without the add-on. They scale every LidaAuroraToon
    material at once; the per-material inputs stay as they are.
    """
    ctrl = bpy.data.objects.get(CONTROL)
    if ctrl is None:
        ctrl = bpy.data.objects.new(CONTROL, None)
        ctrl.empty_display_type = 'SPHERE'
        ctrl.empty_display_size = 0.03
        ctrl.hide_render = True
    if ctrl.name not in scene.collection.all_objects:
        scene.collection.objects.link(ctrl)
    for name, (_node, default, vmax) in LEVELS.items():
        if name not in ctrl:
            ctrl[name] = float(default)
        ui = ctrl.id_properties_ui(name)
        ui.update(min=0.0, max=vmax, soft_min=0.0, soft_max=min(vmax, 2.0), default=float(default),
                  description='LidaAuroraToon master level')
    return ctrl


def bind_control(group, ctrl):
    for name, (node, _default, _max) in LEVELS.items():
        fc = _single_driver(group, 'nodes["%s"].outputs[0].default_value' % node)
        fc.driver.type = 'AVERAGE'
        variable = fc.driver.variables.new()
        variable.name = 'level'
        variable.type = 'SINGLE_PROP'
        variable.targets[0].id_type = 'OBJECT'
        variable.targets[0].id = ctrl
        variable.targets[0].data_path = '["%s"]' % name
        fc.update()


def set_level(name, value, scene=None):
    """Set a master slider from a script: set_level('Aurora', 0.5)."""
    if name not in LEVELS:
        raise KeyError(name)
    ctrl = ensure_control(scene or bpy.context.scene)
    ctrl[name] = float(value)
    ctrl.update_tag()
    return ctrl


GLOW_GROUP = "LidaAuroraToon Glow"


def ensure_glow(scene, strength=0.6, threshold=1.0, size=0.5):
    """Bloom around everything brighter than `threshold` (the glint light is).

    Builds a small compositor: Render Layers -> Glare (Bloom) -> output, and a
    'Glow' slider on the control object that drives the bloom strength.
    A scene that already has its own compositor is left alone (returns None).
    Viewport: Shading > Compositor = Always shows it in rendered view.
    """
    if not hasattr(scene, 'compositing_node_group'):
        raise ValueError('ensure_glow needs the compositor node groups of Blender 5.0 or newer')
    ng = scene.compositing_node_group
    if ng is not None and ng.name != GLOW_GROUP:
        return None
    if ng is None:
        ng = bpy.data.node_groups.get(GLOW_GROUP) or bpy.data.node_groups.new(GLOW_GROUP, 'CompositorNodeTree')
        scene.compositing_node_group = ng
    if 'Glow' not in ng.nodes:
        ng.nodes.clear()
        if not any(i.name == 'Image' for i in ng.interface.items_tree):
            ng.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
        rl = ng.nodes.new('CompositorNodeRLayers')
        rl.location = (-300, 0)
        gl = ng.nodes.new('CompositorNodeGlare')
        gl.name = gl.label = 'Glow'
        gl.inputs['Type'].default_value = 'Bloom'
        out = ng.nodes.new('NodeGroupOutput')
        out.location = (300, 0)
        ng.links.new(rl.outputs['Image'], gl.inputs['Image'])
        ng.links.new(gl.outputs['Image'], out.inputs['Image'])
    gl = ng.nodes['Glow']
    _sock(gl.inputs, 'Highlights Threshold').default_value = threshold
    gl.inputs['Size'].default_value = size
    gl.inputs['Strength'].default_value = strength
    scene.render.use_compositing = True
    ctrl = ensure_control(scene)
    if 'Glow' not in ctrl:
        ctrl['Glow'] = float(strength)
    ctrl.id_properties_ui('Glow').update(min=0.0, max=3.0, soft_min=0.0, soft_max=2.0, default=float(strength),
                                         description='LidaAuroraToon bloom strength (compositor)')
    fc = _single_driver(ng, 'nodes["Glow"].inputs["Strength"].default_value')
    fc.driver.type = 'AVERAGE'
    variable = fc.driver.variables.new()
    variable.name = 'level'
    variable.type = 'SINGLE_PROP'
    variable.targets[0].id_type = 'OBJECT'
    variable.targets[0].id = ctrl
    variable.targets[0].data_path = '["Glow"]'
    fc.update()
    return ng


def remove_glow(scene):
    ng = getattr(scene, 'compositing_node_group', None)
    if ng is not None and ng.name == GLOW_GROUP:
        scene.compositing_node_group = None
        bpy.data.node_groups.remove(ng)


def _owned(node):
    node[PROP + 'owned'] = True
    return node


def find_toon_node(material):
    if not material or not material.node_tree:
        return None
    return next((n for n in material.node_tree.nodes
                 if n.type == 'GROUP' and n.node_tree and n.node_tree.name in (GROUP, GROUP_LIGHTS)
                 and n.get(PROP + 'owned')), None)


def apply_material(material, preset, sun, *, receive_shadows=False,
                   ao_attribute='', thickness_attribute='', mask_attribute='',
                   aurora_coord='OBJECT', blend=None, time_fps=24.0, control=True,
                   lighting=None):
    """Apply to a Principled material without editing geometry or source nodes.

    The original nodes and output stay in the material (restore_material).
    Nodes are looked up by type, never by their (localised) names.
    aurora_coord: 'OBJECT', 'GENERATED' or 'UV'.
    blend: None = decide from the preset ('BLENDED' for translucent presets),
           or force 'BLENDED' / 'DITHERED'.
    lighting: None = 'NODES' on Blender 5.3 or newer, else 'DRIVER';
              'NODES' = Blender 5.3 Material Lighting nodes, every scene light
              shades the toon steps (sun may be None);
              'DRIVER' = one sun through drivers (sun is required).
    """
    if preset not in PRESETS:
        raise ValueError('Unknown material preset: ' + preset)
    if lighting is None:
        lighting = default_lighting()
    if lighting == 'DRIVER' and sun is None:
        raise ValueError('lighting=DRIVER needs a sun')
    material.use_nodes = True
    nt = material.node_tree
    original = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if original is None:
        raise ValueError(material.name + ': a Principled BSDF is required')
    output = next((n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'
                   and n.is_active_output and not n.get(PROP + 'owned')), None)
    if PROP + 'previous_output' not in material:
        if output is None:
            raise ValueError(material.name + ': original Material Output not found')
        material[PROP + 'previous_output'] = output.name
        material[PROP + 'previous_render_method'] = material.surface_render_method
        material[PROP + 'previous_backface_culling'] = bool(material.use_backface_culling)
        material[PROP + 'previous_overlap'] = bool(material.use_transparency_overlap)
    for node in list(nt.nodes):
        if node.get(PROP + 'owned'):
            nt.nodes.remove(node)
    group = build_group(lighting)
    if lighting == 'DRIVER':
        bind_sun(group, sun)
    if time_fps:
        bind_time(group, time_fps)
    if control:
        bind_control(group, ensure_control(bpy.context.scene))
    toon = _owned(nt.nodes.new('ShaderNodeGroup'))
    toon.node_tree = group
    toon.name = 'LidaAuroraToon'
    toon.label = 'LidaAuroraToon / ' + preset
    toon.location = (original.location.x + 320, original.location.y)
    for name, value in PRESETS[preset].items():
        socket = toon.inputs.get(name)
        if socket is None:
            raise KeyError('preset %s: unknown input %s' % (preset, name))
        if socket.type == 'RGBA' and len(value) == 3:
            value = (*value, 1.0)
        socket.default_value = value
    toon.inputs['Receive Shadow'].default_value = 1.0 if receive_shadows else 0.0
    for src_name, dst_name in [('Base Color', 'Base Color'), ('Normal', 'Normal Override')]:
        socket = original.inputs[src_name]
        if socket.is_linked:
            nt.links.new(socket.links[0].from_socket, toon.inputs[dst_name])
            if src_name == 'Normal':
                toon.inputs['Normal Override Mix'].default_value = 1.0
        elif src_name == 'Base Color':
            toon.inputs[dst_name].default_value = socket.default_value
    for attr_name, dst in ((ao_attribute, 'Occlusion'), (thickness_attribute, 'Thickness'),
                           (mask_attribute, 'Effect Mask')):
        if attr_name and attr_name.strip():
            attr = _owned(nt.nodes.new('ShaderNodeAttribute'))
            attr.attribute_name = attr_name.strip()
            attr.location = (toon.location.x - 220, toon.location.y - 500)
            nt.links.new(attr.outputs['Fac'], toon.inputs[dst])
    if aurora_coord not in ('OBJECT', 'GENERATED', 'UV'):
        raise ValueError('aurora_coord must be OBJECT, GENERATED or UV')
    tc = _owned(nt.nodes.new('ShaderNodeTexCoord'))
    tc.location = (toon.location.x - 220, toon.location.y - 700)
    nt.links.new(tc.outputs[{'OBJECT': 'Object', 'GENERATED': 'Generated', 'UV': 'UV'}[aurora_coord]],
                 toon.inputs['Aurora Coord'])
    alpha = original.inputs['Alpha']
    if alpha.is_linked:
        nt.links.new(alpha.links[0].from_socket, toon.inputs['Alpha'])
    else:
        toon.inputs['Alpha'].default_value = alpha.default_value
    out = _owned(nt.nodes.new('ShaderNodeOutputMaterial'))
    out.name = 'LidaAuroraToon Output'
    out.location = (toon.location.x + 420, toon.location.y)
    nt.links.new(toon.outputs['Shader'], out.inputs['Surface'])
    out.is_active_output = True
    translucent = (preset in TRANSLUCENT or alpha.is_linked or alpha.default_value < 1.0)
    if blend is None:
        blend = 'BLENDED' if translucent else None
    if blend:
        material.surface_render_method = blend
        if blend == 'BLENDED':
            # draw only the nearest wall of this object (depth pre-pass), so
            # the far wall of a closed fin does not double or darken it;
            # culling stays off because generated meshes often have flipped faces
            material.use_backface_culling = False
            material.use_transparency_overlap = False
    material[PROP + 'preset'] = preset
    material[PROP + 'lighting'] = lighting
    material[PROP + 'version'] = VERSION
    return toon


def link_attribute(material, attribute, socket_name, low=0.0, high=1.0):
    """Drive one input with a mesh attribute: value = low at 0, high at 1.

    Lets one material change smoothly over a mesh (for example scales at the
    thick tail body, fin membrane at the thin fluke) without splitting faces.
    """
    toon = find_toon_node(material)
    if toon is None:
        raise ValueError(material.name + ': apply LidaAuroraToon first')
    nt = material.node_tree
    sock = toon.inputs[socket_name]
    for l in list(sock.links):
        if l.from_node.get(PROP + 'owned'):
            nt.nodes.remove(l.from_node)
    attr = next((n for n in nt.nodes if n.type == 'ATTRIBUTE' and n.get(PROP + 'owned')
                 and n.attribute_name == attribute), None)
    if attr is None:
        attr = _owned(nt.nodes.new('ShaderNodeAttribute'))
        attr.attribute_name = attribute
        attr.location = (toon.location.x - 460, toon.location.y - 500)
    mr = _owned(nt.nodes.new('ShaderNodeMapRange'))
    mr.label = socket_name
    mr.location = (toon.location.x - 220, toon.location.y - 900)
    mr.inputs['To Min'].default_value = low
    mr.inputs['To Max'].default_value = high
    nt.links.new(attr.outputs['Fac'], mr.inputs['Value'])
    nt.links.new(mr.outputs[0], sock)
    return mr


def restore_material(material, remove_nodes=False):
    """Restore the original output and render settings.

    remove_nodes=False keeps the generated nodes and the user's fine tuning
    (re-applying is then only a matter of re-activating the output);
    remove_nodes=True deletes every node this module added.
    """
    name = material.get(PROP + 'previous_output')
    if not name or not material.node_tree:
        return False
    out = material.node_tree.nodes.get(name)
    if out is None or out.type != 'OUTPUT_MATERIAL':
        return False
    for n in material.node_tree.nodes:
        if n.type == 'OUTPUT_MATERIAL':
            n.is_active_output = False
    out.is_active_output = True
    old_method = material.get(PROP + 'previous_render_method')
    if old_method:
        material.surface_render_method = old_method
    if PROP + 'previous_backface_culling' in material:
        material.use_backface_culling = bool(material[PROP + 'previous_backface_culling'])
    if PROP + 'previous_overlap' in material:
        material.use_transparency_overlap = bool(material[PROP + 'previous_overlap'])
    if remove_nodes:
        for node in list(material.node_tree.nodes):
            if node.get(PROP + 'owned'):
                material.node_tree.nodes.remove(node)
        for key in list(material.keys()):
            if key.startswith(PROP):
                del material[key]
    return True


def bake_thickness(obj, attribute=THICKNESS_ATTR, full_thickness=0.02, smooth_iterations=2):
    """Write a per-vertex thickness (0 = thin, 1 = full_thickness metres or more).

    For a closed mesh (a fin with real volume) the distance to the opposite
    wall is measured by a ray cast against the mesh itself, in object space.
    Only a float point attribute is added; coordinates are unchanged.
    """
    if obj.type != 'MESH':
        raise ValueError('Thickness requires a mesh')
    me = obj.data
    scale = sum(abs(s) for s in obj.matrix_world.to_scale()) / 3.0 or 1.0
    full_local = full_thickness / scale
    verts = [v.co.copy() for v in me.vertices]
    tris = []
    for p in me.polygons:
        vs = list(p.vertices)
        for i in range(1, len(vs) - 1):
            tris.append((vs[0], vs[i], vs[i + 1]))
    tree = BVHTree.FromPolygons(verts, tris)
    values = []
    for v in me.vertices:
        n = v.normal
        hit = tree.ray_cast(v.co - n * (full_local * 0.002 + 1e-6), -n, full_local * 4.0)
        d = hit[3] if hit[0] is not None else full_local * 4.0
        values.append(min(d / full_local, 1.0))
    if smooth_iterations:
        nb = [[] for _ in me.vertices]
        for e in me.edges:
            a, b_ = e.vertices
            nb[a].append(b_)
            nb[b_].append(a)
        for _ in range(smooth_iterations):
            values = [(values[i] + sum(values[j] for j in nb[i])) / (1 + len(nb[i])) for i in range(len(values))]
    attr = me.attributes.get(attribute)
    if attr is None or attr.domain != 'POINT' or attr.data_type != 'FLOAT':
        if attr is not None:
            me.attributes.remove(attr)
        attr = me.attributes.new(attribute, 'FLOAT', 'POINT')
    attr.data.foreach_set('value', values)
    me.update()
    return min(values), sum(values) / max(len(values), 1), max(values)


def add_outline(obj, width_m, color=(0.16, 0.12, 0.22)):
    """Optional inverted hull. The original mesh coordinates are unchanged.

    Do not use it on translucent (BLENDED) membranes: the hull shows through.
    """
    if obj.type != 'MESH':
        raise ValueError('Outline requires a mesh')
    name = 'LidaAuroraToon Outline'
    modifier = obj.modifiers.get(name)
    if modifier is not None:
        modifier.thickness = width_m
        return modifier
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        nt = mat.node_tree
        nt.nodes.clear()
        em = nt.nodes.new('ShaderNodeEmission')
        em.inputs['Color'].default_value = (*color, 1.0)
        out = nt.nodes.new('ShaderNodeOutputMaterial')
        nt.links.new(em.outputs[0], out.inputs['Surface'])
        mat.use_backface_culling = True
    count = len(obj.data.materials)
    obj.data.materials.append(mat)
    modifier = obj.modifiers.new(name, 'SOLIDIFY')
    modifier.thickness = width_m
    modifier.offset = 1.0
    modifier.use_flip_normals = True
    modifier.use_rim = False
    modifier.use_even_offset = False
    modifier.use_quality_normals = True
    modifier.material_offset = count
    return modifier


def remove_outline(obj):
    name = 'LidaAuroraToon Outline'
    modifier = obj.modifiers.get(name)
    if modifier is None:
        return False
    obj.modifiers.remove(modifier)
    return True
