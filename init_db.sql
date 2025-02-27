-- Create tables for the Discord bot

-- Leveling system
CREATE TABLE IF NOT EXISTS levels (
    user_id BIGINT PRIMARY KEY,
    xp BIGINT DEFAULT 0,
    level INTEGER DEFAULT 1,
    last_message_time TIMESTAMP DEFAULT NOW()
);

-- Reaction roles system
CREATE TABLE IF NOT EXISTS reaction_role_categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    emoji VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS reaction_roles (
    id SERIAL PRIMARY KEY,
    category_id INTEGER REFERENCES reaction_role_categories(id) ON DELETE CASCADE,
    role_id BIGINT NOT NULL,
    emoji VARCHAR(100) NOT NULL
);

-- Fursona system
CREATE TABLE IF NOT EXISTS fursonas (
    user_id BIGINT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    species VARCHAR(100) NOT NULL,
    age VARCHAR(50),
    bio TEXT,
    image_url TEXT,
    pack_id INTEGER REFERENCES packs(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pending_fursonas (
    user_id BIGINT PRIMARY KEY,
    data JSONB NOT NULL,
    message_id BIGINT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pending_fursona_images (
    user_id BIGINT PRIMARY KEY,
    image_url TEXT NOT NULL,
    message_id BIGINT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Pack system
CREATE TABLE IF NOT EXISTS packs (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    leader_id BIGINT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    pack_icon_url TEXT,
    member_count INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS pack_members (
    pack_id INTEGER REFERENCES packs(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL,
    role VARCHAR(50) DEFAULT 'member', -- 'leader', 'officer', 'member'
    joined_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (pack_id, user_id)
);

CREATE TABLE IF NOT EXISTS pack_invites (
    id SERIAL PRIMARY KEY,
    pack_id INTEGER REFERENCES packs(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL,
    inviter_id BIGINT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'accepted', 'declined'
    UNIQUE (pack_id, user_id)
);

-- Interaction tracking system
CREATE TABLE IF NOT EXISTS interaction_stats (
    user_id BIGINT NOT NULL,
    interaction_type VARCHAR(50) NOT NULL,
    count INTEGER DEFAULT 0,
    last_used TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (user_id, interaction_type)
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_interaction_stats_user_id ON interaction_stats(user_id);
CREATE INDEX IF NOT EXISTS idx_interaction_stats_count ON interaction_stats(count DESC);
CREATE INDEX IF NOT EXISTS idx_pack_members_user_id ON pack_members(user_id);
CREATE INDEX IF NOT EXISTS idx_pack_invites_user_id ON pack_invites(user_id);