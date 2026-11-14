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
      className="w-full max-w-xl mx-auto relative z-20 flex flex-col gap-2"
    >
      {/* Search Input Box */}
      <div className="flex items-center bg-[#111827] border border-[#374151] focus-within:border-[#3b82f6] rounded shadow-lg px-3 py-2 transition-colors">
        {/* Search SVG Icon */}
        <span className="text-[#9ca3af] mr-2.5 flex items-center">
          <svg
            width="18"
            height="18"
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
          placeholder="Search any country, capital, or region (e.g. Japan, France, Brazil)..."
          className="bg-transparent flex-1 text-sm text-[#f3f4f6] placeholder-[#6b7280] outline-none"
        />

        {/* Clear Button */}
        {query && (
          <button
            onClick={handleClear}
            className="text-[#9ca3af] hover:text-[#f3f4f6] p-1 ml-1 rounded transition-colors"
            title="Clear search"
          >
            <svg
              width="16"
              height="16"
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
            className="ml-2 px-2.5 py-1 bg-[#2563eb] hover:bg-[#1d4ed8] text-white text-xs font-medium rounded transition-colors"
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
              className={`px-2.5 py-1 rounded border whitespace-nowrap font-medium transition-colors ${
                isActive
                  ? "bg-[#2563eb] border-[#3b82f6] text-white"
                  : "bg-[#111827] border-[#374151] text-[#9ca3af] hover:text-[#f3f4f6] hover:bg-[#1f2937]"
              }`}
            >
              {region}
            </button>
          );
        })}
      </div>

      {/* Dropdown Suggestions List */}
      {isOpen && (
        <div className="absolute top-[88px] left-0 right-0 max-h-72 overflow-y-auto bg-[#111827] border border-[#374151] rounded shadow-2xl z-30 divide-y divide-[#1f2937]">
          {filteredCountries.length === 0 ? (
            <div className="p-4 text-center text-sm text-[#6b7280]">
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
                      ? "bg-[#1f2937]"
                      : isSelected
                      ? "bg-[#1e3a8a]"
                      : "hover:bg-[#1f2937]"
                  }`}
                >
                  <div className="flex flex-col">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-[#f3f4f6]">
                        {country.name}
                      </span>
                      <span className="text-[10px] px-1.5 py-0.5 bg-[#374151] text-[#9ca3af] rounded font-mono">
                        {country.code3}
                      </span>
                    </div>
                    <span className="text-xs text-[#9ca3af]">
                      Capital: {country.capital} • {country.subregion}
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="text-xs text-[#60a5fa] font-medium hidden sm:inline">
                      {country.lat > 0 ? `${country.lat.toFixed(1)}°N` : `${Math.abs(country.lat).toFixed(1)}°S`},{" "}
                      {country.lng > 0 ? `${country.lng.toFixed(1)}°E` : `${Math.abs(country.lng).toFixed(1)}°W`}
                    </span>
                    <span className="text-xs text-[#22c55e] border border-[#22c55e] px-2 py-0.5 rounded font-medium">
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
