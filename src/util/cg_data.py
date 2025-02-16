##> Imports
# > Standard libaries
from __future__ import annotations
from typing import Optional, List
import numbers

# > Third party libraries
from pycoingecko import CoinGeckoAPI
import cloudscraper
from bs4 import BeautifulSoup
import pandas as pd

# Local dependencies
import util.vars
from util.vars import stables
from util.tv_data import tv
from util.formatting import format_change

cg = CoinGeckoAPI()
scraper = cloudscraper.create_scraper()


def get_crypto_info(ids):
    if len(ids) > 1:
        id = None
        best_vol = 0
        coin_dict = None
        for symbol in ids.values:
            # Catch potential errors
            try:
                coin_info = cg.get_coin_by_id(symbol)
                if "usd" in coin_info["market_data"]["total_volume"]:
                    volume = coin_info["market_data"]["total_volume"]["usd"]
                    if volume > best_vol:
                        best_vol = volume
                        id = symbol
                        coin_dict = coin_info
            except Exception:
                pass

    else:
        id = ids.values[0]
        # Try in case the CoinGecko API does not work
        try:
            coin_dict = cg.get_coin_by_id(id)
        except Exception:
            return None, None

    return coin_dict, id


def get_coin_vol(coin_dict: dict) -> float:
    if "total_volume" in coin_dict["market_data"].keys():
        if "usd" in coin_dict["market_data"]["total_volume"].keys():
            return coin_dict["market_data"]["total_volume"]["usd"]
        else:
            return 1


def get_coin_price(coin_dict: dict) -> float:
    if "current_price" in coin_dict["market_data"].keys():
        if "usd" in coin_dict["market_data"]["current_price"].keys():
            return coin_dict["market_data"]["current_price"]["usd"]
        else:
            return 0


def get_coin_exchanges(coin_dict: dict) -> tuple[str, list]:
    base = None
    exchanges = []
    if "tickers" in coin_dict.keys():
        for info in coin_dict["tickers"]:
            if "base" in info.keys():
                # Somtimes the base is a contract instead of ticker
                if base == None:
                    # > 7, because $KOMPETE
                    if not (info["base"].startswith("0X") or len(info["base"]) > 7):
                        base = info["base"]

            if "market" in info.keys():
                exchanges.append(info["market"]["name"])

    return base, exchanges


def get_info_from_dict(coin_dict: dict):
    if coin_dict:
        if "market_data" in coin_dict.keys():
            volume = get_coin_vol(coin_dict)
            price = get_coin_price(coin_dict)

            change = None
            if "price_change_percentage_24h" in coin_dict["market_data"].keys():
                if isinstance(
                    coin_dict["market_data"]["price_change_percentage_24h"],
                    numbers.Number,
                ):
                    change = round(
                        coin_dict["market_data"]["price_change_percentage_24h"], 2
                    )

            # Get the exchanges
            base, exchanges = get_coin_exchanges(coin_dict)

            return volume, price, change, exchanges, base
    return 0, None, None, None, None


async def get_coin_info(
    ticker: str,
) -> Optional[tuple[float, str, List[str], float, str, str]]:
    """
    Gets the volume, website, exchanges, price, and change of the coin.
    This can only be called maximum 50 times per minute.

    Parameters
    ----------
    ticker : str
        The ticker of the coin.

    Returns
    -------
    float
        The volume of the coin.
    str
        The website of the coin.
    list[str]
        The exchanges of the coin.
    float
        The price of the coin.
    str
        The 24h price change of the coin.
    str
        The base symbol of the coin, e.g. BTC, ETH, etc.
    """

    id = change = None
    total_vol = 0
    exchanges = []
    change = "N/A"

    # Remove formatting from ticker input
    if ticker not in stables:
        for stable in stables:
            if ticker.endswith(stable):
                ticker = ticker[: -len(stable)]

    # Get the id of the ticker
    # Check if the symbol exists
    coin_dict = None
    if ticker in util.vars.cg_db["symbol"].values:
        # Check coin by symbol, i.e. "BTC"
        coin_dict, id = get_crypto_info(
            util.vars.cg_db[util.vars.cg_db["symbol"] == ticker]["id"]
        )

        # Get the information from the dictionary
        if coin_dict:
            total_vol, price, change, exchanges, base = get_info_from_dict(coin_dict)

    # Try other methods if the information sucks
    if total_vol < 50000 or exchanges == [] or change == "N/A":
        # As a second options check the TradingView data
        price, perc_change, volume, exchange, website = await tv.get_tv_data(
            ticker, "crypto"
        )
        if volume != 0:
            return (
                volume,
                website,
                exchange,
                price,
                format_change(perc_change) if perc_change else "N/A",
                ticker,
            )

        # Third option is to check by id
        elif ticker.lower() in util.vars.cg_db["id"].values:
            coin_dict, id = get_crypto_info(
                util.vars.cg_db[util.vars.cg_db["id"] == ticker.lower()]["id"]
            )

        # Fourth option is to check by name, i.e. "Bitcoin"
        elif ticker in util.vars.cg_db["name"].values:
            coin_dict, id = get_crypto_info(
                util.vars.cg_db[util.vars.cg_db["name"] == ticker]["id"]
            )

        # Get the information from the dictionary
        total_vol, price, change, exchanges, base = get_info_from_dict(coin_dict)

    # remove duplicates and suffix 'exchange'
    if exchanges:
        exchanges = [x.lower().replace(" exchange", "") for x in exchanges]
        exchanges = list(set(exchanges))

    # Look into this!
    if total_vol != 0 and base == None:
        print("No base symbol found for:", ticker)
        base = ticker

    # Return the information
    return (
        total_vol,
        f"https://coingecko.com/en/coins/{id}"
        if id
        else "https://coingecko.com/en/coins/id_not_found",
        exchanges,
        price,
        format_change(change) if change else "N/A",
        base,
    )


async def get_trending_coins() -> pd.DataFrame:
    """
    Gets the trending coins on CoinGecko without using their API.

    Returns
    -------
    DataFrame
        Symbol
            The tickers of the trending coins, formatted with the website.
        Price
            The prices of the trending coins.
        % Change
            The 24h price changes of the trending coins.
        Volume
            The volumes of the trending coins.
    """

    html = scraper.get("https://www.coingecko.com/en/watchlists/trending-crypto").text

    soup = BeautifulSoup(html, "html.parser")

    try:
        table = soup.find(
            "table", class_="sort table mb-0 text-sm text-lg-normal table-scrollable"
        )

        data = []
        for tr in table.find_all("tr"):
            coin_data = {}

            for td_count, td in enumerate(tr.find_all("td")):
                if td_count == 2:
                    ticker = td.find("a").text.split("\n")[-3]
                    website = f"https://www.coingecko.com{td.find('a').get('href')}"
                    coin_data["Symbol"] = f"[{ticker.upper()}]({website})"

                if td_count == 3:
                    price = td.find("span").text.replace("$", "").replace(",", "")
                    try:
                        coin_data["Price"] = float(price)
                    except Exception:
                        coin_data["Price"] = 0

                if td_count == 5:
                    change = td.find("span").text.replace("%", "")
                    try:
                        coin_data["% Change"] = float(change)
                    except Exception:
                        coin_data["% Change"] = 0

                if td_count == 7:
                    volume = td.find("span").text.replace("$", "").replace(",", "")
                    try:
                        coin_data["Volume"] = float(volume)
                    except Exception:
                        coin_data["Volume"] = 0

            if coin_data != {}:
                data.append(coin_data)

        return pd.DataFrame(data)

    except Exception:
        print("Error getting trending coingecko coins")
        return pd.DataFrame()


async def get_top_categories():
    html = scraper.get("https://www.coingecko.com/en/categories").text

    soup = BeautifulSoup(html, "html.parser")

    table = soup.find("table", {"class": "sort table tw-mb-0 text-sm table-scrollable"})

    data = []
    for tr in table.find_all("tr")[1:]:
        coin_data = {}

        for i, td in enumerate(tr.find_all("td")):
            # i == 0 -> rank

            if i == 1:
                coin_data["name"] = td.find("a").text
                coin_data["link"] = "https://www.coingecko.com/" + td.find("a")["href"]

            # 24h
            if i == 4:
                coin_data["24h"] = float(td["data-sort"])

            # Market cap
            if i == 6:
                coin_data["market_cap"] = float(td["data-sort"])

            if i == 7:
                coin_data["volume"] = float(td["data-sort"])

        if coin_data != {}:
            data.append(coin_data)

    return pd.DataFrame(data)
