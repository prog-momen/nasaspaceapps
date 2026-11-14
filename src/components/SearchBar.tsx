"use client";

import React, { useState, useRef, useEffect, useMemo } from "react";
import { Country, COUNTRIES } from "../data/countries";

interface SearchBarProps {
  onSelectCountry: (country: Country) => void;
  selectedCountry: Country | null;
}

const REGIONS = ["All", "Africa", "Americas", "Asia", "Europe", "Oceania"] as const;

export default function SearchBar({
  onSelectCountry,
  selectedCountry,
}: SearchBarProps) {
  const [query, setQuery] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const [activeRegion, setActiveRegion] = useState<string>("All");
  const [highlightedIndex, setHighlightedIndex] = useState(0);

  const containerRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  // Close dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Adjust query when selectedCountry changes without triggering cascading effect renders
  const [prevSelectedCountry, setPrevSelectedCountry] = useState<Country | null>(selectedCountry);
  if (selectedCountry !== prevSelectedCountry) {
    setPrevSelectedCountry(selectedCountry);
    if (selectedCountry) {
      setQuery(selectedCountry.name);
    }
  }

  // Filter countries by query and region
  const filteredCountries = useMemo(() => {
    const q = query.trim().toLowerCase();
    return COUNTRIES.filter((c) => {
      const matchesRegion =
        activeRegion === "All" || c.region === activeRegion;
      if (!matchesRegion) return false;

      if (!q) return true;

      return (
        c.name.toLowerCase().includes(q) ||
        c.officialName.toLowerCase().includes(q) ||
        c.code2.toLowerCase().includes(q) ||
        c.code3.toLowerCase().includes(q) ||
        c.capital.toLowerCase().includes(q) ||
        c.subregion.toLowerCase().includes(q)
      );
    });
  }, [query, activeRegion]);

  // Handle keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!isOpen) {
      if (e.key === "ArrowDown" || e.key === "Enter") {
        setIsOpen(true);
      }
      return;
    }

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlightedIndex((prev) =>
        prev < filteredCountries.length - 1 ? prev + 1 : 0
      );
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlightedIndex((prev) =>
        prev > 0 ? prev - 1 : filteredCountries.length - 1
      );
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (filteredCountries[highlightedIndex]) {
        handleSelect(filteredCountries[highlightedIndex]);
      }
    } else if (e.key === "Escape") {
      setIsOpen(false);
    }
  };

  const handleSelect = (country: Country) => {
    setQuery(country.name);
    setIsOpen(false);
    onSelectCountry(country);
  };

  const handleClear = () => {
    setQuery("");
    setIsOpen(false);
    if (inputRef.current) {
      inputRef.current.focus();
    }
  };

  return (
    <div
      ref={containerRef}
      className="w-full relative z-20 flex flex-col gap-2 font-sans"
    >
      {/* Realistic Glassmorphic Search Input Box */}
      <div className="flex items-center bg-[#18181b]/80 backdrop-blur-xl border border-white/15 focus-within:border-[#2563eb] rounded-xl shadow-[0_8px_32px_0_rgba(0,0,0,0.5)] px-3.5 py-2.5 transition-all">
        {/* Search SVG Icon */}
        <span className="text-[#a1a1aa] mr-2.5 flex items-center">
          <svg
            width="17"
            height="17"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
        </span>

        {/* Input Field */}
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setIsOpen(true);
            setHighlightedIndex(0);
          }}
          onFocus={() => setIsOpen(true)}
          onKeyDown={handleKeyDown}
          placeholder="Search country or scroll below..."
          className="bg-transparent flex-1 text-xs text-[#f4f4f5] placeholder-[#71717a] outline-none"
        />

        {/* Clear Button */}
        {query && (
          <button
            onClick={handleClear}
            className="text-[#a1a1aa] hover:text-white p-1 ml-1 rounded transition-colors"
            title="Clear search"
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        )}

        {/* Locate / Go Button */}
        {filteredCountries.length > 0 && query && (
          <button
            onClick={() => handleSelect(filteredCountries[0])}
            className="ml-2 px-2.5 py-1 bg-[#2563eb] hover:bg-[#1d4ed8] text-white text-xs font-medium rounded-lg transition-colors active:scale-95"
          >
            Locate
          </button>
        )}
      </div>

      {/* Region Filter Chips */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs">
        {REGIONS.map((region) => {
          const isActive = activeRegion === region;
          return (
            <button
              key={region}
              onClick={() => {
                setActiveRegion(region);
                setHighlightedIndex(0);
              }}
              className={`px-2.5 py-1 rounded-lg border whitespace-nowrap text-[11px] font-medium transition-all ${
                isActive
                  ? "bg-[#2563eb] border-blue-400/50 text-white shadow-sm"
                  : "bg-white/5 border-white/10 text-[#a1a1aa] hover:text-[#f4f4f5] hover:bg-white/10"
              }`}
            >
              {region}
            </button>
          );
        })}
      </div>

      {/* Dropdown Suggestions List (Scroll down all countries) */}
      {isOpen && (
        <div className="absolute top-[88px] left-0 right-0 max-h-80 overflow-y-auto bg-[#18181b]/90 backdrop-blur-xl border border-white/15 rounded-xl shadow-[0_20px_50px_rgba(0,0,0,0.7)] z-30 divide-y divide-white/5">
          {filteredCountries.length === 0 ? (
            <div className="p-4 text-center text-xs text-[#71717a]">
              No countries found matching &quot;{query}&quot;
            </div>
          ) : (
            filteredCountries.map((country, index) => {
              const isSelected = selectedCountry?.id === country.id;
              const isHighlighted = highlightedIndex === index;

              return (
                <div
                  key={country.id}
                  onClick={() => handleSelect(country)}
                  onMouseEnter={() => setHighlightedIndex(index)}
                  className={`px-3 py-2.5 flex items-center justify-between cursor-pointer transition-colors ${
                    isHighlighted
                      ? "bg-white/10"
                      : isSelected
                      ? "bg-[#2563eb]/30 border-l-2 border-[#2563eb]"
                      : "hover:bg-white/5"
                  }`}
                >
                  <div className="flex flex-col">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-[#f4f4f5]">
                        {country.name}
                      </span>
                      <span className="text-[9px] px-1.5 py-0.5 bg-white/10 text-[#a1a1aa] rounded font-mono">
                        {country.code3}
                      </span>
                    </div>
                    <span className="text-[10px] text-[#71717a]">
                      Capital: {country.capital} • {country.subregion}
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-mono text-[#60a5fa] font-medium hidden sm:inline">
                      {country.lat > 0 ? `${country.lat.toFixed(1)}°N` : `${Math.abs(country.lat).toFixed(1)}°S`},{" "}
                      {country.lng > 0 ? `${country.lng.toFixed(1)}°E` : `${Math.abs(country.lng).toFixed(1)}°W`}
                    </span>
                    <span className="text-[10px] text-[#34d399] border border-[#34d399]/40 bg-[#34d399]/10 px-2 py-0.5 rounded-lg font-medium">
                      Fly To
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}
