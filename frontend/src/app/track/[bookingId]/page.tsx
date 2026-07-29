"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import { api } from "@/lib/api";
import {
  FaArrowLeft,
  FaBell,
  FaBus,
  FaClock,
  FaMapMarkerAlt,
  FaRoad,
  FaRoute,
  FaTachometerAlt,
} from "react-icons/fa";

const MapView = dynamic(
  () => import("@/components/MapView"),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-full items-center justify-center bg-slate-100 text-sm text-slate-500">
        Loading map...
      </div>
    ),
  }
);

type TrackingPoint = {
  lat: number;
  lng: number;
  timestamp: string;
  speed_kmh?: number;
};

type TimelineEvent = {
  event: string;
  location: string;
  time: string | null;
  done: boolean;
};

type Tracking = {
  booking_id: string;
  bus_number: string;
  current: TrackingPoint;
  eta_minutes: number;
  progress_percent: number;
  next_stop?: string;
  timeline: TimelineEvent[];
};

type TrackingAlert = {
  type: string;
  message: string;
};

export default function TrackPage() {
  const params = useParams<{ bookingId: string }>();
  const router = useRouter();

  const bookingId =
    typeof params.bookingId === "string"
      ? decodeURIComponent(params.bookingId)
      : "";

  const [data, setData] = useState<Tracking | null>(null);
  const [alerts, setAlerts] = useState<TrackingAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let isMounted = true;

    async function loadTracking(showRefresh = false) {
      if (!bookingId) {
        setError("Invalid booking identifier.");
        setLoading(false);
        return;
      }

      if (showRefresh) {
        setRefreshing(true);
      }

      try {
        const trackingResponse = await api<Tracking>(
          `/api/tracking/${encodeURIComponent(
            bookingId
          )}`
        );

        const alertResponse = await api<{
          alerts: TrackingAlert[];
        }>(
          `/api/tracking/${encodeURIComponent(
            bookingId
          )}/alerts`
        );

        if (!isMounted) {
          return;
        }

        setData(trackingResponse);
        setAlerts(alertResponse.alerts ?? []);
        setError("");
      } catch (err) {
        if (!isMounted) {
          return;
        }

        setError(
          err instanceof Error
            ? err.message
            : "Unable to load live tracking."
        );
      } finally {
        if (isMounted) {
          setLoading(false);
          setRefreshing(false);
        }
      }
    }

    loadTracking();

    const intervalId = window.setInterval(() => {
      loadTracking(true);
    }, 10000);

    return () => {
      isMounted = false;
      window.clearInterval(intervalId);
    };
  }, [bookingId]);

  const completedStops = useMemo(() => {
    return data?.timeline.filter((event) => event.done).length ?? 0;
  }, [data]);

  const totalStops = data?.timeline.length ?? 0;

  function formatTime(value?: string | null) {
    if (!value) {
      return "Pending";
    }

    return new Date(value).toLocaleTimeString("en-IN", {
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function progressValue(value: number) {
    return Math.min(100, Math.max(0, value));
  }

  if (loading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-10 text-center shadow-sm">
        <p className="text-sm text-slate-600">
          Loading live tracking...
        </p>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="space-y-4">
        <button
          type="button"
          onClick={() => router.back()}
          className="inline-flex items-center gap-2 text-sm font-semibold text-brand-700"
        >
          <FaArrowLeft />
          Back
        </button>

        <p
          className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
          role="alert"
        >
          {error}
        </p>
      </div>
    );
  }

  if (!data) {
    return null;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <button
            type="button"
            onClick={() => router.back()}
            className="mb-3 inline-flex items-center gap-2 text-sm font-semibold text-brand-700 hover:text-brand-800"
          >
            <FaArrowLeft />
            Back to ticket
          </button>

          <h1 className="text-2xl font-bold text-slate-900">
            Live bus tracking
          </h1>

          <p className="mt-1 text-sm text-slate-600">
            Simulated real-time location for bus{" "}
            <span className="font-semibold">
              {data.bus_number}
            </span>
          </p>
        </div>

        <div className="inline-flex items-center gap-2 rounded-full bg-emerald-50 px-4 py-2 text-sm font-semibold text-emerald-700">
          <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-emerald-500" />
          {refreshing ? "Updating..." : "Live"}
        </div>
      </div>

      {error && (
        <p
          className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800"
          role="alert"
        >
          Showing the last available location. {error}
        </p>
      )}

      <div className="grid gap-6 xl:grid-cols-[1.25fr_0.75fr]">
        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-5 py-4">
            <div>
              <h2 className="flex items-center gap-2 text-lg font-bold text-slate-900">
                <FaMapMarkerAlt className="text-brand-600" />
                Current bus position
              </h2>

              <p className="mt-1 text-sm text-slate-500">
                Location updates automatically every 10
                seconds.
              </p>
            </div>

            <div className="rounded-lg bg-brand-50 px-3 py-2 text-sm font-semibold text-brand-700">
              <FaBus className="mr-2 inline" />
              {data.bus_number}
            </div>
          </div>

          <div className="h-[420px] sm:h-[520px]">
            <MapView
              lat={data.current.lat}
              lng={data.current.lng}
            />
          </div>
        </section>

        <aside className="space-y-5">
          <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="text-lg font-bold text-slate-900">
              Journey status
            </h2>

            <div className="mt-5 space-y-5">
              <div>
                <div className="flex items-center justify-between gap-3 text-sm">
                  <span className="font-medium text-slate-600">
                    Route progress
                  </span>

                  <span className="font-bold text-brand-700">
                    {Math.round(
                      progressValue(data.progress_percent)
                    )}
                    %
                  </span>
                </div>

                <div className="mt-2 h-3 overflow-hidden rounded-full bg-slate-100">
                  <div
                    className="h-full rounded-full bg-brand-600 transition-all duration-700"
                    style={{
                      width: `${progressValue(
                        data.progress_percent
                      )}%`,
                    }}
                  />
                </div>

                <p className="mt-2 text-xs text-slate-500">
                  {completedStops} of {totalStops} timeline
                  events completed
                </p>
              </div>

              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
                <div className="rounded-xl bg-blue-50 p-4">
                  <p className="flex items-center gap-2 text-sm font-semibold text-blue-800">
                    <FaClock />
                    Estimated arrival
                  </p>

                  <p className="mt-2 text-3xl font-bold text-blue-900">
                    {data.eta_minutes} min
                  </p>
                </div>

                <div className="rounded-xl bg-emerald-50 p-4">
                  <p className="flex items-center gap-2 text-sm font-semibold text-emerald-800">
                    <FaTachometerAlt />
                    Current speed
                  </p>

                  <p className="mt-2 text-3xl font-bold text-emerald-900">
                    {Math.round(
                      data.current.speed_kmh ?? 0
                    )}{" "}
                    <span className="text-base">km/h</span>
                  </p>
                </div>
              </div>

              <div className="rounded-xl border border-slate-200 p-4">
                <p className="flex items-center gap-2 text-sm font-semibold text-slate-700">
                  <FaMapMarkerAlt />
                  Next stop
                </p>

                <p className="mt-2 text-lg font-bold text-slate-900">
                  {data.next_stop || "Destination"}
                </p>
              </div>

              <div className="rounded-xl border border-slate-200 p-4">
                <p className="flex items-center gap-2 text-sm font-semibold text-slate-700">
                  <FaClock />
                  Last updated
                </p>

                <p className="mt-2 text-sm text-slate-900">
                  {formatTime(data.current.timestamp)}
                </p>

                <p className="mt-1 text-xs text-slate-500">
                  Coordinates:{" "}
                  {data.current.lat.toFixed(5)},{" "}
                  {data.current.lng.toFixed(5)}
                </p>
              </div>
            </div>
          </section>

          {alerts.length > 0 && (
            <section className="rounded-2xl border border-amber-200 bg-amber-50 p-5">
              <h2 className="flex items-center gap-2 font-bold text-amber-900">
                <FaBell />
                Journey alerts
              </h2>

              <ul className="mt-3 space-y-2">
                {alerts.map((alert, index) => (
                  <li
                    key={`${alert.type}-${index}`}
                    className="rounded-lg bg-white/70 px-3 py-2 text-sm text-amber-900"
                  >
                    {alert.message}
                  </li>
                ))}
              </ul>
            </section>
          )}
        </aside>
      </div>

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="flex items-center gap-2 text-lg font-bold text-slate-900">
              <FaRoute className="text-brand-600" />
              Route timeline
            </h2>

            <p className="mt-1 text-sm text-slate-500">
              Follow the bus journey from boarding to
              destination.
            </p>
          </div>

          <div className="inline-flex items-center gap-2 rounded-lg bg-slate-100 px-3 py-2 text-xs font-semibold text-slate-600">
            <FaRoad />
            {totalStops} events
          </div>
        </div>

        <ol className="mt-6 space-y-0">
          {data.timeline.map((event, index) => {
            const isLast =
              index === data.timeline.length - 1;

            return (
              <li
                key={`${event.event}-${event.location}-${index}`}
                className="relative flex gap-4 pb-6 last:pb-0"
              >
                {!isLast && (
                  <span
                    className={`absolute left-[9px] top-5 h-full w-0.5 ${
                      event.done
                        ? "bg-emerald-400"
                        : "bg-slate-200"
                    }`}
                  />
                )}

                <span
                  className={`relative z-10 mt-1 h-5 w-5 shrink-0 rounded-full border-4 ${
                    event.done
                      ? "border-emerald-100 bg-emerald-500"
                      : "border-slate-100 bg-slate-300"
                  }`}
                />

                <div className="flex-1 rounded-xl border border-slate-200 bg-slate-50 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p
                        className={`font-bold ${
                          event.done
                            ? "text-slate-900"
                            : "text-slate-600"
                        }`}
                      >
                        {event.event}
                      </p>

                      <p className="mt-1 flex items-center gap-2 text-sm text-slate-600">
                        <FaMapMarkerAlt />
                        {event.location}
                      </p>
                    </div>

                    <span
                      className={`rounded-full px-3 py-1 text-xs font-semibold ${
                        event.done
                          ? "bg-emerald-100 text-emerald-700"
                          : "bg-slate-200 text-slate-600"
                      }`}
                    >
                      {event.done
                        ? formatTime(event.time)
                        : "Upcoming"}
                    </span>
                  </div>
                </div>
              </li>
            );
          })}
        </ol>
      </section>

      <div className="rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-900">
        Live location, speed, ETA, and alerts are simulated
        for this BusMate project demonstration.
      </div>
    </div>
  );
}