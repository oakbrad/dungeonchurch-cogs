# CLAUDE.md

This repository contains Python cog plugins for [Red-DiscordBot](https://github.com/Cog-Creators/Red-DiscordBot), a modular Discord bot framework.

## Repository Structure

```
dungeonchurch-cogs/
├── cogname/
│   ├── __init__.py      # Cog loader with setup() function
│   ├── cogname.py       # Main cog implementation
│   └── info.json        # Cog metadata and requirements
├── info.json            # Repository-level metadata
└── README.md
```

Each cog lives in its own directory with a consistent structure.

## Cog Anatomy

### `__init__.py`

The entry point that Red uses to load the cog. Two patterns are used:

**Simple pattern:**
```python
from .cogname import CogClass

async def setup(bot):
    await bot.add_cog(CogClass(bot))
```

**With end user data statement (preferred for distribution):**
```python
import json
from pathlib import Path
from redbot.core.bot import Red
from .cogname import CogClass

with Path(__file__).parent.joinpath("info.json").open() as fp:
    __red_end_user_data_statement__ = json.load(fp)["end_user_data_statement"]

async def setup(bot: Red) -> None:
    cog = CogClass(bot)
    await bot.add_cog(cog)
```

### `info.json`

Required metadata for Red's cog installer:

```json
{
    "name": "CogName",
    "author": ["DM Brad"],
    "short": "Brief description",
    "description": "Longer description of functionality",
    "install_msg": "Post-install instructions for users",
    "requirements": ["package1", "package2"],
    "tags": ["tag1", "tag2"],
    "min_bot_version": "3.5.0",
    "min_python_version": [3, 11, 0],
    "end_user_data_statement": "This cog does not persistently store data about users."
}
```

### Main Cog Class

```python
from redbot.core import commands, Config, checks
from redbot.core.utils.chat_formatting import error, question, success
import discord

class CogName(commands.Cog):
    """Docstring appears in help text."""

    __author__ = "DM Brad"
    __version__ = "0.1"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=UNIQUE_INT, force_registration=True
        )
        default_guild = {
            "setting_name": "default_value",
        }
        self.config.register_guild(**default_guild)
```

## Core Patterns

### Configuration with `Config`

Red's Config system provides persistent per-guild (or global) settings:

```python
# In __init__
self.config = Config.get_conf(self, identifier=4206661044, force_registration=True)
default_guild = {"setting": "value"}
self.config.register_guild(**default_guild)

# Reading
value = await self.config.guild(ctx.guild).setting()

# Writing
await self.config.guild(ctx.guild).setting.set(new_value)

# Async context manager for lists/dicts
async with self.config.status_messages() as messages:
    messages.append(new_item)
```

Use `register_global()` for bot-wide settings instead of per-guild.

### Command Types

**Hybrid commands** (work as both prefix and slash):
```python
@commands.hybrid_command()
async def mycommand(self, ctx: commands.Context, arg: str) -> None:
    """Command description for help text."""
    await ctx.send("Response")
```

**Command groups** (for settings/admin commands):
```python
@commands.group()
@checks.is_owner()
async def cogconfig(self, ctx: commands.Context):
    """Parent command group."""
    pass

@cogconfig.command()
async def setting(self, ctx: commands.Context, value: str) -> None:
    """Subcommand."""
    await self.config.guild(ctx.guild).setting.set(value)
    await ctx.send(success("Setting updated."))
```

### API Keys

Use Red's shared API token storage:

```python
# Getting a key
key = (await self.bot.get_shared_api_tokens("openai")).get("api_key")

# User sets via: [p]set api openai api_key,<key>
```

Common keys used: `openai`, `googlesheets`

### Embeds for Settings Display

```python
embed = discord.Embed(
    title=":emoji: Cog Settings",
    color=0xff0000
)
for setting, value in settings_dict.items():
    embed.add_field(name=setting, value=f"```{value}```", inline=False)
await ctx.send(embed=embed)
```

### Background Tasks

```python
from discord.ext import tasks

def __init__(self, bot):
    self.update_task.start()

def cog_unload(self):
    self.update_task.cancel()

@tasks.loop(seconds=900)
async def update_task(self):
    # Task logic

@update_task.before_loop
async def before_update_task(self):
    await self.bot.wait_until_ready()
```

### Discord UI Components

```python
from discord.ui import Button, View

class MyView(View):
    def __init__(self, timeout: float = 300):
        super().__init__(timeout=timeout)
        self.message = None
        self.add_item(Button(label="Click", style=discord.ButtonStyle.primary))

    async def on_timeout(self):
        if self.message:
            await self.message.edit(view=None)
```

### HTTP Requests

Use `aiohttp` for async HTTP:

```python
import aiohttp

async with aiohttp.ClientSession() as session:
    async with session.get(url) as resp:
        if resp.status == 200:
            data = await resp.json()
```

## Style Conventions

### Imports
- Standard library first, then third-party, then Red/discord imports
- `from redbot.core import commands, Config, checks`
- `from redbot.core.utils.chat_formatting import error, question, success`

### Naming
- Class names: `PascalCase` (e.g., `RollFood`, `RandomStatus`)
- Methods/variables: `snake_case`
- Config identifiers: unique integers (pattern: `420666XXXX`)
- Private helper methods: prefix with `_` (e.g., `_format_activity_type`)

### Type Hints
- Used on command methods: `async def cmd(self, ctx: commands.Context, arg: str) -> None:`
- Optional for internal methods
- Use `str | None` syntax (Python 3.11+)

### Docstrings
- Required on cog class (shown in `[p]help`)
- Required on commands (shown in command help)
- Brief, user-facing descriptions

### Formatting
- Response helpers: `success()`, `error()`, `question()` from chat_formatting
- Backticks for inline code in messages
- Embeds for displaying settings/complex data
- `ephemeral=True` for sensitive responses

### Error Handling
- Check for missing config/API keys before proceeding
- Use `ctx.defer()` before long operations
- Log errors with `logging.getLogger("red.cogname")`
