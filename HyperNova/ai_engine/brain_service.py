import json
import logging
import asyncio
import torch
import numpy as np
from data_layer.config import REDIS_HOST, REDIS_PORT, REDIS_DB, MARKET_DATA_STREAM
import redis.asyncio as aioredis
from ai_engine.model_cnn_lstm import CNNLSTMRegimeDetector
from ai_engine.trainer import ModelTrainer

logger = logging.getLogger("BrainService")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class BrainService:
    """
    Listens to the Hot Data Stream (Redis) published by DataIngestor.
    Builds a sliding window of features and feeds them to the CNN-LSTM.
    """
    def __init__(self, window_size: int = 60, num_features: int = 8):
        self.window_size = window_size
        self.num_features = num_features
        
        # Instantiate Trainer to leverage its weight loading capability
        trainer = ModelTrainer(num_features=num_features, window_size=window_size)
        trainer.load_model() # Will load existing .pth if available
        
        self.model = trainer.model # Assign the potentially trained model
        self.model.eval() # Set to inference mode
        
        # Buffer to hold the trailing 'window_size' candles
        # In a real scenario, this would be initialized by doing a single DB query
        # to fetch the last 60 candles before listening to the stream.
        self.candle_buffer = []
        
    async def listen_to_stream(self):
        """Asynchronously listen to the Redis Pub/Sub channel."""
        logger.info("Connecting to Redis async stream...")
        try:
            redis_conn = await aioredis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
            pubsub = redis_conn.pubsub()
            await pubsub.subscribe(MARKET_DATA_STREAM)
            
            logger.info(f"Subscribed to {MARKET_DATA_STREAM}. Awaiting data...")
            
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    data = json.loads(message['data'])
                    await self.process_candle(data)
                    
        except Exception as e:
            logger.error(f"Brain Service Redis Error: {e}")

    async def process_candle(self, data: dict):
        """Extract features, update buffer, and run inference if buffer is full."""
        try:
            # Extract the 8 engineered features matching our Dataset
            # ['open', 'high', 'low', 'close', 'volume', 'log_return', 'atr', 'std_dev']
            features = [
                data['open'], data['high'], data['low'], data['close'], data['volume'],
                data.get('log_return', 0.0) or 0.0, 
                data.get('atr', 0.0) or 0.0, 
                data.get('std_dev', 0.0) or 0.0
            ]
            
            self.candle_buffer.append(features)
            
            # Maintain sliding window
            if len(self.candle_buffer) > self.window_size:
                self.candle_buffer.pop(0)
                
            # If we have enough data to form an "image"
            if len(self.candle_buffer) == self.window_size:
                await self.run_inference()
                
        except Exception as e:
            logger.error(f"Error processing candle: {e}")

    async def run_inference(self):
        """Convert buffer to tensor and pass through CNN-LSTM."""
        try:
            # Shape requirements for model: (batch_size, window_size, num_features)
            # We are doing batch_size = 1 for real-time inference
            np_array = np.array(self.candle_buffer, dtype=np.float32)
            tensor_input = torch.tensor(np_array).unsqueeze(0) # Add batch dimension -> (1, 60, 8)
            
            with torch.no_grad():
                logits = self.model(tensor_input)
                
                # Convert logits to probabilities via Softmax
                probabilities = torch.nn.functional.softmax(logits, dim=1).squeeze().numpy()
                
                # Classes: 0=Sideways, 1=Uptrend, 2=Downtrend
                regime_idx = np.argmax(probabilities)
                confidence = probabilities[regime_idx]
                
                regimes = ["SIDEWAYS (CHOP)", "UPTREND", "DOWNTREND"]
                detected_regime = regimes[regime_idx]
                
                # XAI Reasoning String
                xai_log = f"AI detected {detected_regime} with {confidence*100:.1f}% confidence."
                
                logger.info(f"🧠 INFERENCE: {xai_log} | Prob Matrix: {probabilities}")
                
                # Future: Publish decision + confidence to ExecutionManager stream
        
        except Exception as e:
            logger.error(f"Inference error: {e}")

if __name__ == "__main__":
    service = BrainService()
    try:
        asyncio.run(service.listen_to_stream())
    except KeyboardInterrupt:
        logger.info("Brain Service stopped manually.")
