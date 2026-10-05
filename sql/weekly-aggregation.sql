BEGIN;

-- This upsert assumes source rows are append-only or corrected in place. It
-- does not delete a weekly row when its final source row is removed.
-- Serialize concurrent refreshes for this logical dataset without holding a
-- session-level lock after the transaction ends.
SELECT pg_advisory_xact_lock(
    hashtextextended('stockbot-case-study.weekly-market-bar', 0)
);

CREATE TABLE IF NOT EXISTS weekly_market_bar (
    symbol text NOT NULL,
    week_start date NOT NULL,
    iso_year integer NOT NULL,
    iso_week integer NOT NULL,
    open_price numeric(18, 4) NOT NULL,
    high_price numeric(18, 4) NOT NULL,
    low_price numeric(18, 4) NOT NULL,
    close_price numeric(18, 4) NOT NULL,
    volume bigint NOT NULL,
    refreshed_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    PRIMARY KEY (symbol, week_start),
    CHECK (iso_week BETWEEN 1 AND 53)
);

WITH aggregated AS (
    SELECT
        symbol,
        date_trunc('week', observed_on)::date AS week_start,
        extract(isoyear FROM observed_on)::integer AS iso_year,
        extract(week FROM observed_on)::integer AS iso_week,
        (array_agg(open_price ORDER BY observed_on ASC))[1] AS open_price,
        max(high_price) AS high_price,
        min(low_price) AS low_price,
        (array_agg(close_price ORDER BY observed_on DESC))[1] AS close_price,
        sum(volume)::bigint AS volume
    FROM daily_market_bar
    GROUP BY
        symbol,
        date_trunc('week', observed_on)::date,
        extract(isoyear FROM observed_on)::integer,
        extract(week FROM observed_on)::integer
)
INSERT INTO weekly_market_bar (
    symbol,
    week_start,
    iso_year,
    iso_week,
    open_price,
    high_price,
    low_price,
    close_price,
    volume,
    refreshed_at
)
SELECT
    symbol,
    week_start,
    iso_year,
    iso_week,
    open_price,
    high_price,
    low_price,
    close_price,
    volume,
    transaction_timestamp()
FROM aggregated
ON CONFLICT (symbol, week_start) DO UPDATE
SET
    iso_year = EXCLUDED.iso_year,
    iso_week = EXCLUDED.iso_week,
    open_price = EXCLUDED.open_price,
    high_price = EXCLUDED.high_price,
    low_price = EXCLUDED.low_price,
    close_price = EXCLUDED.close_price,
    volume = EXCLUDED.volume,
    refreshed_at = EXCLUDED.refreshed_at
WHERE (
    weekly_market_bar.iso_year,
    weekly_market_bar.iso_week,
    weekly_market_bar.open_price,
    weekly_market_bar.high_price,
    weekly_market_bar.low_price,
    weekly_market_bar.close_price,
    weekly_market_bar.volume
) IS DISTINCT FROM (
    EXCLUDED.iso_year,
    EXCLUDED.iso_week,
    EXCLUDED.open_price,
    EXCLUDED.high_price,
    EXCLUDED.low_price,
    EXCLUDED.close_price,
    EXCLUDED.volume
);

COMMIT;
