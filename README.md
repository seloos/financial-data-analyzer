# 📈 Quantitative Financial Data Pipeline & Risk Analyzer

An automated end-to-end **ETL (Extract, Transform, Load) pipeline** and quantitative technical analysis tool built in Python. This system fetches daily market data for **Apple Inc. (`AAPL`)** and **UBS Group AG (`UBSG.SW`)** via the Yahoo Finance API, stores historical time-series and risk metrics in a local **SQLite** database, and generates multi-timeframe dual-axis visualizations updated daily via **GitHub Actions**.

---

## 🚀 Key Features & Architecture

* **Automated Cloud CI/CD Pipeline:** Scheduled via GitHub Actions (`cron`) to execute daily at 08:00 UTC, ensuring the SQLite database and visual dashboards remain continuously updated without manual intervention.
* **Cross-Market Data Cleaning:** Implements forward-filling (`ffill`) across US (NASDAQ) and Swiss (SIX) market calendars to prevent holiday-induced `NaN` gaps in rolling window calculations.
* **Dual-Axis Visualization (`twinx`):** Simultaneously plots equities across different currencies and price scales (**USD** vs. **CHF**) alongside **50-Day** and **200-Day Simple Moving Averages (SMA)**.
* **Relational Storage:** Persists raw closing prices, 14-day RSI time series, and summary risk metrics into structured SQLite tables (`stock_prices`, `stock_rsi`, `risk_metrics`).

---

## 🧮 Quantitative Metrics Implemented

1. **Annualized Volatility ($\sigma_{\text{annual}}$):** Measures the dispersion of daily returns scaled to 252 trading days:
   $$\sigma_{\text{annual}} = \sigma_{\text{daily}} \times \sqrt{252}$$
2. **Maximum Drawdown ($\text{Max DD}$):** Captures tail risk by measuring the largest peak-to-trough percentage decline over the 1-year horizon:
   $$\text{Drawdown}_t = \frac{P_t - \max_{\tau \in [0,t]} P_\tau}{\max_{\tau \in [0,t]} P_\tau} \times 100$$
3. **14-Day Relative Strength Index ($\text{RSI}$):** Momentum oscillator identifying overbought ($>70$) and oversold ($<30$) regimes:
   $$\text{RSI} = 100 - \left( \frac{100}{1 + \frac{\text{Avg Gain}_{14}}{\text{Avg Loss}_{14}}} \right)$$
4. **Simple Moving Averages ($\text{SMA}_{50}$ & $\text{SMA}_{200}$):** Tracks medium- and long-term institutional trend support and Golden/Death Cross regimes.

---

## 📊 Live Automated Market Dashboard

*(Charts below are automatically regenerated and committed daily by GitHub Actions)*

### 1-Year Historical Performance, SMA(50/200) & RSI
![1-Year Analysis](charts/chart_1year.png)

### 6-Month Medium-Term Trend & Momentum
![6-Month Analysis](charts/chart_6months.png)

### 1-Month & 1-Week Short-Term Action
| 1-Month View | 1-Week View |
| :---: | :---: |
| ![1-Month Analysis](charts/chart_1month.png) | ![1-Week Analysis](charts/chart_1week.png) |

---

## 🛠️ Tech Stack
* **Language:** Python 3.9
* **Libraries:** `pandas`, `yfinance`, `matplotlib`, `sqlite3`
* **Automation / DevOps:** GitHub Actions (Ubuntu Runner, Cron Scheduling)
