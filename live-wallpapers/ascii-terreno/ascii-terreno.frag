// ASCII 3D: mapa de altura com parallax occlusion; caracteres mais "cheios" = mais perto. O mouse muda o ponto de vista.
const float CELL_H = 18.0;                     // altura da célula em px (a 720p); largura = metade
const int STEPS = 28;
vec3 ramp(float t) {                            // cor por altura (azul fundo -> ciano -> branco quente)
    vec3 a = vec3(0.10, 0.20, 0.55), b = vec3(0.25, 0.85, 0.95), c = vec3(1.0, 0.85, 0.95);
    return t < 0.55 ? mix(a, b, t / 0.55) : mix(b, c, (t - 0.55) / 0.45);
}

float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float noise(vec2 p){ vec2 i = floor(p), f = fract(p); f = f*f*(3.0-2.0*f);
    return mix(mix(hash(i), hash(i+vec2(1,0)), f.x), mix(hash(i+vec2(0,1)), hash(i+vec2(1,1)), f.x), f.y); }
float hmap(vec2 uv) {                           // relevo procedural: cordilheiras que derivam devagar
    vec2 p = uv * vec2(3.2, 2.2) + vec2(iTime * 0.015, 0.0);
    float v = 0.0, a = 0.55;
    for (int i = 0; i < 4; i++) { v += a * noise(p); p = p * 2.03 + 11.7; a *= 0.48; }
    float ridge = 1.0 - abs(noise(p * 0.35 + 4.0) * 2.0 - 1.0);
    return clamp((v * 0.95 + ridge * 0.35 - 0.1 - 0.5) * 2.4 + 0.45, 0.0, 1.0);
}
void mainImage(out vec4 o, in vec2 fc) {
    float sc = iResolution.y / 720.0;
    vec2 cell = vec2(CELL_H * 0.5, CELL_H) * sc;
    vec2 cid = floor(fc / cell);
    vec2 loc = fract(fc / cell);
    vec2 uv = (cid + 0.5) * cell / iResolution.xy;
    // parallax occlusion: caminha pelo relevo na direção do olhar
    vec2 dir = vec2(iParallax.x, -iParallax.y) * 0.16;
    float depthStep = 1.0 / float(STEPS), d = 0.0, hit = 0.0;
    vec2 p = uv;
    float hprev = hmap(uv), dprev = 0.0;
    for (int i = 0; i < STEPS; i++) {
        d += depthStep;
        p = uv + dir * d;
        float h = hmap(p);
        if (h < 1.0 - d) { hprev = h; dprev = d; continue; }
        hit = h; break;
    }
    float h = hit > 0.0 ? hit : hmap(p);
    // iluminação: inclinação do relevo
    vec2 e = vec2(0.004, 0.0);
    vec2 g = vec2(hmap(p + e.xy) - hmap(p - e.xy), hmap(p + e.yx) - hmap(p - e.yx)) / (2.0 * e.x);
    float light = clamp(0.55 + dot(normalize(vec3(-g * 0.35, 1.0)), normalize(vec3(-0.4, 0.5, 0.75))) * 0.55, 0.0, 1.0);
    float b = smoothstep(0.12, 0.98, h * 0.9 + (light - 0.5) * 0.5 + 0.05);
    b = pow(b, 1.15);                                  // vales ficam vazios, cumes cheios
    b = b * (0.92 + 0.08 * sin(iTime * 0.7 + cid.x * 0.4 + cid.y * 0.2));      // cintilar leve
    float n = iAtlasRes.x / (iAtlasRes.y * 0.5);                          // nº de glifos na rampa
    float idx = floor(clamp(b, 0.0, 0.999) * n);
    vec2 auv = vec2((idx + loc.x) / n, 1.0 - loc.y);
    float gl = texture(iAtlas, auv).a;
    vec3 col = ramp(h) * (0.45 + 0.75 * light);
    vec3 bg = mix(vec3(0.012, 0.02, 0.05), vec3(0.03, 0.05, 0.11), fc.y / iResolution.y);
    vec3 outc = bg + col * gl * (0.35 + 0.85 * b) + col * 0.05 * b;
    outc *= smoothstep(1.4, 0.3, length(fc / iResolution.xy - 0.5) * 1.5);
    o = vec4(outc, 1.0);
}
