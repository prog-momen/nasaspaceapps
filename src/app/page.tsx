"use client";

import React, { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import StarField, { type StarMode } from "../components/StarField";

/**
 * Start screen: the logo and its name over a live starfield. The stars rush past as the logo arrives, then settle into a slow drift.
 * A click or key press stretches the stars into streaks and pulls the viewer into the Earth page (/earth).
 * Links that arrive with a place (?lat=&lon=) skip the splash and go straight to the globe.
 */
function Splash() {
  const router = useRouter();
  const params = useSearchParams();
  const [mode, setMode] = useState<StarMode>("arrive");
  const hasPlace = params.has("lat") && (params.has("lon") || params.has("lng"));

  useEffect(() => {
    router.prefetch("/earth");
    if (hasPlace) {
      router.replace(`/earth?${params.toString()}`);
      return;
    }
    const t = window.setTimeout(() => setMode((m) => (m === "arrive" ? "idle" : m)), 2600);
    return () => window.clearTimeout(t);
  }, [router, params, hasPlace]);

  const enter = () => {
    if (mode === "leave") return;
    setMode("leave");
    window.setTimeout(() => router.push("/earth"), 900);
  };

  if (hasPlace) return <div className="fixed inset-0 bg-black" />;

  return (
    <main className="fixed inset-0 overflow-hidden bg-black">
      <StarField mode={mode} />
      <div className="absolute inset-0 z-10 flex items-center justify-center">
      <button
        type="button"
        onClick={enter}
        aria-label="Enter Astro Earth"
        className={`splash-logo-btn flex cursor-pointer flex-col items-center gap-6 rounded-3xl bg-transparent p-6 outline-offset-4 ${
          mode === "leave" ? "splash-leaving" : ""
        }`}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="/astro-logo.png"
          alt=""
          width={260}
          height={260}
          className="splash-logo block h-[min(40vmin,240px)] w-[min(40vmin,240px)] select-none"
          draggable={false}
        />
        <span className="splash-title select-none text-center text-[clamp(14px,2.2vmin,20px)] font-semibold uppercase tracking-[0.45em] text-white/85">
          Astro Earth
        </span>
      </button>
      </div>
    </main>
  );
}

export default function Home() {
  return (
    <Suspense fallback={<div className="fixed inset-0 bg-black" />}>
      <Splash />
    </Suspense>
  );
}
