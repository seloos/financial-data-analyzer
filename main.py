import os
import sqlite3
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt

# 1. Fetch 2 years of stock data
tickers = ["UBSG.SW", "AAPL"]
print("Downloading financial data from Yahoo Finance...")
data = yf.download(tickers, period="2y", interval="1d")['Close']

# Clean cross-market holiday NaNs using forward-fill so SMAs never break!
data = data.ffill().dropna()

# 2. Save raw prices to SQLite database
conn = sqlite3.connect("stock_data.db")
data.to_sql("stock_prices", conn, if_exists="replace", index=True)
conn.close()

# 3. Read back from database
conn = sqlite3.connect("stock_data.db")
df = pd.read_sql("SELECT * FROM stock_prices", conn, parse_dates=["Date"])
conn.close()
df.set_index("Date", inplace=True)

# 4. Calculate Quantitative Metrics (RSI, SMA 50, SMA 200, Volatility, Max Drawdown)
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period, min_periods=1).mean()
    avg_loss = loss.rolling(window=period, min_periods=1).mean()
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))

def calculate_max_drawdown(series):
    rolling_max = series.cummax()
    drawdown = (series - rolling_max) / rolling_max * 100.0
    return drawdown.min()

rsi_df = pd.DataFrame(index=df.index)
sma50_df = pd.DataFrame(index=df.index)
sma200_df = pd.DataFrame(index=df.index)

for ticker in tickers:
    rsi_df[ticker] = calculate_rsi(df[ticker], 14)
    sma50_df[ticker] = df[ticker].rolling(window=50, min_periods=1).mean()
    sma200_df[ticker] = df[ticker].rolling(window=200, min_periods=1).mean()

# Filter last 1 year (252 trading days)
df_1y = df.tail(252)
rsi_1y = rsi_df.tail(252)
sma50_1y = sma50_df.tail(252)
sma200_1y = sma200_df.tail(252)

# Calculate Risk Metrics over the last 1 year
returns_1y = df_1y.pct_change(fill_method=None).dropna() * 100
volatility = returns_1y.std() * (252 ** 0.5)
max_dd = {ticker: calculate_max_drawdown(df_1y[ticker]) for ticker in tickers}

risk_summary = pd.DataFrame({
    "Annualized Volatility (%)": volatility,
    "Max Drawdown (%)": pd.Series(max_dd),
    "Latest Price": df_1y.iloc[-1],
    "SMA (50)": sma50_1y.iloc[-1],
    "SMA (200)": sma200_1y.iloc[-1],
    "Latest RSI (14)": rsi_1y.iloc[-1]
})

print("\n=== QUANTITATIVE RISK & MOMENTUM SUMMARY (1-YEAR) ===")
print(risk_summary.round(2))

# Save RSI and Risk Summary to SQLite database
conn = sqlite3.connect("stock_data.db")
rsi_1y.to_sql("stock_rsi", conn, if_exists="replace", index=True)
risk_summary.to_sql("risk_metrics", conn, if_exists="replace", index=True)
conn.close()

# 5. Create 'charts' directory
os.makedirs("charts", exist_ok=True)

# 6. Generate Dual-Axis Two-Panel Charts (Top: AAPL vs UBS with SMA50 & SMA200, Bottom: RSI)
def generate_chart(price_sub, sma50_sub, sma200_sub, rsi_sub, filename, title_text):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True, gridspec_kw={'height_ratios': [2.2, 1]})
    
    # Left Y-Axis: Apple (USD)
    l1 = ax1.plot(price_sub.index, price_sub["AAPL"], label="AAPL Price (USD)", color="#0052cc", linewidth=2)
    l2 = ax1.plot(sma50_sub.index, sma50_sub["AAPL"], label="AAPL SMA(50)", color="#00a3bf", linestyle="--", linewidth=1.5)
    l3 = ax1.plot(sma200_sub.index, sma200_sub["AAPL"], label="AAPL SMA(200)", color="#6554c0", linestyle=":", linewidth=2)
    ax1.set_ylabel("Apple Price (USD)", color="#0052cc", fontweight="bold")
    ax1.tick_params(axis='y', labelcolor="#0052cc")
    ax1.grid(True, linestyle="--", alpha=0.5)
    
    # Right Y-Axis: UBS (CHF) so it doesn't look flat!
    ax1_right = ax1.twinx()
    l4 = ax1_right.plot(price_sub.index, price_sub["UBSG.SW"], label="UBS Price (CHF)", color="#ff8b00", linewidth=2)
    l5 = ax1_right.plot(sma50_sub.index, sma50_sub["UBSG.SW"], label="UBS SMA(50)", color="#ff5630", linestyle="--", linewidth=1.5)
    l6 = ax1_right.plot(sma200_sub.index, sma200_sub["UBSG.SW"], label="UBS SMA(200)", color="#bf2600", linestyle=":", linewidth=2)
    ax1_right.set_ylabel("UBS Zürich Price (CHF)", color="#ff8b00", fontweight="bold")
    ax1_right.tick_params(axis='y', labelcolor="#ff8b00")
    
    # Combine legends from both axes
    lines = l1 + l2 + l3 + l4 + l5 + l6
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc="upper left", fontsize=8.5, ncol=2, framealpha=0.9)
    ax1.set_title(title_text, fontsize=13, fontweight="bold")
    
    # Bottom Panel: RSI Indicator
    ax2.plot(rsi_sub.index, rsi_sub["AAPL"], label="AAPL RSI (14)", color="#0052cc", linewidth=1.5)
    ax2.plot(rsi_sub.index, rsi_sub["UBSG.SW"], label="UBSG.SW RSI (14)", color="#ff8b00", linewidth=1.5)
    ax2.axhline(70, color="red", linestyle="--", linewidth=1, label="Overbought (70)")
    ax2.axhline(30, color="green", linestyle="--", linewidth=1, label="Oversold (30)")
    ax2.fill_between(rsi_sub.index, 70, 100, color="red", alpha=0.08)
    ax2.fill_between(rsi_sub.index, 0, 30, color="green", alpha=0.08)
    ax2.set_ylim(0, 100)
    ax2.set_ylabel("RSI (14)", fontweight="bold")
    ax2.set_xlabel("Date")
    ax2.legend(loc="upper left", fontsize=8, ncol=2)
    ax2.grid(True, linestyle="--", alpha=0.5)
    
    plt.tight_layout()
    filepath = os.path.join("charts", filename)
    plt.savefig(filepath, dpi=120)
    plt.close()

# Define timeframes
periods = {
    "chart_1week.png": (df_1y.tail(5), sma50_1y.tail(5), sma200_1y.tail(5), rsi_1y.tail(5), "1-Week Price, SMA(50/200) & RSI Analysis"),
    "chart_1month.png": (df_1y.tail(21), sma50_1y.tail(21), sma200_1y.tail(21), rsi_1y.tail(21), "1-Month Price, SMA(50/200) & RSI Analysis"),
    "chart_6months.png": (df_1y.tail(126), sma50_1y.tail(126), sma200_1y.tail(126), rsi_1y.tail(126), "6-Month Price, SMA(50/200) & RSI Analysis"),
    "chart_1year.png": (df_1y, sma50_1y, sma200_1y, rsi_1y, "1-Year Price, SMA(50/200) & RSI Analysis")
}

for filename, (p_sub, s50_sub, s200_sub, r_sub, title) in periods.items():
    generate_chart(p_sub, s50_sub, s200_sub, r_sub, filename, title)
    print(f"Successfully generated: charts/{filename}")

print("\nAll dual-axis SMA(50/200) and RSI charts updated successfully!")
