// SPDX-License-Identifier: LicenseRef-Lida-Attribution-1.1
// Copyright (c) 2026 Lida
// ============================================================================
// LidaAuroraToonNoise.hlsl - the 4D fBm noise of Blender's Noise Texture node
// (Perlin noise with a Jenkins lookup3 hash, detail octaves, roughness 0.5,
// lacunarity 2, normalized), written again in HLSL so the aurora bands come out
// in the same places as in Blender. Checked against Blender 5.3 Geometry Nodes on
// 4000 random points: largest difference 1.5e-5 (tools/check_noise_port.py).
// ============================================================================
#ifndef LIDA_AURORA_TOON_NOISE_INCLUDED
#define LIDA_AURORA_TOON_NOISE_INCLUDED

#define LAT_ROT(x, k) (((x) << (k)) | ((x) >> (32u - (k))))

uint LatHash4(uint kx, uint ky, uint kz, uint kw)
{
    uint a, b, c;
    a = b = c = 0xdeadbeefu + (4u << 2u) + 13u;
    a += kx; b += ky; c += kz;
    // mix
    a -= c; a ^= LAT_ROT(c, 4u);  c += b;
    b -= a; b ^= LAT_ROT(a, 6u);  a += c;
    c -= b; c ^= LAT_ROT(b, 8u);  b += a;
    a -= c; a ^= LAT_ROT(c, 16u); c += b;
    b -= a; b ^= LAT_ROT(a, 19u); a += c;
    c -= b; c ^= LAT_ROT(b, 4u);  b += a;
    a += kw;
    // final
    c ^= b; c -= LAT_ROT(b, 14u);
    a ^= c; a -= LAT_ROT(c, 11u);
    b ^= a; b -= LAT_ROT(a, 25u);
    c ^= b; c -= LAT_ROT(b, 16u);
    a ^= c; a -= LAT_ROT(c, 4u);
    b ^= a; b -= LAT_ROT(a, 14u);
    c ^= b; c -= LAT_ROT(b, 24u);
    return c;
}

float LatGrad4(uint h, float x, float y, float z, float w)
{
    h &= 31u;
    float u = h < 24u ? x : y;
    float v = h < 16u ? y : z;
    float s = h < 8u ? z : w;
    return ((h & 1u) ? -u : u) + ((h & 2u) ? -v : v) + ((h & 4u) ? -s : s);
}

float LatFade(float t) { return t * t * t * (t * (t * 6.0 - 15.0) + 10.0); }

float LatPerlin4(float4 p)
{
    float4 fl = floor(p);
    int4 I = (int4)fl;
    float4 f = p - fl;
    uint X = (uint)I.x, Y = (uint)I.y, Z = (uint)I.z, W = (uint)I.w;
    float v[16];
    [unroll] for (uint dw = 0; dw < 2; dw++)
    [unroll] for (uint dz = 0; dz < 2; dz++)
    [unroll] for (uint dy = 0; dy < 2; dy++)
    [unroll] for (uint dx = 0; dx < 2; dx++)
    {
        v[dx + 2 * dy + 4 * dz + 8 * dw] = LatGrad4(LatHash4(X + dx, Y + dy, Z + dz, W + dw),
                                                   f.x - dx, f.y - dy, f.z - dz, f.w - dw);
    }
    float u = LatFade(f.x), vv = LatFade(f.y), t = LatFade(f.z), s = LatFade(f.w);
    float b0 = lerp(lerp(v[0], v[1], u), lerp(v[2], v[3], u), vv);
    float b1 = lerp(lerp(v[4], v[5], u), lerp(v[6], v[7], u), vv);
    float b2 = lerp(lerp(v[8], v[9], u), lerp(v[10], v[11], u), vv);
    float b3 = lerp(lerp(v[12], v[13], u), lerp(v[14], v[15], u), vv);
    return lerp(lerp(b0, b1, t), lerp(b2, b3, t), s);
}

// Noise Texture (4D, fBm, normalized, roughness 0.5, lacunarity 2): value in about 0.2 .. 0.8
// detail is a whole number here (1, 2 or 3 in this shader)
float LatNoise4(float3 co, float w, float scale, int detail)
{
    float4 p = float4(co, w) * scale;
    float fscale = 1.0, amp = 1.0, maxamp = 0.0, sum = 0.0;
    [loop] for (int i = 0; i <= detail; i++)
    {
        sum += 0.8344 * LatPerlin4(fscale * p) * amp;
        maxamp += amp;
        amp *= 0.5;
        fscale *= 2.0;
    }
    return 0.5 * sum / maxamp + 0.5;
}

#endif // LIDA_AURORA_TOON_NOISE_INCLUDED
