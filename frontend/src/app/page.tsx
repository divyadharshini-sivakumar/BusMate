"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { FaBus, FaMapMarkedAlt, FaRobot, FaShieldAlt } from "react-icons/fa";

const features = [
  {
    icon: FaBus,
    title: "Search & Book",
    desc: "Chennai-region routes with interactive seat maps and simulated payments.",
  },
  {
    icon: FaMapMarkedAlt,
    title: "Live Tracking",
    desc: "ETA, journey timeline, and destination alerts on an OpenStreetMap view.",
  },
  {
    icon: FaRobot,
    title: "Scoped AI Assistant",
    desc: "Booking, tickets, policy, complaints only – never a general chatbot.",
  },
  {
    icon: FaShieldAlt,
    title: "Secure Tickets",
    desc: "PDF + QR verification tokens with no OTP or sensitive data embedded.",
  },
];

export default function HomePage() {
  return (
    <div className="space-y-12">
      <section className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-brand-600 to-brand-900 px-6 py-14 text-white shadow-lg sm:px-12">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
            Travel smarter with BusMate
          </h1>
          <p className="mt-3 max-w-xl text-brand-100">
            Book seats, track your bus, download secure tickets, and get
            journey help – built for passengers and admins.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link
              href="/search"
              className="rounded-xl bg-white px-5 py-2.5 font-semibold text-brand-700 shadow hover:bg-brand-50"
            >
              Search buses
            </Link>
            <Link
              href="/assistant"
              className="rounded-xl border border-white/40 px-5 py-2.5 font-semibold text-white hover:bg-white/10"
            >
              Ask assistant
            </Link>
          </div>
        </motion.div>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {features.map((f, i) => (
          <motion.div
            key={f.title}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 * i }}
            className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
          >
            <f.icon className="text-2xl text-brand-600" aria-hidden />
            <h2 className="mt-3 font-semibold">{f.title}</h2>
            <p className="mt-1 text-sm text-slate-600">{f.desc}</p>
          </motion.div>
        ))}
      </section>

      
    </div>
  );
}
