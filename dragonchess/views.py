"""
Dragonchess - Discord UI Components

Views and buttons for the game interface.
"""
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
        await self.message.edit(
            embed=status_embed,
            view=game_view
        )

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
            name = current_member.display_name if current_member else "the other player"
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
            name = current_member.display_name if current_member else "the other player"
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
            await self.message.edit(
                embed=status_embed,
                view=game_view
            )
            notification = await self.message.channel.send(
                f"{next_name}, it's your turn! Click **Roll Dice**."
            )
        game_view.set_turn_notification(notification)

    @ui.button(label="Confirm", style=discord.ButtonStyle.primary, emoji="✅", row=1)
    async def confirm(self, interaction: discord.Interaction, button: ui.Button) -> None:
        # Only the player who rolled can confirm (they were current player when dice were rolled)
        rolling_player = self.game.current_player
        if interaction.user.id != rolling_player:
            current_member = self.guild.get_member(rolling_player)
            name = current_member.display_name if current_member else "the other player"
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
            else:
                await self.message.edit(
                    embed=winner_embed,
                    view=rematch_view
                )
        else:
            # Record stats and show winner
            await self.cog.record_game_result(self.guild, self.game)
            winner_embed = embeds.winner_embed(self.game, self.guild)

            if interaction:
                await interaction.response.edit_message(
                    embed=winner_embed,
                    view=None
                )
            else:
                await self.message.edit(
                    embed=winner_embed,
                    view=None
                )

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
            description=f"{interaction.user.display_name} declined the rematch. Game ends in a draw.",
            color=0x95a5a6
        )

        await interaction.response.edit_message(embed=embed, view=None)

        # Clean up
        if self.message and self.message.id in self.cog.active_games:
            del self.cog.active_games[self.message.id]
