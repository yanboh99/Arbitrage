from bito.client import Client
from bito.time_helper import timestamp_to_string
from client_utils.okx_utils import Okx
from loguru import logger
import math
import threading
import requests, json
import asyncio
import time

asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

class BitoOkxArbitrage(threading.Thread):
    
    def __init__(self):
        
        threading.Thread.__init__(self)
        self.exchange_1_key:                str
        self.exchange_1_secret:             str
        self.exchange_2_key:                str
        self.exchange_2_secret:             str
        self.bito_email:                    str
        self.bito_vip_level:                str
        self.quote:                         str
        self.base:                          str
        self.exchange_1_symbol:             str
        self.okx_symbol:                    str
        self.arbitrage_quantity:            float # fixed: contract, percent_of_equity: direction's base balance * amount, percent_of_market_qty: market_contract_qty * amount
        self.arbitrage_quantity_type:       str   # "strategy.fixed", "strategy.percent_of_equity", "strategy.percent_of_market_qty"
        self.arbitrage_ratio:               float
        self.exchange_1_client:             Client
        self.exchange_2_client:             Okx
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
        self.okx_timestamp = 0

    def fetch_current_price(self):
        self.current_price = float(requests.get(f"https://www.okx.com/api/v5/market/tickers?instType=SWAP&uly={self.exchange_2_symbol}").json()["data"][0]["last"])
        self.bito_order_used_buy = round(self.current_price * 1.2, (len(str(self.current_price)) - str(self.current_price).find(".") - 1))
        self.bito_order_used_sell = round(self.current_price * 0.8, (len(str(self.current_price)) - str(self.current_price).find(".") - 1))

    def order_min_limitation(self):
        self.fetch_current_price()
        bito_min_order_qty = float([i for i in requests.get("https://api.bitopro.com/v3/provisioning/limitations-and-fees").json()["orderFeesAndLimitations"] if i["pair"] == f"{self.quote}/{self.base}"][0]["minimumOrderAmount"])
        okx_min_order_qty = float(requests.get(f"https://www.okx.com/api/v5/public/instruments?instType=SPOT&instId={self.quote}-{self.base}").json()["data"][0]["minSz"])
        self.min_step_qty = max(bito_min_order_qty, okx_min_order_qty)
        self.min_order_decimal = len(str(self.min_step_qty)) - 2 # 0.0001 -> 0001
        self.min_order_qty = self.min_step_qty

    def set_initial_capital(self):
        self.initial_quote_balance = self.exchange_1_quote_balance + self.exchange_2_quote_balance
        self.initial_base_balance = self.exchange_1_base_balance + self.exchange_2_base_balance
        self.count = 0

    def exchange_1_login(self, bito_key: str, bito_secret: str, bito_email: str):
        self.exchange_1_symbol  = f"{str.lower(self.quote)}_{str.lower(self.base)}"
        self.exchange_1_key     = bito_key
        self.exchange_1_secret  = bito_secret
        self.bito_email         = bito_email
        self.exchange_1_client  = Client(key = bito_key, secret = bito_secret, account = bito_email)

    def exchange_2_login(self, okx_key: str, okx_secret: str, okx_passphrase: str):
        self.exchange_2_symbol  = f"{self.quote}-{self.base}"
        self.exchange_2_secret  = okx_secret
        self.exchange_2_passphrase = okx_passphrase
        self.exchange_2_client  = Okx(okx_key, okx_secret, okx_passphrase)


    def check_balance(self):
        
        self.exchange_1_quote_balance   = float([i for i in self.exchange_1_client.get_private_account_balance()["data"] if i["currency"] == str.lower(self.quote)][0]["available"])
        self.exchange_1_base_balance    = float([i for i in self.exchange_1_client.get_private_account_balance()["data"] if i["currency"] == str.lower(self.base)][0]["available"])
        try:
            balance_data_quote            = asyncio.run(self.exchange_2_client.get_account_balance())["data"]
        except KeyError:
            return "login error"
        try:
            self.exchange_2_quote_balance = float([i for i in balance_data_quote[0]["details"] if i["ccy"] == f"{self.quote}"][0]["availBal"])
        except IndexError:
            self.exchange_2_quote_balance = 0
        try:
            balance_data_base             = asyncio.run(self.exchange_2_client.get_account_balance())["data"]
        except KeyError:
            return "login error"
        try:
            self.exchange_2_base_balance  = float([i for i in balance_data_base[0]["details"] if i["ccy"] == f"{self.base}"][0]["availBal"])
        except IndexError: 
            self.exchange_2_base_balance  = 0

        self.ex1_to_ex2_max_qty = min(round(self.exchange_1_base_balance / self.current_price, self.min_order_decimal), round(self.exchange_2_quote_balance, self.min_order_decimal))
        self.ex2_to_ex1_max_qty = min(round(self.exchange_2_base_balance / self.current_price, self.min_order_decimal), round(self.exchange_1_quote_balance, self.min_order_decimal))

        self.ex_1_to_ex_2_direction = True if self.ex1_to_ex2_max_qty * 0.8 > self.min_order_qty else False
        self.ex_2_to_ex_1_direction = True if self.ex2_to_ex1_max_qty * 0.8 > self.min_order_qty else False
        
        if self.ex_1_to_ex_2_direction == True:
            if self.ex_2_to_ex_1_direction == True:
                self.direction = "Both"
                return(self.direction)
            else:
                self.direction = "Buy in BitoPro and Sell in OKX"
                return(self.direction)
        elif self.ex_2_to_ex_1_direction == True:
            self.direction = "Buy in OKX and Sell in BitoPro"
            return(self.direction)
        else:
            return "error"           


    def get_trading_fee(self, bito_vip_level): # BITO USERS NEED TO INPUT THE VIP RANKING
        bito_fee_rule = {"0": 0.002, "1": 0.00194, "2": 0.0015, "3": 0.0014, "4": 0.0013, "5": 0.0012, "6": 0.0011, "market maker": 0}
        self.exchange_1_trade_fee = bito_fee_rule[bito_vip_level]
        self.exchange_2_trade_fee = math.fabs(float(asyncio.run(self.exchange_2_client.get_trade_fee("SPOT", "BTC-USDT"))["data"][0]["taker"]))
        self.min_arbitrage_ratio  = self.exchange_1_trade_fee + self.exchange_2_trade_fee


    def on_arbitrage(self, callback_message, callback_exchange):

        if callback_exchange == "BitoPro":
            self.bito_bid           = callback_message[0]
            self.bito_ask           = callback_message[1]
            self.bito_bidsQty       = callback_message[2]
            self.bito_asksQty       = callback_message[3]
            self.bito_timestamp     = callback_message[4]
        if callback_exchange == "OKX":
            self.okx_bid        = callback_message[0]
            self.okx_ask        = callback_message[1]
            self.okx_bidsQty    = callback_message[2]
            self.okx_asksQty    = callback_message[3]
            self.okx_timestamp  = callback_message[4]
        
        if self.bito_timestamp - self.okx_timestamp < 1:
            if self.ex_1_to_ex_2_direction == True:
                if (self.okx_bid - self.bito_ask) / self.bito_ask > self.arbitrage_ratio: # self.amount should be define in the maintainence session
                    
                    if self.arbitrage_quantity_type == "fixed":
                        if self.bito_asksQty / 2 > self.min_order_qty and self.okx_bidsQty / 2 > self.min_order_qty:
                            trade_log = self.create_order_ex1_to_ex2(quantity = min(self.arbitrage_quantity, self.ex1_to_ex2_max_qty * 0.8, self.bito_asksQty / 2, self.okx_bidsQty / 2))
                            return trade_log
                    
                    if self.arbitrage_quantity_type == "market":
                        if self.bito_asksQty * self.arbitrage_quantity > self.min_order_qty and self.okx_bidsQty * self.arbitrage_quantity > self.min_order_qty:
                            trade_log = self.create_order_ex1_to_ex2(qunatity = min(self.ex1_to_ex2_max_qty * 0.8, self.bito_asksQty * self.arbitrage_quantity, self.okx_bidsQty * self.arbitrage_quantity))
                            return trade_log 
                    
                    if self.arbitrage_quantity_type == "equity":
                        if self.bito_asksQty / 2 > self.min_order_qty and self.okx_bidsQty / 2 > self.min_order_qty:
                            trade_log  == self.create_order_ex1_to_ex2(quantity = min(self.ex1_to_ex2_max_qty * self.arbitrage_quantity, self.bito_asksQty / 2, self.okx_bidsQty / 2))                       
                            return trade_log

            elif self.ex_2_to_ex_1_direction == False:
                if (self.bito_bid - self.okx_ask) / self.okx_ask >  self.arbitrage_ratio:
                    
                    if self.arbitrage_quantity_type == "fixed":
                        if self.okx_asksQty > self.min_order_qty / 2 and self.bito_bidsQty > self.min_order_qty / 2:
                            trade_log = self.create_order_ex2_to_ex1(quantity = min(self.arbitrage_quantity, self.ex2_to_ex1_max_qty * 0.8, self.okx_asksQty / 2, self.bito_bidsQty / 2))
                            return trade_log
                    if self.arbitrage_quantity_type == "market":
                        if self.okx_asksQty * self.arbitrage_quantity > self.min_order_qty and self.okx_bidsQty * self.arbitrage_quantity > self.min_order_qty:
                            trade_log = self.create_order_ex2_to_ex1(qunatity = min(self.ex2_to_ex1_max_qty * 0.8, self.bito_bidsQty * self.arbitrage_quantity, self.okx_asksQty * self.arbitrage_quantity))
                            return trade_log 
                    if self.arbitrage_quantity_type == "equity":
                        if self.okx_asksQty / 2 > self.min_order_qty and self.bito_bidsQty / 2 > self.min_order_qty: 
                            trade_log  == self.create_order_ex2_to_ex1(quantity = min(self.ex2_to_ex1_max_qty * self.arbitrage_quantity, self.bito_bidsQty / 2, self.okx_asksQty / 2))                       
                            return trade_log

        ex1_to_ex2_bar_height = ((self.okx_bid - self.bito_ask) / self.bito_ask) * 1000
        ex1_to_ex2_bar_color = True if ex1_to_ex2_bar_height > 0 else False
        ex2_to_ex1_bar_height = ((self.bito_bid - self.okx_ask) / self.okx_ask) * 1000
        ex2_to_ex1_bar_color = True if ex2_to_ex1_bar_height > 0 else False
        return (ex1_to_ex2_bar_height, ex1_to_ex2_bar_color, ex2_to_ex1_bar_height, ex2_to_ex1_bar_color)

    def create_order_ex1_to_ex2(self, quantity: float):
        bito_respond    = self.exchange_1_client.set_private_create_order(
                            pair = self.exchange_1_symbol, 
                            action = "BUY", 
                            amount = quantity, 
                            price = self.bito_order_used_buy, 
                            _type = "LIMIT", 
                        )
        okx_respond     = asyncio.run(self.exchange_2_client.place_an_order(
                            inst_id = self.okx_symbol, 
                            side = "SELL", 
                            size = quantity, 
                            type_ = "market", 
                        ))
        
        
        time.sleep(0.5)
        bito_orderid = bito_respond["orderId"]
        bito_order_data = self.exchange_1_client.get_private_order_data(self.exchange_1_symbol, bito_orderid) 
        bito_fill_time = bito_order_data["createdTimestamp"]
        bito_fill_action = bito_order_data["action"]
        bito_fill_price = float(bito_order_data["avgExecutionPrice"])
        bito_fill_amount = float(bito_order_data["executedAmount"])
        bito_fill_commission = bito_order_data["fee"]
        bito_fill_commission_symbol = bito_order_data["feeSymbol"]

        okx_order_id = okx_respond["data"][0]["ordId"]
        okx_order_data = asyncio.run(self.exchange_2_client.get_an_order(f"{self.quote}-{self.base}", okx_order_id))
        okx_fill_time = okx_order_data["data"][0]["fillTime"]
        okx_fill_action = okx_order_data["data"][0]["side"]
        okx_fill_price = float(okx_order_data["data"][0]["fillPx"])
        okx_fill_amount = float(okx_order_data["data"][0]["fillSz"])
        okx_fill_commission = math.fabs(float(okx_order_data["data"][0]["fee"]))
        okx_fill_commission_symbol = okx_order_data["data"][0]["feeCcy"]

        order_profit = okx_fill_price * okx_fill_amount - bito_fill_price * bito_fill_amount
        self.count += 1
        return (
            (timestamp_to_string(bito_fill_time), "BitoPro", bito_fill_action, bito_fill_price, bito_fill_amount, bito_fill_commission, bito_fill_commission_symbol), 
            (timestamp_to_string(okx_fill_time), "OKX", okx_fill_action, okx_fill_price, okx_fill_amount, okx_fill_commission, okx_fill_commission_symbol), 
            (order_profit)
        )

    
    def create_order_ex2_to_ex1(self, quantity: float):
        okx_respond   = self.exchange_2_client.place_an_order(
                            inst_id = self.okx_symbol,
                            side = "BUY", 
                            size = quantity, 
                            type_ = "MARKET"
                            )
        bito_respond      = self.exchange_1_client.set_private_create_order(
                            pair = self.exchange_1_symbol, 
                            aciton = "SELL", 
                            amount = quantity, 
                            _type = "market", 
                            price = self.bito_order_used_sell
                            )

        time.sleep(0.5)
        bito_orderid = bito_respond["orderId"]
        bito_order_data = self.exchange_1_client.get_private_order_data(self.exchange_1_symbol, bito_orderid) 
        bito_fill_time = bito_order_data["createdTimestamp"]
        bito_fill_action = bito_order_data["action"]
        bito_fill_price = float(bito_order_data["avgExecutionPrice"])
        bito_fill_amount = float(bito_order_data["executedAmount"])
        bito_fill_commission = bito_order_data["fee"]
        bito_fill_commission_symbol = bito_order_data["feeSymbol"]

        okx_order_id = okx_respond["data"][0]["ordId"]
        okx_order_data = asyncio.run(self.exchange_2_client.get_an_order(f"{self.quote}-{self.base}", okx_order_id))
        okx_fill_time = okx_order_data["data"][0]["fillTime"]
        okx_fill_action = okx_order_data["data"][0]["side"]
        okx_fill_price = float(okx_order_data["data"][0]["fillPx"])
        okx_fill_amount = float(okx_order_data["data"][0]["fillSz"])
        okx_fill_commission = math.fabs(float(okx_order_data["data"][0]["fee"]))
        okx_fill_commission_symbol = okx_order_data["data"][0]["feeCcy"]

        order_profit = bito_fill_price * bito_fill_amount - okx_fill_price * okx_fill_amount
        self.count += 1
        return (
            (timestamp_to_string(bito_fill_time), "BitoPro", bito_fill_action, bito_fill_price, bito_fill_amount, bito_fill_commission, bito_fill_commission_symbol), 
            (timestamp_to_string(okx_fill_time), "OKX", okx_fill_action, okx_fill_price, okx_fill_amount, okx_fill_commission, okx_fill_commission_symbol), 
            (order_profit)
        )
