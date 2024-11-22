import MetaTrader5 as mt5
import pandas as pd
from talib import abstract
import time
from BotCodeV2.OrderManager import OrderManager
import threading

class Scalper:

    def __init__(self, symbol, buyEntryRegion, sellEntryRegion):
        self.symbol = symbol
        self.ohlc = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 500)
        self.ohlc = pd.DataFrame(self.ohlc)
        self.buyEntryRegions = buyEntryRegion
        self.sellEntryRegions = sellEntryRegion
        self.open_orders = 0
        self.buy_order_open = False
        self.sell_order_open = False
        self.run()

    def __findBlockOrders__(self):
        print("Finding Block order regions")
        self.buyEntryRegions = []
        self.sellEntryRegions = []
        self.ohlc = pd.DataFrame(mt5.copy_rates_from_pos(self.symbol, mt5.TIMEFRAME_M5, 0, 1000), columns=['time', 'open', 'high', 'low', 'close', 'tick_volume', 'spread', 'real_volume'])
        self.ohlc["candle_length"] = abs(self.ohlc["close"] - self.ohlc["open"])
        avg_order_length = self.ohlc["candle_length"].mean()
        block_orders = self.ohlc.index[self.ohlc["candle_length"] >= 10 * avg_order_length].tolist()
        for x in block_orders:
            last_close = self.ohlc.iloc[x-1]["low"]
            blk_close = self.ohlc.iloc[x]["high"]
            if last_close < blk_close:
                self.buyEntryRegions.append((last_close, blk_close))
            else:
                self.sellEntryRegions.append((self.ohlc.iloc[x]["low"], self.ohlc.iloc[x-1]["low"]))

    def __setBuyEntryRegion__(self, buy_regions):
        self.buyEntryRegions.extend(buy_regions)

    def __setSellEntryRegion__(self, sell_price):
        self.sellEntryRegions.extend(sell_price)

    def dataFetcher(self, time_frame=5, number_of_candles=500):
        """
            This is a function that fetches past 500 candlesticks data at an x-minute time frame
            :param time_frame: Time in minutes to fetch data for.
            :param number_of_candles: Number of candles to fetch data for
            :return: A pandas data frame containing the data of last 1000 candlesticks
            Dataframe columns: time, open, high, low, close, tick_volume, spread, real_volume
        """
        if time_frame == 5:
            time_frame = mt5.TIMEFRAME_M5
        elif time_frame == 15:
            time_frame = mt5.TIMEFRAME_M15
        elif time_frame == 30:
            time_frame = mt5.TIMEFRAME_M30
        elif time_frame == 60:
            time_frame = mt5.TIMEFRAME_H1
        else:
            return
        rates = mt5.copy_rates_from_pos(self.symbol, time_frame, 0, number_of_candles)
        rates_df = pd.DataFrame(rates, columns=['time', 'open', 'high', 'low', 'close', 'tick_volume', 'spread', 'real_volume'])
        rates_df["time"] = pd.to_datetime(rates_df["time"], unit="s")
        self.ohlc = rates_df

    def __checkBlockRegion__(self):
        latest_price = self.ohlc.iloc[-1]["open"]
        for x in self.buyEntryRegions:
            if x[0] <= latest_price <= x[1]:
                return "BUY"
        for x in self.sellEntryRegions:
            if x[0] <= latest_price <= x[1]:
                return "SELL"
        return None

    #### Open Pending Orders ####

    def openPendingBuyStop(self, buy_stop_price, stop_loss_percent=5, take_profit_percent=3, lot_size=0.01):
        request = {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": self.symbol,
            "volume": lot_size,
            "type": mt5.ORDER_TYPE_BUY_STOP,
            "price": buy_stop_price,
            "sl": buy_stop_price * (1 - stop_loss_percent / 100),
            "tp": buy_stop_price * (1 + take_profit_percent / 100),
            "deviation": 30,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC
        }
        order = mt5.order_send(request)

    def openPendingBuyLimit(self, buy_limit_price, stop_loss_percent=5, take_profit_percent=3, lot_size=0.01):
        request = {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": self.symbol,
            "volume": lot_size,
            "type": mt5.ORDER_TYPE_BUY_LIMIT,
            "price": buy_limit_price,
            "sl": buy_limit_price * (1 - stop_loss_percent / 100),
            "tp": buy_limit_price * (1 + take_profit_percent / 100),
            "deviation": 30,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC
        }
        order = mt5.order_send(request)

    def openPendingSellStop(self, sell_stop_price, stop_loss_percent=5, take_profit_percent=3, lot_size=0.01):
        request = {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": self.symbol,
            "volume": lot_size,
            "type": mt5.ORDER_TYPE_SELL_STOP,
            "price": sell_stop_price,
            "sl": sell_stop_price * (1 + stop_loss_percent / 100),
            "tp": sell_stop_price * (1 - take_profit_percent / 100),
            "deviation": 30,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC
        }
        order = mt5.order_send(request)

    def openPendingSellLimit(self, sell_limit_price, stop_loss_percent=5, take_profit_percent=3, lot_size=0.01):
        request = {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": self.symbol,
            "volume": lot_size,
            "type": mt5.ORDER_TYPE_SELL_LIMIT,
            "price": sell_limit_price,
            "sl": sell_limit_price * (1 + stop_loss_percent / 100),
            "tp": sell_limit_price * (1 - take_profit_percent / 100),
            "deviation": 30,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC
        }
        order = mt5.order_send(request)

    def __placePendingOrders__(self):
        orders = mt5.orders_get(symbol=self.symbol)
        for order in orders:
            req = {
                "order": order.ticket,
                "action": mt5.TRADE_ACTION_REMOVE
            }
            mt5.order_send(req)
        cur_price = mt5.symbol_info_tick(self.symbol).ask
        for price in self.buyEntryRegions:
            if cur_price <= price[0]:
                self.openPendingBuyStop(price[0])
            elif cur_price >= price[1]:
                self.openPendingBuyLimit(price[0])
        for price in self.sellEntryRegions:
            if cur_price <= price[0]:
                self.openPendingSellLimit(price[1])
            elif cur_price >= price[1]:
                self.openPendingSellStop(price[1])

    def __stochRSICalculator__(self):
        min_data_1 = pd.DataFrame(mt5.copy_rates_from_pos(self.symbol, mt5.TIMEFRAME_M1, 0, 200))
        min_data_5 = pd.DataFrame(mt5.copy_rates_from_pos(self.symbol, mt5.TIMEFRAME_M5, 0, 100))
        min_data_15 = pd.DataFrame(mt5.copy_rates_from_pos(self.symbol, mt5.TIMEFRAME_M15, 0, 50))
        rsi_1 = abstract.STOCHRSI(min_data_1)
        rsi_5 = abstract.STOCHRSI(min_data_5)
        rsi_15 = abstract.STOCHRSI(min_data_15)

        trend_points = 0

        for i in range(1, 4):
            if rsi_5.iloc[-1 * i]["fastd"] <= 20:
                trend_points -= 10
            elif rsi_5.iloc[-1 * i]["fastd"] >= 80:
                trend_points += 10

            if rsi_15.iloc[-1 * i]["fastd"] <= 20:
                trend_points -= 2
            elif rsi_15.iloc[-1 * i]["fastd"] >= 80:
                trend_points += 2

            if rsi_1.iloc[-1 * i]["fastd"] <= 20:
                trend_points -= 5
            elif rsi_1.iloc[-1 * i]["fastd"] >= 80:
                trend_points += 5

        if trend_points >= 7:
            return "BUY"

        if trend_points <= -7:
            return "SELL"

        else:
            return "WAIT"

    def __volumeTrend__(self):
        data = self.ohlc[-1:-7:-1]
        points = 0
        catch = 0
        for x in range(-1, -6, -1):
            if data.iloc[x]["tick_volume"] - data.iloc[x-1]["tick_volume"] <= 0:
                points += 1
            elif catch <= 2:
                catch += 1
            else:
                break
        if points >= 3:
            return True
        return False

    def __MACDCalculator__(self):
        macd = abstract.MACD(self.ohlc)
        macd.columns = ["macd", "signal", "hist"]
        macd.dropna(inplace=True)
        trend_points = 0
        for i in range(1, 6):
            hist = macd.iloc[-1 * i]["hist"]
            if hist < 0:
                trend_points -= 1
            elif hist > 0:
                trend_points += 1
        if trend_points >= 3:
            return "SELL"
        elif trend_points <= -3:
            return "BUY"
        return "WAIT"

    def __getMargin__(self, order_type, volume):
        if order_type == "BUY":
            order = mt5.ORDER_TYPE_BUY
            price = mt5.symbol_info(self.symbol).ask
        else:
            order = mt5.ORDER_TYPE_SELL
            price = mt5.symbol_info(self.symbol).bid

        margin = mt5.order_calc_margin(order, self.symbol, volume, price)
        return margin

    def __ATRCalculator__(self):
        atr = abstract.ATR(self.ohlc)
        atr.dropna(inplace=True)
        return atr[-1:-11:-1].mean()


    @staticmethod
    def __getAccountFreeMargin__():
        return 0.8 * mt5.account_info().margin_free

    def __SlTpCalculator__(self, atr, order_type, volume):
        # 10 points = 1 pip
        # 10000 pips = 1 USD
        buy_price = mt5.symbol_info_tick(self.symbol).ask
        sell_price = mt5.symbol_info_tick(self.symbol).bid
        points = mt5.symbol_info(self.symbol).point
        pip = points * 10
        if order_type == "BUY":
            sl = buy_price - (atr * 2)
            tp = sell_price + (atr * 1.5)
        else:
            tp = buy_price - (atr * 2)
            sl = sell_price + (atr * 1.5)
        return sl, tp

    def run(self):
        print("Market watch")
        while True:
            self.dataFetcher()
            self.__findBlockOrders__()
            self.__placePendingOrders__()
            # block = self.__checkBlockRegion__()
            if self.buy_order_open and self.sell_order_open:
                print("Max orders open")
                positions = mt5.positions_get(symbol=self.symbol)
                print(positions)
                self.buy_order_open = False
                self.sell_order_open = False
                for pos in positions:
                    if pos.type == 0:
                        self.buy_order_open = True
                    elif pos.type == 1:
                        self.sell_order_open = True
            else:
                if self.__volumeTrend__():
                    votes = []
                    votes.extend([self.__stochRSICalculator__()] * 10)
                    buy = votes.count("BUY")
                    sell = votes.count("SELL")
                    if buy >= 7 and not self.buy_order_open:
                        min_vol = mt5.symbol_info(self.symbol).volume_min
                        if self.__getMargin__("BUY", min_vol) <= self.__getAccountFreeMargin__():
                            atr = self.__ATRCalculator__()
                            sl, tp = self.__SlTpCalculator__(atr, "BUY", min_vol)
                            new_order = threading.Thread(target=OrderManager, args=(self.symbol, "BUY", sl,  tp), kwargs={"volume": min_vol})
                            new_order.start()
                            self.buy_order_open = True
                        else:
                            print("Not enough margin to place order")
                        print("Control to main")
                    elif sell >= 7 and not self.sell_order_open:
                        min_vol = mt5.symbol_info(self.symbol).volume_min
                        if self.__getMargin__("BUY", min_vol) <= self.__getAccountFreeMargin__():
                            atr = self.__ATRCalculator__()
                            sl, tp = self.__SlTpCalculator__(atr, "SELL", min_vol)
                            new_order = threading.Thread(target=OrderManager, args=(self.symbol, "SELL", sl, tp))
                            new_order.start()
                            self.sell_order_open = True
                        else:
                            print("Not enough margin to place order")
                        print("Control to main")
                    else:
                        print("market not good")
                else:
                    print("market not ideal")
            time.sleep(30)