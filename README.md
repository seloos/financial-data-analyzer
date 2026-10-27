# 📈 Quantitative Financial Data Pipeline & Risk Analyzer

An automated end-to-end **ETL (Extract, Transform, Load) pipeline** and quantitative technical analysis tool built in Python. This system fetches daily market data for **Apple Inc. (`AAPL`)** and **UBS Group AG (`UBSG.SW`)** via the Yahoo Finance API, computes native-calendar risk and momentum metrics into a local **SQLite** database, and generates multi-timeframe dual-axis visualizations updated daily via **GitHub Actions**.

---

## 🚀 Key Features & Architecture

* **Automated Cloud CI/CD Pipeline:** Scheduled via GitHub Actions (`cron`) to execute daily at 08:00 UTC, updating the SQLite database and visual dashboards without manual intervention.
* **Unbiased Native-Calendar Math:** Computes daily returns, annualized volatility, Wilder's RSI, and moving averages on each exchange's native trading calendar (`NASDAQ` vs. `SIX`) *prior* to visual forward-filling (`ffill`), preventing artificial zero-return volatility dampening on cross-market holidays.
* **Dual-Axis Visualization (`twinx`):** Simultaneously plots equities across different currencies and nominal price scales (**USD** vs. **CHF**) alongside **50-Day** and **200-Day Simple Moving Averages (SMA)**.
* **Relational Storage:** Persists raw closing prices, 14-day RSI time series, and summary risk metrics into structured SQLite tables (`stock_prices`, `stock_rsi`, `risk_metrics`).

---

## 📊 Latest Quantitative Risk & Momentum Summary (1-Year)

```
         Latest Price (Local CCY)  Annualized Volatility (%)  Max Drawdown (%)  SMA (50)  SMA (200)  Wilder's RSI (14)
UBSG.SW                     38.77                      24.07            -23.81     41.46      37.39              40.38
AAPL                       343.91                      24.07            -13.80    330.23     294.54              57.70
```

---

## 📈 Live Automated Market Dashboard

*(Charts below are automatically regenerated and committed daily by GitHub Actions)*

### 1-Year Historical Performance, SMA(50/200) & Wilder's RSI
![1-Year Analysis](charts/chart_1year.png)

### 6-Month Medium-Term Trend & Momentum
![6-Month Analysis](charts/chart_6months.png)

### 1-Month & 1-Week Short-Term Action
| 1-Month View | 1-Week View |
| :---: | :---: |
| ![1-Month Analysis](charts/chart_1month.png) | ![1-Week Analysis](charts/chart_1week.png) |

---

## ⚙️ How to Run Locally

1. Clone the repository: `git clone [https://github.com/seloos/financial-data-analyzer.git](https://github.com/seloos/financial-data-analyzer.git)`
2. Install dependencies: `pip3 install -r requirements.txt`
3. Run the pipeline: `python3 main.py`

---

## ⚠️ Methodology, Limitations & Disclaimer

* **Wilder's Smoothing:** RSI is calculated using J. Welles Wilder's original exponential smoothing (`alpha = 1/14`) rather than a simple rolling mean, aligning values with institutional terminals.
* **Currency Denominations (Local CCY):** Returns, volatility, and moving averages are calculated in each asset's native listing currency (`AAPL` in **USD**, `UBSG.SW` in **CHF**) without FX conversion.
* **Dual Y-Axis Scaling:** Charts utilize a dual Y-axis (`twinx`) to preserve nominal price levels and exact SMA crossover points. Refer to the summary table above for direct risk-adjusted percentage comparisons.
* **Database Artifact:** `stock_data.db` is committed directly to the repository as an inspectable snapshot updated by GitHub Actions. Running `python3 main.py` locally regenerates this file.
* **Disclaimer:** Built strictly for educational and quantitative engineering demonstration purposes. Data is sourced via `yfinance` and does not constitute financial advice.

---

## 🔮 Future Roadmap

* **Risk-Adjusted Return Ratios:** Implement annualized **Sharpe Ratio** and **Sortino Ratio** using US Treasury / SARON risk-free benchmarks.
* **Normalized Relative Performance:** Add a base-100 (`Rebased = 100`) FX-adjusted comparison chart.
* **Vectorized Backtesting:** Build a historical crossover strategy backtester (SMA 50/200 Golden Cross + RSI filter).
