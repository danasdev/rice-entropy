#version 320 es
precision highp float;
// Vidro: sem escurecer; borda luminosa, reflexo diagonal e neblina de vidro fosco.

in vec2 v_texcoord;
out vec4 fragColor;
uniform sampler2D tex;
uniform float time;
uniform float is_active;

void main() {
    vec4 c = texture(tex, v_texcoord);
    vec2 uv = v_texcoord;

    // borda: linha fina clara (mais forte em cima/esquerda, como luz vindo de cima)
    vec2 e = min(uv, 1.0 - uv);
    float edge = 1.0 - smoothstep(0.0, 0.004, min(e.x * 0.6, e.y));
    float rimLight = mix(0.35, 1.0, (1.0 - uv.y) * 0.6 + (1.0 - uv.x) * 0.4);
    float rim = edge * rimLight * mix(0.25, 0.5, is_active);

    // reflexo diagonal suave que desliza devagar
    float diag = uv.x * 0.8 + uv.y * 0.6;
    float band = smoothstep(0.12, 0.0, abs(fract(diag * 0.7 - time * 0.015) - 0.5) - 0.18);
    float sheen = band * 0.045 + (1.0 - uv.y) * 0.05;

    // neblina de vidro fosco: clareia o fundo, sem mexer no texto
    float haze = (1.0 - c.a) * 0.0 + 0.035;

    vec3 glow = vec3(0.92, 0.94, 1.0) * (rim + sheen + haze);
    c.rgb += glow * max(c.a, 0.35);
    c.a = max(c.a, (rim + sheen) * 0.9);
    fragColor = c;
}
