import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Astro EARTH - Earth System Trend Detective",
  description: "Pick any place on Earth, choose a NASA variable, and test whether it is changing significantly.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full">
      <body className="min-h-full flex flex-col font-sans antialiased bg-[#000000] text-[#f4f4f5]">
        {children}
      </body>
    </html>
  );
}
