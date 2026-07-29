"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import {
  FaCheckCircle,
  FaCommentDots,
  FaStar,
} from "react-icons/fa";

type FeedbackItem = {
  id: string;
  booking_id?: string | null;
  user_id?: string;
  rating: number;
  comment?: string | null;
  created_at: string;
};

export default function FeedbackPage() {
  const [bookingId, setBookingId] = useState("");
  const [rating, setRating] = useState(5);
  const [hoveredRating, setHoveredRating] =
    useState<number | null>(null);
  const [comment, setComment] = useState("");

  const [feedback, setFeedback] = useState<
    FeedbackItem[]
  >([]);

  const [loading, setLoading] = useState(false);
  const [loadingHistory, setLoadingHistory] =
    useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    loadFeedback();
  }, []);

  async function loadFeedback() {
    setLoadingHistory(true);

    try {
      const response = await api<FeedbackItem[]>(
        "/api/feedback/mine"
      );

      setFeedback(response);
    } catch {
      setFeedback([]);
    } finally {
      setLoadingHistory(false);
    }
  }

  async function submitFeedback(
    event: React.FormEvent<HTMLFormElement>
  ) {
    event.preventDefault();

    setError("");
    setSuccess("");

    if (rating < 1 || rating > 5) {
      setError("Please select a rating from 1 to 5.");
      return;
    }

    setLoading(true);

    try {
      await api<FeedbackItem>("/api/feedback", {
        method: "POST",
        body: JSON.stringify({
          booking_id: bookingId.trim() || null,
          rating,
          comment: comment.trim() || null,
        }),
      });

      setSuccess(
        "Feedback submitted successfully and added to the admin dashboard."
      );

      setBookingId("");
      setRating(5);
      setComment("");

      await loadFeedback();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to submit feedback."
      );
    } finally {
      setLoading(false);
    }
  }

  const averageRating = useMemo(() => {
    if (feedback.length === 0) {
      return 0;
    }

    return (
      feedback.reduce(
        (total, item) => total + item.rating,
        0
      ) / feedback.length
    );
  }, [feedback]);

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

  function ratingText(value: number) {
    if (value === 5) return "Excellent";
    if (value === 4) return "Very good";
    if (value === 3) return "Good";
    if (value === 2) return "Needs improvement";
    return "Poor";
  }

  return (
    <div className="space-y-6">
      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="bg-gradient-to-r from-amber-500 to-orange-500 px-6 py-6 text-white">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-white/85">
                Passenger experience
              </p>

              <h1 className="mt-1 text-3xl font-bold">
                Share Feedback
              </h1>

              <p className="mt-2 text-sm text-white/90">
                Rate your journey, booking experience,
                tracking, or BusMate support.
              </p>
            </div>

            <div className="rounded-full bg-white/20 px-4 py-2 text-sm font-semibold">
              {feedback.length} response
              {feedback.length === 1 ? "" : "s"}
            </div>
          </div>
        </div>

        <div className="grid gap-6 p-5 xl:grid-cols-[1fr_0.7fr]">
          <form
            onSubmit={submitFeedback}
            className="space-y-5 rounded-2xl border border-slate-200 bg-slate-50 p-5"
          >
            <div>
              <h2 className="flex items-center gap-2 text-lg font-bold text-slate-900">
                <FaCommentDots className="text-amber-500" />
                Feedback details
              </h2>

              <p className="mt-1 text-sm text-slate-500">
                Tell us what worked well and what could be improved.
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
                  setBookingId(event.target.value)
                }
                placeholder="Optional"
                className="mt-1 w-full rounded-xl border border-slate-300 bg-white px-4 py-3 outline-none focus:border-amber-500 focus:ring-2 focus:ring-amber-100"
              />
            </label>

            <div>
              <p className="text-sm font-medium text-slate-700">
                Your rating
              </p>

              <div className="mt-3 flex flex-wrap items-center gap-3">
                <div className="flex gap-2">
                  {[1, 2, 3, 4, 5].map(
                    (star) => {
                      const active =
                        star <=
                        (hoveredRating ?? rating);

                      return (
                        <button
                          key={star}
                          type="button"
                          onMouseEnter={() =>
                            setHoveredRating(star)
                          }
                          onMouseLeave={() =>
                            setHoveredRating(null)
                          }
                          onClick={() =>
                            setRating(star)
                          }
                          className="text-3xl transition hover:scale-110"
                          aria-label={`${star} star rating`}
                        >
                          <FaStar
                            className={
                              active
                                ? "text-amber-400"
                                : "text-slate-300"
                            }
                          />
                        </button>
                      );
                    }
                  )}
                </div>

                <span className="rounded-full bg-amber-100 px-3 py-1 text-sm font-semibold text-amber-800">
                  {ratingText(
                    hoveredRating ?? rating
                  )}
                </span>
              </div>
            </div>

            <label className="block text-sm">
              <span className="font-medium text-slate-700">
                Comment
              </span>

              <textarea
                value={comment}
                onChange={(event) =>
                  setComment(event.target.value)
                }
                rows={7}
                placeholder="Share your experience with the route, bus, ticket, tracking, staff, or BusMate application."
                className="mt-1 w-full resize-none rounded-xl border border-slate-300 bg-white px-4 py-3 outline-none focus:border-amber-500 focus:ring-2 focus:ring-amber-100"
              />
            </label>

            <button
              type="submit"
              disabled={loading}
              className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-amber-500 px-5 py-3 font-semibold text-white hover:bg-amber-600 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <FaStar />

              {loading
                ? "Submitting feedback..."
                : "Submit feedback"}
            </button>
          </form>

          <aside className="space-y-5">
            <section className="rounded-2xl border border-amber-200 bg-amber-50 p-5">
              <h2 className="font-bold text-amber-900">
                Average rating
              </h2>

              <div className="mt-4 flex items-end gap-3">
                <p className="text-5xl font-bold text-slate-900">
                  {averageRating > 0
                    ? averageRating.toFixed(1)
                    : "—"}
                </p>

                <p className="pb-1 text-sm text-slate-600">
                  out of 5
                </p>
              </div>

              <div className="mt-4 flex gap-1 text-2xl">
                {[1, 2, 3, 4, 5].map(
                  (star) => (
                    <FaStar
                      key={star}
                      className={
                        averageRating >= star
                          ? "text-amber-400"
                          : "text-slate-300"
                      }
                    />
                  )
                )}
              </div>

              <p className="mt-3 text-sm text-amber-900">
                Based on {feedback.length} submitted response
                {feedback.length === 1 ? "" : "s"}.
              </p>
            </section>

            <section className="rounded-2xl border border-blue-200 bg-blue-50 p-5">
              <h2 className="font-bold text-blue-900">
                How feedback is used
              </h2>

              <p className="mt-2 text-sm leading-6 text-blue-900">
                Feedback helps identify popular routes,
                service issues, app usability problems, and
                areas where BusMate can improve.
              </p>
            </section>
          </aside>
        </div>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="flex items-center gap-2 text-lg font-bold text-slate-900">
              <FaStar className="text-amber-500" />
              Feedback history
            </h2>

            <p className="mt-1 text-sm text-slate-500">
              Review feedback submitted in this demo session.
            </p>
          </div>

          <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
            {feedback.length} total
          </span>
        </div>

        {loadingHistory ? (
          <p className="mt-5 rounded-xl bg-slate-50 p-6 text-center text-sm text-slate-500">
            Loading feedback...
          </p>
        ) : feedback.length === 0 ? (
          <p className="mt-5 rounded-xl bg-slate-50 p-6 text-center text-sm text-slate-500">
            No feedback submitted yet.
          </p>
        ) : (
          <div className="mt-5 grid gap-4 lg:grid-cols-2">
            {feedback.map((item) => (
              <article
                key={item.id}
                className="rounded-xl border border-slate-200 bg-slate-50 p-4"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="flex gap-1">
                      {[1, 2, 3, 4, 5].map(
                        (star) => (
                          <FaStar
                            key={star}
                            className={
                              star <= item.rating
                                ? "text-amber-400"
                                : "text-slate-300"
                            }
                          />
                        )
                      )}
                    </div>

                    <p className="mt-2 text-sm font-semibold text-slate-900">
                      {ratingText(item.rating)}
                    </p>

                    <p className="mt-1 text-xs text-slate-500">
                      {formatDate(item.created_at)}
                    </p>
                  </div>

                  <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-800">
                    {item.rating}/5
                  </span>
                </div>

                <p className="mt-4 text-sm leading-6 text-slate-700">
                  {item.comment ||
                    "No written comment provided."}
                </p>

                {item.booking_id && (
                  <p className="mt-4 text-xs font-semibold text-slate-500">
                    Booking: {item.booking_id}
                  </p>
                )}
              </article>
            ))}
          </div>
        )}
      </section>

      {success && (
        <div className="flex items-center gap-3 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          <FaCheckCircle />
          {success}
        </div>
      )}
    </div>
  );
}