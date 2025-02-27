import discord
from discord.ext import commands
import asyncpg
import os
import random
from datetime import datetime
import pytz

class Leveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.xp_cooldown = commands.CooldownMapping.from_cooldown(1, 60, commands.BucketType.user)
        self.level_roles = {
            1: "Winter Villager",
            3: "Frost Forager",
            5: "Squire of the Frost",
            10: "Glacial Knight",
            15: "Aurora Guardian",
            20: "Snowdrift Ranger",
            25: "Iceborne Sentinel",
            30: "Polar Vanguard",
            35: "Blizzard Champion",
            40: "Everfrost Warden",
            45: "Frostfang Warrior",
            50: "Glacier Commander",
            55: "Wraith of Winter",
            60: "Northern Monarch",
            65: "Yulebringer",
            70: "Arctic Sovereign",
            75: "Celestial Frostwalker",
            80: "Snowstorm Overlord",
            85: "Eternal Glacier Lord",
            90: "Spirit of the North",
            95: "Frozen Deity",
            100: "King/Queen of the Everwinter"
        }
        self.level_up_channel_id = 1342884630671523890
        self.verified_role_id = 994238679281303605
        self.db = None
        self.bot.loop.create_task(self.init_db())

    async def init_db(self):
        try:
            print("Initializing database connection...")
            self.db = await asyncpg.create_pool(os.environ['DATABASE_URL'])
            print("Successfully initialized leveling database")
        except Exception as e:
            print(f"Error initializing database: {e}")

    def calculate_xp(self, level):
        """Calculate XP needed for next level using a balanced progression curve"""
        if level <= 3:
            return 250 * level
        elif level <= 10:
            base_xp = 1000
            scaling_factor = 1.5
            return int(base_xp * (scaling_factor ** (level - 3)))
        else:
            base_xp = 100
            scaling_factor = 2.5
            level_multiplier = 75
            return int(base_xp * (scaling_factor ** level) + (level_multiplier * level ** 2))

    async def add_xp(self, user_id: int, xp_to_add: int):
        if not self.db:
            print("Database connection not initialized!")
            return None

        try:
            async with self.db.acquire() as conn:
                print(f"Adding {xp_to_add} XP to user {user_id}")

                # Get current user data or create new entry
                user_data = await conn.fetchrow(
                    '''
                    INSERT INTO levels (user_id, xp, level)
                    VALUES ($1, $2, 1)
                    ON CONFLICT (user_id) 
                    DO UPDATE SET xp = levels.xp + $2
                    RETURNING xp, level
                    ''',
                    user_id, xp_to_add
                )

                current_xp = user_data['xp']
                current_level = user_data['level']

                print(f"User {user_id} now has {current_xp} XP at level {current_level}")

                # Calculate if level up occurred
                new_level = current_level
                while current_xp >= self.calculate_xp(new_level):
                    new_level += 1

                level_up_occurred = new_level > current_level
                is_new_user = current_xp == xp_to_add and current_level == 1

                # Find the user in any guild
                for guild in self.bot.guilds:
                    member = guild.get_member(user_id)
                    if member:
                        level_up_channel = self.bot.get_channel(self.level_up_channel_id)
                        if level_up_channel:
                            if level_up_occurred:
                                print(f"User {user_id} leveled up to {new_level}!")
                                await level_up_channel.send(
                                    f"🎉 **LEVEL UP!** 🎉\n"
                                    f"{member.mention} has reached level **{new_level}**! "
                                    f"Keep chatting to earn more XP! ❄️"
                                )
                                await self.handle_role_rewards(member, new_level, level_up_channel)
                            elif is_new_user:
                                winter_villager_role = discord.utils.get(guild.roles, name="Winter Villager")
                                if winter_villager_role and winter_villager_role not in member.roles:
                                    try:
                                        await member.add_roles(winter_villager_role)
                                        print(f"Added Winter Villager role to {member.name}")
                                        await level_up_channel.send(
                                            f"🎉 Welcome {member.mention}! Congratulations on your first message - "
                                            f"you're now level 1 and have received the Winter Villager role! Keep chatting to earn more XP! ❄️"
                                        )
                                    except Exception as e:
                                        print(f"Error adding Winter Villager role: {e}")
                        break

                if level_up_occurred:
                    await conn.execute(
                        'UPDATE levels SET level = $1 WHERE user_id = $2',
                        new_level, user_id
                    )
                    return new_level
                return None

        except Exception as e:
            print(f"Error in add_xp: {e}")
            return None

    async def handle_role_rewards(self, member, new_level, level_up_channel):
        """Handle role rewards and removal of previous roles"""
        try:
            # First ensure Winter Villager role is present for all leveled users
            winter_villager_role = discord.utils.get(member.guild.roles, name="Winter Villager")
            if winter_villager_role and winter_villager_role not in member.roles:
                await member.add_roles(winter_villager_role)
                print(f"Added missing Winter Villager role to {member.name} during level up")

            # Special case for verified roles at level 3
            if new_level >= 3:
                # Add emoji verified role
                emoji_verified_role = member.guild.get_role(994238679281303605)
                if emoji_verified_role and emoji_verified_role not in member.roles:
                    await member.add_roles(emoji_verified_role)
                    await level_up_channel.send(
                        f"✨ {member.mention} has earned the **Emoji Verified** role! ✨"
                    )
                    print(f"Added emoji verified role to {member.name}")

                # Add VC verified role
                vc_verified_role = member.guild.get_role(1342949414649593887)
                if vc_verified_role and vc_verified_role not in member.roles:
                    await member.add_roles(vc_verified_role)
                    await level_up_channel.send(
                        f"🎤 {member.mention} has earned the **VC Verified** role! 🎤"
                    )
                    print(f"Added VC verified role to {member.name}")

            # Remove previous level roles before adding new one
            current_level_roles = []
            for level, role_name in self.level_roles.items():
                role = discord.utils.get(member.guild.roles, name=role_name)
                if role and role in member.roles:
                    current_level_roles.append(role)

            if current_level_roles:
                await member.remove_roles(*current_level_roles)
                print(f"Removed previous level roles from {member.name}")

            # Add new level role if applicable
            for level, role_name in sorted(self.level_roles.items(), reverse=True):
                if new_level >= level:
                    role = discord.utils.get(member.guild.roles, name=role_name)
                    if role and role not in member.roles:
                        await member.add_roles(role)
                        await level_up_channel.send(
                            f"🎊 {member.mention} has earned the **{role_name}** role! 🎊"
                        )
                        print(f"Added role {role_name} to {member.name}")
                    break

        except Exception as e:
            print(f"Error handling role rewards: {e}")

    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle message events for XP"""
        if message.author.bot or not message.guild:
            print(f"Skipping XP for bot or non-guild message from {message.author.name}")
            return

        print(f"Processing message from {message.author.name} (ID: {message.author.id})")

        # Check if user is on cooldown
        bucket = self.xp_cooldown.get_bucket(message)
        retry_after = bucket.update_rate_limit()
        if retry_after:
            print(f"User {message.author.name} is on cooldown for {retry_after:.2f} seconds")
            return

        # Random XP between 15-25
        xp_to_add = random.randint(15, 25)
        print(f"Attempting to add {xp_to_add} XP to {message.author.name}")
        await self.add_xp(message.author.id, xp_to_add)


    @commands.command()
    async def rank(self, ctx, member: discord.Member = None):
        """Check your or someone else's rank"""
        if not self.db:
            await ctx.send("Leveling system is currently initializing. Please try again in a moment.")
            return

        member = member or ctx.author

        async with self.db.acquire() as conn:
            user_data = await conn.fetchrow(
                'SELECT xp, level FROM levels WHERE user_id = $1',
                member.id
            )

            if not user_data:
                await ctx.send(f"{member.display_name} hasn't earned any XP yet!")
                return

            xp = user_data['xp']
            level = user_data['level']
            xp_needed = self.calculate_xp(level + 1)

            embed = discord.Embed(
                title=f"Rank - {member.display_name}",
                color=discord.Color.blue()
            )
            embed.add_field(name="Level", value=str(level), inline=True)
            embed.add_field(name="XP", value=f"{xp}/{xp_needed}", inline=True)
            embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)

            await ctx.send(embed=embed)

    @commands.command()
    async def leaderboard(self, ctx):
        """Show the server's top 10 members"""
        if not self.db:
            await ctx.send("Leveling system is currently initializing. Please try again in a moment.")
            return

        async with self.db.acquire() as conn:
            top_users = await conn.fetch(
                '''
                SELECT user_id, xp, level 
                FROM levels 
                ORDER BY xp DESC 
                LIMIT 10
                '''
            )

            if not top_users:
                await ctx.send("No one has earned any XP yet!")
                return

            embed = discord.Embed(
                title="🏆 Leaderboard",
                color=discord.Color.gold()
            )

            for idx, user in enumerate(top_users, 1):
                member = ctx.guild.get_member(user['user_id'])
                if member:
                    name = member.display_name
                    embed.add_field(
                        name=f"#{idx} {name}",
                        value=f"Level: {user['level']} | XP: {user['xp']}",
                        inline=False
                    )

            await ctx.send(embed=embed)

    @commands.command()
    async def givexp(self, ctx, member: discord.Member, amount: int):
        """[Admin] Give XP to a user"""
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("❌ This command requires Administrator permissions.")
            return

        if amount <= 0:
            await ctx.send("❌ Please specify a positive amount of XP.")
            return

        print(f"Admin {ctx.author.name} giving {amount} XP to {member.name}")
        new_level = await self.add_xp(member.id, amount)

        async with self.db.acquire() as conn:
            user_data = await conn.fetchrow(
                'SELECT xp, level FROM levels WHERE user_id = $1',
                member.id
            )

            if user_data:
                await ctx.send(f"✅ Gave {amount} XP to {member.mention}. They now have {user_data['xp']} XP (Level {user_data['level']}).")

                if new_level:
                    level_up_channel = self.bot.get_channel(self.level_up_channel_id)
                    if level_up_channel:
                        await self.handle_role_rewards(member, new_level, level_up_channel)
            else:
                await ctx.send("❌ Error updating XP.")

    @commands.command()
    async def removexp(self, ctx, member: discord.Member, amount: int):
        """[Admin] Remove XP from a user"""
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("❌ This command requires Administrator permissions.")
            return

        if amount <= 0:
            await ctx.send("❌ Please specify a positive amount of XP to remove.")
            return

        print(f"Admin {ctx.author.name} removing {amount} XP from {member.name}")

        try:
            async with self.db.acquire() as conn:
                user_data = await conn.fetchrow(
                    'SELECT xp, level FROM levels WHERE user_id = $1',
                    member.id
                )

                if not user_data:
                    await ctx.send(f"❌ {member.mention} doesn't have any XP yet.")
                    return

                new_xp = max(0, user_data['xp'] - amount)

                await conn.execute(
                    'UPDATE levels SET xp = $1 WHERE user_id = $2',
                    new_xp, member.id
                )

                new_level = 1
                while new_xp >= self.calculate_xp(new_level):
                    new_level += 1

                if new_level != user_data['level']:
                    await conn.execute(
                        'UPDATE levels SET level = $1 WHERE user_id = $2',
                        new_level, member.id
                    )

                    level_up_channel = self.bot.get_channel(self.level_up_channel_id)
                    if level_up_channel:
                        await self.handle_role_rewards(member, new_level, level_up_channel)

                await ctx.send(f"✅ Removed {amount} XP from {member.mention}. They now have {new_xp} XP (Level {new_level}).")

        except Exception as e:
            print(f"Error removing XP: {e}")
            await ctx.send("❌ Error updating XP.")

async def setup(bot):
    await bot.add_cog(Leveling(bot))