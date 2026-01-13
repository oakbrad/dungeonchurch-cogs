"""
Dragonchess - Discord UI Components

Views and buttons for the game interface.
"""
import asyncio
import random
import discord
from discord import ui
from .game import DragonchessGame
from . import embeds


class OpenChallengeView(ui.View):
    """View for an open challenge where anyone can accept."""

    def __init__(self, cog, challenger: discord.Member, timeout: float, game_name: str = "Dragonchess"):
        super().__init__(timeout=timeout)
        self.cog = cog
        self.challenger = challenger
        self.message: discord.Message | None = None
        self.accepted = False
        self.game_name = game_name

    def set_message(self, message: discord.Message) -> None:
        self.message = message

    async def on_timeout(self) -> None:
        if self.message and not self.accepted:
            embed = discord.Embed(
                title="Challenge Expired",
                description=f"{self.challenger.mention}'s challenge timed out.",
                color=0x95a5a6
            )
            try:
                await self.message.edit(embed=embed, view=None)
            except (discord.NotFound, discord.HTTPException):
                pass

    @ui.button(label="Accept Challenge", style=discord.ButtonStyle.primary, emoji="⚔️")
    async def accept(self, interaction: discord.Interaction, button: ui.Button) -> None:
        # Can't accept your own challenge
        if interaction.user.id == self.challenger.id:
            await interaction.response.send_message(
                "You can't accept your own challenge!",
                ephemeral=True
            )
            return

        # Can't be a bot
        if interaction.user.bot:
            return

        self.accepted = True
        self.stop()

        # Start the game
        opponent = interaction.user
        game = DragonchessGame(self.challenger.id, opponent.id, game_name=self.game_name)

        # Store game state
        self.cog.active_games[self.message.id] = game

        # Create game view
        game_view = GameView(self.cog, game, interaction.guild)
        game_view.set_message(self.message)

        # Update message with game state
        status_embed = embeds.game_status_embed(game, interaction.guild)
        await interaction.response.defer()
        try:
            await self.message.edit(
                embed=status_embed,
                view=game_view
            )
        except (discord.NotFound, discord.HTTPException):
            await interaction.followup.send(
                "This challenge is no longer available.",
                ephemeral=True
            )
            return

        # Prompt first player to roll
        notification = await interaction.followup.send(
            f"{self.challenger.mention}, you're up first! Click **Roll Dice** to begin.",
            wait=True
        )
        game_view.set_turn_notification(notification)


class GameView(ui.View):
    """Main game view with the Roll Dice button."""

    def __init__(self, cog, game: DragonchessGame, guild: discord.Guild):
        super().__init__(timeout=None)  # No timeout during game
        self.cog = cog
        self.game = game
        self.guild = guild
        self.message: discord.Message | None = None
        self.turn_notification: discord.Message | None = None

    def set_message(self, message: discord.Message) -> None:
        self.message = message

    def set_turn_notification(self, notification: discord.Message) -> None:
        self.turn_notification = notification

    @ui.button(label="Roll Dice", style=discord.ButtonStyle.primary, emoji="🎲")
    async def roll_dice(self, interaction: discord.Interaction, button: ui.Button) -> None:
        # Only current player can roll
        if interaction.user.id != self.game.current_player:
            current_member = self.guild.get_member(self.game.current_player)
            name = current_member.mention if current_member else "the other player"
            await interaction.response.send_message(
                f"It's {name}'s turn!",
                ephemeral=True
            )
            return

        # Delete turn notification if it exists
        if self.turn_notification:
            try:
                await self.turn_notification.delete()
            except (discord.NotFound, discord.HTTPException):
                pass
            self.turn_notification = None

        # Roll the dice
        dice = self.game.roll_dice()

        if not dice:
            await interaction.response.send_message(
                "You can't roll right now.",
                ephemeral=True
            )
            return

        # Check for moon shot
        if self.game.moon_shot:
            await self._handle_game_end(interaction)
            return

        # Show dice selection view
        player_name = interaction.user.display_name
        dice_embed = embeds.dice_roll_embed(dice, player_name)
        select_view = DiceSelectView(self.cog, self.game, self.guild, self.message)

        # Update the status embed
        status_embed = embeds.game_status_embed(self.game, self.guild)

        await interaction.response.edit_message(
            embeds=[status_embed, dice_embed],
            view=select_view
        )

    async def _handle_game_end(self, interaction: discord.Interaction) -> None:
        """Handle the end of the game."""
        self.stop()

        if self.game.is_tie:
            # Show rematch option
            winner_embed = embeds.winner_embed(self.game, self.guild)
            rematch_view = RematchView(self.cog, self.game, self.guild)
            rematch_view.set_message(self.message)

            await interaction.response.edit_message(
                embed=winner_embed,
                view=rematch_view
            )
        else:
            # Record stats and show winner
            await self.cog.record_game_result(self.guild, self.game)
            winner_embed = embeds.winner_embed(self.game, self.guild)

            await interaction.response.edit_message(
                embed=winner_embed,
                view=None
            )

        # Clean up game state
        if self.message and self.message.id in self.cog.active_games:
            del self.cog.active_games[self.message.id]


class DiceButton(ui.Button):
    """Button representing a single die that can be toggled."""

    # Number emojis for dice values
    NUMBER_EMOJIS = {
        1: "1️⃣",
        2: "2️⃣",
        3: "3️⃣",
        4: "4️⃣",
        5: "5️⃣",
        6: "6️⃣",
    }

    def __init__(self, index: int, value: int):
        emoji = self.NUMBER_EMOJIS.get(value, str(value))

        super().__init__(
            label=None,
            style=discord.ButtonStyle.secondary,  # All start gray
            emoji=emoji,
            custom_id=f"die_{index}"
        )
        self.index = index
        self.value = value
        self.selected = False

    async def callback(self, interaction: discord.Interaction) -> None:
        view: DiceSelectView = self.view

        # Only current player can select
        if interaction.user.id != view.game.current_player:
            current_member = view.guild.get_member(view.game.current_player)
            name = current_member.mention if current_member else "the other player"
            await interaction.response.send_message(
                f"It's {name}'s turn!",
                ephemeral=True
            )
            return

        # Toggle selection
        self.selected = not self.selected
        if self.selected:
            self.style = discord.ButtonStyle.success  # Green when selected to keep
        else:
            self.style = discord.ButtonStyle.secondary  # Gray when not selected

        await interaction.response.edit_message(view=view)


class DiceSelectView(ui.View):
    """View for selecting which dice to keep."""

    def __init__(self, cog, game: DragonchessGame, guild: discord.Guild, message: discord.Message):
        # Use timeout for single die auto-confirm
        self.single_die = len(game.current_state.current_roll) == 1
        super().__init__(timeout=10.0 if self.single_die else None)
        self.cog = cog
        self.game = game
        self.guild = guild
        self.message = message
        self.dice_buttons: list[DiceButton] = []
        self.confirmed = False

        # Only add dice toggle buttons if more than one die
        if not self.single_die:
            for i, value in enumerate(game.current_state.current_roll):
                btn = DiceButton(i, value)
                self.dice_buttons.append(btn)
                self.add_item(btn)

    async def on_timeout(self) -> None:
        """Auto-confirm single die after timeout."""
        if self.single_die and not self.confirmed:
            await self._do_confirm(interaction=None)

    async def _do_confirm(self, interaction: discord.Interaction | None) -> None:
        """Shared confirm logic for button and auto-confirm."""
        self.confirmed = True
        self.stop()

        # For single die, keep index 0. Otherwise get selected buttons.
        if self.single_die:
            selected = [0]
        else:
            selected = [btn.index for btn in self.dice_buttons if btn.selected]

        if not selected:
            if interaction:
                await interaction.response.send_message(
                    "You must keep at least one die!",
                    ephemeral=True
                )
            return

        # Keep the selected dice (this also switches turns if game not over)
        success = self.game.keep_dice(selected)
        if not success:
            if interaction:
                await interaction.response.send_message(
                    "Something went wrong keeping those dice.",
                    ephemeral=True
                )
            return

        # Check if game is over
        if self.game.finished:
            await self._handle_game_end(interaction)
            return

        # Game continues - turn has already switched in keep_dice()
        # Notify next player
        next_member = self.guild.get_member(self.game.current_player)
        next_name = next_member.mention if next_member else "Next player"

        status_embed = embeds.game_status_embed(self.game, self.guild)
        game_view = GameView(self.cog, self.game, self.guild)
        game_view.set_message(self.message)

        if interaction:
            await interaction.response.edit_message(
                embed=status_embed,
                view=game_view
            )
            notification = await interaction.followup.send(
                f"{next_name}, it's your turn! Click **Roll Dice**.",
                wait=True
            )
        else:
            # Auto-confirm case - edit message directly
            if not self.message:
                return  # Message reference lost, game is abandoned
            try:
                await self.message.edit(
                    embed=status_embed,
                    view=game_view
                )
                notification = await self.message.channel.send(
                    f"{next_name}, it's your turn! Click **Roll Dice**."
                )
                game_view.set_turn_notification(notification)
            except (discord.NotFound, discord.HTTPException):
                pass  # Message was deleted, game is abandoned
            return
        game_view.set_turn_notification(notification)

    @ui.button(label="Confirm", style=discord.ButtonStyle.primary, emoji="✅", row=1)
    async def confirm(self, interaction: discord.Interaction, button: ui.Button) -> None:
        # Only the player who rolled can confirm (they were current player when dice were rolled)
        rolling_player = self.game.current_player
        if interaction.user.id != rolling_player:
            current_member = self.guild.get_member(rolling_player)
            name = current_member.mention if current_member else "the other player"
            await interaction.response.send_message(
                f"It's {name}'s turn!",
                ephemeral=True
            )
            return

        # For multi-die case, check that at least one is selected
        if not self.single_die:
            selected = [btn.index for btn in self.dice_buttons if btn.selected]
            if not selected:
                await interaction.response.send_message(
                    "You must keep at least one die!",
                    ephemeral=True
                )
                return

        await self._do_confirm(interaction)

    async def _handle_game_end(self, interaction: discord.Interaction | None) -> None:
        """Handle the end of the game."""
        if self.game.is_tie:
            # Show rematch option
            winner_embed = embeds.winner_embed(self.game, self.guild)
            rematch_view = RematchView(self.cog, self.game, self.guild)
            rematch_view.set_message(self.message)

            if interaction:
                await interaction.response.edit_message(
                    embed=winner_embed,
                    view=rematch_view
                )
            elif self.message:
                try:
                    await self.message.edit(
                        embed=winner_embed,
                        view=rematch_view
                    )
                except (discord.NotFound, discord.HTTPException):
                    pass  # Message was deleted
        else:
            # Record stats and show winner
            await self.cog.record_game_result(self.guild, self.game)
            winner_embed = embeds.winner_embed(self.game, self.guild)

            if interaction:
                await interaction.response.edit_message(
                    embed=winner_embed,
                    view=None
                )
            elif self.message:
                try:
                    await self.message.edit(
                        embed=winner_embed,
                        view=None
                    )
                except (discord.NotFound, discord.HTTPException):
                    pass  # Message was deleted

        # Clean up game state
        if self.message and self.message.id in self.cog.active_games:
            del self.cog.active_games[self.message.id]


class RematchView(ui.View):
    """View for offering a rematch after a tie."""

    def __init__(self, cog, game: DragonchessGame, guild: discord.Guild, timeout: float = 300):
        super().__init__(timeout=timeout)
        self.cog = cog
        self.game = game
        self.guild = guild
        self.message: discord.Message | None = None
        self.handled = False

    def set_message(self, message: discord.Message) -> None:
        self.message = message

    async def on_timeout(self) -> None:
        if self.message and not self.handled:
            embed = discord.Embed(
                title="Draw!",
                description="The rematch offer expired. Game ends in a draw.",
                color=0x95a5a6
            )
            try:
                await self.message.edit(embed=embed, view=None)
            except (discord.NotFound, discord.HTTPException):
                pass
            # Clean up game state on timeout
            if self.message.id in self.cog.active_games:
                del self.cog.active_games[self.message.id]

    def _is_player(self, user_id: int) -> bool:
        return user_id in self.game.players

    @ui.button(label="Rematch", style=discord.ButtonStyle.success, emoji="🔄")
    async def rematch(self, interaction: discord.Interaction, button: ui.Button) -> None:
        if not self._is_player(interaction.user.id):
            await interaction.response.send_message(
                "Only the players can start a rematch!",
                ephemeral=True
            )
            return

        self.handled = True
        self.stop()

        # Start new game with same players
        p1, p2 = self.game.players
        new_game = DragonchessGame(p1, p2)

        # Store game state
        self.cog.active_games[self.message.id] = new_game

        # Create game view
        game_view = GameView(self.cog, new_game, self.guild)
        game_view.set_message(self.message)

        status_embed = embeds.game_status_embed(new_game, self.guild)
        await interaction.response.edit_message(
            embed=status_embed,
            view=game_view
        )

        first_member = self.guild.get_member(new_game.current_player)
        first_name = first_member.mention if first_member else "First player"
        notification = await interaction.followup.send(
            f"Rematch! {first_name}, you're up first!",
            wait=True
        )
        game_view.set_turn_notification(notification)

    @ui.button(label="Decline", style=discord.ButtonStyle.secondary, emoji="❌")
    async def decline(self, interaction: discord.Interaction, button: ui.Button) -> None:
        if not self._is_player(interaction.user.id):
            await interaction.response.send_message(
                "Only the players can decline!",
                ephemeral=True
            )
            return

        self.handled = True
        self.stop()

        embed = discord.Embed(
            title="Draw!",
            description=f"{interaction.user.mention} declined the rematch. Game ends in a draw.",
            color=0x95a5a6
        )

        await interaction.response.edit_message(embed=embed, view=None)

        # Clean up
        if self.message and self.message.id in self.cog.active_games:
            del self.cog.active_games[self.message.id]


class BotGameView(ui.View):
    """Game view for playing against a bot opponent."""

    BOT_DELAY_MIN = 2.0  # Minimum seconds for bot delays
    BOT_DELAY_MAX = 6.0  # Maximum seconds for bot delays

    def __init__(self, cog, game: DragonchessGame, guild: discord.Guild, bot_id: int):
        super().__init__(timeout=None)
        self.cog = cog
        self.game = game
        self.guild = guild
        self.bot_id = bot_id
        self.message: discord.Message | None = None
        self.turn_notification: discord.Message | None = None

    def set_message(self, message: discord.Message) -> None:
        self.message = message

    def set_turn_notification(self, notification: discord.Message) -> None:
        self.turn_notification = notification

    def _is_bot_turn(self) -> bool:
        """Check if it's the bot's turn."""
        return self.game.current_player == self.bot_id

    async def _run_bot_turn(self) -> None:
        """Execute the bot's turn automatically.

        The bot keeps rolling until it's finished or the game ends.
        This handles cases where the human finishes early and the bot
        needs multiple consecutive turns.
        """
        if not self.message or self.game.finished:
            return

        bot_member = self.guild.get_member(self.bot_id)
        bot_name = bot_member.display_name if bot_member else "Bot"

        # Keep rolling while it's the bot's turn and bot isn't finished
        while (self.game.current_player == self.bot_id and
               not self.game.finished and
               not self.game.is_player_finished(self.bot_id)):

            # Random delay before rolling
            await asyncio.sleep(random.uniform(self.BOT_DELAY_MIN, self.BOT_DELAY_MAX))

            # Roll the dice
            dice = self.game.roll_dice()
            if not dice:
                break

            # Check for moon shot
            if self.game.moon_shot:
                await self._handle_game_end()
                return

            # Show the bot's roll (no instructions since bot decides automatically)
            dice_embed = embeds.dice_roll_embed(dice, bot_name, show_instructions=False)
            status_embed = embeds.game_status_embed(self.game, self.guild)

            try:
                await self.message.edit(embeds=[status_embed, dice_embed], view=None)
            except (discord.NotFound, discord.HTTPException):
                return

            # Random delay before keeping dice
            await asyncio.sleep(random.uniform(self.BOT_DELAY_MIN, self.BOT_DELAY_MAX))

            # Get optimal dice to keep and keep them
            keep_indices = self.game.get_bot_keep_indices()
            self.game.keep_dice(keep_indices)

        # Check if game is over
        if self.game.finished:
            await self._handle_game_end()
            return

        # Game continues - show updated state and prompt human
        status_embed = embeds.game_status_embed(self.game, self.guild)
        try:
            await self.message.edit(embed=status_embed, view=self)
        except (discord.NotFound, discord.HTTPException):
            return

        # Notify human player
        human_id = [p for p in self.game.players if p != self.bot_id][0]
        human_member = self.guild.get_member(human_id)
        human_name = human_member.mention if human_member else "Your"

        try:
            notification = await self.message.channel.send(
                f"{human_name}, it's your turn! Click **Roll Dice**."
            )
            self.turn_notification = notification
        except (discord.NotFound, discord.HTTPException):
            pass

    async def _handle_game_end(self) -> None:
        """Handle the end of a bot game."""
        self.stop()

        if not self.message:
            return

        winner_embed = embeds.winner_embed(self.game, self.guild)

        if self.game.is_tie:
            # For bot games, auto-decline rematch on tie - but show the full tie embed
            try:
                await self.message.edit(embed=winner_embed, view=None)
            except (discord.NotFound, discord.HTTPException):
                pass
        else:
            # Record stats only for the human player
            await self.cog.record_bot_game_result(self.guild, self.game, self.bot_id)
            try:
                await self.message.edit(embed=winner_embed, view=None)
            except (discord.NotFound, discord.HTTPException):
                pass

        # Clean up
        if self.message.id in self.cog.active_games:
            del self.cog.active_games[self.message.id]

    @ui.button(label="Roll Dice", style=discord.ButtonStyle.primary, emoji="🎲")
    async def roll_dice(self, interaction: discord.Interaction, button: ui.Button) -> None:
        # Only human player can click (bot plays automatically)
        if interaction.user.id == self.bot_id:
            return

        if interaction.user.id != self.game.current_player:
            await interaction.response.send_message(
                "It's not your turn!",
                ephemeral=True
            )
            return

        # Delete turn notification if exists
        if self.turn_notification:
            try:
                await self.turn_notification.delete()
            except (discord.NotFound, discord.HTTPException):
                pass
            self.turn_notification = None

        # Roll the dice
        dice = self.game.roll_dice()
        if not dice:
            await interaction.response.send_message(
                "You can't roll right now.",
                ephemeral=True
            )
            return

        # Check for moon shot
        if self.game.moon_shot:
            await self._handle_game_end_interaction(interaction)
            return

        # Show dice selection view
        player_name = interaction.user.display_name
        dice_embed = embeds.dice_roll_embed(dice, player_name)
        select_view = BotDiceSelectView(self.cog, self.game, self.guild, self.message, self.bot_id)

        status_embed = embeds.game_status_embed(self.game, self.guild)
        await interaction.response.edit_message(
            embeds=[status_embed, dice_embed],
            view=select_view
        )

    async def _handle_game_end_interaction(self, interaction: discord.Interaction) -> None:
        """Handle game end when triggered by an interaction."""
        self.stop()

        winner_embed = embeds.winner_embed(self.game, self.guild)

        if self.game.is_tie:
            # Show the full tie embed (winner_embed handles ties too)
            await interaction.response.edit_message(embed=winner_embed, view=None)
        else:
            await self.cog.record_bot_game_result(self.guild, self.game, self.bot_id)
            await interaction.response.edit_message(embed=winner_embed, view=None)

        if self.message and self.message.id in self.cog.active_games:
            del self.cog.active_games[self.message.id]


class BotDiceSelectView(ui.View):
    """Dice selection view for bot games."""

    def __init__(self, cog, game: DragonchessGame, guild: discord.Guild,
                 message: discord.Message, bot_id: int):
        self.single_die = len(game.current_state.current_roll) == 1
        super().__init__(timeout=10.0 if self.single_die else None)
        self.cog = cog
        self.game = game
        self.guild = guild
        self.message = message
        self.bot_id = bot_id
        self.dice_buttons: list[DiceButton] = []
        self.confirmed = False

        # Only add dice toggle buttons if more than one die
        if not self.single_die:
            for i, value in enumerate(game.current_state.current_roll):
                btn = DiceButton(i, value)
                self.dice_buttons.append(btn)
                self.add_item(btn)

    async def on_timeout(self) -> None:
        """Auto-confirm single die after timeout."""
        if self.single_die and not self.confirmed:
            await self._do_confirm(interaction=None)

    async def _do_confirm(self, interaction: discord.Interaction | None) -> None:
        """Shared confirm logic."""
        self.confirmed = True
        self.stop()

        if self.single_die:
            selected = [0]
        else:
            selected = [btn.index for btn in self.dice_buttons if btn.selected]

        if not selected:
            if interaction:
                await interaction.response.send_message(
                    "You must keep at least one die!",
                    ephemeral=True
                )
            return

        success = self.game.keep_dice(selected)
        if not success:
            if interaction:
                await interaction.response.send_message(
                    "Something went wrong keeping those dice.",
                    ephemeral=True
                )
            return

        # Check if game is over
        if self.game.finished:
            await self._handle_game_end(interaction)
            return

        # Check if it's now the bot's turn
        if self.game.current_player == self.bot_id:
            # Show updated status and schedule bot turn
            status_embed = embeds.game_status_embed(self.game, self.guild)
            bot_view = BotGameView(self.cog, self.game, self.guild, self.bot_id)
            bot_view.set_message(self.message)

            if interaction:
                await interaction.response.edit_message(embed=status_embed, view=None)
            elif self.message:
                try:
                    await self.message.edit(embed=status_embed, view=None)
                except (discord.NotFound, discord.HTTPException):
                    return

            # Run bot turn
            asyncio.create_task(bot_view._run_bot_turn())
        else:
            # Human's turn again (shouldn't happen in normal flow)
            status_embed = embeds.game_status_embed(self.game, self.guild)
            bot_view = BotGameView(self.cog, self.game, self.guild, self.bot_id)
            bot_view.set_message(self.message)

            if interaction:
                await interaction.response.edit_message(embed=status_embed, view=bot_view)
            elif self.message:
                try:
                    await self.message.edit(embed=status_embed, view=bot_view)
                except (discord.NotFound, discord.HTTPException):
                    pass

    async def _handle_game_end(self, interaction: discord.Interaction | None) -> None:
        """Handle game end."""
        winner_embed = embeds.winner_embed(self.game, self.guild)

        # Record stats only if not a tie
        if not self.game.is_tie:
            await self.cog.record_bot_game_result(self.guild, self.game, self.bot_id)

        # Show the result embed (winner_embed handles ties too)
        if interaction:
            await interaction.response.edit_message(embed=winner_embed, view=None)
        elif self.message:
            try:
                await self.message.edit(embed=winner_embed, view=None)
            except (discord.NotFound, discord.HTTPException):
                pass

        if self.message and self.message.id in self.cog.active_games:
            del self.cog.active_games[self.message.id]

    @ui.button(label="Confirm", style=discord.ButtonStyle.primary, emoji="✅", row=1)
    async def confirm(self, interaction: discord.Interaction, button: ui.Button) -> None:
        rolling_player = self.game.current_player
        if interaction.user.id != rolling_player:
            await interaction.response.send_message(
                "It's not your turn!",
                ephemeral=True
            )
            return

        if not self.single_die:
            selected = [btn.index for btn in self.dice_buttons if btn.selected]
            if not selected:
                await interaction.response.send_message(
                    "You must keep at least one die!",
                    ephemeral=True
                )
                return

        await self._do_confirm(interaction)
