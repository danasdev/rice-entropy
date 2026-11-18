// Aurora: faixas de luz que fluem e se inclinam com o mouse (parallax)
float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float noise(vec2 p){
    vec2 i = floor(p), f = fract(p); f = f*f*(3.0-2.0*f);
    return mix(mix(hash(i), hash(i+vec2(1,0)), f.x), mix(hash(i+vec2(0,1)), hash(i+vec2(1,1)), f.x), f.y);
}
float fbm(vec2 p){ float v = 0.0, a = 0.5; for(int i=0;i<5;i++){ v += a*noise(p); p = p*2.02 + 7.3; a *= 0.5; } return v; }
void mainImage(out vec4 o, in vec2 fc){
    vec2 uv = fc / iResolution.xy;
    vec2 p = (uv - 0.5) * vec2(iResolution.x/iResolution.y, 1.0);
    vec3 col = mix(vec3(0.01,0.02,0.06), vec3(0.02,0.05,0.12), uv.y);
    for(int i=0;i<4;i++){
        float d = 1.0 + float(i)*0.45;                      // profundidade da camada
        vec2 q = p + iParallax*vec2(-0.05,0.03)*d;           // parallax por camada
        float t = iTime*0.05*(1.0+float(i)*0.3);
        float w = fbm(vec2(q.x*1.6 + t, float(i)*3.1 + t*0.6));
        float band = smoothstep(0.30, 0.0, abs(q.y - 0.12 + (w-0.5)*0.55 - float(i)*0.08));
        float rays = fbm(vec2(q.x*9.0 + t*2.0, q.y*0.8));
        vec3 c = mix(vec3(0.1,0.9,0.6), vec3(0.5,0.3,1.0), fract(float(i)*0.37 + w));
        col += c * band * (0.25 + 0.55*rays) * (0.9 - float(i)*0.12);
    }
    float st = step(0.9985, hash(floor(fc*0.5)));            // estrelas
    col += st * smoothstep(0.35, 0.8, uv.y) * 0.8;
    float vig = smoothstep(1.25, 0.25, length(p));
    o = vec4(col * vig, 1.0);
}
