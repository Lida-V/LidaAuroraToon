# LidaAuroraToon for Unity (URP)

Unity 版の LidaAuroraToon です。Blender のノード群（0.3.6、灯りノード方式）と同じ計算を HLSL で書き直しました。

- 対象：Unity 6000.6 / URP 17.6、色空間 Linear、Forward+、D3D11 で確認（それ以外の版・Built-in・VRChat は未確認）
- シェーダー名：`LidaAuroraToon/Toon`（不透明と半透明を 1 つで持ち、材質ごとに切り替え）
- 入力の名前は Blender の入力の名前から空白を除いたもの（`Aurora Strength` → `_AuroraStrength`）。一覧とプリセットは `Runtime/Presets/LidaAuroraToonPresets.json`（Blender の `tools/make_unity_shader.py` が作る）

## 入れ方

`Packages/manifest.json` に、このフォルダを指す行を足します。

```json
"com.github.lida-v.lidaauroratoon": "file:<このリポジトリ>/unity/com.github.lida-v.lidaauroratoon"
```

## 使い方

- 材質：シェーダー `LidaAuroraToon/Toon` を選び、`LidaAuroraToonPresets.Create("fin")`（エディター）でプリセットの値を入れます。半透明は `LidaAuroraToonMaterials.SetupRenderState(mat, transparent: true)`（先に深度だけ書く前段のパスを入れ、物体の一番手前の面だけを混ぜる。Blender の BLENDED＋重なり無しと同じ）。
- 全体のつまみ：キャラクターの根元に `LidaAuroraToonControl` を付けます（Aurora・Iridescence・Glint などの 8 つ、時計、にじみ）。キャラクターの根元から見た位置でオーロラの帯を作るので、スキンのメッシュでも Blender の物体の座標と同じになります。
- にじみ（Glow）：URP の Bloom です。しきい値はガンマの値で、半分から効き始めるので、Blender のしきい値 1 に合わせるには **1.37**（リニア 2、効き始め 1.0）にします。描画先は HDR が要ります。
- Blender の制作ファイルから材質を作る：Blender で `tools/export_unity_spec.py` を走らせ、エディターで `LidaAuroraToonSpec.Apply(specDir, textureFolder, root, outFolder)`。入力の値・画像・頂点の値（厚み → 頂点色 R、AO → G、効果の範囲 → B、Alpha → A）を移します。

## Blender との違い

- 灯り：太陽（Directional）は Blender と同じ重み（強さ 1 で 1、1 で頭打ち）。点光源などの減衰は URP の減衰を使うので、Blender の値とは合いません。
- 落ち影：URP の主光の影を使います（Receive Shadow／Shadows が 0 のときは使いません）。
- 法線マップ：未対応（Blender 側の `Normal Override` は使いません）。
- にじみは材質ではなく URP の Bloom です。

## 確かめたこと

- ノイズ：Blender の Noise Texture（4D fBm）と、4000 点で最大 1.5e-5 の差（`tools/check_noise_port.py`）
- 原始図形 8 種（`tests/unity_compare/`）：同じ光・同じ画角・同じ時刻（3 コマ）で、画素の差 平均 1.1／255、95% の画素で 1.7 以下

© 2026 Lida — LicenseRef-Lida-Attribution-1.1（LICENSE.md）
