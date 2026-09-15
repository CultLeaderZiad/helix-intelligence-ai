import React, { useEffect, useRef } from 'react';
import './PixelBlast.css';

const VERTEX_SHADER = `
attribute vec2 a_position;
void main() {
  gl_Position = vec4(a_position, 0.0, 1.0);
}
`;

const FRAGMENT_SHADER = `
precision highp float;

uniform vec3  uColor;
uniform vec2  uResolution;
uniform float uTime;
uniform float uPixelSize;
uniform float uScale;
uniform float uDensity;
uniform float uPixelJitter;
uniform int   uEnableRipples;
uniform float uRippleSpeed;
uniform float uRippleThickness;
uniform float uRippleIntensity;
uniform float uEdgeFade;
uniform int   uShapeType;
uniform float uLiquidStrength;
uniform float uLiquidWobbleSpeed;

const int MAX_CLICKS = 8;
uniform vec2  uClickPos[MAX_CLICKS];
uniform float uClickTimes[MAX_CLICKS];

float Bayer2(vec2 a) {
  a = floor(a);
  return fract(a.x / 2.0 + a.y * a.y * 0.75);
}
#define Bayer4(a) (Bayer2(0.5 * (a)) * 0.25 + Bayer2(a))
#define Bayer8(a) (Bayer4(0.5 * (a)) * 0.25 + Bayer2(a))

#define FBM_OCTAVES 4
#define FBM_LACUNARITY 1.25
#define FBM_GAIN 1.0

float hash11(float n) {
  return fract(sin(n) * 43758.5453);
}

float vnoise(vec3 p) {
  vec3 ip = floor(p);
  vec3 fp = fract(p);
  float n000 = hash11(dot(ip + vec3(0.0, 0.0, 0.0), vec3(1.0, 57.0, 113.0)));
  float n100 = hash11(dot(ip + vec3(1.0, 0.0, 0.0), vec3(1.0, 57.0, 113.0)));
  float n010 = hash11(dot(ip + vec3(0.0, 1.0, 0.0), vec3(1.0, 57.0, 113.0)));
  float n110 = hash11(dot(ip + vec3(1.0, 1.0, 0.0), vec3(1.0, 57.0, 113.0)));
  float n001 = hash11(dot(ip + vec3(0.0, 0.0, 1.0), vec3(1.0, 57.0, 113.0)));
  float n101 = hash11(dot(ip + vec3(1.0, 0.0, 1.0), vec3(1.0, 57.0, 113.0)));
  float n011 = hash11(dot(ip + vec3(0.0, 1.0, 1.0), vec3(1.0, 57.0, 113.0)));
  float n111 = hash11(dot(ip + vec3(1.0, 1.0, 1.0), vec3(1.0, 57.0, 113.0)));
  vec3 w = fp * fp * fp * (fp * (fp * 6.0 - 15.0) + 10.0);
  float x00 = mix(n000, n100, w.x);
  float x10 = mix(n010, n110, w.x);
  float x01 = mix(n001, n101, w.x);
  float x11 = mix(n011, n111, w.x);
  float y0  = mix(x00, x10, w.y);
  float y1  = mix(x01, x11, w.y);
  return mix(y0, y1, w.z) * 2.0 - 1.0;
}

float fbm2(vec2 uv, float t) {
  vec3 p = vec3(uv * uScale, t);
  float amp = 0.5;
  float freq = 1.0;
  float sum = 0.0;
  float norm = 0.0;
  for (int i = 0; i < FBM_OCTAVES; ++i) {
    sum  += amp * (vnoise(p * freq) * 0.5 + 0.5);
    norm += amp;
    freq *= 1.8;
    amp  *= 0.5;
  }
  return sum / norm;
}

float maskCircle(vec2 p, float cov) {
  if (cov <= 0.02) return 0.0;
  float r = sqrt(cov) * 0.55;
  return step(length(p - 0.5), r);
}

float maskDiamond(vec2 p, float cov) {
  if (cov <= 0.02) return 0.0;
  float r = sqrt(cov) * 0.75;
  return step(abs(p.x - 0.5) + abs(p.y - 0.5), r);
}

void main() {
  float pixelSize = max(uPixelSize, 1.0);
  vec2 fragCoord = gl_FragCoord.xy;
  float aspectRatio = uResolution.x / max(uResolution.y, 1.0);

  vec2 pixelUV = fract(fragCoord / pixelSize);

  float cellPixelSize = 6.0 * pixelSize;
  vec2 cellId = floor(fragCoord / cellPixelSize);
  vec2 cellCoord = cellId * cellPixelSize;
  vec2 uv = ((cellCoord - uResolution * 0.5) / uResolution) * vec2(aspectRatio, 1.0);

  // Liquid wobble distortion
  if (uLiquidStrength > 0.0) {
    float wave = 0.5 + 0.5 * sin(uTime * uLiquidWobbleSpeed + (uv.x + uv.y) * 6.2831853);
    uv += vec2(sin(uTime * 1.5 + uv.y * 6.0), cos(uTime * 1.5 + uv.x * 6.0)) * (uLiquidStrength * wave * 0.04);
  }

  float noise = fbm2(uv, uTime * 0.06);
  float dist = length(uv);
  float blast = exp(-dist * 0.7) * 0.3;
  float feed = (noise * 0.55 + blast) * (uDensity * 0.7);

  if (uEnableRipples == 1) {
    for (int i = 0; i < MAX_CLICKS; ++i) {
      vec2 pos = uClickPos[i];
      if (pos.x < 0.0) continue;
      vec2 cuv = (((pos - cellPixelSize * 0.5) - uResolution * 0.5) / uResolution) * vec2(aspectRatio, 1.0);
      float t = max(uTime - uClickTimes[i], 0.0);
      float r = distance(uv, cuv);
      float waveR = uRippleSpeed * t;
      float ring  = exp(-pow((r - waveR) / max(uRippleThickness, 0.01), 2.0));
      float atten = exp(-1.0 * t) * exp(-6.0 * r);
      feed = max(feed, ring * atten * uRippleIntensity);
    }
  }

  float bayer = Bayer8(fragCoord / pixelSize);
  float bw = step(bayer, feed);

  float h = fract(sin(dot(floor(fragCoord / pixelSize), vec2(127.1, 311.7))) * 43758.5453);
  float jitterScale = clamp(1.0 + (h - 0.5) * uPixelJitter, 0.3, 1.7);
  float coverage = clamp(bw * jitterScale, 0.0, 1.0);

  float M = coverage;
  if (uShapeType == 1) {
    M = maskCircle(pixelUV, coverage);
  } else if (uShapeType == 3) {
    M = maskDiamond(pixelUV, coverage);
  }

  if (uEdgeFade > 0.0) {
    vec2 norm = gl_FragCoord.xy / uResolution;
    float edge = min(min(norm.x, norm.y), min(1.0 - norm.x, 1.0 - norm.y));
    float fade = smoothstep(0.0, uEdgeFade, edge);
    M *= fade;
  }

  vec3 srgbColor = mix(
    uColor * 12.92,
    1.055 * pow(uColor, vec3(1.0 / 2.4)) - 0.055,
    step(0.0031308, uColor)
  );

  gl_FragColor = vec4(srgbColor, M);
}
`;

const parseHexColor = (hex) => {
  const clean = hex.replace('#', '');
  if (clean.length === 3) {
    return [
      parseInt(clean[0] + clean[0], 16) / 255,
      parseInt(clean[1] + clean[1], 16) / 255,
      parseInt(clean[2] + clean[2], 16) / 255
    ];
  }
  return [
    parseInt(clean.substring(0, 2), 16) / 255,
    parseInt(clean.substring(2, 4), 16) / 255,
    parseInt(clean.substring(4, 6), 16) / 255
  ];
};

const SHAPE_MAP = {
  square: 0,
  circle: 1,
  triangle: 2,
  diamond: 3
};

export const PixelBlast = ({
  variant = 'diamond',
  pixelSize = 2,
  color = '#29e23f',
  className = '',
  style = {},
  patternScale = 3,
  patternDensity = 1.2,
  liquid = true,
  liquidStrength = 0.12,
  liquidWobbleSpeed = 5,
  pixelSizeJitter = 1.55,
  enableRipples = true,
  rippleIntensityScale = 1.5,
  rippleThickness = 0.12,
  rippleSpeed = 0.4,
  autoPauseOffscreen = true,
  speed = 1.15,
  edgeFade = 0.09
}) => {
  const containerRef = useRef(null);
  const canvasRef = useRef(null);
  const isVisibleRef = useRef(true);

  useEffect(() => {
    const container = containerRef.current;
    const canvas = canvasRef.current;
    if (!container || !canvas) return;

    // Use WebGL context (WebGL2 or WebGL1 fallback)
    const gl = canvas.getContext('webgl2', { alpha: true, antialias: false, powerPreference: 'low-power', preserveDrawingBuffer: true }) ||
               canvas.getContext('webgl', { alpha: true, antialias: false, powerPreference: 'low-power', preserveDrawingBuffer: true });
    if (!gl) return;

    // Enable proper alpha blending for transparency
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);

    const compileShader = (type, source) => {
      const s = gl.createShader(type);
      gl.shaderSource(s, source);
      gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
        console.warn('Shader compile error:', gl.getShaderInfoLog(s));
        gl.deleteShader(s);
        return null;
      }
      return s;
    };

    const vs = compileShader(gl.VERTEX_SHADER, VERTEX_SHADER);
    const fs = compileShader(gl.FRAGMENT_SHADER, FRAGMENT_SHADER);
    if (!vs || !fs) return;

    const program = gl.createProgram();
    gl.attachShader(program, vs);
    gl.attachShader(program, fs);
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      console.warn('Program link error:', gl.getProgramInfoLog(program));
      return;
    }

    gl.useProgram(program);

    // Fullscreen quad buffer
    const positionBuffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
    gl.bufferData(
      gl.ARRAY_BUFFER,
      new Float32Array([
        -1, -1,
         1, -1,
        -1,  1,
        -1,  1,
         1, -1,
         1,  1
      ]),
      gl.STATIC_DRAW
    );

    const posLoc = gl.getAttribLocation(program, 'a_position');
    gl.enableVertexAttribArray(posLoc);
    gl.vertexAttribPointer(posLoc, 2, gl.FLOAT, false, 0, 0);

    // Uniform locations
    const uLocs = {
      color: gl.getUniformLocation(program, 'uColor'),
      resolution: gl.getUniformLocation(program, 'uResolution'),
      time: gl.getUniformLocation(program, 'uTime'),
      pixelSize: gl.getUniformLocation(program, 'uPixelSize'),
      scale: gl.getUniformLocation(program, 'uScale'),
      density: gl.getUniformLocation(program, 'uDensity'),
      pixelJitter: gl.getUniformLocation(program, 'uPixelJitter'),
      enableRipples: gl.getUniformLocation(program, 'uEnableRipples'),
      rippleSpeed: gl.getUniformLocation(program, 'uRippleSpeed'),
      rippleThickness: gl.getUniformLocation(program, 'uRippleThickness'),
      rippleIntensity: gl.getUniformLocation(program, 'uRippleIntensity'),
      edgeFade: gl.getUniformLocation(program, 'uEdgeFade'),
      shapeType: gl.getUniformLocation(program, 'uShapeType'),
      liquidStrength: gl.getUniformLocation(program, 'uLiquidStrength'),
      liquidWobbleSpeed: gl.getUniformLocation(program, 'uLiquidWobbleSpeed'),
      clickPos: gl.getUniformLocation(program, 'uClickPos'),
      clickTimes: gl.getUniformLocation(program, 'uClickTimes')
    };

    const maxClicks = 8;
    const clickPositions = new Float32Array(maxClicks * 2).fill(-1);
    const clickTimes = new Float32Array(maxClicks).fill(0);
    let clickIndex = 0;

    const rgb = parseHexColor(color);
    gl.uniform3f(uLocs.color, rgb[0], rgb[1], rgb[2]);
    gl.uniform1f(uLocs.scale, patternScale);
    gl.uniform1f(uLocs.density, patternDensity);
    gl.uniform1f(uLocs.pixelJitter, pixelSizeJitter);
    gl.uniform1i(uLocs.enableRipples, enableRipples ? 1 : 0);
    gl.uniform1f(uLocs.rippleSpeed, rippleSpeed);
    gl.uniform1f(uLocs.rippleThickness, rippleThickness);
    gl.uniform1f(uLocs.rippleIntensity, rippleIntensityScale);
    gl.uniform1f(uLocs.edgeFade, edgeFade);
    gl.uniform1i(uLocs.shapeType, SHAPE_MAP[variant] ?? 3);
    gl.uniform1f(uLocs.liquidStrength, liquid ? liquidStrength : 0.0);
    gl.uniform1f(uLocs.liquidWobbleSpeed, liquidWobbleSpeed);

    // Resolution handling with mobile optimization
    const updateSize = () => {
      const isMobile = window.innerWidth < 768;
      const dpr = isMobile ? 1 : Math.min(window.devicePixelRatio || 1, 1.25);
      const width = Math.max(1, Math.floor(container.clientWidth * dpr));
      const height = Math.max(1, Math.floor(container.clientHeight * dpr));
      
      if (canvas.width !== width || canvas.height !== height) {
        canvas.width = width;
        canvas.height = height;
        gl.viewport(0, 0, width, height);
        gl.uniform2f(uLocs.resolution, width, height);
        gl.uniform1f(uLocs.pixelSize, pixelSize * dpr);
      }
    };
    updateSize();

    const ro = new ResizeObserver(updateSize);
    ro.observe(container);

    // Pointer down ripple effect
    const handlePointer = (e) => {
      const rect = canvas.getBoundingClientRect();
      const scaleX = canvas.width / (rect.width || 1);
      const scaleY = canvas.height / (rect.height || 1);
      const fx = (e.clientX - rect.left) * scaleX;
      const fy = (rect.height - (e.clientY - rect.top)) * scaleY;

      clickPositions[clickIndex * 2] = fx;
      clickPositions[clickIndex * 2 + 1] = fy;
      clickTimes[clickIndex] = currentTime;
      clickIndex = (clickIndex + 1) % maxClicks;

      gl.uniform2fv(uLocs.clickPos, clickPositions);
      gl.uniform1fv(uLocs.clickTimes, clickTimes);
    };

    window.addEventListener('pointerdown', handlePointer, { passive: true });

    // IntersectionObserver to sleep when off-screen
    let io;
    if (autoPauseOffscreen && typeof IntersectionObserver !== 'undefined') {
      io = new IntersectionObserver(([entry]) => {
        isVisibleRef.current = entry.isIntersecting;
      }, { threshold: 0.0, rootMargin: '200px 0px 200px 0px' });
      io.observe(container);
    }

    const handleVisibility = () => {
      isVisibleRef.current = !document.hidden;
    };
    document.addEventListener('visibilitychange', handleVisibility);

    let rafId = 0;
    let startTime = performance.now();
    let currentTime = 0;

    const render = (now) => {
      if (isVisibleRef.current && canvas.width > 0 && canvas.height > 0) {
        gl.useProgram(program);
        gl.viewport(0, 0, canvas.width, canvas.height);
        gl.uniform2f(uLocs.resolution, canvas.width, canvas.height);
        currentTime = (now - startTime) * 0.001 * speed;
        gl.uniform1f(uLocs.time, currentTime);
        gl.clearColor(0, 0, 0, 0);
        gl.clear(gl.COLOR_BUFFER_BIT);
        gl.drawArrays(gl.TRIANGLES, 0, 6);
      }
      rafId = requestAnimationFrame(render);
    };
    rafId = requestAnimationFrame(render);

    return () => {
      cancelAnimationFrame(rafId);
      ro.disconnect();
      if (io) io.disconnect();
      document.removeEventListener('visibilitychange', handleVisibility);
      window.removeEventListener('pointerdown', handlePointer);
      gl.deleteBuffer(positionBuffer);
      gl.deleteProgram(program);
      gl.deleteShader(vs);
      gl.deleteShader(fs);
    };
  }, [
    variant,
    pixelSize,
    color,
    patternScale,
    patternDensity,
    liquid,
    liquidStrength,
    liquidWobbleSpeed,
    pixelSizeJitter,
    enableRipples,
    rippleIntensityScale,
    rippleThickness,
    rippleSpeed,
    autoPauseOffscreen,
    speed,
    edgeFade
  ]);

  return (
    <div
      ref={containerRef}
      className={`pixel-blast-container ${className}`}
      style={style}
      aria-hidden="true"
    >
      <canvas ref={canvasRef} />
    </div>
  );
};

export default PixelBlast;
