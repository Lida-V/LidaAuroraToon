# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Lida
"""LidaAuroraToon: toon shading with nacre iridescence, aurora glow and
translucency for Blender EEVEE. Derived from LidaAngelToon by the same author."""

bl_info = {
    "name": "LidaAuroraToon", "author": "Lida", "version": (0, 3, 6),
    "blender": (5, 2, 0), "location": "3D View > Sidebar > LidaAuroraToon",
    "description": "Soft toon shading with nacre iridescence, aurora glow and translucent membranes",
    "category": "Material",
}

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, PointerProperty, StringProperty
from . import shader
from .presets import PRESETS

LABELS = {
    'shell': 'Shell (nacre)', 'fin': 'Fin membrane', 'scale': 'Scales', 'pearl': 'Pearl', 'gem': 'Gem',
    'hair_aurora': 'Hair + aurora',
    'skin': 'Skin', 'face': 'Face', 'hair': 'Hair', 'cloth': 'Cloth', 'metal': 'Metal',
    'eye': 'Eye', 'mouth': 'Mouth', 'nail': 'Nail',
}


def sun_only(_self, obj):
    return obj.type == "LIGHT" and obj.data.type == "SUN"


class LAUSettings(bpy.types.PropertyGroup):
    preset: EnumProperty(name="Material", items=[
        (k, LABELS[k], "Apply this preset to the active material") for k in LABELS if k in PRESETS],
        default="shell")
    sun: PointerProperty(name="Main sun", type=bpy.types.Object, poll=sun_only)
    make_single_user: BoolProperty(name="Copy shared material", default=True)
    receive_shadows: BoolProperty(name="Receive cast shadows (single sun)", default=False)
    ao_attribute: StringProperty(name="AO attribute", default="")
    use_thickness: BoolProperty(name="Bake thickness (thin = clearer)", default=True,
        description="Fin preset: measure the wall-to-wall distance of the closed mesh into a point attribute")
    full_thickness_mm: FloatProperty(name="Opaque from (mm)", min=0.1, max=200.0, default=12.0)
    aurora_coord: EnumProperty(name="Aurora coordinates", items=[
        ('OBJECT', 'Object', ''), ('GENERATED', 'Generated', ''), ('UV', 'UV', '')], default='OBJECT')
    animate: BoolProperty(name="Flow with the timeline", default=True)
    lighting: EnumProperty(name="Lighting", items=[
        ('NODES', 'All lights (5.3 nodes)', 'Blender 5.3 Material Lighting nodes: every light, real cast shadows'),
        ('DRIVER', 'One sun (driver)', 'One sun read through drivers; for Blender 5.2')],
        default='NODES')
    outline: BoolProperty(name="Add outline", default=False)
    outline_mm: FloatProperty(name="Outline width (mm)", min=0.0, max=10.0, default=0.5)


class LAU_OT_apply(bpy.types.Operator):
    bl_idname = "lida_aurora_toon.apply"
    bl_label = "Apply to selected meshes"
    bl_description = "Apply to each selected mesh's active material; keep the original nodes for Restore"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT" and any(o.type == "MESH" for o in context.selected_objects)

    def execute(self, context):
        cfg = context.scene.lida_aurora_toon
        if context.scene.render.engine != "BLENDER_EEVEE":
            self.report({"ERROR"}, "Choose EEVEE in Render Properties first")
            return {"CANCELLED"}
        sun = None
        if cfg.lighting == 'DRIVER':
            sun = shader.ensure_sun(context.scene, cfg.sun)
            cfg.sun = sun
        fps = context.scene.render.fps / context.scene.render.fps_base
        changed, errors = 0, []
        for obj in context.selected_objects:
            if obj.type != "MESH":
                continue
            if cfg.ao_attribute.strip() and cfg.ao_attribute.strip() not in obj.data.attributes:
                errors.append(obj.name + ": AO attribute not found")
                continue
            if cfg.make_single_user and obj.data.users > 1:
                obj.data = obj.data.copy()
            mat = obj.active_material
            if mat is None:
                mat = bpy.data.materials.new("LidaAuroraToon Material")
                mat.use_nodes = True
                obj.data.materials.append(mat)
            elif cfg.make_single_user and mat.users > 1:
                mat = mat.copy()
                obj.active_material = mat
            try:
                thick = ''
                if cfg.preset == 'fin' and cfg.use_thickness:
                    shader.bake_thickness(obj, full_thickness=cfg.full_thickness_mm / 1000.0)
                    thick = shader.THICKNESS_ATTR
                shader.apply_material(mat, cfg.preset, sun,
                    receive_shadows=cfg.receive_shadows, ao_attribute=cfg.ao_attribute,
                    thickness_attribute=thick, aurora_coord=cfg.aurora_coord,
                    time_fps=fps if cfg.animate else None, lighting=cfg.lighting)
                if cfg.outline and cfg.preset != 'fin':
                    shader.add_outline(obj, cfg.outline_mm / 1000.0)
                changed += 1
            except (ValueError, KeyError) as exc:
                errors.append(str(exc))
        if errors:
            self.report({"WARNING"}, "; ".join(errors))
        self.report({"INFO"}, "Applied LidaAuroraToon to %d mesh(es)" % changed)
        return {"FINISHED"} if changed else {"CANCELLED"}


class LAU_OT_restore(bpy.types.Operator):
    bl_idname = "lida_aurora_toon.restore"
    bl_label = "Restore original material"
    bl_description = "Restore the previous output and render settings, remove this add-on's outline modifier"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        n = 0
        for obj in context.selected_objects:
            if obj.type != "MESH":
                continue
            for slot in obj.material_slots:
                if slot.material and shader.restore_material(slot.material):
                    n += 1
            shader.remove_outline(obj)
        self.report({"INFO"}, "Restored %d material(s)" % n)
        return {"FINISHED"}


class LAU_PT_panel(bpy.types.Panel):
    bl_label = "LidaAuroraToon 0.3.6"
    bl_idname = "LAU_PT_material"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "LidaAuroraToon"

    def draw(self, context):
        ui = self.layout
        cfg = context.scene.lida_aurora_toon
        ctrl = bpy.data.objects.get(shader.CONTROL)
        if ctrl is not None:
            box = ui.box()
            box.label(text="Master levels (all materials)")
            for name in shader.LEVELS:
                if name in ctrl:
                    box.prop(ctrl, '["%s"]' % name, text=name, slider=True)
            if 'Glow' in ctrl:
                box.prop(ctrl, '["Glow"]', text="Glow (bloom)", slider=True)
        ui.label(text="EEVEE / active material of selected meshes")
        ui.prop(cfg, "preset")
        ui.prop(cfg, "lighting")
        if cfg.lighting == 'DRIVER':
            ui.prop(cfg, "sun")
        ui.prop(cfg, "make_single_user")
        ui.prop(cfg, "receive_shadows")
        ui.prop(cfg, "ao_attribute")
        if cfg.preset == 'fin':
            ui.prop(cfg, "use_thickness")
            if cfg.use_thickness:
                ui.prop(cfg, "full_thickness_mm")
        ui.prop(cfg, "aurora_coord")
        ui.prop(cfg, "animate")
        if cfg.preset != 'fin':
            ui.prop(cfg, "outline")
            if cfg.outline:
                ui.prop(cfg, "outline_mm")
        ui.operator(LAU_OT_apply.bl_idname)
        ui.operator(LAU_OT_restore.bl_idname)
        ui.label(text="Fine tune: Shader Editor > LidaAuroraToon")


CLASSES = (LAUSettings, LAU_OT_apply, LAU_OT_restore, LAU_PT_panel)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.lida_aurora_toon = PointerProperty(type=LAUSettings)


def unregister():
    del bpy.types.Scene.lida_aurora_toon
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
