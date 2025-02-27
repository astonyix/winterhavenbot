import discord
from discord.ext import commands
import config
import asyncio

class Commands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_command_menus = {}  # Store active command menus
        print("Commands cog initialized")

    def create_command_pages(self, ctx):
        """Create pages of commands"""
        pages = []
        is_mod = any(role.id == config.MOD_ROLE_ID for role in ctx.author.roles)
        is_admin = ctx.author.guild_permissions.administrator

        # Admin Commands Page
        if is_admin:
            embed = discord.Embed(
                title="Admin Commands",
                color=discord.Color.red()
            )
            admin_commands = "`!givexp @user amount` - Give XP to a user\n"
            admin_commands += "`!removexp @user amount` - Remove XP from a user"
            embed.add_field(name="Admin Commands", value=admin_commands, inline=False)
            pages.append(embed)

        # Mod Commands Page
        if is_mod:
            embed = discord.Embed(
                title="Moderation Commands",
                color=discord.Color.blue()
            )
            mod_commands = "`!clear [amount]` - Clear messages in the channel\n"
            mod_commands += "`!mute @user [duration] [reason]` - Temporarily mute a user\n"
            mod_commands += "`!unmute @user` - Remove mute from a user"
            embed.add_field(name="Moderation Commands", value=mod_commands, inline=False)
            pages.append(embed)

        # Reaction Roles Page (for mods)
        if is_mod:
            embed = discord.Embed(
                title="Reaction Role Commands",
                color=discord.Color.green()
            )
            rr_commands = "`!rrsetup` - Set up reaction roles in the current channel\n"
            rr_commands += "`!rrrefresh` - Refresh all reaction role messages\n"
            rr_commands += "`!rrcategory add <name> <emoji>` - Add a new role category\n"
            rr_commands += "`!rrcategory remove <name>` - Remove a role category\n"
            rr_commands += "`!rrcategory list` - List all role categories\n"
            rr_commands += "`!rradd <category> <@role> <emoji>` - Add a role to a category\n"
            rr_commands += "`!rrremove <category>` - Remove a role category\n"
            rr_commands += "`!rrlist` - List all reaction roles"
            embed.add_field(name="Reaction Role Commands", value=rr_commands, inline=False)
            pages.append(embed)

        # Server Bump Page
        embed = discord.Embed(
            title="Server Bump Commands",
            color=discord.Color.gold()
        )
        bump_commands = "Use these commands in the bump channel:\n"
        bump_commands += "`!bump` - Set bump timer for 119 minutes and ping mods\n"
        bump_commands += "`!bump <minutes>` - Set custom timer (max 240 minutes)\n"
        bump_commands += "`!bumpstatus` - Check when next bump is available"
        embed.add_field(name="Server Bump Commands", value=bump_commands, inline=False)
        pages.append(embed)

        # Leveling System Page
        embed = discord.Embed(
            title="Leveling System",
            color=discord.Color.purple()
        )
        level_commands = "`!rank` - Show your level and XP\n"
        level_commands += "`!rank @user` - Show another user's level and XP\n"
        level_commands += "`!leaderboard` - Show top 10 members"
        embed.add_field(name="Leveling Commands", value=level_commands, inline=False)
        pages.append(embed)

        # Fursona System Page
        embed = discord.Embed(
            title="Fursona System",
            color=discord.Color.orange()
        )
        fursona_commands = "`!fursona create` - Create your fursona\n"
        fursona_commands += "`!fursona delete` - Delete your fursona\n"
        fursona_commands += "`!fursona view` - View your fursona\n"
        fursona_commands += "`!fursona view @user` - View someone's fursona\n"
        fursona_commands += "`!fursona image add` - Add an image to your fursona\n"
        fursona_commands += "`!fursona image remove` - Remove your fursona's image"
        embed.add_field(name="Fursona Commands", value=fursona_commands, inline=False)
        pages.append(embed)

        # Social Interactions Page
        embed = discord.Embed(
            title="Social Interactions",
            color=discord.Color.blue()
        )
        social_commands = "`!hug @user` - Give someone a hug\n"
        social_commands += "`!snuggle @user` - Snuggle with someone\n"
        social_commands += "`!nuzzle @user` - Nuzzle someone affectionately\n"
        social_commands += "`!scritch @user` - Give someone gentle scritches\n"
        social_commands += "`!groom @user` - Help groom someone's fur\n"
        social_commands += "`!cuddle @user` - Share warm cuddles together\n"
        social_commands += "`!headpat @user` - Give someone gentle headpats\n"
        social_commands += "`!gift @user` - Give someone a special gift"
        embed.add_field(name="Social Interactions", value=social_commands, inline=False)
        pages.append(embed)

        # Playful Actions Page
        embed = discord.Embed(
            title="Playful Actions",
            color=discord.Color.green()
        )
        playful_commands = "`!boop @user` - Boop someone's snoot\n"
        playful_commands += "`!bap @user` - Playfully bap someone\n"
        playful_commands += "`!pat @user` - Pat someone gently\n"
        playful_commands += "`!tail @user` - Play with someone's tail\n"
        playful_commands += "`!pounce @user` - Playfully pounce on someone\n"
        playful_commands += "`!howl @user` - Share a playful howl together\n"
        playful_commands += "`!nom @user` - Give someone a gentle nibble\n"
        playful_commands += "`!chase @user` - Start a playful chase"
        embed.add_field(name="Playful Actions", value=playful_commands, inline=False)
        pages.append(embed)

        # Expressions Page
        embed = discord.Embed(
            title="Expressions",
            color=discord.Color.teal()
        )
        expression_commands = "`!purr @user` - Purr happily at someone\n"
        expression_commands += "`!wag @user` - Wag your tail at someone\n"
        expression_commands += "`!blep @user` - Do a cute blep\n"
        expression_commands += "`!flop @user` - Dramatically flop nearby\n"
        expression_commands += "`!yip @user` - Make happy yipping sounds\n"
        expression_commands += "`!wiggle @user` - Do a happy wiggle dance"
        embed.add_field(name="Expressions", value=expression_commands, inline=False)
        pages.append(embed)

        # Moods Page
        embed = discord.Embed(
            title="Moods",
            color=discord.Color.magenta()
        )
        mood_commands = "`!happy @user` - Share your happiness and joy\n"
        mood_commands += "`!sleepy @user` - Show your sleepy side\n"
        mood_commands += "`!excited @user` - Express your excitement"
        embed.add_field(name="Moods", value=mood_commands, inline=False)
        pages.append(embed)

        # Stats Page
        embed = discord.Embed(
            title="Interaction Stats",
            color=discord.Color.dark_gold()
        )
        stats_commands = "`!interaction_stats` - View top interactive users\n"
        stats_commands += "`!interaction_stats <type>` - View top users for specific interaction"
        embed.add_field(name="Stats Commands", value=stats_commands, inline=False)
        pages.append(embed)

        # Pack Commands Pages
        # Page 1 - Leader and Officer Commands
        embed = discord.Embed(
            title="Pack System Commands (1/2)",
            color=discord.Color.purple()
        )
        pack_commands_1 = (
            "**👑 Leader Commands:**\n"
            "`!pack desc <text>` - Set pack description\n"
            "`!pack icon <url>` - Submit pack icon for approval\n"
            "`!pack icon_remove` - Remove current pack icon\n"
            "`!pack promote @user` - Promote member to officer\n"
            "`!pack demote @user` - Demote officer to member\n"
            "`!pack disband` - Disband your pack\n"
            "`!pack ally <pack_name>` - Request an alliance\n"
            "`!pack accept_ally <pack_name>` - Accept alliance request\n"
            "`!pack decline_ally <pack_name>` - Decline alliance request\n"
            "`!pack unally <pack_name>` - Break an alliance\n"
            "`!pack transfer @user` - Transfer leadership\n\n"
            "**🛡️ Officer & Leader Commands:**\n"
            "`!pack invite @user` - Invite a user to pack\n"
            "`!pack kick @user` - Remove a member"
        )
        embed.add_field(name="Pack Commands - Leadership", value=pack_commands_1, inline=False)
        pages.append(embed)

        # Page 2 - Member and Server Commands
        embed = discord.Embed(
            title="Pack System Commands (2/2)",
            color=discord.Color.purple()
        )
        pack_commands_2 = (
            "**🐾 Member Commands:**\n"
            "`!pack join_pack <name>` - Join a pack (if invited)\n"
            "`!pack leave` - Leave your current pack\n"
            "`!pack info [name]` - View pack information\n\n"
            "**Server Commands:**\n"
            "`!pack alliances` - List all pack alliances\n"
            "`!pack list` - List all packs\n"
            "`!pack pending_alliances` - View pending alliance requests"
        )
        embed.add_field(name="Pack Commands - General", value=pack_commands_2, inline=False)
        pages.append(embed)

        # Economy System Page
        embed = discord.Embed(
            title="🪙 Economy System",
            color=discord.Color.gold()
        )
        economy_commands = (
            "PawCoins are earned by being active in chat!\n\n"
            "**Commands:**\n"
            "`!balance` - Check your PawCoin balance\n"
            "`!bal` - Shortcut for balance command\n"
            "`!coins` - Another way to check balance\n\n"
            "**Earning PawCoins:**\n"
            "• Send messages in chat (2min cooldown)\n"
            "• Participate in server events\n"
            "• More ways coming soon!"
        )
        embed.add_field(name="Economy Commands", value=economy_commands, inline=False)
        pages.append(embed)


        return pages

    @commands.command(name="commands", aliases=["cmds"])
    async def show_commands(self, ctx):
        """Show all available bot commands with pagination"""
        print(f"Commands command received from {ctx.author}")

        try:
            # Create pages
            pages = self.create_command_pages(ctx)
            current_page = 0

            # Add page numbers and dividers to embeds
            for i, embed in enumerate(pages):
                embed.description = "─────────────────────────\n"  # Add divider at top
                for field in embed.fields:
                    field.value = f"{field.value}\n─────────────────────────"  # Add divider after each field
                embed.set_footer(text=f"Page {i + 1} of {len(pages)} • Use ⬅️ ➡️ to navigate")

            # Send first page
            message = await ctx.send(embed=pages[current_page])

            # Add navigation reactions
            await message.add_reaction("⬅️")
            await message.add_reaction("➡️")

            # Store the menu state
            self.active_command_menus[message.id] = {
                "pages": pages,
                "current_page": current_page,
                "author_id": ctx.author.id,
                "last_interaction": asyncio.get_event_loop().time()
            }

            print(f"Successfully sent paginated commands embed to {ctx.author}")
            print(f"Created menu with {len(pages)} pages")

        except Exception as e:
            print(f"Error in show_commands: {e}")
            await ctx.send("❌ Error displaying commands. Please try again.")

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """Handle pagination reactions"""
        if user.bot:
            return

        message = reaction.message
        menu = self.active_command_menus.get(message.id)

        if menu and user.id == menu["author_id"]:
            pages = menu["pages"]
            current_page = menu["current_page"]

            # Update last interaction time
            menu["last_interaction"] = asyncio.get_event_loop().time()

            if str(reaction.emoji) == "➡️" and current_page < len(pages) - 1:
                current_page += 1
                await message.edit(embed=pages[current_page])
                menu["current_page"] = current_page
            elif str(reaction.emoji) == "⬅️" and current_page > 0:
                current_page -= 1
                await message.edit(embed=pages[current_page])
                menu["current_page"] = current_page

            # Remove user's reaction
            try:
                await reaction.remove(user)
            except:
                pass

    async def cleanup_old_menus(self):
        """Clean up inactive command menus"""
        while True:
            current_time = asyncio.get_event_loop().time()
            to_remove = []

            for message_id, menu in self.active_command_menus.items():
                if current_time - menu["last_interaction"] > 300:  # 5 minutes
                    to_remove.append(message_id)

            for message_id in to_remove:
                del self.active_command_menus[message_id]

            await asyncio.sleep(60)  # Check every minute

async def setup(bot):
    print("Setting up Commands cog...")
    try:
        commands_cog = Commands(bot)
        await bot.add_cog(commands_cog)
        # Start cleanup task
        bot.loop.create_task(commands_cog.cleanup_old_menus())
        print("Commands cog setup complete")
    except Exception as e:
        print(f"Error setting up Commands cog: {e}")