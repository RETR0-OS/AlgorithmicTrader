import threading
import MetaTrader5 as mt5
from talib import abstract
import pandas as pd
from BotCodeV2.Strategies.scalping import Scalper

class MarketManager:
    symbol = None
    ohlc_data = None
    buy_entry_regions = []
    sell_entry_regions = []
    strategy = None

    def __init__(self, symbol):
        mt5.initialize()
        self.symbol = symbol
        self.strategy = Scalper
        self.manageMarket()

    def __checkMarketOpen__(self):
        symbol_info = mt5.symbol_info(self.symbol).__asdict()
        pass

    def __findBlockOrders__(self):
        self.ohlc_data = pd.DataFrame(mt5.copy_rates_from_pos(self.symbol, mt5.TIMEFRAME_M5, 0, 6), columns=['time', 'open', 'high', 'low', 'close', 'tick_volume', 'spread', 'real_volume'])
        self.ohlc_data["candle_length"] = abs(self.ohlc_data["close"] - self.ohlc_data["open"])
        #print(self.ohlc_data.columns)
        avg_order_length = self.ohlc_data["candle_length"].mean()
        block_orders = self.ohlc_data.index[self.ohlc_data["candle_length"] >= 2 * avg_order_length].tolist()
        for x in block_orders:
            last_close = self.ohlc_data.iloc[x-1]["low"]
            blk_close = self.ohlc_data.iloc[x]["high"]
            if last_close < blk_close:
                self.buy_entry_regions.append((last_close, blk_close))
            else:
                self.sell_entry_regions.append((self.ohlc_data.iloc[x]["low"], self.ohlc_data.iloc[x-1]["low"]))

    def __NATRCalculator__(self):
        natr = abstract.NATR(self.ohlc_data)
        natr.dropna(inplace=True)
        if natr.iloc[-1] >= 0.01 and natr.iloc[-2] >= 0.01:
            return True
        else:
            return False

    def __Aroon__(self):
        aroondf = abstract.AROON(self.ohlc_data, timeperiod=14)
        aroondf.columns = ["aroondown", "aroonup"]
        aroondf.dropna(inplace=True)
        aroon_last11 = aroondf[-1:-12:-1]
        uptrend, downtrend = 0, 0
        for i in range(-1, -12, -1):
            if aroon_last11.iloc[i]["aroondown"] >= 70 and aroon_last11.iloc[i]["aroonup"] <= 30:
                downtrend += 1
            elif aroon_last11.iloc[i]["aroondown"] <= 30 and aroon_last11.iloc[i]["aroonup"] >= 70:
                uptrend += 1
        if uptrend >= 7:
            return "BUY"
        elif downtrend >= 7:
            return "SELL"
        else:
            return "WAIT"

    def __StochRSICalculator__(self):
        ret_df = abstract.STOCHRSI(self.ohlc_data, period=14, fastk_period=5, fastd_period=3, fastd_matype=0)
        ret_df.columns = ["STOCHRSI_k", "STOCHRSI_d"]
        ret_df.dropna(inplace=True)
        rsi_last11 = ret_df[-1:-12:-1]
        rsi_trend = None
        trend_points = 0
        for i in range(-12, -11, -1):
            if rsi_last11[i] > rsi_last11[i-1]:
                if rsi_trend == "INC":
                    trend_points += 1
                else:
                    rsi_trend = "INC"
                    if trend_points == 0:
                        trend_points += 1
                    else:
                        trend_points -= 1
            elif rsi_last11[i] < rsi_last11[i-1]:
                if rsi_trend == "DEC":
                    trend_points += 1
                else:
                    rsi_trend = "DEC"
                    if trend_points == 0:
                        trend_points += 1
                    else:
                        trend_points -= 1

        if rsi_last11.iloc[-1]["STOCHRSI_d"] <= 20 and rsi_trend == "INC" and trend_points >= 6:
            return "BUY"
        elif rsi_last11.iloc[-1]["STOCHRSI_d"] >= 20 and rsi_trend == "DEC" and trend_points >= 6:
            return "SELL"
        else:
            return "WAIT"

    def __MACDCalculator__(self):
        macd = abstract.MACD(self.ohlc_data)
        macd.columns = ["macd", "macdsignal", "macdhist"]
        macd.dropna(inplace=True)

        ##Identify trends
        uptrend_threshold = macd["macdhist"][macd["macdhist"] >= 0][-1:-21:-1].mean()
        downtrend_threshold = macd["macdhist"][macd["macdhist"] <= 0][-1:-21:-1].mean()

        if macd["macdhist"].iloc[-1] < 0 and macd["macdhist"].iloc[-1] <= downtrend_threshold:
            for i in range(-2, -5, -1):
                if not (macd["macdhist"].iloc[i] <= 0 and macd["macdhist"].iloc[-1] <= downtrend_threshold):
                    return "WAIT"
            return "SELL"
        elif macd["macdhist"].iloc[-1] >= 0 and macd["macdhist"].iloc[-1] >= uptrend_threshold:
            for i in range(-2, -5, -1):
                if not (macd["macdhist"].iloc[i] >= 0 and macd["macdhist"].iloc[-1] <= uptrend_threshold):
                    return "WAIT"
            return "BUY"
        else:
            return "WAIT"

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
        rates_df = pd.DataFrame(rates)
        rates_df["time"] = pd.to_datetime(rates_df["time"], unit="s")
        self.ohlc_data =  rates_df

    def manageMarket(self):
        '''while True:
            self.dataFetcher()
            if self.__NATRCalculator__():
                signals = [self.__Aroon__(), self.__StochRSICalculator__(), self.__MACDCalculator__()]
                buy, sell = 0, 0
                for s in signals:
                    if s == "BUY":
                        buy += 1
                    elif s == "SELL":
                        sell += 1
                if buy == 2:
                    print("buy")
                    #place buy order
                    pass
                elif sell == 2:
                    print("sell")
                    #place sell order
                    pass
                else:
                    print("Trade not ideal")
                time.sleep(60)
            else:
                print("ATR not good")
                time.sleep(5*60)

        '''
        self.__findBlockOrders__()
        new_thread = threading.Thread(target=self.strategy, args=(self.symbol, self.buy_entry_regions, self.sell_entry_regions))
        new_thread.start()

