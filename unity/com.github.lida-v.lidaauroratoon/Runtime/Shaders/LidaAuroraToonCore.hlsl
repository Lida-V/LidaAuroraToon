// SPDX-License-Identifier: LicenseRef-Lida-Attribution-1.1
// Copyright (c) 2026 Lida
// ============================================================================
// LidaAuroraToonCore.hlsl - the look of LidaAuroraToon, node for node the same
// math as the Blender node group (blender/lida_aurora_toon/shader.py, 0.3.6,
// lighting='NODES'). Engine-free: the pass prepares the inputs.
//
// Coordinates: the aurora, the noise and the band directions use Blender axes
// (X right, Y back, Z up). The pass converts Unity positions with LatToBlender().
// Lighting terms (N.L, N.V, half vector) do not depend on the axes.
// ============================================================================
#ifndef LIDA_AURORA_TOON_CORE_INCLUDED
#define LIDA_AURORA_TOON_CORE_INCLUDED

#include "LidaAuroraToonNoise.hlsl"

#define LAT_TAU 6.2831853

// Unity (left-handed, Y up) -> Blender (right-handed, Z up): the inverse of (-x, z, -y)
float3 LatToBlender(float3 u) { return float3(-u.x, -u.z, u.y); }

float3 LatSafeNormalize(float3 v)
{
    float l = length(v);
    return l > 1e-8 ? v / l : float3(0, 0, 0);
}

// Blender Map Range (smoothstep, clamped) to 0..1
float LatSmooth(float x, float lo, float hi)
{
    if (hi == lo) return 0.0;
    return (lo > hi) ? 1.0 - smoothstep(hi, lo, x) : smoothstep(lo, hi, x);
}

float LatLum(float3 c) { return dot(c, float3(0.2126, 0.7152, 0.0722)); }

float3 LatHsvToRgb(float h, float s, float v)
{
    if (s == 0.0) return float3(v, v, v);
    if (h == 1.0) h = 0.0;
    h *= 6.0;
    float i = floor(h);
    float f = h - i;
    float p = v * (1.0 - s);
    float q = v * (1.0 - s * f);
    float t = v * (1.0 - s * (1.0 - f));
    if (i == 0.0) return float3(v, t, p);
    if (i == 1.0) return float3(q, v, p);
    if (i == 2.0) return float3(p, v, t);
    if (i == 3.0) return float3(p, q, v);
    if (i == 4.0) return float3(t, p, v);
    return float3(v, p, q);
}

float3 LatRgbToHsv(float3 c)
{
    float cmax = max(c.r, max(c.g, c.b));
    float cmin = min(c.r, min(c.g, c.b));
    float cd = cmax - cmin;
    float h = 0.0, s = 0.0, v = cmax;
    if (cmax != 0.0) s = cd / cmax;
    if (s != 0.0)
    {
        float3 k = (float3(cmax, cmax, cmax) - c) / cd;
        if (c.r == cmax) h = k.b - k.g;
        else if (c.g == cmax) h = 2.0 + k.r - k.b;
        else h = 4.0 + k.g - k.r;
        h /= 6.0;
        if (h < 0.0) h += 1.0;
    }
    return float3(h, s, v);
}

// Hue/Saturation node with hue 0.5, value 1, factor 1
float3 LatSaturate(float3 c, float sat)
{
    float3 hsv = LatRgbToHsv(c);
    return max(LatHsvToRgb(frac(hsv.x + 1.0), saturate(hsv.y * sat), hsv.z), 0.0);
}

// linear colour ramps (positions and colours of shader.py)
float3 LatRamp(float x, float4 p0, float4 p1, float4 p2, float4 p3, float4 p4, float4 p5)
{
    // pN.xyz = colour, pN.w = position
    if (x <= p0.w) return p0.xyz;
    if (x < p1.w) return lerp(p0.xyz, p1.xyz, (x - p0.w) / (p1.w - p0.w));
    if (x < p2.w) return lerp(p1.xyz, p2.xyz, (x - p1.w) / (p2.w - p1.w));
    if (x < p3.w) return lerp(p2.xyz, p3.xyz, (x - p2.w) / (p3.w - p2.w));
    if (x < p4.w) return lerp(p3.xyz, p4.xyz, (x - p3.w) / (p4.w - p3.w));
    if (x < p5.w) return lerp(p4.xyz, p5.xyz, (x - p4.w) / (p5.w - p4.w));
    return p5.xyz;
}

float3 LatAuroraRamp(float x)
{
    return LatRamp(x, float4(0.25, 1.00, 0.62, 0.00), float4(0.20, 0.85, 1.00, 0.22), float4(0.38, 0.48, 1.00, 0.45),
                      float4(0.72, 0.42, 1.00, 0.65), float4(1.00, 0.52, 0.82, 0.85), float4(0.25, 1.00, 0.62, 1.00));
}

float3 LatGlintRamp(float x)
{
    return LatRamp(x, float4(1.00, 0.42, 0.74, 0.00), float4(0.76, 0.48, 1.00, 0.22), float4(0.42, 0.62, 1.00, 0.45),
                      float4(0.36, 0.95, 0.92, 0.62), float4(0.70, 0.55, 1.00, 0.82), float4(1.00, 0.42, 0.74, 1.00));
}

// master levels (the LidaAuroraToon Control sliders)
struct AuroraLevels
{
    float Aurora, AuroraSpeed, Iridescence, Glint, GlintColor, GlintHue, GlintSpeed, Shadows;
};

// everything that does not depend on a light
struct AuroraPrep
{
    float3 N, V;
    float3 base, shade1, shade2, lit0;
    float occ, open_, fres, thin, edge;
    float3 iri, iri_n;
    float iri_where, iri_gate, rim;
    float a_amt;
    float3 acol;
    float g_int, g_amt, g_mix, g_keep;
    float3 gcol, g_rgb;
};

// N: shading normal (flipped toward the viewer on back faces); Ngeo: the mesh normal (no normal map)
// V: toward the camera; Nview: N in camera space (x right, y up)
// P: aurora coordinate (Blender object space); PW: Blender world position; baseColor / shadeTex: linear
AuroraPrep AuroraPrepare(AuroraParams m, AuroraLevels lv, float3 N, float3 Ngeo, float3 V, float3 Nview,
                         float3 P, float3 PW, float3 baseColor, float3 shadeTex, float time)
{
    AuroraPrep r;
    r.N = N;
    r.V = V;
    r.occ = LatSmooth(1.0 - m.Occlusion, 0.05, 0.9);
    r.open_ = 1.0 - r.occ;
    float3 base = lerp(baseColor, m.BaseLiftColor, saturate(m.BaseLift));
    float baseLum = LatLum(base);
    base = lerp(float3(baseLum, baseLum, baseLum), base, saturate(m.BaseSaturation));
    r.base = base;
    float3 shadeSrc = lerp(base, shadeTex, saturate(m.UseShadeTexture));
    r.shade1 = shadeSrc * m.ShadeTint1;
    r.shade2 = r.shade1 * m.ShadeTint2;
    r.lit0 = base * m.LitTint;
    float nv = abs(dot(N, V));
    r.fres = saturate(1.0 - nv);
    r.thin = saturate(1.0 - m.Thickness);
    r.edge = LatSmooth(r.fres, 0.15, 0.85);

    // nacre
    float grain = LatNoise4(PW, 0.0, m.IriGrainScale, 2);
    float ph = r.fres * m.IriScale + baseLum * m.IriBasePhase + (grain - 0.5) * m.IriGrain;
    float tri = 1.0 - abs(frac(ph) * 2.0 - 1.0);
    float hue = frac(m.IriShift + tri * m.IriHueRange);
    r.iri = LatHsvToRgb(hue, m.IriSaturation, 1.0);
    float mean = dot(r.iri, float3(0.3333, 0.3333, 0.3333));
    r.iri_n = r.iri * (1.0 / max(mean, 0.05));
    r.iri_where = lerp(1.0, r.edge, saturate(m.IriEdgeBias));
    r.iri_gate = r.open_ * m.EffectMask * lv.Iridescence;

    // rim shape
    float rlo = 1.0 - m.RimWidth - m.RimSoft;
    float rhi = 1.0 - m.RimWidth + m.RimSoft;
    r.rim = LatSmooth(r.fres, rlo, rhi);

    // aurora
    float3 D = LatSafeNormalize(m.AuroraDirection);
    float s = dot(P, D);
    float phase = time * lv.AuroraSpeed * m.AuroraSpeed + m.AuroraPhase;
    float wob = LatNoise4(P, phase * 0.35, m.AuroraBandScale * 0.7, 1);
    float wobc = (wob - 0.5) * m.AuroraDistort;
    float uFlow = s * m.AuroraBandScale - phase + wobc;
    float3 side = LatSafeNormalize(cross(D, float3(0.35, 0.94, 0.12)));
    float cs = dot(P, side);
    float tsw = phase * LAT_TAU;
    float sw1 = sin(s * 2.0 - tsw * 0.35);
    float sw2 = sin(s * 4.5 + tsw * 0.2);
    float swn = LatNoise4(P * 0.6, phase * 0.5, 1.0, 1);
    float sway = sw1 * 0.6 + sw2 * 0.15 + (swn - 0.5);
    float anz = m.AuroraNoise;
    sway *= saturate(1.0 - anz * 0.7);
    float wn1 = LatNoise4(P * 1.3, phase * 0.3, 1.0, 3);
    float wn2 = LatNoise4(P * 3.1 + float3(7.3, 2.1, 4.7), phase * 0.45, 1.0, 2);
    float warp = (wn1 - 0.5) * 3.0 + (wn2 - 0.5) * 0.9;
    float uCurt = cs * (m.AuroraBandScale * 1.4) + sway * m.AuroraSway + warp * anz;
    float gn = LatNoise4(P * 0.9 + float3(3.7, 9.2, 1.4), phase * 0.22, 1.0, 2);
    float agate = lerp(1.0, 0.4 + LatSmooth(gn, 0.3, 0.7) * 1.3, saturate(anz));
    float u = lerp(uFlow, uCurt, saturate(m.AuroraCurtain));
    float wave = 0.5 + 0.5 * sin(u * LAT_TAU);
    float bandv = pow(max(wave, 0.0), max(m.AuroraSharpness, 0.05));
    float3 across = P - D * (s * 0.94);
    float stn = LatNoise4(across, phase * lerp(0.6, 0.08, saturate(m.AuroraCurtain)), m.AuroraStreakScale, 2);
    float streak = lerp(1.0, LatSmooth(stn, 0.3, 0.75), saturate(m.AuroraStreak));
    float aEdge = 1.0 + r.edge * m.AuroraEdgeBoost;
    float aInt = bandv * streak * aEdge * agate;
    r.a_amt = aInt * m.AuroraStrength * m.EffectMask * lv.Aurora;
    float hidx = s * m.AuroraHueSpread + wob * 0.6 + m.AuroraHueShift;
    hidx = frac(hidx + phase * 0.12);
    r.acol = LatAuroraRamp(hidx) * m.AuroraTint;

    // glint: a light on the outline of the locks (and optionally a band that slides with the view)
    float gy = abs(Nview.y - m.GlintHeight);
    float gband = 1.0 - LatSmooth(gy, 0.0, max(m.GlintWidth, 0.001));
    float gstn = LatNoise4(across, 0.0, m.GlintStreakScale, 2);
    float gstreak = lerp(1.0, LatSmooth(gstn, 0.5, 0.68), saturate(m.GlintStreak));
    float gclock = time * lv.GlintSpeed;
    float gsoft = max(m.GlintSoftness, 0.0);
    float gpn = LatNoise4(P, gclock * m.GlintFlow, m.GlintPatchScale, 1);
    float gth = 0.75 - m.GlintCoverage * 0.5;
    float gcw = 0.08 + gsoft * 0.22;
    float gcov = LatSmooth(gpn, gth - gcw, gth + gcw);
    float gnv = abs(dot(LatSafeNormalize(Ngeo), V));
    float gfres = saturate(1.0 - gnv);
    float gelo = 1.0 - m.GlintEdgeWidth;
    float gelo2 = gelo - gsoft * 0.25;
    float gehi = gelo + (0.35 + gsoft * 0.25);
    float gedge = pow(max(LatSmooth(gfres, gelo2, gehi), 0.0), 1.0 + gsoft) * m.GlintEdge;
    r.g_int = (gband * m.GlintBand + gedge) * gstreak * gcov;
    r.g_amt = r.g_int * m.GlintStrength * (m.EffectMask * r.open_) * lv.Glint;
    float ghi = m.GlintHueShift + (Nview.x * 0.5) * m.GlintHueSpread;
    float ghn = LatNoise4(P, gclock * 0.25, 2.5, 1);
    ghi += (ghn - 0.5) * m.GlintHueVary;
    ghi += lv.GlintHue + gclock * m.GlintHueSpeed;
    ghi = frac(ghi + r.fres * 0.15 + 2.0);
    float gwhite = saturate(1.0 - (1.0 - m.GlintWhite) * lv.GlintColor);
    float gcore = saturate(saturate(r.g_int) * gwhite);
    r.gcol = lerp(LatSaturate(LatGlintRamp(ghi), 1.25), float3(1, 1, 1), gcore);
    float gHard = saturate(r.g_amt);
    float gSat = 1.0 - exp(r.g_amt * -1.1);
    r.g_mix = lerp(gHard, gSat, saturate(min(gsoft, 1.0)));
    r.g_keep = 1.0 - r.g_mix;
    r.g_rgb = r.gcol * (r.g_amt * (0.3 + m.GlintGlow));
    return r;
}

float3 AuroraAddGlint(AuroraPrep r, float3 col)
{
    return lerp(col, r.gcol, saturate(r.g_mix)) + r.g_rgb;
}

struct AuroraSurface { float3 cv; float t1; float rimk; float spk; };

// One light (hasLight = 1) or no light at all (hasLight = 0). Ls0 = N.L after cast shadows.
AuroraSurface AuroraSurfaceTerm(AuroraParams m, AuroraPrep r, bool hasLight, float Ls0, float3 L, float3 kcol)
{
    AuroraSurface o;
    float3 lit = hasLight ? r.lit0 * kcol : r.lit0;
    float t1 = 0.0, t2 = 0.0;
    float3 c = r.shade2;
    if (hasLight)
    {
        float Ls = Ls0 - r.occ * m.OcclusionShift;
        t1 = LatSmooth(Ls, m.ShadeShift1 - m.ShadeSoft1, m.ShadeShift1 + m.ShadeSoft1);
        t2 = LatSmooth(Ls, m.ShadeShift2 - m.ShadeSoft2, m.ShadeShift2 + m.ShadeSoft2);
        c = lerp(r.shade2, r.shade1, saturate(t2));
        c = lerp(c, lit, saturate(t1));
        float s1 = m.ShadeShift1;
        float band = LatSmooth(Ls, s1 - m.TerminatorWidth, s1) * (1.0 - LatSmooth(Ls, s1, s1 + m.TerminatorWidth));
        c = lerp(c, c * m.TerminatorColor, saturate(band * m.TerminatorStrength));
    }
    c = lerp(c, c * m.ShadeTint2, saturate(r.occ * m.OcclusionDarken));

    // translucency: the unlit side of a thin membrane glows
    float vl = hasLight ? max(dot(r.V, -L), 0.0) : 0.0;
    float back = 1.0 - t1;
    float trn = saturate(back * (0.45 + vl * 0.55) * r.thin * m.TransmitStrength);
    c = lerp(c, lit * m.TransmitColor, trn);

    // nacre, weaker in the shade
    float iriLit = lerp(m.IriShadeKeep, 1.0, saturate(t1));
    float iriMask = r.iri_where * iriLit * r.iri_gate;
    c = lerp(c, c * r.iri_n, saturate(iriMask * m.IriStrength));
    float iriAdd = iriLit * r.iri_gate * (r.edge * m.IriAdd);
    c = c + saturate(iriAdd) * r.iri;

    float rbias = lerp(1.0, t1, saturate(m.RimLitBias));
    o.rimk = r.rim * rbias * m.RimStrength * r.open_;
    c = c + saturate(o.rimk) * m.RimColor;
    o.spk = 0.0;
    if (hasLight)
    {
        float3 H = LatSafeNormalize(L + r.V);
        float nh = max(dot(r.N, H), 0.0);
        float sp = LatSmooth(nh, m.SpecSize - m.SpecSoft, m.SpecSize + m.SpecSoft);
        o.spk = sp * t1 * m.SpecStrength * r.open_;
        c = c + saturate(o.spk) * m.SpecColor;
    }

    // aurora: pull towards the aurora colour, then add a little light
    c = lerp(c, r.acol, saturate(saturate(r.a_amt)));
    c = c + saturate(r.a_amt * 0.35) * r.acol;
    c = lerp(c, r.base, saturate(m.Unlit));

    // highlight knee
    float mx = max(c.r, max(c.g, c.b));
    float k = m.HighlightKnee;
    float over = max(mx - k, 0.0);
    float rng = max(1.0 - k, 0.001);
    float y = min(mx, k) + rng * (1.0 - exp((over / rng) * -1.0));
    o.cv = c * (y / max(mx, 0.0001));
    o.t1 = t1;
    return o;
}

float AuroraOpacity(AuroraParams m, AuroraPrep r, AuroraSurface amb, float alphaIn)
{
    float faceOp = lerp(m.Opacity, 1.0, saturate(m.Thickness));
    float edgeOp = max(faceOp, m.EdgeOpacity);
    float op = lerp(faceOp, edgeOp, saturate(r.fres * r.fres));
    op = op + r.a_amt * m.AuroraAlpha * (1.0 - op);
    float glint = amb.rimk + amb.spk;
    op = op + glint * (1.0 - op);
    float fill = saturate(r.a_amt * m.AuroraAlpha) * LatSmooth(alphaIn, 0.02, 0.2);
    float imgA = alphaIn + (1.0 - alphaIn) * fill;
    return saturate(op * imgA);
}

// weight of one light as in Blender's node version: a sun of strength 1 gives 1, clamped to 0..1
// lightColor = colour x intensity (URP); returns the weight and writes the colour without intensity
float AuroraLightWeight(float3 lightColor, float distanceAtten, out float3 kcol)
{
    float k = max(lightColor.r, max(lightColor.g, lightColor.b));
    kcol = k > 1e-5 ? lightColor / k : float3(1, 1, 1);
    return clamp(k * distanceAtten, 0.0, 1.0);
}

// Ls0 of Blender: the cast shadow only darkens where Receive Shadow (or the Shadows level) asks for it
float AuroraShadowedNL(float NL, float shadowAtten, float receive)
{
    return lerp(NL, min(NL, shadowAtten * 2.0 - 1.0), saturate(receive));
}

#endif // LIDA_AURORA_TOON_CORE_INCLUDED
