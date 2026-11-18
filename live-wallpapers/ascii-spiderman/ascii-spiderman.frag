// ASCII 3D: herói à frente (profundidade alta) e teias ao fundo; o parallax separa os planos. Altura = canal alfa da imagem.
const float CELL_H = 14.0;
const int STEPS = 32;
vec2 coverUV(vec2 uv) {
    vec2 res = iResolution.xy, tex = iChannelRes0.xy;
    float k = max(res.x / tex.x, res.y / tex.y);
    vec2 shown = res / (tex * k);
    vec2 t = (uv - 0.5) * shown + 0.5;
    return vec2(t.x, 1.0 - t.y);
}
vec4 src(vec2 uv) { return texture(iChannel0, coverUV(clamp(uv, 0.0, 1.0))); }
void mainImage(out vec4 o, in vec2 fc) {
    float sc = iResolution.y / 720.0;
    vec2 cell = vec2(CELL_H * 0.5, CELL_H) * sc;
    vec2 cid = floor(fc / cell);
    vec2 loc = fract(fc / cell);
    vec2 uv = (cid + 0.5) * cell / iResolution.xy;
    vec2 dir = vec2(iParallax.x, -iParallax.y) * 0.20;
    float depthStep = 1.0 / float(STEPS), d = 0.0, hit = 0.0;
    vec2 p = uv;
    for (int i = 0; i < STEPS; i++) {
        d += depthStep;
        p = uv + dir * d;
        float h = src(p).a;
        if (h < 1.0 - d) continue;
        hit = h; break;
    }
    vec4 s = hit > 0.0 ? src(p) : src(uv + dir);
    float h = s.a;
    float lum = dot(s.rgb, vec3(0.299, 0.587, 0.114));
    float b = clamp(h * 0.55 + lum * 1.1, 0.0, 0.999);
    if (h < 0.02 && lum < 0.05) b = 0.0;
    float n = iAtlasRes.x / (iAtlasRes.y * 0.5);
    float idx = floor(b * n);
    vec2 auv = vec2((idx + loc.x) / n, 1.0 - loc.y);
    float gl = texture(iAtlas, auv).a;
    vec3 tint = mix(vec3(0.55, 0.65, 0.95), s.rgb * 1.5, 0.75);        // cores do traje (vermelho / azul)
    tint += vec3(0.25) * smoothstep(0.85, 1.0, lum);                      // olhos e fios brilham
    vec3 bg = vec3(0.012, 0.016, 0.04);
    float front = smoothstep(0.6, 1.0, h);
    vec3 outc = bg + tint * gl * (0.45 + 0.9 * b + 0.3 * front) + s.rgb * 0.05 * front;
    outc *= smoothstep(1.4, 0.3, length(fc / iResolution.xy - 0.5) * 1.5);
    o = vec4(outc, 1.0);
}
