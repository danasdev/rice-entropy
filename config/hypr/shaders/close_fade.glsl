#version 320 es
precision highp float;
// @duration 0.5
// Aspirador: a janela afunila e é sugada para o ponto inferior central.

in vec2 v_texcoord;
out vec4 fragColor;
uniform sampler2D tex;
uniform float progress;

void main() {
    float p = pow(clamp(progress, 0.0, 1.0), 2.0);          // acelera, como sendo sugado
    vec2 uv = v_texcoord;
    float k = p * 0.97;                                       // a janela colapsa para baixo
    if (uv.y < k) { fragColor = vec4(0.0); return; }
    float t = (uv.y - k) / (1.0 - k);                         // linha equivalente na janela original
    float pinch = clamp(p * 1.4 + t * 0.35 - 0.15, 0.0, 1.0); // afunila mais perto do ponto
    float w = 1.0 - 0.97 * pinch * pinch;
    float sx = (uv.x - 0.5) / w + 0.5;
    if (sx < 0.0 || sx > 1.0) { fragColor = vec4(0.0); return; }
    float a = 1.0 - smoothstep(0.0, 0.6, progress);
    fragColor = texture(tex, vec2(sx, t)) * a;
}
