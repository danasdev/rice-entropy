// ASCII mosaico com profundidade: células coloridas com o glifo por brilho; o parallax usa um mapa de profundidade.
//  iChannel0 = imagem   iChannel1 = profundidade (claro = perto; se ausente, usa o brilho)   iAtlas = glifos
//  iP0.x = altura da célula (px a 720p, padrão 9)   iP0.y = força do parallax (padrão 0.16)
//  iP0.z = estilo: 0 cores da imagem, 1 duotone ciano/magenta   iP0.w = quantidade de glifo (0..1, padrão 0.8)
vec2 coverUV(vec2 uv) {
    vec2 res = iResolution.xy, tex = iChannelRes0.xy;
    float k = max(res.x / tex.x, res.y / tex.y);
    vec2 shown = res / (tex * k);
    vec2 t = (uv - 0.5) * shown + 0.5;
    return vec2(t.x, 1.0 - t.y);
}
vec3 colorAt(vec2 uv) { return texture(iChannel0, coverUV(clamp(uv, 0.0, 1.0))).rgb; }
float depthAt(vec2 uv) {
    vec2 c = coverUV(clamp(uv, 0.0, 1.0));
    if (iChannelRes1.x > 2.0) return texture(iChannel1, c).r;
    vec3 col = texture(iChannel0, c).rgb;
    return clamp(dot(col, vec3(0.299, 0.587, 0.114)) * 1.2, 0.0, 1.0);
}
void mainImage(out vec4 o, in vec2 fc) {
    float cellH = iP0.x > 0.5 ? iP0.x : 9.0;
    float par = iP0.y > 0.0 ? iP0.y : 0.16;
    float glyphAmt = iP0.w > 0.0 ? iP0.w : 0.8;
    float sc = iResolution.y / 720.0;
    vec2 cell = vec2(cellH * 0.5, cellH) * sc;
    vec2 cid = floor(fc / cell);
    vec2 loc = fract(fc / cell);
    vec2 uv = (cid + 0.5) * cell / iResolution.xy;
    // parallax occlusion: o fundo (longe) anda menos que o sujeito (perto)
    vec2 dir = vec2(iParallax.x, -iParallax.y) * par;
    // parallax iterativo: cada ponto desliza conforme a profundidade (perto anda mais, longe anda menos)
    vec2 p = uv;
    for (int i = 0; i < 5; i++) p = uv + dir * (depthAt(p) - 0.35);
    vec3 c = colorAt(p);
    float lum = dot(c, vec3(0.299, 0.587, 0.114));
    float near = depthAt(p);
    if (iP0.z > 0.5) {                                         // duotone: sombras ciano, luzes magenta
        c = mix(vec3(0.0, 0.85, 0.80), vec3(1.0, 0.1, 0.85), smoothstep(0.25, 0.7, lum)) * smoothstep(0.04, 0.35, lum);
    } else {
        c = floor(c * 7.0 + 0.5) / 7.0;                        // posteriza levemente (visual de mosaico)
    }
    float n = iAtlasRes.x / (iAtlasRes.y * 0.5);
    float idx = floor(clamp(lum * 1.15, 0.0, 0.999) * n);
    float gl = texture(iAtlas, vec2((idx + loc.x) / n, 1.0 - loc.y)).a;
    vec2 e = smoothstep(0.0, 0.10, loc) * smoothstep(1.0, 0.90, loc);       // frestas entre as células
    float tile = e.x * e.y;
    vec3 col = c * (0.38 + 0.25 * near) * tile + c * 1.25 * gl * glyphAmt;
    col *= smoothstep(1.5, 0.35, length(fc / iResolution.xy - 0.5) * 1.5);
    o = vec4(col * (lum < 0.03 ? 0.0 : 1.0), 1.0);
}
