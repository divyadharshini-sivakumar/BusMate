export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  "http://127.0.0.1:8000";

export async function api<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${path}`;

  const response = await fetch(url, {
    ...options,
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });

  if (!response.ok) {
    const errorText = await response.text();

    throw new Error(
      errorText ||
        `Request failed with status ${response.status}`
    );
  }

  return response.json() as Promise<T>;
}

export type BusTrip = {
  id: string;
  route_number: string;
  bus_number: string;
  operator: string;
  origin: string;
  destination: string;
  departure_time: string;
  arrival_time: string;
  duration_minutes: number;
  fare: number;
  available_seats: number;
  amenities: string[];
  bus_type: string;
  stops: string[];
};

export type SeatInfo = {
  seat_number: string;
  is_available: boolean;
  gender_preference: "any" | "male" | "female";
  price: number;
};

export type Booking = {
  id: string;
  trip_id: string;
  user_id: string;
  pnr: string;
  seats: string[];
  passenger_names?: string[];
  passenger_ages?: number[];
  contact_phone?: string;
  contact_email?: string;
  total_fare: number;
  status: string;
  payment_method: string;
  payment_ref?: string;
  route_number?: string;
  bus_number?: string;
  operator?: string;
  bus_type?: string;
  origin?: string;
  destination?: string;
  departure_time?: string;
  arrival_time?: string;
  duration_minutes?: number;
  created_at: string;
};

export type AgentReply = {
  intent: string;
  reply: string;
  agent: string;
  data?: Record<string, unknown>;
  escalated: boolean;
  ai_used: boolean;
  session_id: string;
};