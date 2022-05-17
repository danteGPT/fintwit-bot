##> Imports
# > Standard libraries
from csv import writer

# > Discord dependencies
import discord
from discord.ext import commands

# > Local dependencies
from util.disc_util import get_channel
from util.vars import config

class On_raw_reaction_add(commands.Cog):
    """
    This class is used to handle the on_raw_reaction_add event.
    You can enable / disable this command in the config, under ["LISTENERS"]["ON_RAW_REACTION_ADD"].

    Methods
    ----------
    on_raw_reaction_add(reaction : discord.RawReactionActionEvent) -> None:
        This function is called when a reaction is added to a message.
    classify_reaction(reaction : discord.RawReactionActionEvent, message : discord.Message) -> None:
        This function gets called if a reaction was used for classifying a tweet.
    highlight(message : discord.Message, user : discord.User) -> None:
        This function gets called if a reaction was used for highlighting a tweet.
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.channel = get_channel(self.bot, config["LISTENERS"]["ON_RAW_REACTION_ADD"]["CHANNEL"])

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, reaction : discord.RawReactionActionEvent) -> None:
        """
        This function is called when a reaction is added to a message.

        Parameters
        ----------
        reaction : discord.RawReactionActionEvent
            The information about the reaction that was added.
            
        Returns
        -------
        None
        """

        # Ignore private messages
        if reaction.guild_id is None:
            return

        try:
            # Load necessary variables
            channel = self.bot.get_channel(reaction.channel_id)
            try:
                message = discord.utils.get(
                    await channel.history(limit=100).flatten(), id=reaction.message_id
                )
            except Exception as e:
                print(f"Error getting channel.history for {channel}. Error:", e)
                return

            if reaction.user_id != self.bot.user.id:
                if (
                    str(reaction.emoji) == "🐻"
                    or str(reaction.emoji) == "🐂"
                    or str(reaction.emoji) == "🦆"
                ):
                    await self.classify_reaction(reaction, message)
                if str(reaction.emoji) == "💸":
                    await self.highlight(message, reaction.member)

        except commands.CommandError as e:
            print(e)

    async def classify_reaction(self, 
                                reaction : discord.RawReactionActionEvent, 
                                message : discord.Message
                               ) -> None:
        """
        This function gets called if a reaction was used for classifying a tweet.

        Parameters
        ----------
        reaction : discord.RawReactionActionEvent
            The information about the reaction that was added.
        message : discord.Message
            The message that the reaction was added to.
            
        Returns
        -------
        None
        """

        with open("data/sentiment_data.csv", "a", newline="") as file:
            writer_object = writer(file)
            if str(reaction.emoji) == "🐻":
                writer_object.writerow(
                    [message.embeds[0].description.replace("\n", " "), -1]
                )
            elif str(reaction.emoji) == "🐂":
                writer_object.writerow(
                    [message.embeds[0].description.replace("\n", " "), 1]
                )
            elif str(reaction.emoji) == "🦆":
                writer_object.writerow(
                    [message.embeds[0].description.replace("\n", " "), 0]
                )

    async def highlight(self, 
                        message : discord.Message, 
                        user : discord.User
                       ) -> None:
        """
        This function gets called if a reaction was used for highlighting a tweet.

        Parameters
        ----------
        message : discord.Message
            The tweet that should be posted in the highlight channel.
        user : discord.User
            The user that added this reaction to the tweet.
            
        Returns
        -------
        None
        """

        # Get the old embed
        e = message.embeds[0]

        # Get the Discord name of the user
        user = str(user).split("#")[0]
        
        e.set_footer(
            text=f"{e.footer.text} | Highlighted by {user}", icon_url=e.footer.icon_url
        )

        await self.channel.send(embed=e)


def setup(bot):
    bot.add_cog(On_raw_reaction_add(bot))
