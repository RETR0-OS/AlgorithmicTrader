import MetaTrader5 as mt5
import pandas as pd
import time
from talib import abstract

class OrderManager:
    symbol = None
    order_type = None
    order_id = None

    def __init__(self, symbol, order_type, stop_loss, take_profit, volume=0.01):
        mt5.initialize()
        self.symbol = symbol
        self.order_type = order_type
        self.volume = volume

        if self.order_type == "BUY":
            print("Buy order placed")
            self.placeMarketBuyOrder(stop_loss, take_profit, lot_size=self.volume)
            self.marketWatchBuy()
        elif self.order_type == "SELL":
            print("Sell order placed")
            self.placeMarketSellOrder(stop_loss, take_profit, lot_size=self.volume)
            self.marketWatchSell()

    #### Place Market Orders ####
    def placeMarketBuyOrder(self, stop_loss, take_profit, lot_size=0.01):
        """
            This function places an immediately executed buy order in the MT5 application.
            :param take_profit:
            :param stop_loss:
            :param stop_loss_percent: The percentage of stop loss that can be tolerated (should be ideally more than take profit).
            :param take_profit_percent: The percentage of maximum profit to take
            :param lot_size: Number of lots of the shares to buy
            :return: None
        """
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": lot_size,
            "type": mt5.ORDER_TYPE_BUY,
            "price": mt5.symbol_info_tick(self.symbol).ask,
            "tp": take_profit,
            "sl": stop_loss,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
            "Deviation": 30
        }
        buy_order = mt5.order_send(request)._asdict()
        print(buy_order)
        self.order_id = buy_order["order"]

    def placeMarketSellOrder(self, stop_loss, take_profit, lot_size=0.01):
        """
            This function places an immediately executed sell order in the MT5 application.
            
            :param stop_loss: The stop loss that can be tolerated (should be ideally more than take profit).
            :param take_profit: The maximum profit to take
            :param lot_size: Number of lots of the shares to buy
            :return: None
        """
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": lot_size,
            "type": mt5.ORDER_TYPE_SELL,
            "price": mt5.symbol_info_tick(self.symbol).bid,
            "sl": stop_loss,
            "tp": take_profit,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
            "deviation": 30
        }
        sell_order = mt5.order_send(request)._asdict()
        print(sell_order)
        self.order_id = sell_order["order"]

    #### Close Open Orders ####

    def closeBuyOrder(self):
        """
            This function closes a currently open buy order
            :return: None
        """
        mt5.Close(symbol=self.symbol, comment=f"Closed buy order for {self.symbol}", ticket=self.order_id)

    def closeSellOrder(self):
        """
            This function closes a currently open sell order
            :return: None
        """
        mt5.Close(symbol=self.symbol, comment=f"Closed sell order for {self.symbol}", ticket=self.order_id)

    def openPendingBuyStopLimit(self, buy_stop_limit_price, stop_loss_percent=5, take_profit_percent=3,
                                lot_size=0.01):
        request = {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": self.symbol,
            "volume": lot_size,
            "type": mt5.ORDER_TYPE_BUY_STOP_LIMIT,
            "price": buy_stop_limit_price,
            "sl": buy_stop_limit_price * (1 - stop_loss_percent / 100),
            "tp": buy_stop_limit_price * (1 + take_profit_percent / 100),
            "deviation": 30,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC
        }
        order = mt5.send_order(request)
        print(order)
        self.order_id = order["order"]

    def openPendingSellStopLimit(self, sell_stop_limit_price, stop_loss_percent=5, take_profit_percent=3,
                                 lot_size=0.01):
        request = {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": self.symbol,
            "volume": lot_size,
            "type": mt5.ORDER_TYPE_SELL_STOP_LIMIT,
            "price": sell_stop_limit_price,
            "sl": sell_stop_limit_price * (1 + stop_loss_percent / 100),
            "tp": sell_stop_limit_price * (1 - take_profit_percent / 100),
            "deviation": 30,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC
        }
        order = mt5.send_order(request)
        print(order)
        self.order_id = order["order"]

    #### Remove Pending Orders ####
    def removePendingOrder(self):
        pending_orders = mt5.orders_get(ticket=self.order_id)
        if pending_orders is not None:
            request = {
                "action": mt5.TRADE_ACTION_REMOVE,
                "order": self.order_id
            }
            mt5.order_send(request)

    def modifyBuyStopLossTakeProfit(self, new_sl, new_tp):
        position = mt5.positions_get(ticket=self.order_id)[0]
        if position is not None:
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "position": self.order_id,
                "sl": new_sl,
                "tp": new_tp
            }
            req = mt5.order_send(request)
            print(req)

    def modifySellStopLossTakeProfit(self, new_sl, new_tp):
        position = mt5.positions_get(ticket=self.order_id)[0]
        if position is not None:
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "position": self.order_id,
                "sl": new_sl,
                "tp": new_tp
            }
            req = mt5.order_send(request)
            print(req)

    def dataFetcher(self, time_frame=1, number_of_candles=500):
        """
            This is a function that fetches past 500 candlesticks data at an x-minute time frame
            :param time_frame: Time in minutes to fetch data for.
            :param number_of_candles: Number of candles to fetch data for
            :return: A pandas data frame containing the data of last 1000 candlesticks
            Dataframe columns: time, open, high, low, close, tick_volume, spread, real_volume
        """
        if time_frame == 5:
            time = mt5.TIMEFRAME_M5
        elif time_frame == 15:
            time = mt5.TIMEFRAME_M15
        elif time_frame == 30:
            time = mt5.TIMEFRAME_M30
        elif time_frame == 1:
            time = mt5.TIMEFRAME_M1
        else:
            return
        rates = mt5.copy_rates_from_pos(self.symbol, time, 0, number_of_candles)
        rates_df = pd.DataFrame(rates)
        rates_df["time"] = pd.to_datetime(rates_df["time"], unit="s")
        return rates_df

    def __ATRCalculator__(self):
        ohlc = pd.DataFrame(mt5.copy_rates_from_pos(self.symbol, mt5.TIMEFRAME_M5, 0, 100))
        atr = abstract.ATR(ohlc)
        atr.dropna(inplace=True)
        return atr[-1:-11:-1].mean()

    def __getMargin__(self):
        order_type = mt5.ORDER_TYPE_BUY if self.order_type=="BUY" else mt5.ORDER_TYPE_SELL
        margin = mt5.order_calc_margin(order_type, self.symbol, self.volume, mt5.symbol_info_tick(self.symbol).ask)
        return margin
    
    def __SlTpCalculator__(self, order, atr, order_type):
        # 10 points = 1 pip
        # 10000 pips = 1 USD
        points = mt5.symbol_info(self.symbol).point
        margin = self.__getMargin__()
        tick = mt5.symbol_info_tick(self.symbol)
        pip = points * 10
        if order_type == "BUY":
            sl = order.price_open + margin + (1.5 * atr)
            tp = order.tp + (atr * 2)
        else:
            tp = order.tp - (atr * 2)
            sl = order.price_open - margin - (1.5 * atr)
        return sl, tp

    def marketWatchBuy(self):
        while True:
            try:
                position = mt5.positions_get(ticket=self.order_id)[0]
                if position != ():
                    tp = position.tp
                    sl = position.sl
                    current_price = position.price_current
                    profit = position.profit
                    atr = self.__ATRCalculator__()
                    if profit >= 0.8 * (tp - current_price):
                        sl, tp = self.__SlTpCalculator__(position, atr, "BUY")
                        self.modifyBuyStopLossTakeProfit(sl, tp)
                time.sleep(1)
            except IndexError:
                break

    def marketWatchSell(self):
        while True:
            try:
                position = mt5.positions_get(ticket=self.order_id)[0]
                if position != ():
                    tp = position.tp
                    sl = position.sl
                    current_price = position.price_current
                    profit = position.profit
                    atr = self.__ATRCalculator__()
                    if profit >= 0.6 * (current_price - tp):
                        print("changing profits!")
                        sl, tp = self.__SlTpCalculator__(position, atr, "BUY")
                        self.modifyBuyStopLossTakeProfit(sl, tp)
                time.sleep(1)
            except IndexError:
                break
