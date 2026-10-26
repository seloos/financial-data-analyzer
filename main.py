import os
import sqlite3
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt

# 1. Fetch 2 years of stock data (so 1-year charts have full 200-day SMA & RSI from day 1)
tickers = ["UBSG.SW", "AAPL"]
print("Downloading financial data from Yahoo Finance...")
data = yf.download(tickers, period="2y", interval="1d")['Close']

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
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
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
    rsi_df[ticker] = calculate_rsi(df[ticker])
    sma50_df[ticker] = df[ticker].rolling(window=50).mean()
    sma200_df[ticker] = df[ticker].rolling(window=200).mean()

# Filter last 1 year (252 trading days) for analysis and reporting
df_1y = df.tail(252)
rsi_1y = rsi_df.tail(252)
sma50_1y = sma50_df.tail(252)

# Calculate Risk Metrics over the last 1 year
returns_1y = df_1y.pct_change().dropna() * 100
volatility = returns_1y.std() * (252 ** 0.5)
max_dd = {ticker: calculate_max_drawdown(df_1y[ticker]) for ticker in tickers}

risk_summary = pd.DataFrame({
    "Annualized Volatility (%)": volatility,
    "Max Drawdown (%)": pd.Series(max_dd),
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

# 6. Generate Two-Panel Charts (Top: Price + SMA50, Bottom: RSI)
def generate_chart(price_sub, sma50_sub, rsi_sub, filename, title_text):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 8), sharex=True, gridspec_kw={'height_ratios': [2, 1]})
    
    # Top Panel: Stock Prices & 50-Day SMA
    ax1.plot(price_sub.index, price_sub["AAPL"], label="Apple (AAPL)", color="blue", linewidth=1.8)
    ax1.plot(sma50_sub.index, sma50_sub["AAPL"], label="AAPL SMA (50)", color="cornflowerblue", linestyle="--", linewidth=1.2)
    
    ax1.plot(price_sub.index, price_sub["UBSG.SW"], label="UBS Zürich (UBSG.SW)", color="darkorange", linewidth=1.8)
    ax1.plot(sma50_sub.index, sma50_sub["UBSG.SW"], label="UBSG.SW SMA (50)", color="gold", linestyle="--", linewidth=1.2)
    
    ax1.set_title(title_text, fontsize=13, fontweight="bold")
    ax1.set_ylabel("Closing Price (USD / CHF)")
    ax1.legend(loc="upper left", fontsize=9, ncol=2)
    ax1.grid(True, linestyle="--", alpha=0.6)
    
    # Bottom Panel: RSI Indicator
    ax2.plot(rsi_sub.index, rsi_sub["AAPL"], label="AAPL RSI (14)", color="blue", linewidth=1.5)
    ax2.plot(rsi_sub.index, rsi_sub["UBSG.SW"], label="UBSG.SW RSI (14)", color="darkorange", linewidth=1.5)
    ax2.axhline(70, color="red", linestyle="--", linewidth=1, label="Overbought (70)")
    ax2.axhline(30, color="green", linestyle="--", linewidth=1, label="Oversold (30)")
    ax2.fill_between(rsi_sub.index, 70, 100, color="red", alpha=0.08)
    ax2.fill_between(rsi_sub.index, 0, 30, color="green", alpha=0.08)
    ax2.set_ylim(0, 100)
    ax2.set_ylabel("RSI (14)")
    ax2.set_xlabel("Date")
    ax2.legend(loc="upper left", fontsize=8, ncol=2)
    ax2.grid(True, linestyle="--", alpha=0.6)
    
    plt.tight_layout()
    filepath = os.path.join("charts", filename)
    plt.savefig(filepath, dpi=120)
    plt.close()

# Define timeframes (5d = 1W, 21d = 1M, 126d = 6M, 252d = 1Y)
periods = {
    "chart_1week.png": (df_1y.tail(5), sma50_1y.tail(5), rsi_1y.tail(5), "1-Week Price, SMA(50) & RSI Analysis"),
    "chart_1month.png": (df_1y.tail(21), sma50_1y.tail(21), rsi_1y.tail(21), "1-Month Price, SMA(50) & RSI Analysis"),
    "chart_6months.png": (df_1y.tail(126), sma50_1y.tail(126), rsi_1y.tail(126), "6-Month Price, SMA(50) & RSI Analysis"),
    "chart_1year.png": (df_1y, sma50_1y, rsi_1y, "1-Year Price, SMA(50) & RSI Analysis")
}

for filename, (p_sub, s_sub, r_sub, title) in periods.items():
    generate_chart(p_sub, s_sub, r_sub, filename, title)
    print(f"Successfully generated: charts/{filename}")

print("\nAll quantitative metrics and charts updated successfully!")
