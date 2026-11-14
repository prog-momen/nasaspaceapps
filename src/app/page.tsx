"use client";

import React, { useState } from "react";
import EarthGlobe3D from "../components/EarthGlobe3D";
import SearchBar from "../components/SearchBar";
import CountryDetails from "../components/CountryDetails";
import { Country, COUNTRIES } from "../data/countries";

export default function Home() {
  const [selectedCountry, setSelectedCountry] = useState<Country | null>(null);
  const [autoSpin, setAutoSpin] = useState<boolean>(true);
  const [showGrid, setShowGrid] = useState<boolean>(true);

  const handleSelectCountry = (country: Country) => {
    setSelectedCountry(country);
    // Pause auto-spin when focusing on a searched country
    setAutoSpin(false);
  };

  const handleCloseDetails = () => {
    setSelectedCountry(null);
  };

  // Quick preset destinations
  const popularPresets = [
    { label: "Egypt", id: "egy" },
    { label: "United States", id: "usa" },
    { label: "Japan", id: "jpn" },
    { label: "France", id: "fra" },
    { label: "Brazil", id: "bra" },
    { label: "Australia", id: "aus" },
    { label: "South Africa", id: "zaf" },
  ];

  return (
    <main className="relative w-screen h-screen overflow-hidden bg-[#070a13] text-[#e2e8f0] flex flex-col font-sans select-none">
      {/* Top Navigation & Search Bar Header */}
      <header className="absolute top-0 left-0 right-0 z-30 p-4 sm:p-5 flex flex-col items-center pointer-events-none">
        <div className="w-full max-w-4xl flex flex-col items-center gap-3">
          {/* Top Title Bar */}
          <div className="w-full flex items-center justify-between pointer-events-auto">
            <div className="flex items-center gap-2.5">
              <div className="w-3 h-3 bg-[#3b82f6] rounded-full"></div>
              <h1 className="text-base sm:text-lg font-bold text-[#f8fafc] tracking-tight">
                3D Earth Explorer
              </h1>
              <span className="hidden sm:inline-block text-xs font-mono px-2 py-0.5 bg-[#111827] border border-[#374151] text-[#9ca3af] rounded">
                All World Regions
              </span>
            </div>

            <div className="flex items-center gap-2 text-xs">
              <span className="hidden md:inline text-[#9ca3af]">
                Active Database:
              </span>
              <span className="font-semibold text-[#60a5fa] bg-[#111827] px-2 py-1 rounded border border-[#1f2937]">
                {COUNTRIES.length} Countries & Regions
              </span>
            </div>
          </div>

          {/* Interactive Search Bar */}
          <div className="w-full pointer-events-auto">
            <SearchBar
              onSelectCountry={handleSelectCountry}
              selectedCountry={selectedCountry}
            />
          </div>

          {/* Quick Destination Fly-To Pills */}
          <div className="w-full flex items-center gap-1.5 overflow-x-auto py-0.5 pointer-events-auto text-xs justify-start sm:justify-center">
            <span className="text-[#64748b] text-[11px] uppercase tracking-wider font-semibold mr-1">
              Quick Fly:
            </span>
            {popularPresets.map((preset) => {
              const country = COUNTRIES.find((c) => c.id === preset.id);
              if (!country) return null;
              const isSelected = selectedCountry?.id === country.id;
              return (
                <button
                  key={preset.id}
                  onClick={() => handleSelectCountry(country)}
                  className={`px-2.5 py-0.5 rounded border text-[11px] font-medium transition-colors ${
                    isSelected
                      ? "bg-[#22c55e] border-[#22c55e] text-white"
                      : "bg-[#111827] border-[#1f2937] text-[#cbd5e1] hover:bg-[#1f2937] hover:border-[#374151]"
                  }`}
                >
                  {preset.label}
                </button>
              );
            })}
          </div>
        </div>
      </header>

      {/* 3D Canvas Earth Component (Supports touch on phones and mouse on desktop) */}
      <section className="w-full h-full">
        <EarthGlobe3D
          selectedCountry={selectedCountry}
          onSelectCountry={handleSelectCountry}
          autoSpin={autoSpin}
          showGrid={showGrid}
          onToggleAutoSpin={() => setAutoSpin((prev) => !prev)}
          onToggleGrid={() => setShowGrid((prev) => !prev)}
        />
      </section>

      {/* Selected Country Dossier Card (Bottom overlay) */}
      {selectedCountry && (
        <div className="absolute bottom-6 left-4 right-4 sm:right-auto sm:max-w-md z-20 pointer-events-auto animate-in fade-in slide-in-from-bottom-4 duration-300">
          <CountryDetails
            country={selectedCountry}
            onClose={handleCloseDetails}
            onZoomTo={(customZoom) => {
              // Trigger zoom update
              if (selectedCountry) {
                setSelectedCountry({
                  ...selectedCountry,
                  zoom: customZoom,
                });
              }
            }}
          />
        </div>
      )}
    </main>
  );
}
