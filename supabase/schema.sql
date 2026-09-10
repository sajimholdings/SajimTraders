-- ========================================================================================
--                       SAJIM TRADERS — PRODUCTION DATABASE SCHEMA
-- ========================================================================================
-- Designed for: Supabase (PostgreSQL 15+)
-- ========================================================================================

-- 1. EXTENSIONS
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ========================================================================================
-- 2. USER PROFILES TABLE (Linked directly to Supabase Auth)
-- ========================================================================================
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    full_name TEXT,
    email TEXT,
    phone TEXT,
    role TEXT DEFAULT 'trader' CHECK (role IN ('trader', 'vip', 'admin')),
    avatar_url TEXT,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_profiles_email ON public.profiles(email);

-- ========================================================================================
-- 3. TRADING ACCOUNTS TABLE (MT5 Broker Linkage)
-- ========================================================================================
CREATE TABLE IF NOT EXISTS public.trading_accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    account_id TEXT NOT NULL,                  -- MT5 Login Number (e.g. 17537803)
    account_name TEXT DEFAULT 'Trader Account',
    broker_server TEXT DEFAULT 'Headway-Real',  -- Headway-Real, Headway-Demo, Exness-Real
    broker_name TEXT DEFAULT 'Headway',
    is_demo BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Auto-Pilot Configuration
    autopilot_enabled BOOLEAN DEFAULT FALSE,
    risk_mode TEXT DEFAULT 'ULTRA_SAFE' CHECK (risk_mode IN ('ULTRA_SAFE', 'PRO_SCALP', 'MAX_YIELD')),
    fixed_lot NUMERIC(6, 2) DEFAULT 0.01,
    max_lot NUMERIC(6, 2) DEFAULT 0.05,
    max_open_trades INTEGER DEFAULT 2,
    
    -- Live Financial Telemetry (Mirrored from MT5)
    balance NUMERIC(12, 2) DEFAULT 0.00,
    equity NUMERIC(12, 2) DEFAULT 0.00,
    free_margin NUMERIC(12, 2) DEFAULT 0.00,
    currency TEXT DEFAULT 'USD',
    today_pnl NUMERIC(10, 2) DEFAULT 0.00,
    today_pnl_percent NUMERIC(6, 2) DEFAULT 0.00,
    floating_pnl NUMERIC(10, 2) DEFAULT 0.00,
    terminal_connected BOOLEAN DEFAULT FALSE,
    
    -- Encrypted Credentials / Token Vault
    encrypted_password TEXT,
    last_sync_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()),
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL,

    UNIQUE(user_id, account_id, broker_server)
);

CREATE INDEX IF NOT EXISTS idx_trading_accounts_user ON public.trading_accounts(user_id);
CREATE INDEX IF NOT EXISTS idx_trading_accounts_autopilot ON public.trading_accounts(autopilot_enabled) WHERE autopilot_enabled = TRUE;

-- ========================================================================================
-- 4. QUANTITATIVE SIGNALS TABLE (Live setups streamed to clients)
-- ========================================================================================
CREATE TABLE IF NOT EXISTS public.signals (
    id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('BUY', 'SELL')),
    entry NUMERIC(12, 5) NOT NULL,
    sl NUMERIC(12, 5) NOT NULL,
    tp NUMERIC(12, 5) NOT NULL,
    rr TEXT DEFAULT '1:2.5',
    strategy TEXT DEFAULT 'Kinetic Momentum',
    phase TEXT DEFAULT 'YOUNG_SURGE',
    win_probability TEXT DEFAULT '88.4%',
    gain_estimate_usd TEXT DEFAULT '+$12.50',
    risk_estimate_usd TEXT DEFAULT '-$4.50',
    trade_health_pct INTEGER DEFAULT 85,
    trade_explainer TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL,
    expires_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_signals_active ON public.signals(is_active, created_at DESC);

-- ========================================================================================
-- 5. ORDERS & EXECUTION QUEUE (1-Tap & Auto-Pilot Dispatches)
-- ========================================================================================
CREATE TABLE IF NOT EXISTS public.orders_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    trading_account_id UUID REFERENCES public.trading_accounts(id) ON DELETE CASCADE,
    account_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('BUY', 'SELL')),
    volume NUMERIC(6, 2) DEFAULT 0.01,
    sl NUMERIC(12, 5),
    tp NUMERIC(12, 5),
    comment TEXT DEFAULT 'Sajim_1Tap',
    status TEXT DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'PROCESSING', 'FILLED', 'REJECTED', 'CLOSED')),
    mt5_ticket BIGINT,
    open_price NUMERIC(12, 5),
    current_price NUMERIC(12, 5),
    floating_pnl NUMERIC(10, 2) DEFAULT 0.00,
    be_shield_active BOOLEAN DEFAULT FALSE,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL,
    executed_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_orders_queue_status ON public.orders_queue(status);
CREATE INDEX IF NOT EXISTS idx_orders_queue_user ON public.orders_queue(user_id);

-- ========================================================================================
-- 6. CLOSED TRADE FLIGHT RECORDER (Historical Performance)
-- ========================================================================================
CREATE TABLE IF NOT EXISTS public.trade_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    account_id TEXT NOT NULL,
    mt5_ticket BIGINT NOT NULL,
    symbol TEXT NOT NULL,
    action TEXT NOT NULL,
    volume NUMERIC(6, 2) NOT NULL,
    open_price NUMERIC(12, 5) NOT NULL,
    close_price NUMERIC(12, 5) NOT NULL,
    profit NUMERIC(10, 2) NOT NULL,
    swap NUMERIC(10, 2) DEFAULT 0.00,
    commission NUMERIC(10, 2) DEFAULT 0.00,
    net_pnl NUMERIC(10, 2) NOT NULL,
    open_time TIMESTAMPTZ NOT NULL,
    close_time TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL,
    comment TEXT
);

CREATE INDEX IF NOT EXISTS idx_trade_history_user ON public.trade_history(user_id, close_time DESC);

-- ========================================================================================
-- 7. ROW LEVEL SECURITY (RLS) POLICIES
-- ========================================================================================
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.trading_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.orders_queue ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.trade_history ENABLE ROW LEVEL SECURITY;

-- Profiles Policies
DROP POLICY IF EXISTS "Users can view own profile" ON public.profiles;
CREATE POLICY "Users can view own profile" ON public.profiles FOR SELECT USING (auth.uid() = id);

DROP POLICY IF EXISTS "Users can update own profile" ON public.profiles;
CREATE POLICY "Users can update own profile" ON public.profiles FOR UPDATE USING (auth.uid() = id);

DROP POLICY IF EXISTS "Users can insert own profile" ON public.profiles;
CREATE POLICY "Users can insert own profile" ON public.profiles FOR INSERT WITH CHECK (auth.uid() = id);

-- Trading Accounts Policies
DROP POLICY IF EXISTS "Users can view own trading accounts" ON public.trading_accounts;
CREATE POLICY "Users can view own trading accounts" ON public.trading_accounts FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert own trading accounts" ON public.trading_accounts;
CREATE POLICY "Users can insert own trading accounts" ON public.trading_accounts FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update own trading accounts" ON public.trading_accounts;
CREATE POLICY "Users can update own trading accounts" ON public.trading_accounts FOR UPDATE USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can delete own trading accounts" ON public.trading_accounts;
CREATE POLICY "Users can delete own trading accounts" ON public.trading_accounts FOR DELETE USING (auth.uid() = user_id);

-- Signals Policies (Public read for active signals)
DROP POLICY IF EXISTS "Anyone can view active signals" ON public.signals;
CREATE POLICY "Anyone can view active signals" ON public.signals FOR SELECT USING (is_active = TRUE);

-- Orders Queue Policies
DROP POLICY IF EXISTS "Users can view own orders" ON public.orders_queue;
CREATE POLICY "Users can view own orders" ON public.orders_queue FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert own orders" ON public.orders_queue;
CREATE POLICY "Users can insert own orders" ON public.orders_queue FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Trade History Policies
DROP POLICY IF EXISTS "Users can view own trade history" ON public.trade_history;
CREATE POLICY "Users can view own trade history" ON public.trade_history FOR SELECT USING (auth.uid() = user_id);

-- ========================================================================================
-- 8. AUTOMATIC PROFILE CREATION TRIGGER (Official Supabase Standard)
-- ========================================================================================
CREATE OR REPLACE FUNCTION public.handle_new_user() 
RETURNS trigger 
LANGUAGE plpgsql 
SECURITY DEFINER SET search_path = public
AS $$
BEGIN
    INSERT INTO public.profiles (id, email, full_name, avatar_url)
    VALUES (
        new.id,
        new.email,
        COALESCE(new.raw_user_meta_data->>'full_name', split_part(new.email, '@', 1)),
        new.raw_user_meta_data->>'avatar_url'
    );
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();

-- ========================================================================================
-- 9. ENABLE SUPABASE REALTIME
-- ========================================================================================
DO $$
BEGIN
    BEGIN
        ALTER PUBLICATION supabase_realtime ADD TABLE public.signals;
    EXCEPTION WHEN OTHERS THEN NULL;
    END;
    BEGIN
        ALTER PUBLICATION supabase_realtime ADD TABLE public.trading_accounts;
    EXCEPTION WHEN OTHERS THEN NULL;
    END;
    BEGIN
        ALTER PUBLICATION supabase_realtime ADD TABLE public.orders_queue;
    EXCEPTION WHEN OTHERS THEN NULL;
    END;
END $$;

-- ========================================================================================
-- 10. SEED INITIAL SIGNAL
-- ========================================================================================
INSERT INTO public.signals (
    id, symbol, timeframe, action, entry, sl, tp, rr, strategy, phase, win_probability, gain_estimate_usd, risk_estimate_usd, trade_health_pct, trade_explainer, is_active
) VALUES (
    'SIG_XAU_LIVE_01',
    'XAUUSD',
    'M1',
    'BUY',
    2684.50,
    2679.50,
    2698.00,
    '1:2.7',
    'Kinetic Micro-Surge',
    'YOUNG_SURGE',
    '88.4%',
    '+$13.50',
    '-$5.00',
    89,
    'Early trend surge detected on dynamic baseline. Enters at low maturity with +0.35R Breakeven Shield protection.',
    TRUE
) ON CONFLICT (id) DO UPDATE SET is_active = TRUE;
