import discord
from discord.ext import commands
import asyncpg
import os
from datetime import datetime, timedelta
import random

class EconomySystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = None
        self.coin_cooldowns = {}
        self.bot.loop.create_task(self.init_db())
        print("Initializing EconomySystem cog")

    async def init_db(self):
        """Initialize database connection"""
        try:
            self.db = await asyncpg.create_pool(os.environ['DATABASE_URL'])
            # Create necessary tables if they don't exist
            async with self.db.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS user_economy (
                        user_id BIGINT PRIMARY KEY,
                        pawcoins INTEGER DEFAULT 0,
                        last_coin_earned TIMESTAMP WITH TIME ZONE
                    )
                """)
            print("Economy system database connection initialized")
        except Exception as e:
            print(f"Error initializing economy system database: {e}")

    @commands.Cog.listener()
    async def on_message(self, message):
        """Award PawCoins for chatting"""
        if message.author.bot or not message.guild:
            return

        # Check cooldown (2 minutes)
        now = datetime.utcnow()
        user_id = message.author.id
        last_earned = self.coin_cooldowns.get(user_id)
        
        if last_earned and now - last_earned < timedelta(minutes=2):
            return

        try:
            # Award 1-2 PawCoins
            coins = random.randint(1, 2)
            
            async with self.db.acquire() as conn:
                await conn.execute("""
                    INSERT INTO user_economy (user_id, pawcoins, last_coin_earned)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (user_id)
                    DO UPDATE SET 
                        pawcoins = user_economy.pawcoins + $2,
                        last_coin_earned = $3
                """, user_id, coins, now)

            self.coin_cooldowns[user_id] = now

        except Exception as e:
            print(f"Error awarding PawCoins: {e}")

    @commands.command(name="balance", aliases=["bal", "coins"])
    async def check_balance(self, ctx):
        """Check your PawCoin balance"""
        try:
            balance = await self.db.fetchval(
                "SELECT pawcoins FROM user_economy WHERE user_id = $1",
                ctx.author.id
            ) or 0

            embed = discord.Embed(
                title="🪙 PawCoin Balance",
                description=f"You have **{balance:,}** PawCoins",
                color=discord.Color.gold()
            )
            
            embed.set_footer(text="Earn PawCoins by chatting and participating!")
            await ctx.send(embed=embed)

        except Exception as e:
            print(f"Error checking balance: {e}")
            await ctx.send("❌ Error checking your balance. Please try again.")

async def setup(bot):
    await bot.add_cog(EconomySystem(bot))
