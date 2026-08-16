-- TimescaleDB Initialization Script for The Transparent Strategist

-- 1. Create the base table for OHLCV and Engineered features
CREATE TABLE IF NOT EXISTS market_data (
    time        TIMESTAMPTZ       NOT NULL,
    symbol      TEXT              NOT NULL,
    timeframe   TEXT              NOT NULL,
    open        DOUBLE PRECISION  NOT NULL,
    high        DOUBLE PRECISION  NOT NULL,
    low         DOUBLE PRECISION  NOT NULL,
    close       DOUBLE PRECISION  NOT NULL,
    volume      DOUBLE PRECISION  NOT NULL,
    log_return  DOUBLE PRECISION,
    atr         DOUBLE PRECISION,
    std_dev     DOUBLE PRECISION
);

-- 2. Convert it to a TimescaleDB hypertable partitioned by time
-- chunk_time_interval is typically set to 1 day or 7 days depending on data density
SELECT create_hypertable('market_data', 'time', if_not_exists => TRUE, chunk_time_interval => INTERVAL '1 day');

-- 3. Create index for faster querying by symbol and time
CREATE INDEX IF NOT EXISTS ix_symbol_time ON market_data (symbol, time DESC);

-- 4. Create an Execution logs table for XAI and Slippage tracking
CREATE TABLE IF NOT EXISTS execution_logs (
    time              TIMESTAMPTZ       NOT NULL,
    symbol            TEXT              NOT NULL,
    action            TEXT              NOT NULL, -- 'BUY', 'SELL', 'CIRCUIT_BREAKER'
    confidence_score  DOUBLE PRECISION,
    expected_price    DOUBLE PRECISION,
    actual_price      DOUBLE PRECISION,
    slippage          DOUBLE PRECISION,
    xai_reasoning     TEXT
);

SELECT create_hypertable('execution_logs', 'time', if_not_exists => TRUE);
