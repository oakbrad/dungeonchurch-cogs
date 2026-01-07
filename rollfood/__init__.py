"""Package for RollFood cog."""

import json
from pathlib import Path

from redbot.core.bot import Red

from .rollfood import RollFood

async def setup(bot: Red) -> None:
    """Load RollFood cog."""
    cog = RollFood(bot)
    await bot.add_cog(cog)
