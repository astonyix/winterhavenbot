import discord
from discord.ext import commands
from discord.ext import tasks
import asyncio
from datetime import datetime, timedelta
import pytz
import asyncpg
import os

BUMP_REMINDER_CHANNEL_ID = 994238679910449266  # Bumping channel
MOD_ROLE_ID = 994238679306477680  # Mod role to ping for bump reminders

class BumpSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.next_bump_time = None
        self.db = None
        self.bot.loop.create_task(self.init_db())
        self.bump_check.start()
        print("Initializing BumpSystem cog")

    async def init_db(self):
        """Initialize database connection"""
        try:
            print("Initializing database connection for bump system...")
            self.db = await asyncpg.create_pool(os.environ['DATABASE_URL'])

            # Create table if it doesn't exist
            async with self.db.acquire() as conn:
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS bump_data (
                        id SERIAL PRIMARY KEY,
                        next_bump_time TIMESTAMP WITH TIME ZONE
                    )
                ''')

            # Load existing data
            async with self.db.acquire() as conn:
                row = await conn.fetchrow(
                    'SELECT next_bump_time FROM bump_data ORDER BY id DESC LIMIT 1'
                )
                if row:
                    self.next_bump_time = row['next_bump_time']
                    print(f"Loaded bump data: Next={self.next_bump_time}")
                else:
                    print("No existing bump data found")

        except Exception as e:
            print(f"Error initializing bump database: {e}")

    async def save_bump_data(self):
        """Save bump data to database"""
        if not self.db:
            print("Database not initialized")
            return

        try:
            async with self.db.acquire() as conn:
                await conn.execute(
                    'INSERT INTO bump_data (next_bump_time) VALUES ($1)',
                    self.next_bump_time
                )
                print(f"Saved bump data: Next={self.next_bump_time}")
        except Exception as e:
            print(f"Error saving bump data: {e}")

    @commands.command()
    async def bump(self, ctx, minutes: int = 119):
        """Set the bump timer (default 119 minutes)"""
        if ctx.channel.id != BUMP_REMINDER_CHANNEL_ID:
            await ctx.send("Please use this command in the bump channel!")
            return

        if minutes <= 0:
            await ctx.send("❌ Please specify a positive number of minutes.")
            return

        if minutes > 240:  # 4 hours max
            await ctx.send("❌ Maximum time is 240 minutes (4 hours).")
            return

        try:
            self.next_bump_time = datetime.now(pytz.UTC) + timedelta(minutes=minutes)
            await self.save_bump_data()

            next_bump_str = self.next_bump_time.strftime("%H:%M UTC")
            await ctx.send(
                f"🔔 <@&{MOD_ROLE_ID}>\n"
                f"Bump timer set for {minutes} minutes.\n"
                f"Next bump will be available at: `{next_bump_str}`\n"
                f"I'll ping you again when it's time!"
            )
        except Exception as e:
            print(f"Error in bump command: {e}")
            await ctx.send("❌ Error setting bump timer.")

    @commands.command()
    async def bumpstatus(self, ctx):
        """Check when the next bump is available"""
        if ctx.channel.id != BUMP_REMINDER_CHANNEL_ID:
            await ctx.send("Please use this command in the bump channel!")
            return

        try:
            if not self.next_bump_time:
                await ctx.send("✅ No bump timer set. You can bump now!")
                return

            current_time = datetime.now(pytz.UTC)
            if current_time >= self.next_bump_time:
                await ctx.send(
                    f"✅ Server can be bumped now!\n"
                    f"Use `!bump` to set a new timer."
                )
            else:
                time_until = self.next_bump_time - current_time
                minutes_left = int(time_until.total_seconds() / 60)
                await ctx.send(
                    f"⏰ Next bump available in: {minutes_left} minutes\n"
                    f"(`{self.next_bump_time.strftime('%H:%M UTC')}`)"
                )

        except Exception as e:
            print(f"Error in bumpstatus: {e}")
            await ctx.send("❌ Error checking bump status.")

    @tasks.loop(minutes=1)
    async def bump_check(self):
        """Check if it's time for the next bump"""
        if not self.next_bump_time:
            return

        current_time = datetime.now(pytz.UTC)
        if current_time >= self.next_bump_time:
            channel = self.bot.get_channel(BUMP_REMINDER_CHANNEL_ID)
            if channel:
                await channel.send(
                    f"🔔 <@&{MOD_ROLE_ID}> Bump timer finished!\n"
                    f"You can bump the server now! ⏰"
                )
                self.next_bump_time = None
                await self.save_bump_data()

    @bump_check.before_loop
    async def before_bump_check(self):
        """Wait until bot is ready before starting the loop"""
        await self.bot.wait_until_ready()

    def cog_unload(self):
        """Clean up when cog is unloaded"""
        self.bump_check.cancel()

async def setup(bot):
    await bot.add_cog(BumpSystem(bot))
    print("BumpSystem cog setup complete")