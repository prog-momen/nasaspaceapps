"use client";

import React, { useEffect, useRef, useState, useCallback } from "react";
import { EnvLayerKey, CountryTrend, PilotRegion } from "../data/nasaTrends";
import { WORLD_LANDMASSES } from "../data/worldGeo";

interface EarthScopeGlobeProps {
  mode: "world" | "ai";
  selectedCountry: CountryTrend | null;
  onSelectCountry: (c: CountryTrend) => void;
  selectedPilotRegion: PilotRegion | null;
  onSelectPilotRegion: (r: PilotRegion) => void;
  pilotRegions: PilotRegion[];
  allCountries: CountryTrend[];
  envLayer: EnvLayerKey;
  envOpacity: number;
  showClouds: boolean;
  showBorders: boolean;
  showGraticule: boolean;
  autoSpin: boolean;
  sunAngle: number;
  currentYear: number;
  onToggleAutoSpin: () => void;
}

export default function EarthScopeGlobe({
  mode,
  selectedCountry,
  onSelectCountry,
  selectedPilotRegion,
  onSelectPilotRegion,
  pilotRegions,
  allCountries,
  envLayer,
  showClouds,
  showBorders,
  showGraticule,
  autoSpin,
  sunAngle,
  onToggleAutoSpin,
}: EarthScopeGlobeProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const orientationRef = useRef<{
    rotLng: number;
    rotLat: number;
    zoom: number;
    targetRotLng: number | null;
    targetRotLat: number | null;
    targetZoom: number | null;
    animStartTime: number;
    startRotLng: number;
    startRotLat: number;
    startZoom: number;
    animDuration: number;
    velLng: number;
    velLat: number;
  }>({
    rotLng: 0.61, // Center around Middle East / Levant by default
    rotLat: 0.55,
    zoom: 1.0,
    targetRotLng: null,
    targetRotLat: null,
    targetZoom: null,
    animStartTime: 0,
    startRotLng: 0,
    startRotLat: 0,
    startZoom: 1,
    animDuration: 1000,
    velLng: 0,
    velLat: 0,
  });

  const gestureRef = useRef<{
    isDragging: boolean;
    lastX: number;
    lastY: number;
    startX: number;
    startY: number;
    pinchDist: number | null;
  }>({
    isDragging: false,
    lastX: 0,
    lastY: 0,
    startX: 0,
    startY: 0,
    pinchDist: null,
  });

  const [zoomDisplay, setZoomDisplay] = useState("1.0x");

  // Animate camera to selected country (World Mode)
  useEffect(() => {
    if (mode !== "world" || !selectedCountry) return;

    const state = orientationRef.current;
    const targetLng = (selectedCountry.lon * Math.PI) / 180;
    const targetLat = (selectedCountry.lat * Math.PI) / 180;

    state.startRotLng = state.rotLng;
    state.startRotLat = state.rotLat;
    state.startZoom = state.zoom;

    let deltaLng = (targetLng - state.rotLng) % (2 * Math.PI);
    if (deltaLng > Math.PI) deltaLng -= 2 * Math.PI;
    if (deltaLng < -Math.PI) deltaLng += 2 * Math.PI;

    state.targetRotLng = state.rotLng + deltaLng;
    state.targetRotLat = Math.max(-1.3, Math.min(1.3, targetLat));
    state.targetZoom = 2.4;
    state.animDuration = 1100;
    state.animStartTime = performance.now();
  }, [selectedCountry, mode]);

  // Animate camera to selected pilot region (AI Mode)
  useEffect(() => {
    if (mode !== "ai" || !selectedPilotRegion) return;

    const state = orientationRef.current;
    const targetLng = (selectedPilotRegion.lon * Math.PI) / 180;
    const targetLat = (selectedPilotRegion.lat * Math.PI) / 180;

    state.startRotLng = state.rotLng;
    state.startRotLat = state.rotLat;
    state.startZoom = state.zoom;

    let deltaLng = (targetLng - state.rotLng) % (2 * Math.PI);
    if (deltaLng > Math.PI) deltaLng -= 2 * Math.PI;
    if (deltaLng < -Math.PI) deltaLng += 2 * Math.PI;

    state.targetRotLng = state.rotLng + deltaLng;
    state.targetRotLat = Math.max(-1.3, Math.min(1.3, targetLat));
    state.targetZoom = 3.6; // Close-up on regional cluster
    state.animDuration = 1000;
    state.animStartTime = performance.now();
  }, [selectedPilotRegion, mode]);

  // Main Canvas Render Loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d", { alpha: false });
    if (!ctx) return;

    let animationFrameId: number;
    let lastTime = performance.now();

    const handleResize = () => {
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.floor(rect.width * dpr);
      canvas.height = Math.floor(rect.height * dpr);
    };

    handleResize();
    window.addEventListener("resize", handleResize);

    // Stars background
    const stars: { x: number; y: number; r: number; color: string }[] = [];
    for (let i = 0; i < 150; i++) {
      stars.push({
        x: Math.random(),
        y: Math.random(),
        r: Math.random() * 1.5 + 0.4,
        color: i % 4 === 0 ? "#64748b" : i % 2 === 0 ? "#334155" : "#475569",
      });
    }

    const easeInOutCubic = (t: number): number => {
      return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
    };

    const render = (time: number) => {
      const dt = Math.min((time - lastTime) / 1000, 0.1);
      lastTime = time;

      const state = orientationRef.current;

      // Camera interpolation
      if (
        state.targetRotLng !== null &&
        state.targetRotLat !== null &&
        state.targetZoom !== null
      ) {
        const elapsed = time - state.animStartTime;
        const progress = Math.min(1, elapsed / state.animDuration);
        const ease = easeInOutCubic(progress);

        state.rotLng = state.startRotLng + (state.targetRotLng - state.startRotLng) * ease;
        state.rotLat = state.startRotLat + (state.targetRotLat - state.startRotLat) * ease;
        state.zoom = state.startZoom + (state.targetZoom - state.startZoom) * ease;

        if (progress >= 1) {
          state.targetRotLng = null;
          state.targetRotLat = null;
          state.targetZoom = null;
        }
      } else {
        if (!gestureRef.current.isDragging) {
          if (Math.abs(state.velLng) > 0.0001 || Math.abs(state.velLat) > 0.0001) {
            state.rotLng += state.velLng * dt * 60;
            state.rotLat += state.velLat * dt * 60;
            state.velLng *= 0.92;
            state.velLat *= 0.92;
          } else if (autoSpin) {
            state.rotLng += 0.003;
          }
        }
      }

      state.rotLat = Math.max(-1.35, Math.min(1.35, state.rotLat));
      state.rotLng = ((state.rotLng + Math.PI) % (2 * Math.PI)) - Math.PI;

      const width = canvas.width;
      const height = canvas.height;
      const dpr = Math.min(window.devicePixelRatio || 1, 2);

      const cx = width / 2;
      const cy = height / 2;
      const baseRadius = Math.min(width, height) * 0.38;
      const R = baseRadius * state.zoom;

      // Solid space background
      ctx.fillStyle = "#070a13";
      ctx.fillRect(0, 0, width, height);

      // Stars
      for (const s of stars) {
        ctx.fillStyle = s.color;
        ctx.beginPath();
        ctx.arc(s.x * width, s.y * height, s.r * dpr, 0, Math.PI * 2);
        ctx.fill();
      }

      // Outer atmospheric border (solid ring)
      ctx.strokeStyle = "#1d4ed8";
      ctx.lineWidth = 2 * dpr;
      ctx.beginPath();
      ctx.arc(cx, cy, R + 3 * dpr, 0, Math.PI * 2);
      ctx.stroke();

      // Determine ocean base color based on active environmental layer
      let oceanColor = "#0f172a";
      let landColor = "#1e293b";
      let borderColor = "#334155";

      if (envLayer === "temp") {
        oceanColor = "#0c1527";
        landColor = "#2a1e1e";
        borderColor = "#f59e0b";
      } else if (envLayer === "water") {
        oceanColor = "#0d1b2a";
        landColor = "#1b2838";
        borderColor = "#0284c7";
      } else if (envLayer === "winds") {
        oceanColor = "#11142b";
        landColor = "#1e1e38";
        borderColor = "#6366f1";
      } else if (envLayer === "veg") {
        oceanColor = "#0a1f1a";
        landColor = "#163326";
        borderColor = "#10b981";
      } else if (envLayer === "fires") {
        oceanColor = "#1c0d12";
        landColor = "#2d151c";
        borderColor = "#f43f5e";
      }

      // Ocean sphere
      ctx.fillStyle = oceanColor;
      ctx.beginPath();
      ctx.arc(cx, cy, R, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = "#1e3a8a";
      ctx.lineWidth = 1.5 * dpr;
      ctx.stroke();

      // Clip drawing inside sphere
      ctx.save();
      ctx.beginPath();
      ctx.arc(cx, cy, R - 0.5, 0, Math.PI * 2);
      ctx.clip();

      const cosLat0 = Math.cos(state.rotLat);
      const sinLat0 = Math.sin(state.rotLat);

      const project = (
        lonRad: number,
        latRad: number
      ): { x: number; y: number; z: number; visible: boolean } => {
        const deltaLon = lonRad - state.rotLng;
        const cosLat = Math.cos(latRad);
        const sinLat = Math.sin(latRad);
        const cosDelta = Math.cos(deltaLon);
        const sinDelta = Math.sin(deltaLon);

        const x = R * cosLat * sinDelta;
        const y = R * (cosLat0 * sinLat - sinLat0 * cosLat * cosDelta);
        const z = R * (sinLat0 * sinLat + cosLat0 * cosLat * cosDelta);

        return {
          x: cx + x,
          y: cy - y,
          z: z,
          visible: z >= 0,
        };
      };

      // 1. Lat/Lng Graticule
      if (showGraticule) {
        ctx.lineWidth = 0.75 * dpr;

        for (let latDeg = -60; latDeg <= 60; latDeg += 30) {
          ctx.strokeStyle = latDeg === 0 ? "#2563eb" : "#1e293b";
          ctx.beginPath();
          let started = false;
          const latRad = (latDeg * Math.PI) / 180;
          for (let lonDeg = -180; lonDeg <= 180; lonDeg += 4) {
            const p = project((lonDeg * Math.PI) / 180, latRad);
            if (p.visible) {
              if (!started) {
                ctx.moveTo(p.x, p.y);
                started = true;
              } else {
                ctx.lineTo(p.x, p.y);
              }
            } else {
              started = false;
            }
          }
          ctx.stroke();
        }

        for (let lonDeg = -180; lonDeg < 180; lonDeg += 30) {
          ctx.strokeStyle = lonDeg === 0 ? "#38bdf8" : "#1e293b";
          ctx.beginPath();
          let started = false;
          const lonRad = (lonDeg * Math.PI) / 180;
          for (let latDeg = -85; latDeg <= 85; latDeg += 4) {
            const p = project(lonRad, (latDeg * Math.PI) / 180);
            if (p.visible) {
              if (!started) {
                ctx.moveTo(p.x, p.y);
                started = true;
              } else {
                ctx.lineTo(p.x, p.y);
              }
            } else {
              started = false;
            }
          }
          ctx.stroke();
        }
      }

      // 2. World Continents
      for (const land of WORLD_LANDMASSES) {
        ctx.beginPath();
        let anyVisible = false;

        for (let i = 0; i < land.coordinates.length; i++) {
          const [lng, lat] = land.coordinates[i];
          const p = project((lng * Math.PI) / 180, (lat * Math.PI) / 180);

          if (i === 0) {
            ctx.moveTo(p.x, p.y);
          } else {
            ctx.lineTo(p.x, p.y);
          }

          if (p.visible) {
            anyVisible = true;
          }
        }

        if (anyVisible) {
          ctx.closePath();
          ctx.fillStyle = landColor;
          ctx.fill();
          if (showBorders) {
            ctx.strokeStyle = borderColor;
            ctx.lineWidth = 1 * dpr;
            ctx.stroke();
          }
        }
      }

      // 3. Environmental Layer Visual Overlay (Winds / Fires)
      if (envLayer === "winds") {
        ctx.strokeStyle = "#818cf8";
        ctx.lineWidth = 1.2 * dpr;
        const windArcs = [
          [-30, 20], [20, 25], [45, 20], [80, 15], [-100, 35], [-60, -20], [120, -25]
        ];
        for (const [wLng, wLat] of windArcs) {
          const p = project((wLng * Math.PI) / 180, (wLat * Math.PI) / 180);
          if (p.visible) {
            ctx.beginPath();
            ctx.arc(p.x, p.y, 8 * dpr, 0, Math.PI);
            ctx.stroke();
          }
        }
      } else if (envLayer === "fires") {
        ctx.fillStyle = "#ef4444";
        const fireClusters = [
          [35.5, 32.2], [-3.7, 40.2], [-120.0, 38.0], [149.0, -35.0], [-60.0, -8.0]
        ];
        for (const [fLng, fLat] of fireClusters) {
          const p = project((fLng * Math.PI) / 180, (fLat * Math.PI) / 180);
          if (p.visible) {
            ctx.beginPath();
            ctx.arc(p.x, p.y, 6 * dpr, 0, Math.PI * 2);
            ctx.fill();
          }
        }
      }

      // 4. Clouds layer (solid white subtle wisps)
      if (showClouds) {
        ctx.fillStyle = "rgba(255, 255, 255, 0.12)";
        const cloudBands = [10, -10, 45, -50];
        for (const cLat of cloudBands) {
          for (let cLon = -180; cLon < 180; cLon += 40) {
            const p = project((cLon * Math.PI) / 180, (cLat * Math.PI) / 180);
            if (p.visible) {
              ctx.beginPath();
              ctx.ellipse(p.x, p.y, 22 * dpr, 9 * dpr, 0.2, 0, Math.PI * 2);
              ctx.fill();
            }
          }
        }
      }

      // 5. Sun Terminator / Shading Line
      const sunRad = (sunAngle * Math.PI) / 180;
      ctx.strokeStyle = "#475569";
      ctx.lineWidth = 1 * dpr;
      ctx.beginPath();
      ctx.arc(cx + Math.cos(sunRad) * R * 0.9, cy + Math.sin(sunRad) * R * 0.9, 4 * dpr, 0, Math.PI * 2);
      ctx.stroke();

      // 6. Draw Markers based on Mode
      if (mode === "world") {
        // World Mode: Country centroids
        for (const country of allCountries) {
          const isSelected = selectedCountry?.key === country.key;
          const p = project((country.lon * Math.PI) / 180, (country.lat * Math.PI) / 180);

          if (p.visible) {
            if (isSelected) {
              const pulse = (Math.sin(time / 200) + 1) / 2;
              const pulseRadius = (8 + pulse * 14) * dpr;

              ctx.strokeStyle = "#22c55e";
              ctx.lineWidth = 2 * dpr;
              ctx.beginPath();
              ctx.arc(p.x, p.y, pulseRadius, 0, Math.PI * 2);
              ctx.stroke();

              ctx.fillStyle = "#22c55e";
              ctx.beginPath();
              ctx.arc(p.x, p.y, 5 * dpr, 0, Math.PI * 2);
              ctx.fill();

              // Label box
              const labelText = country.nameEn;
              const hazardText = `${country.tempAnomaly} | ${country.waterTrend}`;
              ctx.font = `bold ${Math.round(12 * dpr)}px Arial, sans-serif`;
              const textWidth = Math.max(ctx.measureText(labelText).width, ctx.measureText(hazardText).width);
              const boxW = textWidth + 20 * dpr;
              const boxH = 40 * dpr;
              const boxX = p.x - boxW / 2;
              const boxY = p.y - 54 * dpr;

              ctx.strokeStyle = "#22c55e";
              ctx.lineWidth = 1.5 * dpr;
              ctx.beginPath();
              ctx.moveTo(p.x, p.y - 6 * dpr);
              ctx.lineTo(p.x, boxY + boxH);
              ctx.stroke();

              ctx.fillStyle = "#111827";
              ctx.fillRect(boxX, boxY, boxW, boxH);
              ctx.strokeStyle = "#22c55e";
              ctx.strokeRect(boxX, boxY, boxW, boxH);

              ctx.fillStyle = "#ffffff";
              ctx.textAlign = "center";
              ctx.fillText(labelText, p.x, boxY + 16 * dpr);

              ctx.fillStyle = "#93c5fd";
              ctx.font = `${Math.round(10 * dpr)}px Arial, sans-serif`;
              ctx.fillText(hazardText, p.x, boxY + 32 * dpr);
            } else {
              ctx.fillStyle = "#38bdf8";
              ctx.beginPath();
              ctx.arc(p.x, p.y, 2.5 * dpr, 0, Math.PI * 2);
              ctx.fill();
            }
          }
        }
      } else {
        // AI Mode: Pilot Regions with Risk Badges
        for (const region of pilotRegions) {
          const isSelected = selectedPilotRegion?.id === region.id;
          const p = project((region.lon * Math.PI) / 180, (region.lat * Math.PI) / 180);

          if (p.visible) {
            const riskColor =
              region.risk >= 80 ? "#ef4444" : region.risk >= 60 ? "#f59e0b" : "#10b981";

            const pulse = (Math.sin(time / 250) + 1) / 2;
            const pulseR = (6 + pulse * 10) * dpr;

            ctx.strokeStyle = riskColor;
            ctx.lineWidth = 2 * dpr;
            ctx.beginPath();
            ctx.arc(p.x, p.y, pulseR, 0, Math.PI * 2);
            ctx.stroke();

            ctx.fillStyle = riskColor;
            ctx.beginPath();
            ctx.arc(p.x, p.y, isSelected ? 6 * dpr : 4.5 * dpr, 0, Math.PI * 2);
            ctx.fill();

            // Label pill
            const title = region.nameEn.replace(/^\d+\.\s*/, "");
            const badgeText = `${region.risk}% Risk`;

            ctx.font = `bold ${Math.round(11 * dpr)}px Arial, sans-serif`;
            const tw = ctx.measureText(title).width;
            const bW = tw + 24 * dpr;
            const bH = 26 * dpr;
            const bX = p.x - bW / 2;
            const bY = p.y - 36 * dpr;

            ctx.fillStyle = "#111827";
            ctx.fillRect(bX, bY, bW, bH);
            ctx.strokeStyle = riskColor;
            ctx.lineWidth = 1.5 * dpr;
            ctx.strokeRect(bX, bY, bW, bH);

            ctx.fillStyle = "#ffffff";
            ctx.textAlign = "center";
            ctx.fillText(title, p.x, bY + 13 * dpr);

            ctx.fillStyle = riskColor;
            ctx.font = `bold ${Math.round(9 * dpr)}px Arial, sans-serif`;
            ctx.fillText(badgeText, p.x, bY + 23 * dpr);
          }
        }
      }

      ctx.restore();

      animationFrameId = requestAnimationFrame(render);
    };

    animationFrameId = requestAnimationFrame(render);

    return () => {
      window.removeEventListener("resize", handleResize);
      cancelAnimationFrame(animationFrameId);
    };
  }, [
    mode,
    selectedCountry,
    selectedPilotRegion,
    pilotRegions,
    allCountries,
    envLayer,
    showClouds,
    showBorders,
    showGraticule,
    autoSpin,
    sunAngle,
  ]);

  // Touch & Pointer Interactions
  const handlePointerDown = (clientX: number, clientY: number) => {
    const gesture = gestureRef.current;
    gesture.isDragging = true;
    gesture.lastX = clientX;
    gesture.lastY = clientY;
    gesture.startX = clientX;
    gesture.startY = clientY;

    orientationRef.current.velLng = 0;
    orientationRef.current.velLat = 0;
    orientationRef.current.targetRotLng = null;
    orientationRef.current.targetRotLat = null;
    orientationRef.current.targetZoom = null;
  };

  const handlePointerMove = (clientX: number, clientY: number) => {
    const gesture = gestureRef.current;
    if (!gesture.isDragging) return;

    const dx = clientX - gesture.lastX;
    const dy = clientY - gesture.lastY;
    gesture.lastX = clientX;
    gesture.lastY = clientY;

    const state = orientationRef.current;
    const sens = 0.0055 / state.zoom;

    state.rotLng += dx * sens;
    state.rotLat += dy * sens;

    state.velLng = dx * sens * 0.4;
    state.velLat = dy * sens * 0.4;
  };

  const handlePointerUp = (clientX: number, clientY: number) => {
    const gesture = gestureRef.current;
    if (!gesture.isDragging) return;
    gesture.isDragging = false;

    const distSq =
      Math.pow(clientX - gesture.startX, 2) + Math.pow(clientY - gesture.startY, 2);

    if (distSq < 25) {
      pickTargetAtCoords(clientX, clientY);
    }
  };

  const pickTargetAtCoords = (screenX: number, screenY: number) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const canvasX = (screenX - rect.left) * dpr;
    const canvasY = (screenY - rect.top) * dpr;

    const width = canvas.width;
    const height = canvas.height;
    const cx = width / 2;
    const cy = height / 2;
    const baseRadius = Math.min(width, height) * 0.38;
    const R = baseRadius * orientationRef.current.zoom;

    const state = orientationRef.current;
    const cosLat0 = Math.cos(state.rotLat);
    const sinLat0 = Math.sin(state.rotLat);

    if (mode === "world") {
      let closest: CountryTrend | null = null;
      let minDist = 45 * dpr;

      for (const c of allCountries) {
        const lonRad = (c.lon * Math.PI) / 180;
        const latRad = (c.lat * Math.PI) / 180;
        const deltaLon = lonRad - state.rotLng;
        const cosLat = Math.cos(latRad);
        const sinLat = Math.sin(latRad);
        const cosDelta = Math.cos(deltaLon);
        const sinDelta = Math.sin(deltaLon);

        const z = R * (sinLat0 * sinLat + cosLat0 * cosLat * cosDelta);
        if (z > 0) {
          const px = cx + R * cosLat * sinDelta;
          const py = cy - R * (cosLat0 * sinLat - sinLat0 * cosLat * cosDelta);
          const d = Math.hypot(canvasX - px, canvasY - py);
          if (d < minDist) {
            minDist = d;
            closest = c;
          }
        }
      }

      if (closest) {
        onSelectCountry(closest);
      }
    } else {
      let closestR: PilotRegion | null = null;
      let minDist = 45 * dpr;

      for (const r of pilotRegions) {
        const lonRad = (r.lon * Math.PI) / 180;
        const latRad = (r.lat * Math.PI) / 180;
        const deltaLon = lonRad - state.rotLng;
        const cosLat = Math.cos(latRad);
        const sinLat = Math.sin(latRad);
        const cosDelta = Math.cos(deltaLon);
        const sinDelta = Math.sin(deltaLon);

        const z = R * (sinLat0 * sinLat + cosLat0 * cosLat * cosDelta);
        if (z > 0) {
          const px = cx + R * cosLat * sinDelta;
          const py = cy - R * (cosLat0 * sinLat - sinLat0 * cosLat * cosDelta);
          const d = Math.hypot(canvasX - px, canvasY - py);
          if (d < minDist) {
            minDist = d;
            closestR = r;
          }
        }
      }

      if (closestR) {
        onSelectPilotRegion(closestR);
      }
    }
  };

  const adjustZoom = useCallback((factor: number) => {
    const state = orientationRef.current;
    const newZoom = Math.max(0.75, Math.min(5.5, state.zoom * factor));
    state.zoom = newZoom;
    setZoomDisplay(`${newZoom.toFixed(1)}x`);
  }, []);

  const resetView = useCallback(() => {
    const state = orientationRef.current;
    state.startRotLng = state.rotLng;
    state.startRotLat = state.rotLat;
    state.startZoom = state.zoom;
    state.targetRotLng = 0.61;
    state.targetRotLat = 0.55;
    state.targetZoom = 1.0;
    state.animDuration = 900;
    state.animStartTime = performance.now();
    setZoomDisplay("1.0x");
  }, []);

  return (
    <div className="relative w-full h-full overflow-hidden select-none touch-none bg-[#070a13]">
      <canvas
        ref={canvasRef}
        className="w-full h-full block cursor-grab active:cursor-grabbing"
        onMouseDown={(e) => handlePointerDown(e.clientX, e.clientY)}
        onMouseMove={(e) => handlePointerMove(e.clientX, e.clientY)}
        onMouseUp={(e) => handlePointerUp(e.clientX, e.clientY)}
        onMouseLeave={(e) => handlePointerUp(e.clientX, e.clientY)}
        onWheel={(e) => {
          e.preventDefault();
          adjustZoom(e.deltaY < 0 ? 1.15 : 0.88);
        }}
        onTouchStart={(e) => {
          if (e.touches.length === 1) {
            handlePointerDown(e.touches[0].clientX, e.touches[0].clientY);
          } else if (e.touches.length === 2) {
            const t1 = e.touches[0];
            const t2 = e.touches[1];
            gestureRef.current.pinchDist = Math.hypot(
              t1.clientX - t2.clientX,
              t1.clientY - t2.clientY
            );
          }
        }}
        onTouchMove={(e) => {
          if (e.touches.length === 1) {
            handlePointerMove(e.touches[0].clientX, e.touches[0].clientY);
          } else if (e.touches.length === 2) {
            const t1 = e.touches[0];
            const t2 = e.touches[1];
            const currentDist = Math.hypot(
              t1.clientX - t2.clientX,
              t1.clientY - t2.clientY
            );
            if (gestureRef.current.pinchDist) {
              const ratio = currentDist / gestureRef.current.pinchDist;
              adjustZoom(ratio);
              gestureRef.current.pinchDist = currentDist;
            }
          }
        }}
        onTouchEnd={(e) => {
          if (e.touches.length === 0) {
            gestureRef.current.pinchDist = null;
            if (e.changedTouches.length > 0) {
              handlePointerUp(e.changedTouches[0].clientX, e.changedTouches[0].clientY);
            }
          }
        }}
      />

      {/* Floating Controls Overlay (Zoom, Reset, Spin) */}
      <div className="absolute right-3.5 bottom-28 flex flex-col gap-2 z-10 items-center pointer-events-auto">
        <div className="px-2 py-0.5 bg-[#111827] border border-[#374151] rounded text-[10px] font-mono font-bold text-[#60a5fa]">
          {zoomDisplay}
        </div>

        <button
          onClick={() => adjustZoom(1.25)}
          title="Zoom In"
          className="w-9 h-9 flex items-center justify-center bg-[#111827] border border-[#374151] text-[#f3f4f6] hover:bg-[#1f2937] rounded text-base font-bold transition-colors"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
        </button>

        <button
          onClick={() => adjustZoom(0.8)}
          title="Zoom Out"
          className="w-9 h-9 flex items-center justify-center bg-[#111827] border border-[#374151] text-[#f3f4f6] hover:bg-[#1f2937] rounded text-base font-bold transition-colors"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
        </button>

        <button
          onClick={resetView}
          title="Reset Globe View"
          className="w-9 h-9 flex items-center justify-center bg-[#111827] border border-[#374151] text-[#9ca3af] hover:text-white hover:bg-[#1f2937] rounded transition-colors"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="9"></circle>
            <line x1="12" y1="3" x2="12" y2="7"></line>
            <line x1="12" y1="17" x2="12" y2="21"></line>
            <line x1="3" y1="12" x2="7" y2="12"></line>
            <line x1="17" y1="12" x2="21" y2="12"></line>
          </svg>
        </button>

        <button
          onClick={onToggleAutoSpin}
          title={autoSpin ? "Pause Auto-Rotation" : "Enable Auto-Rotation"}
          className={`w-9 h-9 flex items-center justify-center border rounded transition-colors ${
            autoSpin
              ? "bg-[#1e3a8a] border-[#3b82f6] text-[#60a5fa]"
              : "bg-[#111827] border-[#374151] text-[#9ca3af] hover:text-white"
          }`}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"></path>
          </svg>
        </button>
      </div>
    </div>
  );
}

