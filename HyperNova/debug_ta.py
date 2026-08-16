
import pandas as pd
import pandas_ta as ta

# Create dummy data
data = {
    'Close': [100, 101, 102, 103, 104, 105, 104, 103, 102, 101] * 5
}
df = pd.DataFrame(data)

# Run bbands
try:
    bb = ta.bbands(df['Close'], length=20, std=2.0)
    print("Columns found:", bb.columns.tolist())
except Exception as e:
    print("Error:", e)
