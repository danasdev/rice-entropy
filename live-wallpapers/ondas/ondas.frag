// Ondas: água calma; o caminho do mouse deixa frentes de onda que se espalham (como arrastar o dedo na água)
float height(vec2 fc) {
    vec2 res = iResolution.xy;
    float h = 0.0;
    for (int i = 0; i < 32; i++) {
        vec4 d = iDrops[i];
        if (d.z > 5.5) continue;
        float r = distance(fc, d.xy) / res.y;           // distância em alturas de tela
        float front = 0.30 * d.z;                        // velocidade da onda
        float w = r - front;
        float env = exp(-w * w * 220.0) * exp(-d.z * 0.75) * d.w / (1.0 + r * 5.0);   // pacote de onda que perde força
        h += env * sin(w * 70.0);
    }
    return h;
}
void mainImage(out vec4 o, in vec2 fc) {
    vec2 res = iResolution.xy;
    vec2 uv = fc / res;
    vec2 pf = fc + iParallax * vec2(-14.0, 10.0);        // parallax leve do fundo
    float e = 1.5;
    float h = height(fc);
    vec2 n = vec2(height(fc + vec2(e, 0.0)) - height(fc - vec2(e, 0.0)),
                  height(fc + vec2(0.0, e)) - height(fc - vec2(0.0, e))) / (2.0 * e) * res.y * 0.05;
    // fundo: gradiente profundo; as ondas "refratam" o fundo e acendem os cumes
    vec2 q = (pf + n * 60.0) / res;
    vec3 deep = vec3(0.01, 0.06, 0.16), mid = vec3(0.04, 0.28, 0.45), top = vec3(0.12, 0.55, 0.70);
    vec3 col = mix(deep, mid, smoothstep(0.0, 1.0, q.y * 0.9 + 0.1));
    col = mix(col, top, smoothstep(0.55, 1.2, q.y + q.x * 0.15) * 0.45);
    vec3 N = normalize(vec3(-n * 1.2, 1.0));
    float spec = pow(max(dot(N, normalize(vec3(0.35, 0.45, 0.82))), 0.0), 60.0);
    float fres = pow(1.0 - N.z, 2.0);
    col += spec * vec3(0.75, 0.92, 1.0) * 0.9 + fres * vec3(0.10, 0.35, 0.55) * 1.4;
    col += h * vec3(0.10, 0.22, 0.30) * 1.2;
    col *= smoothstep(1.35, 0.25, length(uv - 0.5) * 1.35);
    o = vec4(col, 1.0);
}
