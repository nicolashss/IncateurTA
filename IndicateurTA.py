# -------------------------

# Author: Doom & Oji Wolf & xLuX
# Github : https://github.com/nicolashss/TradingBOT
# Website : https://xlux.xyz/

# -------------------------

import os
import sys

from colorama import init, Fore, Back, Style
from pprint import pprint

from time import sleep, time

from binance.client import Client
from binance.exceptions import BinanceAPIException

import pandas_ta as ta

import json
import math
import time

import telepot

import pandas as pd     # needs pip install
import numpy as np
import matplotlib.pyplot as plt   # needs pip install
from operator import add
from operator import sub

from datetime import datetime

import yaml

from tradingview_ta import TA_Handler, Interval, Exchange
import tradingview_ta

#GLOBAL
Telegram_Start_Command_Triggered = False
Telegram_Pair = "None"
Telegram_TradeAmount = -1.0
Telegram_Leverage = -1
TelegramStopSignal = False
Telegram_LastTradeStop = False
telegram_bot = None
chat_id = None


#CALCULATION AND DATA FUNCTION

def get_data_frame(client, crypto, StartTime, Interval):
    global telegram_bot
    # valid intervals - 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M
    # request historical candle (or klines) data using timestamp from above, interval either every min, hr, day or month
    # starttime = '30 minutes ago UTC' for last 30 mins time
    # e.g. client.get_historical_klines(symbol='ETHUSDTUSDT', '1m', starttime)
    # starttime = '1 Dec, 2017', '1 Jan, 2018'  for last month of 2017
    # e.g. client.get_historical_klines(symbol='BTCUSDT', '1h', "1 Dec, 2017", "1 Jan, 2018")
    starttime = StartTime  # to start for 1 day ago
    interval = Interval
    while True:
        try:
            bars = client_binance.futures_historical_klines(crypto, interval, starttime)
            break
        except Exception as e:
            print(e)
            telegram_bot.sendMessage(chat_id, "[BOT] : Erreur : Je n'arrive pas à récupérer les Bougies de Binance, si ça se reproduit trop de fois à la suite, veuillez me stopper.")
            pass
    #pprint.pprint(bars)
    
    for line in bars:        # Keep only first 5 columns, "date" "open" "high" "low" "close"
        del line[5:]
    df = pd.DataFrame(bars, columns=['date', 'open', 'high', 'low', 'close']) #  2 dimensional tabular data
    #df.set_index('date', inplace=True)
    
    for i in df.columns:
        df[i] = df[i].astype(float)

    df['date'] = pd.to_datetime(df['date'], unit='ms') 
    
    return df

def get_precision(client, symbol):
    global telegram_bot
    try:
        info = client.futures_exchange_info()
    except Exception as e:
        print(e)
        telegram_bot.sendMessage(chat_id, "[BOT] : Erreur : Je n'arrive pas à récupérer la précision de la pair, peut-être un problème d'api, je m'arrête.")
        os.execv(sys.executable, [sys.executable, __file__] + sys.argv)
    
    for x in info['symbols']:
        if x['symbol'] == symbol:
            return x['quantityPrecision'], x['pricePrecision']

def round_decimals_down(number:float, decimals:int=2):
    """
    Returns a value rounded down to a specific number of decimal places.
    """
    if not isinstance(decimals, int):
        raise TypeError("decimal places must be an integer")
    elif decimals < 0:
        raise ValueError("decimal places has to be 0 or more")
    elif decimals == 0:
        return math.floor(number)

    factor = 10 ** decimals
    return math.floor(number * factor) / factor

def getUSDTBalanceSTR():
    global telegram_bot
    try:
        acc_balance = client_binance.futures_account_balance()
    except Exception as e:
        print(e)
        telegram_bot.sendMessage(chat_id, "[BOT] : Erreur : Je n'arrive pas à récupérer le montant de ta balance USDT, peut-être un problème d'api, je m'arrête.")
        os.execv(sys.executable, [sys.executable, __file__] + sys.argv)
    
    for i in range(len(acc_balance)) :
        if acc_balance[i]['asset'] == 'USDT':
            return acc_balance[i]['balance']

    return 'NULL'

#CALCULATION AN DATA FUNCTION END

def get_API():

    try:
        yaml_file = open("./api.yaml", 'r')
    except:
        print(Fore.RED + "[ERREUR] :")
        print(Fore.WHITE + "Le fichier api.yaml n'existe pas ou n'est pas au bon endroit")
        os.execv(sys.executable, [sys.executable, __file__] + sys.argv)
    
    

    yaml_content = yaml.safe_load(yaml_file)
    return yaml_content




def handle_TELEGRAM_COMMAND(msg):
    
    global Telegram_Start_Command_Triggered
    global Telegram_Pair
    global Telegram_TradeAmount
    global Telegram_Leverage
    global TelegramStopSignal
    global Telegram_LastTradeStop
    global telegram_bot
    global chat_id

    chat_id = msg['chat']['id']
    command = msg['text']

    if command == 'command start':
        if Telegram_Pair == "None" :
            telegram_bot.sendMessage(chat_id, "[BOT] : Tu n'as pas rentré de pair, je ne peux pas démarrer")
        elif Telegram_TradeAmount == -1.0:
            telegram_bot.sendMessage(chat_id, "[BOT] : Tu n'as pas rentré de mise, je ne peux pas démarrer")
        elif Telegram_Leverage == -1:
            telegram_bot.sendMessage(chat_id, "[BOT] : Tu n'as pas rentré de multiplicateur, je ne peux pas démarrer")
        else :
            telegram_bot.sendMessage(chat_id, "[BOT] : Je démarre.")
            Telegram_Start_Command_Triggered = True

    elif command == 'command info':
        message = "[BOT] : La pair actuelle est : " + str(Telegram_Pair) + ". La mise actuelle est : " + str(Telegram_TradeAmount) + ". Le multiplicateur actuelle est : " + str(Telegram_Leverage) + "."
        telegram_bot.sendMessage(chat_id, message)
        #os.execv(sys.executable, [sys.executable, __file__] + sys.argv)

    elif command == 'command stop':
        telegram_bot.sendMessage(chat_id, "[BOT] : Je m'arrête. à plus dans le bus")
        #os.execv(sys.executable, [sys.executable, __file__] + sys.argv)
        TelegramStopSignal = True

    elif command == 'command ping':
        telegram_bot.sendMessage(chat_id, "[BOT] : pong")

    elif command.find('command set_pair') != -1 :
        arguments = command[17:]
        Telegram_Pair = str(arguments)
        message = "[BOT] : La pair est mise à jour : " + str(Telegram_Pair)
        telegram_bot.sendMessage(chat_id, message)

    elif command.find('command set_trade_amount') != -1 :
        arguments = command[25:]
        Telegram_TradeAmount = float(arguments)
        message = "[BOT] : La mise est mise à jour : " + str(Telegram_TradeAmount)
        telegram_bot.sendMessage(chat_id, message)

    elif command.find('command set_leverage') != -1 :
        arguments = command[21:]
        Telegram_Leverage = int(arguments)
        message = "[BOT] : Le multiplicateur est mis à jour : " + str(Telegram_Leverage)
        telegram_bot.sendMessage(chat_id, message)

    elif command == 'command last_trade_stop':
        telegram_bot.sendMessage(chat_id, "[BOT] Ok, je m'arrête à la fin du trade :) (ou de suite si y a pas de trade en cours)")
        Telegram_LastTradeStop = True

def HA(df):
    df['HA_close']=(df['open']+ df['high']+ df['low']+df['close'])/4

    idx = df.index.name
    df.reset_index(inplace=True)

    for i in range(0, len(df)):
        if i == 0:
            df.at[i, 'HA_open'] = ((df.at[i, 'open'] + df.at[i, 'close']) / 2)
        else:
            df.at[i, 'HA_open'] = ((df.at[i - 1, 'HA_open'] + df.at[i - 1, 'HA_close']) / 2)

    if idx:
        df.set_index(idx, inplace=True)

    df['HA_high']=df[['HA_open','HA_close','high']].max(axis=1)
    df['HA_low']=df[['HA_open','HA_close','low']].min(axis=1)
    return df
    


if __name__ == "__main__":

    init()

    api_yaml = get_API()

    binance_api_is_here = False
    binance_secret_is_here = False
    binance_telegram_bot_token_is_here = False
    if "binance_api" in api_yaml:
        binance_api_is_here = True
    if "binance_secret" in api_yaml:
        binance_secret_is_here = True
    if "telegram_bot_token" in api_yaml:
        binance_telegram_bot_token_is_here = True

    if binance_api_is_here == False :
        print(Fore.RED + "[ERREUR] :")
        print(Fore.WHITE + "Il manque -binance_api- dans le fichier api.yaml")
        os.execv(sys.executable, [sys.executable, __file__] + sys.argv)
    if binance_secret_is_here == False :
        print(Fore.RED + "[ERREUR] :")
        print(Fore.WHITE + "Il manque -binance_secret- dans le fichier api.yaml")
        os.execv(sys.executable, [sys.executable, __file__] + sys.argv)
    if binance_telegram_bot_token_is_here == False :
        print(Fore.RED + "[ERREUR] :")
        print(Fore.WHITE + "Il manque -telegram_bot_token- dans le fichier api.yaml")
        os.execv(sys.executable, [sys.executable, __file__] + sys.argv)



    client_binance = Client(api_yaml['binance_api'], api_yaml['binance_secret'])
    telegram_bot = telepot.Bot(api_yaml['telegram_bot_token'])
    handler = TA_Handler(
    symbol="GMTUSDTPERP",
    exchange="BINANCE",
    screener="crypto",
    interval="5m",
    timeout=None
    )
    telegram_bot.message_loop(handle_TELEGRAM_COMMAND)
    print(Fore.RED + "[BOT] : ")
    print(Fore.YELLOW + "Commandes du BOT (a envoyer depuis Telegram) :")
    print(Fore.GREEN + "command start :")
    print(Fore.WHITE + "Lance le bot.")
    print(Fore.GREEN + "command info :")
    print(Fore.WHITE + "Donne les paramétrages actuelle du bot.")
    print(Fore.GREEN +"command stop : ")
    print(Fore.WHITE + "Stop le bot.")
    print(Fore.GREEN +"command last_trade_stop : ")
    print(Fore.WHITE + "Termine le dernier trade et arrête le bot,")
    print("si aucun trade n'est en cours, le bot se stop directement.")
    print(Fore.GREEN +"command set_pair -Pair- : ")
    print(Fore.WHITE + "Permet de choisir la pair, ")
    print("une fois que le bot est lancé, ce n'est plus modifiable. (exemple : command set_pair BTCUSDT)")
    print(Fore.GREEN +"command set_trade_amount -Amount- : ")
    print(Fore.WHITE + "Permet de choisir le montant de la mise,")
    print("une fois que le bot est lancé, ce n'est plus modifiable. (exemple : command set_trade_amount 50.5)")
    print(Fore.GREEN +"command set_leverage -Leverage- : ")
    print(Fore.WHITE + "Permet de choisir le multiplicateur de trade, prenez soin de le mettre avant de lancer le bot,")
    print("une fois que le bot est lancé, ce n'est plus modifiable, faite attention de mettre un multiplicateur accepté par votre compte.")
    print("(exemple : command set_leverage 10)")
    print(Fore.GREEN +"command ping : ")
    print(Fore.WHITE + "Si le bot tourne toujours, il renvoit un message 'pong'")

    print(Fore.YELLOW + "Veuillez parametrer la Pair et le montant de la mise depuis Telegram")
    print(Fore.YELLOW + "Puis vous pouver lancer le bot")

    

    while(Telegram_Start_Command_Triggered == False):
        i = 0



    #PARAMETER
    leverage = Telegram_Leverage
    pair = Telegram_Pair


    actualBalance = getUSDTBalanceSTR()
    print("Balance Amount in Futures :")
    print(actualBalance)
    message = "[BOT] : Voici ta balance : " + str(actualBalance) + " USDT"
    telegram_bot.sendMessage(chat_id, message)


    try:
        client_binance.futures_change_leverage(symbol=pair, leverage=int(leverage))
    except Exception as e:
        print(e)
        telegram_bot.sendMessage(chat_id, "[BOT] : Erreur : Je n'arrive pas à changer le multiplicateur, peut-être un problème d'api, je m'arrête.")
        os.execv(sys.executable, [sys.executable, __file__] + sys.argv)

    
    precision, pricePrecision = get_precision(client_binance, pair)
    print("Pair and Precision :")
    print(pair + " " + str(precision))


    isLongTake = False
    isShortTake = False
    FirstPoint = False
    lastPricetrade = None
    TradeOrderTime = 0
    TradeOrderTimeSave = 0
    TradeCloseTime = 0
    LogPNL = False

    StopLossPrice = None
    TakeProfitPrice = None

    counterToNotice = 0

    quantityUSDTTrade = Telegram_TradeAmount
    pair = Telegram_Pair

    TradeDateTake = ' '
    TradeDateStop = ' '
    LastDate = ' '

    
    lastRedID = -1
    lastGreenID = -1

    lastNumberRed = 0
    lastNumberGreen = 0
    trendCandle = 1

    firstLoop = True;

    BoolToPlaceSL_TP = False

    while True:

        DataCrypto = get_data_frame(client_binance, pair, '12 hours ago UTC', '5m')

        DataCrypto = HA(DataCrypto)
        
        srcCloseElement = len(DataCrypto['close'])-1
        
        if LastDate != DataCrypto['date'][i]:
            if lastGreenID > 0:
                lastGreenID -= 1
            if lastRedID > 0:
                lastRedID -= 1

        if (DataCrypto['HA_open'][srcCloseElement-1] < DataCrypto['HA_close'][srcCloseElement-1]) and LastDate != DataCrypto['date'][i]:
            
            lastGreenID = srcCloseElement-1


        elif (DataCrypto['HA_open'][srcCloseElement-1] > DataCrypto['HA_close'][srcCloseElement-1]) and LastDate != DataCrypto['date'][i]:
            
            lastRedID = srcCloseElement-1
            


        if (isLongTake == True or isShortTake == True):
            ordersSLTP = client_binance.futures_get_open_orders(symbol=pair)
            if len(ordersSLTP) == 1:
                if isLongTake == True:
                    while True:
                        try:
                            positionInfo = client_binance.futures_position_information(symbol=pair, timestamp=int(time.time() * 1000))
                            break
                        except Exception as e:
                            print(e)
                            telegram_bot.sendMessage(chat_id, "[BOT] : Erreur : Je n'arrive pas à récupérer la position du trade, si ça se reproduit plus de 3 fois à la suite, veuillez me stopper, et allez couper le trade à la main.")
                            pass

                    while True:
                        try:
                            res = client_binance.futures_create_order(symbol=pair, quantity=float(positionInfo[0].get('positionAmt')), side="SELL", type="MARKET", timestamp=int(time.time() * 1000))
                            break
                        except Exception as e:
                            print(e)
                            telegram_bot.sendMessage(chat_id, "[BOT] : Erreur : Je n'arrive pas à close le LONG en cours, si ça se reproduit plus de 3 fois à la suite, veuillez me stopper, et allez couper le trade à la main.")
                            pass
                elif isShortTake == True:
                    while True:
                        try:
                            positionInfo = client_binance.futures_position_information(symbol=pair, timestamp=int(time.time() * 1000))
                            break
                        except Exception as e:
                            print(e)
                            telegram_bot.sendMessage(chat_id, "[BOT] : Erreur : Je n'arrive pas à récupérer la position du trade, si ça se reproduit plus de 3 fois à la suite, veuillez me stopper, et allez couper le trade à la main.")
                            pass
                    quan = float(positionInfo[0].get('positionAmt')) * -1.0
                    while True:
                        try:
                            res = client_binance.futures_create_order(symbol=pair, quantity=quan, side="BUY", type="MARKET", timestamp=int(time.time() * 1000))
                            break
                        except Exception as e:
                            print(e)
                            telegram_bot.sendMessage(chat_id, "[BOT] : Erreur : Je n'arrive pas à close le SHORT en cours, si ça se reproduit plus de 3 fois à la suite, veuillez me stopper, et allez couper le trade à la main.")
                            pass

                    isLongTake = False
                    isShortTake = False
                    LogPNL = True

            elif len(ordersSLTP) == 0:
                isLongTake = False
                isShortTake = False
                LogPNL = True


        if TelegramStopSignal == True:
            os.execv(sys.executable, [sys.executable, __file__] + sys.argv)

        if LogPNL == True :
            pnl_history = client_binance.futures_income_history(symbol=pair, incomeType="REALIZED_PNL")
            income = 0.0
            for i in range(len(pnl_history)):
                if int(TradeOrderTime) <= int(pnl_history[i]['time']):
                    income += float(pnl_history[i]['income'])
            print("PNL : ")
            print(income)
            message = "[BOT] : Bop, un trade est terminé. Voici le PNL = " + str(income) + " et voici ta Balance : " + str(getUSDTBalanceSTR())
            
            while True:
                try:
                    telegram_bot.sendMessage(chat_id, message)
                    break
                except Exception as e:
                    print(e)
                    pass
            if Telegram_LastTradeStop == True:
                
                while True:
                    try:
                        telegram_bot.sendMessage(chat_id, "[BOT] : Le trade est fini, je m'arrête ! ")
                        break
                    except Exception as e:
                        print(e)
                        pass
                os.execv(sys.executable, [sys.executable, __file__] + sys.argv)
            LogPNL = False
            quantityUSDTTrade = Telegram_TradeAmount
            pair = Telegram_Pair

        if Telegram_LastTradeStop == True and isLongTake == False and isShortTake == False:
            while True:
                try:
                    telegram_bot.sendMessage(chat_id, "[BOT] : Pas de trade en cours, je m'arrête ! ")
                    break
                except Exception as e:
                    print(e)
                    pass
            
            os.execv(sys.executable, [sys.executable, __file__] + sys.argv)
                

        while True:
            try:
                pairPrice = float(client_binance.futures_symbol_ticker(symbol=pair)['price'])
                break
            except Exception as e:
                print(e)
                telegram_bot.sendMessage(chat_id, "[BOT] : Erreur : Je n'arrive pas à récupérer le prix de la pair, si ça se reproduit trop de fois à la suite, veuillez me stopper.")
                pass


        quantityCryptoToBuy = quantityUSDTTrade * leverage / pairPrice
        quantityCryptoToBuy = round_decimals_down(quantityCryptoToBuy, int(precision))

        analysis = handler.get_analysis()

        if isLongTake == True and (analysis.moving_averages['RECOMMENDATION'] == 'BUY' or analysis.moving_averages['RECOMMENDATION'] == 'NEUTRAL' or analysis.moving_averages['RECOMMENDATION'] == 'SELL' or analysis.moving_averages['RECOMMENDATION'] == 'STRONG_SELL'):
            while True:
                try:
                    positionInfo = client_binance.futures_position_information(symbol=pair, timestamp=int(time.time() * 1000))
                    break
                except Exception as e:
                    print(e)
                    telegram_bot.sendMessage(chat_id, "[BOT] : Erreur : Je n'arrive pas à récupérer la position du trade, si ça se reproduit plus de 3 fois à la suite, veuillez me stopper, et allez couper le trade à la main.")
                    pass

            while True:
                try:
                    res = client_binance.futures_create_order(symbol=pair, quantity=float(positionInfo[0].get('positionAmt')), side="SELL", type="MARKET", timestamp=int(time.time() * 1000))
                    break
                except Exception as e:
                    print(e)
                    telegram_bot.sendMessage(chat_id, "[BOT] : Erreur : Je n'arrive pas à close le LONG en cours, si ça se reproduit plus de 3 fois à la suite, veuillez me stopper, et allez couper le trade à la main.")
                    pass
            message = "[BOT][Placement SL/TP LONG] : J'ai fermé le trade, l'open était supérieur au TakeProfit. Prix d'entrée : " + str(positionInfo[0].get('entryPrice')) + " Open : " + str(DataCrypto['open'][srcCloseElement]) + " TakeProfit: " + str(TakeProfitPrice)
            while True:
                try:
                    telegram_bot.sendMessage(chat_id, message)
                    break
                except Exception as e:
                    print(e)
                    pass
            isLongTake = False

        elif isShortTake == True and (analysis.moving_averages['RECOMMENDATION'] == 'SELL' or analysis.moving_averages['RECOMMENDATION'] == 'NEUTRAL' or analysis.moving_averages['RECOMMENDATION'] == 'BUY' or analysis.moving_averages['RECOMMENDATION'] == 'STRONG_BUY'):
            while True:
                try:
                    positionInfo = client_binance.futures_position_information(symbol=pair, timestamp=int(time.time() * 1000))
                    break
                except Exception as e:
                    print(e)
                    telegram_bot.sendMessage(chat_id, "[BOT] : Erreur : Je n'arrive pas à récupérer la position du trade, si ça se reproduit plus de 3 fois à la suite, veuillez me stopper, et allez couper le trade à la main.")
                    pass
            quan = float(positionInfo[0].get('positionAmt')) * -1.0
            while True:
                try:
                    res = client_binance.futures_create_order(symbol=pair, quantity=quan, side="BUY", type="MARKET", timestamp=int(time.time() * 1000))
                    break
                except Exception as e:
                    print(e)
                    telegram_bot.sendMessage(chat_id, "[BOT] : Erreur : Je n'arrive pas à close le SHORT en cours, si ça se reproduit plus de 3 fois à la suite, veuillez me stopper, et allez couper le trade à la main.")
                    pass
            message = "[BOT][Placement SL/TP SHORT] : J'ai fermé le trade, l'open était inférieur au TakeProfit. Prix d'entrée : " + str(positionInfo[0].get('entryPrice')) + " Open : " + str(DataCrypto['open'][srcCloseElement]) + " TakeProfit: " + str(TakeProfitPrice)
            while True:
                try:
                    telegram_bot.sendMessage(chat_id, message)
                    break
                except Exception as e:
                    print(e)
                    pass
            isShortTake = False
        
        if firstLoop == False:
            if isLongTake == False and isShortTake == False:
                if (analysis.moving_averages['RECOMMENDATION'] == 'STRONG_BUY' and (analysis.oscillators['RECOMMENDATION'] == 'BUY' or analysis.oscillators['RECOMMENDATION'] == 'NEUTRAL' or analysis.oscillators['RECOMMENDATION'] == 'STRONG_BUY') and
                    (lastAnalysis.moving_averages['RECOMMENDATION'] == 'SELL' or lastAnalysis.moving_averages['RECOMMENDATION'] == 'STRONG_SELL' or lastAnalysis.moving_averages['RECOMMENDATION'] == 'NEUTRAL') and
                     (lastAnalysis.oscillators['RECOMMENDATION'] == 'SELL' or lastAnalysis.oscillators['RECOMMENDATION'] == 'STRONG_SELL' or lastAnalysis.oscillators['RECOMMENDATION'] == 'NEUTRAL')):
                    
                    StopLossPrice = DataCrypto['HA_low'][lastRedID]
                    if float(DataCrypto['open'][srcCloseElement]) - ((float(DataCrypto['open'][srcCloseElement]) * 3.0)/100) <= float(DataCrypto['HA_low'][lastRedID]) and StopLossPrice < DataCrypto['open'][srcCloseElement]:

                        StopLossPrice = round_decimals_down(StopLossPrice, int(pricePrecision))
                        TakeProfitPrice =  DataCrypto['open'][srcCloseElement] + (((DataCrypto['HA_low'][lastRedID] - DataCrypto['open'][srcCloseElement]) * 2.0) * -1.0)
                        TakeProfitPrice = round_decimals_down(TakeProfitPrice, int(pricePrecision));

                        while True:
                            try:
                                res = client_binance.futures_create_order(symbol=pair, side='BUY', type='MARKET', quantity=quantityCryptoToBuy, reduceOnly=False)
                                TradeOrderTime = res['updateTime']
                                break
                            except Exception as e:
                                print(e)
                                telegram_bot.sendMessage(chat_id, "[BOT] : Erreur : Je n'arrive pas à prendre un LONG, si ça se reproduit plus de 3 fois à la suite, veuillez me stopper, et allez couper le trade à la main.")
                                pass
                        
                        lastPricetrade = pairPrice
                        message = "[BOT] : J'ai pris un Trade Long. "
                        TradeDateTake = DataCrypto['date'][srcCloseElement]
                        while True:
                            try:
                                telegram_bot.sendMessage(chat_id, message)
                                break
                            except Exception as e:
                                print(e)
                                pass
                        
                        #print(res)

                        while True:
                            try:
                                positionInfo = client_binance.futures_position_information(symbol=pair, timestamp=int(time.time() * 1000))
                                break
                            except Exception as e:
                                print(e)
                                telegram_bot.sendMessage(chat_id, "[BOT] : Erreur : Je n'arrive pas à récupérer la position du trade, si ça se reproduit plus de 3 fois à la suite, veuillez me stopper, et allez couper le trade à la main.")
                                pass

                        while True:
                            try:
                                res = client_binance.futures_create_order(symbol=pair, side='SELL', type='STOP_MARKET', timeInForce='GTE_GTC', quantity=positionInfo[0].get('positionAmt'), reduceOnly=True, stopPrice=StopLossPrice, workingType='MARK_PRICE')
                                
                                break
                            except Exception as e:
                                print(e)
                                telegram_bot.sendMessage(chat_id, "[BOT] : Erreur : Je n'arrive pas à prendre un StopLoss, si ça se reproduit plus de 3 fois à la suite, veuillez me stopper, et allez couper le trade à la main.")
                                client_binance.futures_create_order(symbol=pair, quantity=float(positionInfo[0].get('positionAmt')), side="SELL", type="MARKET", timestamp=int(time.time() * 1000))
                                break
                        time.sleep(1)
                        while True:
                            try:
                                res = client_binance.futures_create_order(symbol=pair, side='SELL', type='TAKE_PROFIT_MARKET', timeInForce='GTE_GTC', quantity=positionInfo[0].get('positionAmt'), reduceOnly=True, stopPrice=TakeProfitPrice, workingType='MARK_PRICE')
                                
                                break
                            except Exception as e:
                                print(e)
                                telegram_bot.sendMessage(chat_id, "[BOT] : Erreur : Je n'arrive pas à placer un TakeProfit, si ça se reproduit plus de 3 fois à la suite, veuillez me stopper, et allez couper le trade à la main.")
                                client_binance.futures_create_order(symbol=pair, quantity=float(positionInfo[0].get('positionAmt')), side="SELL", type="MARKET", timestamp=int(time.time() * 1000))
                                break
                        message = "[BOT][Placement SL/TP LONG] : J'ai placé le StopLoss et le TakeProfit. Prix d'entrée : " + str(positionInfo[0].get('entryPrice')) + " StopLoss : " + str(StopLossPrice) + " TakeProfit: " + str(TakeProfitPrice)
                        
                        while True:
                            try:
                                telegram_bot.sendMessage(chat_id, message)
                                break
                            except Exception as e:
                                print(e)
                                pass
                        


                        isLongTake = True
                        BoolToPlaceSL_TP = True
                    
                    
                elif (analysis.moving_averages['RECOMMENDATION'] == 'STRONG_SELL' and (analysis.oscillators['RECOMMENDATION'] == 'SELL' or analysis.oscillators['RECOMMENDATION'] == 'NEUTRAL' or analysis.oscillators['RECOMMENDATION'] == 'STRONG_SELL') and
                    (lastAnalysis.moving_averages['RECOMMENDATION'] == 'BUY' or lastAnalysis.moving_averages['RECOMMENDATION'] == 'STRONG_BUY' or lastAnalysis.moving_averages['RECOMMENDATION'] == 'NEUTRAL') and
                     (lastAnalysis.oscillators['RECOMMENDATION'] == 'BUY' or lastAnalysis.oscillators['RECOMMENDATION'] == 'STRONG_BUY' or lastAnalysis.oscillators['RECOMMENDATION'] == 'NEUTRAL')):
                    
                    StopLossPrice = DataCrypto['HA_high'][lastGreenID]
                    if float(DataCrypto['open'][srcCloseElement]) + ((float(DataCrypto['open'][srcCloseElement]) * 3.0)/100) >= float(DataCrypto['HA_high'][lastGreenID]) and StopLossPrice > DataCrypto['open'][srcCloseElement]:

                        StopLossPrice = round_decimals_down(StopLossPrice, int(pricePrecision))
                        TakeProfitPrice =  DataCrypto['open'][srcCloseElement] - (((DataCrypto['HA_high'][lastGreenID] - DataCrypto['open'][srcCloseElement]) * 2.0))
                        TakeProfitPrice = round_decimals_down(TakeProfitPrice, int(pricePrecision));
                        while True:
                            try:
                                res = client_binance.futures_create_order(symbol=pair, side='SELL', type='MARKET', quantity=quantityCryptoToBuy, reduceOnly=False)
                                TradeOrderTime = res['updateTime']
                                break
                            except Exception as e:
                                print(e)
                                telegram_bot.sendMessage(chat_id, "[BOT] : Erreur : Je n'arrive pas à prendre un LONG, si ça se reproduit plus de 3 fois à la suite, veuillez me stopper, et allez couper le trade à la main.")
                                pass
                        
                        lastPricetrade = pairPrice
                        message = "[BOT] : J'ai pris un Trade Short. "
                        TradeDateTake = DataCrypto['date'][srcCloseElement]
                        while True:
                            try:
                                telegram_bot.sendMessage(chat_id, message)
                                break
                            except Exception as e:
                                print(e)
                                pass
                        
                        #print(res)

                        while True:
                            try:
                                positionInfo = client_binance.futures_position_information(symbol=pair, timestamp=int(time.time() * 1000))
                                break
                            except Exception as e:
                                print(e)
                                telegram_bot.sendMessage(chat_id, "[BOT] : Erreur : Je n'arrive pas à récupérer la position du trade, si ça se reproduit plus de 3 fois à la suite, veuillez me stopper, et allez couper le trade à la main.")
                                pass
                        quan = float(positionInfo[0].get('positionAmt')) * -1.0
                        while True:
                            try:
                                res = client_binance.futures_create_order(symbol=pair, side='BUY', type='STOP_MARKET', timeInForce='GTE_GTC', quantity=quan, reduceOnly=True, stopPrice=StopLossPrice, workingType='MARK_PRICE')
                                
                                break
                            except Exception as e:
                                print(e)
                                telegram_bot.sendMessage(chat_id, "[BOT] : Erreur : Je n'arrive pas à prendre un StopLoss, si ça se reproduit plus de 3 fois à la suite, veuillez me stopper, et allez couper le trade à la main.")
                                quan = float(positionInfo[0].get('positionAmt')) * -1.0
                                client_binance.futures_create_order(symbol=pair, quantity=quan, side="BUY", type="MARKET", timestamp=int(time.time() * 1000))
                                break
                        time.sleep(1)
                        while True:
                            try:
                                res = client_binance.futures_create_order(symbol=pair, side='BUY', type='TAKE_PROFIT_MARKET', timeInForce='GTE_GTC', quantity=quan, reduceOnly=True, stopPrice=TakeProfitPrice, workingType='MARK_PRICE')
                                
                                break
                            except Exception as e:
                                print(e)
                                telegram_bot.sendMessage(chat_id, "[BOT] : Erreur : Je n'arrive pas à placer un TakeProfit, si ça se reproduit plus de 3 fois à la suite, veuillez me stopper, et allez couper le trade à la main.")
                                quan = float(positionInfo[0].get('positionAmt')) * -1.0
                                client_binance.futures_create_order(symbol=pair, quantity=quan, side="BUY", type="MARKET", timestamp=int(time.time() * 1000))
                                break
                        message = "[BOT][Placement SL/TP SHORT] : J'ai placé le StopLoss et le TakeProfit. Prix d'entrée : " + str(positionInfo[0].get('entryPrice')) + " StopLoss : " + str(StopLossPrice) + " TakeProfit: " + str(TakeProfitPrice)
                        while True:
                            try:
                                telegram_bot.sendMessage(chat_id, message)
                                break
                            except Exception as e:
                                print(e)
                                pass
                        

                        isShortTake = True
                        BoolToPlaceSL_TP = True

        lastAnalysis = analysis
        firstLoop = True
                
        LastDate = DataCrypto['date'][i]
        time.sleep(1)
