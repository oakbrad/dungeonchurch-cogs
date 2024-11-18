import discord
from redbot.core import commands, Config, checks
from redbot.core.utils.chat_formatting import error, question, success
import pydealer

class TheQuietYear(commands.Cog):
    __author__ = "DM Brad"
    __version__ = "0.1"

    def __init__(self, bot):
        self.bot = bot
        # default settings
        self.config = Config.get_conf(
            self, identifier=4206662013, force_registration=True
        )
        default_guild_settings = {
            "max_players": 4,
            "turn_timeout":  1440, # in minutes, 1440=24 hours
            "player_role": None # placeholder for role ID
        }
        self.config.register_guild(**default_guild_settings)

    # COMMANDS
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
        """Set the turn timeout in minutes."""
        if minutes is None:
            current_timeout = await self.config.guild(ctx.guild).turn_timeout()
            await ctx.send(success(f"`The current turn timeout is set to {current_timeout} minutes.`"))
            return
        
        if minutes < 1:
            await ctx.send(error("`A turn timeout must be at least 1 minute.`"))
            return
        
        hours = minutes // 60
        remaining_minutes = minutes % 60

        await self.config.guild(ctx.guild).turn_timeout.set(minutes)

        # Build a human-readable string for hours and minutes
        human_readable = (
            f"{hours}h " if hours > 0 else ""
        ) + (
            f"{remaining_minutes}m" if remaining_minutes > 0 else ""
        )

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
                "Turn Timeout Length (in minutes):": await self.config.guild(ctx.guild).turn_timeout()
        }

        embed = discord.Embed(
            title = ":hearts: :diamonds: :spades: :clubs: The Quiet Year",
            color = 0xff0000
        )

        for setting, value in setting_list.items():
            embed.add_field(name=setting, value=f"```{value}```", inline=False)

        await ctx.send(embed=embed)