import discord
from discord.ext import commands
import config
from utils.helpers import check_mod_permissions

class RulesSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.check(check_mod_permissions)
    async def rulessetup(self, ctx):
        """Set up server rules in the current channel"""
        try:
            # Clear existing messages in the channel
            await ctx.channel.purge(limit=100)

            # Create main rules embed
            embed = discord.Embed(
                title="Server Rules",
                color=discord.Color.blue(),
                description="Welcome to our server! Please read and follow these rules to ensure a welcoming community for everyone."
            )

            # Add rule sections
            embed.add_field(
                name="👋 Respect & Community",
                value="• Treat everyone with kindness and respect\n"
                      "• No harassment, hate speech, or discrimination\n"
                      "• No personal attacks, threats, or doxxing\n"
                      "• Take disagreements to DMs or involve a mod if needed",
                inline=False
            )

            embed.add_field(
                name="🎭 Behavior & Content",
                value="• Keep drama and toxicity out of public channels\n"
                      "• No spamming, trolling, or disruptive behavior\n"
                      "• No excessive pings or message spam\n"
                      "• Stay on topic in each channel",
                inline=False
            )

            embed.add_field(
                name="🔞 Content Guidelines",
                value="• Keep all content SFW outside designated channels\n"
                      "• No suggestive or explicit content in SFW areas\n"
                      "• No overly gory or disturbing content\n"
                      "• No AI art spam; credit artists when sharing artwork",
                inline=False
            )

            embed.add_field(
                name="🚫 Prohibited Activities",
                value="• No advertising or self-promotion without approval\n"
                      "• No unsolicited Discord invites\n"
                      "• No ban evasion or alternative accounts\n"
                      "• No sharing personal information",
                inline=False
            )

            embed.add_field(
                name="📜 Discord Terms & Moderation",
                value="• Follow Discord's Terms of Service\n"
                      "• Moderators have final say in all situations\n"
                      "• Comply with staff warnings and directions\n"
                      "• Message admins privately with moderation concerns",
                inline=False
            )

            embed.set_footer(text="By being in this server, you agree to follow these rules. Breaking them may result in warnings or bans at moderator discretion.")

            # Send embed
            await ctx.send(embed=embed)

            # Send welcome message
            welcome_embed = discord.Embed(
                description="🐾 Welcome to our community! Please enjoy your stay and let us know if you need any help! 🐾",
                color=discord.Color.green()
            )
            await ctx.send(embed=welcome_embed)

        except Exception as e:
            await ctx.send(f"Error setting up rules: {str(e)}")
            print(f"Error in rulessetup: {str(e)}")

async def setup(bot):
    await bot.add_cog(RulesSystem(bot))