from .thequietyear import TheQuietYear

async def setup(bot):
    await bot.add_cog(TheQuietYear(bot))