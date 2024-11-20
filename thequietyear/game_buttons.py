import discord
from redbot.core.utils.chat_formatting import error, question, success

class ButtonMixin:
    """A mixin to add reusable buttons to views."""

    def add_abundance_button(self, view, custom_id="add_abundance") -> discord.Button:
        """Add the 'Add Abundance' button."""
        button = discord.ui.Button(label="Abundance", style=discord.ButtonStyle.success, emoji="➕", custom_id=custom_id)

        async def callback(interaction: discord.Interaction):
            """Add an abundance to the game_state"""
            game_state = self.cog.game_state[interaction.channel_id]
            player = interaction.user

            if player.id not in game_state["players"]:
                await interaction.response.send_message(error("`You must join the game first!`", ephemeral=True))
                return

            # Trigger the Abundance modal
            from .game_modals import AddAbundanceModal
            modal = AddAbundanceModal(self.cog, interaction.channel_id)
            await interaction.response.send_modal(modal)
            
        button.callback = callback  # Assign the callback to the button
        return button
    
    def add_scarcity_button(self, view, custom_id="add_scarcity") -> discord.Button:
        """Add the 'Add Scarcity' button."""
        button = discord.ui.Button(label="Scarcity", style=discord.ButtonStyle.success, emoji="➕", custom_id=custom_id)

        async def callback(interaction: discord.Interaction):
            """Add a scarcity to the game_state"""
            game_state = self.cog.game_state[interaction.channel_id]
            player = interaction.user

            if player.id not in game_state["players"]:
                await interaction.response.send_message(error("You must join the game first!"), ephemeral=True)
                return
            
            # Trigger the Abundance modal
            from .game_modals import AddScarcityModal
            modal = AddScarcityModal(self.cog, interaction.channel_id)
            await interaction.response.send_modal(modal)
            
        button.callback = callback  # Assign the callback to the button
        return button
    
    def remove_scarcity_button(self, view, custom_id="remove_scarcity") -> discord.Button:
        """Add the 'Remove Scarcity' button."""
        button = discord.ui.Button(label="Scarcity", style=discord.ButtonStyle.danger, emoji="➖", custom_id=custom_id)

        async def callback(interaction: discord.Interaction):
            """Remove a scarcity from the game state"""
            game_state = self.cog.game_state[interaction.channel_id]
            player = interaction.user

            if player.id not in game_state["players"]:
                await interaction.response.send_message(error("`You must join the game first!`"), ephemeral=True)
                return
            
            # Check if there are any scarcities to remove
            scarcities = game_state["scarcities"]
            if len(scarcities) == 0:
                await interaction.response.send_message(error("`There are no scarcities to remove.`"), ephemeral=True)
                return

            # Show the RemoveScarcityView
            from .game_views import RemoveScarcityView
            remove_view = RemoveScarcityView(self.cog, interaction.channel_id)
            await interaction.response.send_message("Choose an Scarcity to remove:", view=remove_view, ephemeral=True)
            
        button.callback = callback  # Assign the callback to the button
        return button
    
    def remove_abundance_button(self, view, custom_id="remove_abundance") -> discord.Button:
        """Add the 'Remove Abundance' button."""
        button = discord.ui.Button(label="Abundance", style=discord.ButtonStyle.danger, emoji="➖",custom_id=custom_id)

        async def callback(interaction: discord.Interaction):
            """Remove an abundance from the game state"""
            game_state = self.cog.game_state[interaction.channel_id]
            player = interaction.user

            if player.id not in game_state["players"]:
                await interaction.response.send_message(error("`You must join the game first!`"), ephemeral=True)
                return
            
            # Check if there are any abundances to remove
            abundances = game_state["abundances"]
            if len(abundances) == 0:
                await interaction.response.send_message(error("`There are no abundances to remove.`"), ephemeral=True)
                return

            # Show the RemoveAbundanceView
            from .game_views import RemoveAbundanceView
            remove_view = RemoveAbundanceView(self.cog, interaction.channel_id)
            await interaction.response.send_message("Choose an abundance to remove:", view=remove_view, ephemeral=True)
            
        button.callback = callback  # Assign the callback to the button
        return button