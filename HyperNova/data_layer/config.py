import os

# Database Configurations
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))

TIMESCALEDB_HOST = os.getenv("TIMESCALEDB_HOST", "localhost")
TIMESCALEDB_PORT = int(os.getenv("TIMESCALEDB_PORT", 5432))
TIMESCALEDB_USER = os.getenv("TIMESCALEDB_USER", "trader")
TIMESCALEDB_PASSWORD = os.getenv("TIMESCALEDB_PASSWORD", "supersecretpassword")
TIMESCALEDB_DB = os.getenv("TIMESCALEDB_DB", "trading_engine")

# Stream Configs
MARKET_DATA_STREAM = "market_data_stream"
