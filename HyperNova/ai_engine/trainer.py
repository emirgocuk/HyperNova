import torch
import torch.nn as nn
import torch.optim as optim
import logging
import os
import time
import json
import numpy as np
from ai_engine.model_cnn_lstm import CNNLSTMRegimeDetector
from ai_engine.data_loader import load_training_data

logger = logging.getLogger("Trainer")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Global progress tracker for the Dashboard API
TRAINING_STATUS = {
    "current_epoch": 0,
    "total_epochs": 0,
    "loss": 0.0,
    "val_loss": 0.0,
    "accuracy": 0.0,
    "val_accuracy": 0.0,
    "best_val_loss": float('inf'),
    "is_active": False,
    "lr": 0.0
}


class ModelTrainer:
    """
    Advanced trainer with:
    - CUDA support
    - Learning rate scheduling (ReduceLROnPlateau)
    - Early stopping
    - Checkpoint saving every N epochs
    - Train/val split tracking  
    - Dual-head loss (classification + confidence)
    """
    def __init__(self, num_features: int = 20, window_size: int = 60, learning_rate: float = 0.001):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"🖥️ Device: {self.device}")
        if self.device.type == "cuda":
            logger.info(f"   GPU: {torch.cuda.get_device_name()}")
            logger.info(f"   VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
        
        self.model = CNNLSTMRegimeDetector(num_features, window_size).to(self.device)
        
        # Class weights to combat the dataset bias (44% Sideways vs 28% Trends). 
        # Forces model to prioritize trends and learn not to falsely predict Sideways.
        if num_features > 0: # Check just to not crash if dummy 
            weights = torch.tensor([0.5, 1.5, 1.5]).to(self.device)
            self.criterion = nn.CrossEntropyLoss(weight=weights)
        else:
            self.criterion = nn.CrossEntropyLoss()
            
        # Increased weight_decay from 1e-4 to 1e-3 (Strong L2 regularization)
        self.optimizer = optim.AdamW(self.model.parameters(), lr=learning_rate, weight_decay=1e-3)
        self.scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer, mode='min', factor=0.5, patience=5
        )
        
        self.weights_dir = "ai_engine/weights"
        os.makedirs(self.weights_dir, exist_ok=True)
        self.model_path = os.path.join(self.weights_dir, "brain_cnn_lstm_latest.pth")
        self.best_model_path = os.path.join(self.weights_dir, "brain_cnn_lstm_best.pth")
        self.norm_params_path = os.path.join(self.weights_dir, "normalization_params.json")

    def train(self, train_loader, val_loader, epochs: int = 100, 
              patience: int = 15, checkpoint_every: int = 10, norm_params=None):
        """Full training loop with validation, scheduling, early stopping."""
        global TRAINING_STATUS
        TRAINING_STATUS["is_active"] = True
        TRAINING_STATUS["total_epochs"] = epochs
        TRAINING_STATUS["best_val_loss"] = float('inf')
        
        best_val_loss = float('inf')
        early_stop_counter = 0
        
        # Save normalization parameters for live inference
        if norm_params is not None:
            means, stds = norm_params
            with open(self.norm_params_path, 'w') as f:
                json.dump({"means": means.tolist(), "stds": stds.tolist()}, f)
            logger.info(f"💾 Normalization params saved to {self.norm_params_path}")
        
        total_params = sum(p.numel() for p in self.model.parameters())
        logger.info(f"🧠 Model: {total_params:,} parameters")
        logger.info(f"📊 Training: {len(train_loader.dataset):,} samples | Validation: {len(val_loader.dataset):,} samples")
        logger.info(f"⚙️ epochs={epochs}, patience={patience}, batch_size={train_loader.batch_size}")
        logger.info("=" * 60)
        
        start_time = time.time()
        
        for epoch in range(epochs):
            # ---- TRAINING ----
            self.model.train()
            train_loss = 0.0
            correct = 0
            total = 0
            
            for inputs, labels in train_loader:
                inputs, labels = inputs.to(self.device), labels.to(self.device)
                
                self.optimizer.zero_grad()
                logits, confidence = self.model(inputs)
                
                loss = self.criterion(logits, labels)
                loss.backward()
                
                # Gradient clipping
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
                
                self.optimizer.step()
                
                train_loss += loss.item()
                _, predicted = torch.max(logits, 1)
                total += labels.size(0)
                correct += (predicted == labels).sum().item()
            
            avg_train_loss = train_loss / len(train_loader)
            train_acc = 100 * correct / total
            
            # ---- VALIDATION ----
            self.model.eval()
            val_loss = 0.0
            val_correct = 0
            val_total = 0
            
            with torch.no_grad():
                for inputs, labels in val_loader:
                    inputs, labels = inputs.to(self.device), labels.to(self.device)
                    logits, confidence = self.model(inputs)
                    loss = self.criterion(logits, labels)
                    
                    val_loss += loss.item()
                    _, predicted = torch.max(logits, 1)
                    val_total += labels.size(0)
                    val_correct += (predicted == labels).sum().item()
            
            avg_val_loss = val_loss / len(val_loader)
            val_acc = 100 * val_correct / val_total
            
            # Learning rate step
            current_lr = self.optimizer.param_groups[0]['lr']
            self.scheduler.step(avg_val_loss)
            
            # Update dashboard
            TRAINING_STATUS["current_epoch"] = epoch + 1
            TRAINING_STATUS["loss"] = round(avg_train_loss, 4)
            TRAINING_STATUS["val_loss"] = round(avg_val_loss, 4)
            TRAINING_STATUS["accuracy"] = round(train_acc, 2)
            TRAINING_STATUS["val_accuracy"] = round(val_acc, 2)
            TRAINING_STATUS["lr"] = current_lr
            
            # Logging
            improved = ""
            if avg_val_loss < best_val_loss:
                best_val_loss = avg_val_loss
                TRAINING_STATUS["best_val_loss"] = round(best_val_loss, 4)
                early_stop_counter = 0
                self._save_model(self.best_model_path)
                improved = " ⭐ BEST"
            else:
                early_stop_counter += 1
            
            logger.info(
                f"Epoch [{epoch+1}/{epochs}] | "
                f"Train: loss={avg_train_loss:.4f} acc={train_acc:.1f}% | "
                f"Val: loss={avg_val_loss:.4f} acc={val_acc:.1f}% | "
                f"LR={current_lr:.6f}{improved}"
            )
            
            # Checkpoint
            if (epoch + 1) % checkpoint_every == 0:
                cp_path = os.path.join(self.weights_dir, f"checkpoint_epoch_{epoch+1}.pth")
                self._save_model(cp_path)
                logger.info(f"💾 Checkpoint saved: {cp_path}")
            
            # Early stopping
            if early_stop_counter >= patience:
                logger.info(f"🛑 Early stopping! No improvement for {patience} epochs.")
                break
        
        elapsed = time.time() - start_time
        logger.info("=" * 60)
        logger.info(f"✅ Training Complete! Time: {elapsed/60:.1f} min | Best Val Loss: {best_val_loss:.4f}")
        
        # Save final model
        self._save_model(self.model_path)
        TRAINING_STATUS["is_active"] = False

    def _save_model(self, path):
        torch.save(self.model.state_dict(), path)

    def save_model(self):
        self._save_model(self.model_path)
        logger.info(f"💾 Model saved to: {self.model_path}")

    def load_model(self, path=None):
        target = path or self.best_model_path
        if not os.path.exists(target):
            target = self.model_path
        if os.path.exists(target):
            self.model.load_state_dict(torch.load(target, map_location=self.device, weights_only=True))
            self.model.eval()
            logger.info(f"📂 Loaded weights from: {target}")
            return True
        logger.warning("No weights found. Model has random weights.")
        return False


def run_training_session(epochs: int = 150):
    """Main entry point — loads data and trains the model."""
    logger.info("🚀 Starting AI Training Session")
    logger.info(f"   CUDA available: {torch.cuda.is_available()}")
    
    # Load data
    train_loader, val_loader, train_dataset = load_training_data(
        data_dir="database/training_data",
        window_size=60
    )
    
    # Initialize trainer
    trainer = ModelTrainer(
        num_features=train_dataset.NUM_INPUT_FEATURES,
        window_size=60,
        learning_rate=0.001
    )
    
    # Get normalization params for live inference later
    norm_params = train_dataset.get_normalization_params()
    
    # Train!
    trainer.train(
        train_loader, val_loader,
        epochs=epochs,
        patience=15,
        checkpoint_every=10,
        norm_params=norm_params
    )


if __name__ == "__main__":
    run_training_session(epochs=150)
