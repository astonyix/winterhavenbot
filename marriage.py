import discord
from discord.ext import commands
import asyncio
import config
import os
import asyncpg

class Marriage(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pending_proposals = {}
        self.db = None
        self.bot.loop.create_task(self.init_db())
        print("Marriage cog initialized")

    async def init_db(self):
        """Initialize database connection"""
        try:
            self.db = await asyncpg.create_pool(os.environ['DATABASE_URL'])
            print("Marriage database connection initialized")
        except Exception as e:
            print(f"Error initializing marriage database: {e}")

    async def check_age_role(self, member: discord.Member) -> bool:
        """Check if member has the 18+ role"""
        return any(role.id == config.ADULT_ROLE_ID for role in member.roles)

    async def get_spouse(self, user_id: int) -> int:
        """Get user's spouse ID if married"""
        if not self.db:
            return None

        try:
            spouse = await self.db.fetchrow("""
                SELECT 
                    CASE 
                        WHEN user1_id = $1 THEN user2_id 
                        WHEN user2_id = $1 THEN user1_id 
                    END as spouse_id
                FROM marriages 
                WHERE user1_id = $1 OR user2_id = $1
            """, user_id)
            return spouse['spouse_id'] if spouse else None
        except Exception as e:
            print(f"Error getting spouse: {e}")
            return None

    async def is_married(self, user_id: int) -> bool:
        """Check if user is already married"""
        return await self.get_spouse(user_id) is not None

    @commands.command()
    async def marry(self, ctx, target: discord.Member):
        """Propose marriage to another user (18+ only)"""
        if not await self.check_age_role(ctx.author):
            await ctx.send("❌ You must be 18+ to use this command.")
            return

        if not await self.check_age_role(target):
            await ctx.send("❌ The person you want to marry must also be 18+.")
            return

        if target.id == ctx.author.id:
            await ctx.send("❤️ Self-love is important, but you can't marry yourself!")
            return

        if await self.is_married(ctx.author.id):
            await ctx.send("💔 You are already married! You must get divorced first.")
            return

        if await self.is_married(target.id):
            await ctx.send("💔 That person is already married!")
            return

        if ctx.author.id in self.pending_proposals:
            await ctx.send("💝 You already have a pending proposal!")
            return

        if target.id in self.pending_proposals:
            await ctx.send("💔 That person already has a pending proposal!")
            return

        # Store the proposal
        self.pending_proposals[ctx.author.id] = target.id

        # Send proposal message
        proposal = await ctx.send(
            f"💍 {target.mention}, {ctx.author.mention} has proposed to you!\n"
            f"React with ✅ to accept or ❌ to decline within 60 seconds!"
        )
        await proposal.add_reaction("✅")
        await proposal.add_reaction("❌")

        def check_target(reaction, user):
            return (
                user.id == target.id 
                and str(reaction.emoji) in ["✅", "❌"]
                and reaction.message.id == proposal.id
            )

        try:
            # Wait for target's response
            reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=check_target)

            if str(reaction.emoji) == "✅":
                # Target accepted, now ask proposer to confirm
                confirm = await ctx.send(
                    f"💕 {target.mention} has accepted! {ctx.author.mention}, do you still want to proceed?\n"
                    f"React with ✅ to confirm or ❌ to cancel within 30 seconds!"
                )
                await confirm.add_reaction("✅")
                await confirm.add_reaction("❌")

                def check_proposer(reaction, user):
                    return (
                        user.id == ctx.author.id
                        and str(reaction.emoji) in ["✅", "❌"]
                        and reaction.message.id == confirm.id
                    )

                try:
                    # Wait for proposer's confirmation
                    reaction, user = await self.bot.wait_for("reaction_add", timeout=30.0, check=check_proposer)

                    if str(reaction.emoji) == "✅":
                        # Both parties have agreed, record the marriage
                        try:
                            await self.db.execute(
                                "INSERT INTO marriages (user1_id, user2_id) VALUES ($1, $2)",
                                ctx.author.id, target.id
                            )
                            await ctx.send(
                                f"🎊 Congratulations! {ctx.author.mention} and {target.mention} are now married! 💕"
                            )
                        except Exception as e:
                            print(f"Error recording marriage: {e}")
                            await ctx.send("❌ There was an error recording your marriage. Please try again.")
                    else:
                        await ctx.send(f"💔 {ctx.author.mention} has cancelled the marriage...")
                except asyncio.TimeoutError:
                    await ctx.send("💔 Marriage confirmation timed out...")
            else:
                await ctx.send(f"💔 {target.mention} has declined the proposal...")
        except asyncio.TimeoutError:
            await ctx.send(f"💔 The proposal has timed out...")
        finally:
            # Clean up the pending proposal
            if ctx.author.id in self.pending_proposals:
                del self.pending_proposals[ctx.author.id]

    @commands.command()
    async def divorce(self, ctx):
        """End your current marriage"""
        if not self.db:
            await ctx.send("❌ Marriage system is currently unavailable.")
            return

        spouse_id = await self.get_spouse(ctx.author.id)
        if not spouse_id:
            await ctx.send("❌ You aren't currently married!")
            return

        try:
            # Send divorce confirmation with reactions
            spouse = ctx.guild.get_member(spouse_id)
            spouse_mention = spouse.mention if spouse else "your spouse"

            confirm = await ctx.send(
                f"💔 Are you sure you want to divorce {spouse_mention}?\n"
                f"React with ✅ to confirm or ❌ to cancel."
            )
            await confirm.add_reaction("✅")
            await confirm.add_reaction("❌")

            def check(reaction, user):
                return (
                    user.id == ctx.author.id
                    and str(reaction.emoji) in ["✅", "❌"]
                    and reaction.message.id == confirm.id
                )

            try:
                reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
                if str(reaction.emoji) == "✅":
                    await self.db.execute(
                        "DELETE FROM marriages WHERE user1_id = $1 OR user2_id = $1",
                        ctx.author.id
                    )
                    await ctx.send(f"💔 {ctx.author.mention} is now divorced.")
                else:
                    await ctx.send("💕 Divorce cancelled. Love wins!")
            except asyncio.TimeoutError:
                await ctx.send("❌ Divorce request timed out.")

        except Exception as e:
            print(f"Error processing divorce: {e}")
            await ctx.send("❌ There was an error processing your divorce. Please try again.")

    @commands.command()
    async def marriage(self, ctx, member: discord.Member = None):
        """Check marriage status of yourself or another user"""
        target = member or ctx.author

        spouse_id = await self.get_spouse(target.id)
        if spouse_id:
            spouse = ctx.guild.get_member(spouse_id)
            spouse_name = spouse.name if spouse else "Unknown User"
            await ctx.send(f"💑 {target.name} is married to {spouse_name} 💕")
        else:
            await ctx.send(f"💝 {target.name} is not currently married.")

async def setup(bot):
    await bot.add_cog(Marriage(bot))
    print("Marriage cog loaded")