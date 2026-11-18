// ASCII 3D: mapa de altura com parallax occlusion; caracteres mais "cheios" = mais perto. O mouse muda o ponto de vista.
const float CELL_H = 18.0;                     // altura da célula em px (a 720p); largura = metade
const int STEPS = 28;
vec3 ramp(float t) {                            // cor por altura (azul fundo -> ciano -> branco quente)
    vec3 a = vec3(0.10, 0.20, 0.55), b = vec3(0.25, 0.85, 0.95), c = vec3(1.0, 0.85, 0.95);
    return t < 0.55 ? mix(a, b, t / 0.55) : mix(b, c, (t - 0.55) / 0.45);
}

vec2 coverUV(vec2 uv) {                         // uv da tela (0..1) -> uv da imagem (modo cover, y de cima)
    vec2 res = iResolution.xy, tex = iChannelRes0.xy;
    float k = max(res.x / tex.x, res.y / tex.y);
    vec2 shown = res / (tex * k);
    vec2 t = (uv - 0.5) * shown + 0.5;
    return vec2(t.x, 1.0 - t.y);
}
float hmap(vec2 uv) {
    vec3 c = texture(iChannel0, coverUV(clamp(uv, 0.0, 1.0))).rgb;
    float l = dot(c, vec3(0.299, 0.587, 0.114));
    return clamp(pow(l, 0.9) * 1.1, 0.0, 1.0);
}
void mainImage(out vec4 o, in vec2 fc) {
    float sc = iResolution.y / 720.0;
    vec2 cell = vec2(CELL_H * 0.5, CELL_H) * sc;
    vec2 cid = floor(fc / cell);
    vec2 loc = fract(fc / cell);
    vec2 uv = (cid + 0.5) * cell / iResolution.xy;
    vec2 dir = vec2(iParallax.x, -iParallax.y) * 0.14;
    float depthStep = 1.0 / float(STEPS), d = 0.0, hit = 0.0;
    vec2 p = uv;
    for (int i = 0; i < STEPS; i++) {
        d += depthStep;
        p = uv + dir * d;
        float h = hmap(p);
        if (h < 1.0 - d) continue;
        hit = h; break;
    }
    float h = hit > 0.0 ? hit : hmap(p);
    vec3 src = texture(iChannel0, coverUV(clamp(p, 0.0, 1.0))).rgb;
    float b = pow(smoothstep(0.08, 0.95, h), 1.25);
    float n = iChannelRes1.x / (iChannelRes1.y * 0.5);
    float idx = floor(b * n);
    vec2 auv = vec2((idx + loc.x) / n, 1.0 - loc.y);
    float gl = texture(iChannel1, auv).a;
    vec3 tint = mix(ramp(h), src * 1.4, 0.55);     // mistura a paleta com as cores da foto
    vec3 bg = vec3(0.01, 0.015, 0.03);
    vec3 outc = bg + tint * gl * (0.4 + 0.8 * b) + src * 0.06;
    outc *= smoothstep(1.4, 0.3, length(fc / iResolution.xy - 0.5) * 1.5);
    o = vec4(outc, 1.0);
}
