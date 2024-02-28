import requests
import pandas as pd
import matplotlib.pyplot as plt

api_url = "https://api.binance.com/api/v3/klines"

symbol = 'BNBUSDT'
interval = '1d'

params = {
    'symbol': symbol,
    'interval': interval,
    'limit': 1000 
}

response = requests.get(api_url, params=params)
klines = response.json()

df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])

# Convert timestamps to datetime format
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

# Keep only relevant columns
df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]

# Save or use the DataFrame for further analysis
df.to_csv('bnb_price_data.csv', index=False)

plt.figure(figsize=(12, 6))
plt.plot(df['timestamp'], df['close'], label='Close Price', color='blue')
plt.title(f'Historical Price Data for {symbol}')
plt.xlabel('Timestamp')
plt.ylabel('Close Price (USDT)')
plt.legend()
plt.grid(True)
plt.show()