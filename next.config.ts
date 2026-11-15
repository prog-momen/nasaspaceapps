import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  cacheComponents: true,
  partialPrefetching: true,
  // Hide the dev-only 'Cache disabled' / issue badge (it only appears in `next dev`, not in a production build).
  devIndicators: false,
  // Required: this is what compiles Tailwind. Without it every utility class is missing and the pages render unstyled.
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
