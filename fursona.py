import discord
from discord.ext import commands
import config
from utils.helpers import check_mod_permissions, create_embed
import asyncio
import json
import os

# File to store pending applications
PENDING_FURSONAS_FILE = 'pending_fursonas.json'
PENDING_IMAGES_FILE = 'pending_images.json'
USER_FURSONAS_FILE = 'user_fursonas.json'

# Load saved data
def load_saved_data():
    global pending_fursonas, pending_images, user_fursonas
    try:
        print("Loading fursona system data...")
        if os.path.exists(PENDING_FURSONAS_FILE):
            with open(PENDING_FURSONAS_FILE, 'r') as f:
                pending_fursonas = json.load(f)
                print(f"Loaded {len(pending_fursonas)} pending fursonas")
        if os.path.exists(PENDING_IMAGES_FILE):
            with open(PENDING_IMAGES_FILE, 'r') as f:
                pending_images = json.load(f)
                print(f"Loaded {len(pending_images)} pending images")
        if os.path.exists(USER_FURSONAS_FILE):
            with open(USER_FURSONAS_FILE, 'r') as f:
                user_fursonas = json.load(f)
                print(f"Loaded {len(user_fursonas)} user fursonas")
    except Exception as e:
        print(f"Error loading saved data: {e}")

# Initialize with empty dictionaries
pending_fursonas = {}
pending_images = {}
user_fursonas = {}

# Load saved data at startup
load_saved_data()

class FursonaSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("Initializing FursonaSystem cog")

    async def ask_fursona_questions(self, member: discord.Member) -> dict:
        """Ask fursona questions via DM"""
        questions = [
            "What's your fursona's name?",
            "What's your fursona's species?",
            "What's your fursona's age?",
            "Please write a brief bio for your fursona:"
        ]

        answers = {}
        try:
            await member.send("Let's create your fursona! Please answer the following questions:")
            await asyncio.sleep(1)

            def check(m):
                return m.author == member and isinstance(m.channel, discord.DMChannel)

            for question in questions:
                await member.send(question)
                try:
                    response = await self.bot.wait_for('message', timeout=300.0, check=check)
                    answers[question] = response.content
                    await asyncio.sleep(1)
                except asyncio.TimeoutError:
                    await member.send("You took too long to respond. Please try again using !fursona create")
                    return None

            return answers

        except discord.Forbidden:
            print(f"Could not DM user {member.name}")
            return None

    @commands.group(invoke_without_command=True)
    async def fursona(self, ctx):
        """Base fursona command"""
        if ctx.invoked_subcommand is None:
            await ctx.send("Available commands:\n"
                          "!fursona create - Create a new fursona\n"
                          "!fursona delete - Delete your fursona\n"
                          "!fursona image add - Add an image to your fursona\n"
                          "!fursona view - View your fursona\n"
                          "!fursona view @user - View someone else's fursona")

    @fursona.command(name='view')
    async def fursona_view(self, ctx, member: discord.Member = None):
        """View a fursona"""
        target_member = member or ctx.author

        if str(target_member.id) not in user_fursonas:
            if member:
                await ctx.send(f"{target_member.name} doesn't have a fursona!")
            else:
                await ctx.send("You don't have a fursona! Use !fursona create to make one.")
            return

        fursona_data = user_fursonas[str(target_member.id)]

        embed = discord.Embed(
            title=f"🦊 {target_member.name}'s Fursona",
            color=discord.Color.blue()
        )

        # Set pack icon first if exists
        pack_cog = self.bot.get_cog('PackSystem')
        if pack_cog and pack_cog.db:  # Ensure database connection exists
            try:
                pack_data = await pack_cog.db.fetchrow(
                    """
                    SELECT p.*, pm.role 
                    FROM packs p 
                    JOIN pack_members pm ON p.id = pm.pack_id 
                    WHERE pm.user_id = $1
                    """,
                    target_member.id
                )
                if pack_data and pack_data['pack_icon_url']:
                    print(f"Setting pack icon URL: {pack_data['pack_icon_url']}")
                    embed.set_thumbnail(url=pack_data['pack_icon_url'])
            except Exception as e:
                print(f"Error getting pack information: {e}")

        # Set fursona image if exists
        if 'image_url' in fursona_data:
            print(f"Setting fursona image URL: {fursona_data['image_url']}")
            embed.set_image(url=fursona_data['image_url'])

        # Basic Information Section
        basic_info = []
        for field in ["What's your fursona's name?", "What's your fursona's species?", "What's your fursona's age?"]:
            if field in fursona_data:
                field_name = field.replace("What's your fursona's", "").replace("?", "").strip()
                basic_info.append(f"**{field_name}:** {fursona_data[field]}")

        embed.add_field(
            name="📝 Basic Information",
            value="\n".join(basic_info),
            inline=False
        )

        # Bio Section (if exists)
        if "Please write a brief bio for your fursona:" in fursona_data:
            embed.add_field(
                name="✨ Biography",
                value=fursona_data["Please write a brief bio for your fursona:"],
                inline=False
            )

        # Pack Information Section
        if pack_cog and pack_cog.db:  # Ensure database connection exists
            try:
                if pack_data:
                    pack_info = [
                        f"**Pack:** {pack_data['name']}",
                        f"**Role:** {pack_data['role'].capitalize()}"
                    ]
                    if pack_data['description']:
                        pack_info.append(f"**Description:** {pack_data['description']}")

                    # Get pack alliances
                    alliances = await pack_cog.db.fetch(
                        """
                        SELECT p.name 
                        FROM packs p 
                        JOIN pack_alliances pa ON (pa.pack2_id = p.id AND pa.pack1_id = $1)
                        OR (pa.pack1_id = p.id AND pa.pack2_id = $1)
                        """,
                        pack_data['id']
                    )

                    if alliances:
                        alliance_names = [f"**{alliance['name']}**" for alliance in alliances]
                        pack_info.append(f"**Alliances:** {', '.join(alliance_names)}")

                    embed.add_field(
                        name="🐾 Pack Affiliation",
                        value="\n".join(pack_info),
                        inline=False
                    )

            except Exception as e:
                print(f"Error getting pack information: {e}")


        # Relationships Section
        relationships = []

        # Marriage Status
        marriage_cog = self.bot.get_cog('Marriage')
        if marriage_cog:
            try:
                spouse_id = await marriage_cog.get_spouse(target_member.id)
                if spouse_id:
                    spouse = ctx.guild.get_member(spouse_id)
                    spouse_name = spouse.name if spouse else "Unknown User"
                    relationships.append(f"💑 Married to **{spouse_name}**")
                else:
                    relationships.append("💝 Single")
            except Exception as e:
                print(f"Error getting marriage status: {e}")

        # Collar Relationships
        collar_cog = self.bot.get_cog('CollarSystem')
        if collar_cog:
            try:
                # Check if user is collared
                owner_id = await collar_cog.get_collar_owner(target_member.id)
                if owner_id:
                    owner = ctx.guild.get_member(owner_id)
                    owner_name = owner.name if owner else "Unknown User"
                    relationships.append(f"🔷 Collared by **{owner_name}**")

                # Check for pets
                pets = await collar_cog.get_pets(target_member.id)
                if pets:
                    pet_names = []
                    for pet_id in pets:
                        pet = ctx.guild.get_member(pet_id)
                        if pet:
                            pet_names.append(f"**{pet.name}**")
                    if pet_names:
                        relationships.append(f"✨ Pets: {', '.join(pet_names)}")
            except Exception as e:
                print(f"Error getting collar relationships: {e}")

        if relationships:
            embed.add_field(
                name="💫 Relationships",
                value="\n".join(relationships),
                inline=False
            )

        # Add footer with creation date if available
        if 'created_at' in fursona_data:
            embed.set_footer(text=f"Fursona created on {fursona_data['created_at']}")

        await ctx.send(embed=embed)

    @fursona.command(name='create')
    async def fursona_create(self, ctx):
        """Create a new fursona"""
        if str(ctx.author.id) in user_fursonas:
            await ctx.send("You already have a fursona! Use !fursona delete to remove it first.")
            return

        if str(ctx.author.id) in pending_fursonas:
            await ctx.send("You already have a pending fursona application!")
            return

        print(f"Starting fursona creation for {ctx.author.name}")
        answers = await self.ask_fursona_questions(ctx.author)
        if not answers:
            return

        embed = discord.Embed(
            title="New Fursona Application",
            color=discord.Color.blue()
        )

        embed.add_field(
            name="User Information",
            value=f"Name: {ctx.author.name}#{ctx.author.discriminator}\n"
                  f"ID: {ctx.author.id}",
            inline=False
        )

        for question, answer in answers.items():
            embed.add_field(
                name=question,
                value=answer,
                inline=False
            )

        mod_channel = self.bot.get_channel(config.FURSONA_APPROVAL_CHANNEL_ID)
        if not mod_channel:
            await ctx.author.send("There was an error submitting your fursona. Please try again later.")
            return

        verify_message = await mod_channel.send(embed=embed)
        await verify_message.add_reaction(config.APPROVE_EMOJI)
        await verify_message.add_reaction(config.DENY_EMOJI)

        # Store as strings to ensure JSON serialization
        pending_fursonas[str(ctx.author.id)] = {
            'answers': answers,
            'message_id': str(verify_message.id)
        }
        save_pending_fursonas()

        await ctx.author.send("Your fursona application has been submitted for review!")
        print(f"Fursona application submitted for {ctx.author.name}")

    @fursona.command(name='delete')
    async def fursona_delete(self, ctx):
        """Delete your fursona"""
        if str(ctx.author.id) not in user_fursonas:
            await ctx.send("You don't have a fursona to delete!")
            return

        del user_fursonas[str(ctx.author.id)]
        save_user_fursonas()
        await ctx.send("Your fursona has been deleted.")
        print(f"Fursona deleted for {ctx.author.name}")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """Handle moderator approval/denial of fursonas and images"""
        if payload.user_id == self.bot.user.id:
            return

        if payload.channel_id != config.FURSONA_APPROVAL_CHANNEL_ID:
            return

        message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
        if not message or not message.embeds:
            return

        guild = self.bot.get_guild(payload.guild_id)
        mod = guild.get_member(payload.user_id)
        if not mod or not any(role.id == config.MOD_ROLE_ID for role in mod.roles):
            return

        embed = message.embeds[0]

        if embed.title == "New Fursona Application":
            # Extract user ID from embed
            user_id = str(int(embed.fields[0].value.split('ID: ')[1].split('\n')[0]))
            user = guild.get_member(int(user_id))

            # Handle approval
            if str(payload.emoji) == config.APPROVE_EMOJI:
                # Get answers either from pending_fursonas or extract from embed
                if user_id in pending_fursonas:
                    answers = pending_fursonas[user_id]['answers']
                else:
                    # Extract answers from embed if not in memory
                    answers = {}
                    for field in embed.fields[1:]:  # Skip user info field
                        answers[field.name] = field.value

                # Store fursona data
                user_fursonas[user_id] = answers
                save_user_fursonas()

                # Clean up pending application
                if user_id in pending_fursonas:
                    del pending_fursonas[user_id]
                    save_pending_fursonas()

                # Update embed and log
                embed.color = discord.Color.green()
                embed.add_field(name="Status", value=f"Approved by {mod.name}#{mod.discriminator}")

                # Log the approval
                log_channel = self.bot.get_channel(config.FURSONA_LOG_CHANNEL_ID)
                if log_channel:
                    await log_channel.send(embed=embed)

                # Delete original message
                await message.delete()

                if user:
                    await user.send("Your fursona has been approved!")

            elif str(payload.emoji) == config.DENY_EMOJI:
                # Clean up pending application
                if user_id in pending_fursonas:
                    del pending_fursonas[user_id]
                    save_pending_fursonas()

                embed.color = discord.Color.red()
                embed.add_field(name="Status", value=f"Denied by {mod.name}#{mod.discriminator}")

                # Log the denial
                log_channel = self.bot.get_channel(config.FURSONA_LOG_CHANNEL_ID)
                if log_channel:
                    await log_channel.send(embed=embed)

                # Delete original message
                await message.delete()

                if user:
                    await user.send("Your fursona application has been denied.")

        elif embed.title == "New Fursona Image Submission":
            # Handle image approval/denial similarly...
            user_id_list = [uid for uid, data in pending_images.items() if str(data['message_id']) == str(message.id)]
            if user_id_list:
                user_id = user_id_list[0]
                if str(payload.emoji) == config.APPROVE_EMOJI:
                    if user_id in user_fursonas:
                        user_fursonas[user_id]['image_url'] = pending_images[user_id]['url']
                        save_user_fursonas()

                    if user_id in pending_images:
                        del pending_images[user_id]
                        save_pending_images()

                    embed.color = discord.Color.green()
                    embed.add_field(name="Status", value=f"Approved by {mod.name}#{mod.discriminator}")

                    # Log the approval
                    log_channel = self.bot.get_channel(config.FURSONA_LOG_CHANNEL_ID)
                    if log_channel:
                        await log_channel.send(embed=embed)

                    # Delete original message
                    await message.delete()

                    user = guild.get_member(int(user_id))
                    if user:
                        await user.send("Your fursona image has been approved!")

                elif str(payload.emoji) == config.DENY_EMOJI:
                    if user_id in pending_images:
                        del pending_images[user_id]
                        save_pending_images()

                    embed.color = discord.Color.red()
                    embed.add_field(name="Status", value=f"Denied by {mod.name}#{mod.discriminator}")

                    # Log the denial
                    log_channel = self.bot.get_channel(config.FURSONA_LOG_CHANNEL_ID)
                    if log_channel:
                        await log_channel.send(embed=embed)

                    # Delete original message
                    await message.delete()

                    user = guild.get_member(int(user_id))
                    if user:
                        await user.send("Your fursona image has been denied.")

    @fursona.group(name='image', invoke_without_command=True)
    async def fursona_image(self, ctx):
        """Base command for fursona image management"""
        if ctx.invoked_subcommand is None:
            await ctx.send("Use !fursona image add to add an image to your fursona")

    @fursona_image.command(name='add')
    async def fursona_image_add(self, ctx):
        """Add an image to your fursona"""
        if str(ctx.author.id) not in user_fursonas:
            await ctx.send("You need to create a fursona first!")
            return

        if str(ctx.author.id) in pending_images:
            await ctx.send("You already have a pending image approval!")
            return

        await ctx.author.send("Please send your fursona image. Only one image will be accepted.")

        def check(m):
            return m.author == ctx.author and isinstance(m.channel, discord.DMChannel) and m.attachments

        try:
            response = await self.bot.wait_for('message', timeout=300.0, check=check)
            image_url = response.attachments[0].url

            embed = discord.Embed(
                title="New Fursona Image Submission",
                color=discord.Color.blue()
            )
            embed.set_author(name=f"{ctx.author.name}#{ctx.author.discriminator}")
            embed.set_image(url=image_url)

            mod_channel = self.bot.get_channel(config.FURSONA_APPROVAL_CHANNEL_ID)
            verify_message = await mod_channel.send(embed=embed)
            await verify_message.add_reaction(config.APPROVE_EMOJI)
            await verify_message.add_reaction(config.DENY_EMOJI)

            # Store as strings to ensure JSON serialization
            pending_images[str(ctx.author.id)] = {
                'url': image_url,
                'message_id': str(verify_message.id)
            }
            save_pending_images()

            await ctx.author.send("Your fursona image has been submitted for review!")

        except asyncio.TimeoutError:
            await ctx.author.send("You took too long to send an image. Please try again.")

async def setup(bot):
    print("Setting up FursonaSystem cog...")
    await bot.add_cog(FursonaSystem(bot))
    print("FursonaSystem cog setup complete")

def save_pending_fursonas():
    with open(PENDING_FURSONAS_FILE, 'w') as f:
        json.dump(pending_fursonas, f, indent=4)

def save_pending_images():
    with open(PENDING_IMAGES_FILE, 'w') as f:
        json.dump(pending_images, f, indent=4)

def save_user_fursonas():
    with open(USER_FURSONAS_FILE, 'w') as f:
        json.dump(user_fursonas, f, indent=4)