import discord
from redbot.core.utils.chat_formatting import error, question, success
from .game_embeds import update_state_embed

class AddAbundanceModal(discord.ui.Modal, title="Add Abundance"):
    def __init__(self, cog, interaction_channel_id):
        super().__init__()
        self.cog = cog
        self.channel_id = interaction_channel_id

        # Input field for abundance
        self.abundance_input = discord.ui.TextInput(
            label="Abundance",
            placeholder="Enter a new abundance...",
            style=discord.TextStyle.short,
        )
        self.add_item(self.abundance_input)

    async def on_submit(self, interaction: discord.Interaction):
        """Handle the add abundance modal submission."""
        game_state = self.cog.game_state[self.channel_id]
        abundance = self.abundance_input.value
        player = interaction.user

        # Update the game state
        game_state["abundances"].append(abundance)
        await interaction.response.send_message(success(f"{player.mention} added **Abundance**: `{abundance}`"))  

        # Update the state tracker view
        await update_state_embed(self.cog, interaction.channel, game_state)

class RemoveAbundanceSelect(discord.ui.Select):
    def __init__(self, cog, interaction_channel_id):
        # Fetch the current abundances
        game_state = cog.game_state[interaction_channel_id]
        abundances = game_state["abundances"]
        # Transform abundances into SelectOption objects
        options = [discord.SelectOption(label=abundance, value=abundance) for abundance in abundances]

        # Initialize the parent class
        super().__init__(
            placeholder="Select an Abundance to remove",
            options=options,
        )

        # Store cog and channel ID for later use
        self.cog = cog
        self.channel_id = interaction_channel_id

    async def callback(self, interaction: discord.Interaction):
        """Handle the remove abundance selection."""
        game_state = self.cog.game_state[self.channel_id]
        abundance = self.values[0]  # Get the selected abundance
        player = interaction.user

        # Remove the abundance
        game_state["abundances"].remove(abundance)
        await interaction.response.send_message(error(f"{player.mention} removed **Abundance**: `{abundance}`"), ephemeral=False)

        # Update the state tracker view
        await update_state_embed(self.cog, interaction.channel, game_state)

class AddScarcityModal(discord.ui.Modal, title="Add Scarcity"):
    def __init__(self, cog, interaction_channel_id):
        super().__init__()
        self.cog = cog
        self.channel_id = interaction_channel_id

        # Input field for scarcity
        self.scarcity_input = discord.ui.TextInput(
            label="Scarcity",
            placeholder="Enter a new scarcity...",
            style=discord.TextStyle.short,
        )
        self.add_item(self.scarcity_input)

    async def on_submit(self, interaction: discord.Interaction):
        """Handle the add scarcity modal submission."""
        game_state = self.cog.game_state[self.channel_id]
        scarcity = self.scarcity_input.value
        player = interaction.user

        # Update the game state
        game_state["scarcities"].append(scarcity)
        await interaction.response.send_message(success(f"{player.mention} added **Scarcity**: `{scarcity}`"))  

        # Update the state tracker view
        await update_state_embed(self.cog, interaction.channel, game_state)

class RemoveScarcitySelect(discord.ui.Select):
    def __init__(self, cog, interaction_channel_id):
        # Fetch the current abundances
        game_state = cog.game_state[interaction_channel_id]
        scarcities = game_state["scarcities"]
        # Transform abundances into SelectOption objects
        options = [discord.SelectOption(label=scarcity, value=scarcity) for scarcity in scarcities]

        # Initialize the parent class
        super().__init__(
            placeholder="Select a Scarcity to remove",
            options=options,
        )

        # Store cog and channel ID for later use
        self.cog = cog
        self.channel_id = interaction_channel_id

    async def callback(self, interaction: discord.Interaction):
        """Handle the remove abundance selection."""
        game_state = self.cog.game_state[self.channel_id]
        scarcity = self.values[0]  # Get the selected abundance
        player = interaction.user

        # Remove the abundance
        game_state["scarcities"].remove(scarcity)
        await interaction.response.send_message(error(f"{player.mention} removed **Scarcity**: `{scarcity}`"), ephemeral=False)

        # Update the state tracker view
        await update_state_embed(self.cog, interaction.channel, game_state)