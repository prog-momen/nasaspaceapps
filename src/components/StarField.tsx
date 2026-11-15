"use client";

import React, { useEffect, useRef } from "react";

export type StarMode = "arrive" | "idle" | "leave";

interface Star {
  a: number; // angle from the centre
  r: number; // distance from the centre, 0..1 of the half-diagonal
  z: number; // depth 0..1 (near stars are bigger, brighter and faster)
  tw: number; // twinkle phase
  hue: number;
}

const TINTS = ["255,255,255", "205,225,255", "255,240,205", "190,210,255"];

/**
 * Full-screen starfield on a canvas. "arrive": stars rush toward the viewer and slow down (the arrival).
 * "idle": a slow drift with twinkling. "leave": stars stretch into streaks as the viewer is pulled into the Earth.
 */
export default function StarField({ mode }: { mode: StarMode }) {
  const ref = useRef<HTMLCanvasElement | null>(null);
  const modeRef = useRef<StarMode>(mode);
  useEffect(() => {
    modeRef.current = mode;
  }, [mode]);

  useEffect(() => {
    const canvas = ref.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    let w = 0;
    let h = 0;
    let raf = 0;
    let last = performance.now();
    const t0 = last;
    let speed = reduced ? 0 : 1.1; // begins fast (arrival) and decays
    const stars: Star[] = Array.from({ length: 260 }, () => ({
      a: Math.random() * Math.PI * 2,
      r: Math.pow(Math.random(), 1.6),
      z: Math.random(),
      tw: Math.random() * Math.PI * 2,
      hue: Math.floor(Math.random() * TINTS.length),
    }));

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      w = window.innerWidth;
      h = window.innerHeight;
      canvas.width = Math.floor(w * dpr);
      canvas.height = Math.floor(h * dpr);
      canvas.style.width = `${w}px`;
      canvas.style.height = `${h}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();
    window.addEventListener("resize", resize);

    const frame = (now: number) => {
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      const m = modeRef.current;
      const target = m === "leave" ? 3.2 : m === "arrive" ? Math.max(0.03, 1.1 * Math.exp(-(now - t0) / 650)) : 0.03;
      // ease toward the target speed (faster when accelerating into the Earth)
      speed += (target - speed) * Math.min(1, dt * (m === "leave" ? 3.5 : 2.2));
      if (reduced) speed = 0;

      const cx = w / 2;
      const cy = h / 2;
      const half = Math.hypot(cx, cy);
      ctx.clearRect(0, 0, w, h);
      // soft deep-space glow behind the logo
      const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, half * 0.75);
      g.addColorStop(0, "rgba(24,38,84,0.35)");
      g.addColorStop(1, "rgba(0,0,0,0)");
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, w, h);

      const fade = Math.min(1, (now - t0) / 900); // stars fade in with the logo
      for (const s of stars) {
        const v = speed * (0.25 + s.z * 1.4);
        const prevR = s.r;
        s.r += v * dt * (0.35 + s.r * 1.6); // perspective: faster as it nears the edge
        if (s.r > 1.05) {
          s.r = 0.02 + Math.random() * 0.12;
          s.a = Math.random() * Math.PI * 2;
          s.z = Math.random();
        }
        const px = cx + Math.cos(s.a) * s.r * half;
        const py = cy + Math.sin(s.a) * s.r * half;
        const tw = 0.65 + 0.35 * Math.sin(now / 700 + s.tw * 3);
        const alpha = Math.min(1, (0.25 + s.z * 0.75) * tw) * fade * Math.min(1, s.r * 6);
        const size = 0.5 + s.z * 1.5 + s.r * 0.9;
        const col = TINTS[s.hue];
        if (speed > 0.35) {
          // streak from the previous position along the radial line
          const sx = cx + Math.cos(s.a) * prevR * half;
          const sy = cy + Math.sin(s.a) * prevR * half;
          const len = Math.min(1, speed * 0.5);
          ctx.strokeStyle = `rgba(${col},${alpha})`;
          ctx.lineWidth = size;
          ctx.beginPath();
          ctx.moveTo(px - (px - sx) * (1 + len * 6), py - (py - sy) * (1 + len * 6));
          ctx.lineTo(px, py);
          ctx.stroke();
        } else {
          ctx.fillStyle = `rgba(${col},${alpha})`;
          ctx.beginPath();
          ctx.arc(px, py, size, 0, Math.PI * 2);
          ctx.fill();
          if (s.z > 0.86) {
            // a few bright stars get a faint glow
            ctx.fillStyle = `rgba(${col},${alpha * 0.18})`;
            ctx.beginPath();
            ctx.arc(px, py, size * 3.2, 0, Math.PI * 2);
            ctx.fill();
          }
        }
      }
      raf = requestAnimationFrame(frame);
    };
    raf = requestAnimationFrame(frame);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
    };
  }, []);

  return <canvas ref={ref} aria-hidden="true" className="absolute inset-0" />;
}
