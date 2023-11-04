#version 300 es
precision highp float;
uniform vec2 u_resolution;
uniform float osg_FrameTime;
uniform sampler2D p3d_Texture0;
in vec2 texcoord;
out vec4 fragColor;

const float PI = 3.14159;

vec3 glow(vec2 p, vec2 lpos) {
    vec2 q = p - lpos;
    float atten = 1. / dot(q, q);
    return vec3(1.) * atten;
}

float rand(vec2 co){
    return fract(sin(dot(co.xy ,vec2(12.9898, 78.233))) * 43758.5453);
}


vec3 lastExplosion(float time) {
    // vec3(time since last explosion,
    //      index of last explosion,
    //      time until next explosion)

    float t = mod(time, 10.);
    float interval = floor(time/10.);
    float t0max = 0., imax=-1.;
    float t0next = 10.;
    for(float i=0.; i<10.; i++) {
        float t0 = rand(vec2(interval, i)) * 10.;
        if(t > t0 && t0 > t0max)
        {
            t0max = t0;
            imax = i;
        }
        if(t < t0 && t0 < t0next)
        {
            t0next = t0;
        }
    }
    return vec3(t-t0max, 10.*interval+imax, t0next-t);
}


void main() {
    vec2 uv = (2. * gl_FragCoord.xy - u_resolution.xy) / u_resolution.y;
    vec3 col = texture(p3d_Texture0, texcoord).rgb;

    vec3 last_expl = lastExplosion(osg_FrameTime);
    float t = last_expl.x;
    float expl_num = last_expl.y;
    float t_fadeout = last_expl.z;

    vec3 base_col = vec3(0.5, 0.5, 0.5) + 0.4 * sin(vec3(1.) * expl_num + vec3(0., 2.1, -21));

    // number of particles
    float n_lights = 100.;
    for (float i=0.; i<n_lights; i++) {
        float f = i / n_lights;
        float r = sqrt(1.0 - f*f);
        float th = 2. * 0.618033 * PI * i;
        float hash = sin(expl_num+i*85412.243);
        float weight = (1.-0.2*hash);
        th += hash*3.*6.28/n_lights;

        vec2 lpos = vec2(cos(th), sin(th) + 1.) * (r * 0.7);            // the position and size of firework
        lpos.xy *= (1.-exp(-3.*t/weight)) * weight;                     // explosion, easing out
        lpos.y += t*0.3*weight - t*(1.-exp(-t*weight)) * 0.6 * weight;  // vertical free-fall motion
        float intensity = 2e-4;
        intensity *= exp(-2.*t);
        intensity *= (1.-0.5*hash);
        intensity *= (1.+10.0*exp(-20.0*t));
        intensity *= clamp(3.*t_fadeout, 0., 1.);
        col += glow(uv, lpos) * intensity * base_col;
    }

    col = max(col, 0.);
    col = (col*(2.51*col+0.03))/(col*(2.43*col+0.59)+0.14);
    col = sqrt(col);  // gamma correction
    fragColor = vec4(col, 1.);
}