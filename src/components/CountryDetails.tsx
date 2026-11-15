"use client";

import React from "react";
import { useRouter } from "next/navigation";
import { Country } from "../data/countries";
import AnalysisControls from "./AnalysisControls";
import { selectionToParams, type Selection } from "../lib/api-client";

interface CountryDetailsProps {
  country: Country;
  onClose: () => void;
  onZoomTo: (zoom: number) => void;
}

export default function CountryDetails({
  country,
  onClose,
  onZoomTo,
}: CountryDetailsProps) {
  const router = useRouter();
  const formatCoord = (lat: number, lng: number) => {
    const latStr =
      lat >= 0
        ? `${lat.toFixed(2)}° N`
        : `${Math.abs(lat).toFixed(2)}° S`;
    const lngStr =
      lng >= 0
        ? `${lng.toFixed(2)}° E`
        : `${Math.abs(lng).toFixed(2)}° W`;
    return `${latStr}, ${lngStr}`;
  };

  return (
    <div className="bg-[#111827] border border-[#374151] rounded-lg shadow-2xl p-4 w-full max-w-sm sm:max-w-md max-h-[70vh] overflow-y-auto text-[#e5e7eb] flex flex-col gap-3">
      {/* Header */}
      <div className="flex items-start justify-between border-b border-[#1f2937] pb-3">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-bold text-[#f9fafb] tracking-tight">
              {country.name}
            </h2>
            <span className="text-xs font-mono px-2 py-0.5 bg-[#1f2937] border border-[#374151] text-[#93c5fd] rounded">
              {country.code2} / {country.code3}
            </span>
          </div>
          <p className="text-xs text-[#9ca3af] mt-0.5">
            {country.officialName}
          </p>
        </div>

        <button
          onClick={onClose}
          className="text-[#9ca3af] hover:text-[#f3f4f6] p-1 rounded hover:bg-[#1f2937] transition-colors"
          title="Close details"
        >
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
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>

      {/* Grid of Attributes */}
      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="bg-[#0b0f19] p-2.5 rounded border border-[#1f2937]">
          <span className="text-[#9ca3af] block text-[11px] uppercase tracking-wider">
            Region
          </span>
          <span className="font-medium text-[#f3f4f6] mt-0.5 block">
            {country.region} ({country.subregion})
          </span>
        </div>

        <div className="bg-[#0b0f19] p-2.5 rounded border border-[#1f2937]">
          <span className="text-[#9ca3af] block text-[11px] uppercase tracking-wider">
            Capital
          </span>
          <span className="font-medium text-[#f3f4f6] mt-0.5 block">
            {country.capital}
          </span>
        </div>

        <div className="bg-[#0b0f19] p-2.5 rounded border border-[#1f2937]">
          <span className="text-[#9ca3af] block text-[11px] uppercase tracking-wider">
            Coordinates
          </span>
          <span className="font-mono text-[#60a5fa] mt-0.5 block">
            {formatCoord(country.lat, country.lng)}
          </span>
        </div>

        <div className="bg-[#0b0f19] p-2.5 rounded border border-[#1f2937]">
          <span className="text-[#9ca3af] block text-[11px] uppercase tracking-wider">
            Population
          </span>
          <span className="font-medium text-[#f3f4f6] mt-0.5 block">
            {country.population}
          </span>
        </div>

        <div className="bg-[#0b0f19] p-2.5 rounded border border-[#1f2937]">
          <span className="text-[#9ca3af] block text-[11px] uppercase tracking-wider">
            Land Area
          </span>
          <span className="font-medium text-[#f3f4f6] mt-0.5 block">
            {country.area}
          </span>
        </div>

        <div className="bg-[#0b0f19] p-2.5 rounded border border-[#1f2937]">
          <span className="text-[#9ca3af] block text-[11px] uppercase tracking-wider">
            Currency
          </span>
          <span className="font-medium text-[#f3f4f6] mt-0.5 block">
            {country.currency}
          </span>
        </div>
      </div>

      {/* Timezone */}
      <div className="bg-[#0b0f19] p-2 rounded border border-[#1f2937] text-xs flex items-center justify-between">
        <span className="text-[#9ca3af]">Timezone</span>
        <span className="font-mono text-[#e5e7eb]">{country.timezone}</span>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 pt-1">
        <button
          onClick={() => onZoomTo(country.zoom * 1.35)}
          className="flex-1 py-1.5 px-3 bg-[#2563eb] hover:bg-[#1d4ed8] text-white text-xs font-semibold rounded transition-colors text-center"
        >
          Close-Up Zoom
        </button>
        <button
          onClick={() => onZoomTo(1.2)}
          className="py-1.5 px-3 bg-[#1f2937] hover:bg-[#374151] text-[#9ca3af] hover:text-white text-xs font-medium rounded transition-colors"
        >
          Globe View
        </button>
      </div>

      {/* Environmental analysis: pick a variable and period, then open the dashboard */}
      <div className="border-t border-[#1f2937] pt-3">
        <h3 className="text-[11px] uppercase tracking-wider text-[#9ca3af] mb-2">Analyze trends</h3>
        <AnalysisControls
          lat={country.lat}
          lon={country.lng}
          name={country.name}
          submitLabel="Open Dashboard"
          onApply={(s: Selection) => router.push(`/dashboard?${selectionToParams(s)}`)}
        />
      </div>
    </div>
  );
}
