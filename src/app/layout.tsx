import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "3D Earth - World Explorer",
  description: "Interactive 3D Earth with world regions, search, and navigation",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full">
      <body className="min-h-full flex flex-col font-sans antialiased bg-[#0b0f19] text-[#e2e8f0]">
        {children}
      </body>
    </html>
  );
}
