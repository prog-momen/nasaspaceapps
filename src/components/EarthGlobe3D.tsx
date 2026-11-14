"use client";

import React, { useEffect, useRef, useState, useCallback } from "react";
import { Country, COUNTRIES } from "../data/countries";
import { WORLD_LANDMASSES } from "../data/worldGeo";

interface EarthGlobe3DProps {
  selectedCountry: Country | null;
  onSelectCountry: (country: Country) => void;
  autoSpin: boolean;
  showGrid: boolean;
  onToggleAutoSpin: () => void;
  onToggleGrid: () => void;
}

export default function EarthGlobe3D({
  selectedCountry,
  onSelectCountry,
  autoSpin,
  showGrid,
  onToggleAutoSpin,
  onToggleGrid,
}: EarthGlobe3DProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // Globe orientation in radians
  // rotLng: longitude rotation (yaw)
  // rotLat: latitude rotation (pitch)
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
    rotLng: 0.2, // ~11 degrees east
    rotLat: 0.35, // ~20 degrees north
    zoom: 1.0,
    targetRotLng: null,
    targetRotLat: null,
    targetZoom: null,
    animStartTime: 0,
    startRotLng: 0,
    startRotLat: 0,
    startZoom: 1,
    animDuration: 1200,
    velLng: 0,
    velLat: 0,
  });

  // Dragging & touch gesture tracking
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

  const [currentZoomDisplay, setCurrentZoomDisplay] = useState("1.0x");

  // Trigger animation to fly to country when selected
  useEffect(() => {
    if (!selectedCountry) return;

    const state = orientationRef.current;
    const targetLng = (selectedCountry.lng * Math.PI) / 180;
    const targetLat = (selectedCountry.lat * Math.PI) / 180;

    state.startRotLng = state.rotLng;
    state.startRotLat = state.rotLat;
    state.startZoom = state.zoom;

    // Shortest rotational path for longitude
    let deltaLng = ((targetLng - state.rotLng) % (2 * Math.PI));
    if (deltaLng > Math.PI) deltaLng -= 2 * Math.PI;
    if (deltaLng < -Math.PI) deltaLng += 2 * Math.PI;

    state.targetRotLng = state.rotLng + deltaLng;
    state.targetRotLat = Math.max(-1.3, Math.min(1.3, targetLat));
    state.targetZoom = selectedCountry.zoom;
    state.animDuration = 1200;
    state.animStartTime = performance.now();
  }, [selectedCountry]);

  // Main Canvas Render Loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d", { alpha: false });
    if (!ctx) return;

    let animationFrameId: number;
    let lastTime = performance.now();

    // Resize handler
    const handleResize = () => {
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.floor(rect.width * dpr);
      canvas.height = Math.floor(rect.height * dpr);
    };

    handleResize();
    window.addEventListener("resize", handleResize);

    // Stars background (fixed positions)
    const starCount = 120;
    const stars: { x: number; y: number; r: number; color: string }[] = [];
    for (let i = 0; i < starCount; i++) {
      stars.push({
        x: Math.random(),
        y: Math.random(),
        r: Math.random() * 1.5 + 0.5,
        color: i % 3 === 0 ? "#475569" : i % 2 === 0 ? "#334155" : "#64748b",
      });
    }

    // Cubic easeInOut function
    const easeInOutCubic = (t: number): number => {
      return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
    };

    // Render frame
    const render = (time: number) => {
      const dt = Math.min((time - lastTime) / 1000, 0.1);
      lastTime = time;

      const state = orientationRef.current;

      // Handle programmatic fly-to animation
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
        // Inertia or auto-spin
        if (!gestureRef.current.isDragging) {
          if (Math.abs(state.velLng) > 0.0001 || Math.abs(state.velLat) > 0.0001) {
            state.rotLng += state.velLng * dt * 60;
            state.rotLat += state.velLat * dt * 60;
            state.velLng *= 0.92;
            state.velLat *= 0.92;
          } else if (autoSpin) {
            // Constant auto-spin when idle
            state.rotLng += 0.0035;
          }
        }
      }

      // Clamp latitude to prevent polar flipping
      state.rotLat = Math.max(-1.35, Math.min(1.35, state.rotLat));
      // Normalize longitude within [-PI, PI]
      state.rotLng = ((state.rotLng + Math.PI) % (2 * Math.PI)) - Math.PI;

      const width = canvas.width;
      const height = canvas.height;
      const dpr = Math.min(window.devicePixelRatio || 1, 2);

      const cx = width / 2;
      const cy = height / 2;
      const baseRadius = Math.min(width, height) * 0.38;
      const R = baseRadius * state.zoom;

      // Clear with solid space background
      ctx.fillStyle = "#070a13";
      ctx.fillRect(0, 0, width, height);

      // Draw background stars
      for (const s of stars) {
        ctx.fillStyle = s.color;
        ctx.beginPath();
        ctx.arc(s.x * width, s.y * height, s.r * dpr, 0, Math.PI * 2);
        ctx.fill();
      }

      // Outer atmospheric border ring (solid color)
      ctx.strokeStyle = "#1d4ed8";
      ctx.lineWidth = 2 * dpr;
      ctx.beginPath();
      ctx.arc(cx, cy, R + 3 * dpr, 0, Math.PI * 2);
      ctx.stroke();

      // Ocean sphere (solid dark navy)
      ctx.fillStyle = "#0f172a";
      ctx.beginPath();
      ctx.arc(cx, cy, R, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = "#1e3a8a";
      ctx.lineWidth = 1.5 * dpr;
      ctx.stroke();

      // Clip drawing inside Earth sphere
      ctx.save();
      ctx.beginPath();
      ctx.arc(cx, cy, R - 0.5, 0, Math.PI * 2);
      ctx.clip();

      const cosLat0 = Math.cos(state.rotLat);
      const sinLat0 = Math.sin(state.rotLat);

      // Project spherical (lon, lat) in radians to 3D Cartesian
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

      // 1. Draw Lat/Lng Graticule Grid
      if (showGrid) {
        ctx.lineWidth = 0.75 * dpr;

        // Parallels (latitude lines every 30 degrees)
        for (let latDeg = -60; latDeg <= 60; latDeg += 30) {
          const isEquator = latDeg === 0;
          ctx.strokeStyle = isEquator ? "#2563eb" : "#1e293b";
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

        // Meridians (longitude lines every 30 degrees)
        for (let lonDeg = -180; lonDeg < 180; lonDeg += 30) {
          const isPrime = lonDeg === 0;
          ctx.strokeStyle = isPrime ? "#38bdf8" : "#1e293b";
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

      // 2. Draw World Continents & Landmasses
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
          // Solid dark slate land color
          ctx.fillStyle = "#1e293b";
          ctx.fill();
          // Solid coastline border
          ctx.strokeStyle = "#334155";
          ctx.lineWidth = 1 * dpr;
          ctx.stroke();
        }
      }

      // 3. Draw Country Centroid Markers
      for (const country of COUNTRIES) {
        const isSelected = selectedCountry?.id === country.id;
        const p = project(
          (country.lng * Math.PI) / 180,
          (country.lat * Math.PI) / 180
        );

        if (p.visible) {
          // Perspective scale based on Z
          const scaleZ = 0.5 + 0.5 * (p.z / R);

          if (isSelected) {
            // Draw targeted selected country beacon
            const pulse = (Math.sin(time / 200) + 1) / 2; // 0..1
            const pulseRadius = (8 + pulse * 14) * dpr;

            // Outer ring
            ctx.strokeStyle = "#22c55e";
            ctx.lineWidth = 2 * dpr;
            ctx.beginPath();
            ctx.arc(p.x, p.y, pulseRadius, 0, Math.PI * 2);
            ctx.stroke();

            // Inner target dot
            ctx.fillStyle = "#22c55e";
            ctx.beginPath();
            ctx.arc(p.x, p.y, 5 * dpr, 0, Math.PI * 2);
            ctx.fill();

            // Center core
            ctx.fillStyle = "#ffffff";
            ctx.beginPath();
            ctx.arc(p.x, p.y, 2 * dpr, 0, Math.PI * 2);
            ctx.fill();
          } else {
            // Standard country marker dot
            ctx.fillStyle = "#38bdf8";
            ctx.beginPath();
            ctx.arc(p.x, p.y, 2.5 * scaleZ * dpr, 0, Math.PI * 2);
            ctx.fill();
          }
        }
      }

      // 4. Draw Selected Country Floating Label Box
      if (selectedCountry) {
        const p = project(
          (selectedCountry.lng * Math.PI) / 180,
          (selectedCountry.lat * Math.PI) / 180
        );

        if (p.visible) {
          const labelText = selectedCountry.name;
          const subText = `${selectedCountry.capital} • ${selectedCountry.code3}`;

          ctx.font = `bold ${Math.round(13 * dpr)}px Arial, Helvetica, sans-serif`;
          const textWidth = Math.max(
            ctx.measureText(labelText).width,
            ctx.measureText(subText).width
          );

          const boxWidth = textWidth + 24 * dpr;
          const boxHeight = 44 * dpr;
          const boxX = p.x - boxWidth / 2;
          const boxY = p.y - 60 * dpr;

          // Indicator stem line
          ctx.strokeStyle = "#22c55e";
          ctx.lineWidth = 1.5 * dpr;
          ctx.beginPath();
          ctx.moveTo(p.x, p.y - 8 * dpr);
          ctx.lineTo(p.x, boxY + boxHeight);
          ctx.stroke();

          // Label box background (solid dark)
          ctx.fillStyle = "#111827";
          ctx.fillRect(boxX, boxY, boxWidth, boxHeight);
          ctx.strokeStyle = "#22c55e";
          ctx.lineWidth = 1.5 * dpr;
          ctx.strokeRect(boxX, boxY, boxWidth, boxHeight);

          // Country Name
          ctx.fillStyle = "#f8fafc";
          ctx.textAlign = "center";
          ctx.font = `bold ${Math.round(12 * dpr)}px Arial, Helvetica, sans-serif`;
          ctx.fillText(labelText, p.x, boxY + 18 * dpr);

          // Capital & Code
          ctx.fillStyle = "#94a3b8";
          ctx.font = `${Math.round(10 * dpr)}px Arial, Helvetica, sans-serif`;
          ctx.fillText(subText, p.x, boxY + 34 * dpr);
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
  }, [autoSpin, showGrid, selectedCountry]);

  // Touch and Mouse Interactions

  const handlePointerDown = (clientX: number, clientY: number) => {
    const gesture = gestureRef.current;
    gesture.isDragging = true;
    gesture.lastX = clientX;
    gesture.lastY = clientY;
    gesture.startX = clientX;
    gesture.startY = clientY;

    // Reset momentum
    orientationRef.current.velLng = 0;
    orientationRef.current.velLat = 0;
    // Cancel active fly-to animation
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
    // Sensitivity adjusts with zoom level
    const sens = 0.0055 / state.zoom;

    state.rotLng += dx * sens;
    state.rotLat += dy * sens;

    // Record instantaneous velocity for smooth release momentum
    state.velLng = dx * sens * 0.4;
    state.velLat = dy * sens * 0.4;
  };

  const handlePointerUp = (clientX: number, clientY: number) => {
    const gesture = gestureRef.current;
    if (!gesture.isDragging) return;
    gesture.isDragging = false;

    // Check if it was a tap/click without dragging
    const distSq =
      Math.pow(clientX - gesture.startX, 2) +
      Math.pow(clientY - gesture.startY, 2);

    if (distSq < 25) {
      // User tapped on the canvas: pick closest visible country
      pickCountryAtCoords(clientX, clientY);
    }
  };

  // Find country closest to screen tap/click
  const pickCountryAtCoords = (screenX: number, screenY: number) => {
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

    let closestCountry: Country | null = null;
    let minDist = 40 * dpr; // selection radius

    for (const c of COUNTRIES) {
      const lonRad = (c.lng * Math.PI) / 180;
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
          closestCountry = c;
        }
      }
    }

    if (closestCountry) {
      onSelectCountry(closestCountry);
    }
  };

  // Zoom manipulation
  const adjustZoom = useCallback((factor: number) => {
    const state = orientationRef.current;
    const newZoom = Math.max(0.75, Math.min(5.5, state.zoom * factor));
    state.zoom = newZoom;
    setCurrentZoomDisplay(`${newZoom.toFixed(1)}x`);
  }, []);

  const resetView = useCallback(() => {
    const state = orientationRef.current;
    state.startRotLng = state.rotLng;
    state.startRotLat = state.rotLat;
    state.startZoom = state.zoom;
    state.targetRotLng = 0.2;
    state.targetRotLat = 0.35;
    state.targetZoom = 1.0;
    state.animDuration = 900;
    state.animStartTime = performance.now();
    setCurrentZoomDisplay("1.0x");
  }, []);

  return (
    <div className="relative w-full h-full overflow-hidden select-none touch-none bg-[#070a13]">
      <canvas
        ref={canvasRef}
        className="w-full h-full block cursor-grab active:cursor-grabbing"
        // Mouse Events (Desktop)
        onMouseDown={(e) => handlePointerDown(e.clientX, e.clientY)}
        onMouseMove={(e) => handlePointerMove(e.clientX, e.clientY)}
        onMouseUp={(e) => handlePointerUp(e.clientX, e.clientY)}
        onMouseLeave={(e) => handlePointerUp(e.clientX, e.clientY)}
        onWheel={(e) => {
          e.preventDefault();
          const factor = e.deltaY < 0 ? 1.15 : 0.88;
          adjustZoom(factor);
        }}
        // Touch Events (Phone / Mobile)
        onTouchStart={(e) => {
          if (e.touches.length === 1) {
            handlePointerDown(e.touches[0].clientX, e.touches[0].clientY);
          } else if (e.touches.length === 2) {
            // Pinch-to-zoom start
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
            // Pinch-to-zoom move
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
              handlePointerUp(
                e.changedTouches[0].clientX,
                e.changedTouches[0].clientY
              );
            }
          }
        }}
      />

      {/* Floating View Controls (Zoom, Reset, Spin, Grid) */}
      <div className="absolute right-4 bottom-6 flex flex-col gap-2 z-10 items-center">
        {/* Zoom Indicator */}
        <div className="px-2 py-1 bg-[#111827] border border-[#374151] rounded text-[10px] font-mono font-bold text-[#60a5fa] select-none">
          {currentZoomDisplay}
        </div>

        {/* Zoom In */}
        <button
          onClick={() => adjustZoom(1.25)}
          title="Zoom In"
          className="w-10 h-10 flex items-center justify-center bg-[#111827] border border-[#374151] text-[#f3f4f6] hover:bg-[#1f2937] active:bg-[#374151] rounded text-lg font-bold transition-colors"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
        </button>

        {/* Zoom Out */}
        <button
          onClick={() => adjustZoom(0.8)}
          title="Zoom Out"
          className="w-10 h-10 flex items-center justify-center bg-[#111827] border border-[#374151] text-[#f3f4f6] hover:bg-[#1f2937] active:bg-[#374151] rounded text-lg font-bold transition-colors"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
        </button>

        {/* Reset View */}
        <button
          onClick={resetView}
          title="Reset View"
          className="w-10 h-10 flex items-center justify-center bg-[#111827] border border-[#374151] text-[#9ca3af] hover:text-[#f3f4f6] hover:bg-[#1f2937] active:bg-[#374151] rounded text-xs font-semibold transition-colors"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="9"></circle>
            <line x1="12" y1="3" x2="12" y2="7"></line>
            <line x1="12" y1="17" x2="12" y2="21"></line>
            <line x1="3" y1="12" x2="7" y2="12"></line>
            <line x1="17" y1="12" x2="21" y2="12"></line>
          </svg>
        </button>

        {/* Auto-Spin Toggle */}
        <button
          onClick={onToggleAutoSpin}
          title={autoSpin ? "Stop Auto-Spin" : "Start Auto-Spin"}
          className={`w-10 h-10 flex items-center justify-center border rounded text-xs font-semibold transition-colors ${
            autoSpin
              ? "bg-[#1e3a8a] border-[#3b82f6] text-[#60a5fa]"
              : "bg-[#111827] border-[#374151] text-[#9ca3af] hover:text-[#f3f4f6]"
          }`}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"></path>
          </svg>
        </button>

        {/* Lat/Lng Grid Toggle */}
        <button
          onClick={onToggleGrid}
          title={showGrid ? "Hide Grid Lines" : "Show Grid Lines"}
          className={`w-10 h-10 flex items-center justify-center border rounded text-xs font-semibold transition-colors ${
            showGrid
              ? "bg-[#1e3a8a] border-[#3b82f6] text-[#60a5fa]"
              : "bg-[#111827] border-[#374151] text-[#9ca3af] hover:text-[#f3f4f6]"
          }`}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="2" y1="12" x2="22" y2="12"></line>
            <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>
          </svg>
        </button>
      </div>

      {/* Touch & Mouse Guidance Hint */}
      <div className="absolute left-4 bottom-6 pointer-events-none hidden sm:block">
        <div className="bg-[#111827] border border-[#1f2937] px-3 py-2 rounded text-xs text-[#94a3b8] flex items-center gap-3">
          <span>Drag with mouse / finger to rotate</span>
          <span className="text-[#374151]">|</span>
          <span>Wheel / pinch to zoom</span>
          <span className="text-[#374151]">|</span>
          <span>Click any region to inspect</span>
        </div>
      </div>
    </div>
  );
}
