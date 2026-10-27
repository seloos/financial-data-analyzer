import os
import sqlite3
import numpy as np
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt

# 1. Fetch 2 years of raw stock data
tickers = ["UBSG.SW", "AAPL"]
print("Downloading financial data from Yahoo Finance...")
raw_data = yf.download(tickers, period="2y", interval="1d")['Close']

# 2. Save raw unadjusted prices to SQLite database
conn = sqlite3.connect("stock_data.db")
raw_data.to_sql("stock_prices", conn, if_exists="replace", index=True)
conn.close()

# 3. Quantitative Functions (Wilder's RSI & Max Drawdown)
def calculate_wilders_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi.fillna(100.0)

def calculate_max_drawdown(series):
    rolling_max = series.cummax()
    drawdown = (series - rolling_max) / rolling_max * 100.0
    return drawdown.min()

# 4. Compute Metrics Per Ticker on Native Trading Calendars (No ffill bias!)
rsi_dict = {}
sma50_dict = {}
sma200_dict = {}
vol_dict = {}
mdd_dict = {}
latest_price = {}

for ticker in tickers:
    s_clean = raw_data[ticker].dropna()
    
    rsi_s = calculate_wilders_rsi(s_clean, 14)
    sma50_s = s_clean.rolling(window=50, min_periods=50).mean()
    sma200_s = s_clean.rolling(window=200, min_periods=200).mean()
    
    s_1y = s_clean.tail(252)
    returns_1y = s_1y.pct_change().dropna() * 100
    
    vol_dict[ticker] = returns_1y.std() * np.sqrt(252)
    mdd_dict[ticker] = calculate_max_drawdown(s_1y)
    latest_price[ticker] = s_1y.iloc[-1]
    
    rsi_dict[ticker] = rsi_s
    sma50_dict[ticker] = sma50_s
    sma200_dict[ticker] = sma200_s

# Align series onto a unified index and forward-fill ONLY for visual plotting
df_plot = raw_data.ffill().dropna().tail(252)
rsi_1y = pd.DataFrame(rsi_dict).reindex(df_plot.index).ffill()
sma50_1y = pd.DataFrame(sma50_dict).reindex(df_plot.index).ffill()
sma200_1y = pd.DataFrame(sma200_dict).reindex(df_plot.index).ffill()

risk_summary = pd.DataFrame({
    "Latest Price (Local CCY)": pd.Series(latest_price),
    "Annualized Volatility (%)": pd.Series(vol_dict),
    "Max Drawdown (%)": pd.Series(mdd_dict),
    "SMA (50)": sma50_1y.iloc[-1],
    "SMA (200)": sma200_1y.iloc[-1],
    "Wilder's RSI (14)": rsi_1y.iloc[-1]
})

print("\n=== QUANTITATIVE RISK & MOMENTUM SUMMARY (1-YEAR NATIVE CALENDAR) ===")
print(risk_summary.round(2))

# Save RSI and Risk Summary to SQLite database
conn = sqlite3.connect("stock_data.db")
rsi_1y.to_sql("stock_rsi", conn, if_exists="replace", index=True)
risk_summary.to_sql("risk_metrics", conn, if_exists="replace", index=True)
conn.close()

# 5. Create 'charts' directory & Generate Dual-Axis Charts
os.makedirs("charts", exist_ok=True)

def generate_chart(price_sub, sma50_sub, sma200_sub, rsi_sub, filename, title_text):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True, gridspec_kw={'height_ratios': [2.2, 1]})
    
    l1 = ax1.plot(price_sub.index, price_sub["AAPL"], label="AAPL Price (USD)", color="#0052cc", linewidth=2)
    l2 = ax1.plot(sma50_sub.index, sma50_sub["AAPL"], label="AAPL SMA(50)", color="#00a3bf", linestyle="--", linewidth=1.5)
    l3 = ax1.plot(sma200_sub.index, sma200_sub["AAPL"], label="AAPL SMA(200)", color="#6554c0", linestyle=":", linewidth=2)
    ax1.set_ylabel("Apple Price (USD)", color="#0052cc", fontweight="bold")
    ax1.tick_params(axis='y', labelcolor="#0052cc")
    ax1.grid(True, linestyle="--", alpha=0.5)
    
    ax1_right = ax1.twinx()
    l4 = ax1_right.plot(price_sub.index, price_sub["UBSG.SW"], label="UBS Price (CHF)", color="#ff8b00", linewidth=2)
    l5 = ax1_right.plot(sma50_sub.index, sma50_sub["UBSG.SW"], label="UBS SMA(50)", color="#ff5630", linestyle="--", linewidth=1.5)
    l6 = ax1_right.plot(sma200_sub.index, sma200_sub["UBSG.SW"], label="UBS SMA(200)", color="#bf2600", linestyle=":", linewidth=2)
    ax1_right.set_ylabel("UBS Zürich Price (CHF)", color="#ff8b00", fontweight="bold")
    ax1_right.tick_params(axis='y', labelcolor="#ff8b00")
    
    lines = l1 + l2 + l3 + l4 + l5 + l6
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc="upper left", fontsize=8.5, ncol=2, framealpha=0.9)
    ax1.set_title(title_text, fontsize=13, fontweight="bold")
    
    ax2.plot(rsi_sub.index, rsi_sub["AAPL"], label="AAPL Wilder's RSI (14)", color="#0052cc", linewidth=1.5)
    ax2.plot(rsi_sub.index, rsi_sub["UBSG.SW"], label="UBSG.SW Wilder's RSI (14)", color="#ff8b00", linewidth=1.5)
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

periods = {
    "chart_1week.png": (df_plot.tail(5), sma50_1y.tail(5), sma200_1y.tail(5), rsi_1y.tail(5), "1-Week Price, SMA(50/200) & Wilder's RSI"),
    "chart_1month.png": (df_plot.tail(21), sma50_1y.tail(21), sma200_1y.tail(21), rsi_1y.tail(21), "1-Month Price, SMA(50/200) & Wilder's RSI"),
    "chart_6months.png": (df_plot.tail(126), sma50_1y.tail(126), sma200_1y.tail(126), rsi_1y.tail(126), "6-Month Price, SMA(50/200) & Wilder's RSI"),
    "chart_1year.png": (df_plot, sma50_1y, sma200_1y, rsi_1y, "1-Year Price, SMA(50/200) & Wilder's RSI")
}

for filename, (p_sub, s50_sub, s200_sub, r_sub, title) in periods.items():
    generate_chart(p_sub, s50_sub, s200_sub, r_sub, filename, title)
    print(f"Successfully generated: charts/{filename}")

# 6. Auto-generate requirements.txt and README.md safely via Python
with open("requirements.txt", "w") as f:
    f.write("yfinance>=0.2.40\npandas>=2.0.0\nnumpy>=1.24.0\nmatplotlib>=3.7.0\n")

readme_lines = [
    "# 📈 Quantitative Financial Data Pipeline & Risk Analyzer\n",
    "An automated end-to-end **ETL (Extract, Transform, Load) pipeline** and quantitative technical analysis tool built in Python. This system fetches daily market data for **Apple Inc. (`AAPL`)** and **UBS Group AG (`UBSG.SW`)** via the Yahoo Finance API, computes native-calendar risk and momentum metrics into a local **SQLite** database, and generates multi-timeframe dual-axis visualizations updated daily via **GitHub Actions**.\n",
    "---\n",
    "## 🚀 Key Features & Architecture\n",
    "* **Automated Cloud CI/CD Pipeline:** Scheduled via GitHub Actions (`cron`) to execute daily at 08:00 UTC, updating the SQLite database and visual dashboards without manual intervention.",
    "* **Unbiased Native-Calendar Math:** Computes daily returns, annualized volatility, Wilder's RSI, and moving averages on each exchange's native trading calendar (`NASDAQ` vs. `SIX`) *prior* to visual forward-filling (`ffill`), preventing artificial zero-return volatility dampening on cross-market holidays.",
    "* **Dual-Axis Visualization (`twinx`):** Simultaneously plots equities across different currencies and nominal price scales (**USD** vs. **CHF**) alongside **50-Day** and **200-Day Simple Moving Averages (SMA)**.",
    "* **Relational Storage:** Persists raw closing prices, 14-day RSI time series, and summary risk metrics into structured SQLite tables (`stock_prices`, `stock_rsi`, `risk_metrics`).\n",
    "---\n",
    "## 📊 Latest Quantitative Risk & Momentum Summary (1-Year)\n",
    "```\n" + risk_summary.round(2).to_string() + "\n```\n",
    "---\n",
    "## 📈 Live Automated Market Dashboard\n",
    "*(Charts below are automatically regenerated and committed daily by GitHub Actions)*\n",
    "### 1-Year Historical Performance, SMA(50/200) & Wilder's RSI",
    "![1-Year Analysis](charts/chart_1year.png)\n",
    "### 6-Month Medium-Term Trend & Momentum",
    "![6-Month Analysis](charts/chart_6months.png)\n",
    "### 1-Month & 1-Week Short-Term Action",
    "| 1-Month View | 1-Week View |",
    "| :---: | :---: |",
    "| ![1-Month Analysis](charts/chart_1month.png) | ![1-Week Analysis](charts/chart_1week.png) |\n",
    "---\n",
    "## ⚙️ How to Run Locally\n",
    "1. Clone the repository: `git clone [https://github.com/seloos/financial-data-analyzer.git](https://github.com/seloos/financial-data-analyzer.git)`",
    "2. Install dependencies: `pip3 install -r requirements.txt`",
    "3. Run the pipeline: `python3 main.py`\n",
    "---\n",
    "## ⚠️ Methodology, Limitations & Disclaimer\n",
    "* **Wilder's Smoothing:** RSI is calculated using J. Welles Wilder's original exponential smoothing (`alpha = 1/14`) rather than a simple rolling mean, aligning values with institutional terminals.",
    "* **Currency Denominations (Local CCY):** Returns, volatility, and moving averages are calculated in each asset's native listing currency (`AAPL` in **USD**, `UBSG.SW` in **CHF**) without FX conversion.",
    "* **Dual Y-Axis Scaling:** Charts utilize a dual Y-axis (`twinx`) to preserve nominal price levels and exact SMA crossover points. Refer to the summary table above for direct risk-adjusted percentage comparisons.",
    "* **Database Artifact:** `stock_data.db` is committed directly to the repository as an inspectable snapshot updated by GitHub Actions. Running `python3 main.py` locally regenerates this file.",
    "* **Disclaimer:** Built strictly for educational and quantitative engineering demonstration purposes. Data is sourced via `yfinance` and does not constitute financial advice.\n",
    "---\n",
    "## 🔮 Future Roadmap\n",
    "* **Risk-Adjusted Return Ratios:** Implement annualized **Sharpe Ratio** and **Sortino Ratio** using US Treasury / SARON risk-free benchmarks.",
    "* **Normalized Relative Performance:** Add a base-100 (`Rebased = 100`) FX-adjusted comparison chart.",
    "* **Vectorized Backtesting:** Build a historical crossover strategy backtester (SMA 50/200 Golden Cross + RSI filter).\n"
]

with open("README.md", "w") as f:
    f.write("\n".join(readme_lines))

print("\nPipeline, requirements.txt, and README.md generated successfully!")
