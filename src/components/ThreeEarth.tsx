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

// Major continental world regions to be written on the Earth
const WORLD_REGIONS = [
  { name: "NORTH AMERICA", lat: 44, lon: -100 },
  { name: "SOUTH AMERICA", lat: -14, lon: -58 },
  { name: "EUROPE", lat: 52, lon: 18 },
  { name: "AFRICA", lat: 4, lon: 21 },
  { name: "ASIA", lat: 44, lon: 95 },
  { name: "OCEANIA", lat: -24, lon: 134 },
  { name: "MIDDLE EAST", lat: 29, lon: 44 },
];

// Helper to create pure country name text billboard sprites directly on the Earth
// Pure text only: zero boxes, zero pills, zero borders, zero triangles
function createCountrySprite(
  countryName: string,
  isHighlighted = false
): THREE.Sprite | null {
  const canvas = document.createElement("canvas");
  canvas.width = 256;
  canvas.height = 64;
  const ctx = canvas.getContext("2d");
  if (!ctx) return null;

  ctx.clearRect(0, 0, 256, 64);

  // Pure country text - high legibility on any terrain or ocean
  const fontSize = isHighlighted ? 22 : 15;
  ctx.font = `bold ${fontSize}px sans-serif`;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";

  // Dark outline halo around text for crystal clear contrast
  ctx.strokeStyle = "rgba(0, 0, 0, 0.92)";
  ctx.lineWidth = isHighlighted ? 4.5 : 3;
  ctx.strokeText(countryName, 128, 32);

  // Text color: glowing blue if selected, crisp clean white otherwise
  ctx.fillStyle = isHighlighted ? "#60a5fa" : "#ffffff";
  ctx.fillText(countryName, 128, 32);

  const texture = new THREE.CanvasTexture(canvas);
  texture.minFilter = THREE.LinearFilter;
  const mat = new THREE.SpriteMaterial({
    map: texture,
    transparent: true,
    depthTest: true,
    depthWrite: false,
  });

  const sprite = new THREE.Sprite(mat);
  sprite.scale.set(isHighlighted ? 15 : 12, isHighlighted ? 3.75 : 3, 1);
  return sprite;
}

// Helper to create pure continental region labels (pure text, no box or triangle)
function createRegionSprite(regionName: string): THREE.Sprite | null {
  const canvas = document.createElement("canvas");
  canvas.width = 320;
  canvas.height = 64;
  const ctx = canvas.getContext("2d");
  if (!ctx) return null;

  ctx.clearRect(0, 0, 320, 64);

  ctx.font = "bold 14px sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";

  ctx.strokeStyle = "rgba(0, 0, 0, 0.85)";
  ctx.lineWidth = 3;
  ctx.strokeText(regionName, 160, 32);

  ctx.fillStyle = "rgba(255, 255, 255, 0.72)";
  ctx.fillText(regionName, 160, 32);

  const texture = new THREE.CanvasTexture(canvas);
  texture.minFilter = THREE.LinearFilter;
  const mat = new THREE.SpriteMaterial({
    map: texture,
    transparent: true,
    depthTest: true,
    depthWrite: false,
  });

  const sprite = new THREE.Sprite(mat);
  sprite.scale.set(16, 3.2, 1);
  return sprite;
}

// Realistic, Static Earth-Observation Satellite (Aerospace cylindrical hull, quilted MLI blankets, multi-panel solar wings, telescope aperture & parabolic dish)
function createRealisticSatellite(scene: THREE.Scene) {
  const satelliteGroup = new THREE.Group();

  // 1. High-Fidelity Quilted Thermal Insulation Blanket Texture (MLI)
  const foilCanvas = document.createElement("canvas");
  foilCanvas.width = 512;
  foilCanvas.height = 512;
  const fCtx = foilCanvas.getContext("2d");
  if (fCtx) {
    // Base aerospace champagne-silver insulation
    fCtx.fillStyle = "#e2e8f0";
    fCtx.fillRect(0, 0, 512, 512);

    const gridSize = 32;
    for (let x = 0; x < 512; x += gridSize) {
      for (let y = 0; y < 512; y += gridSize) {
        const isGoldPatch = (x / gridSize + y / gridSize) % 5 === 0;

        // Quilted pillow gradient effect
        const grad = fCtx.createLinearGradient(
          x,
          y,
          x + gridSize,
          y + gridSize
        );
        if (isGoldPatch) {
          grad.addColorStop(0, "#fde68a");
          grad.addColorStop(0.5, "#d97706");
          grad.addColorStop(1, "#92400e");
        } else {
          grad.addColorStop(0, "#ffffff");
          grad.addColorStop(0.5, "#cbd5e1");
          grad.addColorStop(1, "#94a3b8");
        }
        fCtx.fillStyle = grad;
        fCtx.fillRect(x + 1, y + 1, gridSize - 2, gridSize - 2);

        // Seam shadow
        fCtx.strokeStyle = "rgba(0, 0, 0, 0.35)";
        fCtx.lineWidth = 1;
        fCtx.strokeRect(x, y, gridSize, gridSize);

        // Micro-rivet at seam intersection
        fCtx.fillStyle = "rgba(0, 0, 0, 0.4)";
        fCtx.beginPath();
        fCtx.arc(x, y, 1, 0, Math.PI * 2);
        fCtx.fill();
      }
    }
  }
  const foilTex = new THREE.CanvasTexture(foilCanvas);
  foilTex.wrapS = THREE.RepeatWrapping;
  foilTex.wrapT = THREE.RepeatWrapping;

  // 2. High-Fidelity Photovoltaic Solar Array Texture (Deep Blue Silicon Cells)
  const solarCanvas = document.createElement("canvas");
  solarCanvas.width = 512;
  solarCanvas.height = 256;
  const sCtx = solarCanvas.getContext("2d");
  if (sCtx) {
    // Deep space midnight silicon
    sCtx.fillStyle = "#081120";
    sCtx.fillRect(0, 0, 512, 256);

    const cellW = 32;
    const cellH = 64;

    for (let x = 4; x < 508; x += cellW) {
      for (let y = 4; y < 252; y += cellH) {
        // Individual silicon cell
        sCtx.fillStyle = "#0a1936";
        sCtx.fillRect(x + 1, y + 1, cellW - 2, cellH - 2);

        // Fine metallic collector grid lines
        sCtx.strokeStyle = "rgba(56, 189, 248, 0.45)";
        sCtx.lineWidth = 0.5;
        for (let gy = y + 6; gy < y + cellH - 4; gy += 6) {
          sCtx.beginPath();
          sCtx.moveTo(x + 2, gy);
          sCtx.lineTo(x + cellW - 2, gy);
          sCtx.stroke();
        }

        // Silver cell border
        sCtx.strokeStyle = "rgba(148, 163, 184, 0.6)";
        sCtx.lineWidth = 0.8;
        sCtx.strokeRect(x, y, cellW, cellH);

        // Golden interconnect tabs
        sCtx.fillStyle = "#d97706";
        sCtx.fillRect(x + cellW / 2 - 2, y, 4, 2);
        sCtx.fillRect(x + cellW / 2 - 2, y + cellH - 2, 4, 2);
      }
    }

    // Main silver busbars along the center of array
    sCtx.strokeStyle = "#f8fafc";
    sCtx.lineWidth = 2;
    sCtx.beginPath();
    sCtx.moveTo(0, 128);
    sCtx.lineTo(512, 128);
    sCtx.stroke();
  }
  const solarTex = new THREE.CanvasTexture(solarCanvas);

  // Materials
  const foilMat = new THREE.MeshStandardMaterial({
    map: foilTex,
    roughness: 0.3,
    metalness: 0.75,
  });

  const carbonMat = new THREE.MeshStandardMaterial({
    color: 0x1e293b,
    roughness: 0.6,
    metalness: 0.4,
  });

  const titaniumMat = new THREE.MeshStandardMaterial({
    color: 0xe2e8f0,
    roughness: 0.25,
    metalness: 0.8,
  });

  const darkTitaniumMat = new THREE.MeshStandardMaterial({
    color: 0x334155,
    roughness: 0.45,
    metalness: 0.6,
  });

  const solarMat = new THREE.MeshStandardMaterial({
    map: solarTex,
    roughness: 0.15,
    metalness: 0.65,
  });

  const goldBackingMat = new THREE.MeshStandardMaterial({
    color: 0xd97706,
    roughness: 0.35,
    metalness: 0.85,
  });

  const dishMat = new THREE.MeshStandardMaterial({
    color: 0xf8fafc,
    roughness: 0.3,
    metalness: 0.15,
    side: THREE.DoubleSide,
  });

  const lensMat = new THREE.MeshStandardMaterial({
    color: 0x0284c7,
    roughness: 0.08,
    metalness: 0.95,
  });

  // A. Central Cylindrical Avionics & Equipment Fuselage (Quilted MLI Blanket)
  const mainBus = new THREE.Mesh(
    new THREE.CylinderGeometry(1.5, 1.5, 3.4, 32),
    foilMat
  );
  satelliteGroup.add(mainBus);

  // Structural Titanium Ring Collars
  const ringGeo = new THREE.TorusGeometry(1.54, 0.045, 16, 32);
  const ring1 = new THREE.Mesh(ringGeo, titaniumMat);
  ring1.position.y = 1.0;
  ring1.rotation.x = Math.PI / 2;
  satelliteGroup.add(ring1);

  const ring2 = new THREE.Mesh(ringGeo, titaniumMat);
  ring2.position.y = -1.0;
  ring2.rotation.x = Math.PI / 2;
  satelliteGroup.add(ring2);

  // B. Forward Earth-Observation Telescope Barrel (Pointing along -Z)
  const telescopeGroup = new THREE.Group();
  telescopeGroup.position.set(0, 0, -1.5);
  telescopeGroup.rotation.x = Math.PI / 2;

  // Outer Carbon Baffle Barrel
  const barrelOuter = new THREE.Mesh(
    new THREE.CylinderGeometry(1.4, 1.4, 2.0, 32, 1, true),
    carbonMat
  );
  telescopeGroup.add(barrelOuter);

  // Protective Aperture Sunshield Flap (Tilted at top rim)
  const hoodFlap = new THREE.Mesh(
    new THREE.BoxGeometry(1.6, 0.05, 1.0),
    carbonMat
  );
  hoodFlap.position.set(0, 1.1, -0.4);
  hoodFlap.rotation.x = -Math.PI / 6;
  telescopeGroup.add(hoodFlap);

  // Recessed Primary Optical Mirror / Sensor Lens
  const primaryLens = new THREE.Mesh(
    new THREE.CircleGeometry(1.25, 32),
    lensMat
  );
  primaryLens.position.set(0, -0.6, 0);
  primaryLens.rotation.x = Math.PI / 2;
  telescopeGroup.add(primaryLens);

  satelliteGroup.add(telescopeGroup);

  // C. Aft Propulsion Module (Facing +Z)
  const aftModule = new THREE.Mesh(
    new THREE.CylinderGeometry(1.4, 1.1, 1.2, 32),
    darkTitaniumMat
  );
  aftModule.position.set(0, 0, 2.1);
  aftModule.rotation.x = Math.PI / 2;
  satelliteGroup.add(aftModule);

  // Main Apogee Engine Bell Nozzle
  const engineBell = new THREE.Mesh(
    new THREE.CylinderGeometry(0.3, 0.7, 0.85, 24),
    darkTitaniumMat
  );
  engineBell.position.set(0, 0, 2.9);
  engineBell.rotation.x = Math.PI / 2;
  satelliteGroup.add(engineBell);

  // 4 Corner RCS Attitude-Control Thruster Quads
  const rcsAngles = [
    Math.PI / 4,
    (3 * Math.PI) / 4,
    (5 * Math.PI) / 4,
    (7 * Math.PI) / 4,
  ];
  rcsAngles.forEach((ang) => {
    const rx = Math.cos(ang) * 1.45;
    const ry = Math.sin(ang) * 1.45;
    const rcsBase = new THREE.Mesh(
      new THREE.BoxGeometry(0.3, 0.3, 0.3),
      titaniumMat
    );
    rcsBase.position.set(rx, ry, 1.8);

    const nozzle = new THREE.Mesh(
      new THREE.CylinderGeometry(0.04, 0.1, 0.22, 8),
      darkTitaniumMat
    );
    nozzle.position.set(0, 0, 0.2);
    nozzle.rotation.x = Math.PI / 2;
    rcsBase.add(nozzle);
    satelliteGroup.add(rcsBase);
  });

  // D. Dual Articulated Multi-Segment Solar Array Wings (Ultra-thin, realistic)
  const solarWingsGroup = new THREE.Group();

  const createSolarWing = (isRight: boolean) => {
    const wingGroup = new THREE.Group();
    const sign = isRight ? 1 : -1;

    // Structural mounting truss boom
    const boom = new THREE.Mesh(
      new THREE.CylinderGeometry(0.06, 0.06, 2.0, 8),
      titaniumMat
    );
    boom.rotation.z = Math.PI / 2;
    boom.position.set(sign * 1.8, 0, 0);
    wingGroup.add(boom);

    // Gimbal drive box
    const gimbal = new THREE.Mesh(
      new THREE.BoxGeometry(0.4, 0.4, 0.4),
      darkTitaniumMat
    );
    gimbal.position.set(sign * 2.8, 0, 0);
    wingGroup.add(gimbal);

    // Inner Solar Panel Segment
    const panel1 = new THREE.Mesh(
      new THREE.BoxGeometry(3.6, 0.04, 1.9),
      [
        darkTitaniumMat,
        darkTitaniumMat,
        solarMat,
        goldBackingMat,
        darkTitaniumMat,
        darkTitaniumMat,
      ]
    );
    panel1.position.set(sign * 4.8, 0, 0);
    wingGroup.add(panel1);

    // Hinge bracket
    const hinge = new THREE.Mesh(
      new THREE.CylinderGeometry(0.05, 0.05, 0.3, 8),
      titaniumMat
    );
    hinge.position.set(sign * 6.7, 0, 0);
    wingGroup.add(hinge);

    // Outer Solar Panel Segment
    const panel2 = new THREE.Mesh(
      new THREE.BoxGeometry(3.6, 0.04, 1.9),
      [
        darkTitaniumMat,
        darkTitaniumMat,
        solarMat,
        goldBackingMat,
        darkTitaniumMat,
        darkTitaniumMat,
      ]
    );
    panel2.position.set(sign * 8.6, 0, 0);
    wingGroup.add(panel2);

    return wingGroup;
  };

  solarWingsGroup.add(createSolarWing(false)); // Left wing
  solarWingsGroup.add(createSolarWing(true));  // Right wing
  satelliteGroup.add(solarWingsGroup);

  // E. High-Gain Communications Parabolic Dish Antenna
  const dishGroup = new THREE.Group();
  dishGroup.position.set(1.4, 1.6, 0.2);

  // Articulated mounting strut
  const dishStrut = new THREE.Mesh(
    new THREE.CylinderGeometry(0.06, 0.06, 1.5, 8),
    titaniumMat
  );
  dishStrut.rotation.z = -Math.PI / 4;
  dishGroup.add(dishStrut);

  // Parabolic dish bowl
  const dishBowl = new THREE.Mesh(
    new THREE.SphereGeometry(1.3, 24, 16, 0, Math.PI * 2, 0, Math.PI * 0.42),
    dishMat
  );
  dishBowl.position.set(0.65, 0.75, 0);
  dishBowl.rotation.x = -Math.PI / 3;
  dishGroup.add(dishBowl);

  // Gold Feed Horn & Subreflector
  const feedHorn = new THREE.Mesh(
    new THREE.ConeGeometry(0.18, 0.45, 12),
    goldBackingMat
  );
  feedHorn.position.set(0.65, 0.75, -0.42);
  feedHorn.rotation.x = Math.PI / 2;
  dishGroup.add(feedHorn);
  satelliteGroup.add(dishGroup);

  // F. Star Trackers (2 Miniature conical optical navigation heads)
  const starTracker1 = new THREE.Mesh(
    new THREE.CylinderGeometry(0.12, 0.22, 0.4, 12),
    darkTitaniumMat
  );
  starTracker1.position.set(-1.4, 1.1, 0.8);
  starTracker1.rotation.z = Math.PI / 3;
  satelliteGroup.add(starTracker1);

  const starTracker2 = new THREE.Mesh(
    new THREE.CylinderGeometry(0.12, 0.22, 0.4, 12),
    darkTitaniumMat
  );
  starTracker2.position.set(-1.4, -1.1, 0.8);
  starTracker2.rotation.z = -Math.PI / 3;
  satelliteGroup.add(starTracker2);

  // G. Deployable Magnetometer Boom
  const magBoom = new THREE.Mesh(
    new THREE.CylinderGeometry(0.035, 0.035, 2.6, 6),
    titaniumMat
  );
  magBoom.position.set(0, -2.1, 0.8);
  satelliteGroup.add(magBoom);

  const magSensor = new THREE.Mesh(
    new THREE.BoxGeometry(0.25, 0.25, 0.25),
    darkTitaniumMat
  );
  magSensor.position.set(0, -3.4, 0.8);
  satelliteGroup.add(magSensor);

  // H. Omnidirectional Whip Antennas
  const whip1 = new THREE.Mesh(
    new THREE.CylinderGeometry(0.015, 0.015, 2.2, 4),
    titaniumMat
  );
  whip1.position.set(0.8, -1.5, 1.2);
  whip1.rotation.x = Math.PI / 4;
  satelliteGroup.add(whip1);

  // I. Navigation Status Beacon (Subtle green LED)
  const beacon = new THREE.Mesh(
    new THREE.SphereGeometry(0.12, 8, 8),
    new THREE.MeshBasicMaterial({ color: 0x10b981 })
  );
  beacon.position.set(0, 1.55, 0);
  satelliteGroup.add(beacon);

  // FIXED STATIC POSITION & ORIENTATION
  // Positioned prominently in clear view above the Earth
  const staticPos = new THREE.Vector3(135, 55, 90);
  satelliteGroup.position.copy(staticPos);

  // Grand heroic scale so the spacecraft is bold, large, and clearly visible
  satelliteGroup.scale.set(7.5, 7.5, 7.5);

  // Nadir pointing: optical telescope faces Earth directly
  satelliteGroup.lookAt(0, 0, 0);

  scene.add(satelliteGroup);

  return {
    group: satelliteGroup,
    dispose: () => {
      scene.remove(satelliteGroup);
      foilTex.dispose();
      solarTex.dispose();
      foilMat.dispose();
      carbonMat.dispose();
      titaniumMat.dispose();
      darkTitaniumMat.dispose();
      solarMat.dispose();
      goldBackingMat.dispose();
      dishMat.dispose();
      lensMat.dispose();
    },
  };
}

// Helper to create clean planet name typography sprites
function createPlanetLabel(name: string, size = 32): THREE.Sprite {
  const canvas = document.createElement("canvas");
  canvas.width = 192;
  canvas.height = 48;
  const ctx = canvas.getContext("2d");
  if (ctx) {
    ctx.clearRect(0, 0, 192, 48);
    ctx.font = "bold 16px sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.strokeStyle = "rgba(0, 0, 0, 0.92)";
    ctx.lineWidth = 3.5;
    ctx.strokeText(name, 96, 24);
    ctx.fillStyle = "rgba(240, 249, 255, 0.88)";
    ctx.fillText(name, 96, 24);
  }
  const tex = new THREE.CanvasTexture(canvas);
  const mat = new THREE.SpriteMaterial({
    map: tex,
    transparent: true,
    depthTest: true,
    depthWrite: false,
  });
  const sprite = new THREE.Sprite(mat);
  sprite.scale.set(size, size * 0.25, 1);
  return sprite;
}

// Realistic Solar System (Sun with glowing corona, Moon, Mercury, Venus, Mars, Jupiter with Great Red Spot, Saturn with rings, Uranus, Neptune)
function createSolarSystem(scene: THREE.Scene) {
  const solarSystemGroup = new THREE.Group();
  const clickableBodies: THREE.Object3D[] = [];
  const disposables: { dispose: () => void }[] = [];

  // ==========================================
  // 1. THE SUN (Incandescent Star & Luminous Corona)
  // ==========================================
  const sunPos = new THREE.Vector3(-850, 420, 850);

  // Photosphere Texture
  const sunCanvas = document.createElement("canvas");
  sunCanvas.width = 256;
  sunCanvas.height = 128;
  const sunCtx = sunCanvas.getContext("2d");
  if (sunCtx) {
    const g = sunCtx.createLinearGradient(0, 0, 0, 128);
    g.addColorStop(0, "#fffbeb");
    g.addColorStop(0.5, "#fbbf24");
    g.addColorStop(1, "#f59e0b");
    sunCtx.fillStyle = g;
    sunCtx.fillRect(0, 0, 256, 128);
    for (let i = 0; i < 150; i++) {
      sunCtx.fillStyle = i % 2 === 0 ? "#fef08a" : "#d97706";
      sunCtx.fillRect(
        Math.random() * 256,
        Math.random() * 128,
        4 + Math.random() * 6,
        4 + Math.random() * 6
      );
    }
  }
  const sunTex = new THREE.CanvasTexture(sunCanvas);
  disposables.push(sunTex);

  const sunGeo = new THREE.SphereGeometry(75, 32, 32);
  const sunMat = new THREE.MeshBasicMaterial({ map: sunTex, color: 0xffffff });
  disposables.push(sunGeo, sunMat);

  const sunMesh = new THREE.Mesh(sunGeo, sunMat);
  sunMesh.position.copy(sunPos);
  sunMesh.userData = { celestialTarget: sunPos, targetDist: 220 };
  solarSystemGroup.add(sunMesh);
  clickableBodies.push(sunMesh);

  // Luminous Corona Glow Sprite
  const coronaCanvas = document.createElement("canvas");
  coronaCanvas.width = 256;
  coronaCanvas.height = 256;
  const cCtx = coronaCanvas.getContext("2d");
  if (cCtx) {
    const cg = cCtx.createRadialGradient(128, 128, 12, 128, 128, 128);
    cg.addColorStop(0, "rgba(255, 255, 255, 1.0)");
    cg.addColorStop(0.25, "rgba(254, 240, 138, 0.85)");
    cg.addColorStop(0.55, "rgba(245, 158, 11, 0.4)");
    cg.addColorStop(0.85, "rgba(234, 88, 12, 0.12)");
    cg.addColorStop(1, "rgba(0, 0, 0, 0)");
    cCtx.fillStyle = cg;
    cCtx.fillRect(0, 0, 256, 256);
  }
  const coronaTex = new THREE.CanvasTexture(coronaCanvas);
  disposables.push(coronaTex);

  const coronaMat = new THREE.SpriteMaterial({
    map: coronaTex,
    blending: THREE.AdditiveBlending,
    transparent: true,
    opacity: 0.95,
  });
  disposables.push(coronaMat);

  const coronaSprite = new THREE.Sprite(coronaMat);
  coronaSprite.scale.set(400, 400, 1);
  coronaSprite.position.copy(sunPos);
  solarSystemGroup.add(coronaSprite);

  const sunLabel = createPlanetLabel("SUN", 55);
  sunLabel.position.copy(sunPos).add(new THREE.Vector3(0, 95, 0));
  solarSystemGroup.add(sunLabel);

  // ==========================================
  // 2. THE MOON (Earth's Natural Satellite)
  // ==========================================
  const moonPos = new THREE.Vector3(210, 65, -180);

  const moonCanvas = document.createElement("canvas");
  moonCanvas.width = 256;
  moonCanvas.height = 128;
  const mCtx = moonCanvas.getContext("2d");
  if (mCtx) {
    mCtx.fillStyle = "#94a3b8";
    mCtx.fillRect(0, 0, 256, 128);
    mCtx.fillStyle = "#475569";
    mCtx.beginPath();
    mCtx.arc(90, 60, 36, 0, Math.PI * 2);
    mCtx.fill();
    mCtx.beginPath();
    mCtx.arc(145, 45, 28, 0, Math.PI * 2);
    mCtx.fill();
    mCtx.beginPath();
    mCtx.arc(70, 85, 20, 0, Math.PI * 2);
    mCtx.fill();
    mCtx.beginPath();
    mCtx.arc(180, 75, 25, 0, Math.PI * 2);
    mCtx.fill();
    mCtx.fillStyle = "#f8fafc";
    mCtx.beginPath();
    mCtx.arc(120, 105, 3.5, 0, Math.PI * 2);
    mCtx.fill();
  }
  const moonTex = new THREE.CanvasTexture(moonCanvas);
  disposables.push(moonTex);

  const moonGeo = new THREE.SphereGeometry(27, 32, 32);
  const moonMat = new THREE.MeshStandardMaterial({
    map: moonTex,
    roughness: 0.88,
    metalness: 0.1,
  });
  disposables.push(moonGeo, moonMat);

  const moonMesh = new THREE.Mesh(moonGeo, moonMat);
  moonMesh.position.copy(moonPos);
  moonMesh.userData = { celestialTarget: moonPos, targetDist: 75 };
  solarSystemGroup.add(moonMesh);
  clickableBodies.push(moonMesh);

  const moonLabel = createPlanetLabel("MOON", 32);
  moonLabel.position.copy(moonPos).add(new THREE.Vector3(0, 38, 0));
  solarSystemGroup.add(moonLabel);

  // ==========================================
  // 3. MERCURY
  // ==========================================
  const mercPos = new THREE.Vector3(-480, 210, 480);
  const mercCanvas = document.createElement("canvas");
  mercCanvas.width = 128;
  mercCanvas.height = 64;
  const mercCtx = mercCanvas.getContext("2d");
  if (mercCtx) {
    mercCtx.fillStyle = "#64748b";
    mercCtx.fillRect(0, 0, 128, 64);
    for (let i = 0; i < 40; i++) {
      mercCtx.fillStyle = i % 2 === 0 ? "#475569" : "#94a3b8";
      mercCtx.fillRect(Math.random() * 128, Math.random() * 64, 4, 4);
    }
  }
  const mercTex = new THREE.CanvasTexture(mercCanvas);
  disposables.push(mercTex);

  const mercGeo = new THREE.SphereGeometry(9, 24, 24);
  const mercMat = new THREE.MeshStandardMaterial({
    map: mercTex,
    roughness: 0.85,
  });
  disposables.push(mercGeo, mercMat);

  const mercMesh = new THREE.Mesh(mercGeo, mercMat);
  mercMesh.position.copy(mercPos);
  mercMesh.userData = { celestialTarget: mercPos, targetDist: 35 };
  solarSystemGroup.add(mercMesh);
  clickableBodies.push(mercMesh);

  const mercLabel = createPlanetLabel("MERCURY", 28);
  mercLabel.position.copy(mercPos).add(new THREE.Vector3(0, 16, 0));
  solarSystemGroup.add(mercLabel);

  // ==========================================
  // 4. VENUS
  // ==========================================
  const venusPos = new THREE.Vector3(-420, 160, 640);
  const vCanvas = document.createElement("canvas");
  vCanvas.width = 128;
  vCanvas.height = 64;
  const vCtx = vCanvas.getContext("2d");
  if (vCtx) {
    vCtx.fillStyle = "#fef08a";
    vCtx.fillRect(0, 0, 128, 64);
    vCtx.fillStyle = "rgba(254, 249, 195, 0.55)";
    vCtx.fillRect(0, 15, 128, 30);
  }
  const venusTex = new THREE.CanvasTexture(vCanvas);
  disposables.push(venusTex);

  const venusGeo = new THREE.SphereGeometry(24, 32, 32);
  const venusMat = new THREE.MeshStandardMaterial({
    map: venusTex,
    roughness: 0.65,
  });
  disposables.push(venusGeo, venusMat);

  const venusMesh = new THREE.Mesh(venusGeo, venusMat);
  venusMesh.position.copy(venusPos);
  venusMesh.userData = { celestialTarget: venusPos, targetDist: 65 };
  solarSystemGroup.add(venusMesh);
  clickableBodies.push(venusMesh);

  const venusLabel = createPlanetLabel("VENUS", 36);
  venusLabel.position.copy(venusPos).add(new THREE.Vector3(0, 34, 0));
  solarSystemGroup.add(venusLabel);

  // ==========================================
  // 5. MARS (The Red Planet)
  // ==========================================
  const marsPos = new THREE.Vector3(460, 180, 440);
  const marsCanvas = document.createElement("canvas");
  marsCanvas.width = 256;
  marsCanvas.height = 128;
  const marsCtx = marsCanvas.getContext("2d");
  if (marsCtx) {
    marsCtx.fillStyle = "#c2410c";
    marsCtx.fillRect(0, 0, 256, 128);
    marsCtx.fillStyle = "#7c2d12";
    marsCtx.fillRect(40, 50, 70, 35);
    marsCtx.fillRect(150, 60, 60, 28);
    marsCtx.fillStyle = "#ffffff";
    marsCtx.fillRect(0, 0, 256, 12);
    marsCtx.fillRect(0, 118, 256, 10);
  }
  const marsTex = new THREE.CanvasTexture(marsCanvas);
  disposables.push(marsTex);

  const marsGeo = new THREE.SphereGeometry(15, 32, 32);
  const marsMat = new THREE.MeshStandardMaterial({
    map: marsTex,
    roughness: 0.82,
  });
  disposables.push(marsGeo, marsMat);

  const marsMesh = new THREE.Mesh(marsGeo, marsMat);
  marsMesh.position.copy(marsPos);
  marsMesh.userData = { celestialTarget: marsPos, targetDist: 48 };
  solarSystemGroup.add(marsMesh);
  clickableBodies.push(marsMesh);

  const marsLabel = createPlanetLabel("MARS", 30);
  marsLabel.position.copy(marsPos).add(new THREE.Vector3(0, 24, 0));
  solarSystemGroup.add(marsLabel);

  // ==========================================
  // 6. JUPITER (Gas Giant & Great Red Spot)
  // ==========================================
  const jupPos = new THREE.Vector3(780, 260, -700);
  const jupCanvas = document.createElement("canvas");
  jupCanvas.width = 256;
  jupCanvas.height = 128;
  const jCtx = jupCanvas.getContext("2d");
  if (jCtx) {
    const colors = [
      "#fef3c7",
      "#d97706",
      "#fef3c7",
      "#9a3412",
      "#fef3c7",
      "#b45309",
      "#fef3c7",
      "#78350f",
    ];
    const h = 128 / colors.length;
    colors.forEach((col, idx) => {
      jCtx.fillStyle = col;
      jCtx.fillRect(0, idx * h, 256, h);
    });
    jCtx.fillStyle = "#b91c1c";
    jCtx.beginPath();
    jCtx.ellipse(175, 76, 20, 11, 0, 0, Math.PI * 2);
    jCtx.fill();
    jCtx.strokeStyle = "#fef3c7";
    jCtx.lineWidth = 1.5;
    jCtx.stroke();
  }
  const jupTex = new THREE.CanvasTexture(jupCanvas);
  disposables.push(jupTex);

  const jupGeo = new THREE.SphereGeometry(52, 32, 32);
  const jupMat = new THREE.MeshStandardMaterial({
    map: jupTex,
    roughness: 0.5,
  });
  disposables.push(jupGeo, jupMat);

  const jupMesh = new THREE.Mesh(jupGeo, jupMat);
  jupMesh.position.copy(jupPos);
  jupMesh.userData = { celestialTarget: jupPos, targetDist: 140 };
  solarSystemGroup.add(jupMesh);
  clickableBodies.push(jupMesh);

  // 4 Galilean Moons (Io, Europa, Ganymede, Callisto)
  const moonOffsets = [
    new THREE.Vector3(70, 10, 0),
    new THREE.Vector3(-85, -8, 20),
    new THREE.Vector3(105, 14, -15),
    new THREE.Vector3(-125, 2, -30),
  ];
  const moonColors = [0xfde047, 0xe0f2fe, 0x94a3b8, 0x475569];
  moonOffsets.forEach((off, i) => {
    const gMoon = new THREE.Mesh(
      new THREE.SphereGeometry(1.8, 8, 8),
      new THREE.MeshStandardMaterial({ color: moonColors[i] })
    );
    gMoon.position.copy(jupPos).add(off);
    solarSystemGroup.add(gMoon);
  });

  const jupLabel = createPlanetLabel("JUPITER", 55);
  jupLabel.position.copy(jupPos).add(new THREE.Vector3(0, 68, 0));
  solarSystemGroup.add(jupLabel);

  // ==========================================
  // 7. SATURN (Ringed Planet & Cassini Division)
  // ==========================================
  const satPos = new THREE.Vector3(-650, -220, -1120);
  const satGroup = new THREE.Group();
  satGroup.position.copy(satPos);

  const satCanvas = document.createElement("canvas");
  satCanvas.width = 256;
  satCanvas.height = 128;
  const satCtx = satCanvas.getContext("2d");
  if (satCtx) {
    const sColors = [
      "#fef08a",
      "#fde047",
      "#fef08a",
      "#eab308",
      "#ca8a04",
      "#fde047",
    ];
    const sh = 128 / sColors.length;
    sColors.forEach((col, idx) => {
      satCtx.fillStyle = col;
      satCtx.fillRect(0, idx * sh, 256, sh);
    });
  }
  const satTex = new THREE.CanvasTexture(satCanvas);
  disposables.push(satTex);

  const satGeo = new THREE.SphereGeometry(44, 32, 32);
  const satMat = new THREE.MeshStandardMaterial({
    map: satTex,
    roughness: 0.52,
  });
  disposables.push(satGeo, satMat);

  const satMesh = new THREE.Mesh(satGeo, satMat);
  satGroup.add(satMesh);

  // Concentric Rings with Cassini Division
  const ringCanvas = document.createElement("canvas");
  ringCanvas.width = 256;
  ringCanvas.height = 32;
  const rCtx = ringCanvas.getContext("2d");
  if (rCtx) {
    const rg = rCtx.createLinearGradient(0, 0, 256, 0);
    rg.addColorStop(0.0, "rgba(217, 119, 6, 0.2)");
    rg.addColorStop(0.25, "rgba(253, 224, 71, 0.85)");
    rg.addColorStop(0.58, "rgba(253, 224, 71, 0.85)");
    rg.addColorStop(0.6, "rgba(0, 0, 0, 0)"); // Cassini Division
    rg.addColorStop(0.65, "rgba(0, 0, 0, 0)");
    rg.addColorStop(0.67, "rgba(234, 179, 8, 0.7)");
    rg.addColorStop(0.95, "rgba(202, 138, 4, 0.5)");
    rg.addColorStop(1.0, "rgba(0, 0, 0, 0)");
    rCtx.fillStyle = rg;
    rCtx.fillRect(0, 0, 256, 32);
  }
  const ringsTex = new THREE.CanvasTexture(ringCanvas);
  disposables.push(ringsTex);

  const ringGeo = new THREE.RingGeometry(52, 95, 64);
  const ringMat = new THREE.MeshStandardMaterial({
    map: ringsTex,
    side: THREE.DoubleSide,
    transparent: true,
    opacity: 0.88,
    roughness: 0.45,
  });
  disposables.push(ringGeo, ringMat);

  const ringMesh = new THREE.Mesh(ringGeo, ringMat);
  ringMesh.rotation.x = Math.PI / 2.3;
  ringMesh.rotation.y = Math.PI / 8;
  satGroup.add(ringMesh);

  satGroup.userData = { celestialTarget: satPos, targetDist: 135 };
  solarSystemGroup.add(satGroup);
  clickableBodies.push(satGroup);

  const satLabel = createPlanetLabel("SATURN", 50);
  satLabel.position.copy(satPos).add(new THREE.Vector3(0, 60, 0));
  solarSystemGroup.add(satLabel);

  // ==========================================
  // 8. URANUS
  // ==========================================
  const uranusPos = new THREE.Vector3(1150, -320, 750);
  const uCanvas = document.createElement("canvas");
  uCanvas.width = 128;
  uCanvas.height = 64;
  const uCtx = uCanvas.getContext("2d");
  if (uCtx) {
    uCtx.fillStyle = "#38bdf8";
    uCtx.fillRect(0, 0, 128, 64);
    uCtx.fillStyle = "rgba(103, 232, 249, 0.4)";
    uCtx.fillRect(0, 20, 128, 24);
  }
  const uranusTex = new THREE.CanvasTexture(uCanvas);
  disposables.push(uranusTex);

  const uranusGeo = new THREE.SphereGeometry(22, 24, 24);
  const uranusMat = new THREE.MeshStandardMaterial({
    map: uranusTex,
    roughness: 0.6,
  });
  disposables.push(uranusGeo, uranusMat);

  const uranusMesh = new THREE.Mesh(uranusGeo, uranusMat);
  uranusMesh.position.copy(uranusPos);
  uranusMesh.userData = { celestialTarget: uranusPos, targetDist: 65 };
  solarSystemGroup.add(uranusMesh);
  clickableBodies.push(uranusMesh);

  const uranusLabel = createPlanetLabel("URANUS", 36);
  uranusLabel.position.copy(uranusPos).add(new THREE.Vector3(0, 32, 0));
  solarSystemGroup.add(uranusLabel);

  // ==========================================
  // 9. NEPTUNE
  // ==========================================
  const neptunePos = new THREE.Vector3(-950, 380, -1350);
  const nCanvas = document.createElement("canvas");
  nCanvas.width = 128;
  nCanvas.height = 64;
  const nCtx = nCanvas.getContext("2d");
  if (nCtx) {
    nCtx.fillStyle = "#1d4ed8";
    nCtx.fillRect(0, 0, 128, 64);
    nCtx.fillStyle = "rgba(96, 165, 250, 0.4)";
    nCtx.fillRect(0, 18, 128, 26);
    nCtx.fillStyle = "rgba(255, 255, 255, 0.6)";
    nCtx.fillRect(30, 28, 40, 2);
  }
  const neptuneTex = new THREE.CanvasTexture(nCanvas);
  disposables.push(neptuneTex);

  const neptuneGeo = new THREE.SphereGeometry(21, 24, 24);
  const neptuneMat = new THREE.MeshStandardMaterial({
    map: neptuneTex,
    roughness: 0.6,
  });
  disposables.push(neptuneGeo, neptuneMat);

  const neptuneMesh = new THREE.Mesh(neptuneGeo, neptuneMat);
  neptuneMesh.position.copy(neptunePos);
  neptuneMesh.userData = { celestialTarget: neptunePos, targetDist: 60 };
  solarSystemGroup.add(neptuneMesh);
  clickableBodies.push(neptuneMesh);

  const neptuneLabel = createPlanetLabel("NEPTUNE", 36);
  neptuneLabel.position.copy(neptunePos).add(new THREE.Vector3(0, 30, 0));
  solarSystemGroup.add(neptuneLabel);

  scene.add(solarSystemGroup);

  // ==========================================
  // 10. AUTHENTIC 2K NASA PLANETARY MAPS (High-Res Realistic Textures)
  // ==========================================
  const textureLoader = new THREE.TextureLoader();
  textureLoader.crossOrigin = "anonymous";

  const PLANET_TEXTURES = {
    sun: "https://cdn.jsdelivr.net/gh/Moez-lab/theejs-project-solarsystem@main/textures/2k_sun.jpg",
    mercury: "https://cdn.jsdelivr.net/gh/Moez-lab/theejs-project-solarsystem@main/textures/2k_mercury.jpg",
    venus: "https://cdn.jsdelivr.net/gh/Moez-lab/theejs-project-solarsystem@main/textures/2k_venus_surface.jpg",
    moon: "https://cdn.jsdelivr.net/gh/Moez-lab/theejs-project-solarsystem@main/textures/2k_moon.jpg",
    mars: "https://cdn.jsdelivr.net/gh/Moez-lab/theejs-project-solarsystem@main/textures/2k_mars.jpg",
    jupiter: "https://cdn.jsdelivr.net/gh/Moez-lab/theejs-project-solarsystem@main/textures/2k_jupiter.jpg",
    saturn: "https://cdn.jsdelivr.net/gh/Moez-lab/theejs-project-solarsystem@main/textures/2k_saturn.jpg",
    saturnRing: "https://cdn.jsdelivr.net/gh/Moez-lab/theejs-project-solarsystem@main/textures/2k_saturn_ring_alpha.png",
    uranus: "https://cdn.jsdelivr.net/gh/Moez-lab/theejs-project-solarsystem@main/textures/2k_uranus.jpg",
    neptune: "https://cdn.jsdelivr.net/gh/Moez-lab/theejs-project-solarsystem@main/textures/2k_neptune.jpg",
  };

  textureLoader.load(PLANET_TEXTURES.sun, (tex) => {
    tex.colorSpace = THREE.SRGBColorSpace;
    sunMat.map = tex;
    sunMat.needsUpdate = true;
  });

  textureLoader.load(PLANET_TEXTURES.moon, (tex) => {
    tex.colorSpace = THREE.SRGBColorSpace;
    moonMat.map = tex;
    moonMat.needsUpdate = true;
  });

  textureLoader.load(PLANET_TEXTURES.mercury, (tex) => {
    tex.colorSpace = THREE.SRGBColorSpace;
    mercMat.map = tex;
    mercMat.needsUpdate = true;
  });

  textureLoader.load(PLANET_TEXTURES.venus, (tex) => {
    tex.colorSpace = THREE.SRGBColorSpace;
    venusMat.map = tex;
    venusMat.needsUpdate = true;
  });

  textureLoader.load(PLANET_TEXTURES.mars, (tex) => {
    tex.colorSpace = THREE.SRGBColorSpace;
    marsMat.map = tex;
    marsMat.needsUpdate = true;
  });

  textureLoader.load(PLANET_TEXTURES.jupiter, (tex) => {
    tex.colorSpace = THREE.SRGBColorSpace;
    jupMat.map = tex;
    jupMat.needsUpdate = true;
  });

  textureLoader.load(PLANET_TEXTURES.saturn, (tex) => {
    tex.colorSpace = THREE.SRGBColorSpace;
    satMat.map = tex;
    satMat.needsUpdate = true;
  });

  textureLoader.load(PLANET_TEXTURES.saturnRing, (tex) => {
    ringMat.map = tex;
    ringMat.needsUpdate = true;
  });

  textureLoader.load(PLANET_TEXTURES.uranus, (tex) => {
    tex.colorSpace = THREE.SRGBColorSpace;
    uranusMat.map = tex;
    uranusMat.needsUpdate = true;
  });

  textureLoader.load(PLANET_TEXTURES.neptune, (tex) => {
    tex.colorSpace = THREE.SRGBColorSpace;
    neptuneMat.map = tex;
    neptuneMat.needsUpdate = true;
  });

  return {
    group: solarSystemGroup,
    clickableBodies,
    update: () => {
      // Authentic planetary axial rotations (retrograde for Venus, fast for gas giants)
      sunMesh.rotation.y += 0.0006;
      moonMesh.rotation.y += 0.0004;
      mercMesh.rotation.y += 0.0005;
      venusMesh.rotation.y -= 0.0003;
      marsMesh.rotation.y += 0.001;
      jupMesh.rotation.y += 0.0015;
      satMesh.rotation.y += 0.0014;
      uranusMesh.rotation.y += 0.0008;
      neptuneMesh.rotation.y += 0.0008;
    },
    dispose: () => {
      scene.remove(solarSystemGroup);
      disposables.forEach((d) => d.dispose());
    },
  };
}

export default function ThreeEarth({
  onSelectCountry,
  selectedCountry,
}: ThreeEarthProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  // References across renders
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const earthGroupRef = useRef<THREE.Group | null>(null);
  const earthMeshRef = useRef<THREE.Mesh | null>(null);
  const selectedMarkerGroupRef = useRef<THREE.Group | null>(null);
  const tweenRef = useRef<{
    startPos: THREE.Vector3;
    endPos: THREE.Vector3;
    startTime: number;
    duration: number;
  } | null>(null);

  // DOM refs for 60fps HUD
  const hudCoordsRef = useRef<HTMLSpanElement | null>(null);
  const hudCountryRef = useRef<HTMLSpanElement | null>(null);

  // Lat/Lon to 3D Cartesian Vector
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

  // Smooth camera fly-to function - strictly STATIC upon arrival
  const flyToCoordinates = useCallback(
    (lat: number, lon: number, targetDistance = 210) => {
      if (!cameraRef.current || !controlsRef.current) return;
      // Disable auto-rotation so region remains completely static
      controlsRef.current.autoRotate = false;

      const endPos = latLonToVector3(lat, lon, targetDistance);
      tweenRef.current = {
        startPos: cameraRef.current.position.clone(),
        endPos: endPos,
        startTime: performance.now(),
        duration: 1000,
      };
    },
    [latLonToVector3]
  );

  // Update selected region 3D label on the Earth when selectedCountry changes
  useEffect(() => {
    if (!selectedCountry) return;
    const dist = Math.max(145, 275 / (selectedCountry.zoom || 1));
    flyToCoordinates(selectedCountry.lat, selectedCountry.lng, dist);

    if (hudCountryRef.current) {
      hudCountryRef.current.textContent = `${selectedCountry.name} (${selectedCountry.capital})`;
    }
    if (hudCoordsRef.current) {
      hudCoordsRef.current.textContent = `${Math.abs(selectedCountry.lat).toFixed(2)}° ${selectedCountry.lat >= 0 ? "N" : "S"}, ${Math.abs(selectedCountry.lng).toFixed(2)}° ${selectedCountry.lng >= 0 ? "E" : "W"}`;
    }

    // Update 3D label written directly on the Earth
    const markerGroup = selectedMarkerGroupRef.current;
    if (markerGroup) {
      // Clear previous marker
      while (markerGroup.children.length > 0) {
        const obj = markerGroup.children[0];
        markerGroup.remove(obj);
      }

      // Highlighted country name - pure text, zero triangles, zero boxes, zero lines
      const labelSprite = createCountrySprite(selectedCountry.name, true);
      if (labelSprite) {
        labelSprite.position.copy(
          latLonToVector3(
            selectedCountry.lat,
            selectedCountry.lng,
            EARTH_RADIUS * 1.019
          )
        );
        markerGroup.add(labelSprite);
      }
    }
  }, [selectedCountry, flyToCoordinates, latLonToVector3]);

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

    // 3. WebGL Renderer (Optimized for Mobile & low-end devices)
    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      powerPreference: "high-performance",
      precision: "mediump",
    });
    renderer.setSize(width, height);
    // Cap DPR at 1.5 for smooth 60fps performance on other devices
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
    container.innerHTML = "";
    container.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // 4. OrbitControls - Static by default, no auto-rotation
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.rotateSpeed = 0.65;
    controls.zoomSpeed = 0.9;
    controls.enablePan = false;
    controls.minDistance = 118;
    controls.maxDistance = 1800; // Expanded to view Earth, Moon & Solar System
    controls.autoRotate = false; // Strictly static
    controlsRef.current = controls;

    // 5. Lighting (Sunlight positioned at the physical location of the visual Sun)
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.9);
    scene.add(ambientLight);

    const sunLight = new THREE.DirectionalLight(0xffffff, 1.4);
    sunLight.position.set(-850, 420, 850);
    scene.add(sunLight);

    // 6. Deep Space Stars (Dual-layer, fixed-pixel attenuation for real space look)
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

    // Background stars (4,000 stars)
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
      depthWrite: false,
    });
    scene.add(new THREE.Points(starGeo, starMaterial));

    // Bright prominent celestial stars (700 stars)
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
      depthWrite: false,
    });
    scene.add(new THREE.Points(brightGeo, brightMaterial));

    // 7. Earth Group
    const earthGroup = new THREE.Group();
    scene.add(earthGroup);
    earthGroupRef.current = earthGroup;

    // Build procedural fallback texture on canvas first
    const canvasTex = document.createElement("canvas");
    canvasTex.width = 1024;
    canvasTex.height = 512;
    const ctx = canvasTex.getContext("2d");
    if (ctx) {
      ctx.fillStyle = "#18181b";
      ctx.fillRect(0, 0, 1024, 512);

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

    // Base Earth Mesh (Optimized 64x64 geometry for smooth 60fps)
    const earthMaterial = new THREE.MeshPhongMaterial({
      map: proceduralTexture,
      specular: new THREE.Color(0x27272a),
      shininess: 12,
      bumpScale: 1.0,
    });
    const earthMesh = new THREE.Mesh(
      new THREE.SphereGeometry(EARTH_RADIUS, 64, 64),
      earthMaterial
    );
    earthGroup.add(earthMesh);
    earthMeshRef.current = earthMesh;

    // Load High-Res Textures
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

    // 8. Clouds Layer (64x64 geometry)
    const cloudsMaterial = new THREE.MeshPhongMaterial({
      transparent: true,
      opacity: 0.3,
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

    // 9. Graticule Lines (Parallels and Meridians)
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

    // 10. Country & Region Labels Written Directly on the Earth (Pure text: no boxes, no pills, zero triangles)
    const labelsGroup = new THREE.Group();
    earthGroup.add(labelsGroup);

    const countrySprites: THREE.Sprite[] = [];

    // All countries written directly on the Earth as clean text
    COUNTRIES.forEach((c) => {
      const sprite = createCountrySprite(c.name);
      if (sprite) {
        sprite.position.copy(
          latLonToVector3(c.lat, c.lng, EARTH_RADIUS * 1.018)
        );
        sprite.userData = { country: c };
        labelsGroup.add(sprite);
        countrySprites.push(sprite);
      }
    });

    // World Region Labels (continents) as clean text
    WORLD_REGIONS.forEach((reg) => {
      const sprite = createRegionSprite(reg.name);
      if (sprite) {
        sprite.position.copy(
          latLonToVector3(reg.lat, reg.lon, EARTH_RADIUS * 1.025)
        );
        labelsGroup.add(sprite);
      }
    });

    // 12. Realistic Earth-Observing Satellite (Gold MLI foil, solar panels, high-gain dish & optical lens)
    const satellite = createRealisticSatellite(scene);

    // 13. Realistic Visual Solar System (Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn, Uranus, Neptune)
    const solarSystem = createSolarSystem(scene);

    // 14. Dynamic Selected Region Marker Group
    const selectedMarkerGroup = new THREE.Group();
    earthGroup.add(selectedMarkerGroup);
    selectedMarkerGroupRef.current = selectedMarkerGroup;

    // 15. Pointer Interactivity & Raycasting
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
      if (
        Math.hypot(e.clientX - pointerDownPos.x, e.clientY - pointerDownPos.y) > 6
      )
        return;

      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(mouse, camera);

      // 0a. Check direct clicks on satellite to fly camera and inspect it
      const satHits = raycaster.intersectObjects([satellite.group], true);
      if (satHits.length > 0) {
        if (cameraRef.current && controlsRef.current) {
          controlsRef.current.autoRotate = false;
          const satPos = satellite.group.position.clone();
          const targetCam = satPos.clone().multiplyScalar(1.45);
          tweenRef.current = {
            startPos: cameraRef.current.position.clone(),
            endPos: targetCam,
            startTime: performance.now(),
            duration: 1000,
          };
        }
        return;
      }

      // 0b. Check clicks on solar system celestial bodies (Moon, Mars, Jupiter, Saturn, etc.)
      const celestialHits = raycaster.intersectObjects(solarSystem.clickableBodies, true);
      if (celestialHits.length > 0) {
        let hitObj: THREE.Object3D | null = celestialHits[0].object;
        while (hitObj && !hitObj.userData.celestialTarget) {
          hitObj = hitObj.parent;
        }
        if (hitObj && hitObj.userData.celestialTarget) {
          if (cameraRef.current && controlsRef.current) {
            controlsRef.current.autoRotate = false;
            const targetPos = hitObj.userData.celestialTarget as THREE.Vector3;
            const dist = (hitObj.userData.targetDist as number) || 120;
            const endCam = targetPos
              .clone()
              .add(new THREE.Vector3(dist * 0.7, dist * 0.4, dist * 0.9));
            tweenRef.current = {
              startPos: cameraRef.current.position.clone(),
              endPos: endCam,
              startTime: performance.now(),
              duration: 1200,
            };
          }
          return;
        }
      }

      // 1. Check direct clicks on country text labels
      const labelHits = raycaster.intersectObjects(countrySprites);
      if (labelHits.length > 0) {
        const c = labelHits[0].object.userData.country as Country;
        if (c && onSelectCountry) {
          onSelectCountry(c);
          return;
        }
      }

      // 2. Check Earth surface hits
      const earthHits = raycaster.intersectObject(earthMesh);

      if (earthHits.length > 0) {
        const hitPoint = earthHits[0].point.clone().normalize();
        let closest: Country | null = null;
        let minDist = 0.55; // ~32 degrees angular threshold

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

    // 15. Animation Loop - High Performance
    let animationFrameId: number;

    const animate = (time: number) => {
      animationFrameId = requestAnimationFrame(animate);

      // Handle smooth camera fly-to tween
      if (tweenRef.current) {
        const tween = tweenRef.current;
        const progress = Math.min(1, (time - tween.startTime) / tween.duration);
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

      // Satellite is strictly static in space - no movement

      // Rotate solar system planets slowly on their axes
      solarSystem.update();

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
      satellite.dispose();
      solarSystem.dispose();
      controls.dispose();
      renderer.dispose();
    };
  }, [latLonToVector3, vector3ToLatLon, onSelectCountry]);

  return (
    <div className="relative w-full h-full overflow-hidden select-none bg-[#000000]">
      {/* 3D WebGL Canvas Container */}
      <div
        ref={containerRef}
        className="absolute inset-0 w-full h-full cursor-grab active:cursor-grabbing"
      />

      {/* Real-time HUD (Coordinates, Country, Satellite & Solar System Status) */}
      <div className="absolute bottom-4 left-4 z-10 pointer-events-none">
        <div className="bg-[#18181b]/80 backdrop-blur-xl border border-white/15 px-3.5 py-1.5 rounded-lg shadow-lg flex items-center gap-2.5 text-xs">
          <span className="w-2 h-2 rounded-full bg-[#10b981]"></span>
          <span
            ref={hudCoordsRef}
            className="font-mono text-[#60a5fa] font-bold text-[11px]"
          >
            31.95° N, 35.23° E
          </span>
          <div className="h-3.5 w-px bg-white/20"></div>
          <span
            ref={hudCountryRef}
            className="font-bold text-[#f4f4f5] text-[11px] truncate max-w-[170px]"
          >
            Palestine (Jerusalem)
          </span>
          <div className="h-3.5 w-px bg-white/20"></div>
          <div className="flex items-center gap-1.5 text-[11px]">
            <span className="w-1.5 h-1.5 rounded-full bg-[#10b981]"></span>
            <span className="font-mono text-[#e0f2fe] font-medium text-[10.5px]">
              EOS-1 Satellite (Static)
            </span>
          </div>
          <div className="h-3.5 w-px bg-white/20 hidden md:block"></div>
          <div className="hidden md:flex items-center gap-1.5 text-[11px]">
            <span className="w-1.5 h-1.5 rounded-full bg-[#f59e0b]"></span>
            <span className="font-mono text-[#fef08a] font-medium text-[10.5px]">
              Solar System Active
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
