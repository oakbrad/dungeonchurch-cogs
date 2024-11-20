import discord
from discord import Embed
from redbot.core import commands, Config, checks, app_commands
from redbot.core.utils.chat_formatting import error, question, success
from .oracle import oracle
from .game_views import GameInitView, GameStateView
from .game_embeds import game_state_embed
import pydealer

from pprint import pformat

class TheQuietYear(commands.Cog):
    __author__ = "DM Brad"
    __version__ = "0.1"

    def __init__(self, bot):
        self.bot = bot
        self.active_games = {} # track active games under [channel_id]
        self.game_state = {} # store the state for each game under [channel_id]
        self.bot.add_view(GameStateView(self))

        # default settings
        self.config = Config.get_conf(
            self, identifier=4206662013, force_registration=True
        )
        default_guild_settings = {
            "max_players": 4,
            "round_timeout":  1440, # in minutes, 1440=24 hours
            "player_role": None # placeholder for role ID
        }
        self.config.register_guild(**default_guild_settings)
    #
    # PLAYER SLASH COMMANDS
    #
    @app_commands.command()
    async def startgame(self, interaction: discord.Interaction) -> None:
        """ Start The Quiet Year in the current channel/thread."""
        # Ensure only game per channel
        if interaction.channel.id in self.active_games:
            await interaction.response(error("`A game is already active here. Try a different channel, or start a thread if you want to start a new game.`"), ephemeral=True)
            return
        
        # Retrieve Game Settings
        max_players = int(await self.config.guild(interaction.guild).max_players())
        round_timeout = int(await self.config.guild(interaction.guild).turn_timeout())

        # Initialize the game state
        self.active_games[interaction.channel.id] = True
        self.game_state[interaction.channel.id] = {
            "game_init_message": None,      # Message ID [int] of GameInitView
            "game_state_message": None,     # Message ID [int] of GameStateView
            "max_players": max_players,     # Max players from settings [int]
            "players": [],                  # list of user IDs [int]
            "scarcities": [],               # list of Scarcities [str]
            "abundances": [],               # list of Abundances [str]
            "projects": [],                 # List of active projects [{player_id: int, project: str, duration: int}]
            "contempt_pool": 20,            # Start with 20 Contempt Tokens [int]
            "contempt": {},                 # Track player contempt {player_id: int}
            "round": 0,                     # Number of rotations of all players [int]
            "week": 0,                      # Number of cumulative turns (weeks) [int]
            "current_turn": [],             # Current turn tracker, list of player_id [int]
            "round_timeout": round_timeout, # Turn timeout [int] in minutes, from settings
            "deck": None                    # pydealer [Deck] shuffled by create_deck()
        }

        # Create embeds
        init_embed = Embed(
            title="Let's play...",
            description="# 🗺️ [The Quiet Year](<https://buriedwithoutceremony.com/the-quiet-year>)\n ### *A Map-Drawing Game by Alder Avery*\n"
                        "> *For a long time, we were at war with The Jackals. Now, finally, we've driven them off, and we're left with this: a year of relative peace. One quiet year, with which to build our community up and learn again how to work together. Come Winter, the Frost Shepherds will arrive and we might not survive the encounter. This is when the game will end. But we don't know about that yet. What we know is that right now, in this moment, there is an opportunity to build something.*\n\n",
            color=0xff0000
        )
        # Convert round_timeout to human readable
        hours = round_timeout // 60
        remaining_minutes = round_timeout % 60
        human_readable = (f"{hours}h " if hours > 0 else "") + (f"{remaining_minutes}m" if remaining_minutes > 0 else "")

        init_embed.set_footer(text=f"👥 1{' - '+str(max_players)+' Players' if max_players > 1 else ''} ⏳ Round Time Limit: {human_readable}")
        state_embed = game_state_embed(self, self.game_state[interaction.channel.id])

        # Create the View
        init_view = GameInitView(self, self.game_state[interaction.channel.id])
        state_view = GameStateView(self)

        # Send game initialization message, store ID in game_state
        await interaction.response.send_message(embed=init_embed, view=init_view)
        init_message = await interaction.original_response()
        self.game_state[interaction.channel.id]["game_init_message"] = init_message.id

        # Send game state tracker message, store ID in game_state
        state_message = await interaction.channel.send(embed=state_embed, view=state_view)
        self.game_state[interaction.channel_id]["game_state_message"] = state_message.id

        # Pin state message, checking if channel pins full first & unpin the oldest if so
        channel_pins = await interaction.channel.pins()
        if len(channel_pins) >= 50:
            await channel_pins[-1].unpin()
        #await state_message.pin()


    @app_commands.command()
    async def endgame(self, interaction: discord.Interaction, reason: str = None) -> None:
        """End the game in the current channel."""
        reason = f"{interaction.user.mention} ended the game."
        await self.end_game(interaction.channel.id, interaction, reason)

    #
    # GAME COMMANDS
    # set up command group, limit to bot owner
    @commands.group()
    @checks.is_owner()
    async def thequietyear(self, ctx: commands.Context) -> None:
        """Manage The Quiet Year game settings."""
        pass

    @thequietyear.command()
    async def players(self, ctx, max_players: int = None) -> None:
        """Set the maximum number of players allowed per game."""
        if max_players == None:
            return
        if max_players < 2:
            await ctx.send(error("`You need at least 2 players!`"))
            return
        
        await self.config.guild(ctx.guild).max_players.set(max_players)
        await ctx.send(success(f"`Maximum players was changed to {max_players}`"))
        
    @thequietyear.command()
    async def timeout(self, ctx, minutes: int = None) -> None:
        """Set the round timeout in minutes."""
        if minutes is None:
            current_timeout = await self.config.guild(ctx.guild).round_timeout()
            await ctx.send(success(f"`The current turn timeout is set to {current_timeout} minutes.`"))
            return
        
        if minutes < 1:
            await ctx.send(error("`A turn timeout must be at least 1 minute.`"))
            return
        
        hours = minutes // 60
        remaining_minutes = minutes % 60
        await self.config.guild(ctx.guild).round_timeout.set(minutes)

        # Build a human-readable string for hours and minutes
        human_readable = (f"{hours}h " if hours > 0 else "") + (f"{remaining_minutes}m" if remaining_minutes > 0 else "")

        await ctx.send(success(f"`Turn timeout was changed to {minutes} minutes ({human_readable.strip()}).`"))

    @thequietyear.command()
    async def role(self, ctx, role: discord.Role = None) -> None:
        """Set the role for players in The Quiet Year game."""
        if role == None:
            await self.config.guild(ctx.guild).player_role.set(None)
            await ctx.send(success("`Player role was reset.`"))
            return
        await self.config.guild(ctx.guild).player_role.set(role.id)
        await ctx.send(success(f"`Player role set to: @{role.name}`"))

    @thequietyear.command()
    async def settings(self, ctx: commands.Context) -> None:
        """Show the current game settings."""
        setting_list = {
                "Maximum Players:": await self.config.guild(ctx.guild).max_players(),
                "Player Role:": ctx.guild.get_role(await self.config.guild(ctx.guild).player_role()),
                "Turn Timeout Length (in minutes):": await self.config.guild(ctx.guild).round_timeout()
        }

        embed = discord.Embed(
            title = ":hearts: :diamonds: :spades: :clubs: The Quiet Year",
            color = 0xff0000
        )

        for setting, value in setting_list.items():
            embed.add_field(name=setting, value=f"```{value}```", inline=False)

        await ctx.send(embed=embed)

    @thequietyear.command()
    async def gamestate(self, ctx: commands.Context) -> None:
        """Dump the game state for debugging."""
        await ctx.send(question(f"{pformat(self.game_state)}"))

    #
    # GAME FUNCTIONS
    #
    def create_deck(self) -> pydealer.Deck:
        """Return a Deck sorted by seasons"""
        season_rank = {
            "suits": {
                "Spades": 1, # Winter
                "Clubs": 2, # Autumn
                "Diamonds": 3, # Summer
                "Hearts": 4 # Spring
            }
        }
        deck = pydealer.Deck()
        deck.shuffle()
        deck.sort(season_rank)
        return deck

    async def end_game(self, channel_id: int, interaction: discord.Interaction = None, reason: str = None) -> None:
        """Ends the game in the specified channel or responds to an interaction."""
        # Defer the response if interaction exists
        if interaction:
            try:
                await interaction.response.defer()
            except discord.InteractionResponded:
                pass  # Interaction already responded to

        # Check if the game exists
        if channel_id not in self.active_games:
            if interaction:
                await interaction.followup.send(error("`No game is active in this channel.`"), ephemeral=True)
            return  # No game to end

        # Fetch the original game initialization message
        channel = self.bot.get_channel(channel_id)
        if not channel:
            if interaction:
                await interaction.followup.send(error("`Unable to access the channel.`"), ephemeral=True)
            return  # Channel no longer exists

        game_state = self.game_state.get(channel_id, {})

        # remove role from all players if in settings
        player_role = await self.config.guild(interaction.guild).player_role()
        if player_role:
            role = interaction.guild.get_role(player_role)
            if role:
                for player in game_state.get("players",[]):
                    member = interaction.guild.get_member(player)
                    if member and role in member.roles:
                        try:
                            await member.remove_roles(role)
                        except discord.HTTPException:
                            pass  # Continue even if role removal fails

        for saved_message in ("game_init_message", "game_state_message"):
            message_id = game_state.get(saved_message)
            if message_id:
                try:
                    message = await channel.fetch_message(message_id)
                    await message.edit(view=None)
                    await message.unpin()
                except discord.NotFound:
                    pass  # Message already deleted, continue

        # Remove the game state & from list of games
        self.game_state.pop(channel_id, None)
        self.active_games.pop(channel_id, None)

        # Prepare the response
        reason_text = f"{reason}" if reason else "The game was ended."
        embed = discord.Embed(
            title="The Quiet Year",
            description=f"{reason_text}",
            color=0xFF0000
        )
        # Respond based on the source (command or button)
        if interaction:
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, ephemeral=False)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=False)
        else:
            await channel.send(embed=embed)
            