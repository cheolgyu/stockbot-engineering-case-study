\set ON_ERROR_STOP on

CREATE TEMP TABLE daily_market_bar (
    symbol text NOT NULL,
    observed_on date NOT NULL,
    open_price numeric(18, 4) NOT NULL,
    high_price numeric(18, 4) NOT NULL,
    low_price numeric(18, 4) NOT NULL,
    close_price numeric(18, 4) NOT NULL,
    volume bigint NOT NULL,
    PRIMARY KEY (symbol, observed_on)
) ON COMMIT PRESERVE ROWS;

-- Pre-create the output as TEMP so the included production-shaped SQL cannot
-- resolve to or modify a permanent table with the same unqualified name.
CREATE TEMP TABLE weekly_market_bar (
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
) ON COMMIT PRESERVE ROWS;

INSERT INTO daily_market_bar (
    symbol,
    observed_on,
    open_price,
    high_price,
    low_price,
    close_price,
    volume
) VALUES
    ('SYNTH', DATE '2020-12-28', 100, 112, 95, 108, 10),
    ('SYNTH', DATE '2021-01-01', 108, 120, 104, 118, 20),
    ('SYNTH', DATE '2021-01-04', 118, 125, 110, 121, 30);

\ir weekly-aggregation.sql

DO $test$
DECLARE
    boundary_row weekly_market_bar%ROWTYPE;
BEGIN
    IF (SELECT count(*) FROM weekly_market_bar) <> 2 THEN
        RAISE EXCEPTION 'expected exactly two weekly rows';
    END IF;

    SELECT *
    INTO STRICT boundary_row
    FROM weekly_market_bar
    WHERE symbol = 'SYNTH'
      AND week_start = DATE '2020-12-28';

    IF boundary_row.iso_year <> 2020 OR boundary_row.iso_week <> 53 THEN
        RAISE EXCEPTION 'year boundary must be ISO 2020-W53';
    END IF;

    IF boundary_row.open_price <> 100
       OR boundary_row.high_price <> 120
       OR boundary_row.low_price <> 95
       OR boundary_row.close_price <> 118
       OR boundary_row.volume <> 30 THEN
        RAISE EXCEPTION 'OHLCV aggregation did not preserve ordering';
    END IF;
END
$test$;

CREATE TEMP TABLE first_refresh AS
SELECT symbol, week_start, refreshed_at
FROM weekly_market_bar;

-- A second unchanged refresh must neither duplicate nor rewrite rows.
\ir weekly-aggregation.sql

DO $test$
BEGIN
    IF (SELECT count(*) FROM weekly_market_bar) <> 2 THEN
        RAISE EXCEPTION 'refresh must be idempotent for unchanged source rows';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM weekly_market_bar current_row
        JOIN first_refresh previous_row USING (symbol, week_start)
        WHERE current_row.refreshed_at <> previous_row.refreshed_at
    ) THEN
        RAISE EXCEPTION 'unchanged rows must preserve refreshed_at';
    END IF;
END
$test$;

\echo 'weekly aggregation regression test passed'
