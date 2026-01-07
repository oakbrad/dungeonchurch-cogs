import random

import discord
from discord.ui import Button, View
import aiohttp
from redbot.core import commands, Config, checks


class RerollButton(Button):
    """Button to reroll a random restaurant."""

    def __init__(self, cog, sheet_id: str, api_key: str, openai_key: str | None, prompt: str):
        super().__init__(label="Reroll", style=discord.ButtonStyle.danger, emoji="🎲")
        self.cog = cog
        self.sheet_id = sheet_id
        self.api_key = api_key
        self.openai_key = openai_key
        self.prompt = prompt

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

        content = await self.cog._build_message(name, idx, self.openai_key, self.prompt)

        new_view = RollFoodView(cog=self.cog, sheet_id=self.sheet_id, api_key=self.api_key, link=link, openai_key=self.openai_key, prompt=self.prompt)
        new_view.set_message(self.view.message)
        await self.view.message.edit(content=content, view=new_view)


class RollFoodView(View):
    """View containing reroll and order buttons."""

    def __init__(self, cog, sheet_id: str, api_key: str, link: str, openai_key: str | None = None, prompt: str = "", timeout: float = 300):
        super().__init__(timeout=timeout)
        self.message = None
        self.add_item(RerollButton(cog, sheet_id, api_key, openai_key, prompt))
        self.add_item(Button(label="Start Group Order", style=discord.ButtonStyle.link, url=link))

    def set_message(self, message: discord.Message):
        self.message = message

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.edit(view=None)
            except discord.NotFound:
                pass


DEFAULT_PROMPT = (
    "You are the Oracle of Pyora, a concierge wizard who keeps the lore and secrets of "
    "this dark fantasy realm. You will respond in character, role playing as the omniscient "
    "librarian who deigns to help with banal requests. Your response should be short, succinct, "
    "and spoken in a cryptic, knowing manner which would fit someone with great secrets held closely. "
    "The response should be one or two sentences at most. Right now, you will respond as this character "
    "as if you were asked about a local tavern and restaurant and what they might find there and your "
    "opinion of it. Use the restaurant name to infer what it is. The name of the tavern is "
)


class RollFood(commands.Cog):
    """Roll a random restaurant from a Google Spreadsheet."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=4206661312)
        default_guild = {
            "sheet_id": None,
            "prompt": None
        }
        self.config.register_guild(**default_guild)

    async def _get_oracle_text(self, restaurant_name: str, openai_key: str, prompt: str) -> str | None:
        """Get flavor text from OpenAI. Returns None on failure."""
        import logging
        log = logging.getLogger("red.rollfood")

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {openai_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-4o-mini",
            "max_tokens": 150,
            "messages": [
                {"role": "user", "content": prompt + restaurant_name}
            ]
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as resp:
                    if resp.status != 200:
                        body = await resp.text()
                        log.error(f"OpenAI API error {resp.status}: {body}")
                        return None
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"]
        except Exception as e:
            log.error(f"OpenAI request failed: {e}")
            return None

    async def _get_sheet_values(self, sheet_id: str, api_key: str):
        """Fetch all values from a public Google Sheet."""
        """The first column should be restaurant name, the second column should be the order link."""
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
        """Configure the Google Sheet & optional prompt to use."""

    @foodconfig.command(name="sheet")
    async def sheet(self, ctx: commands.Context, sheet_id: str):
        """Set the Sheet ID for this guild."""
        await self.config.guild(ctx.guild).sheet_id.set(sheet_id)
        await ctx.send("`✅ Sheet ID saved.`", ephemeral=True)

    @foodconfig.command(name="prompt")
    async def prompt(self, ctx: commands.Context, *, prompt: str = None):
        """Set a custom AI prompt. Use 'None' to reset to default. This is optional.

        The restaurant name will be appended to the end of your prompt.
        The response will be included as "flavor text" when rolling a restaurant.
        """
        if prompt and prompt.lower() == "none":
            prompt = None
        await self.config.guild(ctx.guild).prompt.set(prompt)
        if prompt:
            await ctx.send("`✅ Custom prompt saved.`", ephemeral=True)
        else:
            await ctx.send("`✅ Prompt reset to default.`", ephemeral=True)

    @foodconfig.command(name="settings")
    async def settings(self, ctx: commands.Context) -> None:
        """Display the current RollFood settings."""
        sheets_key = (await self.bot.get_shared_api_tokens("googlesheets")).get("api_key")
        openai_key = (await self.bot.get_shared_api_tokens("openai")).get("api_key")
        sheet_id = await self.config.guild(ctx.guild).sheet_id()
        custom_prompt = await self.config.guild(ctx.guild).prompt()

        setting_list = {
            "Google Sheet ID": sheet_id or "Not Set",
            "Google Sheets API Key": "✅ Set" if sheets_key else "❌ Not Set",
            "OpenAI API Key": "✅ Set" if openai_key else "❌ Not Set (AI flavor text disabled)",
            "Custom Prompt": custom_prompt[:100] + "..." if custom_prompt and len(custom_prompt) > 100 else (custom_prompt or "Using default Oracle of Pyora prompt"),
        }

        embed = discord.Embed(
            title="🎲🥡 RollFood Settings",
            color=0xff6600
        )
        for setting, value in setting_list.items():
            embed.add_field(name=setting, value=f"```{value}```", inline=False)
        await ctx.send(embed=embed)

    async def _build_message(self, name: str, idx: int, openai_key: str | None, prompt: str) -> str:
        """Build the message content, optionally with AI prompt flavor text."""
        content = (
            f"# 🎲🥡 {name}\n"
            f"> *You rolled:* **{idx}**"
        )
        if openai_key:
            oracle_text = await self._get_oracle_text(name, openai_key, prompt)
            if oracle_text:
                # Bold the restaurant name in the oracle text and italicize
                oracle_formatted = oracle_text.replace(name, f"**{name}**")
                content += f"\n\n*\"{oracle_formatted}\"*"
        return content

    @commands.hybrid_command()
    async def rollfood(self, ctx: commands.Context):
        """Roll a random restaurant from the list."""
        sheets_key = (await self.bot.get_shared_api_tokens("googlesheets")).get("api_key")
        openai_key = (await self.bot.get_shared_api_tokens("openai")).get("api_key")
        sheet_id = await self.config.guild(ctx.guild).sheet_id()
        custom_prompt = await self.config.guild(ctx.guild).prompt()
        prompt = custom_prompt or DEFAULT_PROMPT

        if not sheet_id or not sheets_key:
            await ctx.send("❌ Spreadsheet or API key not configured.", ephemeral=True)
            return

        await ctx.defer()
        try:
            values = await self._get_sheet_values(sheet_id, sheets_key)
        except Exception as e:
            await ctx.send(f"`❌ Could not fetch sheet: {e}`", ephemeral=True)
            return

        if len(values) < 2:
            await ctx.send("`❌ No restaurants found in the sheet.`", ephemeral=True)
            return

        entries = values[1:]
        idx, (name, link) = random.choice(list(enumerate(entries, start=1)))

        content = await self._build_message(name, idx, openai_key, prompt)

        view = RollFoodView(cog=self, sheet_id=sheet_id, api_key=sheets_key, link=link, openai_key=openai_key, prompt=prompt)
        message = await ctx.send(content, view=view)
        view.set_message(message)
