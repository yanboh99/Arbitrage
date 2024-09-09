from bito.time_helper import timestamp_to_string
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
import pandas as pd
import threading
import websocket
import json
from loguru import logger
from line_notify import LineNotify
import time
import os
import sys
from bito_binance import BitoBinanceArbitrage
from bito_okx import BitoOkxArbitrage
import math


pd.set_option("display.max_rows", 2000)
df = pd.DataFrame(columns=["time", "bid", "ask"])



def clear(obj: tk.Tk):
    for widget in obj.winfo_children():
        widget.destroy()


def loading():
    pass


class Window():

    def __init__(self):

        #
        self.quote: str
        self.base: str
        self.exchange_1: str
        self.exchange_2: str

        #
        self.root = tk.Tk()
        self.root.title("Cross Exchange Arbitrage")
        self.root.geometry("600x600")
        self.root.configure(bg="#0A1A33")
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(self.root, fieldbackground= "#0A1A33", background= "#5A71AB", selectbackground = "#5A71AB")
        self.root.option_add("*TCombobox*Listbox*Background", "#9EB9FF")
        
        
        #
        self.api_key_1:                 str
        self.secret_key_1:              str
        self.api_key_2:                 str
        self.secret_key_2:              str
        self.bito_email:                str
        self.okx_passphrase:            str
        self.ex_1_datastream:           DataStream
        self.ex_2_datastream:           DataStream
        self.bito_vip_level:            str
        self.arbitrage_bot:             object
        self.exchange_1_time_label:     tk.Label
        self.exchange_1_bid_label:      tk.Label
        self.exchange_1_ask_label:      tk.Label
        self.exchange_1_bid_qty_label:  tk.Label
        self.exchange_1_ask_qty_label:  tk.Label
        self.exchange_2_time_label:     tk.Label
        self.exchange_2_bid_label:      tk.Label
        self.exchange_2_ask_label:      tk.Label
        self.exchange_2_bid_qty_label:  tk.Label
        self.exchange_2_ask_qty_label:  tk.Label
        self.status_bar_ex1_to_ex2:     tk.Label
        self.status_bar_ex2_to_ex1:     tk.Label
        self.ex1_quote_balance_label:   tk.Label
        self.ex1_base_balance_label:    tk.Label
        self.ex2_quote_balance_label:   tk.Label
        self.ex2_base_balance_label:    tk.Label
        self.quote_profit_label:        tk.Label
        self.base_profit_label:         tk.Label
        self.count_label:               tk.Label
        self.connection:                bool
        self.lock = threading.Lock()


        self.input_exchange()

############################################################################################################################################################################

    def input_exchange(self):

        def check_exchange():

            self.exchange_1 = exchangeMenu_1.get()
            self.exchange_2 = exchangeMenu_2.get()
            self.quote      = coinMenu_1.get()
            self.base       = coinMenu_2.get()

            for i in range(1):

                if self.exchange_1 == "" or self.exchange_2 == "" or self.quote == "" or self.base == "":
                    messagebox.showerror("Error", "please fill the blank field")
                    self.input_exchange()
                    break

                if self.exchange_1 == self.exchange_2:
                    messagebox.showerror("Error", "exchange1 cannot be the same as exchange2")
                    self.input_exchange()
                    break

                if self.base == self.quote:
                    messagebox.showerror("Error", "quote token and base token can't be the same")
                    self.input_exchange()
                    break

                if self.base == "ETH" and self.quote != "BTC":
                    messagebox.showerror("Error", f"the trading pair {self.quote}/{self.base} doesn't exist")
                    self.input_exchange()
                    break

                if (self.exchange_1 == "BitoPro" and self.exchange_2 == "Binance") or (self.exchange_1 == "Binance" and self.exchange_2 == "BitoPro"):
                    self.arbitrage_bot = BitoBinanceArbitrage()
                    self.exchange_1 = "BitoPro"
                    self.exchange_2 = "Binance"

                if (self.exchange_1 == "BitoPro" and self.exchange_2 == "OKX") or (self.exchange_1 == "Binance" and self.exchange_2 == "OKX"):
                    self.arbitrage_bot = BitoOkxArbitrage()
                    self.exchange_1 = "BitoPro"
                    self.exchange_2 = "OKX"

                self.arbitrage_bot.quote = self.quote
                self.arbitrage_bot.base = self.base
                self.input_key_secret()

        # --------------------------- input exchanges and coin --------------------------- 
        clear(self.root)
        frame = tk.Frame()
        frame.place(relx = 0.5, rely = 0.5, anchor = tk.CENTER)
        tk.Label(frame, text = "Choose Arbitrage Exchanges 1", font = ("Arial 18")).grid(row = 0, column = 0)
        tk.Label(frame, text = "Choose Arbitrage Exchanges 2", font = ("Arial 18")).grid(row = 2, column = 0)
        tk.Label(frame, text = "Choose Arbitrage Quote Coin",  font = ("Arial 18")).grid(row = 4, column = 0)
        tk.Label(frame, text = "Choose Arbitrage Base Coin",   font = ("Arial 18")).grid(row = 6, column = 0)
        exchangeMenu_1 = ttk.Combobox(frame,
                                      values = ["BitoPro", "Binance", "OKX", "Bybit"], 
                                      width = 20, font = ("Arial 18"))
        exchangeMenu_1.grid(row = 1, column = 0)
        exchangeMenu_2 = ttk.Combobox(frame, 
                                      values = ["BitoPro", "Binance", "OKX", "Bybit"], 
                                      width = 20, font = ("Arial 18"))
        exchangeMenu_2.grid(row = 3, column = 0)
        coinMenu_1     = ttk.Combobox(frame,
                                      values = ["BTC", "ETH", "ADA", "BCH", "LTC", "SOL"], 
                                      width = 20, font = ("Arial 18"))
        coinMenu_1.grid(row = 5, column = 0)
        coinMenu_2     = ttk.Combobox(frame, 
                                      values=["USDT", "ETH"],
                                      width = 20, font = ("Arial 18"))
        coinMenu_2.grid(row = 7, column = 0)

        confirmButtom = tk.Button(frame, text = "Next", command = check_exchange, font = ("Arial 18"))
        confirmButtom . grid(row = 8, column = 0, columnspan = 1)
        backButtom    = tk.Button(frame, text = "Back", command = sys.exit, font = ("Arial 18"))
        backButtom    . grid(row = 9, column = 0, columnspan = 1)

        for widget in frame.winfo_children():
            widget.configure(background = "#0A1A33", foreground = "white")
        for widget in self.root.winfo_children():
            widget.configure(bg = "#0A1A33")
############################################################################################################################################################################

    def input_key_secret(self):

        def check_user_info():

            self.api_key_1      = entry_api_key_1.get()
            self.secret_key_1   = entry_secret_key_1.get()
            self.api_key_2      = entry_api_key_2.get()
            self.secret_key_2   = entry_secret_key_2.get()
            if self.exchange_1 == "BitoPro":
                self.bito_email     = entry_bito_email.get()
                self.bito_vip_level = entry_bito_vip_level.get()
            if self.exchange_2 == "OKX":
                self.okx_passphrase = entry_okx_passphrase.get()

            try:
                clear(self.root)

                # -------------------------------------------------- login ------------------------------------------------
                if self.exchange_1 == "BitoPro":
                    self.arbitrage_bot.exchange_1_login(self.api_key_1, self.secret_key_1, self.bito_email)
                else:
                    self.arbitrage_bot.exchange_1_login(self.api_key_1, self.secret_key_1)
                if self.exchange_2 == "OKX":
                    self.arbitrage_bot.exchange_2_login(self.api_key_2, self.secret_key_2, self.okx_passphrase)
                else:
                    self.arbitrage_bot.exchange_2_login(self.api_key_2, self.secret_key_2)
                # ---------- get min_qty, min_qty_step, balance; set direction, set_initial_capital(quote, base) ----------
                self.arbitrage_bot.order_min_limitation()
                balance_res = self.arbitrage_bot.check_balance()
                if balance_res == "error":
                    messagebox.showerror("Error", "Balance insufficient, please replendish before continue")
                    self.input_key_secret()
    
                elif balance_res == "login error":
                    messagebox.showerror("Error", "Login error, please check your login params")
                    self.input_key_secret()                   
                self.arbitrage_bot.set_initial_capital() 

                # ---------------------------------------------- plot balance ----------------------------------------------
                frame = tk.Frame()
                frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
                tk.Label(frame, text = f"{self.exchange_1} {self.quote}  balance: {self.arbitrage_bot.exchange_1_quote_balance}", font = ("Arial 18")).grid(row = 0, column = 0, sticky = "w")
                tk.Label(frame, text = f"{self.exchange_1} {self.base}   balance: {self.arbitrage_bot.exchange_1_base_balance}" , font = ("Arial 18")).grid(row = 1, column = 0, sticky = "w")
                tk.Label(frame, text = f"{self.exchange_2} {self.quote}  balance: {self.arbitrage_bot.exchange_2_quote_balance}", font = ("Arial 18")).grid(row = 2, column = 0, sticky = "w")
                tk.Label(frame, text = f"{self.exchange_2} {self.base}   balance: {self.arbitrage_bot.exchange_2_base_balance}" , font = ("Arial 18")).grid(row = 3, column = 0, sticky = "w")

                # -------------------------------------------- get and plot trading fee -------------------------------------
                if self.exchange_1 == "BitoPro":
                    self.arbitrage_bot.get_trading_fee(self.bito_vip_level)
                else:
                    self.arbitrage_bot.get_trading_fee()
                tk.Label(frame, text = f"{self.exchange_1} trading fee: {self.arbitrage_bot.exchange_1_trade_fee}", font = ("Arial 18")).grid(row = 4, column = 0, sticky = "w")
                tk.Label(frame, text = f"{self.exchange_2} trading fee: {self.arbitrage_bot.exchange_2_trade_fee}", font = ("Arial 18")).grid(row = 5, column = 0, sticky = "w")

                backButtom    = tk.Button(frame, text = "Back", command = self.input_key_secret,    font = ("Arial 18"))
                backButtom    . grid(row = 6, column = 0, sticky = "E")
                confirmButtom = tk.Button(frame, text = "Next", command = self.input_arbitrage_param, font = ("Arial 18"))
                confirmButtom . grid(row = 6, column = 1, sticky = "W")

                for widget in self.root.winfo_children():
                    widget.configure(bg = "#0A1A33")
                for widget in frame.winfo_children():
                    widget.configure(bg = "#0A1A33", foreground = "white")

            except Exception as e:
                messagebox.showerror("Error", f"error {e}")
                self.input_key_secret()

        # --------------------------- input key secret --------------------------- 
        clear(self.root)
        frame = tk.Frame()
        frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        tk.Label(frame, text = f"{self.exchange_1} api key",    font = ("Arial 18")).grid(row = 0, column = 0, sticky = "w")
        tk.Label(frame, text = f"{self.exchange_1} secret key", font = ("Arial 18")).grid(row = 1, column = 0, sticky = "w")
        tk.Label(frame, text = f"{self.exchange_2} api key",    font = ("Arial 18")).grid(row = 2, column = 0, sticky = "w")
        tk.Label(frame, text = f"{self.exchange_2} secret key", font = ("Arial 18")).grid(row = 3, column = 0, sticky = "w")

        if self.exchange_1 == "BitoPro":
            tk.Label(frame, text = f"BitoPro Email", font = ("Arial 18")).grid(row = 4, column = 0, sticky = "w")
            entry_bito_email = tk.Entry(frame, textvariable = tk.StringVar(), font = ("Arial 18"), bg = "#0A1A33", fg = "white")
            entry_bito_email.grid(row = 4, column = 1)

            tk.Label(frame, text = f"BitoPro VIP level", font = ("Arial 18")).grid(row = 5, column = 0, sticky = "w")
            entry_bito_vip_level = ttk.Combobox(frame,
                                                 values = ["0", "1", "2", "3", "4", "5", "6", "market maker"], 
                                                 width = 19, font = ("Arial 18"))    
            entry_bito_vip_level.grid(row = 5, column = 1)

        if self.exchange_2 == "OKX":
            tk.Label(frame, text = f"OKX Passphrase", font = ("Arial 18")).grid(row = 6, column = 0, sticky = "w")
            entry_okx_passphrase = tk.Entry(frame, textvariable = tk.StringVar(), font = ("Arial 18"), bg = "#0A1A33", fg = "white")
            entry_okx_passphrase.grid(row = 6, column = 1)

        entry_api_key_1     = tk.Entry(frame, textvariable = tk.StringVar(), font = ("Arial 18"), bg = "#0A1A33", fg = "white")
        entry_api_key_1     . grid(row = 0, column = 1)
        entry_secret_key_1  = tk.Entry(frame, textvariable = tk.StringVar(), font = ("Arial 18"), bg = "#0A1A33", fg = "white")
        entry_secret_key_1  . grid(row = 1, column = 1)
        entry_api_key_2     = tk.Entry(frame, textvariable = tk.StringVar(), font = ("Arial 18"), bg = "#0A1A33", fg = "white")
        entry_api_key_2     . grid(row = 2, column = 1)
        entry_secret_key_2  = tk.Entry(frame, textvariable = tk.StringVar(), font = ("Arial 18"), bg = "#0A1A33", fg = "white")
        entry_secret_key_2  . grid(row = 3, column = 1)


        confirmButtom = tk.Button(frame, text = "Next", command = check_user_info, font = ("Arial 18"), bg = "#0A1A33", fg = "white")
        confirmButtom . grid(row = 7, column = 1, sticky = "NESW")
        backButtom    = tk.Button(frame, text = "Back", command = self.input_exchange, font = ("Arial 18"), bg = "#0A1A33", fg = "white")
        backButtom    . grid(row = 7, column = 0, sticky = "NESW")

        for widget in self.root.winfo_children():
            widget.configure(background = "#0A1A33")
        for widget in frame.winfo_children():
            widget.configure(background = "#0A1A33", foreground = "white")

############################################################################################################################################################################

    def input_arbitrage_param(self):

        def check_arbitrage_param():

            try:
                self.arbitrage_bot.arbitrage_ratio         = float(entry_arbitrage_ratio.get())
                self.arbitrage_bot.arbitrage_quantity_type = entry_arbitage_quantity_type.get() # fixed, equity, market
                self.arbitrage_bot.arbitrage_quantity      = float(entry_arbitrage_quantity.get()) # fixed: contract / equity: % of equity / market: % of min(ask, bid)
                self.arbitrage_bot.fetch_current_price()
                for i in range(1):

                    if self.arbitrage_bot.arbitrage_ratio < self.arbitrage_bot.min_arbitrage_ratio:
                        messagebox.showwarning("warning", "arbitrage ratio is too small to cover the commission")
                        self.input_arbitrage_param()
                        break

                    if self.arbitrage_bot.arbitrage_quantity_type == "fixed":
                        if (self.arbitrage_bot.arbitrage_quantity > self.arbitrage_bot.ex1_to_ex2_max_qty and 
                            self.arbitrage_bot.arbitrage_quantity > self.arbitrage_bot.ex2_to_ex1_max_qty):
                            messagebox.showerror("error", "quantity is greater than the balance")
                            self.input_arbitrage_param()
                            break
                        if self.arbitrage_bot.arbitrage_quantity < self.arbitrage_bot.min_order_qty:
                            messagebox.showerror("error", "quantity is smaller than the minimum lot size")
                            self.input_arbitrage_param()
                            break

                    if self.arbitrage_bot.arbitrage_quantity_type == "equity":
                        if self.arbitrage_bot.arbitrage_quantity > 1.0 or self.arbitrage_bot.arbitrage_quantity <= 0:
                            messagebox.showerror("error", "percent of equity is must be < 1.00 and > 0.00")
                            break

                    if self.arbitrage_bot.arbitrage_quantity == "market":
                        if self.arbitrage_bot.arbitrage_quantity >= 0.5:
                            messagebox.showerror("warning" "the slippage might be too big, percent of market must be < 0.5")                   
                            break

                    self.enter_main_page()


            except Exception as e:
                messagebox.showerror("Error", e)
                self.input_arbitrage_param()

        # --------------------------- input arbitrage params --------------------------- 
        clear(self.root)
        frame = tk.Frame()
        frame.place(relx = 0.5, rely=0.5, anchor = tk.CENTER)
        tk.Label(frame, text = f"{self.exchange_1} trading fee:", font=("Arial 18")).grid(row=0, column=0, sticky="w")
        tk.Label(frame, text = f"{self.exchange_2} trading fee:", font=("Arial 18")).grid(row=1, column=0, sticky="w")
        tk.Label(frame, text = f"minimum arbitrage ratio:"      , font=("Arial 18")).grid(row=2, column=0, sticky="w")
        tk.Label(frame, text = f"{self.arbitrage_bot.exchange_1_trade_fee}", font=("Arial 18")).grid(row=0, column=1, sticky="w")
        tk.Label(frame, text = f"{self.arbitrage_bot.exchange_2_trade_fee}", font=("Arial 18")).grid(row=1, column=1, sticky="w")
        tk.Label(frame, text = f"{self.arbitrage_bot.min_arbitrage_ratio}" , font=("Arial 18")).grid(row=2, column=1, sticky="w")
        tk.Label(frame, text = f"user arbitrage ratio: "                                                  , font=("Arial 18")).grid(row=3, column=0, sticky="w")
        tk.Label(frame, text = f"arbitrage quantity type"                                                 , font=("Arial 18")).grid(row=4, column=0, sticky="w")
        tk.Label(frame, text = f"arbitrage quantity"                                                      , font=("Arial 18")).grid(row=5, column=0, sticky="w")

        entry_arbitrage_ratio        = tk.Entry(frame, textvariable = tk.DoubleVar(), font = ("Arial 18"))
        entry_arbitrage_ratio        . grid(row = 3, column = 1)
        entry_arbitage_quantity_type = ttk.Combobox(frame,
                                                    values = ["fixed", "market", "equity"], 
                                                    width = 19, font = ("Arial 18"))
        entry_arbitage_quantity_type.grid(row = 4, column = 1)
        entry_arbitrage_quantity     = tk.Entry(frame, textvariable = tk.DoubleVar(), font = ("Arial 18"))
        entry_arbitrage_quantity     . grid(row=5, column=1)

        backButtom = tk.Button(frame, text = "Back", command = self.input_key_secret, font = ("Arial 18"))
        backButtom . grid(row = 6, column = 0, sticky = "NESW")
        confirmButtom = tk.Button(frame, text = "Next", command = check_arbitrage_param, font = ("Arial 18"))
        confirmButtom . grid(row = 6, column = 1, sticky = "NESW")
        entry_arbitage_quantity_type.insert(0, "fixed")

        for widget in self.root.winfo_children():
            widget.configure(background = "#0A1A33")
        for widget in frame.winfo_children():
            widget.configure(background = "#0A1A33", foreground = "white")

############################################################################################################################################################################

    def update(self, new_data, exchange):


        if self.connection == False:
            self.lock.acquire()
            self.ex_1_datastream.stop()
            self.ex_2_datastream.stop()
            self.lock.release()
            self.ex_1_datastream = DataStream(self.exchange_1, self.quote, self.base, self.update)
            self.ex_2_datastream = DataStream(self.exchange_2, self.quote, self.base, self.update)
            tk.Label(self.root, text = f"You are offline now!", font=("Arial 24"), fg = "white", bg = "#A94141").place(relx = 0.5, rely = 0.5, anchor = tk.CENTER)
            tk.Button(self.root, text = "Reconnect", command = self.enter_main_page, font = ("Arial 18"), fg = "white", bg = "#3B3B3B").place(relx = 0.5, rely = 0.58, anchor = tk.CENTER)

        
        else:
            res = self.arbitrage_bot.on_arbitrage(new_data, exchange)

            if len(res) == 4:

                if exchange == self.exchange_1:
                    self.exchange_1_bid_label.config(text=f"{new_data[0]}")
                    self.exchange_1_ask_label.config(text=f"{new_data[1]}")
                    self.exchange_1_bid_qty_label.config(text=f"{new_data[2]}")
                    self.exchange_1_ask_qty_label.config(text=f"{new_data[3]}")
                    self.exchange_1_time_label.config(text=f"{new_data[4]}")
                    self.status_bar_ex1_to_ex2.config(height=math.floor(math.fabs(res[0])), bg="green" if res[1] == True else "red")

                if exchange == self.exchange_2:
                    self.exchange_2_bid_label.config(text=f"{new_data[0]}")
                    self.exchange_2_ask_label.config(text=f"{new_data[1]}")
                    self.exchange_2_bid_qty_label.config(text=f"{new_data[2]}")
                    self.exchange_2_ask_qty_label.config(text=f"{new_data[3]}")
                    self.exchange_2_time_label.config(text=f"{new_data[4]}")
                    self.status_bar_ex2_to_ex1.config(height=math.floor(math.fabs(res[2])), bg="green" if res[3] == True else "red")

            else:
                self.after_arbitrage(res)

############################################################################################################################################################################

    def after_arbitrage(self, trade_res):

        self.lock.acquire()
        clear(self.log_frame)
        frame = tk.Frame(bg="#A6ADFF")
        frame.place(relx=0.8, rely=0.82, anchor=tk.CENTER)
        tk.Label(frame, text="Arbitrage Finished" , font=("Arial", "20", "bold"), fg="#18455D", bg="#A6ADFF").grid(row=0, column=0)
        tk.Label(frame, text="binance_fill_price" , font=("Arial 18"), fg="#18455D", bg="#A6ADFF").grid(row=1, column=0, sticky="w")
        tk.Label(frame, text=f"{trade_res[1][3]}" , font=("Arial 18"), fg="black"  , bg="#A6ADFF").grid(row=1, column=1, sticky="w")
        tk.Label(frame, text="bito_fill_price"    , font=("Arial 18"), fg="#18455D", bg="#A6ADFF").grid(row=2, column=0, sticky="w")
        tk.Label(frame, text=f"{trade_res[0][3]}" , font=("Arial 18"), fg="black"  , bg="#A6ADFF").grid(row=2, column=1, sticky="w")
        tk.Label(frame, text="binance_fill_amount", font=("Arial 18"), fg="#18455D", bg="#A6ADFF").grid(row=3, column=0, sticky="w")
        tk.Label(frame, text=f"{trade_res[1][4]}" , font=("Arial 18"), fg="black"  , bg="#A6ADFF").grid(row=3, column=1, sticky="w")
        tk.Label(frame, text="bito_fill_amount"   , font=("Arial 18"), fg="#18455D", bg="#A6ADFF").grid(row=4, column=0, sticky="w")
        tk.Label(frame, text=f"{trade_res[0][4]}" , font=("Arial 18"), fg="black"  , bg="#A6ADFF").grid(row=4, column=1, sticky="w")
        tk.Label(frame, text="order profit"       , font=("Arial 18"), fg="#18455D", bg="#A6ADFF").grid(row=5, column=0, sticky="w")
        tk.Label(frame, text=f"{trade_res[2]}" , font=("Arial 18"), fg="black"  , bg="#A6ADFF").grid(row=5, column=1, sticky="w")
        tk.Label(frame, text=f"{self.exchange_1} commission", font=("Arial 18")      , fg="#18455D", bg="#A6ADFF").grid(row=6, column=0, sticky="w")
        tk.Label(frame, text=f"{trade_res[0][5]}{trade_res[0][6]}", font=("Arial 18"), fg="black"  , bg="#A6ADFF").grid(row=6, column=1, sticky="w")
        tk.Label(frame, text=f"{trade_res[1][5]}{trade_res[1][6]}", font=("Arial 18"), fg="black"  , bg="#A6ADFF").grid(row=7, column=1, sticky="w")



        self.time_log.              append(trade_res[0][0])
        self.exchange_log.          append(trade_res[0][1])
        self.direction_log.         append(trade_res[0][2])
        self.fill_price_log.        append(trade_res[0][3])
        self.fill_quantity_log.     append(trade_res[0][4])
        self.commission_log.        append(trade_res[0][5])
        self.commission_asset_log.  append(str.upper(trade_res[0][6]))
        self.time_log.              append(trade_res[1][0])
        self.exchange_log.          append(trade_res[1][1])
        self.direction_log.         append(trade_res[1][2])
        self.fill_price_log.        append(trade_res[1][3])
        self.fill_quantity_log.     append(trade_res[1][4])
        self.commission_log.        append(trade_res[1][5])
        self.commission_asset_log.  append(str.upper(trade_res[1][6]))

        clear(self.log_frame)
        for i in range(len(self.time_log)):
            tk.Label(self.log_frame, text=f"{self.time_log[i]}"             , fg="white").grid(row=1 + i, column=0)
            tk.Label(self.log_frame, text=f"{self.exchange_log[i]}"         , fg="white").grid(row=1 + i, column=1)
            tk.Label(self.log_frame, text=f"{self.direction_log[i]}"        , fg="white").grid(row=1 + i, column=2)
            tk.Label(self.log_frame, text=f"{self.fill_price_log[i]}"       , fg="white").grid(row=1 + i, column=3)
            tk.Label(self.log_frame, text=f"{self.fill_quantity_log[i]}"    , fg="white").grid(row=1 + i, column=4)
            tk.Label(self.log_frame, text=f"{self.commission_log[i]}"       , fg="white").grid(row=1 + i, column=5)
            tk.Label(self.log_frame, text=f"{self.commission_asset_log[i]}" , fg="white").grid(row=1 + i, column=6)

        for widget in self.log_frame.winfo_children():
            widget.configure(bg = "#0A1A33")

        balance_res = self.arbitrage_bot.check_balance()
        self.ex1_quote_balance_label.config(text = f"{self.arbitrage_bot.exchange_1_quote_balance}")
        self.ex1_base_balance_label.config( text = f"{self.arbitrage_bot.exchange_1_base_balance}")
        self.ex2_quote_balance_label.config(text = f"{self.arbitrage_bot.exchange_2_quote_balance}")
        self.ex2_base_balance_label.config( text = f"{self.arbitrage_bot.exchange_2_base_balance}")
        self.quote_profit_label.config(     text = f"{self.arbitrage_bot.exchange_1_quote_balance + self.arbitrage_bot.exchange_2_quote_balance - self.arbitrage_bot.initial_quote_balance}")
        self.base_profit_label.config(      text = f"{self.arbitrage_bot.exchange_1_base_balance + self.arbitrage_bot.exchange_2_base_balance - self.arbitrage_bot.initial_base_balance}")
        self.count_label.config(text = f"{self.arbitrage_bot.count}")
        self.move_label.config(text = self.arbitrage_bot.direction)
        
        clear(frame)
        frame.destroy()

        for i in range(1):
            if balance_res == False:
                messagebox.showerror("Error", "Balance insufficient, please replendish and log in again")
                self.input_key_secret()
                break
            self.lock.release()

############################################################################################################################################################################

    def enter_main_page(self):

        def start_datastream():

            clear(frame)
            frame.destroy()
            self.ex_1_datastream.start()
            self.ex_2_datastream.start()

        clear(self.root)
        # frame of the main page
        ex1_to_ex2              = tk.Frame()
        ex1_to_ex2              . place(relx = 0.3, rely = 0.6, anchor = tk.CENTER)
        ex2_to_ex1              = tk.Frame()
        ex2_to_ex1              . place(relx = 0.4, rely = 0.6, anchor = tk.CENTER)
        time_frame              = tk.Frame()
        time_frame              . place(relx = 0.35, rely = 0.4, anchor = tk.CENTER)
        self.balance_frame      = tk.Frame(highlightbackground = "white", highlightcolor = "white", highlightthickness = 2)
        self.balance_frame      . place(relx = 0.01, rely = 0.01)
        self.move_frame         = tk.Frame()
        self.move_frame         . place(relx = 0.35, rely = 0.2, anchor = tk.CENTER)
        self.log_frame          = tk.Frame(highlightbackground="white", highlightcolor="white", highlightthickness=2)
        self.log_frame          . place(relx = 0.8,  rely = 0.1, anchor = "n")
        self.count_frame        = tk.Frame(highlightbackground = "#00B811", highlightcolor = "#00B811", highlightthickness = 2)
        self.count_frame        . place(relx = 0.35, rely = 0.05, anchor = tk.CENTER)


        # plot status bar
        self.status_bar_ex1_to_ex2  = tk.Label(self.root, text = " ", font = ("Arial 12"), height = 0, width = 6)
        self.status_bar_ex1_to_ex2  . place(relx = 0.2, rely = 1, anchor = tk.CENTER)
        self.status_bar_ex1_to_ex2  . config(bg = "green")
        self.status_bar_ex2_to_ex1  = tk.Label(self.root, text = " ", font = ("Arial 12"), height = 0, width = 6)
        self.status_bar_ex2_to_ex1  . place(relx = 0.5, rely = 1, anchor = tk.CENTER)
        self.status_bar_ex2_to_ex1  . config(bg = "red")

        # plot balance sheet ( self.balance_frame )
        tk.Label(self.balance_frame, text = "Balance Sheet", font = ("Arial 8"), fg = "white").grid(row = 0, column = 0, sticky = "w")
        tk.Label(self.balance_frame, text = f"{self.exchange_1} {self.quote} balance:", font = ("Arial 8"), fg = "white").grid(row = 1, column = 0, sticky = "w")
        self.ex1_quote_balance_label = tk.Label(self.balance_frame, text = f"{self.arbitrage_bot.exchange_1_quote_balance}", font = ("Arial 8"), fg = "white")
        self.ex1_quote_balance_label.grid(row = 1, column = 1, sticky = "w")
        tk.Label(self.balance_frame, text = f"{self.exchange_1} {self.base} balance:", font = ("Arial 8"), fg = "white").grid(row = 2, column = 0, sticky = "w")
        self.ex1_base_balance_label  = tk.Label(self.balance_frame, text = f"{self.arbitrage_bot.exchange_1_base_balance}" , font = ("Arial 8"), fg = "white")
        self.ex1_base_balance_label.grid(row = 2, column = 1, sticky = "w")
        tk.Label(self.balance_frame, text = f"{self.exchange_2} {self.quote} balance:", font = ("Arial 8"), fg = "white").grid(row = 3, column = 0, sticky = "w")
        self.ex2_quote_balance_label = tk.Label(self.balance_frame, text = f"{self.arbitrage_bot.exchange_2_quote_balance}", font = ("Arial 8"), fg = "white")
        self.ex2_quote_balance_label.grid(row = 3, column = 1, sticky = "w")
        tk.Label(self.balance_frame, text = f"{self.exchange_2} {self.base} balance", font = ("Arial 8"), fg = "white").grid(row = 4, column = 0, sticky = "w")
        self.ex2_base_balance_label  = tk.Label(self.balance_frame, text = f"{self.arbitrage_bot.exchange_2_base_balance}" , font = ("Arial 8"), fg = "white")
        self.ex2_base_balance_label.grid(row = 4, column = 1, sticky = "w")
        tk.Label(self.balance_frame, text = f"{self.quote} Profit:", font = ("Arial 8"), fg = "white").grid(row = 5, column = 0, sticky = "w")
        self.quote_profit_label      = tk.Label(self.balance_frame, text = " ", font = ("Arial 8"),fg = "white")
        self.quote_profit_label.grid(row = 5, column = 1, sticky = "w")
        tk.Label(self.balance_frame, text = f"{self.base} Profit:",  font = ("Arial 8"), fg = "white").grid(row = 6, column = 0, sticky = "w")
        self.base_profit_label       = tk.Label(self.balance_frame, text = " ", font = ("Arial 8"), fg = "white")                                             
        self.base_profit_label.grid(row = 6, column = 1, sticky = "w")

        # plot ex1_to_ex2 ask, ask qty, bid, bid qty ( ex1_to_ex2 )
        tk.Label(ex1_to_ex2, text = f"{self.exchange_1} Ask", fg = "white").grid(row = 0, column = 0)
        self.exchange_1_ask_label = tk.Label(ex1_to_ex2, text = "conencting", fg = "white")     
        self.exchange_1_ask_label.grid(row = 1, column = 0)
        tk.Label(ex1_to_ex2, text = f"{self.exchange_1} Ask Quantity", fg = "white").grid(row = 2, column = 0)
        self.exchange_1_ask_qty_label = tk.Label(ex1_to_ex2, text = "conencting", fg = "white") 
        self.exchange_1_ask_qty_label.grid(row = 3, column = 0)
        tk.Label(ex1_to_ex2, text = f"{self.exchange_2} Bid", fg = "white").grid(row = 4, column = 0)
        self.exchange_2_bid_label = tk.Label(ex1_to_ex2, text="conencting", fg="white")         
        self.exchange_2_bid_label.grid(row = 5, column = 0)
        tk.Label(ex1_to_ex2, text = f"{self.exchange_2} Bid Qunatity", fg = "white").grid(row = 6, column = 0)
        self.exchange_2_bid_qty_label = tk.Label(ex1_to_ex2, text = "conencting", fg = "white") 
        self.exchange_2_bid_qty_label.grid(row = 7, column = 0)

        # plot ex2 to ex1 ask, ask qty, bid, bid qty ( ex2_to_ex1 )
        tk.Label(ex2_to_ex1, text = f"{self.exchange_2} Ask", fg = "white").grid(row = 0, column = 0)
        self.exchange_2_ask_label = tk.Label(ex2_to_ex1, text = "conencting", fg = "white")
        self.exchange_2_ask_label.grid(row = 1, column = 0)
        tk.Label(ex2_to_ex1, text = f"{self.exchange_2} Ask Quantity", fg = "white").grid(row = 2, column = 0)
        self.exchange_2_ask_qty_label = tk.Label(ex2_to_ex1, text = "conencting", fg="white")
        self.exchange_2_ask_qty_label.grid(row = 3, column = 0)
        tk.Label(ex2_to_ex1, text = f"{self.exchange_1} Bid", fg = "white").grid(row = 4, column = 0)
        self.exchange_1_bid_label = tk.Label(ex2_to_ex1, text = "conencting", fg = "white")
        self.exchange_1_bid_label.grid(row = 5, column = 0)
        tk.Label(ex2_to_ex1, text = f"{self.exchange_1} Bid Quantity", fg = "white").grid(row = 6, column = 0)
        self.exchange_1_bid_qty_label = tk.Label(ex2_to_ex1, text = "conencting", fg = "white")
        self.exchange_1_bid_qty_label.grid(row = 7, column = 0)

        # plot timestamp ( self.timeframe )
        tk.Label(time_frame, text = f"{self.exchange_1} Timestamp", fg = "white").grid(row = 0, column = 0)
        self.exchange_1_time_label = tk.Label(time_frame, text = "connecting", fg = "white")
        self.exchange_1_time_label.grid(row = 1, column = 0)
        tk.Label(time_frame, text = f"{self.exchange_2} Timestamp", fg = "white").grid(row = 2, column = 0)
        self.exchange_2_time_label = tk.Label(time_frame, text = "connecting", fg = "white")
        self.exchange_2_time_label.grid(row = 3, column = 0)

        # plot next arbitrage move label (self.move_frame)
        tk.Label(self.move_frame, text = "Next Arbitrage Move:", fg = "white").grid(row = 0, column = 0)
        self.move_label = tk.Label(self.move_frame, font = ("Arial 16"), fg = "red", text = self.arbitrage_bot.direction)
        self.move_label.grid(row=1, column=0)


        # plot trade log ( self.log_frame )
        # tk.Label(self.root,      text = "Trade History",    font = ("Arial 18"), fg = "white", highlightbackground = "white", highlightcolor = "white", highlightthickness = 2).place(relx = 0.8, rely = 0.05, anchor = tk.CENTER)
        # tk.Label(self.log_frame, text = "Time",             font = ("Arial 10"), fg = "white").grid(row = 1, column = 0)
        # tk.Label(self.log_frame, text = "Exchange",         font = ("Arial 10"), fg = "white").grid(row = 1, column = 1)
        # tk.Label(self.log_frame, text = "Direction",        font = ("Arial 10"), fg = "white").grid(row = 1, column = 2)
        # tk.Label(self.log_frame, text = "Fill Price",       font = ("Arial 10"), fg = "white").grid(row = 1, column = 3)
        # tk.Label(self.log_frame, text = "Fill Quantity",    font = ("Arial 10"), fg = "white").grid(row = 1, column = 4)
        # tk.Label(self.log_frame, text = "Commission",       font = ("Arial 10"), fg = "white").grid(row = 1, column = 5)
        # tk.Label(self.log_frame, text = "Commission Asset", font = ("Arial 10"), fg = "white").grid(row = 1, column = 6)
       

        self.time_log = ["Time", "2022-12-01 08:00:00(test)", "2022-12-01 08:00:00(test)"]
        self.exchange_log = ["Exchange", "BitoPro", "Binance"]
        self.direction_log = ["Direction", "BUY", "SELL"]
        self.fill_price_log = ["Fill Price", 10000, 10001]
        self.fill_quantity_log = ["Fill Quantity", 0.01, 0.01]
        self.commission_log = ["Commission", 1, 1]
        self.commission_asset_log = ["Commission Asset", "BTC", "BTC"]
        for i in range(len(self.time_log)):
            tk.Label(self.log_frame, text = f"{self.time_log[i]}",              fg = "white").grid(row = 1 + i, column = 0)
            tk.Label(self.log_frame, text = f"{self.exchange_log[i]}",          fg = "white").grid(row = 1 + i, column = 1)
            tk.Label(self.log_frame, text = f"{self.direction_log[i]}",         fg = "white").grid(row = 1 + i, column = 2)
            tk.Label(self.log_frame, text = f"{self.fill_price_log[i]}",        fg = "white").grid(row = 1 + i, column = 3)
            tk.Label(self.log_frame, text = f"{self.fill_quantity_log[i]}",     fg = "white").grid(row = 1 + i, column = 4)
            tk.Label(self.log_frame, text = f"{self.commission_log[i]}",        fg = "white").grid(row = 1 + i, column = 5)
            tk.Label(self.log_frame, text = f"{self.commission_asset_log[i]}",  fg = "white").grid(row = 1 + i, column = 6)


        tk.Label(self.count_frame, text = "24hours Arbitrage Count: ", fg = "white", font = ("Arial 18")).grid(row = 0, column = 0, sticky = "NESW")
        self.count_label = tk.Label(self.count_frame, text = " 0 ", font = ("Arial 18"), fg = "#D7FFDB")
        self.count_label.grid(row = 0, column = 1)

        def end():
            os._exit(0)
        confirmButtom = tk.Button(self.root, text="EXIT", command=end, font=(
            "Arial 18"), fg="red", highlightbackground="white", highlightcolor="white", highlightthickness=2, relief="raised")
        confirmButtom.place(relx=0.95, rely=0.02)

        self.ex_1_datastream = DataStream(self.exchange_1, self.quote, self.base, self.update)
        self.ex_2_datastream = DataStream(self.exchange_2, self.quote, self.base, self.update)

        frame = tk.Frame()
        frame.place(relx = 0.35, rely = 0.8, anchor = tk.CENTER)
        backButtom  = tk.Button(frame, text = "Back", command = self.input_arbitrage_param, font = ("Arial 18"), fg = "white")
        startButtom = tk.Button(frame, text = "START ATBITRAGE", command = start_datastream, font = ("Arial 18"), fg = "white")
        backButtom .grid(row = 0, column = 0, sticky = "E")
        startButtom.grid(row = 0, column = 1, sticky = "W")

        for widget in self.root.winfo_children():
            widget.configure(bg="#0A1A33")
        for widget in self.balance_frame.winfo_children():
            widget.configure(bg = "#0A1A33")
        for widget in self.log_frame.winfo_children():
            widget.configure(bg = "#0A1A33")
        for widget in time_frame.winfo_children():
            widget.configure(bg = "#0A1A33")
        for widget in ex1_to_ex2.winfo_children():
            widget.configure(bg = "#0A1A33")
        for widget in ex2_to_ex1.winfo_children():
            widget.configure(bg = "#0A1A33")
        for widget in self.move_frame.winfo_children():
            widget.configure(bg = "#0A1A33")
        for widget in self.count_frame.winfo_children():
            widget.configure(bg = "#0A1A33")
        for widget in frame.winfo_children():
            widget.configure(bg = "#0A1A33")

        self.status_bar_ex1_to_ex2.configure(bg="#37CA00")
        self.status_bar_ex2_to_ex1.configure(bg="#E92E00")

    def run(self):
        self.root.mainloop()


class DataStream(threading.Thread):

    def __init__(self, exchange, quote, base, callback):

        threading.Thread.__init__(self)
        self.exchange = exchange
        self.quote = quote
        self.base = base
        self.callback = callback
        self.stop_event = threading.Event()

        if exchange == "BitoPro":
            self.ws = websocket.WebSocketApp(
                f"wss://stream.bitopro.com:9443/ws/v1/pub/order-books/{self.quote}_{self.base}",
                on_message = lambda ws, msg: self.on_message_bito(ws, msg),
                on_close  = lambda ws: self.on_close_bito(ws),
                on_error = lambda msg: self.on_error_bito(msg),
                on_open = lambda ws: self.on_open_bito(ws)
            )
        elif exchange == "Binance":
            self.ws = websocket.WebSocketApp(
                f"wss://stream.binance.com:9443/ws/{str.lower(self.quote)}{str.lower(self.base)}@ticker",
                on_message=lambda ws, msg: self.on_message_binance(ws, msg),
                on_close=lambda ws:      self.on_close_binance(ws),
                on_error=lambda msg:     self.on_error_binance(msg),
                on_open=lambda msg:     self.on_open_binance(msg)
            )
        elif exchange == "OKX":
            self.ws = websocket.WebSocketApp(
                f"wss://ws.okx.com:8443/ws/v5/public",
                on_message = lambda ws, msg: self.on_message_okx(ws, msg),
                on_close  = lambda ws: self.on_close_okx(ws),
                on_error = lambda msg: self.on_error_okx(msg),
                on_open = lambda ws: self.on_open_okx(ws),
            )


    def on_open_bito(self, ws):

        window.connection = True
        logger.info(f"{self.exchange} connected\n")

    def on_message_bito(self, ws, message):
        jsonMessage = json.loads(message)
        callBackMessage = (
            float(jsonMessage["bids"][0]["price"]),
            float(jsonMessage["asks"][0]["price"]),
            float(jsonMessage["bids"][0]["amount"]),
            float(jsonMessage["asks"][0]["amount"]),
            int(jsonMessage["timestamp"])
        )
        self.callback(callBackMessage, self.exchange)

    def on_error_bito(self, ws, error):
        logger.error(error)

    def on_close_bito(self, ws):
        logger.info(f"{self.exchange} closed connection\n")
        window.connection = False
        self.callback(False, self.exchange)

    ##########

    def on_open_binance(self, ws):

        window.connection = True
        logger.info(f"{self.exchange} connected\n")

    def on_message_binance(self, ws, message):
        jsonMessage = json.loads(message)
        callBackMessage = (
            float(jsonMessage["b"]),
            float(jsonMessage["a"]),
            float(jsonMessage["B"]),
            float(jsonMessage["A"]),
            float(jsonMessage["E"]),
        )
        self.callback(callBackMessage, self.exchange)


    def on_close_binance(self, ws):
        logger.info(f"{self.exchange} closed connection\n")
        window.connection = False
        self.callback(False, self.exchange)

    def on_error_binance(self, error):
        logger.error(error)

    def run(self):
        self.ws.run_forever()


#########################

    def on_open_okx(self, ws):

        window.connection = True
        subscribe_message = {
                            "op": "subscribe",
                            "args": [
                                {
                                "channel": "books",
                                "instId": f"{self.quote}-{self.base}"
                                }
                            ]
                            }
        ws.send(json.dumps(subscribe_message))


    def on_message_okx(self, ws, message):
        jsonMessage = json.loads(message)
        callBackMessage = (
            float(jsonMessage["data"][0]["bids"][0][0]),
            float(jsonMessage["data"][0]["asks"][0][0]),
            float(jsonMessage["data"][0]["bids"][0][1]),
            float(jsonMessage["data"][0]["asks"][0][1]),
            int(jsonMessage["data"][0]["ts"])
        )
        print(callBackMessage)
        self.callback(callBackMessage, self.exchange)

    def on_error_okx(self, ws, error):
        logger.error(error)

    def on_close_okx(self, ws):
        logger.info(f"{self.exchange} closed connection\n")
        window.connection = False
        self.callback(False, self.exchange)

    def run(self):
        self.ws.run_forever()

#########################

    def stop(self):
        self.stop_event.set()


if __name__ == "__main__":

    window = Window()
    window.run()
