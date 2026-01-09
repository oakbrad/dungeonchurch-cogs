"""
DUNGEON CHURCH

Classes for interactive elements of contests.
"""
from discord.ui import Button, View, Modal, TextInput
import discord

class ContestedRollModal(Modal):
    def __init__(self, challenger, challenged, ctx, dice_roller, initial_result, total, message, view):
        super().__init__(title="Submit Your Modifier")
        self.challenger = challenger
        self.challenged = challenged
        self.ctx = ctx
        self.dice_roller = dice_roller
        self.initial_result = initial_result
        self.total = total
        self.message = message
        self.view = view

        self.modifier = TextInput(
            label="Enter modifier:",
            placeholder="0",
            required=False,
            style=discord.TextStyle.short
        )
        self.add_item(self.modifier)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            mod_input = self.children[0].value
            modifier = int(mod_input) if mod_input else 0 # default to 0 if left blank in modal
            challenger_modifier = self.total - self.initial_result
            # Parse and roll for the challenged user
            challenged_result = self.dice_roller.parse("1d20").result
            challenged_total = challenged_result + modifier
            
            # Update the message with both results
            new_content = (
                f"### {self.challenger.mention} vs {interaction.user.mention}!\n\n"
                f"> ✅ **{self.challenger.display_name}** rolled **1d20{f'+{challenger_modifier}' if challenger_modifier != 0 else ''}** and got `{self.total}`\n"
                f"> ❌ **{interaction.user.display_name}** rolled **1d20{f'+{modifier}' if modifier != 0 else ''}** and got `{challenged_total}`\n"
                f"## {'🤝 Draw!' if self.total == challenged_total else (f'👑 {self.challenger.display_name} Won!' if self.total > challenged_total else f'👑 {self.challenged.display_name} Won!')}"
            )
            if self.view:
                self.view.stop() # Stop the view so that it's not edited on_timeout
            await self.message.edit(content=new_content, view=None)  # Remove the button
            await interaction.response.defer() # Acknowledge submission

        except Exception as e:
            await interaction.response.send_message(f"Error: {str(e)}", ephemeral=True)

class ContestedRollButton(Button):
    def __init__(self, challenger, challenged, ctx, dice_roller, initial_result, total):
        super().__init__(label=f"{challenged.display_name}'s Roll!", style=discord.ButtonStyle.primary)
        self.challenger = challenger
        self.challenged = challenged
        self.ctx = ctx
        self.dice_roller = dice_roller
        self.initial_result = initial_result
        self.total = total

    async def callback(self, interaction: discord.Interaction):
        # Ensure only the challenged user can press the button
        if interaction.user.id != self.challenged.id:
            await interaction.response.send_message("This button is not for you!", ephemeral=True)
            return

        # Open the modal for the challenged user
        modal = ContestedRollModal(
            challenger=self.challenger,
            challenged=self.challenged,
            ctx=self.ctx,
            dice_roller=self.dice_roller,
            initial_result=self.initial_result,
            total=self.total,
            message=self.view.message,
            view=self.view
        )
        await interaction.response.send_modal(modal)

class ContestedRollView(View):
    def __init__(self, challenger, challenged, ctx, dice_roller, initial_result, total, timeout: float = None):
        super().__init__(timeout=timeout)
        self.message = None
        self.challenged = challenged
        self.challenger = challenger
        self.add_item(ContestedRollButton(challenger, challenged, ctx, dice_roller, initial_result, total))

    def set_message(self, message):
        self.message = message

    async def on_timeout(self):
        """Timeout the view."""
        if self.message:
            try:
                await self.message.edit(
                    content=f"> 😞 *{self.challenged.mention} did not respond to {self.challenger.mention}'s challenge.*",
                    view=None
                )
            except:
                pass


class CoinFlipButton(Button):
    def __init__(self, choice: str, challenger, challenged, coin_result: str):
        emoji = "🪙" if choice == "heads" else "🪙"
        super().__init__(label=choice.capitalize(), style=discord.ButtonStyle.primary, emoji=emoji)
        self.choice = choice
        self.challenger = challenger
        self.challenged = challenged
        self.coin_result = coin_result

    async def callback(self, interaction: discord.Interaction):
        # Only the challenged user can press the button
        if interaction.user.id != self.challenged.id:
            await interaction.response.send_message("It's not your call!", ephemeral=True)
            return

        # Determine if the challenged user won
        won = self.choice == self.coin_result

        if won:
            result_message = (
                f"### 🪙 {self.challenger.mention} challenged {self.challenged.mention} to a coin flip!\n\n"
                f"> {self.challenged.display_name} called **{self.choice}**...\n"
                f"## 👑 It's {self.coin_result}! {self.challenged.display_name} wins!"
            )
        else:
            result_message = (
                f"### 🪙 {self.challenger.mention} challenged {self.challenged.mention} to a coin flip!\n\n"
                f"> {self.challenged.display_name} called **{self.choice}**...\n"
                f"## 👑 It's {self.coin_result}! {self.challenger.display_name} wins!"
            )

        if self.view:
            self.view.stop()
        await self.view.message.edit(content=result_message, view=None)
        await interaction.response.defer()


class CoinFlipView(View):
    def __init__(self, challenger, challenged, coin_result: str, timeout: float = None):
        super().__init__(timeout=timeout)
        self.message = None
        self.challenger = challenger
        self.challenged = challenged
        self.coin_result = coin_result

        # Add heads and tails buttons
        self.add_item(CoinFlipButton("heads", challenger, challenged, coin_result))
        self.add_item(CoinFlipButton("tails", challenger, challenged, coin_result))

    def set_message(self, message):
        self.message = message

    async def on_timeout(self):
        """Timeout the view."""
        if self.message:
            try:
                await self.message.edit(
                    content=f"> 😞 *{self.challenged.mention} did not respond to {self.challenger.mention}'s coin flip challenge.*",
                    view=None
                )
            except:
                pass