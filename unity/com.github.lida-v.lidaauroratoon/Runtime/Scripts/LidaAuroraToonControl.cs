// SPDX-License-Identifier: LicenseRef-Lida-Attribution-1.1
// Copyright (c) 2026 Lida
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace LidaAuroraToon
{
    /// <summary>
    /// The master sliders of LidaAuroraToon (the "LidaAuroraToon Control" object of Blender) and the clock.
    /// Put one on the character root. The levels and the clock are global shader values, so one Control
    /// drives every LidaAuroraToon material in the scene. Each renderer under <see cref="characterRoot"/>
    /// also gets the root matrix, so the aurora coordinate is the object space of Blender even on skinned meshes.
    /// </summary>
    [ExecuteAlways]
    [DisallowMultipleComponent]
    [AddComponentMenu("LidaAuroraToon/LidaAuroraToon Control")]
    public class LidaAuroraToonControl : MonoBehaviour
    {
        [Header("Master levels (same names as in Blender)")]
        [Range(0f, 3f)] public float aurora = 1f;
        [Range(0f, 5f)] public float auroraSpeed = 1f;
        [Range(0f, 3f)] public float iridescence = 1f;
        [Range(0f, 3f)] public float glint = 1f;
        [Tooltip("0 = white light, 1 = as the material says, 2 = more colour")]
        [Range(0f, 2f)] public float glintColor = 1f;
        [Tooltip("moves the whole glint palette (0..1 is one turn)")]
        [Range(0f, 1f)] public float glintHue = 0f;
        [Range(0f, 5f)] public float glintSpeed = 1f;
        [Tooltip("1 = every material receives cast shadows")]
        [Range(0f, 1f)] public float shadows = 0f;

        [Header("Glow (bloom of the post-processing volume)")]
        [Range(0f, 3f)] public float glow = 0.6f;
        [Tooltip("A volume whose profile has Bloom. Its intensity becomes glow x glowToBloom. Empty = not touched.")]
        public Volume glowVolume;
        public float glowToBloom = 1f;

        public enum TimeSource { UnityTime, Fixed }
        [Header("Clock (seconds; Blender: frame / fps)")]
        public TimeSource timeSource = TimeSource.UnityTime;
        public float fixedTime = 0f;
        public float timeScale = 1f;

        [Tooltip("The character root (Blender object space). Empty = this transform.")]
        public Transform characterRoot;

        static readonly int IdLevelsValid = Shader.PropertyToID("_LidaAuroraLevelsValid");
        static readonly int IdLevelsA = Shader.PropertyToID("_LidaAuroraLevelsA");
        static readonly int IdLevelsB = Shader.PropertyToID("_LidaAuroraLevelsB");
        static readonly int IdTimeValid = Shader.PropertyToID("_LidaAuroraTimeValid");
        static readonly int IdTime = Shader.PropertyToID("_LidaAuroraTime");
        static readonly int IdRootValid = Shader.PropertyToID("_LidaAuroraRootValid");
        static readonly int IdRootW2L = Shader.PropertyToID("_LidaAuroraRootW2L");
        MaterialPropertyBlock _mpb;
        Renderer[] _renderers;

        public float CurrentTime => timeSource == TimeSource.Fixed ? fixedTime
            : (Application.isPlaying ? Time.time : (float)Time.realtimeSinceStartupAsDouble) * timeScale;

        void OnEnable() { _renderers = null; Apply(); }
        void OnValidate() { Apply(); }
        void LateUpdate() { Apply(); }

        void OnDisable()
        {
            Shader.SetGlobalFloat(IdLevelsValid, 0f);
            Shader.SetGlobalFloat(IdTimeValid, 0f);
        }

        /// <summary>Find the renderers again (after adding parts to the character).</summary>
        public void RefreshRenderers() { _renderers = null; Apply(); }

        public void Apply()
        {
            Shader.SetGlobalFloat(IdLevelsValid, 1f);
            Shader.SetGlobalVector(IdLevelsA, new Vector4(aurora, auroraSpeed, iridescence, glint));
            Shader.SetGlobalVector(IdLevelsB, new Vector4(glintColor, glintHue, glintSpeed, shadows));
            Shader.SetGlobalFloat(IdTimeValid, 1f);
            Shader.SetGlobalFloat(IdTime, CurrentTime);

            var root = characterRoot != null ? characterRoot : transform;
            if (_renderers == null) _renderers = root.GetComponentsInChildren<Renderer>(true);
            if (_mpb == null) _mpb = new MaterialPropertyBlock();
            Matrix4x4 w2l = root.worldToLocalMatrix;
            foreach (var r in _renderers)
            {
                if (r == null) continue;
                r.GetPropertyBlock(_mpb);
                _mpb.SetFloat(IdRootValid, 1f);
                _mpb.SetMatrix(IdRootW2L, w2l);
                r.SetPropertyBlock(_mpb);
            }

            if (glowVolume != null && glowVolume.sharedProfile != null && glowVolume.sharedProfile.TryGet(out Bloom bloom))
                bloom.intensity.Override(glow * glowToBloom);
        }
    }
}
