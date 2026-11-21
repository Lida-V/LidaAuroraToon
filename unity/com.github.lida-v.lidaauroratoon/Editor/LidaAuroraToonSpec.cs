// SPDX-License-Identifier: LicenseRef-Lida-Attribution-1.1
// Copyright (c) 2026 Lida
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using J = LidaAuroraToon.Editor.LidaAuroraToonJson;

namespace LidaAuroraToon.Editor
{
    /// <summary>Presets and input names of LidaAuroraToon (generated from the Blender add-on).</summary>
    public static class LidaAuroraToonPresets
    {
        public const string PresetPath = "Packages/com.github.lida-v.lidaauroratoon/Runtime/Presets/LidaAuroraToonPresets.json";
        static Dictionary<string, object> _data;
        static Dictionary<string, (string prop, string type)> _byBlender;

        public static Dictionary<string, object> Data
        {
            get
            {
                if (_data == null)
                {
                    var ta = AssetDatabase.LoadAssetAtPath<TextAsset>(PresetPath);
                    string text = ta != null ? ta.text : File.ReadAllText(Path.GetFullPath(PresetPath));
                    _data = J.O(J.Parse(text));
                    _byBlender = new Dictionary<string, (string, string)>();
                    foreach (var o in J.A(_data["inputs"]))
                    {
                        var d = J.O(o);
                        _byBlender[(string)d["blender"]] = ((string)d["property"], (string)d["type"]);
                    }
                }
                return _data;
            }
        }

        public static bool TryProperty(string blenderName, out string prop, out string type)
        {
            var _ = Data;
            if (_byBlender.TryGetValue(blenderName, out var pt)) { prop = pt.prop; type = pt.type; return true; }
            prop = null; type = null;
            return false;
        }

        public static IEnumerable<string> PresetNames => J.O(Data["presets"]).Keys;

        /// <summary>Set one value by its property name; colours are linear values (as in Blender).</summary>
        public static void Set(Material m, string prop, string type, object value)
        {
            if (type == "float") m.SetFloat(prop, J.F(value));
            else
            {
                var f = J.Floats(value);
                if (f == null || f.Length < 3) return;
                if (type == "color") LidaAuroraToonMaterials.SetLinearColor(m, prop, new Vector3(f[0], f[1], f[2]));
                else m.SetVector(prop, new Vector4(f[0], f[1], f[2], 0f));
            }
        }

        /// <summary>A new material with the defaults of every input, then the preset's values.</summary>
        public static Material Create(string preset, string name = null)
        {
            var shader = Shader.Find(LidaAuroraToonMaterials.ShaderName);
            if (shader == null) throw new Exception("shader not found: " + LidaAuroraToonMaterials.ShaderName);
            var m = new Material(shader) { name = name ?? ("LidaAuroraToon " + preset) };
            ApplyPreset(m, preset);
            return m;
        }

        public static void ApplyPreset(Material m, string preset)
        {
            foreach (var o in J.A(Data["inputs"]))
            {
                var d = J.O(o);
                Set(m, (string)d["property"], (string)d["type"], d["default"]);
            }
            var p = J.O(J.Get(J.O(Data["presets"]), preset)) ?? throw new Exception("unknown preset " + preset);
            foreach (var kv in J.O(p["values"]))
            {
                var type = "float";
                foreach (var o in J.A(Data["inputs"])) { var d = J.O(o); if ((string)d["property"] == kv.Key) { type = (string)d["type"]; break; } }
                Set(m, kv.Key, type, kv.Value);
            }
            LidaAuroraToonMaterials.SetupRenderState(m, p["translucent"] is bool t && t);
        }
    }

    /// <summary>
    /// Builds LidaAuroraToon materials for a model from the files written by the Blender side
    /// (tools/export_unity_spec.py): every input value, the textures, the per-vertex attributes.
    /// </summary>
    public static class LidaAuroraToonSpec
    {
        public class Report
        {
            public List<string> materials = new List<string>();
            public List<string> slotsWithoutSpec = new List<string>();
            public List<string> bakedMeshes = new List<string>();
            public List<string> warnings = new List<string>();
            public Dictionary<string, string> axis = new Dictionary<string, string>();
            public Dictionary<string, float> matchError = new Dictionary<string, float>();
        }

        /// <param name="specDir">folder with aurora_spec.json and attr_*.json (any path)</param>
        /// <param name="textureAssetDir">asset folder with the images (file name = Blender image name + extension)</param>
        /// <param name="outAssetDir">asset folder for the new materials and meshes</param>
        public static Report Apply(string specDir, string textureAssetDir, GameObject root, string outAssetDir)
        {
            var rep = new Report();
            var spec = J.O(J.Parse(File.ReadAllText(Path.Combine(specDir, "aurora_spec.json"))));
            var mats = J.O(spec["materials"]);
            Directory.CreateDirectory(Path.GetFullPath(outAssetDir));
            var made = new Dictionary<string, Material>();
            var needs = new Dictionary<string, (bool thick, bool occ, bool mask, bool alpha)>();

            foreach (var r in root.GetComponentsInChildren<Renderer>(true))
            {
                var shared = r.sharedMaterials;
                bool changed = false;
                for (int s = 0; s < shared.Length; s++)
                {
                    if (shared[s] == null) continue;
                    string mname = shared[s].name.Replace(" (Instance)", "");
                    var ms = J.O(J.Get(mats, mname));
                    if (ms == null) { rep.slotsWithoutSpec.Add(r.name + "/" + mname); continue; }
                    if (!made.TryGetValue(mname, out var mat))
                    {
                        mat = Build(mname, ms, textureAssetDir, rep, out var need);
                        string path = Path.Combine(outAssetDir, Safe(mname) + ".mat").Replace('\\', '/');
                        AssetDatabase.DeleteAsset(path);
                        AssetDatabase.CreateAsset(mat, path);
                        made[mname] = mat;
                        needs[mname] = need;
                        rep.materials.Add(mname + " <- " + J.Get(ms, "preset"));
                    }
                    shared[s] = mat;
                    changed = true;
                }
                if (changed) r.sharedMaterials = shared;

                // per-vertex attributes
                bool any = false; var nd = (thick: false, occ: false, mask: false, alpha: false);
                foreach (var m in r.sharedMaterials)
                {
                    if (m == null) continue;
                    string mname = m.name;
                    if (needs.TryGetValue(mname, out var n)) { any |= n.thick || n.occ || n.mask || n.alpha; nd.thick |= n.thick; nd.occ |= n.occ; nd.mask |= n.mask; nd.alpha |= n.alpha; }
                }
                if (any) BakeVertexColors(r, specDir, outAssetDir, rep);
            }
            AssetDatabase.SaveAssets();
            return rep;
        }

        static string Safe(string s) => string.Concat(s.Select(c => Path.GetInvalidFileNameChars().Contains(c) ? '_' : c));

        static Material Build(string name, Dictionary<string, object> ms, string texDir, Report rep, out (bool thick, bool occ, bool mask, bool alpha) need)
        {
            need = (false, false, false, false);
            string preset = J.Get(ms, "preset") as string;
            var mat = preset != null && LidaAuroraToonPresets.PresetNames.Contains(preset)
                ? LidaAuroraToonPresets.Create(preset, name) : LidaAuroraToonPresets.Create("cloth", name);
            foreach (var kv in J.O(ms["inputs"]))
            {
                if (LidaAuroraToonPresets.TryProperty(kv.Key, out var prop, out var type)) { LidaAuroraToonPresets.Set(mat, prop, type, kv.Value); continue; }
                if (kv.Key == "Base Color") { var f = J.Floats(kv.Value); if (f != null) LidaAuroraToonMaterials.SetLinearColor(mat, "_BaseColor", new Vector3(f[0], f[1], f[2])); }
                else if (kv.Key == "Alpha") mat.SetFloat("_Alpha", J.F(kv.Value));
            }
            foreach (var kv in J.O(ms["links"]))
            {
                var l = J.O(kv.Value);
                string img = J.Get(l, "image") as string;
                string attr = J.Get(l, "attribute") as string;
                switch (kv.Key)
                {
                    case "Base Color":
                        if (img != null) { mat.SetTexture("_BaseMap", LoadTex(texDir, img, true, rep)); mat.SetColor("_BaseColor", Color.white); }
                        else rep.warnings.Add(name + ": Base Color is fed by " + J.Get(l, "node"));
                        break;
                    case "Alpha":
                        if (img != null) { mat.SetTexture("_AlphaMap", LoadTex(texDir, img, false, rep)); mat.SetFloat("_UseAlphaMap", 1f); mat.SetFloat("_Alpha", 1f); }
                        else if (attr != null) { mat.SetFloat("_VertexAlpha", 1f); need.alpha = true; }
                        break;
                    case "Thickness": if (attr != null) { mat.SetFloat("_VertexThickness", 1f); need.thick = true; } break;
                    case "Occlusion": if (attr != null) { mat.SetFloat("_VertexOcclusion", 1f); need.occ = true; } break;
                    case "Effect Mask": if (attr != null) { mat.SetFloat("_VertexMask", 1f); need.mask = true; } break;
                    case "Aurora Coord":
                        mat.SetFloat("_AuroraCoordUV", (J.Get(l, "out") as string) == "UV" ? 1f : 0f);
                        if ((J.Get(l, "out") as string) != "Object" && (J.Get(l, "out") as string) != "UV")
                            rep.warnings.Add(name + ": Aurora Coord = " + J.Get(l, "out") + " (object space used)");
                        break;
                    case "Normal Override":
                        var col = J.O(J.Get(l, "color"));
                        if (col != null && J.Get(col, "image") != null) rep.warnings.Add(name + ": normal map image is not carried over");
                        break;
                    case "Iri Base Phase":
                    case "Aurora Strength":
                        if ((J.Get(l, "node") as string) == "ShaderNodeMapRange")
                        {
                            string vp = kv.Key == "Iri Base Phase" ? "_IriBasePhaseThick" : "_AuroraStrengthThick";
                            mat.SetVector(vp, new Vector4(1f, J.F(J.Get(l, "to_min")), J.F(J.Get(l, "to_max")), 0f));
                            if (Math.Abs(J.F(J.Get(l, "from_min"))) > 1e-6 || Math.Abs(J.F(J.Get(l, "from_max")) - 1f) > 1e-6)
                                rep.warnings.Add(name + ": " + kv.Key + " map range does not start at 0..1");
                        }
                        else rep.warnings.Add(name + ": " + kv.Key + " is linked (" + J.Get(l, "node") + "), not carried over");
                        break;
                    default:
                        rep.warnings.Add(name + ": linked input not carried over: " + kv.Key + " (" + J.Get(l, "node") + ")");
                        break;
                }
            }
            bool transparent = (J.Get(ms, "method") as string) == "BLENDED";
            bool cull = J.Get(ms, "backface_culling") is bool b && b;
            LidaAuroraToonMaterials.SetupRenderState(mat, transparent, cull);
            return mat;
        }

        static Texture2D LoadTex(string dir, string image, bool srgb, Report rep)
        {
            var guids = AssetDatabase.FindAssets(image + " t:Texture2D", new[] { dir.TrimEnd('/') });
            string path = guids.Select(AssetDatabase.GUIDToAssetPath).FirstOrDefault(p => Path.GetFileNameWithoutExtension(p) == image);
            if (path == null) { rep.warnings.Add("texture not found: " + image); return null; }
            var ti = AssetImporter.GetAtPath(path) as TextureImporter;
            if (ti != null && ti.sRGBTexture != srgb) { ti.sRGBTexture = srgb; ti.SaveAndReimport(); }
            return AssetDatabase.LoadAssetAtPath<Texture2D>(path);
        }

        /// <summary>
        /// Vertex colour R = thickness, G = occlusion, B = effect mask, A = alpha attribute, taken from
        /// attr_&lt;object&gt;.json (Blender object space) by the nearest vertex. A copy of the mesh is saved.
        /// </summary>
        public static void BakeVertexColors(Renderer r, string specDir, string outDir, Report rep)
        {
            Mesh mesh = r is SkinnedMeshRenderer smr ? smr.sharedMesh : r.GetComponent<MeshFilter>()?.sharedMesh;
            if (mesh == null) return;
            string obj = r.gameObject.name;
            var verts = mesh.vertices;
            var cols = new Color[verts.Length];
            for (int i = 0; i < cols.Length; i++) cols[i] = new Color(0f, 1f, 1f, 1f);
            string[] files = { Path.Combine(specDir, "attr_" + obj + ".json"), Path.Combine(specDir, "attr_" + obj + "_Alpha.json") };
            foreach (var f in files)
            {
                if (!File.Exists(f)) continue;
                var d = J.O(J.Parse(File.ReadAllText(f)));
                var pos = J.Floats(d["position"]);
                var map = new Dictionary<string, (int ch, float[] v)>();
                foreach (var kv in d)
                {
                    if (kv.Key == "lida_aurora_thickness") map[kv.Key] = (0, J.Floats(kv.Value));
                    else if (kv.Key == "lida_aurora_occlusion") map[kv.Key] = (1, J.Floats(kv.Value));
                    else if (kv.Key == "lida_aurora_mask") map[kv.Key] = (2, J.Floats(kv.Value));
                    else if (kv.Key == "Alpha" && kv.Value is List<object>) map[kv.Key] = (3, J.Floats(kv.Value));
                }
                int n = pos.Length / 3;
                // Blender -> Unity mesh space: try the VRM axes (x mirrored) and without the mirror
                var cands = new (string name, Func<float, float, float, Vector3> f)[]
                {
                    ("(-x, z, -y)", (x, y, z) => new Vector3(-x, z, -y)),
                    ("(x, z, -y)", (x, y, z) => new Vector3(x, z, -y)),
                    ("(x, z, y)", (x, y, z) => new Vector3(x, z, y)),
                };
                var src = new Vector3[n];
                // choose the axes on a sample of 150 vertices (brute force), then match every vertex with a grid
                (string, Func<float, float, float, Vector3>) best = default; float bestErr = float.MaxValue;
                int step = Math.Max(1, verts.Length / 150);
                foreach (var c in cands)
                {
                    for (int i = 0; i < n; i++) src[i] = c.f(pos[3 * i], pos[3 * i + 1], pos[3 * i + 2]);
                    double err = 0; int cnt = 0;
                    for (int i = 0; i < verts.Length; i += step)
                    {
                        float bd = float.MaxValue;
                        for (int j = 0; j < n; j++) { float dd = (src[j] - verts[i]).sqrMagnitude; if (dd < bd) bd = dd; }
                        err += Mathf.Sqrt(bd); cnt++;
                    }
                    float e = (float)(err / Math.Max(cnt, 1));
                    if (e < bestErr) { bestErr = e; best = c; }
                }
                for (int i = 0; i < n; i++) src[i] = best.Item2(pos[3 * i], pos[3 * i + 1], pos[3 * i + 2]);
                var grid = new Grid(src, 0.004f);
                var bestIdx = new int[verts.Length];
                double errAll = 0;
                for (int i = 0; i < verts.Length; i++) { bestIdx[i] = grid.Nearest(verts[i], out float dd); errAll += dd; }
                bestErr = (float)(errAll / Math.Max(verts.Length, 1));
                rep.axis[obj] = best.Item1;
                rep.matchError[Path.GetFileName(f)] = bestErr;
                foreach (var kv in map)
                {
                    if (kv.Value.v == null) continue;
                    for (int i = 0; i < verts.Length; i++)
                    {
                        var c = cols[i];
                        c[kv.Value.ch] = kv.Value.v[bestIdx[i]];
                        cols[i] = c;
                    }
                }
                if (J.Get(d, "missing") != null) rep.warnings.Add(obj + ": attribute missing in Blender, 0 used: " + string.Join(",", J.A(d["missing"]).Select(o => o.ToString())));
            }
            var copy = UnityEngine.Object.Instantiate(mesh);
            copy.name = mesh.name + " aurora";
            copy.colors = cols;
            string path = Path.Combine(outDir, Safe(obj) + "_aurora.asset").Replace('\\', '/');
            AssetDatabase.DeleteAsset(path);
            AssetDatabase.CreateAsset(copy, path);
            if (r is SkinnedMeshRenderer sk) sk.sharedMesh = copy; else r.GetComponent<MeshFilter>().sharedMesh = copy;
            rep.bakedMeshes.Add(obj);
        }

        /// <summary>uniform grid for nearest-vertex lookups</summary>
        class Grid
        {
            readonly Dictionary<(int, int, int), List<int>> cells = new Dictionary<(int, int, int), List<int>>();
            readonly Vector3[] p; readonly float h;
            public Grid(Vector3[] pts, float cell)
            {
                p = pts; h = cell;
                for (int i = 0; i < pts.Length; i++)
                {
                    var k = Key(pts[i]);
                    if (!cells.TryGetValue(k, out var l)) cells[k] = l = new List<int>();
                    l.Add(i);
                }
            }
            (int, int, int) Key(Vector3 v) => (Mathf.FloorToInt(v.x / h), Mathf.FloorToInt(v.y / h), Mathf.FloorToInt(v.z / h));
            public int Nearest(Vector3 q, out float dist)
            {
                var k = Key(q); int best = 0; float bd = float.MaxValue;
                for (int rad = 1; rad <= 64; rad *= 2)
                {
                    for (int x = -rad; x <= rad; x++)
                    for (int y = -rad; y <= rad; y++)
                    for (int z = -rad; z <= rad; z++)
                    {
                        if (!cells.TryGetValue((k.Item1 + x, k.Item2 + y, k.Item3 + z), out var l)) continue;
                        foreach (int i in l) { float d = (p[i] - q).sqrMagnitude; if (d < bd) { bd = d; best = i; } }
                    }
                    if (bd < (rad * h) * (rad * h)) break;
                }
                dist = Mathf.Sqrt(bd);
                return best;
            }
        }
    }
}
