from .ghostlabel import GhostLabel

async def setup(bot):
    await bot.add_cog(GhostLabel(bot))
