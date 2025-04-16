import asyncio

import discord
import random
import gspread
from redbot.core import commands, Config, checks


class RollFood(commands.Cog):
    """Roll a random restaurant from a Google Spreadsheet."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=4206661312)
        default_guild = {
            "sheet_id": None
        }
        self.config.register_guild(**default_guild)

    def _get_sheet_values(self, sheet_id: str, api_key: str):
        # gspread client using API key for public sheet access
        client = gspread.Client(None)
        client.session.params.update({"key": api_key})
        sheet = client.open_by_key(sheet_id).sheet1
        return sheet.get_all_values()


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

    @commands.slash_command()
    async def rollfood(self, ctx: commands.Context):
        """Roll a random restaurant from the list"""
        # [p]set api googlesheets api_key,<paste here>
        api_key = (await self.bot.get_shared_api_tokens("googlesheets")).get("api_key")
        sheet_id = await self.config.guild(ctx.guild).sheet_id()

        if not sheet_id or not api_key:
            await ctx.send("❌ Spreadsheet or API key not configured.",ephemeral=True)
            return
        
        await ctx.defer()
        try:
            # run blocking function with async
            loop = asyncio.get_running_loop()
            values = await loop.run_in_executor(
                None, self._get_sheet_values, sheet_id, api_key
            )
        except Exception as e:
            await ctx.send(f"`❌ Could not fetch sheet: {e}`", ephemeral=True)
            return

        if len(values) < 2:
            await ctx.send("`❌ No restaurants found in the sheet.`", ephemeral=True)
            return

        # choose and enumerate entries to show roll number
        entries = values[1:]
        idx, (name, link) = random.choice(list(enumerate(entries, start=1)))
        await ctx.send(f"You rolled {idx}! 🍽️ **{name}**\nOrder here: {link}")