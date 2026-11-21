// SPDX-License-Identifier: LicenseRef-Lida-Attribution-1.1
// Copyright (c) 2026 Lida
// Unity side of the Blender-vs-Unity check on primitives (tests/unity_compare/blender_primitives.py).
// Copy this file and the OBJ files into a Unity project (Assets/<any>/Editor and Assets/<any>/Primitives), then
//   Unity -batchmode -quit -projectPath <p> -executeMethod LidaAuroraToon.Tests.PrimitiveCompare.Run
//         -latCompare <folder with scene.json> -latObjDir Assets/<any>/Primitives
// Writes unity_fNNN.png next to blender_fNNN.png. Nothing is saved to the project except the imported OBJs.
using System;
using System.IO;
using LidaAuroraToon;
using LidaAuroraToon.Editor;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using J = LidaAuroraToon.Editor.LidaAuroraToonJson;

namespace LidaAuroraToon.Tests
{
    public static class PrimitiveCompare
    {
        static string Arg(string k, string d = null)
        {
            var a = Environment.GetCommandLineArgs();
            for (int i = 0; i < a.Length - 1; i++) if (a[i] == k) return a[i + 1];
            return d;
        }

        static Vector3 B2U(float[] v) => new Vector3(-v[0], v[2], -v[1]);

        public static void Run()
        {
            int code = 0;
            try { Do(); }
            catch (Exception e) { code = 1; Debug.LogError("PrimitiveCompare: " + e); }
            if (Application.isBatchMode) EditorApplication.Exit(code);
        }

        static void Do()
        {
            string dir = Arg("-latCompare");
            string objDir = Arg("-latObjDir");
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            ShaderUtil.allowAsyncCompilation = false;
            var info = J.O(J.Parse(File.ReadAllText(Path.Combine(dir, "scene.json"))));
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            RenderSettings.ambientMode = AmbientMode.Flat;
            RenderSettings.ambientLight = Color.black;
            RenderSettings.skybox = null;

            var lgo = new GameObject("Sun");
            var light = lgo.AddComponent<Light>();
            light.type = LightType.Directional; light.intensity = 1f; light.color = Color.white; light.shadows = LightShadows.None;
            lgo.transform.rotation = Quaternion.LookRotation(-B2U(J.Floats(info["sun_to_light"])), Vector3.up);

            var root = new GameObject("Root");
            var ctrl = root.AddComponent<LidaAuroraToonControl>();
            ctrl.timeSource = LidaAuroraToonControl.TimeSource.Fixed;
            foreach (var o in J.A(info["items"]))
            {
                var it = J.O(o);
                string name = (string)it["name"];
                var mesh = AssetDatabase.LoadAllAssetsAtPath(objDir + "/" + name + ".obj");
                Mesh m = null;
                foreach (var a in mesh) if (a is Mesh mm) m = mm;
                if (m == null) throw new Exception("mesh not found " + name);
                var go = new GameObject(name);
                go.transform.position = B2U(J.Floats(it["location"]));
                go.AddComponent<MeshFilter>().sharedMesh = m;
                var mr = go.AddComponent<MeshRenderer>();
                var mat = LidaAuroraToonPresets.Create((string)it["preset"], name);
                var bc = J.Floats(it["base_linear"]);
                LidaAuroraToonMaterials.SetLinearColor(mat, "_BaseColor", new Vector3(bc[0], bc[1], bc[2]));
                if (it.ContainsKey("thickness")) mat.SetFloat("_VertexThickness", 1f);
                mr.sharedMaterial = mat;
                if (it.ContainsKey("thickness"))
                {
                    var rep = new LidaAuroraToonSpec.Report();
                    LidaAuroraToonSpec.BakeVertexColors(mr, dir, objDir, rep);
                    foreach (var kv in rep.matchError) Debug.Log("PrimitiveCompare match " + kv.Key + " " + kv.Value + " axis " + rep.axis[name]);
                }
            }
            // no character root: object space = each primitive's own space (as in Blender)
            ctrl.characterRoot = null;
            var cg = J.O(info["camera"]);
            var cgo = new GameObject("Cam");
            var cam = cgo.AddComponent<Camera>();
            cam.orthographic = true;
            cam.orthographicSize = J.F(cg["ortho_height"]) * 0.5f;
            cam.clearFlags = CameraClearFlags.SolidColor;
            var bg = J.Floats(info["background_linear"]);
            cam.backgroundColor = new Color(bg[0], bg[1], bg[2], 1f).gamma;
            cam.nearClipPlane = 0.01f; cam.farClipPlane = 100f;
            cgo.transform.position = B2U(J.Floats(cg["position"]));
            cgo.transform.rotation = Quaternion.LookRotation(B2U(J.Floats(cg["forward"])), B2U(J.Floats(cg["up"])));
            var cd = cam.GetUniversalAdditionalCameraData();
            cd.renderPostProcessing = false; cd.antialiasing = AntialiasingMode.None;
            var res = J.Floats(cg["res"]);
            int W = (int)res[0], H = (int)res[1];
            var times = J.O(info["time"]);
            foreach (var f in J.A(info["frames"]))
            {
                int fr = (int)J.F(f);
                ctrl.fixedTime = J.F(times[fr.ToString()]);
                // the root matrix must not be set: Apply() puts it on every renderer under the control
                ctrl.Apply();
                foreach (var r in root.scene.GetRootGameObjects())
                    foreach (var rr in r.GetComponentsInChildren<Renderer>()) { var mpb = new MaterialPropertyBlock(); rr.GetPropertyBlock(mpb); mpb.SetFloat("_LidaAuroraRootValid", 0f); rr.SetPropertyBlock(mpb); }
                var rt = new RenderTexture(W, H, 24, RenderTextureFormat.ARGB32, RenderTextureReadWrite.sRGB) { antiAliasing = 8 };
                rt.Create();
                cam.targetTexture = rt; cam.aspect = (float)W / H;
                cam.Render(); cam.Render();
                var prev = RenderTexture.active; RenderTexture.active = rt;
                var tex = new Texture2D(W, H, TextureFormat.RGBA32, false, false);
                tex.ReadPixels(new Rect(0, 0, W, H), 0, 0); tex.Apply();
                RenderTexture.active = prev; cam.targetTexture = null;
                File.WriteAllBytes(Path.Combine(dir, string.Format("unity_f{0:000}.png", fr)), tex.EncodeToPNG());
                UnityEngine.Object.DestroyImmediate(tex); rt.Release();
            }
        }
    }
}
