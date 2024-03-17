import pandas as pd
import numpy as np
import requests
import time
import Constants as CONST
import hashlib
import hmac
import datetime
import csv


class BinanceAccount:
    
    def __init__(self, symbol='BNBUSDT', interval='1m'):
        self.symbol = symbol
        self.base_url = 'https://api.binance.com/api/v3'
        self.df = pd.DataFrame()
        self.current_data = pd.DataFrame(columns=['timestamp', 'price'])
        self.interval = interval
        
    def place_order(self, side, quantity, order_type='MARKET'):
        # Simulate placing an order with Binance API
        #quantity = round(quantity, 2)
        quantity = int(quantity * 1000) / 1000  # Round down to 2 decimal places Need to make sure there are funds .. dont want a round up
        
        endpoint = '/order'
        params = {
            'symbol': self.symbol,
            'side': side,
            'type': order_type,
            'quantity': quantity,
            'timestamp': int(time.time() * 1000)
        }
        
        print(quantity)
        
        query_string = '&'.join([f"{key}={params[key]}" for key in sorted(params)])
        signature = hmac.new(CONST.B_sKEY.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

        headers = {'X-MBX-APIKEY': CONST.B_KEY}
        
        query_string += f'&signature={signature}'

        response = requests.post(f"{self.base_url}{endpoint}?{query_string}", headers=headers)        
        
        price = response.json()['fills'][0]['price']
        quant = response.json()['fills'][0]['qty']
        
        print(f"ORDER: {side}, Price: {price}, Qty: {quant}")
        
        return response.json()
    
    def place_buy_order_usdt(self, usdt_quantity):
        # Get the current market price (replace 'BNBUSDT' with the actual symbol you are trading)
        ticker_endpoint = '/ticker/price'
        ticker_params = {'symbol': self.symbol}
        ticker_response = requests.get(f"{self.base_url}{ticker_endpoint}", params=ticker_params)
        current_price = float(ticker_response.json()['price'])

        # Calculate the quantity in the base asset (e.g., BNB)
        base_asset_quantity = usdt_quantity / current_price

        # Place a buy order using a signed request with the calculated quantity
        return self.place_order('BUY', base_asset_quantity)
        
    def get_account_balances(self):
        # Retrieve account information including balances
        endpoint = '/account'
        params = {'timestamp': int(time.time() * 1000)}

        # Generate the signature
        query_string = '&'.join([f"{key}={params[key]}" for key in sorted(params)])
        signature = hmac.new(CONST.B_sKEY.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

        # Include both API key and signature in the headers
        headers = {'X-MBX-APIKEY': CONST.B_KEY}

        # Include the signature in the query string
        query_string += f'&signature={signature}'

        # Send the signed request to get account information
        response = requests.get(f"{self.base_url}{endpoint}?{query_string}", headers=headers)
        account_info = response.json()

        self.bnb_balance = float(next(filter(lambda x: x['asset'] == 'BNB', account_info['balances']))['free'])
        self.usdt_balance = float(next(filter(lambda x: x['asset'] == 'USDT', account_info['balances']))['free'])
        
        # Extract balances for specific assets (e.g., BNB and USDT)
        balances = {}
        for balance in account_info['balances']:
            asset = balance['asset']
            free_balance = float(balance['free'])
            balances[asset] = free_balance

        return balances
    
    def fetch_historical_data(self, limit=500):
        endpoint = '/klines'
        params = {'symbol': self.symbol, 'interval': self.interval, 'limit': limit}
        response = requests.get(f"{self.base_url}{endpoint}", params=params)
        data = response.json()

        # Create a DataFrame from the fetched data
        columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume',
                   'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore']
        df_new = pd.DataFrame(data, columns=columns)
        df_new['timestamp'] = pd.to_datetime(df_new['timestamp'], unit='ms')

        # Concatenate new data with existing data
        self.df = pd.concat([self.df, df_new], ignore_index=True)
        
    def calculate_moving_averages(self):
        # Calculate moving averages
        self.current_data['MA_7'] = self.current_data['price'].rolling(window=7).mean()
        self.current_data['MA_25'] = self.current_data['price'].rolling(window=25).mean() # RA for 7 1m
        self.current_data['MA_50'] = self.current_data['price'].rolling(window=50).mean()
        self.current_data['MA_75'] = self.current_data['price'].rolling(window=75).mean()
        self.current_data['MA_99'] = self.current_data['price'].rolling(window=99).mean()
        self.current_data['MA_200'] = self.current_data['price'].rolling(window=200).mean() ## RA 50 for 1m
        
    def get_lot_size_constraints(self):
        endpoint = '/exchangeInfo'
        response = requests.get(f"{self.base_url}{endpoint}")
        exchange_info = response.json()

        for symbol_info in exchange_info['symbols']:
            if symbol_info['symbol'] == self.symbol:
                for filter in symbol_info['filters']:
                    if filter['filterType'] == 'LOT_SIZE':
                        min_qty = float(filter['minQty'])
                        max_qty = float(filter['maxQty'])
                        return min_qty, max_qty
                    
    def get_min_notional(self):
        endpoint = '/exchangeInfo'
        response = requests.get(f"{self.base_url}{endpoint}")
        data = response.json()

        for symbol_info in data.get('symbols', []):
            if symbol_info['symbol'] == self.symbol:
                for filter in symbol_info['filters']:
                    if filter['filterType'] == 'NOTIONAL':
                        return float(filter.get('minNotional', 0.0))
                    
    def get_current_price(self):
        endpoint = f'/ticker/price?symbol={self.symbol}'
        response = requests.get(f"{self.base_url}{endpoint}")
        data = response.json()
        return float(data['price']) if 'price' in data else None
    
    def update_data(self):
        current_time = pd.Timestamp.now()
        current_price = self.get_current_price()
        print(f"Current Price: {current_price}")
        if current_price is not None:
            new_row = {'timestamp': current_time, 'price': current_price}
            self.current_data = pd.concat([self.current_data, pd.DataFrame([new_row])], ignore_index=True)
            #self.current_data = self.current_data.append(new_row, ignore_index=True)
        else:
            print(f"Failed to fetch current price for {self.symbol}")
            
    def saveData(self, filename):
        self.current_data.to_csv(filename, index=False)

bin_Acc = BinanceAccount()
        
while True:
    
    bin_Acc.update_data()
    bin_Acc.calculate_moving_averages()
    bin_Acc.saveData("real_data_15s.csv")
    
    time.sleep(15)