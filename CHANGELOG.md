# Changelog

## Unreleased

- Unity (URP) version 0.1.0 in `unity/com.github.lida-v.lidaauroratoon` (Lida Attribution 1.1): the same math in HLSL, Blender's 4D noise ported exactly, a component for the master levels / clock / glow, materials built from a Blender export.
- `tools/export_unity_spec.py` (what Unity needs from a blend), `tools/make_unity_shader.py` (Unity properties and presets from the Blender inputs), `tools/check_noise_port.py`, `tests/unity_compare/` (Blender vs Unity on primitives).

## 0.3.6 — 2026-11-16

First public version.

- Soft toon shading from LidaAngelToon 0.2.1 (two shade steps, rim, specular, highlight knee, AO).
- Nacre iridescence, aurora light and thickness-based translucency.
- Aurora flow modes: travelling bands or a swaying curtain (`Aurora Curtain`, `Aurora Sway`, `Aurora Noise`).
- Hair light on the outline of the locks (`Glint …` inputs, presets `hair_glint`, `hair_rimglow`, `hair_softglow`) and a compositor bloom (`ensure_glow`).
- Master sliders on the object `LidaAuroraToon Control`.
- Lighting with the Material Lighting nodes of Blender 5.3 (default there) or with one sun through drivers.
- The clock is a scene property read as a View Layer attribute, so playback does not rebuild the materials.

Documentation after the tag: README images of the author's mermaid model (`docs/images/mermaid_*`, not under the GPL).
