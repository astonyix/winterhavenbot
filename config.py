# Bot configuration settings

# Verification settings
VERIFICATION_CHANNEL_ID = 994238679658795143  # Public verification channel
MOD_CHANNEL_ID = 1342617944613457983  # Staff Verification Chat
VERIFIED_ROLE_ID = 994238679281303606  # Verified role
MOD_ROLE_ID = 994238679306477680  # Mod role
VERIFICATION_LOG_CHANNEL_ID = 1342622671569031222  # Channel for verification logs

# Age Role
ADULT_ROLE_ID = 1342949415140200569  # 18+ role

# Member Count Channel
MEMBER_COUNT_CHANNEL_ID = 994238679658795141  # Channel for member count display

# Bot token (loaded from environment variable)
import os
import json

TOKEN = os.environ.get('DISCORD_BOT_TOKEN')

# File to store persistent settings
SETTINGS_FILE = 'bot_settings.json'

# Load persistent settings
try:
    with open(SETTINGS_FILE, 'r') as f:
        persistent_settings = json.load(f)
        REACTION_ROLES_CHANNEL_ID = persistent_settings.get('reaction_roles_channel_id')
except (FileNotFoundError, json.JSONDecodeError):
    persistent_settings = {}
    REACTION_ROLES_CHANNEL_ID = None

def save_settings():
    """Save persistent settings to file"""
    with open(SETTINGS_FILE, 'w') as f:
        json.dump({
            'reaction_roles_channel_id': REACTION_ROLES_CHANNEL_ID
        }, f)

# Verification questions
VERIFICATION_QUESTIONS = [
    "What's your age?",
    "How did you find our server?",
    "Why do you want to join our community?",
    "Do you agree to follow our server rules?"
]

# Emojis
VERIFY_EMOJI = "✅"
APPROVE_EMOJI = "✅"
DENY_EMOJI = "❌"

# Cooldown (in seconds)
VERIFICATION_COOLDOWN = 3600  # 1 hour

# Messages
WELCOME_MESSAGE = """Welcome to the server! To begin verification:
1. React with ✅ to start the process
2. Answer the questions sent to your DMs
3. Wait for moderator approval

Please ensure your DMs are open!"""

VERIFICATION_START_MESSAGE = "Starting verification process. Please answer the following questions..."
VERIFICATION_COMPLETE_MESSAGE = "Thank you! Your application has been submitted for review."
VERIFICATION_APPROVED_MESSAGE = """🎉 Congratulations! Your verification has been approved!

Welcome to our community! Let me tell you about some awesome features you can use:

🎮 **Fun Commands & Features:**
• Create your own fursona with `!fursona create`
• Join or create a pack with `!pack create <name>`
• Earn XP by chatting and check your level with `!rank`
• Use social commands like `!hug`, `!boop`, `!snuggle`, and many more!

📜 **Helpful Commands:**
• Type `!commands` to see all available commands
• Use `!bump` to help promote our server
• Check the leaderboard with `!leaderboard`

💡 **Getting Started:**
• Create your fursona first - it's a great way to introduce yourself!
• Join a pack or start your own to make new friends
• Try out some social interactions to engage with others

Have fun and don't hesitate to ask our moderators if you need help! 🌟"""
VERIFICATION_DENIED_MESSAGE = "Sorry, your verification has been denied."

# Reaction Roles Configuration

# Role Categories and their emojis
ROLE_CATEGORIES = {
    "RP Status": "🎭",
    "Sexual Orientation": "💝",
    "Region": "🌍",
    "Gender": "⚧",
    "Body Type": "👤"
}

# Store message IDs for each category
REACTION_MESSAGE_IDS = {}

# Initialize role dictionaries for each category
RP_STATUS_ROLES = {}
SEXUAL_ORIENTATION_ROLES = {}
REGION_ROLES = {}
GENDER_ROLES = {}
BODY_TYPE_ROLES = {}

# Fursona System Configuration
FURSONA_APPROVAL_CHANNEL_ID = 1342718308360781854  # Channel for fursona approvals
FURSONA_LOG_CHANNEL_ID = 1342916550335795200  # Channel for fursona logs