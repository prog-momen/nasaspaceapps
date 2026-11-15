"use client";

import React, { useState, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import ThreeEarth from "../components/ThreeEarth";
import SearchBar from "../components/SearchBar";
import AiAssistantTemplate from "../components/AiAssistantTemplate";
import { COUNTRIES, Country } from "../data/countries";

function HomeContent() {
  const searchParams = useSearchParams();
  const defaultCountry =
    COUNTRIES.find((c) => c.name === "Palestine") || COUNTRIES[0];

  const urlCountry = React.useMemo<Country | null>(() => {
    const latStr = searchParams.get("lat");
    const lonStr = searchParams.get("lon") || searchParams.get("lng");
    const nameStr = searchParams.get("name");

    if (latStr && lonStr) {
      const lat = parseFloat(latStr);
      const lng = parseFloat(lonStr);
      if (!isNaN(lat) && !isNaN(lng)) {
        const found = COUNTRIES.find((c) =>
          nameStr
            ? c.name.toLowerCase() === nameStr.toLowerCase()
            : Math.abs(c.lat - lat) < 1.0 && Math.abs(c.lng - lng) < 1.0
        );

        if (found) return found;

        return {
          id: (nameStr || "target").toLowerCase().replace(/\s+/g, "-"),
          name: nameStr || "Target Location",
          officialName: nameStr || "NASA Observation Target",
          code2: "UN",
          code3: "UN0",
          region: "Asia" as const,
          subregion: "Observation Target",
          capital: "Target Coordinates",
          lat,
          lng,
          zoom: 2.2,
          population: "N/A",
          area: "N/A",
          currency: "N/A",
          timezone: "UTC",
        };
      }
    }
    return null;
  }, [searchParams]);

  const [activeCountry, setActiveCountry] = useState<Country | null>(null);
  const [isAssistantOpen, setIsAssistantOpen] = useState(false);
  const selectedCountry = activeCountry ?? urlCountry ?? defaultCountry;

  const handleSelectCountry = (country: Country) => {
    setActiveCountry(country);
  };

  return (
    <main className="relative w-screen h-screen overflow-hidden bg-[#000000] text-[#f4f4f5] font-sans select-none flex flex-col">
      {/* Realistic Glassmorphic Navbar: Logo, Home, Dashboard, and AI Assistant */}
      <header className="fixed top-0 left-0 right-0 h-14 bg-[#080d16]/90 backdrop-blur-xl border-b border-white/10 shadow-[0_4px_24px_0_rgba(0,0,0,0.6)] z-40 px-4 sm:px-6 flex items-center justify-between">
        <div className="flex items-center gap-2.5 sm:gap-3">
          <Link href="/" className="flex items-center gap-2.5 group mr-1">
            <div className="w-8 h-8 rounded-lg overflow-hidden border border-amber-400/50 bg-black shadow-[0_0_12px_rgba(245,158,11,0.25)] flex items-center justify-center transition-transform group-hover:scale-105">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src="/logo.jpg" alt="Astro EARTH Logo" className="w-full h-full object-contain" />
            </div>
            <div className="hidden md:flex flex-col">
              <span className="text-xs font-black tracking-tight text-white flex items-center gap-1">
                Astro <span className="text-amber-400">EARTH</span>
              </span>
              <span className="text-[9px] font-mono text-slate-400">NASA Space Apps</span>
            </div>
          </Link>

          <div className="h-5 w-[1px] bg-white/10 hidden md:block" />

          {/* Button 1: Home */}
          <button
            onClick={() => {
              if (defaultCountry) handleSelectCountry(defaultCountry);
            }}
            className="px-3 py-1.5 rounded-xl bg-white/5 hover:bg-white/15 text-[#f4f4f5] hover:text-white border border-white/15 text-xs font-bold transition-all shadow-sm flex items-center gap-1.5 active:scale-95 cursor-pointer"
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>
              <polyline points="9 22 9 12 15 12 15 22"></polyline>
            </svg>
            <span>Home</span>
          </button>

          {/* Button 2: Dashboard (NASA Challenge Analysis & Forecasting) */}
          <Link
            href={`/dashboard?lat=${selectedCountry.lat}&lon=${selectedCountry.lng}&name=${encodeURIComponent(
              selectedCountry.name
            )}`}
            className="px-3 py-1.5 rounded-xl bg-white/5 hover:bg-white/15 text-[#f4f4f5] hover:text-white border border-white/15 text-xs font-bold transition-all shadow-sm flex items-center gap-1.5 active:scale-95 cursor-pointer"
            title={`Open Environmental Trend & Forecasting Dashboard for ${selectedCountry.name}`}
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="18" y1="20" x2="18" y2="10"></line>
              <line x1="12" y1="20" x2="12" y2="4"></line>
              <line x1="6" y1="20" x2="6" y2="14"></line>
            </svg>
            <span>Dashboard</span>
            <span className="hidden sm:inline-block text-[10px] py-0.5 px-1.5 bg-amber-500/15 text-amber-300 border border-amber-500/30 rounded font-mono">
              {selectedCountry.name}
            </span>
          </Link>
        </div>

        {/* Button 3: AI Assistant (Cosmic Gold Styling) */}
        <button
          onClick={() => setIsAssistantOpen((prev) => !prev)}
          className="px-3.5 py-1.5 rounded-xl cosmic-gold-button text-xs font-black flex items-center gap-1.5 active:scale-95 cursor-pointer"
        >
          <div className="w-4 h-4 rounded-full overflow-hidden bg-black shrink-0">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/logo.jpg" alt="AI" className="w-full h-full object-contain" />
          </div>
          <span>AI Assistant</span>
        </button>
      </header>

      {/* Three.js 3D Earth Full-Screen Canvas with Deep Space Stars */}
      <section className="w-full h-full pt-12">
        <ThreeEarth
          onSelectCountry={handleSelectCountry}
          selectedCountry={selectedCountry}
        />
      </section>

      {/* Search Bar for Region: Positioned on the right */}
      <div
        style={{ top: "48px", right: "48px" }}
        className="fixed z-30 w-80 sm:w-96 flex flex-col pointer-events-auto gap-2"
      >
        <SearchBar
          onSelectCountry={handleSelectCountry}
          selectedCountry={selectedCountry}
        />

        {/* Selected Country Quick Dashboard Action Card */}
        {selectedCountry && (
          <div className="p-3 rounded-xl bg-[#18181b]/80 backdrop-blur-xl border border-white/15 flex items-center justify-between text-xs shadow-2xl">
            <div className="flex flex-col min-w-0 pr-2">
              <span className="font-semibold text-white truncate">{selectedCountry.name}</span>
              <span className="text-[10px] text-[#a1a1aa] truncate font-mono">
                {selectedCountry.capital} •{" "}
                {selectedCountry.lat > 0
                  ? `${selectedCountry.lat.toFixed(1)}°N`
                  : `${Math.abs(selectedCountry.lat).toFixed(1)}°S`}
                ,{" "}
                {selectedCountry.lng > 0
                  ? `${selectedCountry.lng.toFixed(1)}°E`
                  : `${Math.abs(selectedCountry.lng).toFixed(1)}°W`}
              </span>
            </div>
            <Link
              href={`/dashboard?lat=${selectedCountry.lat}&lon=${selectedCountry.lng}&name=${encodeURIComponent(
                selectedCountry.name
              )}`}
              className="px-3 py-1.5 rounded-lg bg-[#2563eb] hover:bg-[#1d4ed8] text-white text-[11px] font-bold transition-all flex items-center gap-1.5 shadow-md shrink-0 active:scale-95"
            >
              <span>View Dashboard</span>
              <svg
                width="12"
                height="12"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <polyline points="9 18 15 12 9 6"></polyline>
              </svg>
            </Link>
          </div>
        )}
      </div>

      {/* Pop-up AI Assistant Template */}
      {isAssistantOpen && (
        <div className="fixed bottom-24 right-6 sm:right-8 z-40 w-84 sm:w-96 max-w-[calc(100vw-3rem)] h-[520px] max-h-[calc(100vh-140px)] flex flex-col pointer-events-auto transition-all duration-300 origin-bottom-right">
          <AiAssistantTemplate
            selectedCountry={selectedCountry}
            onClose={() => setIsAssistantOpen(false)}
          />
        </div>
      )}

      {/* Realistic Glassmorphic Little Circle Action Button at Bottom Right */}
      <div className="fixed bottom-6 right-6 sm:bottom-8 sm:right-8 z-40 flex items-center gap-3 group">
        <span className="hidden sm:inline-block px-3 py-1.5 rounded-xl bg-[#18181b]/80 backdrop-blur-xl border border-white/15 text-[#60a5fa] text-xs font-bold tracking-wide shadow-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none">
          {isAssistantOpen ? "Close AI Assistant" : "Open AI Assistant"}
        </span>

        <button
          onClick={() => setIsAssistantOpen((prev) => !prev)}
          aria-label={isAssistantOpen ? "Close AI Assistant" : "Open AI Assistant"}
          className={`relative w-14 h-14 rounded-full flex items-center justify-center backdrop-blur-xl shadow-[0_8px_32px_0_rgba(0,0,0,0.65)] border transition-all duration-300 active:scale-95 cursor-pointer ${
            isAssistantOpen
              ? "bg-[#18181b]/90 border-white/30 text-white"
              : "bg-[#18181b]/80 hover:bg-[#27272a]/90 border-white/20 text-[#60a5fa] hover:text-white"
          }`}
        >
          {!isAssistantOpen && (
            <span className="absolute top-1 right-1 w-3 h-3 rounded-full bg-[#10b981] border-2 border-[#18181b]"></span>
          )}

          {isAssistantOpen ? (
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          ) : (
            <svg
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <circle cx="12" cy="12" r="9"></circle>
              <path d="M12 3a9 9 0 0 1 9 9"></path>
              <circle cx="12" cy="12" r="3"></circle>
              <path d="M12 7v2"></path>
              <path d="M12 15v2"></path>
              <path d="M7 12H9"></path>
              <path d="M15 12h2"></path>
            </svg>
          )}
        </button>
      </div>
    </main>
  );
}

export default function Home() {
  return (
    <Suspense fallback={<div className="w-screen h-screen bg-[#000000]" />}>
      <HomeContent />
    </Suspense>
  );
}
