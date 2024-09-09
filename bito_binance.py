from binance.spot import Spot
from binance.um_futures import UMFutures
from bito.client import Client
from bito.time_helper import timestamp_to_string
from loguru import logger
import math
import threading
import requests, json

class BitoBinanceArbitrage(threading.Thread):
    
    def __init__(self):
        
        threading.Thread.__init__(self)
        self.exchange_1_key:                str
        self.exchange_1_secret:             str
        self.bito_email:                    str
        self.exchange_2_key:                str
        self.exchange_2_secret:             str
        self.bito_vip_level:                str
        self.quote:                         str
        self.base:                          str
        self.exchange_1_symbol:             str
        self.exchange_2_symbol:             str
        self.arbitrage_quantity:            float # fixed: contract, percent_of_equity: direction's base balance * amount, percent_of_market_qty: market_contract_qty * amount
        self.arbitrage_quantity_type:       str   # "strategy.fixed", "strategy.percent_of_equity", "strategy.percent_of_market_qty"
        self.arbitrage_ratio:               float
        self.exchange_1_client:             Client
        self.exchange_2_client:             Spot
        self.ex_1_to_ex_2_direction:        bool
        self.ex_2_to_ex_1_direction:        bool
        self.initial_quote_balance:         float
        self.initial_base_balance:          float
        self.exchange_1_quote_balance:      float
        self.exchange_1_base_balance:       float
        self.exchange_2_quote_balance:      float
        self.exchange_2_base_balance:       float
        self.exchange_1_trade_fee:          float
        self.exchange_2_trade_fee:          float
        self.min_arbitrage_ratio:           float
        self.exchange_1_bid:                float
        self.exchange_1_ask:                float
        self.exchange_2_bid:                float
        self.exchange_2_ask:                float
        self.exchange_1_bid_qty:            float
        self.exchange_1_ask_qty:            float
        self.exchange_2_bid_qty:            float
        self.exchange_2_ask_qty:            float
        self.min_order_qty:                 float
        self.min_step_qty:                  float
        self.min_order_decimal:             int
        self.count:                         int
        self.bito_timestamp = 99999
        self.binance_timestamp = 0

    def fetch_current_price(self):
        self.current_price = float(self.exchange_2_client.ticker_price(str.upper(f"{self.quote}{self.base}"))["price"])

    def order_min_limitation(self):
        self.fetch_current_price()
        bito_min_order_qty = float([i for i in requests.get("https://api.bitopro.com/v3/provisioning/limitations-and-fees").json()["orderFeesAndLimitations"] if i["pair"] == f"{self.quote}/{self.base}"][0]["minimumOrderAmount"])
        binance_min_order_qty = float(self.exchange_2_client.exchange_info(f"{self.quote}{self.base}")["symbols"][0]["filters"][2]["minQty"])
        self.min_step_qty = max(bito_min_order_qty, binance_min_order_qty)
        self.min_order_decimal = len(str(self.min_step_qty)) - 2 # 0.0001 -> 0001
        order_multiplier = 15 / (self.min_step_qty * self.current_price)
        self.min_order_qty = round(self.min_step_qty * order_multiplier, self.min_order_decimal)

    def set_initial_capital(self):
        self.initial_quote_balance = self.exchange_1_quote_balance + self.exchange_2_quote_balance
        self.initial_base_balance = self.exchange_1_base_balance + self.exchange_2_base_balance


    def exchange_1_login(self, bito_key: str, bito_secret: str, bito_email: str):
        self.exchange_1_symbol  = f"{str.lower(self.quote)}_{str.lower(self.base)}"      
        self.exchange_1_key     = bito_key
        self.exchange_1_secret  = bito_secret
        self.bito_email         = bito_email
        self.exchange_1_client  = Client(key = bito_key, secret = bito_secret, account = bito_email)

    def exchange_2_login(self, binance_key: str, binance_secret: str):
        self.exchange_2_symbol  = f"{self.quote}{self.base}"
        self.exchange_2_key     = binance_key
        self.exchange_2_secret  = binance_secret
        self.exchange_2_client  = Spot(binance_key, binance_secret)

    def check_balance(self):
        
        self.exchange_1_quote_balance   = float([i for i in self.exchange_1_client.get_private_account_balance()["data"] if i["currency"] == str.lower(self.quote)][0]["available"])
        self.exchange_1_base_balance    = float([i for i in self.exchange_1_client.get_private_account_balance()["data"] if i["currency"] == str.lower(self.base)][0]["available"])
        try:
            self.exchange_2_quote_balance = float([i for i in self.exchange_2_client.user_asset() if i["asset"] == str.upper(self.quote)][0]["free"])
        except:
            self.exchange_2_quote_balance = 0
        try:
            self.exchange_2_base_balance  = float([i for i in self.exchange_2_client.user_asset() if i["asset"] == str.upper(self.base)][0]["free"])
        except:            
            self.exchange_2_base_balance  = 0

        self.ex1_to_ex2_max_qty = min(round(self.exchange_1_base_balance / self.current_price, self.min_order_decimal), round(self.exchange_2_quote_balance, self.min_order_decimal))
        self.ex2_to_ex1_max_qty = min(round(self.exchange_2_base_balance / self.current_price, self.min_order_decimal), round(self.exchange_1_quote_balance, self.min_order_decimal))

        self.ex_1_to_ex_2_direction = True if self.ex1_to_ex2_max_qty * 0.8 > self.min_order_qty else False
        self.ex_2_to_ex_1_direction = True if self.ex2_to_ex1_max_qty * 0.8 > self.min_order_qty else False
        
        if self.ex_1_to_ex_2_direction == True:
            if self.ex_2_to_ex_1_direction == True:
                self.direction == "Both"
                return(self.direction)
            else:
                self.direction = "Buy in BitoPro and Sell in Binance"
                return(self.direction)
        elif self.ex_2_to_ex_1_direction == True:
            self.direction = "Buy in Binance and Sell in BitoPro"
            return(self.direction)
        else:
            return "None"           


    def get_trading_fee(self, bito_vip_level): # BITO USERS NEED TO INPUT THE VIP RANKING
        bito_fee_rule = {"0": 0.002, "1": 0.00194, "2": 0.0015, "3": 0.0014, "4": 0.0013, "5": 0.0012, "6": 0.0011, "market maker": 0}
        self.exchange_1_trade_fee = bito_fee_rule[bito_vip_level]
        self.exchange_2_trade_fee = float([i for i in self.exchange_2_client.trade_fee() if i["symbol"] == f"{self.quote}{self.base}"][0]["takerCommission"])
        self.min_arbitrage_ratio  = self.exchange_1_trade_fee + self.exchange_2_trade_fee


    def on_arbitrage(self, callback_message, callback_exchange):

        if callback_exchange == "BitoPro":
            self.bito_bid           = callback_message[0]
            self.bito_ask           = callback_message[1]
            self.bito_bidsQty       = callback_message[2]
            self.bito_asksQty       = callback_message[3]
            self.bito_timestamp     = callback_message[4]
        if callback_exchange == "Binance":
            self.binance_bid        = callback_message[0]
            self.binance_ask        = callback_message[1]
            self.binance_bidsQty    = callback_message[2]
            self.binance_asksQty    = callback_message[3]
            self.binance_timestamp  = callback_message[4]
        
        if self.bito_timestamp - self.binance_timestamp < 1000:
            if self.ex_1_to_ex_2_direction == True:
                if (self.binance_bid - self.bito_ask) / self.bito_ask > self.arbitrage_ratio: # self.amount should be define in the maintainence session
                    
                    if self.arbitrage_quantity_type == "fixed":
                        if self.bito_asksQty / 2 > self.min_order_qty and self.binance_bidsQty / 2 > self.min_order_qty:
                            trade_log = self.create_order_ex1_to_ex2(quantity = round(min(self.arbitrage_quantity, self.ex1_to_ex2_max_qty * 0.8, self.bito_asksQty / 2, self.binance_bidsQty / 2), self.min_order_decimal))
                            return trade_log
                    
                    if self.arbitrage_quantity_type == "market":
                        if self.bito_asksQty * self.arbitrage_quantity > self.min_order_qty and self.binance_bidsQty * self.arbitrage_quantity > self.min_order_qty:
                            trade_log = self.create_order_ex1_to_ex2(qunatity = round(min(self.ex1_to_ex2_max_qty * 0.8, self.bito_asksQty * self.arbitrage_quantity, self.binance_bidsQty * self.arbitrage_quantity), self.min_order_decimal))
                            return trade_log 
                    
                    if self.arbitrage_quantity_type == "equity":
                        if self.bito_asksQty / 2 > self.min_order_qty and self.binance_bidsQty / 2 > self.min_order_qty:
                            trade_log  == self.create_order_ex1_to_ex2(quantity = round(min(self.ex1_to_ex2_max_qty * self.arbitrage_quantity, self.bito_asksQty / 2, self.binance_bidsQty / 2), self.min_order_decimal))                       
                            return trade_log

            elif self.ex_2_to_ex_1_direction == False:
                if (self.bito_bid - self.binance_ask) / self.binance_ask >  self.arbitrage_ratio:
                    
                    if self.arbitrage_quantity_type == "fixed":
                        if self.binance_asksQty > self.min_order_qty / 2 and self.bito_bidsQty > self.min_order_qty / 2:
                            trade_log = self.create_order_ex2_to_ex1(quantity = round(min(self.arbitrage_quantity, self.ex2_to_ex1_max_qty * 0.8, self.binance_asksQty / 2, self.bito_bidsQty / 2), self.min_order_decimal))
                            return trade_log
                    if self.arbitrage_quantity_type == "market":
                        if self.binance_asksQty * self.arbitrage_quantity > self.min_order_qty and self.binance_bidsQty * self.arbitrage_quantity > self.min_order_qty:
                            trade_log = self.create_order_ex2_to_ex1(qunatity = round(min(self.ex2_to_ex1_max_qty * 0.8, self.bito_bidsQty * self.arbitrage_quantity, self.binance_asksQty * self.arbitrage_quantity), self.min_order_decimal))
                            return trade_log 
                    if self.arbitrage_quantity_type == "equity":
                        if self.binance_asksQty / 2 > self.min_order_qty and self.bito_bidsQty / 2 > self.min_order_qty: 
                            trade_log  == self.create_order_ex2_to_ex1(quantity = round(min(self.ex2_to_ex1_max_qty * self.arbitrage_quantity, self.bito_bidsQty / 2, self.binance_asksQty / 2), self.min_order_decimal))                       
                            return trade_log

        ex1_to_ex2_bar_height = ((self.binance_bid - self.bito_ask) / self.bito_ask) * 1000
        ex1_to_ex2_bar_color = True if ex1_to_ex2_bar_height > 0 else False
        ex2_to_ex1_bar_height = ((self.bito_bid - self.binance_ask) / self.binance_ask) * 1000
        ex2_to_ex1_bar_color = True if ex2_to_ex1_bar_height > 0 else False
        return (ex1_to_ex2_bar_height, ex1_to_ex2_bar_color, ex2_to_ex1_bar_height, ex2_to_ex1_bar_color)

    def create_order_ex1_to_ex2(self, quantity: float):
        bito_respond    = self.exchange_1_client.set_private_create_order(
                            pair = self.exchange_1_symbol, 
                            action = "BUY", 
                            amount = quantity, 
                            price = self.current_price * 1.2, 
                            _type = "LIMIT", 
                        )
        binance_respond = self.exchange_2_client.new_order(
                            symbol = self.exchange_2_symbol, 
                            side = "SELL", 
                            quantity = quantity, 
                            type = "MARKET", 
                        )
        
        bito_orderid = bito_respond["orderId"]
        bito_order_data = self.exchange_1_client.get_private_order_data(self.exchange_1_symbol, bito_orderid) 
        bito_fill_time = bito_order_data["createdTimestamp"]
        bito_fill_action = bito_order_data["action"]
        bito_fill_price = float(bito_order_data["avgExecutionPrice"])
        bito_fill_amount = float(bito_order_data["executedAmount"])
        bito_fill_commission = bito_order_data["fee"]
        bito_fill_commission_symbol = bito_order_data["feeSymbol"]

        binance_fill_time = binance_respond["transactTime"]
        binance_fill_action = binance_respond["side"]
        binance_fill_price = float([i for i in binance_respond["fills"]][0]["price"])
        binance_fill_amount = float([i for i in binance_respond["fills"]][0]["qty"])
        binance_fill_commission = [i for i in binance_respond["fills"]][0]["commission"]
        binance_fill_commission_symbol = [i for i in binance_respond["fills"]][0]["commissionAsset"]

        order_profit = binance_fill_price * binance_fill_amount - bito_fill_price * bito_fill_amount
        self.count += 1
        return (
            (timestamp_to_string(bito_fill_time), "BitoPro", bito_fill_action, bito_fill_price, bito_fill_amount, bito_fill_commission, bito_fill_commission_symbol), 
            (timestamp_to_string(binance_fill_time), "Binance", binance_fill_action, binance_fill_price, binance_fill_amount, binance_fill_commission, binance_fill_commission_symbol), 
            (order_profit)
        )

    
    def create_order_ex2_to_ex1(self, quantity: float):
        binance_respond   = self.exchange_2_client.new_order(
                            symbol = self.exchange_2_symbol, 
                            side = "BUY", 
                            quantity = quantity, 
                            type = "MARKET"
                            )
        bito_respond      = self.exchange_1_client.set_private_create_order(
                            pair = self.exchange_1_symbol, 
                            aciton = "SELL", 
                            amount = quantity, 
                            _type = "MARKET", 
                            price = self.current_price * 0.8
                            )

        bito_orderid = bito_respond["orderId"]
        bito_order_data = self.exchange_1_client.get_private_order_data(self.exchange_1_symbol, bito_orderid) 
        bito_fill_time = bito_order_data["createdTimestamp"]
        bito_fill_action = bito_order_data["action"]
        bito_fill_price = float(bito_order_data["avgExecutionPrice"])
        bito_fill_amount = float(bito_order_data["executedAmount"])
        bito_fill_commission = bito_order_data["fee"]
        bito_fill_commission_symbol = bito_order_data["feeSymbol"]

        binance_fill_time = binance_respond["transactTime"]
        binance_fill_action = binance_respond["side"]
        binance_fill_price = float([i for i in binance_respond["fills"]][0]["price"])
        binance_fill_amount = float([i for i in binance_respond["fills"]][0]["qty"])
        binance_fill_commission = [i for i in binance_respond["fills"]][0]["commission"]
        binance_fill_commission_symbol = [i for i in binance_respond["fills"]][0]["commissionAsset"]

        order_profit = bito_fill_price * bito_fill_amount - binance_fill_price * binance_fill_amount
        self.count += 1
        return (
            (timestamp_to_string(bito_fill_time), "BitoPro", bito_fill_action, bito_fill_price, bito_fill_amount, bito_fill_commission, bito_fill_commission_symbol), 
            (timestamp_to_string(binance_fill_time), "Binance", binance_fill_action, binance_fill_price, binance_fill_amount, binance_fill_commission, binance_fill_commission_symbol), 
            (order_profit)
        )

if __name__ == "__main__":
    
    a = BitoBinanceArbitrage()
    a.quote = "BCH"
    a.base = "USDT"
    a.exchange_2_client = Spot()
    a.order_min_limitation()