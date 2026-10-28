"""
Financial Data Analyzer v2.3
ETL (Yahoo Finance -> SQLite) + risk metrics + transparent backtest.
Writes charts/, requirements.txt and README.md on every run (GitHub Actions runs it daily).
"""
import os
import sqlite3
from datetime import datetime, timezone

import matplotlib
matplotlib.use("Agg")  # headless-safe (GitHub Actions)
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, LogLocator, NullFormatter
import numpy as np
import pandas as pd
import yfinance as yf

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
TICKERS = ["UBSG.SW", "AAPL"]
PERIOD = "10y"
COST = 0.0010          # 10 bps per position change (commission + slippage)
RSI_THRESHOLD = 65     # chosen AFTER looking at the last year -> see README limitations
DASH_DAYS = 252        # ~1 trading year: dashboard window and "tuning window"

STRATEGIES = ["Buy & Hold", "SMA50 Only", "Multi-Factor", "Multi-Factor w/o RSI"]
STYLE = {  # colour, linestyle, linewidth
    "Buy & Hold": ("gray", "--", 1.6),
    "SMA50 Only": ("#ff8b00", "-", 1.6),
    "Multi-Factor": ("#0052cc", "-", 2.2),
    "Multi-Factor w/o RSI": ("#6554c0", ":", 1.8),
}
LAST_LABEL = f"Last {DASH_DAYS} days"

# ---------------------------------------------------------------------------
# 1. Fetch data (adjusted close = splits + dividends)
# ---------------------------------------------------------------------------
print(f"Downloading {PERIOD} of daily data from Yahoo Finance...")
raw_data = yf.download(TICKERS, period=PERIOD, interval="1d", auto_adjust=True)["Close"]
if raw_data is None or raw_data.empty:
    raise SystemExit("No data returned from Yahoo Finance.")
raw_data = raw_data[TICKERS]

conn = sqlite3.connect("stock_data.db")
raw_data.to_sql("stock_prices", conn, if_exists="replace", index=True)
conn.close()


# ---------------------------------------------------------------------------
# 2. Quantitative helpers
# ---------------------------------------------------------------------------
def wilders_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss  # avg_loss == 0 -> inf -> RSI 100; warm-up stays NaN
    return 100.0 - 100.0 / (1.0 + rs)


def max_drawdown(series):
    rolling_max = series.cummax()
    return ((series - rolling_max) / rolling_max * 100.0).min()


def sharpe(daily_returns):
    sd = daily_returns.std()
    return 0.0 if sd == 0 or np.isnan(sd) else daily_returns.mean() / sd * np.sqrt(252)


def run_segment(ret, pos):
    """Run one strategy on one segment as a fresh start (entry cost included)."""
    trades = pos.diff().abs()
    trades.iloc[0] = pos.iloc[0]
    net = pos * ret - trades * COST
    curve = (1.0 + net).cumprod() * 100.0
    years = len(net) / 252.0
    stats = {
        "Net Return (%)": curve.iloc[-1] - 100.0,
        "Ann. Return (%)": ((curve.iloc[-1] / 100.0) ** (1.0 / years) - 1.0) * 100.0,
        "Net Sharpe": sharpe(net),
        "Max DD (%)": max_drawdown(curve),
        "Trades": int(trades.sum()),
        "In Market (%)": pos.mean() * 100.0,
    }
    return curve, stats


# ---------------------------------------------------------------------------
# 3. Indicators, risk metrics and backtest (each ticker on its own calendar)
# ---------------------------------------------------------------------------
indicators, risk, rows, curves, period_text = {}, {}, [], {}, []

for t in TICKERS:
    s = raw_data[t].dropna()
    rsi = wilders_rsi(s, 14)
    sma50 = s.rolling(50, min_periods=50).mean()
    sma200 = s.rolling(200, min_periods=200).mean()
    indicators[t] = (rsi, sma50, sma200)

    # Risk metrics: last DASH_DAYS trading days
    s_1y = s.tail(DASH_DAYS)
    r_1y = s_1y.pct_change().dropna()
    risk[t] = {
        "Latest Price (CCY)": s_1y.iloc[-1],
        "Annual Volatility (%)": r_1y.std() * np.sqrt(252) * 100.0,
        "Sharpe Ratio": sharpe(r_1y),
        "Max Drawdown (%)": max_drawdown(s_1y),
        "SMA (50)": sma50.iloc[-1],
        "SMA (200)": sma200.iloc[-1],
        "Wilder's RSI (14)": rsi.iloc[-1],
    }

    # Backtest: all strategies (and Buy & Hold) cover the SAME dates, starting
    # once the SMA(200) exists, so nobody is penalised for warm-up.
    first_valid = sma200.first_valid_index()
    ret = s.pct_change().dropna()
    ret = ret.loc[ret.index > first_valid]
    if len(ret) <= 2 * DASH_DAYS:
        raise SystemExit(f"Not enough history for {t} (need more than {2 * DASH_DAYS} backtest days).")

    signals = {
        "Buy & Hold": pd.Series(1.0, index=s.index),
        "SMA50 Only": (s > sma50).astype(float),
        "Multi-Factor": ((s > sma50) | ((s > sma200) & (rsi < RSI_THRESHOLD))).astype(float),
        "Multi-Factor w/o RSI": ((s > sma50) | (s > sma200)).astype(float),  # ablation
    }
    # Signal at close of day t is executed on day t+1 returns (no look-ahead)
    positions = {n: sg.shift(1).reindex(ret.index).fillna(0.0) for n, sg in signals.items()}

    idx = ret.index
    segments = {
        "Full period": idx,
        "Older period": idx[:-DASH_DAYS],
        LAST_LABEL: idx[-DASH_DAYS:],
    }
    period_text.append(f"{t}: {idx[0].date()} to {idx[-1].date()}")
    for seg_name, seg_idx in segments.items():
        for name in STRATEGIES:
            curve, stats = run_segment(ret.loc[seg_idx], positions[name].loc[seg_idx])
            rows.append({"Ticker": t, "Strategy": name, "Segment": seg_name, **stats})
            curves.setdefault((t, seg_name), {})[name] = curve

results = pd.DataFrame(rows)
risk_summary = pd.DataFrame(risk).T

# Dashboard series on a unified calendar (forward-fill for plotting only)
df_plot = raw_data.ffill().dropna().tail(DASH_DAYS)
rsi_1y = pd.DataFrame({t: indicators[t][0] for t in TICKERS}).reindex(df_plot.index).ffill()
sma50_1y = pd.DataFrame({t: indicators[t][1] for t in TICKERS}).reindex(df_plot.index).ffill()
sma200_1y = pd.DataFrame({t: indicators[t][2] for t in TICKERS}).reindex(df_plot.index).ffill()


def seg_table(seg):
    d = results[results["Segment"] == seg].drop(columns="Segment").set_index(["Ticker", "Strategy"])
    return d.round(2).to_string()


print("\n=== RISK & MOMENTUM SUMMARY (LAST 252 DAYS) ===")
print(risk_summary.round(2))
for seg in ["Full period", "Older period", LAST_LABEL]:
    print(f"\n=== BACKTEST: {seg.upper()} (NET OF {COST * 1e4:.0f} BPS) ===")
    print(seg_table(seg))

conn = sqlite3.connect("stock_data.db")
rsi_1y.to_sql("stock_rsi", conn, if_exists="replace", index=True)
risk_summary.to_sql("risk_metrics", conn, if_exists="replace", index=True)
results.to_sql("backtest_results", conn, if_exists="replace", index=False)
conn.close()

# ---------------------------------------------------------------------------
# 4. Charts
# ---------------------------------------------------------------------------
os.makedirs("charts", exist_ok=True)


def generate_chart(price_sub, sma50_sub, sma200_sub, rsi_sub, filename, title_text):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True,
                                   gridspec_kw={"height_ratios": [2.2, 1]})
    l1 = ax1.plot(price_sub.index, price_sub["AAPL"], label="AAPL Price (USD)", color="#0052cc", linewidth=2)
    l2 = ax1.plot(sma50_sub.index, sma50_sub["AAPL"], label="AAPL SMA(50)", color="#00a3bf", linestyle="--", linewidth=1.5)
    l3 = ax1.plot(sma200_sub.index, sma200_sub["AAPL"], label="AAPL SMA(200)", color="#6554c0", linestyle=":", linewidth=2)
    ax1.set_ylabel("Apple Price (USD)", color="#0052cc", fontweight="bold")
    ax1.tick_params(axis="y", labelcolor="#0052cc")
    ax1.grid(True, linestyle="--", alpha=0.5)

    ax1r = ax1.twinx()
    l4 = ax1r.plot(price_sub.index, price_sub["UBSG.SW"], label="UBS Price (CHF)", color="#ff8b00", linewidth=2)
    l5 = ax1r.plot(sma50_sub.index, sma50_sub["UBSG.SW"], label="UBS SMA(50)", color="#ff5630", linestyle="--", linewidth=1.5)
    l6 = ax1r.plot(sma200_sub.index, sma200_sub["UBSG.SW"], label="UBS SMA(200)", color="#bf2600", linestyle=":", linewidth=2)
    ax1r.set_ylabel("UBS Zürich Price (CHF)", color="#ff8b00", fontweight="bold")
    ax1r.tick_params(axis="y", labelcolor="#ff8b00")

    lines = l1 + l2 + l3 + l4 + l5 + l6
    ax1.legend(lines, [ln.get_label() for ln in lines], loc="upper left", fontsize=8.5, ncol=2, framealpha=0.9)
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
    plt.close(fig)


periods = {
    "chart_1week.png": (5, "1-Week Price, SMA(50/200) & Wilder's RSI"),
    "chart_1month.png": (21, "1-Month Price, SMA(50/200) & Wilder's RSI"),
    "chart_6months.png": (126, "6-Month Price, SMA(50/200) & Wilder's RSI"),
    "chart_1year.png": (DASH_DAYS, "1-Year Price, SMA(50/200) & Wilder's RSI"),
}
for fname, (n, title) in periods.items():
    generate_chart(df_plot.tail(n), sma50_1y.tail(n), sma200_1y.tail(n), rsi_1y.tail(n), fname, title)


def plot_backtest(segment, filename, heading, log_scale=False, mark_tuning=False):
    fig, axes = plt.subplots(len(TICKERS), 1, figsize=(12, 4.6 * len(TICKERS)))
    for ax, t in zip(axes, TICKERS):
        for name, curve in curves[(t, segment)].items():
            color, ls, lw = STYLE[name]
            ax.plot(curve.index, curve.values, label=name, color=color, linestyle=ls, linewidth=lw)
        if mark_tuning:
            start = curves[(t, LAST_LABEL)]["Buy & Hold"].index[0]
            ax.axvline(start, color="black", linestyle="-.", linewidth=1,
                       label=f"{LAST_LABEL} (RSI threshold chosen here)")
        ax.axhline(100, color="black", linestyle=":", linewidth=0.8)
        if log_scale:
            ax.set_yscale("log")
            ax.yaxis.set_major_locator(LogLocator(base=10, subs=(1, 2, 3, 5), numticks=12))
            ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
            ax.yaxis.set_minor_formatter(NullFormatter())
        ax.set_title(f"{heading}: {t} (net of {COST * 1e4:.0f} bps costs"
                     f"{', log scale' if log_scale else ''})", fontsize=12, fontweight="bold")
        ax.set_ylabel("Portfolio Value (Base 100)", fontweight="bold")
        ax.legend(loc="upper left", fontsize=9)
        ax.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()
    plt.savefig(os.path.join("charts", filename), dpi=120)
    plt.close(fig)


plot_backtest("Full period", "chart_backtest.png", "Backtest, full period", log_scale=True, mark_tuning=True)
plot_backtest(LAST_LABEL, "chart_backtest_1y.png", f"Backtest, {LAST_LABEL.lower()}")

# ---------------------------------------------------------------------------
# 5. requirements.txt and README.md
# ---------------------------------------------------------------------------
with open("requirements.txt", "w") as f:
    f.write("yfinance>=0.2.40\npandas>=2.0.0\nnumpy>=1.24.0\nmatplotlib>=3.7.0\n")

now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
readme = f"""# Financial Data Pipeline, Risk Analyzer & Transparent Backtester (v2.3)

Automated pipeline: **Yahoo Finance -> SQLite -> risk metrics -> backtest -> charts -> this README**,
for Apple (`AAPL`) and UBS Group (`UBSG.SW`). Refreshed daily by GitHub Actions (see `.github/workflows`).
Last updated: {now}.

## What it does

* **ETL:** downloads {PERIOD} of daily adjusted prices (`auto_adjust=True`, i.e. splits and dividends included) and stores them in SQLite.
* **Risk metrics (last {DASH_DAYS} trading days):** annualised volatility, Sharpe ratio, maximum drawdown, SMA(50/200), Wilder's RSI(14).
* **Backtest:** four rules are compared on identical dates:
  1. `Buy & Hold`
  2. `SMA50 Only`: long while price > SMA(50)
  3. `Multi-Factor`: long while price > SMA(50) OR (price > SMA(200) AND RSI < {RSI_THRESHOLD})
  4. `Multi-Factor w/o RSI`: ablation, long while price > SMA(50) OR price > SMA(200). Comparing rows 3 and 4 shows whether the RSI condition adds anything.
* Results are reported for three periods: the **full period**, the **older period** (everything before the last {DASH_DAYS} days) and the **last {DASH_DAYS} days**.

Backtest data: {'; '.join(period_text)}.

## Risk & momentum summary (last {DASH_DAYS} days)

```
{risk_summary.round(2).to_string()}
```

## Backtest results (net of {COST * 1e4:.0f} bps per position change)

### Full period
```
{seg_table("Full period")}
```
![Backtest, full period](charts/chart_backtest.png)

### Older period (before the last {DASH_DAYS} days)
```
{seg_table("Older period")}
```

### {LAST_LABEL} (the window in which the Multi-Factor rule was designed)
```
{seg_table(LAST_LABEL)}
```
![Backtest, last year](charts/chart_backtest_1y.png)

## Market dashboard

![1-Year Analysis](charts/chart_1year.png)
![6-Month Analysis](charts/chart_6months.png)

| 1-Month View | 1-Week View |
| :---: | :---: |
| ![1-Month Analysis](charts/chart_1month.png) | ![1-Week Analysis](charts/chart_1week.png) |

## How to run locally

```
git clone https://github.com/seloos/financial-data-analyzer.git
cd financial-data-analyzer
pip install -r requirements.txt
python main.py
```

## Methodology & limitations

* **No look-ahead:** a signal computed at the close of day t is applied to the returns of day t+1 (`shift(1)`).
* **Same dates for everyone:** evaluation starts once SMA(200) exists, so all strategies and Buy & Hold cover identical days.
* **Costs:** {COST * 1e4:.0f} bps per position change, including the initial entry. Each period is run as a fresh start (a strategy that is already invested at the start of a period pays the entry cost, like Buy & Hold).
* **Cash earns 0%** and the Sharpe ratio uses a 0% risk-free rate. Taxes are ignored.
* **In-sample warning:** the Multi-Factor rule and its RSI threshold ({RSI_THRESHOLD}) were chosen after looking at the last {DASH_DAYS} days, where SMA(50) alone produced many false signals on AAPL. That window is therefore in-sample. The older period is only a rough out-of-sample check, not a clean one, because the author had already seen the price history.
* **Two assets, chosen in hindsight:** this is not statistical evidence of any trading edge. Results can look better or worse than Buy & Hold depending on the period, and the tables above are regenerated from live data on every run.
* **Data:** Yahoo Finance via `yfinance`; no checks for data errors or survivorship effects.
* **Disclaimer:** educational project, not financial advice.
"""

with open("README.md", "w") as f:
    f.write(readme)

print("\nv2.3 finished: database, charts, requirements.txt and README.md updated.")
