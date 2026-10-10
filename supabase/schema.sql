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
    margin_level NUMERIC(12, 2) DEFAULT 0.00,
    terminal_connected BOOLEAN DEFAULT FALSE,
    
    -- Encrypted Credentials / Token Vault
    encrypted_password TEXT,
    last_sync_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()),
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL,

    -- An MT5 login on a given server can be linked by exactly ONE user.
    CONSTRAINT trading_accounts_account_server_key UNIQUE (account_id, broker_server)
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
CREATE INDEX IF NOT EXISTS idx_signals_expires ON public.signals(expires_at);

-- ========================================================================================
-- 5. ORDERS & EXECUTION QUEUE (1-Tap & Auto-Pilot Dispatches)
-- ========================================================================================
CREATE TABLE IF NOT EXISTS public.orders_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    trading_account_id UUID REFERENCES public.trading_accounts(id) ON DELETE CASCADE,
    account_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('BUY', 'SELL', 'CLOSE')),
    volume NUMERIC(6, 2) DEFAULT 0.01,
    sl NUMERIC(12, 5),
    tp NUMERIC(12, 5),
    comment TEXT DEFAULT 'Sajim_1Tap',
    status TEXT DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'PROCESSING', 'FILLED', 'REJECTED', 'FAILED', 'CLOSED')),
    mt5_ticket BIGINT,
    close_ticket BIGINT,
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
    comment TEXT,

    -- One history row per closed MT5 position (bridge reconciliation is idempotent).
    CONSTRAINT trade_history_account_ticket_key UNIQUE (account_id, mt5_ticket)
);

CREATE INDEX IF NOT EXISTS idx_trade_history_user ON public.trade_history(user_id, close_time DESC);

-- ========================================================================================
-- 6b. IDEMPOTENT MIGRATIONS (safe to re-run on databases created by older schema.sql)
-- ========================================================================================
ALTER TABLE public.trading_accounts ADD COLUMN IF NOT EXISTS margin_level NUMERIC(12, 2) DEFAULT 0.00;
ALTER TABLE public.trading_accounts ADD COLUMN IF NOT EXISTS floating_pnl NUMERIC(10, 2) DEFAULT 0.00;
ALTER TABLE public.signals ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ;
ALTER TABLE public.orders_queue ADD COLUMN IF NOT EXISTS close_ticket BIGINT;

ALTER TABLE public.orders_queue DROP CONSTRAINT IF EXISTS orders_queue_action_check;
ALTER TABLE public.orders_queue ADD CONSTRAINT orders_queue_action_check
    CHECK (action IN ('BUY', 'SELL', 'CLOSE'));
ALTER TABLE public.orders_queue DROP CONSTRAINT IF EXISTS orders_queue_status_check;
ALTER TABLE public.orders_queue ADD CONSTRAINT orders_queue_status_check
    CHECK (status IN ('PENDING', 'PROCESSING', 'FILLED', 'REJECTED', 'FAILED', 'CLOSED'));

-- Exclusive MT5 ownership: replace the old per-user UNIQUE(user_id, account_id, broker_server)
-- with UNIQUE(account_id, broker_server).
-- NOTE: if two users already linked the same login+server, this ADD CONSTRAINT fails. Resolve
-- duplicates first, e.g.:
--   SELECT account_id, broker_server, array_agg(user_id) FROM public.trading_accounts
--   GROUP BY 1, 2 HAVING count(*) > 1;
ALTER TABLE public.trading_accounts DROP CONSTRAINT IF EXISTS trading_accounts_user_id_account_id_broker_server_key;
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'trading_accounts_account_server_key'
          AND conrelid = 'public.trading_accounts'::regclass
    ) THEN
        ALTER TABLE public.trading_accounts
            ADD CONSTRAINT trading_accounts_account_server_key UNIQUE (account_id, broker_server);
    END IF;
END $$;

-- De-duplicate trade_history (keep the earliest row per account/ticket), then enforce uniqueness.
DELETE FROM public.trade_history a
USING public.trade_history b
WHERE a.account_id = b.account_id
  AND a.mt5_ticket = b.mt5_ticket
  AND (a.close_time, a.id) > (b.close_time, b.id);
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'trade_history_account_ticket_key'
          AND conrelid = 'public.trade_history'::regclass
    ) THEN
        ALTER TABLE public.trade_history
            ADD CONSTRAINT trade_history_account_ticket_key UNIQUE (account_id, mt5_ticket);
    END IF;
END $$;

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
-- Users may update their own profile but can NOT change their role (no self-promotion to admin).
CREATE POLICY "Users can update own profile" ON public.profiles FOR UPDATE
    USING (auth.uid() = id)
    WITH CHECK (
        auth.uid() = id
        AND role IS NOT DISTINCT FROM (SELECT p.role FROM public.profiles p WHERE p.id = auth.uid())
    );

-- Self-inserted profiles are always plain traders (handle_new_user normally creates the row).
DROP POLICY IF EXISTS "Users can insert own profile" ON public.profiles;
CREATE POLICY "Users can insert own profile" ON public.profiles FOR INSERT
    WITH CHECK (auth.uid() = id AND COALESCE(role, 'trader') = 'trader');

-- Trading Accounts Policies
DROP POLICY IF EXISTS "Users can view own trading accounts" ON public.trading_accounts;
CREATE POLICY "Users can view own trading accounts" ON public.trading_accounts FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert own trading accounts" ON public.trading_accounts;
CREATE POLICY "Users can insert own trading accounts" ON public.trading_accounts FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update own trading accounts" ON public.trading_accounts;
CREATE POLICY "Users can update own trading accounts" ON public.trading_accounts FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can delete own trading accounts" ON public.trading_accounts;
CREATE POLICY "Users can delete own trading accounts" ON public.trading_accounts FOR DELETE USING (auth.uid() = user_id);

-- Signals Policies: see "Anyone can view active signals" below (active + unexpired only).

-- Orders Queue Policies
DROP POLICY IF EXISTS "Users can view own orders" ON public.orders_queue;
CREATE POLICY "Users can view own orders" ON public.orders_queue FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert own orders" ON public.orders_queue;
-- Users can only queue PENDING orders, for accounts they own.
CREATE POLICY "Users can insert own orders" ON public.orders_queue FOR INSERT WITH CHECK (
    auth.uid() = user_id
    AND status = 'PENDING'
    AND EXISTS (
        SELECT 1 FROM public.trading_accounts ta
        WHERE ta.user_id = auth.uid()
          AND ta.account_id = orders_queue.account_id
          AND (orders_queue.trading_account_id IS NULL OR ta.id = orders_queue.trading_account_id)
    )
);

-- Signals: only the service role (bypasses RLS) may write; also hide expired signals.
DROP POLICY IF EXISTS "Anyone can view active signals" ON public.signals;
CREATE POLICY "Anyone can view active signals" ON public.signals FOR SELECT
    USING (is_active = TRUE AND (expires_at IS NULL OR expires_at > NOW()));

-- Trade History Policies
DROP POLICY IF EXISTS "Users can view own trade history" ON public.trade_history;
CREATE POLICY "Users can view own trade history" ON public.trade_history FOR SELECT USING (auth.uid() = user_id);

-- ========================================================================================
-- 7b. COLUMN GUARDS (authenticated clients cannot forge server-owned fields)
-- ========================================================================================
-- RLS is row-level; these triggers make server-owned columns immutable for browser
-- (role 'authenticated' / 'anon') writes. The service role (API + bridge) is unaffected.
CREATE OR REPLACE FUNCTION public.guard_profile_role()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF COALESCE(auth.role(), '') IN ('authenticated', 'anon')
       AND NEW.role IS DISTINCT FROM OLD.role THEN
        RAISE EXCEPTION 'role cannot be changed by the user';
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_guard_profile_role ON public.profiles;
CREATE TRIGGER trg_guard_profile_role
    BEFORE UPDATE ON public.profiles
    FOR EACH ROW EXECUTE PROCEDURE public.guard_profile_role();

CREATE OR REPLACE FUNCTION public.guard_trading_account_telemetry()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF COALESCE(auth.role(), '') IN ('authenticated', 'anon') THEN
        IF TG_OP = 'UPDATE' THEN
            -- Telemetry, ownership and credentials are server-owned.
            NEW.user_id            := OLD.user_id;
            NEW.account_id         := OLD.account_id;
            NEW.broker_server      := OLD.broker_server;
            NEW.balance            := OLD.balance;
            NEW.equity             := OLD.equity;
            NEW.free_margin        := OLD.free_margin;
            NEW.margin_level       := OLD.margin_level;
            NEW.today_pnl          := OLD.today_pnl;
            NEW.today_pnl_percent  := OLD.today_pnl_percent;
            NEW.floating_pnl       := OLD.floating_pnl;
            NEW.terminal_connected := OLD.terminal_connected;
            NEW.last_sync_at       := OLD.last_sync_at;
            NEW.encrypted_password := OLD.encrypted_password;
            NEW.max_lot            := OLD.max_lot;
        ELSIF TG_OP = 'INSERT' THEN
            NEW.balance            := 0;
            NEW.equity             := 0;
            NEW.free_margin        := 0;
            NEW.margin_level       := 0;
            NEW.today_pnl          := 0;
            NEW.today_pnl_percent  := 0;
            NEW.floating_pnl       := 0;
            NEW.terminal_connected := FALSE;
            NEW.max_lot            := 0.05;
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_guard_trading_account_telemetry ON public.trading_accounts;
CREATE TRIGGER trg_guard_trading_account_telemetry
    BEFORE INSERT OR UPDATE ON public.trading_accounts
    FOR EACH ROW EXECUTE PROCEDURE public.guard_trading_account_telemetry();

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
-- 10. REMOVE LEGACY SEED SIGNAL
-- ========================================================================================
-- Earlier versions seeded a static 'SIG_XAU_LIVE_01' signal that autopilot could mirror as
-- if it were live. Signals now come only from scripts/signal_generator.py (with expires_at).
DELETE FROM public.signals WHERE id = 'SIG_XAU_LIVE_01';

-- ========================================================================================
-- MIGRATION NOTES
-- ========================================================================================
-- All migrations are applied idempotently in section 6b above; re-running this whole file
-- on an existing database is safe (resolve duplicate account ownership first, see 6b).
-- ========================================================================================
