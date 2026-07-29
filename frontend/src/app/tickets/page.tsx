"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { QRCodeSVG } from "qrcode.react";
import { api, Booking } from "@/lib/api";
import {
  FaBus,
  FaCalendarAlt,
  FaChair,
  FaCheckCircle,
  FaClock,
  FaEnvelope,
  FaFilePdf,
  FaMapMarkerAlt,
  FaPhone,
  FaQrcode,
  FaRoute,
  FaUser,
} from "react-icons/fa";

export default function TicketsPage() {
  const searchParams = useSearchParams();
  const highlightedBookingId = searchParams.get("highlight");

  const [bookings, setBookings] = useState<Booking[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [otpMsg, setOtpMsg] = useState("");

  useEffect(() => {
    async function loadBookings() {
      setLoading(true);
      setError("");

      try {
        const response = await api<Booking[]>(
          "/api/bookings/mine"
        );

        setBookings(response);
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : "Unable to load tickets."
        );
      } finally {
        setLoading(false);
      }
    }

    loadBookings();
  }, []);

  async function sendOtp(id: string) {
    setOtpMsg("");

    try {
      const response = await api<{
        demo_otp: string;
        message: string;
      }>(
        `/api/tickets/send-otp?booking_id=${encodeURIComponent(
          id
        )}`,
        {
          method: "POST",
        }
      );

      setOtpMsg(
        response.demo_otp
          ? `${response.message} OTP: ${response.demo_otp}`
          : response.message
      );
    } catch (err) {
      setOtpMsg(
        err instanceof Error
          ? err.message
          : "Unable to generate OTP."
      );
    }
  }

  const backend =
    process.env.NEXT_PUBLIC_BACKEND_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    "http://localhost:8000";

  const sortedBookings = useMemo(() => {
    return [...bookings].sort((a, b) => {
      if (a.id === highlightedBookingId) {
        return -1;
      }

      if (b.id === highlightedBookingId) {
        return 1;
      }

      return (
        new Date(b.created_at).getTime() -
        new Date(a.created_at).getTime()
      );
    });
  }, [bookings, highlightedBookingId]);

  function formatDate(value?: string | null) {
    if (!value) {
      return "Not available";
    }

    return new Date(value).toLocaleDateString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  }

  function formatTime(value?: string | null) {
    if (!value) {
      return "Not available";
    }

    return new Date(value).toLocaleTimeString("en-IN", {
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function bookingPassengers(booking: Booking) {
    const names = booking.passenger_names ?? [];

    if (names.length === 0) {
      return "Passenger";
    }

    return names.join(", ");
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">
          My Tickets
        </h1>

        <p className="mt-1 text-sm text-slate-600">
          View your confirmed Chennai MTC bookings and
          journey details.
        </p>
      </div>

      {error && (
        <p
          className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
          role="alert"
        >
          {error}
        </p>
      )}

      {otpMsg && (
        <p className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          {otpMsg}
        </p>
      )}

      {loading && (
        <div className="rounded-xl border border-slate-200 bg-white p-10 text-center shadow-sm">
          <p className="text-sm text-slate-600">
            Loading your tickets...
          </p>
        </div>
      )}

      {!loading && !bookings.length && !error && (
        <div className="rounded-xl border border-slate-200 bg-white p-8 text-center shadow-sm">
          <FaBus className="mx-auto text-4xl text-slate-300" />

          <h2 className="mt-4 text-lg font-bold text-slate-900">
            No bookings yet
          </h2>

          <p className="mt-1 text-sm text-slate-600">
            Search for an MTC route and book your first
            ticket.
          </p>

          <Link
            href="/search"
            className="mt-5 inline-flex rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-700"
          >
            Search buses
          </Link>
        </div>
      )}

      <ul className="space-y-6">
        {sortedBookings.map((booking) => {
          const isHighlighted =
            booking.id === highlightedBookingId;

          const qrPayload = JSON.stringify({
            booking_id: booking.id,
            pnr: booking.pnr,
            route_number: booking.route_number ?? "MTC",
            bus_number: booking.bus_number ?? "",
            seats: booking.seats,
            origin: booking.origin ?? "",
            destination: booking.destination ?? "",
            status: booking.status,
          });

          return (
            <li
              key={booking.id}
              className={`overflow-hidden rounded-2xl border bg-white shadow-sm ${
                isHighlighted
                  ? "border-brand-500 ring-2 ring-brand-100"
                  : "border-slate-200"
              }`}
            >
              <div className="bg-gradient-to-r from-brand-700 to-brand-500 px-5 py-4 text-white">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.2em] text-white/80">
                      Chennai MTC e-ticket
                    </p>

                    <h2 className="mt-1 text-2xl font-bold">
                      BusMate
                    </h2>
                  </div>

                  <div className="rounded-full bg-white/15 px-4 py-2 text-sm font-semibold">
                    {booking.status.toUpperCase()}
                  </div>
                </div>
              </div>

              <div className="grid gap-6 p-5 lg:grid-cols-[1fr_250px]">
                <div className="space-y-6">
                  <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                    <div>
                      <p className="text-xs uppercase tracking-wide text-slate-500">
                        PNR
                      </p>

                      <p className="mt-1 font-bold text-slate-900">
                        {booking.pnr}
                      </p>
                    </div>

                    <div>
                      <p className="text-xs uppercase tracking-wide text-slate-500">
                        Route
                      </p>

                      <p className="mt-1 inline-flex items-center gap-2 font-bold text-brand-700">
                        <FaRoute />
                        {booking.route_number ?? "MTC"}
                      </p>
                    </div>

                    <div>
                      <p className="text-xs uppercase tracking-wide text-slate-500">
                        Bus number
                      </p>

                      <p className="mt-1 inline-flex items-center gap-2 font-semibold text-slate-900">
                        <FaBus />
                        {booking.bus_number ?? "Not available"}
                      </p>
                    </div>

                    <div>
                      <p className="text-xs uppercase tracking-wide text-slate-500">
                        Fare
                      </p>

                      <p className="mt-1 text-xl font-bold text-brand-700">
                        ₹{booking.total_fare}
                      </p>
                    </div>
                  </div>

                  <div className="grid gap-5 rounded-xl bg-slate-50 p-4 md:grid-cols-[1fr_auto_1fr] md:items-center">
                    <div>
                      <p className="text-xs uppercase tracking-wide text-slate-500">
                        Boarding
                      </p>

                      <p className="mt-2 flex items-start gap-2 font-bold text-slate-900">
                        <FaMapMarkerAlt className="mt-1 text-emerald-600" />
                        {booking.origin ?? "Not available"}
                      </p>

                      <p className="mt-2 inline-flex items-center gap-2 text-sm text-slate-600">
                        <FaClock />
                        {formatTime(booking.departure_time)}
                      </p>
                    </div>

                    <div className="hidden text-2xl text-slate-300 md:block">
                      →
                    </div>

                    <div>
                      <p className="text-xs uppercase tracking-wide text-slate-500">
                        Destination
                      </p>

                      <p className="mt-2 flex items-start gap-2 font-bold text-slate-900">
                        <FaMapMarkerAlt className="mt-1 text-red-500" />
                        {booking.destination ?? "Not available"}
                      </p>

                      <p className="mt-2 inline-flex items-center gap-2 text-sm text-slate-600">
                        <FaClock />
                        {formatTime(booking.arrival_time)}
                      </p>
                    </div>
                  </div>

                  <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    <div className="rounded-xl border border-slate-200 p-4">
                      <p className="flex items-center gap-2 text-sm font-semibold text-slate-700">
                        <FaUser />
                        Passenger
                      </p>

                      <p className="mt-2 text-sm text-slate-900">
                        {bookingPassengers(booking)}
                      </p>
                    </div>

                    <div className="rounded-xl border border-slate-200 p-4">
                      <p className="flex items-center gap-2 text-sm font-semibold text-slate-700">
                        <FaChair />
                        Seat
                      </p>

                      <p className="mt-2 text-sm font-bold text-slate-900">
                        {booking.seats.join(", ")}
                      </p>
                    </div>

                    <div className="rounded-xl border border-slate-200 p-4">
                      <p className="flex items-center gap-2 text-sm font-semibold text-slate-700">
                        <FaCalendarAlt />
                        Travel date
                      </p>

                      <p className="mt-2 text-sm text-slate-900">
                        {formatDate(booking.departure_time)}
                      </p>
                    </div>

                    <div className="rounded-xl border border-slate-200 p-4">
                      <p className="flex items-center gap-2 text-sm font-semibold text-slate-700">
                        <FaPhone />
                        Phone
                      </p>

                      <p className="mt-2 break-all text-sm text-slate-900">
                        {booking.contact_phone ??
                          "Not available"}
                      </p>
                    </div>

                    <div className="rounded-xl border border-slate-200 p-4">
                      <p className="flex items-center gap-2 text-sm font-semibold text-slate-700">
                        <FaEnvelope />
                        Email
                      </p>

                      <p className="mt-2 break-all text-sm text-slate-900">
                        {booking.contact_email ??
                          "Not available"}
                      </p>
                    </div>

                    <div className="rounded-xl border border-slate-200 p-4">
                      <p className="flex items-center gap-2 text-sm font-semibold text-slate-700">
                        <FaCheckCircle />
                        Booked on
                      </p>

                      <p className="mt-2 text-sm text-slate-900">
                        {formatDate(booking.created_at)}
                      </p>
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-3">
                    <a
                      href={`${backend}/api/tickets/booking/${booking.id}/pdf`}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
                    >
                      <FaFilePdf />
                      Download PDF
                    </a>

                    <Link
                      href={`/track/${booking.id}`}
                      className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700"
                    >
                      <FaMapMarkerAlt />
                      Track bus
                    </Link>

                    <button
                      type="button"
                      onClick={() => sendOtp(booking.id)}
                      className="inline-flex items-center gap-2 rounded-lg border border-brand-300 bg-brand-50 px-4 py-2 text-sm font-semibold text-brand-700 hover:bg-brand-100"
                    >
                      <FaQrcode />
                      Generate OTP
                    </button>
                  </div>
                </div>

                <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50 p-5 text-center">
                  <div className="rounded-xl bg-white p-3 shadow-sm">
                    <QRCodeSVG
                      value={qrPayload}
                      size={170}
                      bgColor="#ffffff"
                      fgColor="#111827"
                      level="H"
                      includeMargin
                      title={`Ticket QR for ${booking.pnr}`}
                    />
                  </div>

                  <p className="mt-5 text-base font-bold text-slate-900">
                    Scan to verify
                  </p>

                  <p className="mt-2 text-sm font-semibold text-brand-700">
                    {booking.pnr}
                  </p>

                  <p className="mt-2 text-xs text-slate-500">
                    Secure ticket-verification QR
                  </p>

                  <p className="mt-1 text-xs text-slate-500">
                    Contains no OTP, secrets, or sensitive
                    passenger data.
                  </p>

                  <p className="mt-4 text-xs text-slate-500">
                    Show this ticket during boarding.
                  </p>
                </div>
              </div>

              <div className="border-t border-dashed border-slate-300 bg-slate-50 px-5 py-3">
                <div className="flex flex-wrap justify-between gap-2 text-xs text-slate-500">
                  <span>
                    Payment:{" "}
                    {booking.payment_method.toUpperCase()}
                  </span>

                  <span>
                    Reference:{" "}
                    {booking.payment_ref ??
                      "Not available"}
                  </span>

                  <span>
                    Booking ID: {booking.id}
                  </span>
                </div>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}