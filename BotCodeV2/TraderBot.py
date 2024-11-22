import MetaTrader5 as mt5
import pickle
from BotCodeV2.MarketManager import MarketManager
import multiprocessing


class TraderBot:
    symbols = None
    login_code = None
    password = None
    server = None

    def __init__(self):
        print("Starting Trader Bot!")
        with open("BotCodeV2/Data/symbols.txt", "r") as f:
            self.symbols = f.readlines()

        with open("BotCodeV2/Data/secrets.dat", "rb") as f:
            data = pickle.load(f)
            self.login_code = data[0]
            self.password = data[1]
            self.server = data[2]

        mt5.initialize()
        if mt5.account_info() is None:
            if not mt5.login(self.login_code, self.password, self.server):
                print("[-] Login error. Recheck credentials.")
                exit()

        for symbol in self.symbols:
            p = multiprocessing.Process(target=MarketManager, args=(symbol.strip(),))
            p.start()