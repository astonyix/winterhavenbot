import discord
from discord.ext import commands
import asyncpg
import os
from datetime import datetime
from utils.helpers import check_mod_permissions
import asyncio
import config

class PackSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = None
        self.bot.loop.create_task(self.init_db())
        print("Initializing PackSystem cog")

    async def init_db(self):
        """Initialize database connection"""
        try:
            self.db = await asyncpg.create_pool(os.environ['DATABASE_URL'])
            # Create necessary tables if they don't exist
            async with self.db.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS packs (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(100) UNIQUE NOT NULL,
                        description TEXT,
                        leader_id BIGINT NOT NULL,
                        pack_icon_url TEXT,
                        member_count INT DEFAULT 1,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE TABLE IF NOT EXISTS pack_members (
                        pack_id INT REFERENCES packs(id) ON DELETE CASCADE,
                        user_id BIGINT NOT NULL,
                        role VARCHAR(20) NOT NULL,
                        joined_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (pack_id, user_id)
                    );
                    CREATE TABLE IF NOT EXISTS pack_alliances (
                        pack1_id INT REFERENCES packs(id) ON DELETE CASCADE,
                        pack2_id INT REFERENCES packs(id) ON DELETE CASCADE,
                        formed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (pack1_id, pack2_id)
                    );
                    CREATE TABLE IF NOT EXISTS pack_invites (
                        pack_id INT REFERENCES packs(id) ON DELETE CASCADE,
                        user_id BIGINT NOT NULL,
                        inviter_id BIGINT NOT NULL,
                        status VARCHAR(20) DEFAULT 'pending',
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (pack_id, user_id)
                    );
                    CREATE TABLE IF NOT EXISTS pack_alliance_requests (
                        requesting_pack_id INT REFERENCES packs(id) ON DELETE CASCADE,
                        target_pack_id INT REFERENCES packs(id) ON DELETE CASCADE,
                        status VARCHAR(20) DEFAULT 'pending',
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (requesting_pack_id, target_pack_id)
                    );
                """)
                
            print("Pack system database connection initialized")
        except Exception as e:
            print(f"Error initializing pack system database: {e}")

    @commands.group(invoke_without_command=True)
    async def pack(self, ctx):
        """Pack management commands"""
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(
                title="🐾 Pack Commands",
                description="Manage your pack with these commands:",
                color=discord.Color.blue()
            )

            commands_list = (
                "**👑 Leader Commands:**\n"
                "`!pack desc <text>` - Set pack description\n"
                "`!pack icon <url>` - Submit pack icon for approval\n"
                "`!pack icon_remove` - Remove current pack icon\n"
                "`!pack promote @user` - Promote member to officer\n"
                "`!pack demote @user` - Demote officer to member\n"
                "`!pack disband` - Disband your pack\n"
                "`!pack ally <pack_name>` - Request an alliance with another pack\n"
                "`!pack accept_ally <pack_name>` - Accept an alliance request\n"
                "`!pack decline_ally <pack_name>` - Decline an alliance request\n"
                "`!pack unally <pack_name>` - Break an alliance with another pack\n"
                "`!pack transfer @user` - Transfer leadership to another member\n\n"
                "**🛡️ Officer & Leader Commands:**\n"
                "`!pack invite @user` - Invite a user to pack\n"
                "`!pack kick @user` - Remove a member\n\n"
                "**🐾 Member Commands:**\n"
                "`!pack join_pack <name>` - Join a pack (if invited)\n"
                "`!pack leave` - Leave your current pack\n"
                "`!pack info [name]` - View pack information\n\n"
                "**Server Commands:**\n"
                "`!pack alliances` - List all pack alliances\n"
                "`!pack list` - List all packs\n"
                "`!pack pending_alliances` - View pending alliance requests"
            )

            embed.add_field(name="Available Commands", value=commands_list, inline=False)
            await ctx.send(embed=embed)

    # Pack Creation & Management Commands

    @pack.command(name="create")
    async def pack_create(self, ctx, *, name: str):
        """Create a new pack (requires staff approval)"""
        if not self.db:
            await ctx.send("❌ Pack system temporarily unavailable")
            return

        try:
            # Check if user is already in a pack
            existing_membership = await self.db.fetchrow(
                "SELECT * FROM pack_members WHERE user_id = $1",
                ctx.author.id
            )

            if existing_membership:
                await ctx.send("❌ You're already in a pack! Leave your current pack first.")
                return

            # Submit pack for approval
            mod_channel = self.bot.get_channel(1344011559764234343)  # Pack verification channel
            if not mod_channel:
                await ctx.send("❌ Unable to submit pack for approval. Please try again later.")
                return

            embed = discord.Embed(
                title="New Pack Creation Request",
                color=discord.Color.blue()
            )

            embed.add_field(
                name="User Information",
                value=f"Name: {ctx.author.name}#{ctx.author.discriminator}\n"
                      f"ID: {ctx.author.id}",
                inline=False
            )

            embed.add_field(
                name="Pack Name",
                value=name,
                inline=False
            )

            verify_message = await mod_channel.send(embed=embed)
            await verify_message.add_reaction(config.APPROVE_EMOJI)
            await verify_message.add_reaction(config.DENY_EMOJI)

            await ctx.send("Your pack creation request has been submitted for staff approval! You'll be notified once it's reviewed.")

        except Exception as e:
            print(f"Error creating pack: {e}")
            await ctx.send("❌ Error submitting pack creation request. Please try again.")

    @pack.command(name="info")
    async def pack_info(self, ctx, *, name: str = None):
        """View pack information"""
        if not self.db:
            await ctx.send("❌ Pack system temporarily unavailable")
            return

        try:
            # If no name provided, show user's pack
            if not name:
                pack_data = await self.db.fetchrow(
                    """
                    SELECT p.*, pm.role
                    FROM packs p
                    JOIN pack_members pm ON p.id = pm.pack_id
                    WHERE pm.user_id = $1
                    """,
                    ctx.author.id
                )
            else:
                pack_data = await self.db.fetchrow(
                    "SELECT * FROM packs WHERE name = $1",
                    name
                )

            if not pack_data:
                await ctx.send("❌ Pack not found!")
                return

            # Get pack members
            members = await self.db.fetch(
                """
                SELECT pm.user_id, pm.role
                FROM pack_members pm
                WHERE pm.pack_id = $1
                ORDER BY 
                    CASE pm.role 
                        WHEN 'leader' THEN 1 
                        WHEN 'officer' THEN 2 
                        ELSE 3 
                    END
                """,
                pack_data['id']
            )

            # Get pack alliances
            alliances = await self.db.fetch(
                """
                SELECT p.name
                FROM packs p
                JOIN pack_alliances pa ON 
                    (pa.pack1_id = $1 AND pa.pack2_id = p.id) OR
                    (pa.pack1_id = p.id AND pa.pack2_id = $1)
                """,
                pack_data['id']
            )

            embed = discord.Embed(
                title=f"🐾 {pack_data['name']}",
                description=pack_data['description'] or "No description set.",
                color=discord.Color.blue()
            )

            # Add member list grouped by role
            for role in ['leader', 'officer', 'member']:
                role_members = [m for m in members if m['role'] == role]
                if role_members:
                    member_list = []
                    for member in role_members:
                        user = ctx.guild.get_member(member['user_id'])
                        if user:
                            member_list.append(user.mention)

                    if member_list:
                        embed.add_field(
                            name=f"{role.capitalize()}s" if len(role_members) > 1 else role.capitalize(),
                            value="\n".join(member_list),
                            inline=False
                        )

            # Add alliances field
            if alliances:
                alliance_list = []
                for alliance in alliances:
                    alliance_list.append(f"• {alliance['name']}")
                embed.add_field(
                    name="🤝 Alliances",
                    value="\n".join(alliance_list),
                    inline=False
                )

            if pack_data['pack_icon_url']:
                embed.set_thumbnail(url=pack_data['pack_icon_url'])

            embed.set_footer(text=f"Created {pack_data['created_at'].strftime('%Y-%m-%d')}")
            await ctx.send(embed=embed)

        except Exception as e:
            print(f"Error showing pack info: {e}")
            await ctx.send("❌ Error fetching pack information.")

    @pack.command(name="join_pack")
    async def pack_join(self, ctx, *, name: str):
        """Join a pack (if invited)"""
        if not self.db:
            await ctx.send("❌ Pack system temporarily unavailable")
            return

        try:
            # First check if the pack exists
            pack_data = await self.db.fetchrow(
                "SELECT id FROM packs WHERE name = $1",
                name
            )

            if not pack_data:
                await ctx.send("❌ This pack doesn't exist!")
                return

            # Then check for an invitation
            invite_data = await self.db.fetchrow(
                """
                SELECT * FROM pack_invites 
                WHERE user_id = $1 AND pack_id = $2 AND status = 'pending'
                """,
                ctx.author.id, pack_data['id']
            )

            if not invite_data:
                await ctx.send("❌ You haven't been invited to this pack!")
                return

            # Check if user is already in a pack
            existing_pack = await self.db.fetchrow(
                "SELECT * FROM pack_members WHERE user_id = $1",
                ctx.author.id
            )

            if existing_pack:
                await ctx.send("❌ You're already in a pack! Leave your current pack first.")
                return

            # Join the pack
            async with self.db.acquire() as conn:
                async with conn.transaction():
                    # Add member
                    await conn.execute(
                        """
                        INSERT INTO pack_members (pack_id, user_id, role) 
                        VALUES ($1, $2, 'member')
                        """,
                        pack_data['id'], ctx.author.id
                    )

                    # Update member count
                    await conn.execute(
                        """
                        UPDATE packs 
                        SET member_count = member_count + 1 
                        WHERE id = $1
                        """,
                        pack_data['id']
                    )

                    # Remove invitation
                    await conn.execute(
                        """
                        DELETE FROM pack_invites 
                        WHERE user_id = $1 AND pack_id = $2
                        """,
                        ctx.author.id, pack_data['id']
                    )

            await ctx.send(f"Welcome! You have joined the pack **{name}**! 🐾")

        except Exception as e:
            print(f"Error joining pack: {e}")
            await ctx.send("❌ Error joining pack. Please try again.")

    @pack.command(name="leave")
    async def pack_leave(self, ctx):
        """Leave your current pack"""
        if not self.db:
            await ctx.send("❌ Pack system temporarily unavailable")
            return

        try:
            # Check if user is in a pack
            member_data = await self.db.fetchrow(
                """
                SELECT p.*, pm.role
                FROM packs p
                JOIN pack_members pm ON p.id = pm.pack_id
                WHERE pm.user_id = $1
                """,
                ctx.author.id
            )

            if not member_data:
                await ctx.send("❌ You're not in a pack!")
                return

            if member_data['role'] == 'leader':
                await ctx.send("❌ Pack leaders must disband the pack or transfer leadership first!")
                return

            # Remove from pack
            async with self.db.acquire() as conn:
                async with conn.transaction():
                    await conn.execute(
                        "DELETE FROM pack_members WHERE user_id = $1",
                        ctx.author.id
                    )
                    await conn.execute(
                        """
                        UPDATE packs 
                        SET member_count = member_count - 1 
                        WHERE id = $1
                        """,
                        member_data['id']
                    )

            await ctx.send(f"You have left the pack **{member_data['name']}**.")

        except Exception as e:
            print(f"Error leaving pack: {e}")
            await ctx.send("❌ Error leaving pack.")

    @pack.command(name="alliances")
    async def list_alliances(self, ctx):
        """List all pack alliances in the server"""
        if not self.db:
            await ctx.send("❌ Pack system temporarily unavailable")
            return

        try:
            # Get all alliances
            alliances = await self.db.fetch(
                """
                SELECT p1.name as pack1_name, p2.name as pack2_name
                FROM pack_alliances pa
                JOIN packs p1 ON pa.pack1_id = p1.id
                JOIN packs p2 ON pa.pack2_id = p2.id
                ORDER BY p1.name, p2.name
                """
            )

            if not alliances:
                await ctx.send("There are no pack alliances in the server.")
                return

            embed = discord.Embed(
                title="🤝 Pack Alliances",
                description="Current alliances between packs:",
                color=discord.Color.gold()
            )

            alliance_text = ""
            for alliance in alliances:
                alliance_text += f"• {alliance['pack1_name']} 🤝 {alliance['pack2_name']}\n"

            embed.add_field(
                name="Active Alliances",
                value=alliance_text or "No active alliances",
                inline=False
            )

            await ctx.send(embed=embed)

        except Exception as e:
            print(f"Error listing alliances: {e}")
            await ctx.send("❌ Error fetching alliance information.")

    @pack.command(name="ally")
    async def pack_ally(self, ctx, *, target_pack_name: str):
        """Request an alliance with another pack (leader only)"""
        if not self.db:
            await ctx.send("❌ Pack system temporarily unavailable")
            return

        try:
            # Check if user is pack leader
            pack_data = await self.db.fetchrow(
                """
                SELECT p.*
                FROM packs p
                JOIN pack_members pm ON p.id = pm.pack_id
                WHERE pm.user_id = $1 AND pm.role = 'leader'
                """,
                ctx.author.id
            )

            if not pack_data:
                await ctx.send("❌ Only pack leaders can request alliances!")
                return

            try:
                # Get target pack data
                target_pack = await self.db.fetchrow(
                    """
                    SELECT p.* 
                    FROM packs p 
                    WHERE CAST(p.name AS text) = CAST($1 AS text)
                    """,
                    target_pack_name
                )

                if not target_pack:
                    all_packs = await self.db.fetch("SELECT name FROM packs")
                    print(f"Available packs: {[p['name'] for p in all_packs]}")
                    await ctx.send(f"❌ Could not find pack '{target_pack_name}'. Use `!pack list` to see all available packs.")
                    return

                if target_pack['id'] == pack_data['id']:
                    await ctx.send("❌ You can't form an alliance with your own pack!")
                    return

                # Check alliance limit (2 per pack)
                alliance_count = await self.db.fetchval(
                    """
                    SELECT COUNT(*) FROM pack_alliances 
                    WHERE pack1_id = $1 OR pack2_id = $1
                    """,
                    pack_data['id']
                )

                if alliance_count >= 2:
                    await ctx.send("❌ Your pack already has the maximum number of alliances (2)!")
                    return

                # Check if alliance already exists
                existing_alliance = await self.db.fetchrow(
                    """
                    SELECT * FROM pack_alliances 
                    WHERE (pack1_id = $1 AND pack2_id = $2)
                    OR (pack1_id = $2 AND pack2_id = $1)
                    """,
                    pack_data['id'], target_pack['id']
                )

                if existing_alliance:
                    await ctx.send("❌ Your packs are already allied!")
                    return

                # Check for existing pending request
                existing_request = await self.db.fetchrow(
                    """
                    SELECT * FROM pack_alliance_requests
                    WHERE (requesting_pack_id = $1 AND target_pack_id = $2)
                    OR (requesting_pack_id = $2 AND target_pack_id = $1)
                    AND status = 'pending'
                    """,
                    pack_data['id'], target_pack['id']
                )

                if existing_request:
                    if existing_request['requesting_pack_id'] == pack_data['id']:
                        await ctx.send("❌ You already have a pending alliance request to this pack!")
                    else:
                        await ctx.send("❌ This pack has already sent you an alliance request! Use `!pack accept_ally` to accept it.")
                    return

                # Create alliance request
                await self.db.execute(
                    """
                    INSERT INTO pack_alliance_requests (requesting_pack_id, target_pack_id, status)
                    VALUES ($1, $2, 'pending')
                    """,
                    pack_data['id'], target_pack['id']
                )

                await ctx.send(f"✅ Alliance request sent to **{target_pack['name']}**! Their leader must use `!pack accept_ally {pack_data['name']}` to accept.")

            except asyncpg.DataError as e:
                print(f"Database error when handling pack name '{target_pack_name}': {e}")
                await ctx.send("❌ Invalid pack name format. Please use `!pack list` to see available packs.")
            except Exception as e:
                print(f"Error in alliance formation: {e}")
                await ctx.send("❌ Error sending alliance request. Please try again.")

        except Exception as e:
            print(f"Error in pack_ally command: {e}")
            await ctx.send("❌ Error processing command. Please try again.")

    @pack.command(name="accept_ally")
    async def accept_ally(self, ctx, *, requesting_pack_name: str):
        """Accept an alliance request from another pack (leader only)"""
        if not self.db:
            await ctx.send("❌ Pack system temporarily unavailable")
            return

        try:
            # Check if user is pack leader
            pack_data = await self.db.fetchrow(
                """
                SELECT p.*
                FROM packs p
                JOIN pack_members pm ON p.id = pm.pack_id
                WHERE pm.user_id = $1 AND pm.role = 'leader'
                """,
                ctx.author.id
            )

            if not pack_data:
                await ctx.send("❌ Only pack leaders can accept alliance requests!")
                return

            # Get requesting pack data
            requesting_pack = await self.db.fetchrow(
                """
                SELECT p.* 
                FROM packs p 
                WHERE CAST(p.name AS text) = CAST($1 AS text)
                """,
                requesting_pack_name
            )

            if not requesting_pack:
                await ctx.send("❌ Could not find the requesting pack!")
                return

            # Check for pending request
            request = await self.db.fetchrow(
                """
                SELECT * FROM pack_alliance_requests
                WHERE requesting_pack_id = $1 AND target_pack_id = $2
                AND status = 'pending'
                """,
                requesting_pack['id'], pack_data['id']
            )

            if not request:
                await ctx.send("❌ No pending alliance request found from this pack!")
                return

            # Check alliance limit
            alliance_count = await self.db.fetchval(
                """
                SELECT COUNT(*) FROM pack_alliances 
                WHERE pack1_id = $1 OR pack2_id = $1
                """,
                pack_data['id']
            )

            if alliance_count >= 2:
                await ctx.send("❌ Your pack already has the maximum number of alliances (2)!")
                return

            async with self.db.acquire() as conn:
                async with conn.transaction():
                    # Create alliance
                    await conn.execute(
                        """
                        INSERT INTO pack_alliances (pack1_id, pack2_id)
                        VALUES ($1, $2)
                        """,
                        requesting_pack['id'], pack_data['id']
                    )

                    # Update request status
                    await conn.execute(
                        """
                        UPDATE pack_alliance_requests
                        SET status = 'accepted'
                        WHERE requesting_pack_id = $1 AND target_pack_id = $2
                        """,
                        requesting_pack['id'], pack_data['id']
                    )

            await ctx.send(f"✅ Alliance formed between **{pack_data['name']}** and **{requesting_pack['name']}**!")

        except Exception as e:
            print(f"Error accepting alliance: {e}")
            await ctx.send("❌ Error accepting alliance request. Please try again.")

    @pack.command(name="decline_ally")
    async def decline_ally(self, ctx, *, requesting_pack_name: str):
        """Decline an alliance request from another pack (leader only)"""
        if not self.db:
            await ctx.send("❌ Pack system temporarily unavailable")
            return

        try:
            # Check if user is pack leader
            pack_data = await self.db.fetchrow(
                """
                SELECT p.*
                FROM packs p
                JOIN pack_members pm ON p.id = pm.pack_id
                WHERE pm.user_id = $1 AND pm.role = 'leader'
                """,
                ctx.author.id
            )

            if not pack_data:
                await ctx.send("❌ Only pack leaders can decline alliance requests!")
                return

            # Get requesting pack data
            requesting_pack = await self.db.fetchrow(
                """
                SELECT p.* 
                FROM packs p 
                WHERE CAST(p.name AS text) = CAST($1 AS text)
                """,
                requesting_pack_name
            )

            if not requesting_pack:
                await ctx.send("❌ Could not find the requesting pack!")
                return

            # Update request status
            result = await self.db.execute(
                """
                UPDATE pack_alliance_requests
                SET status = 'declined'
                WHERE requesting_pack_id = $1 AND target_pack_id = $2
                AND status = 'pending'
                """,
                requesting_pack['id'], pack_data['id']
            )

            if result == "UPDATE 0":
                await ctx.send("❌ No pending alliance request found from this pack!")
                return

            await ctx.send(f"Alliance request from **{requesting_pack['name']}** has been declined.")

        except Exception as e:
            print(f"Error declining alliance: {e}")
            await ctx.send("❌ Error declining alliance request. Please try again.")

    @pack.command(name="pending_alliances")
    async def pending_alliances(self, ctx):
        """View pending alliance requests"""
        if not self.db:
            await ctx.send("❌ Pack system temporarily unavailable")
            return

        try:
            # Get user's pack
            pack_data = await self.db.fetchrow(
                """
                SELECT p.*
                FROM packs p
                JOIN pack_members pm ON p.id = pm.pack_id
                WHERE pm.user_id = $1 AND pm.role = 'leader'
                """,
                ctx.author.id
            )

            if not pack_data:
                await ctx.send("❌ Only pack leaders can view alliance requests!")
                return

            # Get incoming requests
            incoming = await self.db.fetch(
                """
                SELECT p.name as requester_name
                FROM pack_alliance_requests par
                JOIN packs p ON par.requesting_pack_id = p.id
                WHERE par.target_pack_id = $1 AND par.status = 'pending'
                """,
                pack_data['id']
            )

            # Get outgoing requests
            outgoing = await self.db.fetch(
                """
                SELECT p.name as target_name
                FROM pack_alliance_requests par
                JOIN packs p ON par.target_pack_id = p.id
                WHERE par.requesting_pack_id = $1 AND par.status = 'pending'
                """,
                pack_data['id']
            )

            embed = discord.Embed(
                title="🤝 Pending Alliance Requests",
                color=discord.Color.gold()
            )

            if incoming:
                incoming_text = "\n".join([f"• From **{r['requester_name']}**" for r in incoming])
                embed.add_field(
                    name="Incoming Requests",
                    value=incoming_text + "\n\nUse `!pack accept_ally <pack_name>` to accept",
                    inline=False
                )

            if outgoing:
                outgoing_text = "\n".join([f"• To **{r['target_name']}**" for r in outgoing])
                embed.add_field(
                    name="Outgoing Requests",
                    value=outgoing_text,
                    inline=False
                )

            if not incoming and not outgoing:
                embed.description = "No pending alliance requests."

            await ctx.send(embed=embed)

        except Exception as e:
            print(f"Error checking pending alliances: {e}")
            await ctx.send("❌ Error fetching alliance requests. Please try again.")

    @pack.command(name="list")
    async def list_packs(self, ctx):
        """List all packs in the server"""
        if not self.db:
            await ctx.send("❌ Pack system temporarily unavailable")
            return

        try:
            # Get all packs
            packs = await self.db.fetch(
                """
                SELECT name, member_count, description
                FROM packs
                ORDER BY name
                """
            )

            if not packs:
                await ctx.send("There are no packs in the server yet!")
                return

            embed = discord.Embed(
                title="🐾 Server Packs",
                description="All available packs:",
                color=discord.Color.blue()
            )

            pack_list = ""
            for pack in packs:
                pack_list += f"• **{pack['name']}** ({pack['member_count']} members)\n"
                if pack['description']:
                    pack_list += f"  *{pack['description'][:100]}*\n"

            embed.add_field(
                name="Available Packs",
                value=pack_list or "No packs found",
                inline=False
            )

            embed.set_footer(text="Use !pack info <name> to view more details about a specific pack")
            await ctx.send(embed=embed)

        except Exception as e:
            print(f"Error listing packs: {e}")
            await ctx.send("❌ Error fetching pack list.")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """Handle staff approval/denial of packs and pack icons"""
        if payload.user_id == self.bot.user.id:
            return

        if payload.channel_id not in [config.FURSONA_APPROVAL_CHANNEL_ID, 1344011559764234343]:  # Allow both channels
            return

        message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
        if not message or not message.embeds:
            return

        guild = self.bot.get_guild(payload.guild_id)
        mod = guild.get_member(payload.user_id)
        if not mod or not any(role.id == config.MOD_ROLE_ID for role in mod.roles):
            return

        embed = message.embeds[0]

        # Get the correct log channel
        log_channel = self.bot.get_channel(1344015781826007050)  # Pack log channel
        if not log_channel:
            print("Warning: Pack log channel not found")
            return

        if embed.title == "New Pack Creation Request":
            # Extract user ID and pack name from embed
            user_id = int(embed.fields[0].value.split('ID: ')[1])
            pack_name = embed.fields[1].value
            user = guild.get_member(user_id)

            if str(payload.emoji) == config.APPROVE_EMOJI:
                try:
                    # Create new pack
                    async with self.db.acquire() as conn:
                        async with conn.transaction():
                            pack_id = await conn.fetchval(
                                """
                                INSERT INTO packs (name, leader_id)
                                VALUES ($1, $2)
                                RETURNING id
                                """,
                                pack_name, user_id
                            )

                            # Add leader as first member
                            await conn.execute(
                                """
                                INSERT INTO pack_members (pack_id, user_id, role)
                                VALUES ($1, $2, 'leader')
                                """,
                                pack_id, user_id
                            )

                    embed.color = discord.Color.green()
                    embed.add_field(name="Status", value=f"Approved by {mod.name}#{mod.discriminator}")

                    if user:
                        await user.send(f"Your pack **{pack_name}** has been approved!")

                except asyncpg.UniqueViolationError:
                    if user:
                        await user.send(f"Pack name **{pack_name}** is already taken. Please try a different name.")
                except Exception as e:
                    print(f"Error creating approved pack: {e}")
                    if user:
                        await user.send("There was an error creating your pack. Please try again.")

            elif str(payload.emoji) == config.DENY_EMOJI:
                embed.color = discord.Color.red()
                embed.add_field(name="Status", value=f"Denied by {mod.name}#{mod.discriminator}")

                if user:
                    await user.send(f"Your pack creation request for **{pack_name}** has been denied.")

            # Log the action
            await log_channel.send(embed=embed)

            # Delete original message
            await message.delete()

async def setup(bot):
    print("Setting up PackSystem cog...")
    await bot.add_cog(PackSystem(bot))