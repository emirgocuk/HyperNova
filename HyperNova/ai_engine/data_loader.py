import torch
from torch.utils.data import Dataset, DataLoader
import numpy as np
import pandas as pd
import os
import logging

logger = logging.getLogger("DataLoader")

class FinancialDataset(Dataset):
    """
    Loads pre-engineered CSV data with 21 features for CNN-LSTM training.
    
    Labels are generated via ATR-adaptive forward-looking classification:
    - 0 = Sideways (change < 1.0 × ATR)
    - 1 = Uptrend  (change > +1.0 × ATR)
    - 2 = Downtrend (change < -1.0 × ATR)
    """
    FEATURE_COLS = [
        'rsi_14', 'rsi_7', 'macd', 'macd_signal', 'macd_hist',
        'stoch_rsi', 'ema_cross_9_21', 'ema_cross_21_50', 'price_vs_sma200',
        'adx_14', 'atr_14', 'atr_7', 'bb_width', 'bb_position',
        'log_return', 'vol_sma_ratio', 'obv_norm',
        'candle_body', 'upper_wick', 'lower_wick',
        'close'  # Keep close for normalization reference
    ]
    
    # 21 features (close used internally, then dropped from final input)
    NUM_INPUT_FEATURES = 20  # All above minus 'close'
    
    def __init__(self, df: pd.DataFrame, window_size: int = 60, forward_look: int = 10):
        # Only keep the columns we need
        available_cols = [c for c in self.FEATURE_COLS if c in df.columns]
        if len(available_cols) < len(self.FEATURE_COLS):
            missing = set(self.FEATURE_COLS) - set(available_cols)
            raise ValueError(f"Missing columns: {missing}. Available: {list(df.columns)}")
        
        df = df[available_cols].copy()
        df.replace([np.inf, -np.inf], np.nan, inplace=True)
        df.dropna(inplace=True)
        df.reset_index(drop=True, inplace=True)
        
        # Z-score normalization per feature (crucial for CNN convergence)
        self.close_values = df['close'].values.copy()
        feature_cols = [c for c in self.FEATURE_COLS if c != 'close']
        
        self.means = df[feature_cols].mean().values
        self.stds = df[feature_cols].std().values
        self.stds[self.stds < 1e-8] = 1.0  # Avoid division by zero
        
        self.features = ((df[feature_cols].values - self.means) / self.stds).astype(np.float32)
        
        self.window_size = window_size
        self.forward_look = forward_look
        
        # ATR-adaptive labeling
        atr_values = df['atr_14'].values
        self.labels = self._generate_atr_labels(self.close_values, atr_values, forward_look)
        
        # Valid samples count
        self.n_samples = len(self.features) - self.window_size - self.forward_look
        
        # Log class distribution
        valid_labels = self.labels[self.window_size:self.window_size + self.n_samples]
        counts = np.bincount(valid_labels, minlength=3)
        total = counts.sum()
        logger.info(f"📊 Label distribution: Sideways={counts[0]} ({counts[0]/total*100:.1f}%), "
                    f"Uptrend={counts[1]} ({counts[1]/total*100:.1f}%), "
                    f"Downtrend={counts[2]} ({counts[2]/total*100:.1f}%)")
    
    def _generate_atr_labels(self, closes, atr, forward_look):
        """ATR-adaptive labeling: threshold scales with volatility."""
        labels = np.zeros(len(closes), dtype=np.int64)
        
        for i in range(len(closes) - forward_look):
            future_return = closes[i + forward_look] - closes[i]
            threshold = atr[i] * 1.0  # 1x ATR multiplier
            
            if future_return > threshold:
                labels[i] = 1  # Uptrend
            elif future_return < -threshold:
                labels[i] = 2  # Downtrend
            else:
                labels[i] = 0  # Sideways
        
        return labels
    
    def __len__(self):
        return self.n_samples
    
    def __getitem__(self, idx):
        window = self.features[idx : idx + self.window_size]
        label = self.labels[idx + self.window_size]
        
        x = torch.tensor(window, dtype=torch.float32)
        y = torch.tensor(label, dtype=torch.long)
        return x, y
    
    def get_normalization_params(self):
        """Returns means and stds for live inference normalization."""
        return self.means, self.stds


def load_training_data(data_dir: str = "database/training_data", window_size: int = 60):
    """Loads all CSV files in the training directory and creates dataloaders."""
    all_dfs = []
    
    for f in sorted(os.listdir(data_dir)):
        if f.endswith('_engineered.csv'):
            path = os.path.join(data_dir, f)
            df = pd.read_csv(path)
            logger.info(f"📂 Loaded {f}: {len(df):,} rows")
            all_dfs.append(df)
    
    if not all_dfs:
        raise FileNotFoundError(f"No engineered CSV files found in {data_dir}")
    
    combined = pd.concat(all_dfs, ignore_index=True)
    logger.info(f"📊 Combined dataset: {len(combined):,} rows")
    
    # Train/Val split (80/20 chronological per symbol)
    train_dfs = []
    val_dfs = []
    for symbol in combined['symbol'].unique():
        sym_df = combined[combined['symbol'] == symbol].copy()
        split_idx = int(len(sym_df) * 0.8)
        train_dfs.append(sym_df.iloc[:split_idx])
        val_dfs.append(sym_df.iloc[split_idx:])
    
    train_combined = pd.concat(train_dfs, ignore_index=True)
    val_combined = pd.concat(val_dfs, ignore_index=True)
    
    logger.info(f"🏋️ Training set: {len(train_combined):,} rows")
    logger.info(f"🧪 Validation set: {len(val_combined):,} rows")
    
    train_dataset = FinancialDataset(train_combined, window_size=window_size)
    val_dataset = FinancialDataset(val_combined, window_size=window_size)
    
    train_loader = DataLoader(train_dataset, batch_size=128, shuffle=True, num_workers=0, pin_memory=True)
    val_loader = DataLoader(val_dataset, batch_size=128, shuffle=False, num_workers=0, pin_memory=True)
    
    return train_loader, val_loader, train_dataset


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    train_loader, val_loader, _ = load_training_data()
    for x, y in train_loader:
        print(f"Batch X: {x.shape}, Y: {y.shape}")
        break
