import discord
from discord import Embed, ui
from redbot.core.utils.chat_formatting import error, question, success

class GameInitView(ui.View):
    def __init__(self, cog):
        super().__init__()
        self.cog = cog

        # Add the link button at the end
        self.add_item(discord.ui.Button(
            label="Buy PDF",
            style=discord.ButtonStyle.link,
            emoji="📚",
            url="https://store.buriedwithoutceremony.com/collections/frontpage/products/the-quiet-year-pdf"
        ))

    @ui.button(label="Join", style=discord.ButtonStyle.primary, emoji="✅")
    async def join(self, interaction: discord.Interaction, button: ui.Button):
        """Add the player to the game."""
        game_state = self.cog.game_state[interaction.channel_id]
        player = interaction.user

        if player.id in [p.id for p in game_state["players"]]:
            await interaction.response.send_message(error("`You're already in the player list!`"), ephemeral=True)
            return
        
        # check player limit setting
        max_players = await self.cog.config.guild(interaction.guild).max_players()
        if max_players == len(game_state["players"]):
            await interaction.response.send_message(error("`Sorry, this game is already full.`"))
            return
        
        # add player to game
        game_state["players"].append(player.id)
        # add player to current round
        game_state["turn_tracker"]["remaining"].append(player.id)
        # assign role if in settings
        player_role = await self.cog.config.guild(interaction.guild).player_role()
        if player_role:
            await player.add_roles(interaction.guild.get_role(player_role))
        
        await interaction.response.send_message(
            "> *When we play [The Quiet Year](<https://buriedwithoutceremony.com/the-quiet-year>), we don't control specific characters or act out scenes. Instead, we all act as abstract social forces within the community. At any point, we might be representing a single person or a great many. This is a story about social forces and their impact on the land.*\n"
            f"### To begin the game, start a short discussion with your fellow players{' (<@&'+str(player_role)+'>)' if player_role else ''}:\n" 
            "> 1. **Introduce something about our terrain** - draw it on the map.\n"
            "> 2. **Name an important resource** for our community - add it to `Abundances` or `Scarcities`."
            "\n### Once everyone has done so, we will start the first week.", ephemeral=True
        )
        await interaction.channel.send(success(f"{player.mention} joined the game!"))
            

    @ui.button(label="Leave", style=discord.ButtonStyle.secondary, emoji="🚷")
    async def leave(self, interaction: discord.Interaction, button: ui.Button):
        """Remove player from the game."""
        game_state = self.cog.game_state[interaction.channel_id]
        player = interaction.user

        # Remove the player from the game
        if player.id in game_state["players"]:
            game_state["players"].remove(player.id)

            # Remove the player from turn tracker
            if player.id in game_state["turn_tracker"]["remaining"]:
                game_state["turn_tracker"]["remaining"].remove(player.id)
            if player.id in game_state["turn_tracker"]["taken"]:
                game_state["turn_tracker"]["taken"].remove(player.id)

            await interaction.response.send_message(error(f"{player.mention} left the game."), ephemeral=False)

            # Remove role if in settings
            player_role = await self.cog.config.guild(interaction.guild).player_role()
            if player_role:
                await player.remove_roles(interaction.guild.get_role(player_role))

        else:
            await interaction.response.send_message(error(f"`You can't leave if you didn't join.`"), ephemeral=True)

    @ui.button(label="Start Game", style=discord.ButtonStyle.green,emoji="▶️")
    async def start_game(self, interaction: discord.Interaction, button: ui.Button):
        """Start the game."""
        game_state = self.cog.game_state[interaction.channel_id]
        player = interaction.user

        if player.id not in game_state["players"]:
            await interaction.response.send_message(error("`Only a player in the game can start it!`"), ephemeral=True)
            return

        # Transition to the turn handler (placeholder)
        await interaction.response.send_message(success("The game has started!"), ephemeral=False)
        # Create the deck
        game_state["deck"] = self.cog.create_deck()
        # Start the turn loop
        await self.cog.start_turn_handler(interaction.channel_id)

    @ui.button(label="Cancel", style=discord.ButtonStyle.danger,emoji="✖️")
    async def cancel_game(self, interaction: discord.Interaction, button: ui.Button):
        """Cancel the game."""
        await interaction.response.defer(ephemeral=True)
        game_state = self.cog.game_state[interaction.channel_id]
        player = interaction.user

        # End the game
        reason = f"The game was cancelled by {interaction.user.mention}."
        await self.cog.end_game(interaction.channel_id, interaction, reason)

class GameStateView(ui.View):
    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    @ui.button(label="Add Abundance", style=discord.ButtonStyle.secondary)
    async def add_abundance(self, interaction: discord.Interaction, button: ui.Button):
        """Add an Abundance to the game state."""
        game_state = self.cog.game_state[interaction.channel_id]
        player = interaction.user

        if player.id not in game_state["players"]:
            await interaction.response.send_message("You must join the game first!", ephemeral=True)
            return

        # Ask for Abundance input (placeholder for future modal implementation)
        abundance = "Example Abundance"  # Replace with input modal later
        game_state["abundances"].append(abundance)
        await interaction.response.send_message(f"Added Abundance: {abundance}", ephemeral=False)

    @ui.button(label="Add Scarcity", style=discord.ButtonStyle.secondary)
    async def add_scarcity(self, interaction: discord.Interaction, button: ui.Button):
        """Add a Scarcity to the game state."""
        game_state = self.cog.game_state[interaction.channel_id]
        player = interaction.user

        if player.id not in game_state["players"]:
            await interaction.response.send_message(error("`You must join the game first!`"), ephemeral=True)
            return

        # Ask for Scarcity input (placeholder for future modal implementation)
        scarcity = "Example Scarcity"  # Replace with input modal later
        game_state["scarcities"].append(scarcity)
        await interaction.response.send_message(f"Added Scarcity: {scarcity}", ephemeral=False)