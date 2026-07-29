"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { api, BusTrip as BaseBusTrip } from "@/lib/api";


type BusTrip = BaseBusTrip & {
  quality_score?: number | null;
  quality_label?: string | null;
  quality_reasons?: string[];
  quality_disclaimer?: string | null;
};

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