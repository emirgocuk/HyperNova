import redis
import psycopg2
import logging
import json
from data_layer.config import *

logger = logging.getLogger("DBWriter")

class DBWriter:
    """
    Handles connections to Redis (Pub/Sub and Hot Stream) and TimescaleDB (Historical).
    Assumes Docker containers are running as per docker-compose.yml.
    """
    def __init__(self):
        self.redis_client = None
        self.pg_conn = None
        self.connect()

    def connect(self):
        try:
            # Connect to Redis
            self.redis_client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                decode_responses=True
            )
            # Test ping
            self.redis_client.ping()
            logger.info("Connected to Redis Successfully.")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")

        try:
            # Connect to TimescaleDB
            self.pg_conn = psycopg2.connect(
                host=TIMESCALEDB_HOST,
                port=TIMESCALEDB_PORT,
                user=TIMESCALEDB_USER,
                password=TIMESCALEDB_PASSWORD,
                dbname=TIMESCALEDB_DB
            )
            logger.info("Connected to TimescaleDB Successfully.")
            
        except Exception as e:
            logger.error(f"Failed to connect to TimescaleDB: {e}")

    def publish_hot_stream(self, data: dict):
        """Publish real-time candle + features to Redis stream for The Brain to consume."""
        if not self.redis_client:
            return
            
        try:
            # Convert pandas timestamp to ISO string if needed
            if 'timestamp' in data and not isinstance(data['timestamp'], str):
                data['timestamp'] = data['timestamp'].isoformat()
                
            self.redis_client.publish(MARKET_DATA_STREAM, json.dumps(data))
        except Exception as e:
            logger.error(f"Redis Publish Error: {e}")

    def write_timescale(self, data: dict):
        """Persist data to TimescaleDB."""
        if not self.pg_conn:
            return
            
        try:
            cursor = self.pg_conn.cursor()
            
            insert_query = """
                INSERT INTO market_data (time, symbol, timeframe, open, high, low, close, volume, log_return, atr, std_dev) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING;
            """
            
            cursor.execute(insert_query, (
                data['timestamp'],
                data['symbol'],
                data['timeframe'],
                data['open'],
                data['high'],
                data['low'],
                data['close'],
                data['volume'],
                data.get('log_return'),
                data.get('atr'),
                data.get('std_dev')
            ))
            self.pg_conn.commit()
            cursor.close()
            
        except Exception as e:
            logger.error(f"TimescaleDB Insert Error: {e}")
            self.pg_conn.rollback()

    def disconnect(self):
        if self.pg_conn:
            self.pg_conn.close()
        logger.info("Database connections closed.")
