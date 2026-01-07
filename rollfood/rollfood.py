import random

import discord
from discord.ui import Button, View
import aiohttp
from redbot.core import commands, Config, checks


class RerollButton(Button):
    """Button to reroll a random restaurant."""

    def __init__(self, cog, sheet_id: str, api_key: str):
        super().__init__(label="Reroll", style=discord.ButtonStyle.danger, emoji="🎲")
        self.cog = cog
        self.sheet_id = sheet_id
        self.api_key = api_key

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            values = await self.cog._get_sheet_values(self.sheet_id, self.api_key)
        except Exception as e:
            await interaction.followup.send(f"`❌ Could not fetch sheet: {e}`", ephemeral=True)
            return

        if len(values) < 2:
            await interaction.followup.send("`❌ No restaurants found in the sheet.`", ephemeral=True)
            return

        entries = values[1:]
        idx, (name, link) = random.choice(list(enumerate(entries, start=1)))

        content = (
            f"# 🎲🥡 {name}\n"
            f"> *You rolled:* **{idx}**"
        )

        new_view = RollFoodView(cog=self.cog, sheet_id=self.sheet_id, api_key=self.api_key, link=link)
        new_view.set_message(self.view.message)
        await self.view.message.edit(content=content, view=new_view)


class RollFoodView(View):
    """View containing reroll and order buttons."""

    def __init__(self, cog, sheet_id: str, api_key: str, link: str, timeout: float = 300):
        super().__init__(timeout=timeout)
        self.message = None
        self.add_item(RerollButton(cog, sheet_id, api_key))
        self.add_item(Button(label="Start Group Order", style=discord.ButtonStyle.link, url=link))

    def set_message(self, message: discord.Message):
        self.message = message

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.edit(view=None)
            except discord.NotFound:
                pass


class RollFood(commands.Cog):
    """Roll a random restaurant from a Google Spreadsheet."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=4206661312)
        default_guild = {
            "sheet_id": None
        }
        self.config.register_guild(**default_guild)

    async def _get_sheet_values(self, sheet_id: str, api_key: str):
        """Fetch all values from a public Google Sheet."""
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/Sheet1?key={api_key}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    raise Exception(f"API returned status {resp.status}")
                data = await resp.json()
                return data.get("values", [])

    #
    # Command methods
    #
    @commands.group()
    @checks.is_owner()
    async def foodconfig(self, ctx: commands.Context) -> None:
        """Configure the Google Spreadsheet to use for the restaurant list."""

    @foodconfig.command(name="sheet")
    async def sheet(self, ctx: commands.Context, sheet_id: str):
        """Set the Sheet ID for this guild."""
        await self.config.guild(ctx.guild).sheet_id.set(sheet_id)
        await ctx.send("`✅ Sheet ID saved.`", ephemeral=True)

    @commands.hybrid_command()
    async def rollfood(self, ctx: commands.Context):
        """Roll a random restaurant from the list."""
        api_key = (await self.bot.get_shared_api_tokens("googlesheets")).get("api_key")
        sheet_id = await self.config.guild(ctx.guild).sheet_id()

        if not sheet_id or not api_key:
            await ctx.send("❌ Spreadsheet or API key not configured.", ephemeral=True)
            return

        await ctx.defer()
        try:
            values = await self._get_sheet_values(sheet_id, api_key)
        except Exception as e:
            await ctx.send(f"`❌ Could not fetch sheet: {e}`", ephemeral=True)
            return

        if len(values) < 2:
            await ctx.send("`❌ No restaurants found in the sheet.`", ephemeral=True)
            return

        entries = values[1:]
        idx, (name, link) = random.choice(list(enumerate(entries, start=1)))

        content = (
            f"# 🎲🥡 {name}\n"
            f"> *You rolled:* **{idx}**"
        )

        view = RollFoodView(cog=self, sheet_id=sheet_id, api_key=api_key, link=link)
        message = await ctx.send(content, view=view)
        view.set_message(message)
