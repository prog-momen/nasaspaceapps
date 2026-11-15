"use client";

import React, { useEffect, useRef, useState, useCallback } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { COUNTRIES, Country } from "../data/countries";
import { WORLD_LANDMASSES } from "../data/worldGeo";

interface ThreeEarthProps {
  onSelectCountry?: (country: Country) => void;
  selectedCountry?: Country | null;
}

const EARTH_RADIUS = 100;

export type EnvLayer = "natural" | "temp" | "water" | "winds" | "veg" | "fires";

// Helper to get country flag emoji from code2
function getCountryFlag(code2?: string): string {
  if (!code2 || code2.length !== 2) return "🌍";
  const codePoints = code2
    .toUpperCase()
    .split("")
    .map((char) => 127397 + char.charCodeAt(0));
  return String.fromCodePoint(...codePoints);
}

// Color scale metadata for scientific layers (matching NASA EarthScope reference)
const SCALE_META: Record<
  EnvLayer,
  {
    title: string;
    src: string;
    grad: string;
    min: string;
    mid: string;
    max: string;
  } | null
> = {
  natural: null,
  temp: {
    title: "Surface Temp Anomaly (°C)",
    src: "Illustrative pattern - not live data",
    grad: "linear-gradient(90deg, #1a104c, #2b5c8f, #48a9b0, #87c576, #f5e98f, #f39c38, #d13b28, #701428)",
    min: "-20°C",
    mid: "+22°C",
    max: "+48°C",
  },
  water: {
    title: "Precipitable Water & Moisture (mm)",
    src: "Illustrative pattern - not live data",
    grad: "linear-gradient(90deg, #0a183c, #1862a8, #16afb4, #48d741, #fade19, #e11e19)",
    min: "0 mm (Arid)",
    mid: "35 mm",
    max: "75+ mm (Storms)",
  },
  winds: {
    title: "Wind Speed & Jet Streams",
    src: "Illustrative pattern - not live data",
    grad: "linear-gradient(90deg, #0a1223, #19559b, #38bdf8, #eab308, #ef4444, #d946ef)",
    min: "0 m/s",
    mid: "14 m/s (Trades)",
    max: "40+ m/s (Jet Stream)",
  },
  veg: {
    title: "Vegetation Index (NDVI)",
    src: "Illustrative pattern - not live data",
    grad: "linear-gradient(90deg, #e1cda5, #d2b47d, #b9bc5f, #78b937, #2d8c26, #0a4b18)",
    min: "0.05 Desert",
    mid: "0.45 Savanna",
    max: "0.92 Rainforest",
  },
  fires: {
    title: "Active Fire Hotspots (FIRMS)",
    src: "Illustrative pattern - not live data",
    grad: "linear-gradient(90deg, #060a16, #7f1d1d, #ea580c, #facc15, #ffffff)",
    min: "Calm",
    mid: "Thermal Anomaly",
    max: "Active Blaze 🔥",
  },
};

export default function ThreeEarth({
  onSelectCountry,
  selectedCountry,
}: ThreeEarthProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const labelsContainerRef = useRef<HTMLDivElement | null>(null);

  // Keep references to handlers so main scene setup never tears down on selection change
  const onSelectCountryRef = useRef(onSelectCountry);
  const selectedCountryRef = useRef(selectedCountry);

  useEffect(() => {
    onSelectCountryRef.current = onSelectCountry;
    selectedCountryRef.current = selectedCountry;
  }, [onSelectCountry, selectedCountry]);

  // References across render frames
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const earthGroupRef = useRef<THREE.Group | null>(null);
  const earthMeshRef = useRef<THREE.Mesh | null>(null);
  const cloudsMeshRef = useRef<THREE.Mesh | null>(null);
  const bordersMeshRef = useRef<THREE.LineSegments | null>(null);
  const graticuleMeshRef = useRef<THREE.LineSegments | null>(null);
  const windLinesGroupRef = useRef<THREE.Group | null>(null);
  const envOverlayMeshRef = useRef<THREE.Mesh | null>(null);
  const highlightedCountryMeshRef = useRef<THREE.LineSegments | null>(null);
  const selectedMarkerGroupRef = useRef<THREE.Group | null>(null);
  const reticleRingRef = useRef<THREE.Mesh | null>(null);
  const beaconMeshRef = useRef<THREE.Mesh | null>(null);
  const spawnRippleRef = useRef<
    ((point: THREE.Vector3, color?: number) => void) | null
  >(null);

  // Interactive Layer States
  const [activeEnvLayer, setActiveEnvLayer] = useState<EnvLayer>("natural");
  const [showClouds, setShowClouds] = useState(true);
  const [showBorders, setShowBorders] = useState(true);
  const [showGraticule, setShowGraticule] = useState(false);
  const [autoRotate, setAutoRotate] = useState(true);

  // Camera tween ref
  const tweenRef = useRef<{
    startPos: THREE.Vector3;
    endPos: THREE.Vector3;
    startTime: number;
    duration: number;
  } | null>(null);

  // Active pin objects tracked for screen-space 2D badge projection
  const activePinsRef = useRef<
    {
      country: Country;
      worldPos: THREE.Vector3;
      pinMesh: THREE.Mesh;
      ringMesh: THREE.Mesh;
      element: HTMLDivElement;
    }[]
  >([]);

  // HUD DOM refs for 60fps real-time updates
  const hudCoordsRef = useRef<HTMLSpanElement | null>(null);
  const hudCountryRef = useRef<HTMLSpanElement | null>(null);

  // Textures and Canvas references for environmental layers
  const envTexturesRef = useRef<Record<EnvLayer, THREE.CanvasTexture | null>>({
    natural: null,
    temp: null,
    water: null,
    winds: null,
    veg: null,
    fires: null,
  });
  const baseDayTexRef = useRef<THREE.Texture | null>(null);

  // Lat/Lon to 3D Cartesian coordinates
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

  // Vector3 to Lat/Lon
  const vector3ToLatLon = useCallback((vec: THREE.Vector3) => {
    const normalized = vec.clone().normalize();
    const lat = 90 - (Math.acos(normalized.y) * 180) / Math.PI;
    const lon =
      (Math.atan2(normalized.z, -normalized.x) * 180) / Math.PI - 180;
    return {
      lat,
      lon: lon < -180 ? lon + 360 : lon > 180 ? lon - 360 : lon,
    };
  }, []);

  // Smooth camera fly-to tween with cubic easing
  const flyToCoordinates = useCallback(
    (lat: number, lon: number, targetDistance = 205) => {
      if (!cameraRef.current || !controlsRef.current) return;
      controlsRef.current.autoRotate = false;
      setAutoRotate(false);

      const startPos = cameraRef.current.position.clone();
      const endPos = latLonToVector3(lat, lon, targetDistance);

      tweenRef.current = {
        startPos,
        endPos,
        startTime: performance.now(),
        duration: 1200,
      };
    },
    [latLonToVector3]
  );

  // Helper to highlight a country's border in glowing golden yellow 0xfacc15
  const highlightCountryBorder = useCallback(
    (country: Country) => {
      const earthGroup = earthGroupRef.current;
      if (!earthGroup) return;

      if (highlightedCountryMeshRef.current) {
        earthGroup.remove(highlightedCountryMeshRef.current);
        highlightedCountryMeshRef.current.geometry.dispose();
        highlightedCountryMeshRef.current = null;
      }

      // Find matching landmass polygon or build fine radius boundary
      const matching = WORLD_LANDMASSES.find(
        (m) =>
          m.name.toLowerCase() === country.name.toLowerCase() ||
          (country.name === "Palestine" && m.name === "Middle East") ||
          (country.name === "United States" && m.name === "North America")
      );

      const points: THREE.Vector3[] = [];
      const r = EARTH_RADIUS * 1.006;

      if (matching && matching.coordinates.length > 5) {
        for (let i = 0; i < matching.coordinates.length - 1; i++) {
          const [lon1, lat1] = matching.coordinates[i];
          const [lon2, lat2] = matching.coordinates[i + 1];
          points.push(
            latLonToVector3(lat1, lon1, r),
            latLonToVector3(lat2, lon2, r)
          );
        }
      } else {
        // High-precision circular boundary around country coordinates
        const radiusDeg = 3.8;
        const numSteps = 64;
        for (let i = 0; i < numSteps; i++) {
          const a1 = (i / numSteps) * Math.PI * 2;
          const a2 = ((i + 1) / numSteps) * Math.PI * 2;
          const lat1 = country.lat + Math.sin(a1) * (radiusDeg * 0.7);
          const lon1 = country.lng + Math.cos(a1) * radiusDeg;
          const lat2 = country.lat + Math.sin(a2) * (radiusDeg * 0.7);
          const lon2 = country.lng + Math.cos(a2) * radiusDeg;
          points.push(
            latLonToVector3(lat1, lon1, r),
            latLonToVector3(lat2, lon2, r)
          );
        }
      }

      const hlMesh = new THREE.LineSegments(
        new THREE.BufferGeometry().setFromPoints(points),
        new THREE.LineBasicMaterial({
          color: 0xfacc15,
          transparent: true,
          opacity: 0.95,
        })
      );
      earthGroup.add(hlMesh);
      highlightedCountryMeshRef.current = hlMesh;
    },
    [latLonToVector3]
  );

  // Sync selected country: fly camera, spawn shockwave, update 3D pins and badges
  useEffect(() => {
    if (!selectedCountry) return;

    // Fly camera smoothly to target country
    flyToCoordinates(selectedCountry.lat, selectedCountry.lng, 205);

    // Update real-time HUD
    if (hudCountryRef.current) {
      hudCountryRef.current.textContent = `${selectedCountry.name} (${selectedCountry.capital})`;
    }
    if (hudCoordsRef.current) {
      hudCoordsRef.current.textContent = `${Math.abs(selectedCountry.lat).toFixed(
        2
      )}° ${selectedCountry.lat >= 0 ? "N" : "S"}, ${Math.abs(
        selectedCountry.lng
      ).toFixed(2)}° ${selectedCountry.lng >= 0 ? "E" : "W"}`;
    }

    const pos = latLonToVector3(
      selectedCountry.lat,
      selectedCountry.lng,
      EARTH_RADIUS * 1.008
    );

    // Spawn tactile golden shockwave ripple
    if (spawnRippleRef.current) {
      spawnRippleRef.current(pos, 0xfacc15);
    }

    // Highlight golden boundary
    highlightCountryBorder(selectedCountry);

    // Update 3D Beacon and Reticle Marker
    const markerGroup = selectedMarkerGroupRef.current;
    if (markerGroup) {
      while (markerGroup.children.length > 0) {
        const obj = markerGroup.children[0];
        markerGroup.remove(obj);
      }

      // Central glowing gold node
      const pinMesh = new THREE.Mesh(
        new THREE.SphereGeometry(1.4, 16, 16),
        new THREE.MeshBasicMaterial({ color: 0xfacc15 })
      );
      pinMesh.position.copy(pos);
      markerGroup.add(pinMesh);

      // Rotating Inner Radar Reticle
      const reticleRing = new THREE.Mesh(
        new THREE.RingGeometry(1.8, 3.2, 32),
        new THREE.MeshBasicMaterial({
          color: 0xf59e0b,
          side: THREE.DoubleSide,
          transparent: true,
          opacity: 0.9,
          depthWrite: false,
        })
      );
      reticleRing.position.copy(pos);
      reticleRing.lookAt(pos.clone().multiplyScalar(2));
      markerGroup.add(reticleRing);
      reticleRingRef.current = reticleRing;

      // Outer Radar Pulse Ring
      const outerRing = new THREE.Mesh(
        new THREE.RingGeometry(3.6, 4.4, 32),
        new THREE.MeshBasicMaterial({
          color: 0x38bdf8,
          side: THREE.DoubleSide,
          transparent: true,
          opacity: 0.7,
          depthWrite: false,
        })
      );
      outerRing.position.copy(pos);
      outerRing.lookAt(pos.clone().multiplyScalar(2));
      markerGroup.add(outerRing);

      // Vertical Laser Scanner Beacon Light Pillar
      const beaconHeight = 22;
      const beaconGeo = new THREE.CylinderGeometry(
        0.35,
        1.3,
        beaconHeight,
        16,
        1,
        true
      );
      beaconGeo.translate(0, beaconHeight / 2, 0);
      beaconGeo.rotateX(Math.PI / 2);
      const beaconMesh = new THREE.Mesh(
        beaconGeo,
        new THREE.MeshBasicMaterial({
          color: 0xfacc15,
          transparent: true,
          opacity: 0.65,
          blending: THREE.AdditiveBlending,
          side: THREE.DoubleSide,
          depthWrite: false,
        })
      );
      beaconMesh.position.copy(pos);
      beaconMesh.lookAt(pos.clone().multiplyScalar(2));
      markerGroup.add(beaconMesh);
      beaconMeshRef.current = beaconMesh;
    }

    // Update styling of 2D Projected Badges & 3D Pins
    activePinsRef.current.forEach((item) => {
      const isSelected = item.country.name === selectedCountry.name;
      const colHex = isSelected ? 0xfacc15 : 0x38bdf8;

      (item.pinMesh.material as THREE.MeshBasicMaterial).color.setHex(colHex);
      item.pinMesh.scale.setScalar(isSelected ? 1.35 : 1.0);
      (item.ringMesh.material as THREE.MeshBasicMaterial).color.setHex(colHex);

      if (isSelected) {
        item.element.classList.add("selected-pin");
      } else {
        item.element.classList.remove("selected-pin");
      }
    });
  }, [
    selectedCountry,
    flyToCoordinates,
    latLonToVector3,
    highlightCountryBorder,
  ]);

  // Handle Layer Switch (Natural, Temp, Water, Winds, Veg, Fires)
  const handleSetEnvLayer = (layer: EnvLayer) => {
    setActiveEnvLayer(layer);

    if (windLinesGroupRef.current) {
      windLinesGroupRef.current.visible = layer === "winds";
    }

    const overlayMesh = envOverlayMeshRef.current;
    const earthMesh = earthMeshRef.current;

    if (layer === "natural") {
      if (overlayMesh) overlayMesh.visible = false;
      if (earthMesh && baseDayTexRef.current) {
        (earthMesh.material as THREE.MeshPhongMaterial).map =
          baseDayTexRef.current;
        (earthMesh.material as THREE.MeshPhongMaterial).color.setHex(0xffffff);
        (earthMesh.material as THREE.MeshPhongMaterial).needsUpdate = true;
      }
    } else {
      if (overlayMesh && envTexturesRef.current[layer]) {
        overlayMesh.visible = true;
        (overlayMesh.material as THREE.MeshPhongMaterial).map =
          envTexturesRef.current[layer];
        (overlayMesh.material as THREE.MeshPhongMaterial).opacity =
          layer === "fires" ? 0.95 : 0.82;
        (overlayMesh.material as THREE.MeshPhongMaterial).needsUpdate = true;
      }

      if (earthMesh) {
        if (layer === "fires") {
          (earthMesh.material as THREE.MeshPhongMaterial).color.setHex(0x94a3b8);
        } else {
          (earthMesh.material as THREE.MeshPhongMaterial).color.setHex(0xffffff);
        }
      }
    }
  };

  // Toggle Auto-Rotate
  const handleToggleAutoRotate = () => {
    if (!controlsRef.current) return;
    const next = !controlsRef.current.autoRotate;
    controlsRef.current.autoRotate = next;
    setAutoRotate(next);
  };

  // Reset to default Levant / Palestine View
  const handleResetLevantView = () => {
    flyToCoordinates(28, 35, 265);
  };

  // Main Three.js Scene Setup
  useEffect(() => {
    const container = containerRef.current;
    const labelsContainer = labelsContainerRef.current;
    if (!container || !labelsContainer) return;

    // 1. Scene with Deep Space Black Background
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x000000);
    sceneRef.current = scene;

    // 2. Camera: 45° FOV, perspective view centered on Levant / Middle East
    const width = container.clientWidth || window.innerWidth;
    const height = container.clientHeight || window.innerHeight;
    const camera = new THREE.PerspectiveCamera(45, width / height, 1, 4000);
    camera.position.copy(latLonToVector3(28, 35, 265));
    cameraRef.current = camera;

    // 3. WebGL Renderer with High-Performance Settings
    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      powerPreference: "high-performance",
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    container.innerHTML = "";
    container.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // 4. OrbitControls: Smooth damping, controlled zoom limits, auto-rotate 0.35
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.rotateSpeed = 0.65;
    controls.zoomSpeed = 0.9;
    controls.enablePan = false;
    controls.minDistance = 118;
    controls.maxDistance = 620;
    controls.autoRotate = true;
    controls.autoRotateSpeed = 0.35;
    controlsRef.current = controls;

    // 5. Lighting: Soft ambient 0x93c5fd (0.78) + Directional Sun 0xffffff (1.35) at (-300, 120, 300)
    const ambientLight = new THREE.AmbientLight(0x93c5fd, 0.78);
    scene.add(ambientLight);

    const sunLight = new THREE.DirectionalLight(0xffffff, 1.35);
    sunLight.position.set(-300, 120, 300);
    scene.add(sunLight);

    // 6. Deep Space Starfield (2,600 stars from r=900 to 2,300, color 0xe0f2fe)
    const starCount = 2600;
    const starGeo = new THREE.BufferGeometry();
    const starPositions = new Float32Array(starCount * 3);
    for (let i = 0; i < starCount; i++) {
      const r = 900 + Math.random() * 1400;
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
      color: 0xe0f2fe,
      size: 2.0,
      transparent: true,
      opacity: 0.8,
    });
    scene.add(new THREE.Points(starGeo, starMaterial));

    // 7. Earth Group
    const earthGroup = new THREE.Group();
    scene.add(earthGroup);
    earthGroupRef.current = earthGroup;

    // Base Earth Mesh (SphereGeometry EARTH_RADIUS, 96, 96)
    const earthMaterial = new THREE.MeshPhongMaterial({
      color: 0xffffff,
      specular: new THREE.Color(0x1e3a5f),
      shininess: 14,
      bumpScale: 1.1,
    });
    const earthMesh = new THREE.Mesh(
      new THREE.SphereGeometry(EARTH_RADIUS, 96, 96),
      earthMaterial
    );
    earthGroup.add(earthMesh);
    earthMeshRef.current = earthMesh;

    // Environmental Overlay Mesh (r = EARTH_RADIUS * 1.002)
    const envOverlayMaterial = new THREE.MeshPhongMaterial({
      transparent: true,
      opacity: 0.82,
      depthWrite: false,
    });
    const envOverlayMesh = new THREE.Mesh(
      new THREE.SphereGeometry(EARTH_RADIUS * 1.002, 96, 96),
      envOverlayMaterial
    );
    envOverlayMesh.visible = false;
    earthGroup.add(envOverlayMesh);
    envOverlayMeshRef.current = envOverlayMesh;

    // Clouds Layer (SphereGeometry EARTH_RADIUS * 1.009, 64, 64)
    const cloudsMaterial = new THREE.MeshPhongMaterial({
      transparent: true,
      opacity: 0.34,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });
    const cloudsMesh = new THREE.Mesh(
      new THREE.SphereGeometry(EARTH_RADIUS * 1.009, 64, 64),
      cloudsMaterial
    );
    earthGroup.add(cloudsMesh);
    cloudsMeshRef.current = cloudsMesh;

    // Atmosphere Glow Shader (SphereGeometry EARTH_RADIUS * 1.12, 64, 64)
    const atmosphereMaterial = new THREE.ShaderMaterial({
      vertexShader: `
        varying vec3 vNormal;
        void main() {
          vNormal = normalize(normalMatrix * normal);
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        varying vec3 vNormal;
        void main() {
          float intensity = pow(0.62 - dot(vNormal, vec3(0.0, 0.0, 1.0)), 2.8);
          gl_FragColor = vec4(0.22, 0.68, 1.0, 1.0) * intensity * 1.15;
        }
      `,
      blending: THREE.AdditiveBlending,
      side: THREE.BackSide,
      transparent: true,
      depthWrite: false,
    });
    const atmosphereMesh = new THREE.Mesh(
      new THREE.SphereGeometry(EARTH_RADIUS * 1.12, 64, 64),
      atmosphereMaterial
    );
    scene.add(atmosphereMesh);

    // 8. Graticule Lines (Parallels and Meridians at r = EARTH_RADIUS * 1.0025, color 0x38bdf8)
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
        color: 0x38bdf8,
        transparent: true,
        opacity: 0.22,
      })
    );
    graticuleMesh.visible = false;
    earthGroup.add(graticuleMesh);
    graticuleMeshRef.current = graticuleMesh;

    // 9. Continental and Regional Borders (r = EARTH_RADIUS * 1.003, color 0x38bdf8)
    const borderPoints: THREE.Vector3[] = [];
    const rBorder = EARTH_RADIUS * 1.003;
    for (const land of WORLD_LANDMASSES) {
      for (let i = 0; i < land.coordinates.length - 1; i++) {
        const [lon1, lat1] = land.coordinates[i];
        const [lon2, lat2] = land.coordinates[i + 1];
        borderPoints.push(
          latLonToVector3(lat1, lon1, rBorder),
          latLonToVector3(lat2, lon2, rBorder)
        );
      }
    }
    const bordersLineMesh = new THREE.LineSegments(
      new THREE.BufferGeometry().setFromPoints(borderPoints),
      new THREE.LineBasicMaterial({
        color: 0x38bdf8,
        transparent: true,
        opacity: 0.4,
      })
    );
    earthGroup.add(bordersLineMesh);
    bordersMeshRef.current = bordersLineMesh;

    // 10. Animated Wind Jet Streams & Trade Wind Curves with Particles
    const windLinesGroup = new THREE.Group();
    windLinesGroup.visible = false;
    earthGroup.add(windLinesGroup);
    windLinesGroupRef.current = windLinesGroup;

    interface WindParticle {
      mesh: THREE.Mesh;
      curve: THREE.CatmullRomCurve3;
      progress: number;
    }
    const windParticles: WindParticle[] = [];

    for (let i = 0; i < 48; i++) {
      const isNorthernJet = i % 3 === 0;
      const isSouthernJet = i % 3 === 1;
      const baseLat = isNorthernJet
        ? 42 + Math.sin(i * 1.5) * 8
        : isSouthernJet
        ? -46 + Math.cos(i * 1.3) * 7
        : -14 + (i % 5) * 6;
      const startLon = -180 + (i * 360) / 48;
      const pts: THREE.Vector3[] = [];

      for (let s = 0; s < 12; s++) {
        const waveAmp = isNorthernJet || isSouthernJet ? 5.5 : 2.0;
        const latPt = baseLat + Math.sin((startLon + s * 7.5) * 0.05) * waveAmp;
        const lonPt = startLon + s * 7.5;
        pts.push(latLonToVector3(latPt, lonPt, EARTH_RADIUS * 1.014));
      }

      const curve = new THREE.CatmullRomCurve3(pts);
      const streamColor = isNorthernJet || isSouthernJet ? 0x38bdf8 : 0x0ea5e9;
      const line = new THREE.Line(
        new THREE.BufferGeometry().setFromPoints(curve.getPoints(32)),
        new THREE.LineBasicMaterial({
          color: streamColor,
          transparent: true,
          opacity: 0.55,
        })
      );
      windLinesGroup.add(line);

      const dot = new THREE.Mesh(
        new THREE.SphereGeometry(0.75, 8, 8),
        new THREE.MeshBasicMaterial({
          color: isNorthernJet || isSouthernJet ? 0xfacc15 : 0xe0f2fe,
        })
      );
      windLinesGroup.add(dot);
      windParticles.push({ mesh: dot, curve, progress: Math.random() });
    }

    // 11. Load High-Res NASA Earth Textures
    const textureLoader = new THREE.TextureLoader();
    textureLoader.crossOrigin = "anonymous";

    textureLoader.load(
      "https://unpkg.com/three-globe/example/img/earth-blue-marble.jpg",
      (tex) => {
        baseDayTexRef.current = tex;
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
    textureLoader.load(
      "https://unpkg.com/three-globe/example/img/earth-clouds.png",
      (tex) => {
        cloudsMaterial.map = tex;
        cloudsMaterial.needsUpdate = true;
      }
    );

    // 12. Build Photorealistic Geophysical Raster Synthesis Textures
    const buildEnvTextures = () => {
      const w = 512;
      const h = 256;

      const createLayerCanvas = (mode: EnvLayer) => {
        const canvas = document.createElement("canvas");
        canvas.width = w;
        canvas.height = h;
        const ctx = canvas.getContext("2d");
        if (!ctx) return null;

        const imgData = ctx.createImageData(w, h);
        const data = imgData.data;

        if (mode === "fires") {
          for (let i = 0; i < data.length; i += 4) {
            data[i] = 6;
            data[i + 1] = 10;
            data[i + 2] = 22;
            data[i + 3] = 145;
          }
          ctx.putImageData(imgData, 0, 0);

          // Wildfire Hotspots (NASA FIRMS)
          const hotspots = [
            { lat: 32.3, lon: 35.8, r: 16 }, // Palestine/Levant
            { lat: 39.5, lon: -121.1, r: 24 }, // California
            { lat: -9.8, lon: -56.1, r: 28 }, // Amazon
            { lat: 8.5, lon: 18.2, r: 26 }, // Sub-Sahel
            { lat: -33.8, lon: 150.2, r: 25 }, // Australia
            { lat: 38.2, lon: 23.7, r: 18 }, // Greece
          ];

          hotspots.forEach((hp) => {
            const cx = ((hp.lon + 180) / 360) * w;
            const cy = ((90 - hp.lat) / 180) * h;
            const grad = ctx.createRadialGradient(
              cx,
              cy,
              0,
              cx,
              cy,
              hp.r * 1.6
            );
            grad.addColorStop(0, "#ffffff");
            grad.addColorStop(0.2, "#fef08a");
            grad.addColorStop(0.5, "#f97316");
            grad.addColorStop(1, "rgba(220, 38, 38, 0)");
            ctx.fillStyle = grad;
            ctx.beginPath();
            ctx.arc(cx, cy, hp.r * 1.6, 0, Math.PI * 2);
            ctx.fill();
          });
        } else {
          for (let y = 0; y < h; y++) {
            const lat = 90 - (y / h) * 180;
            const absLat = Math.abs(lat);

            for (let x = 0; x < w; x++) {
              const lon = (x / w) * 360 - 180;
              const idx = (y * w + x) * 4;

              if (mode === "temp") {
                const isSahara = lat > 14 && lat < 34 && lon > -16 && lon < 72;
                const solar = Math.pow(Math.cos((lat * Math.PI) / 180), 0.85) + (isSahara ? 0.22 : 0);
                const r = Math.min(255, Math.round(solar * 240 + 20));
                const g = Math.min(255, Math.round(solar * 150 + 10));
                const b = Math.min(255, Math.round((1 - Math.min(1, solar)) * 220 + 20));
                data[idx] = r;
                data[idx + 1] = g;
                data[idx + 2] = b;
                data[idx + 3] = 195;
              } else if (mode === "water") {
                const itcz = Math.exp(-Math.pow((lat - 4) / 14, 2));
                data[idx] = 16;
                data[idx + 1] = Math.round(98 + itcz * 150);
                data[idx + 2] = Math.round(180 + itcz * 75);
                data[idx + 3] = Math.round(120 + itcz * 120);
              } else if (mode === "winds") {
                const jet = Math.exp(-Math.pow((absLat - 48) / 12, 2));
                data[idx] = Math.round(25 + jet * 220);
                data[idx + 1] = Math.round(189 - jet * 80);
                data[idx + 2] = Math.round(248);
                data[idx + 3] = Math.round(110 + jet * 135);
              } else if (mode === "veg") {
                const v = Math.max(0, 0.7 - (absLat / 90) * 0.8);
                data[idx] = Math.round(120 - v * 90);
                data[idx + 1] = Math.round(140 + v * 100);
                data[idx + 2] = Math.round(40);
                data[idx + 3] = Math.round(v * 210);
              }
            }
          }
          ctx.putImageData(imgData, 0, 0);
        }

        const tex = new THREE.CanvasTexture(canvas);
        return tex;
      };

      envTexturesRef.current.temp = createLayerCanvas("temp");
      envTexturesRef.current.water = createLayerCanvas("water");
      envTexturesRef.current.winds = createLayerCanvas("winds");
      envTexturesRef.current.veg = createLayerCanvas("veg");
      envTexturesRef.current.fires = createLayerCanvas("fires");
    };

    buildEnvTextures();

    // 13. Dynamic Selected Region Marker Group (Reticle + Beacon + Node)
    const selectedMarkerGroup = new THREE.Group();
    earthGroup.add(selectedMarkerGroup);
    selectedMarkerGroupRef.current = selectedMarkerGroup;

    // 14. 3D Pins & Projected 2D Badges (#labels-container)
    const pinsGroup = new THREE.Group();
    earthGroup.add(pinsGroup);
    labelsContainer.innerHTML = "";
    activePinsRef.current = [];

    COUNTRIES.forEach((c) => {
      const pos = latLonToVector3(c.lat, c.lng, EARTH_RADIUS * 1.008);
      const isSelected = selectedCountryRef.current?.name === c.name;
      const colorHex = isSelected ? 0xfacc15 : 0x38bdf8;

      // 3D Pin Sphere
      const pinMesh = new THREE.Mesh(
        new THREE.SphereGeometry(isSelected ? 1.35 : 1.0, 16, 16),
        new THREE.MeshBasicMaterial({ color: colorHex })
      );
      pinMesh.position.copy(pos);
      pinsGroup.add(pinMesh);

      // 3D Ring Mesh looking outward
      const ringMesh = new THREE.Mesh(
        new THREE.RingGeometry(1.4, 2.2, 24),
        new THREE.MeshBasicMaterial({
          color: colorHex,
          side: THREE.DoubleSide,
          transparent: true,
          opacity: 0.75,
        })
      );
      ringMesh.position.copy(pos);
      ringMesh.lookAt(pos.clone().multiplyScalar(2));
      pinsGroup.add(ringMesh);

      // 2D Projected DOM Badge element
      const el = document.createElement("div");
      el.className = `globe-label ${isSelected ? "selected-pin" : ""}`;
      el.innerHTML = `
        <div class="globe-label-badge">
          <span>${getCountryFlag(c.code2)}</span>
          <span>${c.name}</span>
        </div>
      `;
      el.onclick = (e) => {
        e.stopPropagation();
        if (onSelectCountryRef.current) onSelectCountryRef.current(c);
      };
      labelsContainer.appendChild(el);

      activePinsRef.current.push({
        country: c,
        worldPos: pos,
        pinMesh,
        ringMesh,
        element: el,
      });
    });

    // 15. Tactile Shockwave Ripple System on Contact
    interface ActiveRipple {
      group: THREE.Group;
      rings: THREE.Mesh[];
      startTime: number;
      duration: number;
    }
    const activeRipples: ActiveRipple[] = [];

    const spawnContactRipple = (point: THREE.Vector3, color = 0xfacc15) => {
      const normPos = point
        .clone()
        .normalize()
        .multiplyScalar(EARTH_RADIUS * 1.006);
      const rippleGroup = new THREE.Group();
      rippleGroup.position.copy(normPos);
      rippleGroup.lookAt(normPos.clone().multiplyScalar(2));

      const ring1 = new THREE.Mesh(
        new THREE.RingGeometry(0.8, 1.8, 32),
        new THREE.MeshBasicMaterial({
          color,
          side: THREE.DoubleSide,
          transparent: true,
          opacity: 0.95,
          depthWrite: false,
        })
      );
      const ring2 = new THREE.Mesh(
        new THREE.RingGeometry(2.2, 3.2, 32),
        new THREE.MeshBasicMaterial({
          color: 0x38bdf8,
          side: THREE.DoubleSide,
          transparent: true,
          opacity: 0.8,
          depthWrite: false,
        })
      );
      const ring3 = new THREE.Mesh(
        new THREE.RingGeometry(3.8, 4.6, 32),
        new THREE.MeshBasicMaterial({
          color: 0xffffff,
          side: THREE.DoubleSide,
          transparent: true,
          opacity: 0.6,
          depthWrite: false,
        })
      );

      rippleGroup.add(ring1);
      rippleGroup.add(ring2);
      rippleGroup.add(ring3);
      earthGroup.add(rippleGroup);

      activeRipples.push({
        group: rippleGroup,
        rings: [ring1, ring2, ring3],
        startTime: performance.now(),
        duration: 1100,
      });
    };

    spawnRippleRef.current = spawnContactRipple;

    // 16. Pointer Events and Raycasting
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();
    let pointerDownPos = { x: 0, y: 0 };

    const onPointerDown = (e: PointerEvent) => {
      pointerDownPos = { x: e.clientX, y: e.clientY };

      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(mouse, camera);
      const hits = raycaster.intersectObject(earthMesh);
      if (hits.length > 0) {
        spawnContactRipple(hits[0].point, 0x38bdf8);
      }
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
          hudCoordsRef.current.textContent = `${Math.abs(lat).toFixed(2)}° ${
            lat >= 0 ? "N" : "S"
          }, ${Math.abs(lon).toFixed(2)}° ${lon >= 0 ? "E" : "W"}`;
        }
      }
    };

    const onPointerUp = (e: PointerEvent) => {
      if (
        Math.hypot(e.clientX - pointerDownPos.x, e.clientY - pointerDownPos.y) >
        6
      )
        return;

      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(mouse, camera);

      // Check pin hits
      const pinHits = raycaster.intersectObjects(
        activePinsRef.current.map((p) => p.pinMesh)
      );
      if (pinHits.length > 0) {
        const found = activePinsRef.current.find(
          (p) => p.pinMesh === pinHits[0].object
        );
        if (found && onSelectCountryRef.current) {
          onSelectCountryRef.current(found.country);
          return;
        }
      }

      // Check Earth surface hit (supports picking ANY arbitrary point/grid cell on Earth)
      const earthHits = raycaster.intersectObject(earthMesh);
      if (earthHits.length > 0) {
        const hitPoint = earthHits[0].point;
        spawnContactRipple(hitPoint, 0xfacc15);

        const { lat, lon } = vector3ToLatLon(hitPoint);
        const normHit = hitPoint.clone().normalize();
        let closest: Country | null = null;
        let minDist = 0.09; // Tight threshold (~5 degrees) for snapping to a known country marker

        for (const c of COUNTRIES) {
          const cPos = latLonToVector3(c.lat, c.lng, 1).normalize();
          const d = normHit.distanceTo(cPos);
          if (d < minDist) {
            minDist = d;
            closest = c;
          }
        }

        if (closest && onSelectCountryRef.current) {
          onSelectCountryRef.current(closest);
        } else if (onSelectCountryRef.current) {
          // Select ANY arbitrary point or ocean/land coordinate as a NASA POWER 0.5° Grid Cell
          const latRounded = Math.round(lat * 10) / 10;
          const lonRounded = Math.round(lon * 10) / 10;
          const latStr = `${Math.abs(latRounded).toFixed(1)}°${latRounded >= 0 ? "N" : "S"}`;
          const lonStr = `${Math.abs(lonRounded).toFixed(1)}°${lonRounded >= 0 ? "E" : "W"}`;

          const pointTarget: Country = {
            id: `point-${latRounded}-${lonRounded}`,
            name: `Grid Cell (${latStr}, ${lonStr})`,
            officialName: `NASA POWER Grid Cell (${latStr}, ${lonStr})`,
            code2: "UN",
            code3: "CELL",
            region: "Asia",
            subregion: "Observation Point",
            capital: `Point Coordinates (${latStr}, ${lonStr})`,
            lat: latRounded,
            lng: lonRounded,
            zoom: 2.5,
            population: "N/A",
            area: "0.5° × 0.5° (~50km)",
            currency: "N/A",
            timezone: "UTC",
          };
          onSelectCountryRef.current(pointTarget);
        }
      }
    };

    const dom = renderer.domElement;
    dom.addEventListener("pointerdown", onPointerDown);
    dom.addEventListener("pointermove", onPointerMove);
    dom.addEventListener("pointerup", onPointerUp);

    // 17. Update 2D Projected Badges in Screen Space
    const updateProjectedLabels = () => {
      if (!cameraRef.current || !activePinsRef.current.length || !container)
        return;
      const cam = cameraRef.current;
      const camDir = cam.position.clone().normalize();
      const halfW = container.clientWidth / 2;
      const halfH = container.clientHeight / 2;

      activePinsRef.current.forEach((obj) => {
        if (!obj.element) return;
        const normal = obj.worldPos.clone().normalize();
        const dot = normal.dot(camDir);

        if (dot < 0.18) {
          obj.element.style.opacity = "0";
          obj.element.style.pointerEvents = "none";
          return;
        }

        const projected = obj.worldPos.clone().project(cam);
        const x = projected.x * halfW + halfW;
        const y = -(projected.y * halfH) + halfH;

        obj.element.style.left = `${x}px`;
        obj.element.style.top = `${y}px`;
        obj.element.style.opacity = String(Math.min(1, (dot - 0.15) * 2.8));
        obj.element.style.pointerEvents = "auto";
      });
    };

    // Resize handler
    const onResize = () => {
      if (!container || !camera || !renderer) return;
      const w = container.clientWidth || window.innerWidth;
      const h = container.clientHeight || window.innerHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
      updateProjectedLabels();
    };
    window.addEventListener("resize", onResize);

    // 18. Animation Loop
    let animationFrameId: number;

    const animate = (time: number) => {
      animationFrameId = requestAnimationFrame(animate);

      // Camera tween lerping with cubic ease-out
      if (tweenRef.current) {
        const tween = tweenRef.current;
        const progress = Math.min(1, (time - tween.startTime) / tween.duration);
        const ease = 1 - Math.pow(1 - progress, 3);

        camera.position.lerpVectors(tween.startPos, tween.endPos, ease);
        controls.target.set(0, 0, 0);

        if (progress >= 1) {
          tweenRef.current = null;
        }
      }

      // Slowly rotate clouds
      if (cloudsMesh && cloudsMesh.visible) {
        cloudsMesh.rotation.y += 0.0003;
      }

      // Animate wind particles along jet streams
      if (windLinesGroup && windLinesGroup.visible) {
        windParticles.forEach((p) => {
          p.progress = (p.progress + 0.008) % 1;
          p.mesh.position.copy(p.curve.getPointAt(p.progress));
        });
      }

      // Update active contact ripples
      for (let i = activeRipples.length - 1; i >= 0; i--) {
        const r = activeRipples[i];
        const elapsed = time - r.startTime;
        const progress = Math.min(1, elapsed / r.duration);
        if (progress >= 1) {
          earthGroup.remove(r.group);
          r.rings.forEach((ring) => {
            ring.geometry.dispose();
            (ring.material as THREE.Material).dispose();
          });
          activeRipples.splice(i, 1);
        } else {
          const scale = 1 + progress * 5.2;
          r.group.scale.set(scale, scale, scale);
          r.rings.forEach((ring, idx) => {
            (ring.material as THREE.MeshBasicMaterial).opacity =
              (1 - progress) * (idx === 0 ? 0.95 : idx === 1 ? 0.75 : 0.5);
          });
        }
      }

      // Rotate selected reticle
      if (reticleRingRef.current) {
        reticleRingRef.current.rotation.z += 0.02;
      }

      // Pulse beacon opacity
      if (beaconMeshRef.current) {
        const pulse = 0.55 + Math.sin(time * 0.005) * 0.25;
        (beaconMeshRef.current.material as THREE.MeshBasicMaterial).opacity =
          pulse;
      }

      controls.update();
      updateProjectedLabels();
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
  }, [latLonToVector3, vector3ToLatLon]);

  // Sync layer toggles to Three.js meshes
  useEffect(() => {
    if (cloudsMeshRef.current) cloudsMeshRef.current.visible = showClouds;
  }, [showClouds]);

  useEffect(() => {
    if (bordersMeshRef.current) bordersMeshRef.current.visible = showBorders;
  }, [showBorders]);

  useEffect(() => {
    if (graticuleMeshRef.current)
      graticuleMeshRef.current.visible = showGraticule;
  }, [showGraticule]);

  const scaleMeta = SCALE_META[activeEnvLayer];

  return (
    <div className="relative w-full h-full overflow-hidden select-none bg-[#000000]">
      {/* 3D WebGL Canvas Container */}
      <div
        ref={containerRef}
        className="absolute inset-0 w-full h-full cursor-grab active:cursor-grabbing"
      />

      {/* 3D Projected Screen Badges Overlay Container (Matching exact HTML reference) */}
      <div
        ref={labelsContainerRef}
        id="labels-container"
        className="absolute inset-0 pointer-events-none z-10 overflow-hidden"
      />

      {/* Scientific Color Scale Bar (Appears when activeEnvLayer !== 'natural') */}
      {scaleMeta && (
        <div className="fixed top-16 right-4 sm:right-6 z-20 flex flex-col gap-1.5 p-3 rounded-2xl bg-[#080d16]/90 backdrop-blur-xl border border-white/15 text-[10px] w-64 shadow-2xl pointer-events-auto transition-all animate-in fade-in slide-in-from-top-2">
          <div className="flex items-center justify-between font-bold text-white">
            <span>{scaleMeta.title}</span>
            <span className="font-mono text-amber-300 text-[9px] px-1.5 py-0.5 rounded bg-amber-500/15 border border-amber-500/30">
              {scaleMeta.src}
            </span>
          </div>
          <div
            className="w-full h-2.5 rounded-full shadow-inner border border-white/10"
            style={{ background: scaleMeta.grad }}
          />
          <div className="flex items-center justify-between text-[9px] text-slate-300 font-mono">
            <span>{scaleMeta.min}</span>
            <span>{scaleMeta.mid}</span>
            <span>{scaleMeta.max}</span>
          </div>
        </div>
      )}

      {/* Floating Layer Control Dock (Bottom Left) */}
      <div className="fixed bottom-16 sm:bottom-12 left-4 sm:left-6 z-20 flex flex-col gap-2 pointer-events-auto">
        {/* Layer Variable Selector */}
        <div className="flex items-center gap-1 p-1 rounded-2xl bg-[#080d16]/90 backdrop-blur-xl border border-white/15 shadow-2xl">
          <button
            onClick={() => handleSetEnvLayer("natural")}
            className={`px-2.5 py-1.5 rounded-xl text-[11px] font-bold transition-all flex items-center gap-1.5 cursor-pointer ${
              activeEnvLayer === "natural"
                ? "cosmic-gold-button"
                : "text-slate-300 hover:text-white hover:bg-white/10"
            }`}
          >
            <span>🌍</span>
            <span className="hidden sm:inline">Natural</span>
          </button>
          <button
            onClick={() => handleSetEnvLayer("temp")}
            className={`px-2.5 py-1.5 rounded-xl text-[11px] font-bold transition-all flex items-center gap-1.5 cursor-pointer ${
              activeEnvLayer === "temp"
                ? "cosmic-gold-button"
                : "text-slate-300 hover:text-white hover:bg-white/10"
            }`}
          >
            <span>🌡️</span>
            <span className="hidden sm:inline">Temp (illustrative)</span>
          </button>
          <button
            onClick={() => handleSetEnvLayer("water")}
            className={`px-2.5 py-1.5 rounded-xl text-[11px] font-bold transition-all flex items-center gap-1.5 cursor-pointer ${
              activeEnvLayer === "water"
                ? "cosmic-gold-button"
                : "text-slate-300 hover:text-white hover:bg-white/10"
            }`}
          >
            <span>💧</span>
            <span className="hidden sm:inline">Moisture</span>
          </button>
          <button
            onClick={() => handleSetEnvLayer("winds")}
            className={`px-2.5 py-1.5 rounded-xl text-[11px] font-bold transition-all flex items-center gap-1.5 cursor-pointer ${
              activeEnvLayer === "winds"
                ? "cosmic-gold-button"
                : "text-slate-300 hover:text-white hover:bg-white/10"
            }`}
          >
            <span>💨</span>
            <span className="hidden sm:inline">Winds</span>
          </button>
          <button
            onClick={() => handleSetEnvLayer("veg")}
            className={`px-2.5 py-1.5 rounded-xl text-[11px] font-bold transition-all flex items-center gap-1.5 cursor-pointer ${
              activeEnvLayer === "veg"
                ? "cosmic-gold-button"
                : "text-slate-300 hover:text-white hover:bg-white/10"
            }`}
          >
            <span>🌿</span>
            <span className="hidden sm:inline">NDVI</span>
          </button>
          <button
            onClick={() => handleSetEnvLayer("fires")}
            className={`px-2.5 py-1.5 rounded-xl text-[11px] font-bold transition-all flex items-center gap-1.5 cursor-pointer ${
              activeEnvLayer === "fires"
                ? "cosmic-gold-button"
                : "text-slate-300 hover:text-white hover:bg-white/10"
            }`}
          >
            <span>🔥</span>
            <span className="hidden sm:inline">Fires (illustrative)</span>
          </button>
        </div>

        {/* Quick Toggles: Clouds, Borders, Graticule, Auto-Rotate, Levant View */}
        <div className="flex items-center gap-1.5 p-1 rounded-xl bg-[#080d16]/80 backdrop-blur-xl border border-white/10 w-fit text-[10px] text-slate-300">
          <button
            onClick={() => setShowClouds((prev) => !prev)}
            className={`px-2 py-1 rounded-lg font-semibold transition cursor-pointer ${
              showClouds
                ? "bg-sky-500/20 text-sky-300 border border-sky-500/40"
                : "hover:bg-white/10"
            }`}
          >
            ☁️ Clouds
          </button>
          <button
            onClick={() => setShowBorders((prev) => !prev)}
            className={`px-2 py-1 rounded-lg font-semibold transition cursor-pointer ${
              showBorders
                ? "bg-sky-500/20 text-sky-300 border border-sky-500/40"
                : "hover:bg-white/10"
            }`}
          >
            🗺️ Borders
          </button>
          <button
            onClick={() => setShowGraticule((prev) => !prev)}
            className={`px-2 py-1 rounded-lg font-semibold transition cursor-pointer ${
              showGraticule
                ? "bg-sky-500/20 text-sky-300 border border-sky-500/40"
                : "hover:bg-white/10"
            }`}
          >
            🌐 Grid
          </button>
          <button
            onClick={handleToggleAutoRotate}
            className={`px-2 py-1 rounded-lg font-semibold transition cursor-pointer ${
              autoRotate
                ? "bg-amber-500/20 text-amber-300 border border-amber-500/40"
                : "hover:bg-white/10"
            }`}
          >
            🔄 Auto-Rotate
          </button>
          <button
            onClick={handleResetLevantView}
            className="px-2 py-1 rounded-lg font-semibold hover:bg-white/10 transition cursor-pointer text-slate-200"
            title="Reset to Levant Perspective"
          >
            📍 Levant View
          </button>
        </div>
      </div>

      {/* Real-time HUD (Bottom-left telemetry status) */}
      <div className="absolute bottom-4 left-4 z-10 pointer-events-none">
        <div className="bg-[#080d16]/90 backdrop-blur-xl border border-white/15 px-3.5 py-1.5 rounded-lg shadow-lg flex items-center gap-2.5 text-xs">
          <span className="w-2 h-2 rounded-full bg-[#10b981] animate-pulse"></span>
          <span
            ref={hudCoordsRef}
            className="font-mono text-[#38bdf8] font-bold text-[11px]"
          >
            31.95° N, 35.23° E
          </span>
          <div className="h-3.5 w-px bg-white/20"></div>
          <span
            ref={hudCountryRef}
            className="font-bold text-[#f4f4f5] text-[11px] truncate max-w-[200px]"
          >
            Palestine (Jerusalem)
          </span>
          <div className="h-3.5 w-px bg-white/20 hidden md:block"></div>
          <div className="hidden md:flex items-center gap-1.5 text-[11px]">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
            <span className="font-mono text-amber-300 font-medium text-[10.5px]">
              NASA Astro EARTH Engine Active
            </span>
          </div>
        </div>
      </div>

      {/* Exact CSS from reference HTML file for 3D projected floating badges */}
      <style jsx global>{`
        #labels-container {
          position: absolute;
          inset: 0;
          pointer-events: none;
          z-index: 10;
          overflow: hidden;
        }
        .globe-label {
          position: absolute;
          left: -9999px;
          top: -9999px;
          transform: translate(-50%, -125%);
          pointer-events: auto;
          cursor: pointer;
          transition: opacity 0.15s ease, transform 0.15s ease;
          white-space: nowrap;
          user-select: none;
        }
        .globe-label:hover {
          z-index: 50 !important;
          transform: translate(-50%, -138%) scale(1.08);
        }
        .globe-label-badge {
          background: rgba(8, 15, 32, 0.9);
          backdrop-filter: blur(6px);
          border: 1px solid rgba(56, 189, 248, 0.48);
          padding: 3px 9px;
          border-radius: 9999px;
          font-size: 11px;
          font-weight: 700;
          color: #e0f2fe;
          display: flex;
          align-items: center;
          gap: 5px;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.65);
        }
        .globe-label.selected-pin .globe-label-badge {
          background: rgba(245, 158, 11, 0.95);
          border-color: #ffffff;
          color: #ffffff;
          box-shadow: 0 0 16px rgba(245, 158, 11, 0.9);
        }
      `}</style>
    </div>
  );
}