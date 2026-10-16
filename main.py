import sqlite3
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt

# 1. Hisseleri çekelim
tickers = ["UBSG.SW", "AAPL"]
print("Güncel borsa verileri indiriliyor...")
data = yf.download(tickers, period="1y", interval="1d")['Close']

# 2. SQLite veritabanına kaydedelim
conn = sqlite3.connect("stock_data.db")
data.to_sql("stock_prices", conn, if_exists="replace", index=True)
conn.close()

# 3. Veritabanından veriyi okuyup Getiri ve Volatilite hesaplayalım
conn = sqlite3.connect("stock_data.db")
df = pd.read_sql("SELECT * FROM stock_prices", conn, parse_dates=["Date"])
conn.close()

df.set_index("Date", inplace=True)

# Günlük getiriler (%)
returns = df.pct_change() * 100

print("\n--- Son 5 Günlük Yüzdesel Getiriler (%) ---")
print(returns.tail(5))

# 4. Yıllıklandırılmış Volatilite (Risk) Hesaplama Mantığı
# (Günlük standart sapmanın kök 252 ile çarpılmış hali - finansta standart formüldür)
annualized_volatility = returns.std() * (252 ** 0.5)

print("\n--- Yıllıklandırılmış Volatilite (Risk/Oynaklık %) ---")
print(annualized_volatility)

# 5. Grafik Çizdirme Ekleyelim
print("\nFiyat grafiği çizdiriliyor...")
plt.figure(figsize=(10, 5))
plt.plot(df.index, df["AAPL"], label="Apple (AAPL)", color="blue")
plt.plot(df.index, df["UBSG.SW"], label="UBS Zürich (UBSG.SW)", color="orange")
plt.title("Son 1 Yıllık Hisse Senedi Fiyat Hareketleri")
plt.xlabel("Tarih")
plt.ylabel("Kapanış Fiyatı (USD / CHF)")
plt.legend()
plt.grid(True)

# Grafiği dosya olarak kaydedelim
plt.savefig("stock_chart.png")
print("Grafik başarıyla 'stock_chart.png' olarak kaydedildi!")

# (Not: Eğer MacBook'un ekranında grafik pencerisinin anında açılmasını istersen plt.show() ekleyebiliriz)
