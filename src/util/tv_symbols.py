# This file is used to store all the symbols used in the TV module.
# Use format EXCHANGE:INDEX for TradingView symbols
crypto_indices = [
    "CRYPTOCAP:TOTAL",
    "CRYPTOCAP:TOTAL2",
    "CRYPTOCAP:TOTAL3",
    "CRYPTOCAP:BTC.D",
    "CRYPTOCAP:ETH.D",
    "CRYPTOCAP:OTHERS.D",
    "CRYPTOCAP:TOTALDEFI.D",
    "CRYPTOCAP:USDT.D",
    "CRYPTOCAP:USDC.D",
]

# https://www.tradingview.com/markets/currencies/indices-all/
forex_indices = [
    "TVC:DXY",
    "TVC:EXY",
    "TVC:BXY",
    "TVC:JXY",
]

US_bonds = [
    "TVC:US01MY",
    "TVC:US02MY",
    "TVC:US03MY",
    "TVC:US06MY",
    "TVC:US01Y",
    "TVC:US02Y",
    "TVC:US03Y",
    "TVC:US05Y",
    "TVC:US07Y",
    "TVC:US10Y",
    "TVC:US20Y",
    "TVC:US30Y",
]

EU_bonds = [
    "TVC:EU03MY",
    "TVC:EU06MY",
    "TVC:EU09MY",
    "TVC:EU01Y",
    "TVC:EU02Y",
    "TVC:EU03Y",
    "TVC:EU04Y",
    "TVC:EU05Y",
    "TVC:EU06Y",
    "TVC:EU07Y",
    "TVC:EU08Y",
    "TVC:EU09Y",
    "TVC:EU10Y",
    "TVC:EU15Y",
    "TVC:EU20Y",
    "TVC:EU25Y",
    "TVC:EU30Y",
]

# https://www.tradingview.com/markets/cfds/quotes-world-indices/
# https://www.tradingview.com/markets/indices/quotes-major/
stock_indices = [
    "AMEX:SPY",
    "NASDAQ:NDX",
    "USI:PCC",
    "USI:PCCE",
    "TVC:VIX",
    "TVC:SPX",
]

all_forex_indices = forex_indices + EU_bonds + US_bonds
