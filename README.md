# 📈 Quantitative Financial Data Pipeline, Risk Analyzer & Backtester (v2.0)

An automated end-to-end **ETL (Extract, Transform, Load) pipeline**, quantitative risk analyzer, and vectorized backtesting engine built in Python. This system fetches daily market data for **Apple Inc. (`AAPL`)** and **UBS Group AG (`UBSG.SW`)** via the Yahoo Finance API, computes native-calendar risk/momentum metrics and strategy backtests into a local **SQLite** database, and generates daily visualizations via **GitHub Actions**.

---

## 🚀 Key Features & Architecture

* **Automated Cloud CI/CD Pipeline:** Scheduled via GitHub Actions (`cron`) to execute daily at 08:00 UTC, updating the SQLite database, README metrics, and visual dashboards automatically.
* **v2.0 Vectorized Backtesting Engine:** Simulates a regime-switching **SMA(50) Trend-Following Strategy** (`Long` when $P_t > \text{SMA}_{50,t}$, `Cash` otherwise) using a 1-day execution lag (`.shift(1)`) to strictly eliminate look-ahead bias.
* **Unbiased Native-Calendar Math:** Computes daily returns, annualized volatility, **Sharpe Ratio**, Wilder's RSI, and moving averages on each exchange's native trading calendar (`NASDAQ` vs. `SIX`) *prior* to visual forward-filling (`ffill`).
* **Relational Storage:** Persists raw closing prices, 14-day RSI time series, risk metrics, and backtest performance into structured SQLite tables (`stock_prices`, `stock_rsi`, `risk_metrics`, `backtest_results`).

---

## 📊 Latest Quantitative Risk & Momentum Summary (1-Year)

```
         Latest Price (CCY)  Annual Volatility (%)  Sharpe Ratio  Max Drawdown (%)  SMA (50)  SMA (200)  Wilder's RSI (14)
UBSG.SW               38.89                  24.07          1.29            -23.81     41.46      37.39              41.51
AAPL                 345.98                  23.97          1.19            -13.80    331.03     294.97              59.97
```

## 🧪 v2.0 Backtest Performance: SMA(50) Strategy vs. Buy & Hold (1-Year)

```
         Buy & Hold Return (%)  Strategy Return (%)  Buy & Hold Sharpe  Strategy Sharpe  Buy & Hold Max DD (%)  Strategy Max DD (%)
UBSG.SW                  32.24                48.39               1.29             2.29                 -23.81                -8.88
AAPL                     29.18                11.40               1.19             0.64                 -13.80               -12.71
```

![Backtest Equity Curves](charts/chart_backtest.png)

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

1. Clone the repository: `git clone https://github.com/seloos/financial-data-analyzer.git`
2. Install dependencies: `pip3 install -r requirements.txt`
3. Run the pipeline: `python3 main.py`

---

## ⚠️ Methodology, Limitations & Disclaimer

* **Look-Ahead Bias Prevention:** Strategy signals generated at Day $t$ market close are executed on Day $t+1$ returns via `signal.shift(1)`.
* **Zero Transaction Cost Assumption:** Backtest returns represent gross performance and do not deduct brokerage commissions, bid-ask spread slippage, or interest on cash.
* **Wilder's Smoothing:** RSI is calculated using J. Welles Wilder's original exponential smoothing (`alpha = 1/14`).
* **Currency Denominations (Local CCY):** Metrics are calculated in each asset's native listing currency (`AAPL` in **USD**, `UBSG.SW` in **CHF**). The backtest chart normalizes both assets to **Base = 100** for direct relative comparison.
* **Disclaimer:** Built strictly for educational and quantitative engineering demonstration purposes. Does not constitute financial advice.
