import discord
from discord.ext import commands
import asyncio
import config
import os
import traceback

# Initialize bot with intents and remove default help command
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

@bot.event
async def on_ready():
    print(f'Bot is ready! Logged in as {bot.user.name}')
    print('------')
    # Check bot permissions
    for guild in bot.guilds:
        print(f"Connected to guild: {guild.name}")
        channel = guild.get_channel(config.VERIFICATION_CHANNEL_ID)
        if channel:
            permissions = channel.permissions_for(guild.me)
            print(f"Bot permissions in verification channel {channel.name}:")
            print(f"Send Messages: {permissions.send_messages}")
            print(f"Read Messages: {permissions.read_messages}")
            print(f"Add Reactions: {permissions.add_reactions}")
            print(f"Manage Messages: {permissions.manage_messages}")
        else:
            print(f"Could not find verification channel {config.VERIFICATION_CHANNEL_ID}")

    # Sync application commands after bot is ready
    try:
        print("\nSyncing command tree...")
        await bot.tree.sync()
        print("Command tree synced!")
    except Exception as e:
        print(f"Error syncing command tree: {e}")

@bot.event
async def on_disconnect():
    print("Bot disconnected from Discord. Attempting to reconnect...")

@bot.event
async def on_error(event, *args, **kwargs):
    """Log any errors that occur"""
    print(f"Error in {event}:")
    traceback.print_exc()
    print(f"Args: {args}")
    print(f"Kwargs: {kwargs}")

async def load_cogs():
    """Load all cogs"""
    print("\nLoading cogs...")

    # First unload any loaded cogs to prevent "already loaded" errors
    for extension in list(bot.extensions):
        try:
            print(f'Unloading extension {extension}...')
            await bot.unload_extension(extension)
        except Exception as e:
            print(f'Error unloading {extension}: {e}')

    # Now load all cogs from the handlers directory
    loaded_cogs = []
    for filename in os.listdir('./handlers'):
        if filename.endswith('.py'):
            cog_name = f'handlers.{filename[:-3]}'
            try:
                print(f'Loading {filename}...')
                await bot.load_extension(cog_name)
                loaded_cogs.append(cog_name)
                print(f'Successfully loaded {filename}')
            except Exception as e:
                print(f'Failed to load {filename}')
                print(f'Error type: {type(e).__name__}')
                print(f'Error message: {str(e)}')
                traceback.print_exc()

    print(f"\nSuccessfully loaded {len(loaded_cogs)} cogs:")
    for cog in loaded_cogs:
        print(f"- {cog}")

async def main():
    """Main function to start the bot"""
    try:
        print("Starting bot...")
        async with bot:
            await load_cogs()
            print("\nConnecting to Discord...")
            await bot.start(config.TOKEN)
    except Exception as e:
        print(f"Critical error in main function:")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    while True:
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            print("\nBot shutdown requested by user")
            break
        except Exception as e:
            print(f"\nBot crashed with error: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            traceback.print_exc()
            print("\nRestarting bot in 5 seconds...")
            import time
            time.sleep(5)

@bot.event
async def on_command(ctx):
    """Log when commands are received"""
    print(f"Command received: {ctx.command.name} from {ctx.author}")

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    print(f"Command error: {error}")
    if isinstance(error, commands.errors.CommandNotFound):
        # Don't respond to unknown commands
        return
    elif isinstance(error, commands.errors.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command.")
    else:
        await ctx.send("❌ An error occurred. Please try again later.")