// SPDX-License-Identifier: LicenseRef-Lida-Attribution-1.1
// Copyright (c) 2026 Lida
using UnityEngine;
using UnityEngine.Rendering;

namespace LidaAuroraToon
{
    /// <summary>Small helpers for LidaAuroraToon materials (usable at runtime and in the editor).</summary>
    public static class LidaAuroraToonMaterials
    {
        public const string ShaderName = "LidaAuroraToon/Toon";

        /// <summary>
        /// Opaque, or see-through like Blender's BLENDED with Transparency Overlap off: the object first
        /// writes its depth (pass "SRPDefaultUnlit"), then only its nearest wall is blended.
        /// cullBack = Blender's Backface Culling (off by default: generated meshes often have flipped faces).
        /// </summary>
        public static void SetupRenderState(Material m, bool transparent, bool cullBack = false)
        {
            m.SetFloat("_Surface", transparent ? 1f : 0f);
            m.SetFloat("_Cull", cullBack ? (float)CullMode.Back : (float)CullMode.Off);
            if (transparent)
            {
                m.SetFloat("_SrcBlend", (float)BlendMode.SrcAlpha);
                m.SetFloat("_DstBlend", (float)BlendMode.OneMinusSrcAlpha);
                m.SetFloat("_ZWrite", 0f);
                m.SetOverrideTag("RenderType", "Transparent");
                m.renderQueue = (int)RenderQueue.Transparent;
                m.SetShaderPassEnabled("SRPDefaultUnlit", true);
                m.SetShaderPassEnabled("ShadowCaster", false);
                m.SetShaderPassEnabled("DepthOnly", false);
                m.SetShaderPassEnabled("DepthNormals", false);
            }
            else
            {
                m.SetFloat("_SrcBlend", (float)BlendMode.One);
                m.SetFloat("_DstBlend", (float)BlendMode.Zero);
                m.SetFloat("_ZWrite", 1f);
                m.SetOverrideTag("RenderType", "Opaque");
                m.renderQueue = (int)RenderQueue.Geometry;
                m.SetShaderPassEnabled("SRPDefaultUnlit", false);
                m.SetShaderPassEnabled("ShadowCaster", true);
                m.SetShaderPassEnabled("DepthOnly", true);
                m.SetShaderPassEnabled("DepthNormals", true);
            }
        }

        /// <summary>Set a colour given in linear values (Blender's numbers). Unity keeps colours in sRGB.</summary>
        public static void SetLinearColor(Material m, string property, Vector3 linear)
        {
            m.SetColor(property, new Color(linear.x, linear.y, linear.z, 1f).gamma);
        }
    }
}
