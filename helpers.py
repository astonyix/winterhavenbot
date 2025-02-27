import discord
from discord.ext import commands
import asyncio
from typing import List, Dict
import config
import time

# Store verification states
active_verifications = set()
verification_cooldowns = {}
pending_applications = set()  # Track users with pending applications
message_locks = {}  # Add message locks to prevent duplicate messages

async def check_mod_permissions(ctx) -> bool:
    """Check if user has moderator permissions"""
    if not ctx.guild:
        return False
    return any(role.id == config.MOD_ROLE_ID for role in ctx.author.roles)

async def create_embed(title: str, fields: Dict[str, str], user: discord.Member) -> discord.Embed:
    """Create a formatted embed for verification"""
    embed = discord.Embed(
        title=title,
        color=discord.Color.blue()
    )
    embed.set_author(name=f"{user.name}#{user.discriminator}", icon_url=user.avatar.url if user.avatar else None)

    for field_name, field_value in fields.items():
        embed.add_field(name=field_name, value=field_value, inline=False)

    return embed

async def ask_question(user: discord.Member, question: str, bot: commands.Bot = None) -> str:
    """Ask a question and wait for response"""
    try:
        # Check if user is still in verification
        if not is_in_verification(user.id):
            return None

        # Prevent duplicate messages using a lock
        if user.id in message_locks:
            print(f"Skipping duplicate message for user {user.id}")
            return None

        message_locks[user.id] = True

        # Send question
        await user.send(question)
        print(f"Sent question to user {user.id}: {question}")

        def check(m):
            return m.author == user and isinstance(m.channel, discord.DMChannel)

        # Wait for response
        response = await bot.wait_for('message', timeout=300.0, check=check)

        # Clear the message lock after getting response
        if user.id in message_locks:
            del message_locks[user.id]

        return response.content if response else None

    except asyncio.TimeoutError:
        await user.send("Verification timed out. Please try again in the verification channel.")
        remove_from_verification(user.id)
        if user.id in message_locks:
            del message_locks[user.id]
        return None
    except discord.Forbidden:
        remove_from_verification(user.id)
        if user.id in message_locks:
            del message_locks[user.id]
        return None
    except Exception as e:
        print(f"Error in ask_question: {str(e)}")
        remove_from_verification(user.id)
        if user.id in message_locks:
            del message_locks[user.id]
        return None

def is_in_verification(user_id: int) -> bool:
    """Check if user is currently in verification process"""
    return user_id in active_verifications

def add_to_verification(user_id: int):
    """Add user to verification states"""
    active_verifications.add(user_id)

def remove_from_verification(user_id: int):
    """Remove user from verification states"""
    active_verifications.discard(user_id)
    # Also clear any message locks
    if user_id in message_locks:
        del message_locks[user_id]  # Fixed: using user_id instead of user.id
    print(f"Removed user {user_id} from verification process and cleared locks")

def has_pending_application(user_id: int) -> bool:
    """Check if user has a pending application"""
    is_pending = user_id in pending_applications
    print(f"Checking pending status for user {user_id}: {is_pending}")
    return is_pending

def add_pending_application(user_id: int):
    """Add user to pending applications"""
    pending_applications.add(user_id)
    print(f"Added user {user_id} to pending applications. Current pending: {len(pending_applications)}")

def remove_pending_application(user_id: int):
    """Remove user from pending applications"""
    pending_applications.discard(user_id)
    print(f"Removed user {user_id} from pending applications. Current pending: {len(pending_applications)}")

def is_on_cooldown(user_id: int) -> bool:
    """Check if user is on verification cooldown"""
    if user_id not in verification_cooldowns:
        return False
    current_time = time.time()
    if current_time - verification_cooldowns[user_id] >= config.VERIFICATION_COOLDOWN:
        remove_cooldown(user_id)
        return False
    return True

def add_cooldown(user_id: int):
    """Add user to cooldown"""
    verification_cooldowns[user_id] = time.time()

def remove_cooldown(user_id: int):
    """Remove user from cooldown"""
    if user_id in verification_cooldowns:
        del verification_cooldowns[user_id]