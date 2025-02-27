import discord
from discord.ext import commands
import config
from utils.helpers import check_mod_permissions
import asyncpg
import os
import json

class ReactionRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = None
        self.setup_messages = {}
        self.bot.loop.create_task(self.init_db())
        print("Initializing ReactionRoles cog")

    async def init_db(self):
        """Initialize database connection and create tables if needed"""
        try:
            print("Initializing database connection for reaction roles...")
            self.db = await asyncpg.create_pool(os.environ['DATABASE_URL'])
            print("Successfully initialized reaction roles database")

            # Load existing data from JSON if available (for migration)
            try:
                with open('reaction_roles.json', 'r') as f:
                    saved_data = json.load(f)
                    # Migrate data to database
                    await self.migrate_json_to_db(saved_data)
                    print("Migrated existing reaction roles from JSON to database")
            except FileNotFoundError:
                print("No JSON data to migrate")

        except Exception as e:
            print(f"Error initializing database: {e}")

    async def migrate_json_to_db(self, saved_data):
        """Migrate data from JSON to database"""
        if not self.db:
            return

        try:
            async with self.db.acquire() as conn:
                # Start a transaction
                async with conn.transaction():
                    # Migrate categories and roles
                    for category_name, emoji in saved_data.get('categories', {}).items():
                        category_id = await conn.fetchval(
                            """
                            INSERT INTO reaction_role_categories (name, emoji)
                            VALUES ($1, $2)
                            RETURNING id
                            """,
                            category_name, emoji
                        )

                        # Migrate roles for this category
                        role_dict_name = f"{category_name.upper().replace(' ', '_')}_ROLES"
                        if role_dict_name in saved_data:
                            role_dict = saved_data[role_dict_name]
                            for role_emoji, role_id in role_dict.items():
                                await conn.execute(
                                    """
                                    INSERT INTO reaction_roles 
                                    (category_id, role_id, emoji)
                                    VALUES ($1, $2, $3)
                                    """,
                                    category_id, role_id, role_emoji
                                )

                    print("Successfully migrated reaction roles data to database")
        except Exception as e:
            print(f"Error migrating data: {e}")

    async def load_category_data(self):
        """Load reaction role categories from database"""
        if not self.db:
            print("Database connection not initialized!")
            return

        try:
            async with self.db.acquire() as conn:
                # Load categories
                categories = await conn.fetch(
                    "SELECT * FROM reaction_role_categories"
                )
                config.ROLE_CATEGORIES = {
                    cat['name']: cat['emoji'] 
                    for cat in categories
                }

                # Load roles for each category
                for category in categories:
                    roles = await conn.fetch(
                        """
                        SELECT role_id, emoji 
                        FROM reaction_roles 
                        WHERE category_id = $1
                        """,
                        category['id']
                    )

                    role_dict_name = f"{category['name'].upper().replace(' ', '_')}_ROLES"
                    setattr(config, role_dict_name, {
                        role['emoji']: role['role_id']
                        for role in roles
                    })

                print(f"Loaded {len(categories)} categories from database")
        except Exception as e:
            print(f"Error loading category data: {e}")

    async def save_category_data(self):
        """Save reaction role categories to database"""
        if not self.db:
            print("Database connection not initialized!")
            return

        try:
            async with self.db.acquire() as conn:
                # Start a transaction
                async with conn.transaction():
                    # Clear existing data
                    await conn.execute("DELETE FROM reaction_roles")
                    await conn.execute("DELETE FROM reaction_role_categories")

                    # Insert categories
                    for name, emoji in config.ROLE_CATEGORIES.items():
                        category_id = await conn.fetchval(
                            """
                            INSERT INTO reaction_role_categories (name, emoji)
                            VALUES ($1, $2)
                            RETURNING id
                            """,
                            name, emoji
                        )

                        # Insert roles for this category
                        role_dict_name = f"{name.upper().replace(' ', '_')}_ROLES"
                        if hasattr(config, role_dict_name):
                            role_dict = getattr(config, role_dict_name)
                            for role_emoji, role_id in role_dict.items():
                                await conn.execute(
                                    """
                                    INSERT INTO reaction_roles 
                                    (category_id, role_id, emoji)
                                    VALUES ($1, $2, $3)
                                    """,
                                    category_id, role_id, role_emoji
                                )

                print("Saved reaction roles configuration to database")
        except Exception as e:
            print(f"Error saving category data: {e}")

    @commands.command()
    @commands.check(check_mod_permissions)
    async def rrrefresh(self, ctx):
        """Refresh all reaction role messages"""
        print("Starting rrrefresh command...")

        if not config.REACTION_ROLES_CHANNEL_ID:
            await ctx.send("No reaction roles channel set. Please run !rrsetup first.")
            return

        channel = self.bot.get_channel(config.REACTION_ROLES_CHANNEL_ID)
        if not channel:
            await ctx.send("Could not find reaction roles channel. Please run !rrsetup first.")
            return

        # Clear existing messages
        await channel.purge(limit=100)
        config.REACTION_MESSAGE_IDS.clear()

        # Load fresh data from database
        await self.load_category_data()

        # Create new messages for each category
        for category, emoji in config.ROLE_CATEGORIES.items():
            role_dict_name = f"{category.upper().replace(' ', '_')}_ROLES"
            if not hasattr(config, role_dict_name):
                continue

            role_dict = getattr(config, role_dict_name)
            embed = discord.Embed(
                title=f"{emoji} {category}",
                color=discord.Color.blue(),
                description="React to get roles:\n\n\n"
            )

            roles_added = 0
            for role_emoji, role_id in role_dict.items():
                role = ctx.guild.get_role(role_id)
                if role:
                    embed.description += f"{role_emoji} - {role.name}\n"
                    roles_added += 1

            if roles_added > 0:
                message = await channel.send(embed=embed)
                config.REACTION_MESSAGE_IDS[category] = message.id

                for role_emoji in role_dict.keys():
                    await message.add_reaction(role_emoji)

        await ctx.send("Reaction roles refreshed!")

    @commands.command()
    @commands.check(check_mod_permissions)
    async def rrcategory(self, ctx, action: str = None, *, args: str = None):
        """Manage reaction role categories"""
        if not action:
            await ctx.send("Available actions: add, remove, list\nExample: !rrcategory add 'New Category' 🔵")
            return

        if action.lower() == "list":
            embed = discord.Embed(
                title="Current Role Categories",
                color=discord.Color.blue()
            )
            for category, emoji in config.ROLE_CATEGORIES.items():
                embed.add_field(name=category, value=f"Emoji: {emoji}", inline=True)
            await ctx.send(embed=embed)
            return

        if action.lower() == "add":
            if not args:
                await ctx.send("Please provide both category name and emoji.\nExample: !rrcategory add 'New Category' 🔵")
                return

            try:
                # Split args into category name and emoji
                if '"' in args or "'" in args:
                    import shlex
                    parts = shlex.split(args)
                else:
                    parts = args.rsplit(' ', 1)

                if len(parts) != 2:
                    await ctx.send("Please provide both category name and emoji.\nExample: !rrcategory add 'New Category' 🔵")
                    return

                category_name, emoji = parts

                if len(emoji.strip()) != 1 and not emoji.startswith('<'):
                    await ctx.send("Please provide a valid emoji.")
                    return

                config.ROLE_CATEGORIES[category_name] = emoji
                setattr(config, f"{category_name.upper().replace(' ', '_')}_ROLES", {})

                await self.save_category_data()
                await ctx.send(f"Added category {category_name} with emoji {emoji}")

            except Exception as e:
                await ctx.send(f"Error adding category: {str(e)}")
                return

        elif action.lower() == "remove":
            if not args:
                await ctx.send("Please provide the category name to remove.\nExample: !rrcategory remove 'Category Name'")
                return

            try:
                if args.startswith('"') or args.startswith("'"):
                    import shlex
                    category_name = shlex.split(args)[0]
                else:
                    category_name = args

                if category_name in config.ROLE_CATEGORIES:
                    del config.ROLE_CATEGORIES[category_name]
                    role_dict_name = f"{category_name.upper().replace(' ', '_')}_ROLES"
                    if hasattr(config, role_dict_name):
                        delattr(config, role_dict_name)

                    await self.save_category_data()
                    await ctx.send(f"Removed category {category_name}")
                else:
                    await ctx.send(f"Category {category_name} not found")

            except Exception as e:
                await ctx.send(f"Error removing category: {str(e)}")
                return

        await ctx.send("Invalid action. Use: add, remove, or list")

    @commands.command()
    @commands.check(check_mod_permissions)
    async def rrsetup(self, ctx):
        """Set up reaction roles in the current channel"""
        config.REACTION_ROLES_CHANNEL_ID = ctx.channel.id
        await self.save_category_data()
        await self.rrrefresh(ctx)
        await ctx.send("Reaction roles setup complete! Use !rradd to add roles to categories.")

    @commands.command()
    @commands.check(check_mod_permissions)
    async def rradd(self, ctx, *, args=None):
        """Add a role to a category with specified emoji"""
        if not args:
            await ctx.send("Please use the format: !rradd \"Category Name\" @Role emoji\nExample: !rradd \"Ping Roles\" @Announcements 🔔")
            return

        try:
            print(f"Processing rradd command with args: {args}")
            # Split args handling quoted strings
            import shlex
            parts = shlex.split(args)
            print(f"Parsed parts: {parts}")

            if len(parts) < 3:
                await ctx.send("Please provide all required arguments: category name, role, and emoji.\nExample: !rradd \"Ping Roles\" @Announcements 🔔")
                return

            # The first part(s) until the last two are the category name
            category = " ".join(parts[:-2])
            role_mention = parts[-2]
            emoji = parts[-1]

            print(f"Parsed values - Category: '{category}', Role mention: '{role_mention}', Emoji: '{emoji}'")

            # Extract role ID from mention
            try:
                role_id = int(role_mention.strip('<@&>'))
                print(f"Extracted role ID: {role_id}")
            except ValueError:
                await ctx.send("Invalid role format. Please @mention the role you want to add.")
                print(f"Failed to extract role ID from: {role_mention}")
                return

            role = ctx.guild.get_role(role_id)
            if not role:
                await ctx.send(f"Could not find the role with ID {role_id}. Make sure you're @mentioning the role correctly.")
                print(f"Could not find role with ID {role_id}")
                return

            print(f"Found role: {role.name} ({role.id})")

            if category not in config.ROLE_CATEGORIES:
                categories_list = ", ".join(f'"{cat}"' for cat in config.ROLE_CATEGORIES.keys())
                await ctx.send(f"Invalid category. Available categories: {categories_list}")
                print(f"Category '{category}' not found in available categories: {config.ROLE_CATEGORIES.keys()}")
                return

            # Get the role category dictionary
            role_dict_name = f"{category.upper().replace(' ', '_')}_ROLES"
            role_dict = getattr(config, role_dict_name)
            print(f"Using role dictionary: {role_dict_name}")

            # Add role to category
            role_dict[emoji] = role.id
            print(f"Added role {role.name} to category {category} with emoji {emoji}")

            # Save the updated configuration
            await self.save_category_data()
            print("Saved reaction roles configuration")

            # Send success message
            await ctx.send(f"✅ Successfully added role **{role.name}** to category **{category}** with emoji {emoji}\nUse !rrrefresh to update the reaction role messages.")

        except ValueError as ve:
            error_msg = "Invalid role mention. Please @mention the role you want to add."
            await ctx.send(error_msg)
            print(f"ValueError in rradd: {str(ve)}")
        except Exception as e:
            error_msg = f"Error: {str(e)}\nPlease use the format: !rradd \"Category Name\" @Role emoji"
            await ctx.send(error_msg)
            print(f"Exception in rradd: {str(e)}")

    @commands.command()
    @commands.check(check_mod_permissions)
    async def rrremove(self, ctx, *, category_name: str = None):
        """Remove a role from a category"""
        if not category_name:
            await ctx.send(f"Please provide the category name.\nExample: !rrremove 'Category Name'")
            return

        try:
            # Handle quoted category names
            if category_name.startswith('"') or category_name.startswith("'"):
                import shlex
                category_name = shlex.split(category_name)[0]

            # Strip any extra whitespace
            category_name = category_name.strip()

            print(f"Attempting to remove category: '{category_name}'")
            print(f"Available categories: {list(config.ROLE_CATEGORIES.keys())}")

            if category_name in config.ROLE_CATEGORIES:
                # Remove from config
                del config.ROLE_CATEGORIES[category_name]

                # Remove role dictionary
                role_dict_name = f"{category_name.upper().replace(' ', '_')}_ROLES"
                if hasattr(config, role_dict_name):
                    delattr(config, role_dict_name)

                # Save changes
                await self.save_category_data()

                # Update the channel if it exists
                if config.REACTION_ROLES_CHANNEL_ID:
                    channel = self.bot.get_channel(config.REACTION_ROLES_CHANNEL_ID)
                    if channel:
                        await channel.purge(limit=100)
                        await self.rrrefresh(ctx)

                await ctx.send(f"Successfully removed category '{category_name}'")
            else:
                categories_list = ", ".join(f"'{cat}'" for cat in config.ROLE_CATEGORIES.keys())
                await ctx.send(f"Category '{category_name}' not found.\nAvailable categories: {categories_list}")

        except Exception as e:
            print(f"Error in rrremove: {str(e)}")
            await ctx.send(f"Error removing category: {str(e)}")

    @commands.command()
    @commands.check(check_mod_permissions)
    async def rrlist(self, ctx):
        """List all reaction role categories and their roles"""
        embed = discord.Embed(
            title="Reaction Roles Configuration",
            color=discord.Color.blue()
        )

        for category in config.ROLE_CATEGORIES:
            role_dict = getattr(config, f"{category.upper().replace(' ', '_')}_ROLES")
            roles_text = ""

            for emoji, role_id in role_dict.items():
                role = ctx.guild.get_role(role_id)
                if role:
                    roles_text += f"{emoji} - {role.name}\n"

            if roles_text:
                embed.add_field(
                    name=f"{config.ROLE_CATEGORIES[category]} {category}",
                    value=roles_text,
                    inline=False
                )
            else:
                embed.add_field(
                    name=f"{config.ROLE_CATEGORIES[category]} {category}",
                    value="No roles set up yet",
                    inline=False
                )

        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """Handle adding roles when users react"""
        if payload.user_id == self.bot.user.id:
            return

        # Check if the message is a reaction role message
        for category, message_id in config.REACTION_MESSAGE_IDS.items():
            if payload.message_id == message_id:
                role_dict = getattr(config, f"{category.upper().replace(' ', '_')}_ROLES")
                emoji = str(payload.emoji)

                if emoji in role_dict:
                    guild = self.bot.get_guild(payload.guild_id)
                    if guild:
                        member = guild.get_member(payload.user_id)
                        role = guild.get_role(role_dict[emoji])
                        if member and role:
                            if role in member.roles:
                                await member.remove_roles(role)
                                print(f"Removed role {role.name} from {member.name}")
                            else:
                                await member.add_roles(role)
                                print(f"Added role {role.name} to {member.name}")

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        """Handle removing roles when users remove reactions"""
        if payload.user_id == self.bot.user.id:
            return

        # Check if the message is a reaction role message
        for category, message_id in config.REACTION_MESSAGE_IDS.items():
            if payload.message_id == message_id:
                role_dict = getattr(config, f"{category.upper().replace(' ', '_')}_ROLES")
                emoji = str(payload.emoji)

                if emoji in role_dict:
                    guild = self.bot.get_guild(payload.guild_id)
                    if guild:
                        member = guild.get_member(payload.user_id)
                        role = guild.get_role(role_dict[emoji])
                        if member and role:
                            if role not in member.roles:
                                await member.add_roles(role)
                                print(f"Added role {role.name} to {member.name}")



async def setup(bot):
    print("Setting up ReactionRoles cog...")
    cog = ReactionRoles(bot)
    await bot.add_cog(cog)
    await cog.load_category_data()  # Load data when cog is added
    print("ReactionRoles cog setup complete")