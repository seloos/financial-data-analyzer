import sqlite3
import pandas as pd
import yfinance as yf

# 1. Hisseleri çekelim
tickers = ["UBSG.SW", "AAPL"]
data = yf.download(tickers, period="1y", interval="1d")['Close']

# 2. SQLite veritabanına kaydedelim
conn = sqlite3.connect("stock_data.db")
data.to_sql("stock_prices", conn, if_exists="replace", index=True)
conn.close()

# 3. Veritabanından veriyi tekrar okuyup Pandas ile Finansal Hesaplama (Getiri Oranı) yapalım
conn = sqlite3.connect("stock_data.db")
df = pd.read_sql("SELECT * FROM stock_prices", conn, parse_dates=["Date"])
conn.close()

# Tarih sütununu index yapalım
df.set_index("Date", inplace=True)

# Günlük yüzdesel getirileri (Daily Returns) hesaplayalım
returns = df.pct_change() * 100

print("\n--- Son 5 Günlük Yüzdesel Getiriler (%) ---")
print(returns.tail(5))

# Getirileri de ayrı bir SQL tablosuna kaydedelim
conn = sqlite3.connect("stock_data.db")
returns.to_sql("stock_returns", conn, if_exists="replace", index=True)
conn.close()

print("\nBaşarılı! Getiri hesaplamaları da veritabanına eklendi.")





