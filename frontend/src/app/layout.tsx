import type { Metadata } from "next";
import "./globals.css";
import { Nav } from "@/components/Nav";

export const metadata: Metadata = {
  title: "BusMate – Smart Bus Booking",
  description:
    "Book buses, track journeys, and get AI assistance – scoped to bus travel only.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <Nav />
        <main className="mx-auto min-h-[calc(100vh-4rem)] max-w-6xl px-4 py-6">
          {children}
        </main>
        <footer className="border-t border-slate-200 bg-white py-6 text-center text-sm text-slate-500">
          BusMate · Demo (Chennai region) · Not a general-purpose chatbot
        </footer>
      </body>
    </html>
  );
}
