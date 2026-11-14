// Source of truth for the variable catalog and demo investigations.
// `npm run db:seed` upserts these into Supabase; the API falls back to them
// when the database is not configured so local development works offline.

export interface VariableDef {
  key: string; // our public id (same as the POWER parameter code)
  provider: "nasa_power";
  provider_param: string;
  name: string;
  category: "atmosphere" | "land" | "energy" | "water";
  unit: string;
  definition: string; // plain-language, for students
  why_it_matters: string;
  source_model: string;
  higher_means: string;
  sort_order: number;
}

export const VARIABLES: VariableDef[] = [
  {
    key: "T2M", provider: "nasa_power", provider_param: "T2M", name: "Air temperature (2 m)", category: "atmosphere", unit: "C",
    definition: "Average air temperature measured two metres above the ground.",
    why_it_matters: "The most direct indicator of warming or cooling in a region.",
    source_model: "MERRA-2", higher_means: "A warmer climate.", sort_order: 1,
  },
  {
    key: "T2M_MAX", provider: "nasa_power", provider_param: "T2M_MAX", name: "Maximum air temperature", category: "atmosphere", unit: "C",
    definition: "Average of the daily highest air temperature at two metres.",
    why_it_matters: "Shows whether hot days are getting hotter, which drives heat stress.",
    source_model: "MERRA-2", higher_means: "Hotter daytime conditions.", sort_order: 2,
  },
  {
    key: "T2M_MIN", provider: "nasa_power", provider_param: "T2M_MIN", name: "Minimum air temperature", category: "atmosphere", unit: "C",
    definition: "Average of the daily lowest air temperature at two metres.",
    why_it_matters: "Warming nights reduce recovery from heat and affect crops and ecosystems.",
    source_model: "MERRA-2", higher_means: "Warmer nights.", sort_order: 3,
  },
  {
    key: "TS", provider: "nasa_power", provider_param: "TS", name: "Land or ocean surface temperature", category: "land", unit: "C",
    definition: "Temperature of the Earth's surface itself (skin temperature), not the air above it.",
    why_it_matters: "Surface heating drives evaporation, ice melt and urban heat.",
    source_model: "MERRA-2", higher_means: "A hotter surface.", sort_order: 4,
  },
  {
    key: "PRECTOTCORR", provider: "nasa_power", provider_param: "PRECTOTCORR", name: "Precipitation", category: "water", unit: "mm/day",
    definition: "Average daily rain and snow, bias-corrected using ground observations.",
    why_it_matters: "Controls water supply, drought, floods and farming.",
    source_model: "MERRA-2 corrected with GPCP", higher_means: "A wetter climate.", sort_order: 5,
  },
  {
    key: "EVLAND", provider: "nasa_power", provider_param: "EVLAND", name: "Evaporation from land", category: "water", unit: "mm/day",
    definition: "Water returned from soil and plants to the atmosphere each day.",
    why_it_matters: "Links temperature, vegetation and the water cycle.",
    source_model: "MERRA-2", higher_means: "More water leaving the land surface.", sort_order: 6,
  },
  {
    key: "GWETROOT", provider: "nasa_power", provider_param: "GWETROOT", name: "Root zone soil wetness", category: "land", unit: "fraction (0-1)",
    definition: "How saturated the soil is where plant roots grow (0 is dry, 1 is saturated).",
    why_it_matters: "Early indicator of agricultural drought and vegetation stress.",
    source_model: "MERRA-2", higher_means: "Wetter soil.", sort_order: 7,
  },
  {
    key: "RH2M", provider: "nasa_power", provider_param: "RH2M", name: "Relative humidity (2 m)", category: "atmosphere", unit: "%",
    definition: "How much water vapour the air holds compared with the maximum it could hold.",
    why_it_matters: "Affects comfort, fire risk, cloud formation and evaporation.",
    source_model: "MERRA-2", higher_means: "More humid air.", sort_order: 8,
  },
  {
    key: "WS10M", provider: "nasa_power", provider_param: "WS10M", name: "Wind speed (10 m)", category: "atmosphere", unit: "m/s",
    definition: "Average wind speed ten metres above the ground.",
    why_it_matters: "Relevant to wind energy, erosion, dust transport and storms.",
    source_model: "MERRA-2", higher_means: "Stronger winds.", sort_order: 9,
  },
  {
    key: "CLOUD_AMT", provider: "nasa_power", provider_param: "CLOUD_AMT", name: "Cloud amount", category: "atmosphere", unit: "%",
    definition: "Share of the sky covered by cloud.",
    why_it_matters: "Clouds shade the surface and trap heat, so they shape the energy budget.",
    source_model: "CERES SYN1deg", higher_means: "Cloudier skies.", sort_order: 10,
  },
  {
    key: "ALLSKY_SFC_SW_DWN", provider: "nasa_power", provider_param: "ALLSKY_SFC_SW_DWN", name: "Solar radiation at the surface", category: "energy", unit: "MJ/m^2/day",
    definition: "Sunlight energy reaching each square metre of ground per day under real sky conditions.",
    why_it_matters: "Key for solar power, plant growth and surface heating.",
    source_model: "CERES SYN1deg", higher_means: "More sunlight reaching the ground.", sort_order: 11,
  },
  {
    key: "PS", provider: "nasa_power", provider_param: "PS", name: "Surface pressure", category: "atmosphere", unit: "kPa",
    definition: "Weight of the air column pressing on the surface.",
    why_it_matters: "Pressure patterns steer weather systems and monsoons.",
    source_model: "MERRA-2", higher_means: "Higher air pressure.", sort_order: 12,
  },
];

export interface ExampleDef {
  slug: string;
  title: string;
  story: string;
  region_name: string;
  country: string | null;
  lat: number;
  lon: number;
  variable_key: string;
  start_year: number;
  end_year: number;
  sort_order: number;
}

export const EXAMPLES: ExampleDef[] = [
  {
    slug: "arctic-warming", title: "Is the Arctic warming faster?",
    story: "Svalbard sits where sea ice is retreating. Check whether its air temperature rises faster than the global average.",
    region_name: "Svalbard", country: "Norway", lat: 78.2, lon: 15.6, variable_key: "T2M", start_year: 1990, end_year: 2024, sort_order: 1,
  },
  {
    slug: "sahel-rainfall", title: "Sahel rainfall recovery",
    story: "The Sahel suffered severe droughts in the 1970s and 80s. See whether rainfall has recovered since the 1990s.",
    region_name: "Niamey", country: "Niger", lat: 13.5, lon: 2.1, variable_key: "PRECTOTCORR", start_year: 1990, end_year: 2024, sort_order: 2,
  },
  {
    slug: "amazon-drying", title: "Amazon soil moisture",
    story: "Deforestation and climate change may be drying the Amazon basin. Look at root zone soil wetness near Manaus.",
    region_name: "Manaus", country: "Brazil", lat: -3.1, lon: -60.0, variable_key: "GWETROOT", start_year: 1990, end_year: 2024, sort_order: 3,
  },
  {
    slug: "amman-heat", title: "Summer heat in Amman",
    story: "Do the hottest days in a Middle Eastern capital show a significant upward trend?",
    region_name: "Amman", country: "Jordan", lat: 31.95, lon: 35.9, variable_key: "T2M_MAX", start_year: 1990, end_year: 2024, sort_order: 4,
  },
  {
    slug: "himalaya-solar", title: "Sunlight over the Himalaya",
    story: "Cloud and aerosol changes can alter how much sunlight reaches high mountains. Check Lhasa.",
    region_name: "Lhasa", country: "China", lat: 29.65, lon: 91.1, variable_key: "ALLSKY_SFC_SW_DWN", start_year: 2001, end_year: 2024, sort_order: 5,
  },
];
