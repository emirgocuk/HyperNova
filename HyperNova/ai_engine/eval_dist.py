import torch
import numpy as np
from ai_engine.data_loader import load_training_data
from ai_engine.model_cnn_lstm import CNNLSTMRegimeDetector
import os

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = CNNLSTMRegimeDetector(num_features=20, window_size=60).to(device)
try:
    model.load_state_dict(torch.load("ai_engine/weights/brain_cnn_lstm_best.pth", map_location=device, weights_only=True))
except Exception as e:
    print(f"Failed to load model: {e}")
    exit(1)
model.eval()

_, val_loader, _ = load_training_data("database/training_data", 60)

preds = {0: 0, 1: 0, 2: 0}
raw_probs = []
raw_confs = []
final_confs = []
above_35 = 0

with torch.no_grad():
    for x, y in val_loader:
        x = x.to(device)
        logits, conf = model(x)
        probs = torch.softmax(logits, dim=1).cpu().numpy()
        conf_vals = conf.cpu().numpy()
        
        for p, c in zip(probs, conf_vals):
            idx = int(np.argmax(p))
            preds[idx] += 1
            raw_probs.append(p[idx])
            raw_confs.append(c[0])
            final_c = float(p[idx]) * c[0]
            if idx in (1, 2):
                final_confs.append(final_c)
                if final_c >= 0.35:
                    above_35 += 1

print(f"\n--- VALIDATION SET PREDICTIONS ---")
print(f"SIDEWAYS : {preds[0]}")
print(f"UPTREND  : {preds[1]}")
print(f"DOWNTREND: {preds[2]}")
print(f"\nAvg Raw Max Prob (Softmax): {np.mean(raw_probs):.4f}")
print(f"Avg Raw Conf Head (Sigmoid): {np.mean(raw_confs):.4f}")
if final_confs:
    print(f"Avg Final Confidence (Prob * Conf): {np.mean(final_confs):.4f}")
    print(f"Max Final Confidence: {max(final_confs):.4f}")
    print(f"Trend predictions above 0.35 threshold: {above_35}")
else:
    print("No trend predictions made!")
