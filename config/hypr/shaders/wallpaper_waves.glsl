#version 320 es
precision highp float;
// Papel de parede animado: as ondas do wallpaper ondulam devagar
// e um brilho percorre as linhas mais claras.

in vec2 v_texcoord;
out vec4 fragColor;
uniform sampler2D tex;
uniform float time;

void main() {
    vec2 uv = v_texcoord;
    float t = time;

    // ondulação vertical lenta (as faixas "respiram" e fluem)
    float dy = 0.010 * sin(uv.x * 5.5 + t * 0.45)
             + 0.005 * sin(uv.x * 12.0 - t * 0.70 + uv.y * 3.0);
    float dx = 0.004 * sin(uv.y * 7.0 + t * 0.30);
    vec2 p = clamp(uv + vec2(dx, dy), 0.001, 0.999);
    vec4 c = texture(tex, p);

    // brilho que corre ao longo das linhas claras
    float lum = dot(c.rgb, vec3(0.299, 0.587, 0.114));
    float glint = smoothstep(0.30, 0.85, lum)
                * pow(0.5 + 0.5 * sin(uv.x * 9.0 - t * 1.2 + uv.y * 5.0), 6.0);
    c.rgb += glint * 0.22 * vec3(0.85, 0.75, 1.0);

    // pulso suave geral
    c.rgb *= 0.96 + 0.04 * sin(t * 0.5);

    fragColor = vec4(min(c.rgb, vec3(1.0)), c.a);
}
