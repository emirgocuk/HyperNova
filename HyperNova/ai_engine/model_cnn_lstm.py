import torch
import torch.nn as nn
import logging

logger = logging.getLogger("BrainModel")


class TemporalAttention(nn.Module):
    """Attention mechanism: learns which timesteps in the LSTM output matter most."""
    def __init__(self, hidden_size: int):
        super().__init__()
        self.attention = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2),
            nn.Tanh(),
            nn.Linear(hidden_size // 2, 1)
        )
    
    def forward(self, lstm_output):
        # lstm_output: (batch, seq_len, hidden_size)
        attn_weights = self.attention(lstm_output)  # (batch, seq_len, 1)
        attn_weights = torch.softmax(attn_weights, dim=1)
        context = (lstm_output * attn_weights).sum(dim=1)  # (batch, hidden_size)
        return context, attn_weights.squeeze(-1)


class CNNLSTMRegimeDetector(nn.Module):
    """
    Optimized CNN-LSTM tailored for noisy financial data.
    Preventing Overfitting:
    - Reduced capacity (~200k params instead of 4.3M)
    - Aggressive Dropout (50-60%)
    """
    def __init__(self, num_features: int = 20, window_size: int = 60, num_classes: int = 3):
        super().__init__()
        
        self.num_features = num_features
        self.window_size = window_size
        self.num_classes = num_classes
        
        # 1. Smaller CNN Feature Extractor with BatchNorm
        self.cnn = nn.Sequential(
            nn.Conv1d(num_features, 32, kernel_size=3, padding=1),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.MaxPool1d(2),
            
            nn.Conv1d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.MaxPool1d(2),
        )
        
        # 2. Smaller Bidirectional LSTM
        self.lstm = nn.LSTM(
            input_size=64,
            hidden_size=64,  # Reduced from 256
            num_layers=2,    # Reduced from 3
            batch_first=True,
            dropout=0.5,     # Increased dropout
            bidirectional=True
        )
        
        self.attention = TemporalAttention(hidden_size=128)  # 64 * 2 (bidirectional)
        
        # 4a. Classification Head (Heavy Dropout)
        self.classifier = nn.Sequential(
            nn.Linear(128, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Dropout(0.6), # Very aggressive dropout to prevent memorization
            nn.Linear(64, num_classes)
        )
        
        # 4b. Confidence Head
        self.confidence_head = nn.Sequential(
            nn.Linear(128, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid()
        )
        
        self._init_weights()
    
    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv1d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
            elif isinstance(m, nn.Linear):
                nn.init.xavier_normal_(m.weight)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
    
    def forward(self, x, return_attention=False):
        x = x.permute(0, 2, 1)
        c_out = self.cnn(x)
        c_out = c_out.permute(0, 2, 1)
        l_out, _ = self.lstm(c_out)
        
        context, attn_weights = self.attention(l_out)
        
        logits = self.classifier(context)
        confidence = self.confidence_head(context)
        
        if return_attention:
            return logits, confidence, attn_weights
        return logits, confidence


def test_model():
    batch_size = 16
    window_size = 60
    num_features = 20
    model = CNNLSTMRegimeDetector(num_features, window_size)
    dummy = torch.randn(batch_size, window_size, num_features)
    logits, confidence = model(dummy)
    total_params = sum(p.numel() for p in model.parameters())
    print(f"Total parameters: {total_params:,}")

if __name__ == "__main__":
    test_model()
