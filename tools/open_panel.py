# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Lida
"""Show the LidaAuroraToon panel for this Blender session only (nothing is installed).

blender <file.blend> --python tools/open_panel.py
Sidebar (N) > LidaAuroraToon: master sliders "Aurora", "Aurora Speed", "Iridescence".
"""
import bpy, sys, os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'blender'))
import lida_aurora_toon
from lida_aurora_toon import shader

try:
    lida_aurora_toon.unregister()
except Exception:
    pass
lida_aurora_toon.register()


def _setup():
    ctrl = bpy.data.objects.get(shader.CONTROL)
    for win in bpy.context.window_manager.windows:
        for area in win.screen.areas:
            if area.type == 'VIEW_3D':
                sp = area.spaces.active
                sp.shading.type = 'RENDERED'
                if hasattr(sp.shading, 'use_compositor'):
                    sp.shading.use_compositor = 'ALWAYS'   # shows the glow in the viewport
                sp.show_region_ui = True
                if bpy.context.scene.camera:
                    sp.region_3d.view_perspective = 'CAMERA'
    if ctrl is not None:
        for o in bpy.context.view_layer.objects:
            o.select_set(False)
        ctrl.select_set(True)
        bpy.context.view_layer.objects.active = ctrl
    return None


bpy.app.timers.register(_setup, first_interval=0.5)
print('LidaAuroraToon panel registered for this session')
