from __future__ import annotations
from typing import List, Optional
import traceback

import aiohttp
import discord
from discord.ext import commands
from discord.ext.tasks import loop

from util.vars import config
from util.disc_util import get_channel, get_tagged_users, get_webhook
from util.tweet_embed import make_tweet_embed
from util.parse_tweet import parse_tweet
from util.get_tweet import get_tweet


class Timeline(commands.Cog):
    """
    The main Class of this project. This class is responsible for streaming tweets from the Twitter API.
    It can be configured in the config.yaml file under ["LOOPS"]["TIMELINE"].
    """

    def __init__(self, bot: commands.Bot) -> None:
        """Initializes the Timeline class.

        Parameters
        ----------
        bot : commands.Bot
            The bot object from discord.py
        """
        self.bot = bot

        charts_channel = config["LOOPS"]["TIMELINE"]["CHARTS_CHANNEL"]
        text_channel = config["LOOPS"]["TIMELINE"]["TEXT_CHANNEL"]

        # Set the channels
        self.set_channels("STOCKS", charts_channel, text_channel)
        self.set_channels("CRYPTO", charts_channel, text_channel)
        self.set_channels("FOREX", charts_channel, text_channel)

        # These channels are not crypto or stocks
        self.set_channels("IMAGES")
        self.set_channels("OTHER")
        self.set_channels("NEWS")

        # Get all text channels
        self.all_txt_channels.start()
        self.get_latest_tweet.start()

    def set_channels(
        self,
        name: str,
        charts_channel: str = None,
        text_channel: str = None,
    ) -> None:
        """Set channels for each category.

        Parameters
        ----------
        name : str
            The name of the category.
        charts_channel : str
            The name of the charts channel.
        text_channel : str
            The name of the text channel.
        """
        if config["LOOPS"]["TIMELINE"][name]["ENABLED"]:
            if name in ["STOCKS", "CRYPTO", "FOREX"]:
                self.__dict__[f"{name.lower()}_charts_channel"] = get_channel(
                    self.bot, charts_channel, config["CATEGORIES"][name]
                )
                self.__dict__[f"{name.lower()}_text_channel"] = get_channel(
                    self.bot, text_channel, config["CATEGORIES"][name]
                )
            elif name in ["IMAGES", "OTHER"]:
                self.__dict__[f"{name.lower()}_channel"] = get_channel(
                    self.bot, config["LOOPS"]["TIMELINE"][name]["CHANNEL"]
                )
            elif name in ["NEWS"]:
                self.__dict__[f"{name.lower()}_channel"] = get_channel(
                    self.bot,
                    config["LOOPS"]["TIMELINE"][name]["CHANNEL"],
                    config["CATEGORIES"]["TWITTER"],
                )

                if config["LOOPS"]["TIMELINE"]["NEWS"]["CRYPTO"]["ENABLED"]:
                    self.crypto_news_channel = get_channel(
                        self.bot,
                        config["LOOPS"]["TIMELINE"]["NEWS"]["CHANNEL"],
                        config["CATEGORIES"]["CRYPTO"],
                    )

    @loop(hours=1)
    async def all_txt_channels(self) -> None:
        """Gets all the text channels as Discord object and the names of the channels."""
        self.following_ids = []

        text_channel_list = []
        text_channel_names = []

        # Loop over all the text channels
        for server in self.bot.guilds:
            for channel in server.channels:
                if str(channel.type) == "text":
                    text_channel_list.append(channel)
                    text_channel_names.append(channel.name.split("┃")[1])

        # Set the class variables
        self.text_channels = text_channel_list
        self.text_channel_names = text_channel_names

    @loop(minutes=5)
    async def get_latest_tweet(self) -> None:
        """Fetches the latest tweets."""
        tweets = await get_tweet()

        # Loop from oldest to newest tweet
        for tweet in reversed(tweets):
            tweet = tweet["content"]

            # Skip if the tweet is not a timeline item
            if tweet["entryType"] != "TimelineTimelineItem":
                continue

            await self.on_data(tweet, update_tweet_id=True)

    async def on_data(self, tweet: dict, update_tweet_id: bool = False) -> None:
        """This method is called whenever data is received from the stream.

        Parameters
        ----------
        tweet : dict
            The raw tweet data.
        update_tweet_id : bool, optional
            Whether or not to update the tweet ID, by default False
        """
        formatted_tweet = parse_tweet(tweet, update_tweet_id=update_tweet_id)

        if formatted_tweet is not None:
            (
                text,
                user_name,
                user_screen_name,
                user_img,
                tweet_url,
                media,
                tickers,
                hashtags,
                e_title,
                media_types,
            ) = formatted_tweet

            e, category, base_symbols = await make_tweet_embed(
                text,
                user_name,
                user_img,
                tweet_url,
                media,
                tickers,
                hashtags,
                e_title,
                media_types,
                self.bot,
            )

            # Upload the tweet to the Discord.
            await self.upload_tweet(e, category, media, user_screen_name, base_symbols)

    async def upload_tweet(
        self,
        e: discord.Embed,
        category: Optional[str],
        media: List[str],
        user_screen_name: str,
        tickers: List[str],
    ) -> None:
        """Uploads tweet in the dedicated Discord channel.

        Parameters
        ----------
        e : discord.Embed
            The Tweet as a Discord embed object.
        category : str, optional
            The category of the tweet, used to decide which Discord channel it should be uploaded to.
        media : list
            The images contained in this tweet.
        user_screen_name : str
            The user that posted this tweet.
        tickers : list
            The list of tickers contained in this tweet.
        """
        user_channel = None

        # Default channel
        channel = self.other_channel

        # Check if there is a user specific channel
        if user_screen_name.lower() in self.text_channel_names:
            user_channel = self.text_channels[
                self.text_channel_names.index(user_screen_name.lower())
            ]

        # News posters (Do not post news in other channels)
        if user_screen_name in config["LOOPS"]["TIMELINE"]["NEWS"]["FOLLOWING"]:
            channel = self.news_channel
        elif (
            user_screen_name
            in config["LOOPS"]["TIMELINE"]["NEWS"]["CRYPTO"]["FOLLOWING"]
        ):
            channel = self.crypto_news_channel
        else:
            channel = self.get_channel_based_on_category(category, media)

        await self.post_tweet(channel, e, media, tickers, user_channel, category)

    def get_channel_based_on_category(
        self, category: Optional[str], media: List[str]
    ) -> discord.abc.GuildChannel:
        """Get the Discord channel based on the category of the tweet.

        Parameters
        ----------
        category : str, optional
            The category of the tweet.
        media : list
            The images contained in this tweet.

        Returns
        -------
        discord.abc.GuildChannel
            The Discord channel.
        """
        if category is None:
            channel = self.images_channel if media else self.other_channel
        else:
            channel_type = "charts" if media else "text"
            channel = self.__dict__[f"{category}_{channel_type}_channel"]

        return channel

    async def post_tweet(
        self,
        channel: discord.abc.GuildChannel,
        e: discord.Embed,
        media: List[str],
        tickers: List[str],
        user_channel: Optional[discord.abc.GuildChannel],
        category: Optional[str],
    ) -> None:
        """Formats the tweet and passes it to upload_tweet().

        Parameters
        ----------
        channel : discord.abc.GuildChannel
            The Discord channel where the tweet should be posted.
        e : discord.Embed
            The Tweet as a Discord embed object.
        media : list
            The images contained in this tweet.
        tickers : list
            The list of tickers contained in this tweet.
        user_channel : discord.abc.GuildChannel, optional
            The user-specific Discord channel.
        category : str, optional
            The category of the tweet.
        """
        msgs = []

        try:
            # Create a list of image embeds, max 10 images per post
            image_e = [e] + [
                discord.Embed(url=e.url).set_image(url=img) for img in media[1:10]
            ]

            # If there are multiple images to be sent, use a webhook to send them all at once
            if len(image_e) > 1:
                msg = await self.make_and_send_webhook(channel, tickers, image_e)
                msgs.append(msg)

                if user_channel:
                    msg = await self.make_and_send_webhook(
                        user_channel, tickers, image_e
                    )
                    msgs.append(msg)

            else:
                # Use the normal send function
                msg = await channel.send(content=get_tagged_users(tickers), embed=e)
                msgs.append(msg)

                if user_channel:
                    msg = await user_channel.send(
                        content=get_tagged_users(tickers), embed=e
                    )
                    msgs.append(msg)

            # Do this for every message
            try:
                for msg in msgs:
                    # Post in highlight channel
                    await msg.add_reaction("💸")
                    # Send to user DM
                    await msg.add_reaction("❤️")

                    if category != None:
                        await msg.add_reaction("🐂")
                        await msg.add_reaction("🦆")
                        await msg.add_reaction("🐻")

            except discord.DiscordServerError:
                print("Could not add reaction to message")

        except aiohttp.ClientConnectionError:
            print("Connection Error posting tweet on timeline")

        except Exception as error:
            print("Error posting tweet on timeline", error)
            print(traceback.format_exc())

    async def make_and_send_webhook(
        self,
        channel: discord.abc.GuildChannel,
        tickers: List[str],
        image_e: List[discord.Embed],
    ) -> discord.Message:
        """Creates and sends a webhook.

        Parameters
        ----------
        channel : discord.abc.GuildChannel
            The Discord channel.
        tickers : list
            The list of tickers contained in this tweet.
        image_e : list
            The images contained in this tweet.

        Returns
        -------
        discord.Message
            The Discord message.
        """
        webhook = await get_webhook(channel)

        # Wait so we can use this message as reference
        msg = await webhook.send(
            content=get_tagged_users(tickers),
            embeds=image_e,
            username="FinTwit",
            wait=True,
            avatar_url=self.bot.user.avatar.url,
        )

        return msg


def setup(bot: commands.Bot) -> None:
    """
    This is a necessary method to make the cog loadable.

    Returns
    -------
    None
    """
    bot.add_cog(Timeline(bot))
