import re
import discord
import requests

from config import *

client = discord.Client()

PREFIX = '!'

url = 'https://api.coingecko.com/api/v3/coins/list'
coins = requests.get(url).json()
COINS = { ii['symbol']: ii['id'] for ii in coins }

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
        elif msg == "img":
            print ('---------------')
            await client.send_file(message.channel, '../img/Hopetoun_falls.jpg')

client.run(TOKEN)
