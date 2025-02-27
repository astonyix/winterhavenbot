import discord
from discord.ext import commands
import config
from utils.helpers import (
    create_embed, ask_question, is_in_verification,
    add_to_verification, remove_from_verification,
    is_on_cooldown, add_cooldown, remove_cooldown,
    add_pending_application, has_pending_application,
    check_mod_permissions
)
import asyncio

class VerificationSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.processing_lock = asyncio.Lock()

    @commands.command()
    @commands.check(check_mod_permissions)
    async def verificationsetup(self, ctx):
        """Set up verification in the current channel"""
        try:
            # Clear existing messages in the channel
            await ctx.channel.purge(limit=100)

            # Create embed
            embed = discord.Embed(
                title="Server Verification",
                description="Welcome to our community! To ensure a safe and friendly environment, we require all new members to complete a brief verification process.",
                color=discord.Color.blue()
            )

            # Add verification steps
            embed.add_field(
                name="📝 Verification Steps",
                value=(
                    "**1.** React with ✅ below to begin\n"
                    "**2.** Answer a few simple questions in DMs\n"
                    "**3.** Wait for moderator approval\n"
                    "\n**Note:** Please ensure your DMs are open!"
                ),
                inline=False
            )

            # Add additional information
            embed.add_field(
                name="ℹ️ Important Information",
                value=(
                    "• Verification helps us maintain a safe community\n"
                    "• Your answers will be reviewed by our moderation team\n"
                    "• The process usually takes just a few minutes\n"
                    "• If you need help, please contact a moderator"
                ),
                inline=False
            )

            embed.set_footer(text="Thank you for your patience! We look forward to welcoming you to our community.")

            # Send embed and add reaction
            welcome_msg = await ctx.send(embed=embed)
            await welcome_msg.add_reaction(config.VERIFY_EMOJI)

            await ctx.send("Verification setup complete! Users can now react with ✅ to begin verification.")

        except Exception as e:
            await ctx.send(f"Error setting up verification: {str(e)}")
            print(f"Error in verificationsetup: {str(e)}")

    @commands.Cog.listener()
    async def on_ready(self):
        """Set up verification message if it doesn't exist"""
        print("Initializing verification system...")
        channel = self.bot.get_channel(config.VERIFICATION_CHANNEL_ID)
        if not channel:
            print(f"Error: Could not find verification channel {config.VERIFICATION_CHANNEL_ID}")
            return

        # Check for existing verification message
        async for message in channel.history(limit=100):
            if message.author == self.bot.user and message.embeds and message.embeds[0].title == "Server Verification":
                print("Found existing verification message, refreshing reactions")
                # Clear existing reactions
                await message.clear_reactions()
                # Add fresh verification reaction
                await message.add_reaction(config.VERIFY_EMOJI)
                print(f"Added verification reaction {config.VERIFY_EMOJI}")
                return

        print("No existing verification message found, creating new one")
        # If no message exists, create a new one
        try:
            #This line is improved to avoid fetching a potentially non-existent message.
            #The original code had issues here because it was trying to fetch a message that may not exist yet, which would cause the bot to error. This fixed version makes sure a valid context can be created by fetching message object first then creating context object based on the valid message object.
            message = await channel.fetch_message(channel.last_message_id)
            ctx = await self.bot.get_context(message)
            await self.verificationsetup(ctx)
        except Exception as e:
            print(f"Error in verification setup: {str(e)}")


    async def process_verification(self, member: discord.Member):
        """Process the verification for a member"""
        try:
            print(f"Starting verification process for {member.name} (ID: {member.id})")
            # Send initial message
            await member.send(config.VERIFICATION_START_MESSAGE)
            await asyncio.sleep(1)  # Small delay to prevent message overlap

            # Process all questions in sequence
            answers = []
            for i, question in enumerate(config.VERIFICATION_QUESTIONS):
                print(f"Asking question {i+1} to {member.name}")
                answer = await ask_question(member, question, self.bot)
                if answer is None:  # If any question fails
                    print(f"Question {i+1} failed for {member.name}")
                    remove_from_verification(member.id)
                    return
                answers.append(answer)
                await asyncio.sleep(1)  # Small delay between questions

            # Get mod channel
            mod_channel = self.bot.get_channel(config.MOD_CHANNEL_ID)
            if not mod_channel:
                print(f"Error: Could not find mod channel {config.MOD_CHANNEL_ID}")
                remove_from_verification(member.id)
                return

            print(f"Creating verification request for {member.name}")
            # Create verification request embed
            embed = discord.Embed(
                title="New Verification Request",
                color=discord.Color.blue()
            )

            # Add user information
            embed.add_field(
                name="User Information",
                value=f"Name: {member.name}#{member.discriminator}\n"
                f"ID: {member.id}\n"
                f"Joined: {member.joined_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Account Created: {member.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
                inline=False
            )

            # Add all questions and answers
            for question, answer in zip(config.VERIFICATION_QUESTIONS, answers):
                embed.add_field(
                    name=question,
                    value=answer,
                    inline=False
                )

            # Send to mod channel
            verify_message = await mod_channel.send(embed=embed)
            await verify_message.add_reaction(config.APPROVE_EMOJI)
            await verify_message.add_reaction(config.DENY_EMOJI)

            print(f"Adding {member.name} to pending applications")
            # Mark application as pending
            add_pending_application(member.id)

            # Notify user of completion
            await asyncio.sleep(1)
            await member.send(config.VERIFICATION_COMPLETE_MESSAGE)

            # Add cooldown after successful submission
            add_cooldown(member.id)
            print(f"Added cooldown for {member.name}")

        except discord.Forbidden:
            print(f"Could not DM user {member.name}#{member.discriminator} - DMs are closed")
            try:
                channel = self.bot.get_channel(config.VERIFICATION_CHANNEL_ID)
                await channel.send(
                    f"{member.mention} I cannot send you direct messages. Please enable DMs for this server and try again.",
                    delete_after=10
                )
            except:
                pass
        finally:
            remove_from_verification(member.id)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """Handle verification reactions"""
        print(f"Reaction detected: {payload.emoji} in channel {payload.channel_id}")

        if payload.user_id == self.bot.user.id:
            return

        if payload.channel_id != config.VERIFICATION_CHANNEL_ID:
            return

        print(f"Comparing emoji: received '{str(payload.emoji)}' vs expected '{config.VERIFY_EMOJI}'")
        if str(payload.emoji) != config.VERIFY_EMOJI:
            return

        async with self.processing_lock:
            try:
                guild = self.bot.get_guild(payload.guild_id)
                if not guild:
                    print("Could not find guild")
                    return

                member = guild.get_member(payload.user_id)
                if not member:
                    print(f"Could not find member {payload.user_id}")
                    return

                # Check if user is already in verification, has pending application, or is on cooldown
                if is_in_verification(member.id):
                    try:
                        await member.send("You are already in the verification process. Please complete it or wait a moment.")
                    except:
                        pass
                    return

                if has_pending_application(member.id):
                    try:
                        await member.send("You already have a pending application. Please wait for moderators to review it.")
                    except:
                        pass
                    return

                if is_on_cooldown(member.id):
                    try:
                        await member.send("Please wait before submitting another verification request.")
                    except:
                        pass
                    return

                channel = guild.get_channel(payload.channel_id)
                if channel:
                    message = await channel.fetch_message(payload.message_id)
                    await message.remove_reaction(payload.emoji, member)

                print(f"Starting verification for member {member.name}")
                add_to_verification(member.id)
                await self.process_verification(member)

            except Exception as e:
                print(f"Error in verification process: {str(e)}")
                if 'member' in locals():
                    try:
                        await member.send("An error occurred during verification. Please try again later.")
                    except:
                        pass
                    remove_from_verification(member.id)

async def setup(bot):
    await bot.add_cog(VerificationSystem(bot))