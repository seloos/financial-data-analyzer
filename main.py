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

# 3. Quantitative Functions (Wilder's RSI, Max Drawdown, Sharpe Ratio)
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

def calculate_sharpe(daily_returns_decimal):
    if daily_returns_decimal.std() == 0:
        return 0.0
    return (daily_returns_decimal.mean() / daily_returns_decimal.std()) * np.sqrt(252)

# 4. Compute Metrics & Run Vectorized Backtest with Transaction Costs (10 bps = 0.10%)
COST_BPS = 0.0010  # 0.10% commission + slippage per trade

rsi_dict, sma50_dict, sma200_dict = {}, {}, {}
vol_dict, mdd_dict, sharpe_dict, latest_price = {}, {}, {}, {}
bt_results = {}
bt_curves = {}

for ticker in tickers:
    s_clean = raw_data[ticker].dropna()
    
    rsi_s = calculate_wilders_rsi(s_clean, 14)
    sma50_s = s_clean.rolling(window=50, min_periods=50).mean()
    sma200_s = s_clean.rolling(window=200, min_periods=200).mean()
    
    # 1-Year window (252 native trading days)
    s_1y = s_clean.tail(252)
    sma50_1y_nat = sma50_s.tail(252)
    sma200_1y_nat = sma200_s.tail(252)
    rsi_1y_nat = rsi_s.tail(252)
    ret_1y_dec = s_1y.pct_change().dropna()
    
    vol_dict[ticker] = ret_1y_dec.std() * np.sqrt(252) * 100.0
    mdd_dict[ticker] = calculate_max_drawdown(s_1y)
    sharpe_dict[ticker] = calculate_sharpe(ret_1y_dec)
    latest_price[ticker] = s_1y.iloc[-1]
    
    # --- STRATEGY 1: Classic SMA(50) Trend-Following ---
    sig_sma50 = (s_1y > sma50_1y_nat).astype(int)
    pos_sma50 = sig_sma50.shift(1).loc[ret_1y_dec.index].fillna(0)
    trades_sma50 = pos_sma50.diff().abs().fillna(pos_sma50.iloc[0])
    net_ret_sma50 = (pos_sma50 * ret_1y_dec) - (trades_sma50 * COST_BPS)
    
    # --- STRATEGY 2: v2.1 Multi-Factor Regime Filter (SMA 50/200 + RSI Whipsaw Protection) ---
    # Stay Long if Price > SMA50 OR (Price > SMA200 and RSI < 65 to survive shallow bull-market dips)
    sig_multi = ((s_1y > sma50_1y_nat) | ((s_1y > sma200_1y_nat) & (rsi_1y_nat < 65))).astype(int)
    pos_multi = sig_multi.shift(1).loc[ret_1y_dec.index].fillna(0)
    trades_multi = pos_multi.diff().abs().fillna(pos_multi.iloc[0])
    net_ret_multi = (pos_multi * ret_1y_dec) - (trades_multi * COST_BPS)
    
    # Cumulative Equity Curves (Rebased to 100, Net of Costs)
    bh_curve = (1.0 + ret_1y_dec).cumprod() * 100.0
    sma50_curve = (1.0 + net_ret_sma50).cumprod() * 100.0
    multi_curve = (1.0 + net_ret_multi).cumprod() * 100.0
    
    bt_curves[f"{ticker}_BH"] = bh_curve
    bt_curves[f"{ticker}_SMA50"] = sma50_curve
    bt_curves[f"{ticker}_MULTI"] = multi_curve
    
    bt_results[f"{ticker} (Buy & Hold)"] = {
        "Net Return (%)": (bh_curve.iloc[-1] - 100.0),
        "Net Sharpe": calculate_sharpe(ret_1y_dec),
        "Max DD (%)": calculate_max_drawdown(bh_curve),
        "Trades": 1
    }
    bt_results[f"{ticker} (SMA50 Only)"] = {
        "Net Return (%)": (sma50_curve.iloc[-1] - 100.0),
        "Net Sharpe": calculate_sharpe(net_ret_sma50),
        "Max DD (%)": calculate_max_drawdown(sma50_curve),
        "Trades": int(trades_sma50.sum())
    }
    bt_results[f"{ticker} (v2.1 Multi-Factor)"] = {
        "Net Return (%)": (multi_curve.iloc[-1] - 100.0),
        "Net Sharpe": calculate_sharpe(net_ret_multi),
        "Max DD (%)": calculate_max_drawdown(multi_curve),
        "Trades": int(trades_multi.sum())
    }
    
    rsi_dict[ticker] = rsi_s
    sma50_dict[ticker] = sma50_s
    sma200_dict[ticker] = sma200_s

# Align series onto unified index for plotting
df_plot = raw_data.ffill().dropna().tail(252)
rsi_1y = pd.DataFrame(rsi_dict).reindex(df_plot.index).ffill()
sma50_1y = pd.DataFrame(sma50_dict).reindex(df_plot.index).ffill()
sma200_1y = pd.DataFrame(sma200_dict).reindex(df_plot.index).ffill()
bt_curves_df = pd.DataFrame(bt_curves).reindex(df_plot.index).ffill().bfill()

risk_summary = pd.DataFrame({
    "Latest Price (CCY)": pd.Series(latest_price),
    "Annual Volatility (%)": pd.Series(vol_dict),
    "Sharpe Ratio": pd.Series(sharpe_dict),
    "Max Drawdown (%)": pd.Series(mdd_dict),
    "SMA (50)": sma50_1y.iloc[-1],
    "SMA (200)": sma200_1y.iloc[-1],
    "Wilder's RSI (14)": rsi_1y.iloc[-1]
})

backtest_summary = pd.DataFrame(bt_results).T
backtest_summary["Trades"] = backtest_summary["Trades"].astype(int)

print("\n=== v2.1 QUANTITATIVE RISK & MOMENTUM SUMMARY (1-YEAR) ===")
print(risk_summary.round(2))
print("\n=== v2.1 BACKTEST COMPARISON (NET OF 10 BPS TRANSACTION COSTS) ===")
print(backtest_summary.round(2))

# Save all tables to SQLite database
conn = sqlite3.connect("stock_data.db")
rsi_1y.to_sql("stock_rsi", conn, if_exists="replace", index=True)
risk_summary.to_sql("risk_metrics", conn, if_exists="replace", index=True)
backtest_summary.to_sql("backtest_results", conn, if_exists="replace", index=True)
conn.close()

# 5. Generate Multi-Timeframe Dual-Axis Charts + v2.1 Two-Panel Backtest Chart
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
    plt.savefig(os.path.join("charts", filename), dpi=120)
    plt.close()

periods = {
    "chart_1week.png": (df_plot.tail(5), sma50_1y.tail(5), sma200_1y.tail(5), rsi_1y.tail(5), "1-Week Price, SMA(50/200) & Wilder's RSI"),
    "chart_1month.png": (df_plot.tail(21), sma50_1y.tail(21), sma200_1y.tail(21), rsi_1y.tail(21), "1-Month Price, SMA(50/200) & Wilder's RSI"),
    "chart_6months.png": (df_plot.tail(126), sma50_1y.tail(126), sma200_1y.tail(126), rsi_1y.tail(126), "6-Month Price, SMA(50/200) & Wilder's RSI"),
    "chart_1year.png": (df_plot, sma50_1y, sma200_1y, rsi_1y, "1-Year Price, SMA(50/200) & Wilder's RSI")
}

for filename, (p_sub, s50_sub, s200_sub, r_sub, title) in periods.items():
    generate_chart(p_sub, s50_sub, s200_sub, r_sub, filename, title)

# Generate v2.1 Backtest Equity Curve Chart (Two Subplots: AAPL & UBS)
fig, (ax_aapl, ax_ubs) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

# Top Panel: Apple Backtest
ax_aapl.plot(bt_curves_df.index, bt_curves_df["AAPL_BH"], label="AAPL Buy & Hold", color="gray", linestyle="--", linewidth=1.5)
ax_aapl.plot(bt_curves_df.index, bt_curves_df["AAPL_SMA50"], label="AAPL SMA(50) Only (Whipsaw Prone)", color="#00a3bf", linestyle=":", linewidth=1.8)
ax_aapl.plot(bt_curves_df.index, bt_curves_df["AAPL_MULTI"], label="AAPL v2.1 Multi-Factor (SMA50/200 + RSI)", color="#0052cc", linewidth=2.3)
ax_aapl.axhline(100, color="black", linestyle=":", linewidth=0.8)
ax_aapl.set_title("v2.1 Backtest (Net of 10 bps Costs): Apple (AAPL) — Solving the Whipsaw Effect", fontsize=12, fontweight="bold")
ax_aapl.set_ylabel("Portfolio Value (Base 100)", fontweight="bold")
ax_aapl.legend(loc="upper left", fontsize=9)
ax_aapl.grid(True, linestyle="--", alpha=0.5)

# Bottom Panel: UBS Backtest
ax_ubs.plot(bt_curves_df.index, bt_curves_df["UBSG.SW_BH"], label="UBS Buy & Hold", color="gray", linestyle="--", linewidth=1.5)
ax_ubs.plot(bt_curves_df.index, bt_curves_df["UBSG.SW_SMA50"], label="UBS SMA(50) Only", color="#ff8b00", linewidth=2.2)
ax_ubs.plot(bt_curves_df.index, bt_curves_df["UBSG.SW_MULTI"], label="UBS v2.1 Multi-Factor (SMA50/200 + RSI)", color="#bf2600", linestyle="-.", linewidth=1.8)
ax_ubs.axhline(100, color="black", linestyle=":", linewidth=0.8)
ax_ubs.set_title("v2.1 Backtest (Net of 10 bps Costs): UBS Group (UBSG.SW) — Drawdown Protection", fontsize=12, fontweight="bold")
ax_ubs.set_ylabel("Portfolio Value (Base 100)", fontweight="bold")
ax_ubs.set_xlabel("Date")
ax_ubs.legend(loc="upper left", fontsize=9)
ax_ubs.grid(True, linestyle="--", alpha=0.5)

plt.tight_layout()
plt.savefig(os.path.join("charts", "chart_backtest.png"), dpi=120)
plt.close()
print("Successfully updated: charts/chart_backtest.png")

# 6. Update README.md
readme_lines = [
    "# 📈 Quantitative Financial Data Pipeline, Risk Analyzer & Backtester (v2.1)\n",
    "An automated end-to-end **ETL (Extract, Transform, Load) pipeline**, quantitative risk analyzer, and vectorized backtesting engine built in Python. This system fetches daily market data for **Apple Inc. (`AAPL`)** and **UBS Group AG (`UBSG.SW`)** via the Yahoo Finance API, computes native-calendar risk/momentum metrics and transaction-cost-adjusted strategy backtests into a local **SQLite** database, and generates daily visualizations via **GitHub Actions**.\n",
    "---\n",
    "## 🚀 Key Features & Architecture\n",
    "* **Automated Cloud CI/CD Pipeline:** Scheduled via GitHub Actions (`cron`) to execute daily at 08:00 UTC, updating the SQLite database, README metrics, and visual dashboards automatically.",
    "* **v2.1 Multi-Factor Backtesting & Transaction Costs:** Compares a single-factor **SMA(50)** trend strategy against a **Multi-Factor Regime Filter (SMA 50/200 + RSI)** designed to eliminate bull-market whipsaws, deducting **10 bps (0.10%)** per trade for realistic slippage and commission modeling.",
    "* **Unbiased Native-Calendar Math:** Computes daily returns, annualized volatility, **Sharpe Ratio**, Wilder's RSI, and moving averages on each exchange's native trading calendar (`NASDAQ` vs. `SIX`) *prior* to visual forward-filling (`ffill`).\n",
    "---\n",
    "## 📊 Latest Quantitative Risk & Momentum Summary (1-Year)\n",
    "```\n" + risk_summary.round(2).to_string() + "\n```\n",
    "## 🧪 v2.1 Strategy Backtest Comparison (Net of 10 bps Costs, 1-Year)\n",
    "```\n" + backtest_summary.round(2).to_string() + "\n```\n",
    "![Backtest Equity Curves](charts/chart_backtest.png)\n",
    "---\n",
    "## 📈 Live Automated Market Dashboard\n",
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
    "1. Clone the repository: `git clone https://github.com/seloos/financial-data-analyzer.git`",
    "2. Install dependencies: `pip3 install -r requirements.txt`",
    "3. Run the pipeline: `python3 main.py`\n",
    "---\n",
    "## ⚠️ Methodology, Limitations & Disclaimer\n",
    "* **Look-Ahead Bias Prevention:** Strategy signals generated at Day $t$ market close are executed on Day $t+1$ returns via `signal.shift(1)`.",
    "* **Transaction Cost Modeling:** Every position flip (`0 -> 1` or `1 -> 0`) incurs a **10 bps (0.10%)** cost deducted directly from daily strategy returns.",
    "* **Wilder's Smoothing:** RSI is calculated using J. Welles Wilder's original exponential smoothing (`alpha = 1/14`).",
    "* **Disclaimer:** Built strictly for educational and quantitative engineering demonstration purposes. Does not constitute financial advice.\n"
]

with open("README.md", "w") as f:
    f.write("\n".join(readme_lines))

print("\nv2.1 Multi-Factor Backtest and README updated successfully!")
