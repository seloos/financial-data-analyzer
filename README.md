# 📈 Quantitative Financial Data Pipeline, Risk Analyzer & Backtester (v2.2)

An automated end-to-end **ETL (Extract, Transform, Load) pipeline**, quantitative risk analyzer, and vectorized backtesting engine built in Python. This system ingests 10 years of historical equity data for **Apple Inc. (`AAPL`)** and **UBS Group AG (`UBSG.SW`)** via Yahoo Finance (`auto_adjust=True`), evaluates strategy backtests across native trading calendars, and updates visualizations daily via **GitHub Actions**.

---

## 🚀 Key Features & Architecture

* **Automated Cloud CI/CD Pipeline:** Scheduled via GitHub Actions (`cron`) at 08:00 UTC, committing updated SQLite databases and visual dashboards automatically.
* **v2.2 Multi-Factor Regime Filter & Cost Modeling:** Evaluates a trend filter (`Price > SMA50` OR `Price > SMA200 & RSI < 65`) across a 10-year historical ingestion window, incorporating a **10 bps (0.10%)** transaction fee on both Buy & Hold and strategy executions.
* **Robust Out-of-Sample / In-Sample Separation:** Explicitly documents parameter tuning limitations and regime sensitivity across different asset classes.

---

## 📊 Latest Quantitative Risk & Momentum Summary (1-Year Slice)

```
         Latest Price (CCY)  Annual Volatility (%)  Sharpe Ratio  Max Drawdown (%)  SMA (50)  SMA (200)  Wilder's RSI (14)
UBSG.SW               38.39                  24.08          1.18            -23.81     41.37      37.40              38.09
AAPL                 347.10                  23.98          1.21            -13.80    331.06     294.98              61.11
```

## 🧪 v2.2 Strategy Backtest Comparison (Net of 10 bps Costs)

```
                             Net Return (%)  Net Sharpe  Max DD (%)  Trades
UBSG.SW (Buy & Hold)                  29.05        1.18      -23.81       1
UBSG.SW (v2.2 Multi-Factor)           21.95        1.01      -19.76       2
AAPL (Buy & Hold)                     29.60        1.21      -13.80       1
AAPL (v2.2 Multi-Factor)              25.69        1.08      -14.01       2
```

![Backtest Equity Curves](charts/chart_backtest.png)

---

## ⚠️ Methodology, Limitations & Peer-Review Notes

* **In-Sample Optimization & Whipsaw Reduction:** Multi-factor thresholds (`RSI < 65`) were evaluated on historical data to *reduce* (rather than eliminate) whipsaw effects; performance reflects in-sample sample characteristics.
* **Regime Sensitivity:** Single-rule trend filters perform robustly on trending financial equities (UBS) but encounter friction on tech equities prone to shallow dips (AAPL).
* **Transaction Costs & Cash Return:** A 10 bps fee is applied to initial Buy & Hold allocation and strategy switches. Cash held outside the market earns **0% risk-free interest**.
* **Data Ingestion:** Sourced via `yfinance` with `auto_adjust=True` to account for corporate actions and dividends.
