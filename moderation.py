import discord
from discord.ext import commands
import config
from utils.helpers import check_mod_permissions, remove_pending_application
import asyncio
import re
from datetime import datetime, timedelta

class ModerationSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.processing_approvals = set()  # Track approvals in progress
        self.muted_users = {}  # Track muted users and their unmute tasks
        self.muted_role_id = 994238679281303612  # Muted role ID

    def parse_duration(self, duration_str: str) -> int:
        """Convert duration string to seconds"""
        if not duration_str:
            return 0

        # Parse time format (e.g., 1h, 2d, 30m)
        time_units = {
            's': 1,
            'm': 60,
            'h': 3600,
            'd': 86400
        }

        match = re.match(r'(\d+)([smhd])', duration_str.lower())
        if not match:
            return 0

        amount = int(match.group(1))
        unit = match.group(2)
        return amount * time_units[unit]

    async def schedule_unmute(self, user_id: int, guild_id: int, duration: int):
        """Schedule an unmute task"""
        if duration <= 0:
            return

        try:
            await asyncio.sleep(duration)
            guild = self.bot.get_guild(guild_id)
            if not guild:
                return

            member = guild.get_member(user_id)
            if not member:
                return

            muted_role = guild.get_role(self.muted_role_id)
            if not muted_role:
                return

            await member.remove_roles(muted_role)

            # Log the unmute
            log_channel = self.bot.get_channel(config.MOD_LOG_CHANNEL_ID)
            if log_channel:
                embed = discord.Embed(
                    title="Member Unmuted (Auto)",
                    description=f"{member.mention}'s mute duration has expired.",
                    color=discord.Color.green()
                )
                await log_channel.send(embed=embed)

            # Clean up tracking
            if user_id in self.muted_users:
                del self.muted_users[user_id]

        except Exception as e:
            print(f"Error in unmute task: {str(e)}")

    @commands.command()
    @commands.check(check_mod_permissions)
    async def mute(self, ctx, member: discord.Member, duration: str = None, *, reason: str = "No reason provided"):
        """Mute a member"""
        try:
            # Check if user is already muted
            muted_role = ctx.guild.get_role(self.muted_role_id)
            if not muted_role:
                await ctx.send("Error: Could not find muted role.")
                return

            if muted_role in member.roles:
                await ctx.send(f"{member.mention} is already muted.")
                return

            # Parse duration
            duration_seconds = self.parse_duration(duration) if duration else 0

            # Apply mute
            await member.add_roles(muted_role)

            # Create embed for logging
            embed = discord.Embed(
                title="Member Muted",
                description=f"**User:** {member.mention}\n"
                          f"**Moderator:** {ctx.author.mention}\n"
                          f"**Duration:** {duration if duration else 'Indefinite'}\n"
                          f"**Reason:** {reason}",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )

            # Send to mod log channel
            log_channel = self.bot.get_channel(config.MOD_LOG_CHANNEL_ID)
            if log_channel:
                await log_channel.send(embed=embed)

            # Schedule unmute if duration was provided
            if duration_seconds > 0:
                # Cancel existing unmute task if exists
                if member.id in self.muted_users:
                    self.muted_users[member.id].cancel()

                # Create new unmute task
                task = asyncio.create_task(
                    self.schedule_unmute(member.id, ctx.guild.id, duration_seconds)
                )
                self.muted_users[member.id] = task

            # Send confirmation
            await ctx.send(
                f"🔇 Muted {member.mention}\n"
                f"**Duration:** {duration if duration else 'Indefinite'}\n"
                f"**Reason:** {reason}"
            )

            # Try to DM the user
            try:
                await member.send(
                    f"You have been muted in {ctx.guild.name}\n"
                    f"**Duration:** {duration if duration else 'Indefinite'}\n"
                    f"**Reason:** {reason}"
                )
            except:
                pass

        except Exception as e:
            await ctx.send(f"Error muting user: {str(e)}")

    @commands.command()
    @commands.check(check_mod_permissions)
    async def unmute(self, ctx, member: discord.Member):
        """Unmute a member"""
        try:
            muted_role = ctx.guild.get_role(self.muted_role_id)
            if not muted_role:
                await ctx.send("Error: Could not find muted role.")
                return

            if muted_role not in member.roles:
                await ctx.send(f"{member.mention} is not muted.")
                return

            # Remove muted role
            await member.remove_roles(muted_role)

            # Cancel any pending unmute task
            if member.id in self.muted_users:
                self.muted_users[member.id].cancel()
                del self.muted_users[member.id]

            # Create embed for logging
            embed = discord.Embed(
                title="Member Unmuted",
                description=f"**User:** {member.mention}\n"
                          f"**Moderator:** {ctx.author.mention}",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )

            # Send to mod log channel
            log_channel = self.bot.get_channel(config.MOD_LOG_CHANNEL_ID)
            if log_channel:
                await log_channel.send(embed=embed)

            # Send confirmation
            await ctx.send(f"🔊 Unmuted {member.mention}")

            # Try to DM the user
            try:
                await member.send(f"You have been unmuted in {ctx.guild.name}")
            except:
                pass

        except Exception as e:
            await ctx.send(f"Error unmuting user: {str(e)}")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """Handle moderator approval/denial reactions"""
        print(f"Processing reaction: {payload.emoji} in channel {payload.channel_id}")

        # Ignore bot's own reactions
        if payload.user_id == self.bot.user.id:
            print("Ignoring bot's own reaction")
            return

        # Only process reactions in mod channel
        if payload.channel_id != config.MOD_CHANNEL_ID:
            print(f"Reaction not in mod channel (expected {config.MOD_CHANNEL_ID}, got {payload.channel_id})")
            return

        try:
            # Get the guild and member objects
            guild = self.bot.get_guild(payload.guild_id)
            if not guild:
                print("Could not find guild")
                return

            mod = guild.get_member(payload.user_id)
            if not mod:
                print(f"Could not find member {payload.user_id}")
                return

            # Verify moderator permissions
            if not any(role.id == config.MOD_ROLE_ID for role in mod.roles):
                print(f"User {mod.name} does not have mod role")
                return

            # Get the channel and message
            channel = guild.get_channel(payload.channel_id)
            if not channel:
                print(f"Could not find channel {payload.channel_id}")
                return

            message = await channel.fetch_message(payload.message_id)
            if not message or not message.embeds:
                print("Could not find message or message has no embeds")
                return

            # Process verification request
            embed = message.embeds[0]
            if embed.title != "New Verification Request":
                print(f"Unexpected embed title: {embed.title}")
                return

            # Extract user ID from embed
            user_info = embed.fields[0].value
            user_id = int(user_info.split('ID: ')[1].split('\n')[0])
            user = guild.get_member(user_id)

            if not user:
                await channel.send(f"Error: Could not find user with ID {user_id}")
                return

            print(f"Processing verification for user {user.name} by mod {mod.name}")

            # Check if this verification is already being processed
            if user_id in self.processing_approvals:
                print(f"Verification for {user.name} is already being processed")
                return

            # Handle approval/denial
            if str(payload.emoji) == config.APPROVE_EMOJI:
                self.processing_approvals.add(user_id)
                try:
                    await self.approve_user(user, guild, message, mod)
                finally:
                    self.processing_approvals.remove(user_id)
            elif str(payload.emoji) == config.DENY_EMOJI:
                await self.deny_user(user, message, mod)

        except Exception as e:
            print(f"Error in on_raw_reaction_add: {str(e)}")
            if 'user_id' in locals() and user_id in self.processing_approvals:
                self.processing_approvals.remove(user_id)

    async def approve_user(self, user: discord.Member, guild: discord.Guild, message: discord.Message, mod: discord.Member):
        """Approve a user's verification"""
        try:
            # Check if message was already processed (has status field)
            if len(message.embeds[0].fields) > len(config.VERIFICATION_QUESTIONS) + 1:
                return

            # Add verified role
            role = guild.get_role(config.VERIFIED_ROLE_ID)
            if not role:
                await message.channel.send(f"Error: Could not find verified role {config.VERIFIED_ROLE_ID}")
                return

            # Check if user already has the role to prevent duplicate processing
            if role in user.roles:
                return

            await user.add_roles(role)

            # Update embed
            embed = message.embeds[0]
            embed.color = discord.Color.green()
            embed.add_field(name="Status", value=f"Approved by {mod.name}#{mod.discriminator}", inline=False)

            # Log to verification log channel
            log_channel = self.bot.get_channel(config.VERIFICATION_LOG_CHANNEL_ID)
            if log_channel:
                await log_channel.send(embed=embed)

            # Delete original message
            await message.delete()

            # Remove pending application status
            remove_pending_application(user.id)

            # Send welcome message in general chat
            general_channel = self.bot.get_channel(994238680115986496)  # General chat ID
            if general_channel:
                welcome_embed = discord.Embed(
                    title="🎉 New Member!",
                    description=f"Please welcome {user.mention} to the server! 🎊",
                    color=discord.Color.blue()
                )
                await general_channel.send(content=f"Everyone welcome {user.mention}!", embed=welcome_embed)

            # Notify user
            try:
                await user.send(config.VERIFICATION_APPROVED_MESSAGE)
            except:
                print(f"Could not DM user {user.name}#{user.discriminator}")

        except Exception as e:
            await message.channel.send(f"Error approving user: {str(e)}")

    async def deny_user(self, user: discord.Member, message: discord.Message, mod: discord.Member):
        """Deny a user's verification"""
        try:
            # Check if message was already processed (has status field)
            if len(message.embeds[0].fields) > len(config.VERIFICATION_QUESTIONS) + 1:
                return

            # Update embed
            embed = message.embeds[0]
            embed.color = discord.Color.red()
            embed.add_field(name="Status", value=f"Denied by {mod.name}#{mod.discriminator}", inline=False)

            # Log to verification log channel
            log_channel = self.bot.get_channel(config.VERIFICATION_LOG_CHANNEL_ID)
            if log_channel:
                await log_channel.send(embed=embed)

            # Delete original message
            await message.delete()

            # Remove pending application status
            remove_pending_application(user.id)

            # Notify user
            try:
                await user.send(config.VERIFICATION_DENIED_MESSAGE)
            except:
                print(f"Could not DM user {user.name}#{user.discriminator}")

        except Exception as e:
            await message.channel.send(f"Error denying user: {str(e)}")

    @commands.command(name='clear')
    @commands.check(check_mod_permissions)
    async def clear_messages(self, ctx, amount: int = None):
        """Clear messages from the channel"""
        try:
            # If no amount specified, clear all messages (limit 1000 for safety)
            if amount is None:
                amount = 1000

            deleted = await ctx.channel.purge(limit=amount)
            confirm_msg = await ctx.send(f"Cleared {len(deleted)} messages.")
            await asyncio.sleep(5)  # Show confirmation for 5 seconds
            await confirm_msg.delete()

        except discord.Forbidden:
            await ctx.send("I don't have permission to delete messages.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")
            print(f"Error in clear command: {str(e)}")

async def setup(bot):
    await bot.add_cog(ModerationSystem(bot))