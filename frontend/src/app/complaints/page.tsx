"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import {
  FaBus,
  FaCheckCircle,
  FaClipboardList,
  FaExclamationTriangle,
  FaRobot,
  FaSearch,
} from "react-icons/fa";

type Complaint = {
  id: string;
  booking_id?: string | null;
  user_id?: string;
  category: string;
  description: string;
  priority?: string;
  status: string;
  sentiment?: string | null;
  created_at: string;
};

type ComplaintResponse = Complaint & {
  ai_category?: string;
  ai_priority?: string;
  escalated?: boolean;
  ai_used?: boolean;
};

const CATEGORIES = [
  "Bus delay",
  "Driver or conductor behaviour",
  "Overcrowding",
  "Cleanliness",
  "Lost item",
  "Ticket issue",
  "Safety concern",
  "Other",
];

export default function ComplaintsPage() {
  const [bookingId, setBookingId] = useState("");
  const [category, setCategory] =
    useState(CATEGORIES[0]);
  const [priority, setPriority] =
    useState("medium");
  const [description, setDescription] =
    useState("");

  const [complaints, setComplaints] = useState<
    Complaint[]
  >([]);

  const [result, setResult] =
    useState<ComplaintResponse | null>(null);

  const [loading, setLoading] = useState(false);
  const [loadingHistory, setLoadingHistory] =
    useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    loadComplaints();
  }, []);

  async function loadComplaints() {
    setLoadingHistory(true);

    try {
      const response = await api<Complaint[]>(
        "/api/complaints/mine"
      );

      setComplaints(response);
    } catch {
      setComplaints([]);
    } finally {
      setLoadingHistory(false);
    }
  }

  async function submitComplaint(
    event: React.FormEvent<HTMLFormElement>
  ) {
    event.preventDefault();

    setError("");
    setResult(null);

    if (!description.trim()) {
      setError(
        "Please enter a clear complaint description."
      );
      return;
    }

    setLoading(true);

    try {
      const response =
        await api<ComplaintResponse>(
          "/api/complaints",
          {
            method: "POST",
            body: JSON.stringify({
              booking_id:
                bookingId.trim() || null,
              category,
              description:
                description.trim(),
              priority,
            }),
          }
        );

      setResult(response);
      setDescription("");
      setBookingId("");
      setCategory(CATEGORIES[0]);
      setPriority("medium");

      await loadComplaints();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to submit complaint."
      );
    } finally {
      setLoading(false);
    }
  }

  const openCount = useMemo(() => {
    return complaints.filter(
      (complaint) =>
        complaint.status.toLowerCase() !==
          "resolved" &&
        complaint.status.toLowerCase() !==
          "closed"
    ).length;
  }, [complaints]);

  function formatDate(value: string) {
    return new Date(value).toLocaleString(
      "en-IN",
      {
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      }
    );
  }

  function statusClasses(status: string) {
    const normalized =
      status.toLowerCase();

    if (
      normalized === "resolved" ||
      normalized === "closed"
    ) {
      return "bg-emerald-100 text-emerald-700";
    }

    if (
      normalized === "in progress" ||
      normalized === "processing"
    ) {
      return "bg-blue-100 text-blue-700";
    }

    return "bg-amber-100 text-amber-700";
  }

  return (
    <div className="space-y-6">
      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="bg-gradient-to-r from-red-700 to-orange-500 px-6 py-6 text-white">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-white/80">
                Passenger support
              </p>

              <h1 className="mt-1 text-3xl font-bold">
                Raise a Complaint
              </h1>

              <p className="mt-2 text-sm text-white/85">
                Report delays, safety concerns,
                staff behaviour, cleanliness, or
                ticketing issues.
              </p>
            </div>

            <div className="rounded-full bg-white/15 px-4 py-2 text-sm font-semibold">
              {openCount} open complaint
              {openCount === 1 ? "" : "s"}
            </div>
          </div>
        </div>

        <div className="grid gap-6 p-5 xl:grid-cols-[1fr_0.75fr]">
          <form
            onSubmit={submitComplaint}
            className="space-y-5 rounded-2xl border border-slate-200 bg-slate-50 p-5"
          >
            <div>
              <h2 className="flex items-center gap-2 text-lg font-bold text-slate-900">
                <FaClipboardList className="text-red-600" />
                Complaint details
              </h2>

              <p className="mt-1 text-sm text-slate-500">
                Provide enough information for the
                support team to investigate.
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

            <label className="block text-sm">
              <span className="font-medium text-slate-700">
                Booking ID or PNR
              </span>

              <input
                type="text"
                value={bookingId}
                onChange={(event) =>
                  setBookingId(
                    event.target.value
                  )
                }
                placeholder="Optional"
                className="mt-1 w-full rounded-xl border border-slate-300 bg-white px-4 py-3 outline-none focus:border-red-500 focus:ring-2 focus:ring-red-100"
              />
            </label>

            <div className="grid gap-4 sm:grid-cols-2">
              <label className="block text-sm">
                <span className="font-medium text-slate-700">
                  Category
                </span>

                <select
                  value={category}
                  onChange={(event) =>
                    setCategory(
                      event.target.value
                    )
                  }
                  className="mt-1 w-full rounded-xl border border-slate-300 bg-white px-4 py-3"
                >
                  {CATEGORIES.map(
                    (item) => (
                      <option
                        key={item}
                        value={item}
                      >
                        {item}
                      </option>
                    )
                  )}
                </select>
              </label>

              <label className="block text-sm">
                <span className="font-medium text-slate-700">
                  Priority
                </span>

                <select
                  value={priority}
                  onChange={(event) =>
                    setPriority(
                      event.target.value
                    )
                  }
                  className="mt-1 w-full rounded-xl border border-slate-300 bg-white px-4 py-3"
                >
                  <option value="low">
                    Low
                  </option>
                  <option value="medium">
                    Medium
                  </option>
                  <option value="high">
                    High
                  </option>
                </select>
              </label>
            </div>

            <label className="block text-sm">
              <span className="font-medium text-slate-700">
                Description
              </span>

              <textarea
                value={description}
                onChange={(event) =>
                  setDescription(
                    event.target.value
                  )
                }
                rows={7}
                placeholder="Describe what happened, including route, bus number, location, and approximate time."
                className="mt-1 w-full resize-none rounded-xl border border-slate-300 bg-white px-4 py-3 outline-none focus:border-red-500 focus:ring-2 focus:ring-red-100"
              />
            </label>

            <button
              type="submit"
              disabled={
                loading ||
                !description.trim()
              }
              className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-red-600 px-5 py-3 font-semibold text-white hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <FaExclamationTriangle />

              {loading
                ? "Submitting complaint..."
                : "Submit complaint"}
            </button>
          </form>

          <aside className="space-y-5">
            <section className="rounded-2xl border border-blue-200 bg-blue-50 p-5">
              <h2 className="flex items-center gap-2 font-bold text-blue-900">
                <FaRobot />
                AI complaint analysis
              </h2>

              {!result ? (
                <p className="mt-3 text-sm leading-6 text-blue-900">
                  After submission, BusMate will
                  classify the issue, estimate
                  sentiment and priority, and mark
                  serious safety complaints for
                  escalation.
                </p>
              ) : (
                <div className="mt-4 space-y-3 text-sm">
                  <div className="rounded-xl bg-white p-4">
                    <p className="text-xs uppercase text-slate-500">
                      Complaint ID
                    </p>

                    <p className="mt-1 break-all font-semibold text-slate-900">
                      {result.id}
                    </p>
                  </div>

                  <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
                    <div className="rounded-xl bg-white p-4">
                      <p className="text-xs uppercase text-slate-500">
                        Category
                      </p>

                      <p className="mt-1 font-semibold text-slate-900">
                        {result.ai_category ||
                          result.category}
                      </p>
                    </div>

                    <div className="rounded-xl bg-white p-4">
                      <p className="text-xs uppercase text-slate-500">
                        Priority
                      </p>

                      <p className="mt-1 font-semibold text-slate-900">
                        {result.ai_priority ||
                          result.priority ||
                          priority}
                      </p>
                    </div>

                    <div className="rounded-xl bg-white p-4">
                      <p className="text-xs uppercase text-slate-500">
                        Sentiment
                      </p>

                      <p className="mt-1 font-semibold text-slate-900">
                        {result.sentiment ||
                          "Not analysed"}
                      </p>
                    </div>

                    <div className="rounded-xl bg-white p-4">
                      <p className="text-xs uppercase text-slate-500">
                        Escalation
                      </p>

                      <p
                        className={`mt-1 font-semibold ${
                          result.escalated
                            ? "text-red-700"
                            : "text-emerald-700"
                        }`}
                      >
                        {result.escalated
                          ? "Escalated"
                          : "Standard review"}
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </section>

            <section className="rounded-2xl border border-amber-200 bg-amber-50 p-5">
              <h2 className="font-bold text-amber-900">
                Safety notice
              </h2>

              <p className="mt-2 text-sm leading-6 text-amber-900">
                For an active emergency or immediate
                danger, contact the appropriate local
                emergency service or transport
                authority. Do not rely only on this
                project complaint form.
              </p>
            </section>
          </aside>
        </div>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="flex items-center gap-2 text-lg font-bold text-slate-900">
              <FaSearch className="text-brand-600" />
              Complaint history
            </h2>

            <p className="mt-1 text-sm text-slate-500">
              Review complaints submitted in this
              demo session.
            </p>
          </div>

          <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
            {complaints.length} total
          </span>
        </div>

        {loadingHistory ? (
          <p className="mt-5 rounded-xl bg-slate-50 p-6 text-center text-sm text-slate-500">
            Loading complaints...
          </p>
        ) : complaints.length === 0 ? (
          <p className="mt-5 rounded-xl bg-slate-50 p-6 text-center text-sm text-slate-500">
            No complaints submitted yet.
          </p>
        ) : (
          <div className="mt-5 grid gap-4 lg:grid-cols-2">
            {complaints.map(
              (complaint) => (
                <article
                  key={complaint.id}
                  className="rounded-xl border border-slate-200 bg-slate-50 p-4"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="font-bold text-slate-900">
                        {complaint.category}
                      </p>

                      <p className="mt-1 text-xs text-slate-500">
                        {formatDate(
                          complaint.created_at
                        )}
                      </p>
                    </div>

                    <span
                      className={`rounded-full px-3 py-1 text-xs font-semibold ${statusClasses(
                        complaint.status
                      )}`}
                    >
                      {complaint.status.toUpperCase()}
                    </span>
                  </div>

                  <p className="mt-4 text-sm leading-6 text-slate-700">
                    {complaint.description}
                  </p>

                  <div className="mt-4 flex flex-wrap gap-2 text-xs">
                    {complaint.priority && (
                      <span className="rounded-full bg-red-50 px-3 py-1 font-semibold text-red-700">
                        Priority:{" "}
                        {complaint.priority}
                      </span>
                    )}

                    {complaint.sentiment && (
                      <span className="rounded-full bg-blue-50 px-3 py-1 font-semibold text-blue-700">
                        Sentiment:{" "}
                        {complaint.sentiment}
                      </span>
                    )}

                    {complaint.booking_id && (
                      <span className="rounded-full bg-slate-200 px-3 py-1 font-semibold text-slate-700">
                        Booking:{" "}
                        {complaint.booking_id}
                      </span>
                    )}
                  </div>
                </article>
              )
            )}
          </div>
        )}
      </section>

      {result && (
        <div className="flex items-center gap-3 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          <FaCheckCircle />
          Complaint submitted successfully and
          added to the admin dashboard.
        </div>
      )}
    </div>
  );
}