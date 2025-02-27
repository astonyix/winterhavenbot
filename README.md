# Winterhaven Discord Bot

A powerful Discord bot that enhances community management through intelligent moderation, verification, and engagement tools.

## Features
- Leveling system with role rewards
- Reaction roles management
- Fursona system with approval workflow
- Server bump reminders
- Comprehensive moderation tools
- Member verification system
- Social interaction commands
- Collar system (18+ only)
- Pack management system

## Prerequisites
- Python 3.11+
- PostgreSQL 16+
- Discord Bot Token with following intents enabled:
  - Presence Intent
  - Server Members Intent
  - Message Content Intent

## Environment Variables
The following environment variables need to be set:

```env
# Discord Bot Configuration
DISCORD_BOT_TOKEN=your_discord_bot_token

# Database Configuration (Automatically set by Render)
DATABASE_URL=postgresql://username:password@host:port/database
```

## Local Development
1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up environment variables in a `.env` file
4. Initialize database: Execute `init_db.sql` script
5. Run the bot: `python main.py`

## Database Schema
The bot uses PostgreSQL for data storage. Tables include:
- `levels` - User XP and leveling data
- `reaction_role_categories` - Categories for reaction roles
- `reaction_roles` - Role assignments and emoji mappings
- `fursonas` - User fursona information
- `pending_fursonas` - Pending fursona applications
- `pending_fursona_images` - Pending fursona image approvals
- `packs` - Pack management system
- `pack_members` - Pack membership tracking
- `pack_invites` - Pack invitation system
- `interaction_stats` - Social interaction tracking
- `collars` - Collar system relationships (18+ feature)

## Deployment to Render

1. Push your code to GitHub
2. In Render:
   - Create a new Web Service
   - Connect your GitHub repository
   - Select Python as the environment
   - Set build command: `pip install -r requirements.txt`
   - Set start command: `python main.py`
   - Add environment variables:
     - `DISCORD_BOT_TOKEN`
     - `DATABASE_URL` (automatically set by Render PostgreSQL)
   - Deploy!

### Important Notes for Render Deployment
- Use Render's PostgreSQL service for the database
- Initialize your database using the provided `init_db.sql` script
- Make sure to enable the necessary Discord bot intents in the Discord Developer Portal
- The bot will automatically handle database connections and table creation
- Ensure your Discord bot token has the required permissions and intents enabled

## Support
For any issues or questions, please open an issue in the GitHub repository.

## Contributing
1. Fork the repository
2. Create a new branch for your feature
3. Make your changes
4. Submit a pull request

## License
This project is licensed under the MIT License - see the LICENSE file for details