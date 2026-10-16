import sqlite3
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt

# 1. Fetch stock data (1 year data covers all periods)
tickers = ["UBSG.SW", "AAPL"]
print("Downloading multi-period financial data...")
data = yf.download(tickers, period="1y", interval="1d")['Close']

# 2. Save to SQLite database
conn = sqlite3.connect("stock_data.db")
data.to_sql("stock_prices", conn, if_exists="replace", index=True)
conn.close()

# 3. Read back from database
conn = sqlite3.connect("stock_data.db")
df = pd.read_sql("SELECT * FROM stock_prices", conn, parse_dates=["Date"])
conn.close()
df.set_index("Date", inplace=True)

# Function to generate and save charts for different timeframes
def generate_chart(subset_df, filename, title_text):
    plt.figure(figsize=(10, 5))
    plt.plot(subset_df.index, subset_df["AAPL"], label="Apple (AAPL)", color="blue")
    plt.plot(subset_df.index, subset_df["UBSG.SW"], label="UBS Zürich (UBSG.SW)", color="orange")
    plt.title(title_text)
    plt.xlabel("Date")
    plt.ylabel("Closing Price (USD / CHF)")
    plt.legend()
    plt.grid(True)
    plt.savefig(filename)
    plt.close()

# Define timeframes
periods = {
    "chart_1month.png": (df.last("30D"), "1-Week Historical Stock Price Movements"),
    "chart_1month.png": (df.last("30D"), "1-Month Historical Stock Price Movements"),
    "chart_6months.png": (df.last("180D"), "6-Month Historical Stock Price Movements"),
    "chart_1year.png": (df, "1-Year Historical Stock Price Movements")
}

# Generate all charts automatically
for filename, (subset_data, title) in periods.items():
    generate_chart(subset_data, filename, title)
    print(f"Successfully generated: {filename}")

print("\nAll multi-period charts updated successfully!")
