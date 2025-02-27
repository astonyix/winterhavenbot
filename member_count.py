import discord
from discord.ext import commands
import config
from datetime import datetime

class MemberCount(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def update_member_count(self, guild: discord.Guild):
        """Update the member count channel name"""
        channel = guild.get_channel(config.MEMBER_COUNT_CHANNEL_ID)
        if channel:
            try:
                await channel.edit(name=f"Member Count: {guild.member_count}")
                print(f"Updated member count to {guild.member_count}")
            except discord.Forbidden:
                print("Bot lacks permission to edit channel name")
            except Exception as e:
                print(f"Error updating member count: {str(e)}")

    async def send_log_embed(self, member: discord.Member, event_type: str):
        """Send join/leave log embed"""
        log_channel = self.bot.get_channel(994238679910449267)  # Specified log channel
        if not log_channel:
            return

        # Create embed with different colors for join/leave
        embed = discord.Embed(
            title=f"Member {event_type}",
            color=discord.Color.green() if event_type == "Joined" else discord.Color.red(),
            timestamp=datetime.utcnow()
        )

        # Add member information
        embed.add_field(name="User", value=f"{member.name}#{member.discriminator}", inline=True)
        embed.add_field(name="ID", value=member.id, inline=True)
        embed.add_field(name="Created On", value=member.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"), inline=False)

        if event_type == "Joined":
            embed.description = f"📥 {member.mention} joined the server"
        else:
            embed.description = f"📤 {member.mention} left the server"

        # Set member avatar as thumbnail
        if member.avatar:
            embed.set_thumbnail(url=member.avatar.url)

        try:
            await log_channel.send(embed=embed)
        except Exception as e:
            print(f"Error sending log embed: {str(e)}")

    @commands.Cog.listener()
    async def on_ready(self):
        """Update member count when bot starts"""
        for guild in self.bot.guilds:
            await self.update_member_count(guild)
            print(f"Initial member count set for {guild.name}")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Handle member join"""
        await self.update_member_count(member.guild)
        await self.send_log_embed(member, "Joined")
        print(f"Member joined: {member.name}, updating count")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Handle member leave"""
        await self.update_member_count(member.guild)
        await self.send_log_embed(member, "Left")
        print(f"Member left: {member.name}, updating count")

async def setup(bot):
    await bot.add_cog(MemberCount(bot))