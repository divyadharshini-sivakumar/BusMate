"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { api, BusTrip } from "@/lib/api";
import {
  FaBus,
  FaChair,
  FaClock,
  FaMapMarkerAlt,
  FaRoute,
  FaSearch,
  FaStar,
} from "react-icons/fa";

export default function SearchPage() {
  const router = useRouter();

  const [stops, setStops] = useState<string[]>([]);
  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");

  const today = useMemo(() => {
    const currentDate = new Date();

    currentDate.setMinutes(
      currentDate.getMinutes() -
        currentDate.getTimezoneOffset()
    );

    return currentDate.toISOString().split("T")[0];
  }, []);

  const [date, setDate] = useState(today);

  const [trips, setTrips] = useState<BusTrip[]>([]);
  const [loadingStops, setLoadingStops] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadStops() {
      setLoadingStops(true);
      setError("");

      try {
        const response = await api<string[]>(
          "/api/bookings/stops"
        );

        setStops(response);
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : "Unable to load MTC stops."
        );
      } finally {
        setLoadingStops(false);
      }
    }

    loadStops();
  }, []);

  function normalizeStop(value: string) {
    return value
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, " ")
      .trim()
      .replace(/\s+/g, " ");
  }

  function resolveOfficialStop(value: string) {
    const typedValue = value.trim();

    if (!typedValue) {
      return "";
    }

    const exactMatch = stops.find(
      (stop) =>
        stop.toLowerCase() === typedValue.toLowerCase()
    );

    if (exactMatch) {
      return exactMatch;
    }

    const normalizedMatch = stops.find(
      (stop) =>
        normalizeStop(stop) ===
        normalizeStop(typedValue)
    );

    return normalizedMatch ?? typedValue;
  }

  async function onSearch(
    event: React.FormEvent<HTMLFormElement>
  ) {
    event.preventDefault();

    setError("");
    setTrips([]);

    const resolvedOrigin = resolveOfficialStop(origin);
    const resolvedDestination =
      resolveOfficialStop(destination);

    if (!resolvedOrigin || !resolvedDestination) {
      setError(
        "Please enter both boarding stop and destination."
      );
      return;
    }

    if (
      normalizeStop(resolvedOrigin) ===
      normalizeStop(resolvedDestination)
    ) {
      setError(
        "Boarding stop and destination cannot be the same."
      );
      return;
    }

    setLoading(true);

    try {
      const response = await api<BusTrip[]>(
        "/api/bookings/search",
        {
          method: "POST",
          body: JSON.stringify({
            origin: resolvedOrigin,
            destination: resolvedDestination,
            travel_date: date,
            passengers: 1,
          }),
        }
      );

      setOrigin(resolvedOrigin);
      setDestination(resolvedDestination);
      setTrips(response);

      if (response.length === 0) {
        setError(
          `No direct MTC route was found from ${resolvedOrigin} to ${resolvedDestination}. Try a nearby stop or another official stop name.`
        );
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to search for buses."
      );
    } finally {
      setLoading(false);
    }
  }

  function formatDuration(minutes: number) {
    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;

    if (hours === 0) {
      return `${remainingMinutes}m`;
    }

    return `${hours}h ${remainingMinutes}m`;
  }

  function formatTime(value: string) {
    return new Date(value).toLocaleTimeString(
      "en-IN",
      {
        hour: "2-digit",
        minute: "2-digit",
      }
    );
  }

  function getQualityClasses(score?: number) {
    if (typeof score !== "number") {
      return "border-slate-200 bg-slate-50 text-slate-700";
    }

    if (score >= 90) {
      return "border-emerald-200 bg-emerald-50 text-emerald-700";
    }

    if (score >= 80) {
      return "border-blue-200 bg-blue-50 text-blue-700";
    }

    if (score >= 70) {
      return "border-amber-200 bg-amber-50 text-amber-700";
    }

    return "border-orange-200 bg-orange-50 text-orange-700";
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">
          Search Chennai MTC buses
        </h1>

        <p className="mt-1 text-sm text-slate-600">
          Enter your boarding and destination stops to
          find direct Chennai MTC routes.
        </p>
      </div>

      <form
        onSubmit={onSearch}
        className="grid gap-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm lg:grid-cols-4"
      >
        <label className="block text-sm">
          <span className="text-slate-600">
            Boarding stop
          </span>

          <input
            type="text"
            list="origin-stop-list"
            value={origin}
            disabled={loadingStops}
            onChange={(event) =>
              setOrigin(event.target.value)
            }
            autoComplete="off"
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
          />

          <datalist id="origin-stop-list">
            {stops.map((stop) => (
              <option
                key={`origin-${stop}`}
                value={stop}
              />
            ))}
          </datalist>
        </label>

        <label className="block text-sm">
          <span className="text-slate-600">
            Destination
          </span>

          <input
            type="text"
            list="destination-stop-list"
            value={destination}
            disabled={loadingStops}
            onChange={(event) =>
              setDestination(event.target.value)
            }
            autoComplete="off"
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
          />

          <datalist id="destination-stop-list">
            {stops.map((stop) => (
              <option
                key={`destination-${stop}`}
                value={stop}
              />
            ))}
          </datalist>
        </label>

        <label className="block text-sm">
          <span className="text-slate-600">
            Travel date
          </span>

          <input
            type="date"
            value={date}
            min={today}
            onChange={(event) =>
              setDate(event.target.value)
            }
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
          />
        </label>

        <div className="flex items-end">
          <button
            type="submit"
            disabled={
              loading ||
              loadingStops ||
              !origin.trim() ||
              !destination.trim()
            }
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 px-4 py-2.5 font-semibold text-white hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <FaSearch />

            {loading
              ? "Searching..."
              : "Search buses"}
          </button>
        </div>
      </form>

      <div className="rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-900">
        Start typing a stop name and select the correct
        official MTC stop from the suggestions.
      </div>

      {error && (
        <p
          className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700"
          role="alert"
        >
          {error}
        </p>
      )}

      {!loading &&
        !error &&
        trips.length > 0 && (
          <p className="text-sm text-slate-600">
            Found {trips.length} direct route
            {trips.length === 1 ? "" : "s"} from{" "}
            <strong>{origin}</strong> to{" "}
            <strong>{destination}</strong>.
          </p>
        )}

      <ul className="space-y-4">
        {trips.map((trip) => (
          <li
            key={trip.id}
            className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
          >
            <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-center">
              <div className="space-y-3">
                <div className="flex flex-wrap items-center gap-3">
                  <span className="inline-flex items-center gap-2 rounded-lg bg-brand-50 px-3 py-1.5 text-lg font-bold text-brand-700">
                    <FaRoute />
                    Route {trip.route_number}
                  </span>

                  <span className="inline-flex items-center gap-2 rounded-lg bg-slate-100 px-3 py-1 text-sm text-slate-700">
                    <FaBus />
                    {trip.bus_number}
                  </span>

                  <span className="text-sm font-medium text-slate-700">
                    {trip.operator}
                  </span>
                </div>

                <p className="flex items-center gap-2 font-medium text-slate-800">
                  <FaMapMarkerAlt className="text-brand-600" />
                  {trip.origin} → {trip.destination}
                </p>

                <p className="text-sm text-slate-600">
                  {trip.bus_type}
                </p>

                <div className="flex flex-wrap gap-4 text-sm text-slate-500">
                  <span className="inline-flex items-center gap-1">
                    <FaClock />
                    {formatTime(trip.departure_time)} →{" "}
                    {formatTime(trip.arrival_time)}
                  </span>

                  <span className="inline-flex items-center gap-1">
                    <FaClock />
                    {formatDuration(
                      trip.duration_minutes
                    )}
                  </span>

                  <span className="inline-flex items-center gap-1">
                    <FaChair />
                    {trip.available_seats} seats
                  </span>
                </div>

                {trip.stops?.length > 0 && (
                  <details className="text-sm">
                    <summary className="cursor-pointer font-medium text-brand-700">
                      View {trip.stops.length} route stops
                    </summary>

                    <div className="mt-3 flex flex-wrap gap-2">
                      {trip.stops.map((stop, index) => (
                        <span
                          key={`${trip.id}-${stop}-${index}`}
                          className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-700"
                        >
                          {index + 1}. {stop}
                        </span>
                      ))}
                    </div>
                  </details>
                )}

                <div className="flex flex-wrap gap-2">
                  {trip.amenities.map((amenity) => (
                    <span
                      key={amenity}
                      className="rounded bg-slate-100 px-2 py-1 text-xs text-slate-600"
                    >
                      {amenity}
                    </span>
                  ))}
                </div>
              </div>

              <div className="flex items-center justify-between gap-5 lg:min-w-48 lg:flex-col lg:items-end">
                <div className="space-y-3 text-right">
                  <div>
                    <p className="text-xs text-slate-500">
                      Estimated fare
                    </p>

                    <p className="text-2xl font-bold text-brand-700">
                      ₹{trip.fare}
                    </p>
                  </div>

                  {typeof trip.quality_score ===
                    "number" && (
                    <div
                      className={`rounded-lg border px-3 py-2 ${getQualityClasses(
                        trip.quality_score
                      )}`}
                    >
                      <p className="flex items-center justify-end gap-1 text-xs font-medium">
                        <FaStar />
                        BusMate Quality Score
                      </p>

                      <p className="mt-1 text-lg font-bold">
                        {trip.quality_score}/100
                      </p>

                      <p className="text-xs font-semibold">
                        {trip.quality_label}
                      </p>
                    </div>
                  )}
                </div>

                <button
                  type="button"
                  onClick={() =>
                    router.push(
                      `/book/${encodeURIComponent(
                        trip.id
                      )}`
                    )
                  }
                  className="rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-700"
                >
                  Select seats
                </button>
              </div>
            </div>

            {trip.quality_reasons &&
              trip.quality_reasons.length > 0 && (
                <details className="mt-4 border-t border-slate-100 pt-3 text-sm">
                  <summary className="cursor-pointer font-medium text-slate-700">
                    Why this quality score?
                  </summary>

                  <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-600">
                    {trip.quality_reasons.map(
                      (reason, index) => (
                        <li
                          key={`${trip.id}-quality-${index}`}
                        >
                          {reason}
                        </li>
                      )
                    )}
                  </ul>

                  {trip.quality_disclaimer && (
                    <p className="mt-2 text-xs text-slate-500">
                      {trip.quality_disclaimer}
                    </p>
                  )}
                </details>
              )}
          </li>
        ))}
      </ul>
    </div>
  );
}