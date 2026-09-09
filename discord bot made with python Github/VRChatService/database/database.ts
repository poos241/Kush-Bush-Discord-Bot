import Database from "better-sqlite3";

const db = new Database("vrchat.db");

db.prepare(`
CREATE TABLE IF NOT EXISTS linked_accounts (

    guild_id TEXT NOT NULL,

    discord_id TEXT NOT NULL,

    vrchat_id TEXT NOT NULL,

    vrchat_username TEXT,

    display_name TEXT,

    verified INTEGER,

    friend_status TEXT,

    group_status TEXT,

    roles_synced INTEGER,

    created_at INTEGER,

    updated_at INTEGER,

    PRIMARY KEY (guild_id, discord_id)

)
`).run();

export default db;