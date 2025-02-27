import discord
from discord.ext import commands
import asyncio
import config
import os
import asyncpg
import logging

class CollarSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = None
        self.ready = asyncio.Event()
        self.bot.loop.create_task(self.init_db())
        self.pending_proposals = {} # Track pending proposals
        self.proposal_cooldown = commands.CooldownMapping.from_cooldown(1, 60, commands.BucketType.user)
        print("CollarSystem cog initialized")

    async def init_db(self):
        """Initialize database connection"""
        retries = 3
        while retries > 0:
            try:
                self.db = await asyncpg.create_pool(os.environ['DATABASE_URL'])
                print("Collar database connection initialized")
                self.ready.set()
                return
            except Exception as e:
                print(f"Error initializing collar database (retries left: {retries}): {e}")
                retries -= 1
                if retries > 0:
                    await asyncio.sleep(1)
        print("Failed to initialize collar database after all retries")

    async def get_collar_owner(self, pet_id: int) -> int:
        """Get the ID of the user who collared this pet"""
        await self.ready.wait()
        if not self.db:
            print("Database connection not available")
            return None
        try:
            record = await self.db.fetchrow(
                "SELECT owner_id FROM collars WHERE pet_id = $1",
                pet_id
            )
            return record['owner_id'] if record else None
        except Exception as e:
            print(f"Error getting collar owner: {e}")
            return None

    async def get_pets(self, owner_id: int) -> list:
        """Get list of pet IDs for this owner"""
        await self.ready.wait()
        if not self.db:
            return []
        try:
            records = await self.db.fetch(
                "SELECT pet_id FROM collars WHERE owner_id = $1",
                owner_id
            )
            return [record['pet_id'] for record in records]
        except Exception as e:
            print(f"Error getting pets: {e}")
            return []

    async def count_pets(self, owner_id: int) -> int:
        """Count how many pets this owner has"""
        await self.ready.wait()
        if not self.db:
            return 0
        try:
            record = await self.db.fetchrow(
                "SELECT COUNT(*) as pet_count FROM collars WHERE owner_id = $1",
                owner_id
            )
            return record['pet_count']
        except Exception as e:
            print(f"Error counting pets: {e}")
            return 0

    async def check_age_role(self, member: discord.Member) -> bool:
        """Check if member has the 18+ role"""
        return any(role.id == config.ADULT_ROLE_ID for role in member.roles)

    @commands.command()
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def collar(self, ctx, pet: discord.Member):
        """Collar another user as your pet (18+ only)"""
        await self.ready.wait()

        # Check if either user has a pending proposal
        if ctx.author.id in self.pending_proposals:
            await ctx.send("❌ You already have a pending collar request!")
            return

        if pet.id in self.pending_proposals:
            await ctx.send("❌ That person already has a pending collar request!")
            return

        if not await self.check_age_role(ctx.author):
            await ctx.send("❌ You must be 18+ to use the collar system!")
            return

        if not await self.check_age_role(pet):
            await ctx.send("❌ The person you want to collar must also be 18+!")
            return

        if pet.id == ctx.author.id:
            await ctx.send("❌ You can't collar yourself!")
            return

        # Check if pet is already collared
        current_owner = await self.get_collar_owner(pet.id)
        if current_owner:
            if current_owner == ctx.author.id:
                await ctx.send("❌ You've already collared this pet!")
            else:
                owner = ctx.guild.get_member(current_owner)
                owner_name = owner.display_name if owner else "someone else"
                await ctx.send(f"❌ This person is already collared by {owner_name}!")
            return

        # Check if owner has reached their pet limit
        pet_count = await self.count_pets(ctx.author.id)
        if pet_count >= 2:
            await ctx.send("❌ You can only have up to 2 pets!")
            return

        # Add to pending proposals
        self.pending_proposals[ctx.author.id] = pet.id
        self.pending_proposals[pet.id] = ctx.author.id

        # Send collar request
        proposal = await ctx.send(
            f"🔷 {pet.mention}, {ctx.author.mention} wants to collar you as their pet!\n"
            f"React with ✅ to accept or ❌ to decline within 60 seconds!"
        )
        await proposal.add_reaction("✅")
        await proposal.add_reaction("❌")

        def check(reaction, user):
            return (
                user.id == pet.id 
                and str(reaction.emoji) in ["✅", "❌"]
                and reaction.message.id == proposal.id
            )

        try:
            # Wait for target's response
            reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)

            # Delete the proposal message first
            try:
                await proposal.delete()
            except discord.errors.NotFound:
                pass  # Message was already deleted

            if str(reaction.emoji) == "✅":
                try:
                    async with self.db.acquire() as conn:
                        await conn.execute(
                            "INSERT INTO collars (owner_id, pet_id, collared_at) VALUES ($1, $2, NOW())",
                            ctx.author.id, pet.id
                        )
                    await ctx.send(
                        f"🔷 **Collar Accepted!** ✨\n"
                        f"{ctx.author.mention} has claimed {pet.mention} as their pet!\n"
                        f"Use `!uncollar @user` to remove the collar."
                    )
                except Exception as e:
                    print(f"Error recording collar: {e}")
                    await ctx.send("❌ There was an error recording the collar. Please try again.")
            else:
                await ctx.send(f"❌ {pet.mention} has declined {ctx.author.mention}'s collar request...")
        except asyncio.TimeoutError:
            # Delete the proposal message and send timeout notification
            try:
                await proposal.delete()
                await ctx.send("❌ Collar request timed out...")
            except discord.errors.NotFound:
                # Message was already deleted
                pass
        finally:
            # Clean up pending proposals
            if ctx.author.id in self.pending_proposals:
                del self.pending_proposals[ctx.author.id]
            if pet.id in self.pending_proposals:
                del self.pending_proposals[pet.id]

    @collar.error
    async def collar_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"❌ Please wait {int(error.retry_after)} seconds before using this command again.")

    @commands.command()
    async def uncollar(self, ctx, pet: discord.Member):
        """Remove your collar from a pet"""
        await self.ready.wait()
        try:
            current_owner = await self.get_collar_owner(pet.id)
            if not current_owner or current_owner != ctx.author.id:
                await ctx.send("❌ You haven't collared this person!")
                return

            async with self.db.acquire() as conn:
                await conn.execute(
                    "DELETE FROM collars WHERE owner_id = $1 AND pet_id = $2",
                    ctx.author.id, pet.id
                )
            await ctx.send(f"🔷 **Collar Removed!** ✨\n{ctx.author.mention} has removed their collar from {pet.mention}")
        except Exception as e:
            print(f"Error removing collar: {e}")
            await ctx.send("❌ There was an error removing the collar. Please try again.")

    @commands.command(name="escape")
    async def escape_collar(self, ctx):
        """Escape from your current collar"""
        await self.ready.wait()
        try:
            current_owner = await self.get_collar_owner(ctx.author.id)
            if not current_owner:
                await ctx.send("❌ You're not currently collared!")
                return

            owner = ctx.guild.get_member(current_owner)
            owner_mention = owner.mention if owner else "your owner"

            confirm = await ctx.send(
                f"🔷 Are you sure you want to escape from {owner_mention}'s collar?\n"
                f"React with ✅ to confirm or ❌ to cancel within 30 seconds!"
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
                reaction, user = await self.bot.wait_for("reaction_add", timeout=30.0, check=check)

                # Delete the confirmation message first
                try:
                    await confirm.delete()
                except discord.errors.NotFound:
                    pass  # Message was already deleted

                if str(reaction.emoji) == "✅":
                    async with self.db.acquire() as conn:
                        await conn.execute(
                            "DELETE FROM collars WHERE pet_id = $1",
                            ctx.author.id
                        )
                    await ctx.send(f"🔷 **Freedom Achieved!** ✨\n{ctx.author.mention} has escaped from their collar!")
                else:
                    await ctx.send("🔷 You remain collared.")
            except asyncio.TimeoutError:
                # Delete the confirmation message and send timeout
                try:
                    await confirm.delete()
                    await ctx.send("❌ Escape request timed out.")
                except discord.errors.NotFound:
                    pass

        except Exception as e:
            print(f"Error processing escape: {e}")
            await ctx.send("❌ There was an error processing your escape. Please try again.")

async def setup(bot):
    await bot.add_cog(CollarSystem(bot))
    print("CollarSystem cog loaded")