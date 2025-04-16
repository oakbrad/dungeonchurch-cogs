from .rollfood import RollFood

async def setup(bot):
    await bot.add_cog(RollFood(bot))