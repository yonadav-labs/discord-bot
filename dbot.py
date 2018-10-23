import re
import discord
import requests

from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
from mpl_finance import candlestick_ohlc

from config import *

client = discord.Client()

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

        match = re.search(r'[cC] (\w+)\s+(\w+)', msg)
        if match:
            fsym = match.group(1).upper()
            tsym = match.group(2).upper()
            url = 'https://min-api.cryptocompare.com/data/histohour?fsym={}&tsym={}&limit=70&aggregate=3'
            url = url.format(fsym, tsym)
            coins = requests.get(url).json()['Data']
            ohlcv = [(mdates.date2num(datetime.utcfromtimestamp(ii['time'])), ii['open'], ii['high'], ii['low'], ii['close'], ii['volumeto']) for ii in coins]
            filename = 'img/{}-{}.png'.format(fsym, tsym)

            fig = plt.figure()
            ax1 = plt.subplot2grid((1,1), (0,0))
            candlestick_ohlc(ax1, ohlcv, width=0.04, colorup='#77d879', colordown='#db3f3f')

            for label in ax1.xaxis.get_ticklabels():
                label.set_rotation(45)

            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            ax1.xaxis.set_major_locator(mticker.MaxNLocator(10))
            ax1.grid(True)
            
            plt.xlabel('Date')
            plt.ylabel('Price')
            plt.title('ARKbot - Image')
            plt.legend()
            plt.subplots_adjust(left=0.09, bottom=0.20, right=0.94, top=0.90, wspace=0.2, hspace=0)
            # plt.show()
            plt.savefig(filename)
            await client.send_file(message.channel, filename)

client.run(TOKEN)
