# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Lida
"""User-selectable presets; no material-name or character detection.

BASE presets are copied from LidaAngelToon 0.2.1 (MatCap entries removed,
hair 'Use Shade Texture' set to 0 because no shade image is bundled).
AURORA presets are new.
"""

_TOON = {
    'cloth': {'Highlight Knee': 0.8, 'Occlusion Darken': 0.45, 'Occlusion Shift': 1.2,
              'Rim Color': (0.92, 0.94, 1.0), 'Rim Lit Bias': 0.4, 'Rim Soft': 0.15,
              'Rim Strength': 0.08, 'Rim Width': 0.25,
              'Shade Shift 1': 0.05, 'Shade Shift 2': -0.75, 'Shade Soft 1': 0.32, 'Shade Soft 2': 0.3,
              'Shade Tint 1': (0.7, 0.72, 0.89), 'Shade Tint 2': (0.8, 0.82, 0.93)},
    'eye': {'Highlight Knee': 0.92, 'Lit Tint': (1.04, 1.04, 1.05), 'Occlusion Darken': 0.25,
            'Shade Shift 1': -0.25, 'Shade Shift 2': -1.5, 'Shade Soft 1': 0.4, 'Shade Soft 2': 0.1,
            'Shade Tint 1': (0.84, 0.84, 0.93), 'Shade Tint 2': (0.86, 0.86, 0.93), 'Unlit': 0.6},
    'face': {'Base Lift': 0.14, 'Base Lift Color': (1.0, 0.97, 0.96), 'Base Saturation': 0.87,
             'Highlight Knee': 0.92, 'Occlusion Darken': 0.25, 'Occlusion Shift': 0.9,
             'Rim Color': (1.0, 0.92, 0.92), 'Rim Lit Bias': 0.6, 'Rim Soft': 0.14,
             'Rim Strength': 0.05, 'Rim Width': 0.22,
             'Shade Shift 1': 0.12, 'Shade Shift 2': -0.75, 'Shade Soft 1': 0.32, 'Shade Soft 2': 0.28,
             'Shade Tint 1': (0.94, 0.83, 0.86), 'Shade Tint 2': (0.94, 0.87, 0.9),
             'Terminator Color': (1.0, 0.84, 0.82), 'Terminator Strength': 0.26, 'Terminator Width': 0.2},
    'hair': {'Highlight Knee': 0.8, 'Lit Tint': (1.04, 1.04, 1.04),
             'Occlusion Darken': 0.5, 'Occlusion Shift': 1.3,
             'Rim Color': (0.9, 0.93, 1.0), 'Rim Lit Bias': 0.4, 'Rim Soft': 0.15,
             'Rim Strength': 0.12, 'Rim Width': 0.26,
             'Shade Shift 1': 0.08, 'Shade Shift 2': -0.7, 'Shade Soft 1': 0.3, 'Shade Soft 2': 0.3,
             'Shade Tint 1': (0.82, 0.82, 0.91), 'Shade Tint 2': (0.83, 0.83, 0.9),
             'Use Shade Texture': 0.0},
    'metal': {'Highlight Knee': 0.9, 'Occlusion Darken': 0.25, 'Occlusion Shift': 0.6,
              'Rim Color': (0.95, 0.97, 1.0), 'Rim Lit Bias': 0.3, 'Rim Soft': 0.14,
              'Rim Strength': 0.1, 'Rim Width': 0.25,
              'Shade Shift 1': 0.1, 'Shade Shift 2': -0.4, 'Shade Soft 1': 0.25, 'Shade Soft 2': 0.28,
              'Shade Tint 1': (0.74, 0.75, 0.88), 'Shade Tint 2': (0.83, 0.83, 0.94),
              'Spec Size': 0.95, 'Spec Soft': 0.02, 'Spec Strength': 0.3},
    'mouth': {'Occlusion Darken': 0.25,
              'Shade Shift 1': 0.0, 'Shade Shift 2': -0.55, 'Shade Soft 1': 0.35, 'Shade Soft 2': 0.3,
              'Shade Tint 1': (0.88, 0.75, 0.78), 'Shade Tint 2': (0.93, 0.9, 0.91), 'Unlit': 0.2},
    'nail': {'Occlusion Darken': 0.2, 'Occlusion Shift': 0.5,
             'Shade Shift 1': 0.05, 'Shade Shift 2': -0.6, 'Shade Soft 1': 0.3, 'Shade Soft 2': 0.3,
             'Shade Tint 1': (0.9, 0.8, 0.83), 'Shade Tint 2': (0.93, 0.9, 0.91),
             'Spec Size': 0.96, 'Spec Soft': 0.02, 'Spec Strength': 0.18},
    'skin': {'Base Lift': 0.16, 'Base Lift Color': (1.0, 0.97, 0.96), 'Base Saturation': 0.85,
             'Highlight Knee': 0.92, 'Occlusion Darken': 0.35, 'Occlusion Shift': 1.0,
             'Rim Color': (1.0, 0.9, 0.9), 'Rim Lit Bias': 0.5, 'Rim Soft': 0.15,
             'Rim Strength': 0.08, 'Rim Width': 0.25,
             'Shade Shift 1': 0.05, 'Shade Shift 2': -0.75, 'Shade Soft 1': 0.32, 'Shade Soft 2': 0.3,
             'Shade Tint 1': (0.91, 0.82, 0.85), 'Shade Tint 2': (0.92, 0.86, 0.9),
             'Terminator Color': (1.0, 0.82, 0.8), 'Terminator Strength': 0.34, 'Terminator Width': 0.14},
}

_AURORA = {
    # sea shell / mother-of-pearl plate: opaque, hue walks from face-on to the rim
    'shell': {'Highlight Knee': 0.86,
              'Shade Shift 1': 0.02, 'Shade Shift 2': -0.7, 'Shade Soft 1': 0.34, 'Shade Soft 2': 0.3,
              'Shade Tint 1': (0.80, 0.76, 0.93), 'Shade Tint 2': (0.86, 0.84, 0.95),
              'Rim Color': (0.95, 0.92, 1.0), 'Rim Strength': 0.12, 'Rim Width': 0.28, 'Rim Soft': 0.16, 'Rim Lit Bias': 0.3,
              'Spec Strength': 0.22, 'Spec Size': 0.93, 'Spec Soft': 0.05, 'Spec Color': (1.0, 0.97, 1.0),
              'Iri Strength': 0.55, 'Iri Add': 0.12, 'Iri Scale': 1.0, 'Iri Shift': 0.45, 'Iri Hue Range': 0.5,
              'Iri Saturation': 0.5, 'Iri Edge Bias': 0.15, 'Iri Base Phase': 0.7,
              'Iri Grain': 0.06, 'Iri Grain Scale': 90.0, 'Iri Shade Keep': 0.4},
    # fin membrane: thin, see-through face-on, glowing edge, light from behind, flowing aurora
    'fin': {'Highlight Knee': 0.88,
            'Shade Shift 1': 0.0, 'Shade Shift 2': -0.75, 'Shade Soft 1': 0.4, 'Shade Soft 2': 0.3,
            'Shade Tint 1': (0.82, 0.80, 0.95), 'Shade Tint 2': (0.90, 0.88, 0.96),
            'Rim Color': (0.86, 0.95, 1.0), 'Rim Strength': 0.28, 'Rim Width': 0.3, 'Rim Soft': 0.2, 'Rim Lit Bias': 0.0,
            'Iri Strength': 0.3, 'Iri Add': 0.08, 'Iri Scale': 1.0, 'Iri Shift': 0.42, 'Iri Hue Range': 0.5,
            'Iri Saturation': 0.45, 'Iri Edge Bias': 0.4, 'Iri Shade Keep': 0.7,
            'Aurora Strength': 0.6, 'Aurora Direction': (0.0, 0.0, -1.0),
            'Aurora Band Scale': 3.0, 'Aurora Streak Scale': 45.0, 'Aurora Streak': 0.65,
            'Aurora Distort': 0.7, 'Aurora Sharpness': 1.0, 'Aurora Speed': 0.45, 'Aurora Curtain': 1.0, 'Aurora Sway': 1.5, 'Aurora Noise': 1.0,
            'Aurora Hue Spread': 0.9, 'Aurora Hue Shift': 0.15, 'Aurora Edge Boost': 1.0, 'Aurora Alpha': 0.9,
            'Opacity': 0.62, 'Edge Opacity': 0.97,
            'Transmit Strength': 0.75, 'Transmit Color': (1.0, 0.90, 0.97)},
    # scales: opaque, every scale shifts hue a little through the base image brightness
    'scale': {'Highlight Knee': 0.86,
              'Shade Shift 1': 0.04, 'Shade Shift 2': -0.7, 'Shade Soft 1': 0.3, 'Shade Soft 2': 0.3,
              'Shade Tint 1': (0.78, 0.74, 0.93), 'Shade Tint 2': (0.85, 0.83, 0.95),
              'Rim Color': (0.9, 0.93, 1.0), 'Rim Strength': 0.14, 'Rim Width': 0.26, 'Rim Soft': 0.15, 'Rim Lit Bias': 0.3,
              'Spec Strength': 0.18, 'Spec Size': 0.9, 'Spec Soft': 0.06, 'Spec Color': (0.95, 0.97, 1.0),
              'Iri Strength': 0.5, 'Iri Add': 0.1, 'Iri Scale': 1.1, 'Iri Shift': 0.45, 'Iri Hue Range': 0.5,
              'Iri Saturation': 0.5, 'Iri Edge Bias': 0.1, 'Iri Base Phase': 1.6,
              'Iri Grain': 0.1, 'Iri Grain Scale': 70.0, 'Iri Shade Keep': 0.45,
              'Aurora Strength': 0.3, 'Aurora Direction': (0.0, 0.0, -1.0),
              'Aurora Band Scale': 2.0, 'Aurora Streak': 0.35, 'Aurora Streak Scale': 30.0, 'Aurora Sharpness': 1.8,
              'Aurora Speed': 0.3, 'Aurora Curtain': 1.0, 'Aurora Sway': 1.5, 'Aurora Noise': 1.0, 'Aurora Hue Spread': 0.9, 'Aurora Hue Shift': 0.15},
    # pearl: round soft shading, a soft highlight and an orient glow near the rim
    'pearl': {'Highlight Knee': 0.9,
              'Shade Shift 1': -0.05, 'Shade Shift 2': -0.75, 'Shade Soft 1': 0.4, 'Shade Soft 2': 0.3,
              'Shade Tint 1': (0.84, 0.80, 0.92), 'Shade Tint 2': (0.90, 0.88, 0.95),
              'Rim Color': (1.0, 0.95, 1.0), 'Rim Strength': 0.18, 'Rim Width': 0.3, 'Rim Soft': 0.2, 'Rim Lit Bias': 0.2,
              'Spec Strength': 0.45, 'Spec Size': 0.94, 'Spec Soft': 0.035,
              'Iri Strength': 0.4, 'Iri Add': 0.2, 'Iri Scale': 0.9, 'Iri Shift': 0.42, 'Iri Hue Range': 0.55,
              'Iri Saturation': 0.45, 'Iri Edge Bias': 0.6, 'Iri Shade Keep': 0.6},
    # gem / crystal drop: brighter core, crisp highlight, strong edge colour
    'gem': {'Highlight Knee': 0.9, 'Unlit': 0.3,
            'Shade Shift 1': 0.0, 'Shade Shift 2': -0.45, 'Shade Soft 1': 0.25, 'Shade Soft 2': 0.28,
            'Shade Tint 1': (0.76, 0.8, 0.94), 'Shade Tint 2': (0.88, 0.88, 0.96),
            'Rim Color': (0.85, 0.92, 1.0), 'Rim Strength': 0.15, 'Rim Width': 0.3, 'Rim Soft': 0.15, 'Rim Lit Bias': 0.0,
            'Spec Strength': 0.55, 'Spec Size': 0.96, 'Spec Soft': 0.015,
            'Iri Strength': 0.3, 'Iri Add': 0.3, 'Iri Scale': 1.6, 'Iri Shift': 0.5,
            'Iri Saturation': 0.6, 'Iri Edge Bias': 0.5, 'Iri Shade Keep': 0.8},
}

# hair with a soft aurora running down the strands (opaque, toon values of 'hair')
_AURORA['hair_aurora'] = dict(_TOON['hair'], **{
    'Aurora Strength': 0.3, 'Aurora Direction': (0.0, 0.0, -1.0),
    'Aurora Band Scale': 1.6, 'Aurora Streak Scale': 55.0, 'Aurora Streak': 0.75,
    'Aurora Distort': 0.9, 'Aurora Sharpness': 2.6, 'Aurora Speed': 0.4, 'Aurora Curtain': 1.0, 'Aurora Sway': 1.5, 'Aurora Noise': 1.0,
    'Aurora Hue Spread': 0.7, 'Aurora Hue Shift': 0.2, 'Aurora Edge Boost': 0.4})

# hair_aurora plus a faint light that moves with the viewing angle, on some locks only
_AURORA['hair_glint'] = dict(_AURORA['hair_aurora'], **{
    'Glint Strength': 1.8, 'Glint Height': 0.3, 'Glint Width': 0.22,
    'Glint Streak': 0.85, 'Glint Streak Scale': 70.0,
    'Glint Coverage': 0.6, 'Glint Patch Scale': 6.0, 'Glint Edge': 0.25,
    'Glint Hue Shift': 0.42, 'Glint Hue Spread': 0.5, 'Glint White': 0.35})

# hair_aurora plus a faint coloured light on the outline of the locks only
_AURORA['hair_rimglow'] = dict(_AURORA['hair_aurora'], **{
    'Glint Strength': 1.0, 'Glint Band': 0.0, 'Glint Edge': 1.0, 'Glint Edge Width': 0.4, 'Glint Glow': 1.6,
    'Glint Streak': 0.0, 'Glint Coverage': 0.6, 'Glint Patch Scale': 4.0,
    'Glint Hue Shift': 0.6, 'Glint Hue Spread': 0.4, 'Glint White': 0.75})
# softer: thinner, fainter line; meant for a wider bloom (ensure_glow strength 1.0, size 0.7)
_AURORA['hair_softglow'] = dict(_AURORA['hair_rimglow'], **{
    'Glint Strength': 1.9, 'Glint Edge Width': 0.6, 'Glint Glow': 0.6, 'Glint Coverage': 0.5,
    'Glint White': 0.1, 'Glint Hue Shift': 0.45, 'Glint Hue Spread': 0.5, 'Glint Hue Vary': 0.7, 'Glint Hue Speed': 0.08,
    'Glint Softness': 2.0, 'Glint Flow': 0.3})

PRESETS = {}
PRESETS.update(_TOON)
PRESETS.update(_AURORA)

# presets that turn on alpha blending when applied
TRANSLUCENT = {'fin'}

AURORA_PRESETS = tuple(_AURORA)
TOON_PRESETS = tuple(_TOON)
