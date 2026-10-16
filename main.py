import sqlite3
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt

# 1. Fetch stock data
tickers = ["UBSG.SW", "AAPL"]
print("Downloading financial data from Yahoo Finance...")
data = yf.download(tickers, period="1y", interval="1d")['Close']

# 2. Save to SQLite database
conn = sqlite3.connect("stock_data.db")
data.to_sql("stock_prices", conn, if_exists="replace", index=True)
conn.close()

# 3. Read back from database and calculate returns & volatility
conn = sqlite3.connect("stock_data.db")
df = pd.read_sql("SELECT * FROM stock_prices", conn, parse_dates=["Date"])
conn.close()

df.set_index("Date", inplace=True)

# Daily percentage returns (%)
returns = df.pct_change() * 100

print("\n--- Last 5 Days Percentage Returns (%) ---")
print(returns.tail(5))

# Annualized Volatility (Risk) Calculation
annualized_volatility = returns.std() * (252 ** 0.5)

print("\n--- Annualized Volatility (Risk %) ---")
print(annualized_volatility)

# 4. Generate & Save Professional English Chart
print("\nGenerating stock price chart...")
plt.figure(figsize=(10, 5))
plt.plot(df.index, df["AAPL"], label="Apple (AAPL)", color="blue")
plt.plot(df.index, df["UBSG.SW"], label="UBS Zürich (UBSG.SW)", color="orange")
plt.setTitle("1-Year Historical Stock Price Movements")
plt.xlabel("Date")
plt.ylabel("Closing Price (USD / CHF)")
plt.legend()
plt.grid(True)

plt.savefig("stock_chart.png")
print("Chart successfully saved as 'stock_chart.png'!")
