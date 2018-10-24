import re
import discord
import requests

import numpy as np
import matplotlib
import pylab

from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
from mpl_finance import candlestick_ohlc

from config import *

client = discord.Client()
matplotlib.rcParams.update({'font.size': 9})
MA1 = 12
MA2 = 26
NUM_X = 120
PREFIX = '!'

url = 'https://api.coingecko.com/api/v3/coins/list'
coins = requests.get(url).json()
COINS = { ii['symbol']: ii['id'] for ii in coins }

url = 'https://api.coincap.io/v2/assets'
coins = requests.get(url).json()['data']
RCOINS = { ii['symbol']: { 'rank': ii['rank'], 'market_cap': ii['marketCapUsd'] } for ii in coins }


@client.event
async def on_ready():
    print("The bot is ready!")
    await client.change_presence(game=discord.Game(name="Making a bot"))

def getEmoji(val):
    if val > 0:
        return u'\U0001f440'
    else:
        return u'\U0001f62f'

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if message.content.startswith(PREFIX):
        msg = message.content.strip(PREFIX)
        match = re.search(r'[pP] (\w+)', msg)
        if match:
            symbol = match.group(1).lower()
            if symbol not in COINS:
                res = "```This coin is not listed on exchanges we support 😶```"
            else:
                url = 'https://api.coingecko.com/api/v3/coins/{}?localization=false&sparkline=false'.format(COINS[symbol])
                info = requests.get(url).json()
                res = "```{symbol} = ${usd_price:,.2f} |  {btc_price:.8f} BTC\n1h   {usd_1h: 6.2f}%     {emo_1h}\n24h  {usd_24h: 6.2f}%     {emo_24h}\nVol: ${usd_vol_24h:,.2f} |  {btc_vol_24h:,.8f} BTC```"
                usd_1h = info['market_data']['price_change_percentage_1h_in_currency']['usd']
                usd_24h = info['market_data']['price_change_percentage_24h_in_currency']['usd']
                res = res.format(symbol=symbol.upper(),
                                 usd_price=info['market_data']['current_price']['usd'],
                                 btc_price=info['market_data']['current_price']['btc'],
                                 usd_1h=usd_1h,
                                 usd_24h=usd_24h,
                                 emo_1h=getEmoji(usd_1h),
                                 emo_24h=getEmoji(usd_24h),
                                 usd_vol_24h=info['market_data']['total_volume']['usd'],
                                 btc_vol_24h=info['market_data']['total_volume']['btc'])
            await client.send_message(message.channel, res)

        match = re.search(r'[rR] (\w+)', msg)
        if match:
            symbol = match.group(1).upper()
            if symbol not in RCOINS:
                res = "```This coin is not listed on exchanges we support 😶```"
            else:
                res = "```{} Rank: {}\nMarketCap = ${:,.2f}```"
                res = res.format(symbol, RCOINS[symbol]['rank'], float(RCOINS[symbol]['market_cap'] or 0.0))
            await client.send_message(message.channel, res)

        match = re.search(r'[cC] (\w+)\s+(\w+)\s+(\d+)', msg)
        if match:
            fsym = match.group(1).upper()
            tsym = match.group(2).upper()
            period = int(match.group(3))

            filename = 'img/{}-{}.png'.format(fsym, tsym)
            graphData(fsym, tsym, period, filename)
            await client.send_file(message.channel, filename)

        if msg == 'help':
            res = "```help: show this message.\np <currency>: show price\nr <currency>: show rank\nc <base> <quote> <period>: show chart\n```"
            await client.send_message(message.channel, res)

def rsiFunc(prices, n=14):
    deltas = np.diff(prices)
    seed = deltas[:n+1]
    up = seed[seed>=0].sum()/n
    down = -seed[seed<0].sum()/n
    rs = up/down
    rsi = np.zeros_like(prices)
    rsi[:n] = 100. - 100./(1.+rs)

    for i in range(n, len(prices)):
        delta = deltas[i-1] # cause the diff is 1 shorter

        if delta>0:
            upval = delta
            downval = 0.
        else:
            upval = 0.
            downval = -delta

        up = (up*(n-1) + upval)/n
        down = (down*(n-1) + downval)/n

        rs = up/down
        rsi[i] = 100. - 100./(1.+rs)

    return rsi

def movingaverage(values,window):
    weigths = np.repeat(1.0, window)/window
    smas = np.convolve(values, weigths, 'valid')
    return smas # as a numpy array


def ExpMovingAverage(values, window):
    weights = np.exp(np.linspace(-1., 0., window))
    weights /= weights.sum()
    a =  np.convolve(values, weights, mode='full')[:len(values)]
    a[:window] = a[window]
    return a


def computeMACD(x, slow=26, fast=12):
    """
    compute the MACD (Moving Average Convergence/Divergence) using a fast and slow exponential moving avg'
    return value is emaslow, emafast, macd which are len(x) arrays
    """
    emaslow = ExpMovingAverage(x, slow)
    emafast = ExpMovingAverage(x, fast)
    return emaslow, emafast, emafast - emaslow


def bytespdate2num(fmt, encoding='utf-8'):
    strconverter = mdates.strpdate2num(fmt)
    def bytesconverter(b):
        s = b.decode(encoding)
        return strconverter(s)
    return bytesconverter


def graphData(fsym, tsym, period, filename):
    api = 'minute' if period < 32 else 'hour'
    if api == 'minute':
        wh = 60 * period
        limit = NUM_X if wh >= NUM_X else 70
        aggregate = wh // NUM_X or 1
        xw = 0.0005 * aggregate * 0.65 if aggregate > 1 else 0.0005
    else:
        wh = period
        limit = NUM_X if wh >= NUM_X else 60
        aggregate = wh // NUM_X or 1
        xw = 0.025 * aggregate * 0.65 if aggregate > 1 else 0.025

    url = 'https://min-api.cryptocompare.com/data/histo{}?fsym={}&tsym={}&limit={}&aggregate={}'
    url = url.format(api, fsym, tsym, limit, aggregate)
    # print (wh, limit, aggregate, xw)
    coins = requests.get(url).json()['Data']
    ohlcv = [(mdates.date2num(datetime.utcfromtimestamp(ii['time'])), ii['open'], ii['high'], ii['low'], ii['close'], ii['volumeto']) for ii in coins]

    date = [mdates.date2num(datetime.utcfromtimestamp(ii['time'])) for ii in coins]
    volume = [ii['volumeto'] for ii in coins]
    closep = [ii['close'] for ii in coins]

    Av1 = movingaverage(closep, MA1)
    Av2 = movingaverage(closep, MA2)

    SP = len(date[MA2-1:])
        
    fig = plt.figure(facecolor='#07000d')

    ax1 = plt.subplot2grid((6,4), (0,0), rowspan=4, colspan=4)
    ax1.set_facecolor('#07000d')
    candlestick_ohlc(ax1, ohlcv[-SP:], width=xw, colorup='#53c156', colordown='#ff1717')

    Label1 = str(MA1)+' SMA'
    Label2 = str(MA2)+' SMA'

    ax1.plot(date[-SP:],Av1[-SP:],'#e1edf9',label=Label1, linewidth=1.5)
    ax1.plot(date[-SP:],Av2[-SP:],'#4ee6fd',label=Label2, linewidth=1.5)
    
    ax1.grid(True, color='#eeeeee', linestyle='--', alpha=.3)
    ax1.xaxis.set_major_locator(mticker.MaxNLocator(10))
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M\n%Y-%m-%d'))
    ax1.yaxis.label.set_color("w")
    ax1.spines['bottom'].set_color("#5998ff")
    ax1.spines['top'].set_color("#5998ff")
    ax1.spines['left'].set_color("#5998ff")
    ax1.spines['right'].set_color("#5998ff")
    ax1.tick_params(axis='y', colors='w')
    plt.gca().yaxis.set_major_locator(mticker.MaxNLocator(prune='upper'))
    ax1.tick_params(axis='x', colors='w')
    plt.ylabel('Stock {} and Volume'.format(tsym))

    maLeg = plt.legend(loc=9, ncol=2, prop={'size':7},
               fancybox=True, borderaxespad=0.)
    maLeg.get_frame().set_alpha(0.4)
    textEd = pylab.gca().get_legend().get_texts()
    pylab.setp(textEd[0:5], color = 'w')

    volumeMin = 0
    
    ax0 = plt.subplot2grid((6,4), (4,0), sharex=ax1, rowspan=1, colspan=4)
    ax0.set_facecolor('#07000d')
    rsi = rsiFunc(closep)
    rsiCol = '#c1f9f7'
    posCol = '#386d13'
    negCol = '#8f2020'
    
    ax0.plot(date[-SP:], rsi[-SP:], rsiCol, linewidth=1.5)
    ax0.axhline(70, color=negCol)
    ax0.axhline(30, color=posCol)
    ax0.fill_between(date[-SP:], rsi[-SP:], 70, where=(rsi[-SP:]>=70), facecolor=negCol, edgecolor=negCol, alpha=0.5)
    ax0.fill_between(date[-SP:], rsi[-SP:], 30, where=(rsi[-SP:]<=30), facecolor=posCol, edgecolor=posCol, alpha=0.5)
    ax0.set_yticks([30,70])
    ax0.yaxis.label.set_color("w")
    ax0.spines['bottom'].set_color("#5998ff")
    ax0.spines['top'].set_color("#5998ff")
    ax0.spines['left'].set_color("#5998ff")
    ax0.spines['right'].set_color("#5998ff")
    ax0.tick_params(axis='y', colors='w')
    ax0.tick_params(axis='x', colors='w')
    plt.ylabel('RSI')

    ax1v = ax1.twinx()
    ax1v.fill_between(date[-SP:],volumeMin, volume[-SP:], facecolor='#00ffe8', alpha=.5)
    ax1v.axes.yaxis.set_ticklabels([])
    ax1v.grid(False)
    ###Edit this to 3, so it's a bit larger
    ax1v.set_ylim(0, 3*max(volume))
    ax1v.spines['bottom'].set_color("#5998ff")
    ax1v.spines['top'].set_color("#5998ff")
    ax1v.spines['left'].set_color("#5998ff")
    ax1v.spines['right'].set_color("#5998ff")
    ax1v.tick_params(axis='x', colors='w')
    ax1v.tick_params(axis='y', colors='w')
    ax2 = plt.subplot2grid((6,4), (5,0), sharex=ax1, rowspan=1, colspan=4)
    ax2.set_facecolor('#07000d')
    fillcolor = '#00ffe8'
    nslow = 26
    nfast = 12
    nema = 9
    emaslow, emafast, macd = computeMACD(closep)
    ema9 = ExpMovingAverage(macd, nema)
    ax2.plot(date[-SP:], macd[-SP:], color='#4ee6fd', lw=2)
    ax2.plot(date[-SP:], ema9[-SP:], color='#e1edf9', lw=1)
    ax2.fill_between(date[-SP:], macd[-SP:]-ema9[-SP:], 0, alpha=0.5, facecolor=fillcolor, edgecolor=fillcolor)

    plt.gca().yaxis.set_major_locator(mticker.MaxNLocator(prune='upper'))
    ax2.spines['bottom'].set_color("#5998ff")
    ax2.spines['top'].set_color("#5998ff")
    ax2.spines['left'].set_color("#5998ff")
    ax2.spines['right'].set_color("#5998ff")
    ax2.tick_params(axis='x', colors='w')
    ax2.tick_params(axis='y', colors='w')
    plt.ylabel('MACD', color='w')
    ax2.yaxis.set_major_locator(mticker.MaxNLocator(nbins=5, prune='upper'))
    for label in ax2.xaxis.get_ticklabels():
        label.set_rotation(45)

    plt.suptitle(fsym, color='w')
    plt.setp(ax0.get_xticklabels(), visible=False)
    plt.setp(ax1.get_xticklabels(), visible=False)

    plt.subplots_adjust(left=.15, bottom=.18, right=.94, top=.93, wspace=.20, hspace=0)
    # plt.show()
    fig.savefig(filename,facecolor=fig.get_facecolor())

client.run(TOKEN)

