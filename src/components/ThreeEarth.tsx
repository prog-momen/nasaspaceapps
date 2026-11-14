"use client";

import React, { useEffect, useRef, useCallback } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { COUNTRIES, Country } from "../data/countries";
import { WORLD_LANDMASSES } from "../data/worldGeo";

interface ThreeEarthProps {
  onSelectCountry?: (country: Country) => void;
  selectedCountry?: Country | null;
}

const EARTH_RADIUS = 100;

export default function ThreeEarth({
  onSelectCountry,
  selectedCountry,
}: ThreeEarthProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  // References to keep across re-renders
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const earthGroupRef = useRef<THREE.Group | null>(null);
  const earthMeshRef = useRef<THREE.Mesh | null>(null);
  const pinsGroupRef = useRef<THREE.Group | null>(null);
  const windLinesGroupRef = useRef<THREE.Group | null>(null);
  const tweenRef = useRef<{
    startPos: THREE.Vector3;
    endPos: THREE.Vector3;
    startTime: number;
    duration: number;
  } | null>(null);

  // DOM refs for 60fps HUD updates without triggering React renders
  const hudCoordsRef = useRef<HTMLSpanElement | null>(null);
  const hudCountryRef = useRef<HTMLSpanElement | null>(null);

  // Lat/Lon to 3D Cartesian on Sphere
  const latLonToVector3 = useCallback(
    (lat: number, lon: number, radius = EARTH_RADIUS) => {
      const phi = (90 - lat) * (Math.PI / 180);
      const theta = (lon + 180) * (Math.PI / 180);
      const x = -(radius * Math.sin(phi) * Math.cos(theta));
      const z = radius * Math.sin(phi) * Math.sin(theta);
      const y = radius * Math.cos(phi);
      return new THREE.Vector3(x, y, z);
    },
    []
  );

  const vector3ToLatLon = useCallback((vec: THREE.Vector3) => {
    const normalized = vec.clone().normalize();
    const lat = 90 - (Math.acos(normalized.y) * 180) / Math.PI;
    const lon = (Math.atan2(normalized.z, -normalized.x) * 180) / Math.PI - 180;
    return {
      lat,
      lon: lon < -180 ? lon + 360 : lon > 180 ? lon - 360 : lon,
    };
  }, []);

  // Smooth camera fly-to function
  const flyToCoordinates = useCallback(
    (lat: number, lon: number, targetDistance = 210) => {
      if (!cameraRef.current || !controlsRef.current) return;
      controlsRef.current.autoRotate = false;

      const endPos = latLonToVector3(lat, lon, targetDistance);
      tweenRef.current = {
        startPos: cameraRef.current.position.clone(),
        endPos: endPos,
        startTime: performance.now(),
        duration: 1200,
      };
    },
    [latLonToVector3]
  );

  // Fly to country when selected prop changes
  useEffect(() => {
    if (!selectedCountry) return;
    const dist = Math.max(150, 280 / (selectedCountry.zoom || 1));
    flyToCoordinates(selectedCountry.lat, selectedCountry.lng, dist);
    if (hudCountryRef.current) {
      hudCountryRef.current.textContent = `${selectedCountry.name} (${selectedCountry.capital})`;
    }
    if (hudCoordsRef.current) {
      hudCoordsRef.current.textContent = `${Math.abs(selectedCountry.lat).toFixed(2)}° ${selectedCountry.lat >= 0 ? "N" : "S"}, ${Math.abs(selectedCountry.lng).toFixed(2)}° ${selectedCountry.lng >= 0 ? "E" : "W"}`;
    }
  }, [selectedCountry, flyToCoordinates]);

  // Main Three.js setup
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // 1. Scene with Deep Space Black Background
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x000000);
    sceneRef.current = scene;

    // 2. Camera
    const width = container.clientWidth || window.innerWidth;
    const height = container.clientHeight || window.innerHeight;
    const camera = new THREE.PerspectiveCamera(45, width / height, 1, 4000);
    camera.position.copy(latLonToVector3(25, 35, 270));
    cameraRef.current = camera;

    // 3. WebGL Renderer
    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      powerPreference: "high-performance",
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    container.innerHTML = "";
    container.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // 4. OrbitControls (Smooth mouse & phone touch controls)
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.rotateSpeed = 0.65;
    controls.zoomSpeed = 0.9;
    controls.enablePan = false;
    controls.minDistance = 118;
    controls.maxDistance = 650;
    controls.autoRotate = true;
    controls.autoRotateSpeed = 0.35;
    controlsRef.current = controls;

    // 5. Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.9);
    scene.add(ambientLight);

    const sunLight = new THREE.DirectionalLight(0xffffff, 1.4);
    sunLight.position.set(-300, 150, 300);
    scene.add(sunLight);

    // 6. Deep Space Stars (Visible crisp celestial starfield)
    const starCanvas = document.createElement("canvas");
    starCanvas.width = 16;
    starCanvas.height = 16;
    const starCtx = starCanvas.getContext("2d");
    if (starCtx) {
      starCtx.beginPath();
      starCtx.arc(8, 8, 7, 0, Math.PI * 2);
      starCtx.fillStyle = "#ffffff";
      starCtx.fill();
    }
    const starTexture = new THREE.CanvasTexture(starCanvas);

    // Layer 1: Background stars (4,000 stars)
    const starCount = 4000;
    const starGeo = new THREE.BufferGeometry();
    const starPositions = new Float32Array(starCount * 3);
    for (let i = 0; i < starCount; i++) {
      const r = 800 + Math.random() * 1200;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      starPositions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      starPositions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      starPositions[i * 3 + 2] = r * Math.cos(phi);
    }
    starGeo.setAttribute(
      "position",
      new THREE.BufferAttribute(starPositions, 3)
    );
    const starMaterial = new THREE.PointsMaterial({
      map: starTexture,
      color: 0xffffff,
      size: 2.2,
      sizeAttenuation: false,
      transparent: true,
      opacity: 0.85,
    });
    scene.add(new THREE.Points(starGeo, starMaterial));

    // Layer 2: Bright prominent stars / constellations (700 stars)
    const brightCount = 700;
    const brightGeo = new THREE.BufferGeometry();
    const brightPositions = new Float32Array(brightCount * 3);
    for (let i = 0; i < brightCount; i++) {
      const r = 700 + Math.random() * 900;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      brightPositions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      brightPositions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      brightPositions[i * 3 + 2] = r * Math.cos(phi);
    }
    brightGeo.setAttribute(
      "position",
      new THREE.BufferAttribute(brightPositions, 3)
    );
    const brightMaterial = new THREE.PointsMaterial({
      map: starTexture,
      color: 0xffffff,
      size: 3.5,
      sizeAttenuation: false,
      transparent: true,
      opacity: 0.95,
    });
    scene.add(new THREE.Points(brightGeo, brightMaterial));

    // 7. Earth Group
    const earthGroup = new THREE.Group();
    scene.add(earthGroup);
    earthGroupRef.current = earthGroup;

    // Build procedural fallback texture on canvas first so Earth is never black
    const canvasTex = document.createElement("canvas");
    canvasTex.width = 1024;
    canvasTex.height = 512;
    const ctx = canvasTex.getContext("2d");
    if (ctx) {
      // Solid neutral charcoal ocean (no navy, no gradients)
      ctx.fillStyle = "#18181b";
      ctx.fillRect(0, 0, 1024, 512);

      // Draw world continents onto texture
      ctx.fillStyle = "#27272a";
      ctx.strokeStyle = "#3f3f46";
      ctx.lineWidth = 1.5;

      for (const land of WORLD_LANDMASSES) {
        ctx.beginPath();
        for (let i = 0; i < land.coordinates.length; i++) {
          const [lon, lat] = land.coordinates[i];
          const px = ((lon + 180) / 360) * 1024;
          const py = ((90 - lat) / 180) * 512;
          if (i === 0) ctx.moveTo(px, py);
          else ctx.lineTo(px, py);
        }
        ctx.closePath();
        ctx.fill();
        ctx.stroke();
      }
    }
    const proceduralTexture = new THREE.CanvasTexture(canvasTex);

    // Base Earth Mesh (solid neutral specular, no navy)
    const earthMaterial = new THREE.MeshPhongMaterial({
      map: proceduralTexture,
      specular: new THREE.Color(0x27272a),
      shininess: 12,
      bumpScale: 1.0,
    });
    const earthMesh = new THREE.Mesh(
      new THREE.SphereGeometry(EARTH_RADIUS, 96, 96),
      earthMaterial
    );
    earthGroup.add(earthMesh);
    earthMeshRef.current = earthMesh;

    // Load High-Res NASA Textures from CDN
    const textureLoader = new THREE.TextureLoader();
    textureLoader.crossOrigin = "anonymous";
    textureLoader.load(
      "https://unpkg.com/three-globe/example/img/earth-blue-marble.jpg",
      (tex) => {
        earthMaterial.map = tex;
        earthMaterial.needsUpdate = true;
      }
    );
    textureLoader.load(
      "https://unpkg.com/three-globe/example/img/earth-topology.png",
      (tex) => {
        earthMaterial.bumpMap = tex;
        earthMaterial.needsUpdate = true;
      }
    );
    textureLoader.load(
      "https://unpkg.com/three-globe/example/img/earth-water.png",
      (tex) => {
        earthMaterial.specularMap = tex;
        earthMaterial.needsUpdate = true;
      }
    );

    // 8. Clouds Layer
    const cloudsMaterial = new THREE.MeshPhongMaterial({
      transparent: true,
      opacity: 0.32,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });
    const cloudsMesh = new THREE.Mesh(
      new THREE.SphereGeometry(EARTH_RADIUS * 1.01, 64, 64),
      cloudsMaterial
    );
    earthGroup.add(cloudsMesh);

    textureLoader.load(
      "https://unpkg.com/three-globe/example/img/earth-clouds.png",
      (tex) => {
        cloudsMaterial.map = tex;
        cloudsMaterial.needsUpdate = true;
      }
    );

    // 9. Graticule Lines (Parallels and Meridians - solid neutral lines, no gradients)
    const graticulePoints: THREE.Vector3[] = [];
    const rGrat = EARTH_RADIUS * 1.0025;
    for (let lat = -75; lat <= 75; lat += 15) {
      for (let lon = -180; lon < 180; lon += 5) {
        graticulePoints.push(
          latLonToVector3(lat, lon, rGrat),
          latLonToVector3(lat, lon + 5, rGrat)
        );
      }
    }
    for (let lon = -180; lon < 180; lon += 15) {
      for (let lat = -85; lat < 85; lat += 5) {
        graticulePoints.push(
          latLonToVector3(lat, lon, rGrat),
          latLonToVector3(lat + 5, lon, rGrat)
        );
      }
    }
    const graticuleMesh = new THREE.LineSegments(
      new THREE.BufferGeometry().setFromPoints(graticulePoints),
      new THREE.LineBasicMaterial({
        color: 0x3f3f46,
        transparent: true,
        opacity: 0.25,
      })
    );
    earthGroup.add(graticuleMesh);

    // 10. Animated Wind Streams (solid colors, no gradients)
    const windLinesGroup = new THREE.Group();
    earthGroup.add(windLinesGroup);
    windLinesGroupRef.current = windLinesGroup;

    const windParticles: {
      mesh: THREE.Mesh;
      curve: THREE.CatmullRomCurve3;
      progress: number;
    }[] = [];

    for (let i = 0; i < 36; i++) {
      const isNorthernJet = i % 3 === 0;
      const isSouthernJet = i % 3 === 1;
      const baseLat = isNorthernJet
        ? 42 + Math.sin(i * 1.5) * 8
        : isSouthernJet
        ? -46 + Math.cos(i * 1.3) * 7
        : -14 + (i % 5) * 6;
      const startLon = -180 + (i * 360) / 36;
      const pts: THREE.Vector3[] = [];

      for (let s = 0; s < 12; s++) {
        const waveAmp = isNorthernJet || isSouthernJet ? 5.5 : 2.0;
        const latPt = baseLat + Math.sin((startLon + s * 7.5) * 0.05) * waveAmp;
        const lonPt = startLon + s * 7.5;
        pts.push(latLonToVector3(latPt, lonPt, EARTH_RADIUS * 1.014));
      }

      const curve = new THREE.CatmullRomCurve3(pts);
      const streamColor = isNorthernJet || isSouthernJet ? 0x2563eb : 0x52525b;
      const line = new THREE.Line(
        new THREE.BufferGeometry().setFromPoints(curve.getPoints(24)),
        new THREE.LineBasicMaterial({
          color: streamColor,
          transparent: true,
          opacity: 0.45,
        })
      );
      windLinesGroup.add(line);

      const dot = new THREE.Mesh(
        new THREE.SphereGeometry(0.7, 8, 8),
        new THREE.MeshBasicMaterial({
          color: 0x60a5fa,
        })
      );
      windLinesGroup.add(dot);
      windParticles.push({ mesh: dot, curve, progress: Math.random() });
    }

    // 11. Country 3D Pins (Solid blue, no gradients)
    const pinsGroup = new THREE.Group();
    earthGroup.add(pinsGroup);
    pinsGroupRef.current = pinsGroup;

    const pinMeshes: THREE.Mesh[] = [];

    COUNTRIES.forEach((c) => {
      const pos = latLonToVector3(c.lat, c.lng, EARTH_RADIUS * 1.008);
      const pinMesh = new THREE.Mesh(
        new THREE.SphereGeometry(1.0, 16, 16),
        new THREE.MeshBasicMaterial({ color: 0x2563eb })
      );
      pinMesh.position.copy(pos);
      pinMesh.userData = { country: c };
      pinsGroup.add(pinMesh);
      pinMeshes.push(pinMesh);

      const ringMesh = new THREE.Mesh(
        new THREE.RingGeometry(1.2, 1.8, 16),
        new THREE.MeshBasicMaterial({
          color: 0x3b82f6,
          side: THREE.DoubleSide,
          transparent: true,
          opacity: 0.6,
        })
      );
      ringMesh.position.copy(pos);
      ringMesh.lookAt(pos.clone().multiplyScalar(2));
      pinsGroup.add(ringMesh);
    });

    // 13. Pointer Interactivity & Raycasting
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();
    let pointerDownPos = { x: 0, y: 0 };

    const onPointerDown = (e: PointerEvent) => {
      pointerDownPos = { x: e.clientX, y: e.clientY };
    };

    const onPointerMove = (e: PointerEvent) => {
      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(mouse, camera);
      const hits = raycaster.intersectObject(earthMesh);
      if (hits.length > 0) {
        const { lat, lon } = vector3ToLatLon(hits[0].point);
        if (hudCoordsRef.current) {
          hudCoordsRef.current.textContent = `${Math.abs(lat).toFixed(2)}° ${lat >= 0 ? "N" : "S"}, ${Math.abs(lon).toFixed(2)}° ${lon >= 0 ? "E" : "W"}`;
        }
      }
    };

    const onPointerUp = (e: PointerEvent) => {
      if (Math.hypot(e.clientX - pointerDownPos.x, e.clientY - pointerDownPos.y) > 6)
        return;

      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(mouse, camera);

      // 1. Check Pin hits
      const pinHits = raycaster.intersectObjects(pinMeshes);
      if (pinHits.length > 0) {
        const c = pinHits[0].object.userData.country as Country;
        if (c && onSelectCountry) {
          onSelectCountry(c);
        }
        return;
      }

      // 2. Check Earth hits
      const earthHits = raycaster.intersectObject(earthMesh);
      if (earthHits.length > 0) {
        const hitPoint = earthHits[0].point.clone().normalize();
        let closest: Country | null = null;
        let minDist = 0.65; // ~37 degrees angular radius

        for (const c of COUNTRIES) {
          const cPos = latLonToVector3(c.lat, c.lng, 1).normalize();
          const d = hitPoint.distanceTo(cPos);
          if (d < minDist) {
            minDist = d;
            closest = c;
          }
        }
        if (closest && onSelectCountry) {
          onSelectCountry(closest);
        }
      }
    };

    const dom = renderer.domElement;
    dom.addEventListener("pointerdown", onPointerDown);
    dom.addEventListener("pointermove", onPointerMove);
    dom.addEventListener("pointerup", onPointerUp);

    // Resize handler
    const onResize = () => {
      if (!container || !camera || !renderer) return;
      const w = container.clientWidth || window.innerWidth;
      const h = container.clientHeight || window.innerHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener("resize", onResize);

    // 14. Animation Loop
    let animationFrameId: number;

    const animate = (time: number) => {
      animationFrameId = requestAnimationFrame(animate);

      // Handle smooth camera fly-to tween
      if (tweenRef.current) {
        const tween = tweenRef.current;
        const progress = Math.min(1, (time - tween.startTime) / tween.duration);
        // Cubic easeInOut
        const ease =
          progress < 0.5
            ? 4 * progress * progress * progress
            : 1 - Math.pow(-2 * progress + 2, 3) / 2;

        camera.position.lerpVectors(tween.startPos, tween.endPos, ease);
        controls.target.set(0, 0, 0);

        if (progress >= 1) {
          tweenRef.current = null;
        }
      }

      // Slowly rotate clouds
      cloudsMesh.rotation.y += 0.0003;

      // Animate wind particles
      for (const p of windParticles) {
        p.progress = (p.progress + 0.004) % 1.0;
        const pt = p.curve.getPoint(p.progress);
        p.mesh.position.copy(pt);
      }

      controls.update();
      renderer.render(scene, camera);
    };

    animationFrameId = requestAnimationFrame(animate);

    // Cleanup
    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener("resize", onResize);
      dom.removeEventListener("pointerdown", onPointerDown);
      dom.removeEventListener("pointermove", onPointerMove);
      dom.removeEventListener("pointerup", onPointerUp);
      controls.dispose();
      renderer.dispose();
    };
  }, [latLonToVector3, vector3ToLatLon, onSelectCountry]);

  return (
    <div className="relative w-full h-full overflow-hidden select-none bg-[#000000]">
      {/* 3D WebGL Canvas Container */}
      <div ref={containerRef} className="absolute inset-0 w-full h-full cursor-grab active:cursor-grabbing" />

      {/* Real-time HUD (Coordinates & Country - Solid colors, no navy, no gradients) */}
      <div className="absolute bottom-4 left-4 z-10 pointer-events-none">
        <div className="bg-[#18181b] border border-[#27272a] px-3 py-1.5 rounded-lg shadow-lg flex items-center gap-2.5 text-xs">
          <span className="w-2 h-2 rounded-full bg-[#10b981]"></span>
          <span ref={hudCoordsRef} className="font-mono text-[#60a5fa] font-bold text-[11px]">
            31.95° N, 35.23° E
          </span>
          <div className="h-3.5 w-px bg-[#3f3f46]"></div>
          <span ref={hudCountryRef} className="font-bold text-[#f4f4f5] text-[11px] truncate max-w-[200px]">
            Palestine (Jerusalem)
          </span>
        </div>
      </div>
    </div>
  );
}
