"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  FaBrain,
  FaBus,
  FaChartBar,
  FaChartLine,
  FaComments,
  FaExclamationTriangle,
  FaMoneyBillWave,
  FaRoute,
  FaStar,
  FaTicketAlt,
  FaUsers,
} from "react-icons/fa";
import { api } from "@/lib/api";

type Stats = {
  total_bookings: number;
  active_trips: number;
  open_complaints: number;
  revenue_today: number;
  occupancy_rate: number;
};

type Booking = {
  id: string;
  pnr: string;
  route_number?: string | null;
  bus_number?: string | null;
  origin?: string | null;
  destination?: string | null;
  seats: string[];
  passenger_names?: string[];
  total_fare: number;
  status: string;
  created_at: string;
};

type Complaint = {
  id?: string;
  category?: string;
  description?: string;
  status?: string;
  priority?: string;
  sentiment?: string;
  created_at?: string;
};

type Feedback = {
  id?: string;
  rating?: number;
  comment?: string;
  sentiment?: string;
  created_at?: string;
};

type Trip = {
  id?: string;
  route_number?: string;
  bus_number?: string;
  origin?: string;
  destination?: string;
  available_seats?: number;
  fare?: number | null;
};

const CHART_COLORS = [
  "#2563EB",
  "#F59E0B",
  "#10B981",
  "#EF4444",
  "#8B5CF6",
  "#06B6D4",
];

export default function AdminPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [trips, setTrips] = useState<Trip[]>([]);
  const [complaints, setComplaints] = useState<
    Complaint[]
  >([]);
  const [feedback, setFeedback] = useState<Feedback[]>(
    []
  );

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadDashboard() {
      setLoading(true);
      setError("");

      const results = await Promise.allSettled([
        api<Stats>("/api/admin/stats"),
        api<Trip[]>("/api/admin/trips"),
        api<Booking[]>("/api/admin/bookings"),
        api<Complaint[]>("/api/admin/complaints"),
        api<Feedback[]>("/api/admin/feedback"),
      ]);

      const [
        statsResult,
        tripsResult,
        bookingsResult,
        complaintsResult,
        feedbackResult,
      ] = results;

      if (statsResult.status === "fulfilled") {
        setStats(statsResult.value);
      }

      if (tripsResult.status === "fulfilled") {
        setTrips(tripsResult.value);
      }

      if (bookingsResult.status === "fulfilled") {
        setBookings(bookingsResult.value);
      }

      if (complaintsResult.status === "fulfilled") {
        setComplaints(complaintsResult.value);
      }

      if (feedbackResult.status === "fulfilled") {
        setFeedback(feedbackResult.value);
      }

      const failedRequests = results.filter(
        (result) => result.status === "rejected"
      );

      if (failedRequests.length === results.length) {
        setError(
          "Unable to load the admin dashboard. Check that the backend is running."
        );
      } else if (failedRequests.length > 0) {
        setError(
          "Some dashboard information is temporarily unavailable."
        );
      }

      setLoading(false);
    }

    loadDashboard();
  }, []);

  const recentBookings = useMemo(() => {
    return [...bookings]
      .sort(
        (first, second) =>
          new Date(second.created_at).getTime() -
          new Date(first.created_at).getTime()
      )
      .slice(0, 6);
  }, [bookings]);

  const passengerCount = useMemo(() => {
    return bookings.reduce(
      (total, booking) =>
        total + (booking.seats?.length ?? 0),
      0
    );
  }, [bookings]);

  const totalRevenue = useMemo(() => {
    return bookings.reduce(
      (total, booking) =>
        total + Number(booking.total_fare || 0),
      0
    );
  }, [bookings]);

  const averageRating = useMemo(() => {
    const ratings = feedback
      .map((item) => Number(item.rating))
      .filter(
        (rating) =>
          Number.isFinite(rating) && rating > 0
      );

    if (ratings.length === 0) {
      return 0;
    }

    return (
      ratings.reduce(
        (total, rating) => total + rating,
        0
      ) / ratings.length
    );
  }, [feedback]);

  const popularRoutes = useMemo(() => {
    const routeCounts = new Map<string, number>();

    bookings.forEach((booking) => {
      const route =
        booking.route_number?.trim() || "Unknown";

      routeCounts.set(
        route,
        (routeCounts.get(route) || 0) + 1
      );
    });

    return Array.from(routeCounts.entries())
      .map(([route, bookingsCount]) => ({
        route: `Route ${route}`,
        bookings: bookingsCount,
      }))
      .sort(
        (first, second) =>
          second.bookings - first.bookings
      )
      .slice(0, 6);
  }, [bookings]);

  const dailyAnalytics = useMemo(() => {
    const dailyValues = new Map<
      string,
      {
        date: string;
        bookings: number;
        revenue: number;
      }
    >();

    bookings.forEach((booking) => {
      const dateObject = new Date(
        booking.created_at
      );

      const dateKey = dateObject.toLocaleDateString(
        "en-IN",
        {
          day: "2-digit",
          month: "short",
        }
      );

      const existing = dailyValues.get(dateKey) ?? {
        date: dateKey,
        bookings: 0,
        revenue: 0,
      };

      existing.bookings += 1;
      existing.revenue += Number(
        booking.total_fare || 0
      );

      dailyValues.set(dateKey, existing);
    });

    return Array.from(dailyValues.values()).slice(-7);
  }, [bookings]);

  const complaintCategories = useMemo(() => {
    const categoryCounts = new Map<string, number>();

    complaints.forEach((complaint) => {
      const category =
        complaint.category || "Other";

      categoryCounts.set(
        category,
        (categoryCounts.get(category) || 0) + 1
      );
    });

    return [...categoryCounts.entries()]
      .map(([category, value]) => ({
        category,
        value,
      }))
      .sort(
        (first, second) =>
          second.value - first.value
      );
  }, [complaints]);

  const ratingDistribution = useMemo(() => {
    const distribution = [1, 2, 3, 4, 5].map(
      (rating) => ({
        rating: `${rating} star`,
        responses: 0,
      })
    );

    feedback.forEach((item) => {
      const rating = Number(item.rating);

      if (rating >= 1 && rating <= 5) {
        distribution[rating - 1].responses += 1;
      }
    });

    return distribution;
  }, [feedback]);

  const dashboardStats = [
    {
      label: "Total bookings",
      value:
        stats?.total_bookings ?? bookings.length,
      detail: "Confirmed demo bookings",
      icon: <FaTicketAlt />,
    },
    {
      label: "Passengers",
      value: passengerCount,
      detail: "Across all booked seats",
      icon: <FaUsers />,
    },
    {
      label: "Revenue",
      value: `₹${Math.round(
        stats?.revenue_today ?? totalRevenue
      )}`,
      detail: "Current demo revenue",
      icon: <FaMoneyBillWave />,
    },
    {
      label: "Active routes",
      value: stats?.active_trips ?? trips.length,
      detail: "Imported MTC routes",
      icon: <FaRoute />,
    },
    {
      label: "Open complaints",
      value:
        stats?.open_complaints ??
        complaints.filter(
          (complaint) =>
            !["resolved", "closed"].includes(
              (
                complaint.status || "open"
              ).toLowerCase()
            )
        ).length,
      detail: "Awaiting admin action",
      icon: <FaExclamationTriangle />,
    },
    {
      label: "Occupancy",
      value: `${Math.round(
        stats?.occupancy_rate ?? 0
      )}%`,
      detail: "Current demo estimate",
      icon: <FaBus />,
    },
  ];

  function formatDate(value?: string) {
    if (!value) {
      return "Not available";
    }

    return new Date(value).toLocaleDateString(
      "en-IN",
      {
        day: "2-digit",
        month: "short",
        year: "numeric",
      }
    );
  }

  if (loading) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-12 text-center shadow-sm">
        <p className="text-sm text-slate-600">
          Loading admin analytics...
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="bg-gradient-to-r from-slate-950 via-slate-900 to-brand-800 px-6 py-7 text-white">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-white/70">
                BusMate operations
              </p>

              <h1 className="mt-1 text-3xl font-bold">
                Admin Dashboard
              </h1>

              <p className="mt-2 text-sm text-white/75">
                Monitor bookings, revenue, passenger
                feedback, complaints, routes, and AI
                services.
              </p>
            </div>

            <div className="rounded-full bg-emerald-500/20 px-4 py-2 text-sm font-semibold text-emerald-100">
              System operational
            </div>
          </div>
        </div>

        <div className="p-5">
          {error && (
            <p className="mb-5 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
              {error}
            </p>
          )}

          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {dashboardStats.map((item) => (
              <div
                key={item.label}
                className="rounded-2xl border border-slate-200 bg-slate-50 p-5"
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      {item.label}
                    </p>

                    <p className="mt-2 text-3xl font-bold text-slate-900">
                      {item.value}
                    </p>

                    <p className="mt-1 text-xs text-slate-500">
                      {item.detail}
                    </p>
                  </div>

                  <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-100 text-lg text-brand-700">
                    {item.icon}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div>
            <h2 className="flex items-center gap-2 text-lg font-bold text-slate-900">
              <FaChartLine className="text-brand-600" />
              Daily bookings
            </h2>

            <p className="mt-1 text-sm text-slate-500">
              Booking activity during the current demo
              session.
            </p>
          </div>

          <div className="mt-5 h-72">
            {dailyAnalytics.length === 0 ? (
              <div className="flex h-full items-center justify-center rounded-xl bg-slate-50 text-sm text-slate-500">
                Create bookings to display this chart.
              </div>
            ) : (
              <ResponsiveContainer
                width="100%"
                height="100%"
              >
                <LineChart data={dailyAnalytics}>
                  <CartesianGrid
                    strokeDasharray="3 3"
                  />

                  <XAxis
                    dataKey="date"
                    fontSize={12}
                  />

                  <YAxis
                    allowDecimals={false}
                    fontSize={12}
                  />

                  <Tooltip />

                  <Line
                    type="monotone"
                    dataKey="bookings"
                    stroke="#2563EB"
                    strokeWidth={3}
                    dot={{
                      r: 5,
                    }}
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div>
            <h2 className="flex items-center gap-2 text-lg font-bold text-slate-900">
              <FaMoneyBillWave className="text-emerald-600" />
              Revenue analytics
            </h2>

            <p className="mt-1 text-sm text-slate-500">
              Revenue generated from confirmed bookings.
            </p>
          </div>

          <div className="mt-5 h-72">
            {dailyAnalytics.length === 0 ? (
              <div className="flex h-full items-center justify-center rounded-xl bg-slate-50 text-sm text-slate-500">
                Revenue data will appear after bookings.
              </div>
            ) : (
              <ResponsiveContainer
                width="100%"
                height="100%"
              >
                <BarChart data={dailyAnalytics}>
                  <CartesianGrid
                    strokeDasharray="3 3"
                  />

                  <XAxis
                    dataKey="date"
                    fontSize={12}
                  />

                  <YAxis fontSize={12} />

                  <Tooltip
                    formatter={(value) => [
                      `₹${value}`,
                      "Revenue",
                    ]}
                  />

                  <Bar
                    dataKey="revenue"
                    fill="#10B981"
                    radius={[8, 8, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div>
            <h2 className="flex items-center gap-2 text-lg font-bold text-slate-900">
              <FaRoute className="text-brand-600" />
              Popular routes
            </h2>

            <p className="mt-1 text-sm text-slate-500">
              Routes ranked by number of bookings.
            </p>
          </div>

          <div className="mt-5 h-72">
            {popularRoutes.length === 0 ? (
              <div className="flex h-full items-center justify-center rounded-xl bg-slate-50 text-sm text-slate-500">
                Popular routes will appear after
                bookings.
              </div>
            ) : (
              <ResponsiveContainer
                width="100%"
                height="100%"
              >
                <BarChart
                  data={popularRoutes}
                  layout="vertical"
                  margin={{
                    left: 15,
                  }}
                >
                  <CartesianGrid
                    strokeDasharray="3 3"
                  />

                  <XAxis
                    type="number"
                    allowDecimals={false}
                  />

                  <YAxis
                    type="category"
                    dataKey="route"
                    width={95}
                    fontSize={12}
                  />

                  <Tooltip />

                  <Bar
                    dataKey="bookings"
                    fill="#2563EB"
                    radius={[0, 8, 8, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div>
            <h2 className="flex items-center gap-2 text-lg font-bold text-slate-900">
              <FaStar className="text-amber-500" />
              Rating distribution
            </h2>

            <p className="mt-1 text-sm text-slate-500">
              Passenger ratings from 1 to 5 stars.
            </p>
          </div>

          <div className="mt-5 h-72">
            {feedback.length === 0 ? (
              <div className="flex h-full items-center justify-center rounded-xl bg-slate-50 text-sm text-slate-500">
                Submit feedback to display ratings.
              </div>
            ) : (
              <ResponsiveContainer
                width="100%"
                height="100%"
              >
                <BarChart data={ratingDistribution}>
                  <CartesianGrid
                    strokeDasharray="3 3"
                  />

                  <XAxis
                    dataKey="rating"
                    fontSize={12}
                  />

                  <YAxis
                    allowDecimals={false}
                    fontSize={12}
                  />

                  <Tooltip />

                  <Bar
                    dataKey="responses"
                    fill="#F59E0B"
                    radius={[8, 8, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[0.8fr_1.2fr]">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div>
            <h2 className="flex items-center gap-2 text-lg font-bold text-slate-900">
              <FaComments className="text-red-500" />
              Complaint categories
            </h2>

            <p className="mt-1 text-sm text-slate-500">
              Distribution of passenger complaints.
            </p>
          </div>

          <div className="mt-5 h-72">
            {complaintCategories.length === 0 ? (
              <div className="flex h-full items-center justify-center rounded-xl bg-slate-50 text-sm text-slate-500">
                Complaint analytics will appear after
                submissions.
              </div>
            ) : (
              <ResponsiveContainer
                width="100%"
                height="100%"
              >
                <PieChart>
                  <Pie
                    data={complaintCategories}
                    dataKey="value"
                    nameKey="category"
                    outerRadius={100}
                    label
                  >
                    {complaintCategories.map(
                      (_, index) => (
                        <Cell
                          key={index}
                          fill={
                            CHART_COLORS[
                              index %
                                CHART_COLORS.length
                            ]
                          }
                        />
                      )
                    )}
                  </Pie>

                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="flex items-center gap-2 text-lg font-bold text-slate-900">
                <FaTicketAlt className="text-brand-600" />
                Recent bookings
              </h2>

              <p className="mt-1 text-sm text-slate-500">
                Latest confirmed passenger bookings.
              </p>
            </div>

            <span className="rounded-full bg-brand-50 px-3 py-1 text-xs font-semibold text-brand-700">
              {bookings.length} total
            </span>
          </div>

          {recentBookings.length === 0 ? (
            <p className="mt-5 rounded-xl bg-slate-50 p-8 text-center text-sm text-slate-500">
              No bookings available yet.
            </p>
          ) : (
            <div className="mt-5 overflow-x-auto">
              <table className="w-full min-w-[760px] text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
                    <th className="px-3 py-3">
                      PNR
                    </th>

                    <th className="px-3 py-3">
                      Route
                    </th>

                    <th className="px-3 py-3">
                      Journey
                    </th>

                    <th className="px-3 py-3">
                      Passengers
                    </th>

                    <th className="px-3 py-3">
                      Fare
                    </th>

                    <th className="px-3 py-3">
                      Status
                    </th>

                    <th className="px-3 py-3">
                      Booked
                    </th>
                  </tr>
                </thead>

                <tbody>
                  {recentBookings.map((booking) => (
                    <tr
                      key={booking.id}
                      className="border-b border-slate-100 last:border-0"
                    >
                      <td className="px-3 py-4 font-bold text-slate-900">
                        {booking.pnr}
                      </td>

                      <td className="px-3 py-4 font-semibold text-brand-700">
                        {booking.route_number ||
                          "MTC"}
                      </td>

                      <td className="px-3 py-4 text-slate-600">
                        {booking.origin ||
                          "Unknown"}{" "}
                        →{" "}
                        {booking.destination ||
                          "Unknown"}
                      </td>

                      <td className="px-3 py-4 text-slate-600">
                        {booking.passenger_names?.join(
                          ", "
                        ) ||
                          `${booking.seats.length} passenger(s)`}
                      </td>

                      <td className="px-3 py-4 font-semibold text-slate-900">
                        ₹{booking.total_fare}
                      </td>

                      <td className="px-3 py-4">
                        <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-700">
                          {booking.status.toUpperCase()}
                        </span>
                      </td>

                      <td className="px-3 py-4 text-slate-500">
                        {formatDate(
                          booking.created_at
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="flex items-center gap-2 text-lg font-bold text-slate-900">
            <FaStar className="text-amber-500" />
            Passenger feedback summary
          </h2>

          <div className="mt-5 flex items-end gap-3">
            <p className="text-5xl font-bold text-slate-900">
              {averageRating > 0
                ? averageRating.toFixed(1)
                : "—"}
            </p>

            <p className="pb-1 text-sm text-slate-500">
              from {feedback.length} response
              {feedback.length === 1 ? "" : "s"}
            </p>
          </div>

          <div className="mt-4 flex gap-1 text-xl">
            {[1, 2, 3, 4, 5].map((star) => (
              <FaStar
                key={star}
                className={
                  averageRating >= star
                    ? "text-amber-400"
                    : "text-slate-200"
                }
              />
            ))}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="flex items-center gap-2 text-lg font-bold text-slate-900">
            <FaBrain className="text-purple-600" />
            AI and platform status
          </h2>

          <div className="mt-5 grid gap-3 sm:grid-cols-2">
            {[
              ["LangGraph", "Operational"],
              ["CrewAI", "Available"],
              ["MTC route engine", "Operational"],
              ["RAG knowledge base", "Available"],
              ["OpenRouter", "Fallback enabled"],
              ["Tracking engine", "Simulated live"],
            ].map(([service, status]) => (
              <div
                key={service}
                className="rounded-xl border border-slate-200 bg-slate-50 p-4"
              >
                <p className="text-sm font-semibold text-slate-900">
                  {service}
                </p>

                <p className="mt-2 flex items-center gap-2 text-xs font-medium text-emerald-700">
                  <span className="h-2 w-2 rounded-full bg-emerald-500" />
                  {status}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <div className="rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-900">
        Analytics use the current in-memory demo data and
        reset whenever the backend restarts.
      </div>
    </div>
  );
}