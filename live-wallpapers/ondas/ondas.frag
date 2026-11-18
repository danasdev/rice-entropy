// Ondas: superfície d'água com ondulações que seguem o mouse
float hash(vec2 p){ return fract(sin(dot(p, vec2(41.3, 289.1))) * 15731.743); }
float wave(vec2 p, float t){
    float h = 0.0;
    h += sin(p.x*3.0 + t*0.9 + sin(p.y*1.7 + t*0.4)) * 0.5;
    h += sin(p.x*5.5 - p.y*4.0 + t*1.3) * 0.25;
    h += sin(length(p - vec2(0.6,0.2))*9.0 - t*1.7) * 0.18;
    return h;
}
void mainImage(out vec4 o, in vec2 fc){
    vec2 res = iResolution.xy;
    vec2 uv = fc / res;
    vec2 p = (uv - 0.5) * vec2(res.x/res.y, 1.0) + iParallax*vec2(-0.04,0.03);
    float t = iTime;
    vec2 m = (iMouse.xy / res - 0.5) * vec2(res.x/res.y, 1.0);
    float dm = length(p - m);
    float ripple = sin(dm*40.0 - t*5.0) * exp(-dm*4.5) * 0.35;      // anéis ao redor do cursor
    float h = wave(p, t) + ripple;
    float e = 0.01;
    vec2 n = vec2(wave(p+vec2(e,0),t) - wave(p-vec2(e,0),t), wave(p+vec2(0,e),t) - wave(p-vec2(0,e),t)) / (2.0*e);
    n += vec2(cos(dm*40.0 - t*5.0)) * exp(-dm*4.5) * 0.2 * normalize(p - m + 1e-4);
    vec3 deep = vec3(0.02, 0.10, 0.22), shallow = vec3(0.10, 0.45, 0.60);
    vec3 col = mix(deep, shallow, smoothstep(-0.6, 0.9, h + uv.y*0.7));
    float spec = pow(max(0.0, dot(normalize(vec3(-n*0.6, 1.0)), normalize(vec3(0.4, 0.5, 0.8)))), 48.0);
    col += spec * vec3(0.7, 0.9, 1.0) * 0.7;
    col *= smoothstep(1.3, 0.2, length(uv - 0.5)*1.4);
    o = vec4(col, 1.0);
}
