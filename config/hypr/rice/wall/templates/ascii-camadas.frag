// ASCII em camadas rígidas: cada camada (iChannel0 = mais ao fundo ... iChannel2 = mais à frente) é uma imagem RGBA
// convertida em ASCII com a grade presa à própria camada. O parallax só desloca as camadas entre si (nada se deforma dentro delas).
//  iP0.x = altura da célula (px a 720p)   iP0.y = força do parallax   iP0.w = quantidade de glifo (0..1)
//  iP1.xyz = profundidade de cada camada (0 longe, 1 perto)
vec2 coverUV(vec2 uv, vec3 texRes) {
    vec2 res = iResolution.xy;
    float k = max(res.x / texRes.x, res.y / texRes.y);
    vec2 shown = res / (texRes.xy * k);
    vec2 t = (uv - 0.5) * shown + 0.5;
    return vec2(t.x, 1.0 - t.y);
}
vec4 layerSample(int i, vec2 uv) {
    if (i == 0) return texture(iChannel0, coverUV(uv, iChannelRes0));
    if (i == 1) return texture(iChannel1, coverUV(uv, iChannelRes1));
    return texture(iChannel2, coverUV(uv, iChannelRes2));
}
void mainImage(out vec4 o, in vec2 fc) {
    float cellH = iP0.x > 0.5 ? iP0.x : 9.0;
    float str = iP0.y > 0.0 ? iP0.y : 0.05;
    float glyphAmt = iP0.w > 0.0 ? iP0.w : 0.85;
    float sc = iResolution.y / 720.0;
    float depths[3] = float[3](iP1.x, iP1.y, iP1.z);
    float n = iAtlasRes.x / (iAtlasRes.y * 0.5);
    vec3 acc = vec3(0.012, 0.012, 0.02);
    for (int i = 0; i < 3; i++) {
        vec3 rs = i == 0 ? iChannelRes0 : (i == 1 ? iChannelRes1 : iChannelRes2);
        if (rs.x < 2.0) continue;
        float d = depths[i];
        // desloca a camada inteira (em px) ao contrário do mouse; quanto mais perto, mais anda
        vec2 off = vec2(-iParallax.x, iParallax.y) * str * d * iResolution.x;
        float zoom = 1.0 + 2.2 * str * d;
        vec2 p = fc - off;                                            // coordenada no espaço da camada
        vec2 cell = vec2(cellH * 0.5, cellH) * sc * (1.0 + 0.5 * (1.0 - d));   // camadas distantes têm células maiores
        vec2 cid = floor(p / cell);
        vec2 loc = fract(p / cell);
        vec2 uv = (cid + 0.5) * cell / iResolution.xy;               // centro da célula, preso à camada
        uv = (uv - 0.5) / zoom + 0.5;
        vec4 s = layerSample(i, uv);
        if (s.a < 0.04) continue;
        float lum = dot(s.rgb, vec3(0.299, 0.587, 0.114));
        vec3 c = floor(s.rgb * 7.0 + 0.5) / 7.0;
        float idx = floor(clamp(lum * 1.15, 0.0, 0.999) * n);
        float gl = texture(iAtlas, vec2((idx + loc.x) / n, 1.0 - loc.y)).a;
        vec2 e = smoothstep(0.0, 0.10, loc) * smoothstep(1.0, 0.90, loc);
        vec3 col = c * 0.36 * e.x * e.y + c * 1.25 * gl * glyphAmt;
        acc = mix(acc, col, smoothstep(0.04, 0.5, s.a));
    }
    acc *= smoothstep(1.5, 0.35, length(fc / iResolution.xy - 0.5) * 1.5);
    o = vec4(acc, 1.0);
}
