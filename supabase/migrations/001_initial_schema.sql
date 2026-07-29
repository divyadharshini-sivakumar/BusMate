-- BusMate initial schema + RLS
-- Apply via Supabase SQL editor or CLI

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Profiles (extends auth.users)
CREATE TABLE IF NOT EXISTS public.profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  full_name TEXT,
  phone TEXT,
  role TEXT NOT NULL DEFAULT 'passenger' CHECK (role IN ('passenger', 'admin')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users read own profile"
  ON public.profiles FOR SELECT
  USING (auth.uid() = id);

CREATE POLICY "Users update own profile"
  ON public.profiles FOR UPDATE
  USING (auth.uid() = id);

CREATE POLICY "Service role full access profiles"
  ON public.profiles FOR ALL
  USING (auth.jwt() ->> 'role' = 'service_role');

-- Auto-create profile on signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.profiles (id, full_name, role, phone)
  VALUES (
    NEW.id,
    COALESCE(NEW.raw_user_meta_data->>'full_name', ''),
    COALESCE(NEW.raw_user_meta_data->>'role', 'passenger'),
    NEW.raw_user_meta_data->>'phone'
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Routes / Trips
CREATE TABLE IF NOT EXISTS public.trips (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  bus_number TEXT NOT NULL,
  operator TEXT NOT NULL,
  origin TEXT NOT NULL,
  destination TEXT NOT NULL,
  departure_time TIMESTAMPTZ NOT NULL,
  arrival_time TIMESTAMPTZ NOT NULL,
  duration_minutes INT NOT NULL,
  fare NUMERIC(10,2) NOT NULL,
  available_seats INT NOT NULL DEFAULT 40,
  amenities TEXT[] DEFAULT '{}',
  bus_type TEXT DEFAULT 'AC Seater',
  seat_map JSONB DEFAULT '[]',
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE public.trips ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone authenticated can read active trips"
  ON public.trips FOR SELECT
  USING (is_active = true);

CREATE POLICY "Admin manage trips"
  ON public.trips FOR ALL
  USING (
    EXISTS (
      SELECT 1 FROM public.profiles p
      WHERE p.id = auth.uid() AND p.role = 'admin'
    )
  );

-- Bookings
CREATE TABLE IF NOT EXISTS public.bookings (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES public.profiles(id),
  trip_id UUID NOT NULL REFERENCES public.trips(id),
  seats TEXT[] NOT NULL,
  passenger_names TEXT[] NOT NULL,
  passenger_ages INT[] DEFAULT '{}',
  total_fare NUMERIC(10,2) NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'confirmed', 'cancelled', 'completed')),
  payment_method TEXT,
  payment_ref TEXT,
  pnr TEXT UNIQUE NOT NULL,
  contact_phone TEXT,
  contact_email TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE public.bookings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users read own bookings"
  ON public.bookings FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users insert own bookings"
  ON public.bookings FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Admin read all bookings"
  ON public.bookings FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM public.profiles p
      WHERE p.id = auth.uid() AND p.role = 'admin'
    )
  );

-- Tickets (derived; QR token only)
CREATE TABLE IF NOT EXISTS public.tickets (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  booking_id UUID NOT NULL REFERENCES public.bookings(id) ON DELETE CASCADE,
  seat TEXT NOT NULL,
  passenger_name TEXT NOT NULL,
  qr_token TEXT NOT NULL,
  status TEXT DEFAULT 'valid',
  created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE public.tickets ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users read own tickets via booking"
  ON public.tickets FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM public.bookings b
      WHERE b.id = booking_id AND b.user_id = auth.uid()
    )
  );

-- Complaints
CREATE TABLE IF NOT EXISTS public.complaints (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES public.profiles(id),
  booking_id UUID REFERENCES public.bookings(id),
  category TEXT NOT NULL,
  description TEXT NOT NULL,
  priority TEXT DEFAULT 'medium',
  status TEXT DEFAULT 'open',
  sentiment TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE public.complaints ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users manage own complaints"
  ON public.complaints FOR ALL
  USING (auth.uid() = user_id);

CREATE POLICY "Admin all complaints"
  ON public.complaints FOR ALL
  USING (
    EXISTS (
      SELECT 1 FROM public.profiles p
      WHERE p.id = auth.uid() AND p.role = 'admin'
    )
  );

-- Feedback
CREATE TABLE IF NOT EXISTS public.feedback (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES public.profiles(id),
  booking_id UUID REFERENCES public.bookings(id),
  rating INT CHECK (rating BETWEEN 1 AND 5),
  comment TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE public.feedback ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users manage own feedback"
  ON public.feedback FOR ALL
  USING (auth.uid() = user_id);

-- Knowledge embeddings for RAG
CREATE TABLE IF NOT EXISTS public.knowledge_chunks (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  source TEXT NOT NULL,
  content TEXT NOT NULL,
  embedding vector(384),  -- all-MiniLM-L6-v2
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS knowledge_chunks_embedding_idx
  ON public.knowledge_chunks
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

ALTER TABLE public.knowledge_chunks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Authenticated read knowledge"
  ON public.knowledge_chunks FOR SELECT
  USING (auth.role() = 'authenticated');

-- Similarity search RPC
CREATE OR REPLACE FUNCTION match_knowledge(
  query_embedding vector(384),
  match_count INT DEFAULT 4
)
RETURNS TABLE (id UUID, source TEXT, content TEXT, similarity FLOAT)
LANGUAGE sql STABLE AS $$
  SELECT
    id,
    source,
    content,
    1 - (embedding <=> query_embedding) AS similarity
  FROM public.knowledge_chunks
  ORDER BY embedding <=> query_embedding
  LIMIT match_count;
$$;
