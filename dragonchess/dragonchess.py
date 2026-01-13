"""
Dragonchess (Threes) - A dice game cog for Red-DiscordBot

Play the dice game Threes against other players.
"""
import discord
from discord import app_commands
from redbot.core import commands, Config, checks
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import error, success

from .game import DragonchessGame
from .views import OpenChallengeView, GameView
from . import embeds


class Dragonchess(commands.Cog):
    """Play the dice game Threes (Dragonchess)."""

    __author__ = "DM Brad"
    __version__ = "1.0.0"

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=4206661099, force_registration=True
        )
        default_guild = {
            "timeout": 86400,  # 24 hours for open challenges
            "stats": {}  # {user_id: {"wins": int, "losses": int, "moon_shots": int}}
        }
        self.config.register_guild(**default_guild)

        # Track active games by message ID
        self.active_games: dict[int, DragonchessGame] = {}

    def format_help_for_context(self, ctx: commands.Context) -> str:
        """Show version in help."""
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\n\nCog Version: {self.__version__}"

    async def red_delete_data_for_user(self, *, requester: str, user_id: int) -> None:
        """Delete user data on request."""
        all_guilds = await self.config.all_guilds()
        for guild_id, guild_data in all_guilds.items():
            if str(user_id) in guild_data.get("stats", {}):
                async with self.config.guild_from_id(guild_id).stats() as stats:
                    if str(user_id) in stats:
                        del stats[str(user_id)]

    async def record_game_result(self, guild: discord.Guild, game: DragonchessGame) -> None:
        """Record the result of a completed game."""
        if game.is_tie or not game.winner:
            return

        async with self.config.guild(guild).stats() as stats:
            winner_id = str(game.winner)
            loser_id = str(game.loser)

            if winner_id not in stats:
                stats[winner_id] = {"wins": 0, "losses": 0, "moon_shots": 0}
            stats[winner_id]["wins"] += 1
            if game.moon_shot:
                stats[winner_id]["moon_shots"] += 1

            if loser_id not in stats:
                stats[loser_id] = {"wins": 0, "losses": 0, "moon_shots": 0}
            stats[loser_id]["losses"] += 1

    # -------------------------------------------------------------------------
    # Slash Commands (User-facing) - Dragonchess
    # -------------------------------------------------------------------------

    dragonchess_group = app_commands.Group(name="dragonchess", description="Play Dragonchess (Threes) - a dice game")

    @dragonchess_group.command(name="play")
    @app_commands.describe(opponent="Challenge a specific player (optional)")
    async def dragonchess_play_slash(self, interaction: discord.Interaction, opponent: discord.Member = None) -> None:
        """Start a game of Dragonchess."""
        ctx = await commands.Context.from_interaction(interaction)
        await self._start_game(ctx, opponent, game_name="Dragonchess")

    @dragonchess_group.command(name="stats")
    @app_commands.describe(player="Player to check stats for (optional, defaults to yourself)")
    async def dragonchess_stats_slash(self, interaction: discord.Interaction, player: discord.Member = None) -> None:
        """Show Dragonchess stats for a player."""
        if player is None:
            player = interaction.user
        stats = await self.config.guild(interaction.guild).stats()
        embed = embeds.stats_embed(player, stats, game_name="Dragonchess")
        await interaction.response.send_message(embed=embed)

    @dragonchess_group.command(name="rules")
    async def dragonchess_rules_slash(self, interaction: discord.Interaction) -> None:
        """Show the rules of Dragonchess (Threes)."""
        embed = self._build_rules_embed(game_name="Dragonchess")
        await interaction.response.send_message(embed=embed)

    @dragonchess_group.command(name="leaderboard")
    async def dragonchess_leaderboard_slash(self, interaction: discord.Interaction) -> None:
        """Show the Dragonchess leaderboard."""
        stats = await self.config.guild(interaction.guild).stats()
        embed = embeds.leaderboard_embed(stats, interaction.guild, game_name="Dragonchess")
        await interaction.response.send_message(embed=embed)

    # -------------------------------------------------------------------------
    # Slash Commands (User-facing) - Threes (alias)
    # -------------------------------------------------------------------------

    threes_group = app_commands.Group(name="threes", description="Play Threes - a dice game")

    @threes_group.command(name="play")
    @app_commands.describe(opponent="Challenge a specific player (optional)")
    async def threes_play_slash(self, interaction: discord.Interaction, opponent: discord.Member = None) -> None:
        """Start a game of Threes."""
        ctx = await commands.Context.from_interaction(interaction)
        await self._start_game(ctx, opponent, game_name="Threes")

    @threes_group.command(name="stats")
    @app_commands.describe(player="Player to check stats for (optional, defaults to yourself)")
    async def threes_stats_slash(self, interaction: discord.Interaction, player: discord.Member = None) -> None:
        """Show Threes stats for a player."""
        if player is None:
            player = interaction.user
        stats = await self.config.guild(interaction.guild).stats()
        embed = embeds.stats_embed(player, stats, game_name="Threes")
        await interaction.response.send_message(embed=embed)

    @threes_group.command(name="rules")
    async def threes_rules_slash(self, interaction: discord.Interaction) -> None:
        """Show the rules of Threes."""
        embed = self._build_rules_embed(game_name="Threes")
        await interaction.response.send_message(embed=embed)

    @threes_group.command(name="leaderboard")
    async def threes_leaderboard_slash(self, interaction: discord.Interaction) -> None:
        """Show the Threes leaderboard."""
        stats = await self.config.guild(interaction.guild).stats()
        embed = embeds.leaderboard_embed(stats, interaction.guild, game_name="Threes")
        await interaction.response.send_message(embed=embed)

    async def _start_game(self, ctx: commands.Context, opponent: discord.Member | None, game_name: str = "Dragonchess") -> None:
        """Internal method to start a game."""
        challenger = ctx.author

        # Validate opponent
        if opponent:
            if opponent.bot:
                await ctx.send(error("You can't challenge a bot!"), ephemeral=True)
                return
            if opponent.id == challenger.id:
                await ctx.send(error("You can't challenge yourself!"), ephemeral=True)
                return

            # Direct challenge - start game immediately
            game = DragonchessGame(challenger.id, opponent.id, game_name=game_name)
            status_embed = embeds.game_status_embed(game, ctx.guild)
            game_view = GameView(self, game, ctx.guild)

            sent = await ctx.send(embed=status_embed, view=game_view)
            game_view.set_message(sent)
            self.active_games[sent.id] = game

            notification = await ctx.send(
                f"{challenger.mention} has challenged {opponent.mention} to {game_name}!\n"
                f"{challenger.mention}, click **Roll Dice** to begin."
            )
            game_view.set_turn_notification(notification)
        else:
            # Open challenge
            timeout = await self.config.guild(ctx.guild).timeout()
            challenge_embed = embeds.open_challenge_embed(challenger, game_name=game_name, timeout=timeout)
            challenge_view = OpenChallengeView(self, challenger, timeout, game_name=game_name)

            sent = await ctx.send(embed=challenge_embed, view=challenge_view)
            challenge_view.set_message(sent)

    def _build_rules_embed(self, game_name: str = "Dragonchess") -> discord.Embed:
        """Build the rules embed."""
        if game_name == "Threes":
            description = "Also known as **Tripps**."
        else:
            description = "Also known as **Threes** or **Tripps**."

        embed = discord.Embed(
            title=f"{game_name} Rules",
            description=description,
            color=0x9b59b6
        )
        embed.add_field(
            name="Objective",
            value="Score the **lowest** total by adding up your kept dice. **3s count as zero!**",
            inline=False
        )
        embed.add_field(
            name="Gameplay",
            value=(
                "1. Players alternate turns.\n"
                "2. On your turn, roll your remaining dice.\n"
                "3. You must keep at least one die after each roll.\n"
                "4. Each player gets up to 5 rolls total.\n"
                "5. You're done when all 5 dice are kept or you're out of rolls."
            ),
            inline=False
        )
        embed.add_field(
            name="Scoring",
            value=(
                "- Add up all your kept dice.\n"
                "- **3s count as 0 points!**\n"
                "- Best possible score: 0 (all 3s)"
            ),
            inline=False
        )
        embed.add_field(
            name="Shooting the Moon",
            value="Roll **6-6-6-6-6** on your first roll to win instantly!",
            inline=False
        )
        embed.add_field(
            name="Winning",
            value="The player with the **lowest** score wins. Ties result in a rematch offer.",
            inline=False
        )
        return embed

    # -------------------------------------------------------------------------
    # Admin Commands
    # -------------------------------------------------------------------------

    @commands.group(aliases=["dragonchess"])
    @checks.admin_or_permissions(manage_guild=True)
    async def dc(self, ctx: commands.Context) -> None:
        """Manage Dragonchess settings."""

    @dc.command(name="settings")
    async def dc_settings(self, ctx: commands.Context) -> None:
        """Show current Dragonchess settings."""
        timeout = await self.config.guild(ctx.guild).timeout()
        stats = await self.config.guild(ctx.guild).stats()

        embed = discord.Embed(
            title="Dragonchess Settings",
            color=0x9b59b6
        )
        embed.add_field(name="Challenge Timeout", value=f"`{timeout}` seconds", inline=True)
        embed.add_field(name="Players Tracked", value=f"`{len(stats)}`", inline=True)

        await ctx.send(embed=embed)

    @dc.command(name="timeout")
    async def dc_timeout(self, ctx: commands.Context, seconds: int) -> None:
        """Set the timeout for open challenges.

        Must be between 30 and 900 seconds (15 minutes).
        """
        if seconds < 30 or seconds > 900:
            await ctx.send(error("Timeout must be between 30 and 900 seconds."))
            return

        await self.config.guild(ctx.guild).timeout.set(seconds)
        await ctx.send(success(f"Challenge timeout set to `{seconds}` seconds."))

    @dc.command(name="reset")
    async def dc_reset(self, ctx: commands.Context, member: discord.Member) -> None:
        """Reset a player's Dragonchess stats."""
        async with self.config.guild(ctx.guild).stats() as stats:
            user_id = str(member.id)
            if user_id in stats:
                del stats[user_id]
                await ctx.send(success(f"Reset stats for {member.display_name}."))
            else:
                await ctx.send(error(f"{member.display_name} has no recorded stats."))

    @dc.command(name="resetall")
    @checks.is_owner()
    async def dc_resetall(self, ctx: commands.Context) -> None:
        """Reset all Dragonchess stats for this server."""
        await self.config.guild(ctx.guild).stats.set({})
        await ctx.send(success("All Dragonchess stats have been reset."))

    @dc.command(name="debug")
    @checks.is_owner()
    async def dc_debug(self, ctx: commands.Context) -> None:
        """Show active games for debugging."""
        if not self.active_games:
            await ctx.send("No active games.")
            return

        lines = []
        for msg_id, game in self.active_games.items():
            p1, p2 = game.players
            m1 = ctx.guild.get_member(p1)
            m2 = ctx.guild.get_member(p2)
            name1 = m1.display_name if m1 else str(p1)
            name2 = m2.display_name if m2 else str(p2)
            current = ctx.guild.get_member(game.current_player)
            current_name = current.display_name if current else str(game.current_player)

            state1 = game.player_states[p1]
            state2 = game.player_states[p2]

            lines.append(
                f"**Message ID:** `{msg_id}`\n"
                f"  {name1}: kept={state1.kept_dice}, rolls_used={state1.rolls_used}, finished={state1.finished}\n"
                f"  {name2}: kept={state2.kept_dice}, rolls_used={state2.rolls_used}, finished={state2.finished}\n"
                f"  Current turn: {current_name} | Game finished: {game.finished}"
            )

        await ctx.send("\n\n".join(lines))
