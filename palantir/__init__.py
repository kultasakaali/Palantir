from .palantir import Palantir

async def setup(bot):
    await bot.add_cog(Palantir(bot))
