from .ghostsync import GhostSync

async def setup(bot):
    await bot.add_cog(GhostSync(bot))
