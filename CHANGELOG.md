# Changelog

## 0.3.6 — 2026-11-16

First public version.

- Soft toon shading from LidaAngelToon 0.2.1 (two shade steps, rim, specular, highlight knee, AO).
- Nacre iridescence, aurora light and thickness-based translucency.
- Aurora flow modes: travelling bands or a swaying curtain (`Aurora Curtain`, `Aurora Sway`, `Aurora Noise`).
- Hair light on the outline of the locks (`Glint …` inputs, presets `hair_glint`, `hair_rimglow`, `hair_softglow`) and a compositor bloom (`ensure_glow`).
- Master sliders on the object `LidaAuroraToon Control`.
- Lighting with the Material Lighting nodes of Blender 5.3 (default there) or with one sun through drivers.
- The clock is a scene property read as a View Layer attribute, so playback does not rebuild the materials.
