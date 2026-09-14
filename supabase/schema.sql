CREATE TABLE IF NOT EXISTS profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id),
  user_type VARCHAR(50) DEFAULT 'farmer',
  name TEXT NOT NULL,
  phone VARCHAR(20),
  latitude FLOAT,
  longitude FLOAT,
  state VARCHAR(100),
  district VARCHAR(100),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS market_price_history (
  id SERIAL PRIMARY KEY,
  commodity VARCHAR(100) NOT NULL,
  market VARCHAR(100),
  state VARCHAR(100),
  price FLOAT NOT NULL,
  observed_at TIMESTAMP DEFAULT NOW(),
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(commodity, market, observed_at)
);

CREATE TABLE IF NOT EXISTS buyer_demand (
  id SERIAL PRIMARY KEY,
  buyer_id UUID REFERENCES auth.users(id),
  commodity VARCHAR(100) NOT NULL,
  quantity FLOAT NOT NULL,
  unit VARCHAR(50) DEFAULT 'quintals',
  price_range_min FLOAT,
  price_range_max FLOAT,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS crop_lots (
  id SERIAL PRIMARY KEY,
  farmer_id UUID REFERENCES auth.users(id) NOT NULL,
  commodity VARCHAR(100) NOT NULL,
  quantity FLOAT NOT NULL,
  unit VARCHAR(50) DEFAULT 'quintals',
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS farmer_offers (
  id SERIAL PRIMARY KEY,
  farmer_id UUID REFERENCES auth.users(id) NOT NULL,
  commodity VARCHAR(100) NOT NULL,
  quantity FLOAT NOT NULL,
  price_per_unit FLOAT,
  status VARCHAR(50) DEFAULT 'open',
  created_at TIMESTAMP DEFAULT NOW()
);

-- Enable Row Level Security
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE market_price_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE buyer_demand ENABLE ROW LEVEL SECURITY;
ALTER TABLE crop_lots ENABLE ROW LEVEL SECURITY;
ALTER TABLE farmer_offers ENABLE ROW LEVEL SECURITY;

-- RLS Policies for profiles
CREATE POLICY "Users can read own profile" ON profiles
  FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" ON profiles
  FOR UPDATE USING (auth.uid() = id);

-- RLS Policies for buyer_demand
CREATE POLICY "Buyers can read own demand" ON buyer_demand
  FOR SELECT USING (auth.uid() = buyer_id);

CREATE POLICY "Buyers can create demand" ON buyer_demand
  FOR INSERT WITH CHECK (auth.uid() = buyer_id);

-- RLS Policies for crop_lots
CREATE POLICY "Farmers can read own lots" ON crop_lots
  FOR SELECT USING (auth.uid() = farmer_id);

CREATE POLICY "Farmers can create lots" ON crop_lots
  FOR INSERT WITH CHECK (auth.uid() = farmer_id);

-- RLS Policies for farmer_offers
CREATE POLICY "Farmers can read own offers" ON farmer_offers
  FOR SELECT USING (auth.uid() = farmer_id);

CREATE POLICY "Farmers can create offers" ON farmer_offers
  FOR INSERT WITH CHECK (auth.uid() = farmer_id);

-- Public read access to market history (for predictions)
CREATE POLICY "Anyone can read market history" ON market_price_history
  FOR SELECT USING (true);

-- Create storage bucket for crop photos
INSERT INTO storage.buckets (id, name, public)
VALUES ('crop-lot-photos', 'crop-lot-photos', false)
ON CONFLICT DO NOTHING;

-- Auth trigger to create profile
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.profiles (id, user_type, name, phone)
  VALUES (
    NEW.id,
    'farmer',
    COALESCE(NEW.user_metadata ->> 'name', NEW.phone),
    NEW.phone
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
