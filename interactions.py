import discord
from discord.ext import commands
import random
import asyncio
import os
import asyncpg
from datetime import datetime, timedelta

class InteractionCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = None
        self.ready = asyncio.Event()
        self.bot.loop.create_task(self.init_db())
        print("Initializing InteractionCommands cog")

        # Add new interaction types to self.interactions dictionary
        self.interactions = {
            'boop': [
                "{user} gently boops {target}'s snoot! *boop!* 🐾",
                "{user} sneaks up and boops {target}'s nose! owo",
                "{user} gives {target} a playful boop on the snoot! *boop boop!* 💕",
                "{user} reaches out and boops {target}'s snoot with a paw! *pat pat*",
                "{user} surprises {target} with a sneaky nose boop! *boop!* 🌟"
            ],
            'bap': [
                "{user} lightly baps {target} with a paw! *bap!* 🐾",
                "{user} playfully baps {target}! *gentle bap*",
                "{user} gives {target} a soft bap on the head! uwu",
                "{user} baps {target} with a fluffy tail! *swoosh bap!* ✨",
                "{user} delivers a gentle warning bap to {target}! *bap bap!*"
            ],
            'hug': [
                "{user} gives {target} a big warm fluffy hug! 💝",
                "{user} wraps {target} in a cozy embrace! *squish* 🤗",
                "{user} sneaks up and hugs {target} from behind! *surprise hug!* 💕",
                "{user} shares a warm, comforting hug with {target}! *snuggle*",
                "{user} wraps their fluffy tail around {target} in a gentle hug! ✨"
            ],
            'nuzzle': [
                "{user} nuzzles {target} affectionately! *nuzzle nuzzle* 💕",
                "{user} gives {target} a gentle nuzzle! uwu",
                "{user} softly nuzzles against {target}'s cheek! *purr* ✨",
                "{user} shares a tender nuzzle with {target}! *happy noises* 🌟",
                "{user} nuzzles {target} with their soft fluffy fur! *cozy nuzzle* 🐾"
            ],
            'pat': [
                "{user} gently pats {target}'s head! *pat pat* 🐾",
                "{user} gives {target} some loving head pats! uwu",
                "{user} reaches over to pat {target} softly! 💕",
                "{user} offers {target} encouraging pats! *pat pat* ✨",
                "{user} shares some comforting pats with {target}! *happy pats*"
            ],
            'snuggle': [
                "{user} snuggles up close to {target}! *cozy* 💝",
                "{user} shares a warm snuggle with {target}! *snug snug*",
                "{user} cuddles up to {target} for warmth! uwu",
                "{user} offers {target} a cozy snuggle! *comfy* ✨",
                "{user} wraps their tail around {target} for snuggles! 🌟"
            ],
            'purr': [
                "{user} purrs happily at {target}! *purrrrr* 💕",
                "{user} lets out a soft purr near {target}! *happy sounds*",
                "{user} rumbles with a gentle purr for {target}! ✨",
                "{user} can't help but purr around {target}! *content purring*",
                "{user} shares their happy purrs with {target}! *purr purr* 🌟"
            ],
            'wag': [
                "{user}'s tail starts wagging happily at {target}! *wag wag* 🐾",
                "{user} can't contain their joy, wagging their tail for {target}! ✨",
                "{user}'s tail goes into maximum wag mode around {target}! *happy wags*",
                "{user} expresses their excitement with tail wags at {target}! 💖",
                "{user} wags their tail with boundless energy for {target}! *swoosh*"
            ],
            'flop': [
                "{user} flops over dramatically in front of {target}! *thump* 💫",
                "{user} does a playful flop near {target}! *floof* ✨",
                "{user} shows their trust with a happy flop beside {target}! uwu",
                "{user} flops down and shows their belly to {target}! *comfy flop*",
                "{user} performs the majestic art of flopping for {target}! 🌟"
            ],
            'blep': [
                "{user} does a cute little blep at {target}! :P",
                "{user}'s tongue peeks out in an adorable blep for {target}! uwu",
                "{user} can't help but blep around {target}! *cute noises*",
                "{user} shows their playful side with a blep at {target}! ✨",
                "{user} expresses happiness through a tiny blep for {target}! 💕"
            ],
            'scritch': [
                "{user} gives {target} some gentle scritches behind the ears! *scritch scritch* ✨",
                "{user} finds {target}'s favorite scritch spot! *happy noises* 💝",
                "{user} offers {target} some relaxing scritches! *purr* 🐾",
                "{user} shares some loving scritches with {target}! *happy wiggles* 🌟",
                "{user} gives {target} the most satisfying scritches! *blissful sounds*"
            ],
            'groom': [
                "{user} helps groom {target}'s fluffy fur! *brush brush* ✨",
                "{user} carefully detangles {target}'s fur with gentle paws! 💝",
                "{user} makes sure {target}'s fur is nice and tidy! *groom groom* 🐾",
                "{user} helps {target} look their fluffiest best! *happy grooming* 🌟",
                "{user} shares some social grooming time with {target}! *purr*"
            ],
            'tail': [
                "{user} gently plays with {target}'s tail! *swoosh* ✨",
                "{user} carefully brushes {target}'s tail to make it extra fluffy! 💝",
                "{user} admires {target}'s beautiful tail! *happy gasps* 🐾",
                "{user} gets mesmerized by {target}'s swishing tail! *wow* 🌟",
                "{user} gives {target}'s tail the softest pets! *gentle pets*"
            ],
            'yip': [
                "{user} makes happy yipping sounds at {target}! *yip yip* ✨",
                "{user} can't contain their excitement and yips at {target}! 💝",
                "{user} shares joyful yips with {target}! *excited noises* 🐾",
                "{user} yips playfully around {target}! *happy yipping* 🌟",
                "{user} expresses their happiness with tiny yips at {target}! *yip!*"
            ],
            'wiggle': [
                "{user} does a happy wiggle dance for {target}! *wiggle wiggle* ✨",
                "{user} can't help but wiggle with joy around {target}! 💝",
                "{user} shares their happiness through wiggles with {target}! 🐾",
                "{user} performs the cutest wiggle dance for {target}! *happy wiggles* 🌟",
                "{user} expresses their excitement through wiggles at {target}! *wiggle!*"
            ],
            'pounce': [
                "{user} playfully pounces on {target}! *bounce* ✨",
                "{user} sneaks up and pounces on {target} with excitement! *pounce* 💫",
                "{user} does a surprise pounce attack on {target}! *gotcha!* 🌟",
                "{user} crouches down before pouncing on {target}! *spring* 🐾",
                "{user} practices their hunting skills with a playful pounce on {target}! *pounce pounce* 💝"
            ],
            'cuddle': [
                "{user} wraps {target} in a cozy cuddle! *snuggle snuggle* 💝",
                "{user} shares a warm and fluffy cuddle with {target}! *soft purrs* ✨",
                "{user} pulls {target} into a gentle cuddle! *happy noises* 🌟",
                "{user} offers {target} the warmest, coziest cuddles! *snuggles close* 💕",
                "{user} wraps their tail around {target} for extra cuddly comfort! *warm cuddles* 🐾"
            ],
            'headpat': [
                "{user} gives {target} gentle headpats! *pat pat* 💝",
                "{user} softly pats {target}'s head! *happy pats* ✨",
                "{user} finds the perfect spot to pat {target}'s head! *gentle pats* 🌟",
                "{user} shares loving headpats with {target}! *pat pat pat* 💕",
                "{user} gives {target} the most soothing headpats! *content purring* 🐾"
            ],
            'gift': [
                "{user} gives {target} a lovely bouquet of flowers! 🌸",
                "{user} presents {target} with a batch of fresh-baked cookies! 🍪",
                "{user} surprises {target} with a cute plushie! 🧸",
                "{user} gifts {target} a shiny new collar with a bell! 🔔",
                "{user} shares their favorite treats with {target}! 🎁"
            ],
            'howl': [
                "{user} howls playfully with {target}! *awoooo!* 🐺",
                "{user} tilts their head back and howls alongside {target}! *howl* ✨",
                "{user} starts a chorus of howls with {target}! *melodic howling* 🌙",
                "{user} shares a happy howl with {target}! *awooooooo!* 🎵",
                "{user} teaches {target} their special howl! *harmonious howling* 🌟"
            ],
            'nom': [
                "{user} playfully nibbles on {target}'s ear! *nom nom* 🦊",
                "{user} gives {target} a gentle nom! *nibble* ✨",
                "{user} can't resist nomming {target}! *careful nom* 💝",
                "{user} playfully pretends to nom {target}! *gentle chomp* 🌟",
                "{user} gives {target} the tiniest nom! *delicate nibble* 🐾"
            ],
            'chase': [
                "{user} starts a playful chase with {target}! *zoom* 🏃‍♂️",
                "{user} dashes around with {target} in a game of tag! *whoosh* ✨",
                "{user} invites {target} to a fun chase! *playful running* 🌟",
                "{user} zooms after {target} with their tail wagging! *excited chase* 🐾",
                "{user} plays an energetic game of chase with {target}! *happy zoomies* 💨"
            ],
            'happy': [
                "{user} bounces around {target} with pure joy! *happy bounces* 🌟",
                "{user} radiates happiness around {target}! *gleeful wiggles* ✨",
                "{user} can't contain their joy near {target}! *excited hops* 💝",
                "{user} shares their happiness with {target}! *joyful dance* 🎵",
                "{user} spreads cheer and joy to {target}! *happy prancing* 🌈"
            ],
            'sleepy': [
                "{user} yawns softly and leans against {target}! *sleepy noises* 💤",
                "{user} gets cozy next to {target} for a nap! *drowsy snuggles* 🌙",
                "{user} shares tired blinks with {target}! *sleepy purrs* ✨",
                "{user} finds a comfy spot near {target} to rest! *soft yawning* 🛏️",
                "{user} dozes off peacefully beside {target}! *gentle snoozing* 🌟"
            ],
            'excited': [
                "{user} zooms around {target} with boundless energy! *excited zoomies* ⚡",
                "{user} can barely contain their excitement around {target}! *happy bouncing* 🌟",
                "{user} shares their enthusiasm with {target}! *energetic hops* ✨",
                "{user} expresses pure excitement to {target}! *joyful spins* 💫",
                "{user} bounces with endless energy near {target}! *excited wiggles* 🎉"
            ]
        }

    async def init_db(self):
        """Initialize database connection"""
        retries = 3
        while retries > 0:
            try:
                self.db = await asyncpg.create_pool(os.environ['DATABASE_URL'])
                print("Interactions database connection initialized")
                self.ready.set()
                return
            except Exception as e:
                print(f"Error initializing interactions database (retries left: {retries}): {e}")
                retries -= 1
                if retries > 0:
                    await asyncio.sleep(1)
        print("Failed to initialize interactions database after all retries")

    async def record_interaction(self, user_id: int, interaction_type: str):
        """Record an interaction in the database"""
        await self.ready.wait()
        if not self.db:
            return

        try:
            async with self.db.acquire() as conn:
                await conn.execute("""
                    INSERT INTO interaction_stats (user_id, interaction_type, count, last_used)
                    VALUES ($1, $2, 1, NOW())
                    ON CONFLICT (user_id, interaction_type)
                    DO UPDATE SET 
                        count = interaction_stats.count + 1,
                        last_used = NOW()
                """, user_id, interaction_type)
        except Exception as e:
            print(f"Error recording interaction: {e}")

    async def check_cooldown(self, user_id: int, interaction_type: str) -> bool:
        """Check if user is on cooldown for this interaction"""
        await self.ready.wait()
        if not self.db:
            return False

        try:
            async with self.db.acquire() as conn:
                last_used = await conn.fetchval("""
                    SELECT last_used 
                    FROM interaction_stats 
                    WHERE user_id = $1 AND interaction_type = $2
                """, user_id, interaction_type)

                if not last_used:
                    return False

                cooldown_time = timedelta(minutes=10)
                return datetime.utcnow() - last_used < cooldown_time
        except Exception as e:
            print(f"Error checking cooldown: {e}")
            return False

    async def handle_interaction(self, ctx, target: discord.Member, interaction_type: str):
        """Generic handler for all interaction commands"""
        print(f"Processing {interaction_type} interaction from {ctx.author} to {target}")

        # Delete the command message
        await ctx.message.delete()

        # Check if user has verified role
        verified_role = discord.utils.get(ctx.guild.roles, name="Verified")
        if verified_role and verified_role in ctx.author.roles:
            # Check cooldown for verified users
            if await self.check_cooldown(ctx.author.id, interaction_type):
                remaining = await self.get_cooldown_remaining(ctx.author.id, interaction_type)
                cooldown_msg = await ctx.send(
                    f"❌ {ctx.author.mention} You need to wait {remaining:.1f} minutes before using {interaction_type} again!"
                )
                # Delete the cooldown message after 5 seconds
                await asyncio.sleep(5)
                try:
                    await cooldown_msg.delete()
                except:
                    pass
                return

        if target.id == ctx.author.id:
            self_msg = await ctx.send(f"{ctx.author.mention} tries to {interaction_type} themselves... but just looks silly! *giggles*")
            await asyncio.sleep(5)
            try:
                await self_msg.delete()
            except:
                pass
            return

        message = random.choice(self.interactions[interaction_type])
        await ctx.send(message.format(user=ctx.author.mention, target=target.mention))
        await self.record_interaction(ctx.author.id, interaction_type)

    @commands.command()
    async def boop(self, ctx, target: discord.Member):
        """Boop another user's snoot!"""
        await self.handle_interaction(ctx, target, 'boop')

    @commands.command()
    async def bap(self, ctx, target: discord.Member):
        """Playfully bap another user!"""
        await self.handle_interaction(ctx, target, 'bap')

    @commands.command()
    async def hug(self, ctx, target: discord.Member):
        """Give another user a warm hug!"""
        await self.handle_interaction(ctx, target, 'hug')

    @commands.command()
    async def nuzzle(self, ctx, target: discord.Member):
        """Nuzzle another user affectionately!"""
        await self.handle_interaction(ctx, target, 'nuzzle')

    @commands.command()
    async def pat(self, ctx, target: discord.Member):
        """Pat another user gently!"""
        await self.handle_interaction(ctx, target, 'pat')

    @commands.command()
    async def snuggle(self, ctx, target: discord.Member):
        """Snuggle with another user!"""
        await self.handle_interaction(ctx, target, 'snuggle')

    @commands.command()
    async def purr(self, ctx, target: discord.Member):
        """Purr happily at another user!"""
        await self.handle_interaction(ctx, target, 'purr')

    @commands.command()
    async def wag(self, ctx, target: discord.Member):
        """Wag your tail at another user!"""
        await self.handle_interaction(ctx, target, 'wag')

    @commands.command()
    async def flop(self, ctx, target: discord.Member):
        """Flop over dramatically near another user!"""
        await self.handle_interaction(ctx, target, 'flop')

    @commands.command()
    async def blep(self, ctx, target: discord.Member):
        """Do a cute blep at another user!"""
        await self.handle_interaction(ctx, target, 'blep')

    @commands.command()
    async def scritch(self, ctx, target: discord.Member):
        """Give another user some gentle scritches!"""
        await self.handle_interaction(ctx, target, 'scritch')

    @commands.command()
    async def groom(self, ctx, target: discord.Member):
        """Help groom another user's fur!"""
        await self.handle_interaction(ctx, target, 'groom')

    @commands.command()
    async def tail(self, ctx, target: discord.Member):
        """Play with another user's tail!"""
        await self.handle_interaction(ctx, target, 'tail')

    @commands.command()
    async def yip(self, ctx, target: discord.Member):
        """Make happy yipping sounds at another user!"""
        await self.handle_interaction(ctx, target, 'yip')

    @commands.command()
    async def wiggle(self, ctx, target: discord.Member):
        """Do a happy wiggle dance for another user!"""
        await self.handle_interaction(ctx, target, 'wiggle')

    @commands.command()
    async def pounce(self, ctx, target: discord.Member):
        """Playfully pounce on another user!"""
        await self.handle_interaction(ctx, target, 'pounce')

    @commands.command()
    async def cuddle(self, ctx, target: discord.Member):
        """Share warm cuddles with another user!"""
        await self.handle_interaction(ctx, target, 'cuddle')

    @commands.command()
    async def headpat(self, ctx, target: discord.Member):
        """Give someone gentle headpats!"""
        await self.handle_interaction(ctx, target, 'headpat')

    @commands.command()
    async def gift(self, ctx, target: discord.Member):
        """Give a special gift to another user!"""
        await self.handle_interaction(ctx, target, 'gift')

    @commands.command()
    async def howl(self, ctx, target: discord.Member):
        """Share a playful howl with another user!"""
        await self.handle_interaction(ctx, target, 'howl')

    @commands.command()
    async def nom(self, ctx, target: discord.Member):
        """Playfully nibble on another user!"""
        await self.handle_interaction(ctx, target, 'nom')

    @commands.command()
    async def chase(self, ctx, target: discord.Member):
        """Start a playful chase with another user!"""
        await self.handle_interaction(ctx, target, 'chase')

    @commands.command()
    async def happy(self, ctx, target: discord.Member):
        """Share your happiness with another user!"""
        await self.handle_interaction(ctx, target, 'happy')

    @commands.command()
    async def sleepy(self, ctx, target: discord.Member):
        """Show your sleepy side to another user!"""
        await self.handle_interaction(ctx, target, 'sleepy')

    @commands.command()
    async def excited(self, ctx, target: discord.Member):
        """Express your excitement to another user!"""
        await self.handle_interaction(ctx, target, 'excited')

    @commands.command()
    async def interactions(self, ctx):
        """List all available interaction commands"""
        embed = discord.Embed(
            title="🌟 Available Interactions",
            description="Here are all the fun ways to interact with others!\n"
                        "**Note:** Verified users have a 10-minute cooldown between interactions.",
            color=discord.Color.blue()
        )

        # Group interactions by type
        social = ['hug', 'snuggle', 'nuzzle', 'scritch', 'groom', 'cuddle', 'headpat', 'gift']
        playful = ['boop', 'bap', 'pat', 'tail', 'pounce', 'howl', 'nom', 'chase']
        expressions = ['purr', 'wag', 'blep', 'flop', 'yip', 'wiggle']
        moods = ['happy', 'sleepy', 'excited']

        embed.add_field(
            name="💝 Social Interactions",
            value="\n".join([f"`!{cmd} @user` - {cmd.capitalize()} someone!" for cmd in social]),
            inline=False
        )
        embed.add_field(
            name="🎮 Playful Actions",
            value="\n".join([f"`!{cmd} @user` - {cmd.capitalize()} someone!" for cmd in playful]),
            inline=False
        )
        embed.add_field(
            name="✨ Expressions",
            value="\n".join([f"`!{cmd} @user` - {cmd.capitalize()} at someone!" for cmd in expressions]),
            inline=False
        )
        embed.add_field(
            name="🌈 Moods",
            value="\n".join([f"`!{cmd} @user` - Show your {cmd} side!" for cmd in moods]),
            inline=False
        )

        embed.add_field(
            name="📊 Statistics",
            value="`!interaction_stats` - View overall interaction leaderboard\n"
                  "`!interaction_stats <type>` - View leaderboard for specific interaction",
            inline=False
        )

        await ctx.send(embed=embed)

    @commands.command(name='interaction_stats')
    async def show_interaction_stats(self, ctx, interaction_type: str = None):
        """Show interaction leaderboard"""
        await self.ready.wait()
        if not self.db:
            await ctx.send("❌ Leaderboard temporarily unavailable.")
            return

        try:
            async with self.db.acquire() as conn:
                if interaction_type:
                    if interaction_type not in self.interactions:
                        await ctx.send(f"❌ Invalid interaction type. Use !interactions to see available types.")
                        return

                    # Get top 10 users for specific interaction
                    records = await conn.fetch("""
                        SELECT user_id, count 
                        FROM interaction_stats 
                        WHERE interaction_type = $1 
                        ORDER BY count DESC 
                        LIMIT 10
                    """, interaction_type)

                    embed = discord.Embed(
                        title=f"🏆 Top 10 {interaction_type} Users",
                        color=discord.Color.gold()
                    )
                else:
                    # Get top 10 users across all interactions
                    records = await conn.fetch("""
                        SELECT user_id, SUM(count) as total 
                        FROM interaction_stats 
                        GROUP BY user_id 
                        ORDER BY total DESC 
                        LIMIT 10
                    """)

                    embed = discord.Embed(
                        title="🏆 Top 10 Most Interactive Users",
                        color=discord.Color.gold()
                    )

                description = ""
                for i, record in enumerate(records, 1):
                    user = ctx.guild.get_member(record['user_id'])
                    if user:
                        count = record['count' if interaction_type else 'total']
                        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "✨"
                        description += f"{medal} **{i}.** {user.display_name}: {count} interactions\n"

                embed.description = description if description else "No interactions recorded yet!"
                await ctx.send(embed=embed)

        except Exception as e:
            print(f"Error displaying leaderboard: {e}")
            await ctx.send("❌ Error fetching leaderboard data.")

    async def get_cooldown_remaining(self, user_id: int, interaction_type: str) -> float:
        """Get remaining cooldown time in minutes"""
        await self.ready.wait()
        if not self.db:
            return 0

        try:
            async with self.db.acquire() as conn:
                last_used = await conn.fetchval("""
                    SELECT last_used 
                    FROM interaction_stats 
                    WHERE user_id = $1 AND interaction_type = $2
                """, user_id, interaction_type)

                if not last_used:
                    return 0

                elapsed = datetime.utcnow() - last_used
                remaining = timedelta(minutes=10) - elapsed
                return max(0, remaining.total_seconds() / 60)
        except Exception as e:
            print(f"Error checking cooldown remaining: {e}")
            return 0

async def setup(bot):
    print("Setting up InteractionCommands cog...")
    cog = InteractionCommands(bot)
    await bot.add_cog(cog)
    print("InteractionCommands cog setup complete")