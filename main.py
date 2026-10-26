import os
import sqlite3
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt

# 1. Fetch stock data
tickers = ["UBSG.SW", "AAPL"]
print("Downloading financial data from Yahoo Finance...")
data = yf.download(tickers, period="1y", interval="1d")['Close']

# 2. Save raw prices to SQLite database
conn = sqlite3.connect("stock_data.db")
data.to_sql("stock_prices", conn, if_exists="replace", index=True)
conn.close()

# 3. Read back from database
conn = sqlite3.connect("stock_data.db")
df = pd.read_sql("SELECT * FROM stock_prices", conn, parse_dates=["Date"])
conn.close()
df.set_index("Date", inplace=True)

# 4. Calculate 14-Day RSI (Relative Strength Index)
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    
    rs = avg_gain / avg_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi

rsi_df = pd.DataFrame(index=df.index)
for ticker in tickers:
    rsi_df[ticker] = calculate_rsi(df[ticker])

# Save RSI values to SQLite database
conn = sqlite3.connect("stock_data.db")
rsi_df.to_sql("stock_rsi", conn, if_exists="replace", index=True)
conn.close()

print("\n--- Latest 14-Day RSI Values (30=Oversold, 70=Overbought) ---")
print(rsi_df.tail(5))

# 5. Create 'charts' directory
os.makedirs("charts", exist_ok=True)

# 6. Generate Two-Panel Charts (Top: Price, Bottom: RSI)
def generate_chart(price_sub, rsi_sub, filename, title_text):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 8), sharex=True, gridspec_kw={'height_ratios': [2, 1]})
    
    # Top Panel: Stock Prices
    ax1.plot(price_sub.index, price_sub["AAPL"], label="Apple (AAPL)", color="blue")
    ax1.plot(price_sub.index, price_sub["UBSG.SW"], label="UBS Zürich (UBSG.SW)", color="orange")
    ax1.set_title(title_text, fontsize=13, fontweight="bold")
    ax1.set_ylabel("Closing Price (USD / CHF)")
    ax1.legend(loc="upper left")
    ax1.grid(True, linestyle="--", alpha=0.6)
    
    # Bottom Panel: RSI Indicator
    ax2.plot(rsi_sub.index, rsi_sub["AAPL"], label="AAPL RSI (14)", color="blue", linestyle="-")
    ax2.plot(rsi_sub.index, rsi_sub["UBSG.SW"], label="UBSG.SW RSI (14)", color="orange", linestyle="-")
    ax2.axhline(70, color="red", linestyle="--", linewidth=1, label="Overbought (70)")
    ax2.axhline(30, color="green", linestyle="--", linewidth=1, label="Oversold (30)")
    ax2.fill_between(rsi_sub.index, 70, 100, color="red", alpha=0.08)
    ax2.fill_between(rsi_sub.index, 0, 30, color="green", alpha=0.08)
    ax2.set_ylim(0, 100)
    ax2.set_ylabel("RSI (14)")
    ax2.set_xlabel("Date")
    ax2.legend(loc="upper left", fontsize=8)
    ax2.grid(True, linestyle="--", alpha=0.6)
    
    plt.tight_layout()
    filepath = os.path.join("charts", filename)
    plt.savefig(filepath, dpi=150)
    plt.close()

# Define timeframes using trading days (5d = 1W, 21d = 1M, 126d = 6M)
periods = {
    "chart_1week.png": (df.tail(5), rsi_df.tail(5), "1-Week Stock Price & RSI Analysis"),
    "chart_1month.png": (df.tail(21), rsi_df.tail(21), "1-Month Stock Price & RSI Analysis"),
    "chart_6months.png": (df.tail(126), rsi_df.tail(126), "6-Month Stock Price & RSI Analysis"),
    "chart_1year.png": (df, rsi_df, "1-Year Stock Price & RSI Analysis")
}

for filename, (p_sub, r_sub, title) in periods.items():
    generate_chart(p_sub, r_sub, filename, title)
    print(f"Successfully generated: charts/{filename}")

print("\nAll price and RSI charts updated successfully!")
