#version 320 es
precision highp float;
// @duration 0.45
// Surgindo: a janela sai do ponto inferior central e se expande até o tamanho normal.

in vec2 v_texcoord;
out vec4 fragColor;
uniform sampler2D tex;
uniform float progress;

void main() {
    float q = 1.0 - clamp(progress, 0.0, 1.0);
    float p = pow(q, 2.2);                                    // desacelera ao chegar
    vec2 uv = v_texcoord;
    float k = p * 0.97;
    if (uv.y < k) { fragColor = vec4(0.0); return; }
    float t = (uv.y - k) / (1.0 - k);
    float pinch = clamp(p * 1.4 + t * 0.35 - 0.15, 0.0, 1.0);
    float w = 1.0 - 0.97 * pinch * pinch;
    float sx = (uv.x - 0.5) / w + 0.5;
    if (sx < 0.0 || sx > 1.0) { fragColor = vec4(0.0); return; }
    float a = smoothstep(0.0, 0.18, progress);
    fragColor = texture(tex, vec2(sx, t)) * a;
}
