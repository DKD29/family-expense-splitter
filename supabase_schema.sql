-- Family Trip Expense Splitter
-- Phase 2 database schema
--
-- Fixed users:
--   Krishna
--   Krishnamurty
--   Karthik
--
-- Expenses determine settlement.
-- Money Transfers are completely separate.


-- ============================================================
-- EXPENSES
-- ============================================================

CREATE TABLE expenses (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),

    date date NOT NULL,

    description text NOT NULL
        CHECK (length(trim(description)) > 0),

    amount numeric NOT NULL
        CHECK (amount > 0)
        CHECK (amount = round(amount, 2)),

    paid_by text NOT NULL
        CHECK (
            paid_by IN (
                'Krishna',
                'Krishnamurty',
                'Karthik'
            )
        ),

    krishna_ratio numeric NOT NULL
        CHECK (krishna_ratio >= 0),

    karthik_ratio numeric NOT NULL
        CHECK (karthik_ratio >= 0),

    krishnamurty_ratio numeric NOT NULL
        CHECK (krishnamurty_ratio >= 0),

    created_at timestamptz NOT NULL DEFAULT now(),

    CHECK (
        krishna_ratio > 0
        OR karthik_ratio > 0
        OR krishnamurty_ratio > 0
    )
);


-- ============================================================
-- MONEY TRANSFERS
-- ============================================================

CREATE TABLE money_transfers (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),

    date date NOT NULL,

    description text NOT NULL
        CHECK (length(trim(description)) > 0),

    amount numeric NOT NULL
        CHECK (amount > 0)
        CHECK (amount = round(amount, 2)),

    from_user text NOT NULL
        CHECK (
            from_user IN (
                'Krishna',
                'Krishnamurty',
                'Karthik'
            )
        ),

    to_user text NOT NULL
        CHECK (
            to_user IN (
                'Krishna',
                'Krishnamurty',
                'Karthik'
            )
        ),

    created_at timestamptz NOT NULL DEFAULT now(),

    CHECK (from_user <> to_user)
);


-- ============================================================
-- FUTURE DATE VALIDATION
-- ============================================================

CREATE OR REPLACE FUNCTION reject_future_transaction_date()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.date > (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Kolkata')::date THEN
        RAISE EXCEPTION 'Transaction date cannot be in the future.';
    END IF;

    RETURN NEW;
END;
$$;


CREATE TRIGGER expenses_reject_future_date
BEFORE INSERT OR UPDATE OF date
ON expenses
FOR EACH ROW
EXECUTE FUNCTION reject_future_transaction_date();


CREATE TRIGGER money_transfers_reject_future_date
BEFORE INSERT OR UPDATE OF date
ON money_transfers
FOR EACH ROW
EXECUTE FUNCTION reject_future_transaction_date();


-- ============================================================
-- INDEXES
-- ============================================================

CREATE INDEX expenses_date_idx
    ON expenses (date DESC);

CREATE INDEX money_transfers_date_idx
    ON money_transfers (date DESC);


-- ============================================================
-- ROW LEVEL SECURITY
-- ============================================================

ALTER TABLE expenses ENABLE ROW LEVEL SECURITY;
ALTER TABLE money_transfers ENABLE ROW LEVEL SECURITY;


-- ============================================================
-- ANONYMOUS ACCESS POLICIES
-- ============================================================

CREATE POLICY "Allow anonymous read expenses"
ON expenses
FOR SELECT
TO anon
USING (true);


CREATE POLICY "Allow anonymous insert expenses"
ON expenses
FOR INSERT
TO anon
WITH CHECK (true);


CREATE POLICY "Allow anonymous update expenses"
ON expenses
FOR UPDATE
TO anon
USING (true)
WITH CHECK (true);


CREATE POLICY "Allow anonymous delete expenses"
ON expenses
FOR DELETE
TO anon
USING (true);


CREATE POLICY "Allow anonymous read money transfers"
ON money_transfers
FOR SELECT
TO anon
USING (true);


CREATE POLICY "Allow anonymous insert money transfers"
ON money_transfers
FOR INSERT
TO anon
WITH CHECK (true);


CREATE POLICY "Allow anonymous update money transfers"
ON money_transfers
FOR UPDATE
TO anon
USING (true)
WITH CHECK (true);


CREATE POLICY "Allow anonymous delete money transfers"
ON money_transfers
FOR DELETE
TO anon
USING (true);