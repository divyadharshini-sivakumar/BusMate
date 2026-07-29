"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, Booking, SeatInfo } from "@/lib/api";
import {
  FaArrowLeft,
  FaBus,
  FaChair,
  FaCreditCard,
  FaEnvelope,
  FaPhone,
  FaUser,
  FaWallet,
} from "react-icons/fa";
import clsx from "clsx";

type PaymentMethod = "upi" | "card" | "wallet";

type PassengerDetails = {
  name: string;
  age: string;
};

export default function BookPage() {
  const params = useParams<{ tripId: string }>();
  const router = useRouter();

  const tripId =
    typeof params.tripId === "string"
      ? decodeURIComponent(params.tripId)
      : "";

  const [seats, setSeats] = useState<SeatInfo[]>([]);
  const [selectedSeats, setSelectedSeats] = useState<string[]>([]);

  const [passengers, setPassengers] = useState<
    Record<string, PassengerDetails>
  >({});

  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");

  const [paymentMethod, setPaymentMethod] =
    useState<PaymentMethod>("upi");

  const [loadingSeats, setLoadingSeats] = useState(true);
  const [booking, setBooking] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadSeats() {
      if (!tripId) {
        setError("Invalid trip identifier.");
        setLoadingSeats(false);
        return;
      }

      setLoadingSeats(true);
      setError("");

      try {
        const response = await api<SeatInfo[]>(
          `/api/bookings/trips/${encodeURIComponent(
            tripId
          )}/seats`
        );

        setSeats(response);
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : "Unable to load seats."
        );
      } finally {
        setLoadingSeats(false);
      }
    }

    loadSeats();
  }, [tripId]);

  const farePerSeat = useMemo(() => {
    return seats[0]?.price ?? 0;
  }, [seats]);

  const totalFare = useMemo(() => {
    return selectedSeats.reduce((total, seatNumber) => {
      const seat = seats.find(
        (item) => item.seat_number === seatNumber
      );

      return total + (seat?.price ?? farePerSeat);
    }, 0);
  }, [selectedSeats, seats, farePerSeat]);

  const availableCount = useMemo(() => {
    return seats.filter((seat) => seat.is_available).length;
  }, [seats]);

  function toggleSeat(seat: SeatInfo) {
    if (!seat.is_available) {
      return;
    }

    setError("");

    setSelectedSeats((currentSeats) => {
      const alreadySelected = currentSeats.includes(
        seat.seat_number
      );

      if (alreadySelected) {
        setPassengers((currentPassengers) => {
          const updatedPassengers = {
            ...currentPassengers,
          };

          delete updatedPassengers[seat.seat_number];

          return updatedPassengers;
        });

        return currentSeats.filter(
          (seatNumber) =>
            seatNumber !== seat.seat_number
        );
      }

      setPassengers((currentPassengers) => ({
        ...currentPassengers,
        [seat.seat_number]: {
          name: "",
          age: "",
        },
      }));

      return [...currentSeats, seat.seat_number];
    });
  }

  function updatePassenger(
    seatNumber: string,
    field: keyof PassengerDetails,
    value: string
  ) {
    setPassengers((currentPassengers) => ({
      ...currentPassengers,
      [seatNumber]: {
        ...currentPassengers[seatNumber],
        [field]: value,
      },
    }));
  }

  function validateBooking(): string {
    if (selectedSeats.length === 0) {
      return "Select at least one seat.";
    }

    for (const seatNumber of selectedSeats) {
      const passenger = passengers[seatNumber];

      if (!passenger?.name.trim()) {
        return `Enter passenger name for seat ${seatNumber}.`;
      }

      const age = Number(passenger.age);

      if (
        !Number.isInteger(age) ||
        age < 1 ||
        age > 120
      ) {
        return `Enter a valid age for seat ${seatNumber}.`;
      }
    }

    if (!phone.trim()) {
      return "Enter your phone number.";
    }

    const cleanedPhone = phone.replace(/\s+/g, "");

    if (!/^\+?[0-9]{10,15}$/.test(cleanedPhone)) {
      return "Enter a valid phone number.";
    }

    if (!email.trim()) {
      return "Enter your email address.";
    }

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      return "Enter a valid email address.";
    }

    return "";
  }

  async function confirmBooking() {
    const validationError = validateBooking();

    if (validationError) {
      setError(validationError);
      return;
    }

    setBooking(true);
    setError("");

    try {
      const createdBooking = await api<Booking>(
        "/api/bookings",
        {
          method: "POST",
          body: JSON.stringify({
            trip_id: tripId,
            seat_numbers: selectedSeats,
            passenger_names: selectedSeats.map(
              (seatNumber) =>
                passengers[seatNumber].name.trim()
            ),
            passenger_ages: selectedSeats.map(
              (seatNumber) =>
                Number(passengers[seatNumber].age)
            ),
            payment_method: paymentMethod,
            contact_phone: phone.trim(),
            contact_email: email.trim(),
          }),
        }
      );

      router.push(
        `/tickets?highlight=${encodeURIComponent(
          createdBooking.id
        )}`
      );
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Booking failed."
      );
    } finally {
      setBooking(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <button
          type="button"
          onClick={() => router.back()}
          className="mb-3 inline-flex items-center gap-2 text-sm font-medium text-brand-700 hover:text-brand-800"
        >
          <FaArrowLeft />
          Back to search
        </button>

        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">
              Select your seats
            </h1>

            <p className="mt-1 text-sm text-slate-600">
              Choose seats and enter passenger details.
            </p>
          </div>

          <div className="inline-flex items-center gap-2 rounded-lg bg-brand-50 px-4 py-2 text-sm font-semibold text-brand-700">
            <FaBus />
            MTC local bus
          </div>
        </div>
      </div>

      {error && (
        <p
          className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
          role="alert"
        >
          {error}
        </p>
      )}

      {loadingSeats ? (
        <div className="rounded-xl border border-slate-200 bg-white p-10 text-center shadow-sm">
          <p className="text-sm text-slate-600">
            Loading seats...
          </p>
        </div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-bold text-slate-900">
                  Bus seat layout
                </h2>

                <p className="mt-1 text-sm text-slate-500">
                  {availableCount} of {seats.length} seats
                  available
                </p>
              </div>

              <div className="flex flex-wrap gap-3 text-xs">
                <span className="flex items-center gap-1">
                  <span className="h-3 w-3 rounded bg-emerald-100 ring-1 ring-emerald-300" />
                  Available
                </span>

                <span className="flex items-center gap-1">
                  <span className="h-3 w-3 rounded bg-brand-600" />
                  Selected
                </span>

                <span className="flex items-center gap-1">
                  <span className="h-3 w-3 rounded bg-slate-200" />
                  Booked
                </span>

                <span className="flex items-center gap-1">
                  <span className="h-3 w-3 rounded bg-pink-100 ring-1 ring-pink-300" />
                  Women
                </span>
              </div>
            </div>

            <div className="mx-auto mt-6 max-w-sm rounded-[2rem] border-4 border-slate-300 bg-slate-50 p-5">
              <div className="mb-6 flex justify-end">
                <div className="flex h-12 w-12 items-center justify-center rounded-full border-4 border-slate-400 bg-white text-xs font-bold text-slate-500">
                  Driver
                </div>
              </div>

              {seats.length === 0 ? (
                <p className="py-10 text-center text-sm text-slate-500">
                  No seat information available.
                </p>
              ) : (
                <div className="grid grid-cols-4 gap-3">
                  {seats.map((seat) => {
                    const isSelected =
                      selectedSeats.includes(
                        seat.seat_number
                      );

                    return (
                      <button
                        key={seat.seat_number}
                        type="button"
                        disabled={!seat.is_available}
                        onClick={() => toggleSeat(seat)}
                        aria-label={`Seat ${seat.seat_number}`}
                        aria-pressed={isSelected}
                        className={clsx(
                          "flex h-11 items-center justify-center rounded-lg border text-xs font-bold transition",
                          !seat.is_available &&
                            "cursor-not-allowed border-slate-200 bg-slate-200 text-slate-400",
                          seat.is_available &&
                            isSelected &&
                            "border-brand-700 bg-brand-600 text-white ring-2 ring-brand-200",
                          seat.is_available &&
                            !isSelected &&
                            seat.gender_preference ===
                              "female" &&
                            "border-pink-300 bg-pink-100 text-pink-800 hover:bg-pink-200",
                          seat.is_available &&
                            !isSelected &&
                            seat.gender_preference !==
                              "female" &&
                            "border-emerald-300 bg-emerald-100 text-emerald-800 hover:bg-emerald-200"
                        )}
                      >
                        <FaChair className="mr-1" />
                        {seat.seat_number}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          </section>

          <aside className="space-y-5">
            <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="text-lg font-bold text-slate-900">
                Booking summary
              </h2>

              <div className="mt-4 space-y-3 text-sm">
                <div className="flex justify-between gap-4">
                  <span className="text-slate-500">
                    Selected seats
                  </span>

                  <span className="font-semibold text-slate-900">
                    {selectedSeats.length > 0
                      ? selectedSeats.join(", ")
                      : "None"}
                  </span>
                </div>

                <div className="flex justify-between gap-4">
                  <span className="text-slate-500">
                    Fare per seat
                  </span>

                  <span className="font-semibold text-slate-900">
                    ₹{farePerSeat.toFixed(0)}
                  </span>
                </div>

                <div className="border-t border-slate-200 pt-3">
                  <div className="flex justify-between">
                    <span className="font-semibold text-slate-800">
                      Total fare
                    </span>

                    <span className="text-2xl font-bold text-brand-700">
                      ₹{totalFare.toFixed(0)}
                    </span>
                  </div>
                </div>
              </div>
            </section>

            <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="text-lg font-bold text-slate-900">
                Contact information
              </h2>

              <p className="mt-1 text-sm text-slate-500">
                Your ticket details will be sent to these
                contact details.
              </p>

              <div className="mt-4 space-y-4">
                <label className="block text-sm">
                  <span className="flex items-center gap-2 font-medium text-slate-700">
                    <FaPhone />
                    Phone number
                  </span>

                  <input
                    type="tel"
                    placeholder="Enter your phone number"
                    value={phone}
                    onChange={(event) =>
                      setPhone(event.target.value)
                    }
                    className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
                  />
                </label>

                <label className="block text-sm">
                  <span className="flex items-center gap-2 font-medium text-slate-700">
                    <FaEnvelope />
                    Email address
                  </span>

                  <input
                    type="email"
                    placeholder="Enter your email address"
                    value={email}
                    onChange={(event) =>
                      setEmail(event.target.value)
                    }
                    className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
                  />
                </label>
              </div>
            </section>
          </aside>
        </div>
      )}

      {selectedSeats.length > 0 && (
        <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-lg font-bold text-slate-900">
            Passenger details
          </h2>

          <p className="mt-1 text-sm text-slate-500">
            Enter one passenger for every selected seat.
          </p>

          <div className="mt-4 grid gap-4 md:grid-cols-2">
            {selectedSeats.map((seatNumber) => (
              <div
                key={seatNumber}
                className="rounded-lg border border-slate-200 bg-slate-50 p-4"
              >
                <p className="mb-3 flex items-center gap-2 font-bold text-brand-700">
                  <FaChair />
                  Seat {seatNumber}
                </p>

                <div className="grid gap-3 sm:grid-cols-[1fr_110px]">
                  <label className="block text-sm">
                    <span className="flex items-center gap-2 text-slate-600">
                      <FaUser />
                      Passenger name
                    </span>

                    <input
                      type="text"
                      placeholder="Enter passenger name"
                      value={
                        passengers[seatNumber]?.name ?? ""
                      }
                      onChange={(event) =>
                        updatePassenger(
                          seatNumber,
                          "name",
                          event.target.value
                        )
                      }
                      className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
                    />
                  </label>

                  <label className="block text-sm">
                    <span className="text-slate-600">
                      Age
                    </span>

                    <input
                      type="number"
                      min={1}
                      max={120}
                      placeholder="Age"
                      value={
                        passengers[seatNumber]?.age ?? ""
                      }
                      onChange={(event) =>
                        updatePassenger(
                          seatNumber,
                          "age",
                          event.target.value
                        )
                      }
                      className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
                    />
                  </label>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-lg font-bold text-slate-900">
          Payment method
        </h2>

        <p className="mt-1 text-sm text-slate-500">
          Payment is simulated for this project.
        </p>

        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <button
            type="button"
            onClick={() => setPaymentMethod("upi")}
            className={clsx(
              "flex items-center gap-3 rounded-lg border p-4 text-left transition",
              paymentMethod === "upi"
                ? "border-brand-600 bg-brand-50 text-brand-700 ring-2 ring-brand-100"
                : "border-slate-200 text-slate-700 hover:border-brand-300"
            )}
          >
            <FaWallet />
            <span className="font-semibold">UPI</span>
          </button>

          <button
            type="button"
            onClick={() => setPaymentMethod("card")}
            className={clsx(
              "flex items-center gap-3 rounded-lg border p-4 text-left transition",
              paymentMethod === "card"
                ? "border-brand-600 bg-brand-50 text-brand-700 ring-2 ring-brand-100"
                : "border-slate-200 text-slate-700 hover:border-brand-300"
            )}
          >
            <FaCreditCard />
            <span className="font-semibold">
              Debit / credit card
            </span>
          </button>

          <button
            type="button"
            onClick={() => setPaymentMethod("wallet")}
            className={clsx(
              "flex items-center gap-3 rounded-lg border p-4 text-left transition",
              paymentMethod === "wallet"
                ? "border-brand-600 bg-brand-50 text-brand-700 ring-2 ring-brand-100"
                : "border-slate-200 text-slate-700 hover:border-brand-300"
            )}
          >
            <FaWallet />
            <span className="font-semibold">
              Digital wallet
            </span>
          </button>
        </div>
      </section>

      <div className="sticky bottom-4 flex flex-col gap-3 rounded-xl border border-slate-200 bg-white/95 p-4 shadow-lg backdrop-blur sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm text-slate-500">
            {selectedSeats.length} seat
            {selectedSeats.length === 1 ? "" : "s"} selected
          </p>

          <p className="text-xl font-bold text-slate-900">
            Total ₹{totalFare.toFixed(0)}
          </p>
        </div>

        <button
          type="button"
          disabled={
            booking ||
            loadingSeats ||
            selectedSeats.length === 0
          }
          onClick={confirmBooking}
          className="rounded-lg bg-brand-600 px-7 py-3 font-semibold text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {booking
            ? "Confirming booking..."
            : "Confirm and pay"}
        </button>
      </div>
    </div>
  );
}