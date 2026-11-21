// SPDX-License-Identifier: LicenseRef-Lida-Attribution-1.1
// Copyright (c) 2026 Lida
// ============================================================================
// LidaAuroraToonPasses.hlsl - URP passes of LidaAuroraToon (forward, depth
// pre-pass for the see-through presets, shadow caster, depth only, depth normals).
// Only Unity / URP ShaderLibrary functions are called; nothing is copied from
// other shaders.
// ============================================================================
#ifndef LIDA_AURORA_TOON_PASSES_INCLUDED
#define LIDA_AURORA_TOON_PASSES_INCLUDED

#include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
#include "LidaAuroraToonInput.hlsl"
#include "LidaAuroraToonCore.hlsl"

TEXTURE2D(_BaseMap);  SAMPLER(sampler_BaseMap);
TEXTURE2D(_ShadeMap);
TEXTURE2D(_AlphaMap);

// set by LidaAuroraToonControl (global); when absent the defaults of Blender are used
float  _LidaAuroraLevelsValid;
float4 _LidaAuroraLevelsA;      // Aurora, Aurora Speed, Iridescence, Glint
float4 _LidaAuroraLevelsB;      // Glint Color, Glint Hue, Glint Speed, Shadows
float  _LidaAuroraTimeValid;
float  _LidaAuroraTime;         // seconds (Blender: frame / fps)
// set per renderer by LidaAuroraToonControl: world -> character root, so the aurora coordinate
// is the object space of Blender even on skinned meshes
float    _LidaAuroraRootValid;
float4x4 _LidaAuroraRootW2L;

AuroraLevels AuroraGetLevels()
{
    AuroraLevels lv;
    if (_LidaAuroraLevelsValid > 0.5)
    {
        lv.Aurora = _LidaAuroraLevelsA.x; lv.AuroraSpeed = _LidaAuroraLevelsA.y;
        lv.Iridescence = _LidaAuroraLevelsA.z; lv.Glint = _LidaAuroraLevelsA.w;
        lv.GlintColor = _LidaAuroraLevelsB.x; lv.GlintHue = _LidaAuroraLevelsB.y;
        lv.GlintSpeed = _LidaAuroraLevelsB.z; lv.Shadows = _LidaAuroraLevelsB.w;
    }
    else
    {
        lv.Aurora = 1.0; lv.AuroraSpeed = 1.0; lv.Iridescence = 1.0; lv.Glint = 1.0;
        lv.GlintColor = 1.0; lv.GlintHue = 0.0; lv.GlintSpeed = 1.0; lv.Shadows = 0.0;
    }
    return lv;
}

float AuroraGetTime() { return (_LidaAuroraTimeValid > 0.5) ? _LidaAuroraTime : _Time.y; }

struct AuroraAttributes
{
    float4 positionOS : POSITION;
    float3 normalOS   : NORMAL;
    float2 uv         : TEXCOORD0;
    float4 color      : COLOR;
    UNITY_VERTEX_INPUT_INSTANCE_ID
};

struct AuroraVaryings
{
    float4 positionCS : SV_POSITION;
    float3 positionWS : TEXCOORD0;
    float3 normalWS   : TEXCOORD1;
    float2 uv         : TEXCOORD2;
    float4 color      : TEXCOORD3;
    float  fogFactor  : TEXCOORD4;
    UNITY_VERTEX_INPUT_INSTANCE_ID
    UNITY_VERTEX_OUTPUT_STEREO
};

AuroraVaryings AuroraForwardVertex(AuroraAttributes v)
{
    AuroraVaryings o = (AuroraVaryings)0;
    UNITY_SETUP_INSTANCE_ID(v);
    UNITY_TRANSFER_INSTANCE_ID(v, o);
    UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
    VertexPositionInputs vpi = GetVertexPositionInputs(v.positionOS.xyz);
    o.positionCS = vpi.positionCS;
    o.positionWS = vpi.positionWS;
    o.normalWS = TransformObjectToWorldNormal(v.normalOS);
    o.uv = TRANSFORM_TEX(v.uv, _BaseMap);
    o.color = v.color;
    o.fogFactor = ComputeFogFactor(vpi.positionCS.z);
    return o;
}

#if defined(LIDA_AURORA_FORWARD)
#include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

// adds one light to the colour (Blender: (look under the light - unlit look) x weight x glint keep)
void AuroraAddLight(inout float3 col, AuroraParams m, AuroraPrep r, AuroraLevels lv, float3 unlitFloor, Light li)
{
    float3 kcol;
    float w = AuroraLightWeight(li.color, li.distanceAttenuation, kcol);
    UNITY_BRANCH if (w <= 0.0) return;
    float NL = dot(r.N, li.direction);
    float Ls0 = AuroraShadowedNL(NL, li.shadowAttenuation, max(m.ReceiveShadow, lv.Shadows));
    AuroraSurface s = AuroraSurfaceTerm(m, r, true, Ls0, li.direction, kcol);
    col += max(s.cv - unlitFloor, 0.0) * (w * r.g_keep);
}

float4 AuroraForwardFragment(AuroraVaryings i, FRONT_FACE_TYPE facing : FRONT_FACE_SEMANTIC) : SV_Target
{
    UNITY_SETUP_INSTANCE_ID(i);
    UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);

    AuroraParams m = AuroraLoadParams();
    float4 vc = i.color;
    UNITY_BRANCH if (_VertexThickness > 0.5) m.Thickness = vc.r;
    UNITY_BRANCH if (_VertexOcclusion > 0.5) m.Occlusion = vc.g;
    UNITY_BRANCH if (_VertexMask > 0.5) m.EffectMask = vc.b;
    // inputs that follow the thickness (Blender: attribute -> Map Range)
    UNITY_BRANCH if (_IriBasePhaseThick.x > 0.5) m.IriBasePhase = lerp(_IriBasePhaseThick.y, _IriBasePhaseThick.z, saturate(m.Thickness));
    UNITY_BRANCH if (_AuroraStrengthThick.x > 0.5) m.AuroraStrength = lerp(_AuroraStrengthThick.y, _AuroraStrengthThick.z, saturate(m.Thickness));

    float3 baseColor = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, i.uv).rgb * _BaseColor.rgb;
    float3 shadeTex = SAMPLE_TEXTURE2D(_ShadeMap, sampler_BaseMap, i.uv).rgb * _ShadeMapColor.rgb;
    float alphaIn = _Alpha;
    UNITY_BRANCH if (_UseAlphaMap > 0.5) alphaIn *= SAMPLE_TEXTURE2D(_AlphaMap, sampler_BaseMap, i.uv).r;
    UNITY_BRANCH if (_VertexAlpha > 0.5) alphaIn *= vc.a;

    float3 positionWS = i.positionWS;
    float3 N = LatSafeNormalize(i.normalWS);
    N = IS_FRONT_VFACE(facing, N, -N);            // EEVEE turns the normal toward the viewer on back faces
    float3 V = GetWorldSpaceNormalizeViewDir(positionWS);
    float3 Nview = LatSafeNormalize(TransformWorldToViewDir(N));

    float3 rootPos = (_LidaAuroraRootValid > 0.5) ? mul(_LidaAuroraRootW2L, float4(positionWS, 1.0)).xyz : positionWS;
    float3 objPos = (_LidaAuroraRootValid > 0.5) ? rootPos : TransformWorldToObject(positionWS);
    float3 P = (_AuroraCoordUV > 0.5) ? float3(i.uv, 0.0) : LatToBlender(objPos);
    float3 PW = LatToBlender(rootPos);

    AuroraLevels lv = AuroraGetLevels();
    AuroraPrep r = AuroraPrepare(m, lv, N, N, V, Nview, P, PW, baseColor, shadeTex, AuroraGetTime());
    AuroraSurface amb = AuroraSurfaceTerm(m, r, false, 0.0, float3(0, 0, 1), float3(1, 1, 1));
    float3 unlitFloor = amb.cv * (1.0 - _UnlitDarkness);
    float3 col = AuroraAddGlint(r, unlitFloor);

    float4 shadowCoord = TransformWorldToShadowCoord(positionWS);
    Light mainLight = GetMainLight(shadowCoord, positionWS, half4(1, 1, 1, 1));
    AuroraAddLight(col, m, r, lv, unlitFloor, mainLight);
#if defined(_ADDITIONAL_LIGHTS)
    UNITY_BRANCH if (_AdditionalLights > 0.5)
    {
        InputData inputData = (InputData)0;          // the URP light loop macros read inputData
        inputData.positionWS = positionWS;
        inputData.normalWS = N;
        inputData.normalizedScreenSpaceUV = GetNormalizedScreenSpaceUV(i.positionCS);
        half4 shadowMask = half4(1, 1, 1, 1);
    #if USE_CLUSTER_LIGHT_LOOP
        [loop] for (uint li = 0; li < min(URP_FP_DIRECTIONAL_LIGHTS_COUNT, MAX_VISIBLE_LIGHTS); li++)
        {
            Light dl = GetAdditionalLight(li, positionWS, shadowMask);
            AuroraAddLight(col, m, r, lv, unlitFloor, dl);
        }
    #endif
        uint lightCount = GetAdditionalLightsCount();
        LIGHT_LOOP_BEGIN(lightCount)
            Light al = GetAdditionalLight(lightIndex, positionWS, shadowMask);
            AuroraAddLight(col, m, r, lv, unlitFloor, al);
        LIGHT_LOOP_END
    }
#endif
    col = MixFog(col, i.fogFactor);
    float alpha = AuroraOpacity(m, r, amb, alphaIn);
    return float4(col, (_Surface > 0.5) ? alpha : 1.0);
}
#endif // LIDA_AURORA_FORWARD

// ---------- depth, shadow ----------
struct AuroraDepthVaryings
{
    float4 positionCS : SV_POSITION;
    float3 normalWS   : TEXCOORD0;
    UNITY_VERTEX_INPUT_INSTANCE_ID
};

#if defined(LIDA_AURORA_SHADOW)
#include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Shadows.hlsl"
float3 _LightDirection;
float3 _LightPosition;
#endif

AuroraDepthVaryings AuroraDepthVertex(AuroraAttributes v)
{
    AuroraDepthVaryings o = (AuroraDepthVaryings)0;
    UNITY_SETUP_INSTANCE_ID(v);
    UNITY_TRANSFER_INSTANCE_ID(v, o);
    float3 positionWS = TransformObjectToWorld(v.positionOS.xyz);
    float3 normalWS = TransformObjectToWorldNormal(v.normalOS);
#if defined(LIDA_AURORA_SHADOW)
  #if defined(_CASTING_PUNCTUAL_LIGHT_SHADOW)
    float3 lightDir = normalize(_LightPosition - positionWS);
  #else
    float3 lightDir = _LightDirection;
  #endif
    float4 cs = TransformWorldToHClip(ApplyShadowBias(positionWS, normalWS, lightDir));
  #if UNITY_REVERSED_Z
    cs.z = min(cs.z, UNITY_NEAR_CLIP_VALUE);
  #else
    cs.z = max(cs.z, UNITY_NEAR_CLIP_VALUE);
  #endif
    o.positionCS = cs;
#else
    o.positionCS = TransformWorldToHClip(positionWS);
#endif
    o.normalWS = normalWS;
    return o;
}

half4 AuroraDepthFragment(AuroraDepthVaryings i) : SV_Target
{
    return half4(i.positionCS.z, 0, 0, 0);
}

half4 AuroraDepthNormalsFragment(AuroraDepthVaryings i, FRONT_FACE_TYPE facing : FRONT_FACE_SEMANTIC) : SV_Target
{
    float3 n = LatSafeNormalize(i.normalWS);
    n = IS_FRONT_VFACE(facing, n, -n);
    return half4(NormalizeNormalPerPixel(n), 0.0);
}

#endif // LIDA_AURORA_TOON_PASSES_INCLUDED
