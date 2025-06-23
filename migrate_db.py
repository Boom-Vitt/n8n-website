#!/usr/bin/env python3
"""
Database migration script to add platform connection columns
"""

import sqlite3
import os

DB_PATH = "social_media.db"

def migrate_database():
    """Add new columns for platform connections to existing users table"""
    
    if not os.path.exists(DB_PATH):
        print("Database doesn't exist. Will be created with new schema when app starts.")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if new columns already exist
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        new_columns = [
            "facebook_access_token TEXT",
            "facebook_page_id VARCHAR(100)",
            "instagram_access_token TEXT",
            "instagram_account_id VARCHAR(100)",
            "tiktok_access_token TEXT",
            "tiktok_user_id VARCHAR(100)",
            "youtube_access_token TEXT",
            "youtube_channel_id VARCHAR(100)",
            "facebook_connected BOOLEAN DEFAULT 0",
            "instagram_connected BOOLEAN DEFAULT 0",
            "tiktok_connected BOOLEAN DEFAULT 0",
            "youtube_connected BOOLEAN DEFAULT 0"
        ]
        
        for column_def in new_columns:
            column_name = column_def.split()[0]
            if column_name not in columns:
                try:
                    cursor.execute(f"ALTER TABLE users ADD COLUMN {column_def}")
                    print(f"✅ Added column: {column_name}")
                except sqlite3.OperationalError as e:
                    print(f"⚠️  Column {column_name} might already exist: {e}")
        
        # Also make google_id NOT NULL if possible (create new table and migrate)
        print("🔄 Updating google_id to be required...")
        
        # Check current schema
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='users'")
        current_schema = cursor.fetchone()[0]
        
        if "google_id VARCHAR(100)" in current_schema and "NOT NULL" not in current_schema:
            # Need to recreate table to make google_id NOT NULL
            cursor.execute("""
                CREATE TABLE users_new (
                    id INTEGER NOT NULL PRIMARY KEY,
                    username VARCHAR(50) NOT NULL UNIQUE,
                    email VARCHAR(100) NOT NULL UNIQUE,
                    hashed_password VARCHAR NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    google_id VARCHAR(100) NOT NULL UNIQUE,
                    facebook_access_token TEXT,
                    facebook_page_id VARCHAR(100),
                    instagram_access_token TEXT,
                    instagram_account_id VARCHAR(100),
                    tiktok_access_token TEXT,
                    tiktok_user_id VARCHAR(100),
                    youtube_access_token TEXT,
                    youtube_channel_id VARCHAR(100),
                    facebook_connected BOOLEAN DEFAULT 0,
                    instagram_connected BOOLEAN DEFAULT 0,
                    tiktok_connected BOOLEAN DEFAULT 0,
                    youtube_connected BOOLEAN DEFAULT 0,
                    api_key VARCHAR(64) UNIQUE,
                    api_key_created_at DATETIME,
                    api_key_name VARCHAR(100),
                    api_key_last_used DATETIME,
                    api_key_usage_count INTEGER DEFAULT 0,
                    api_key_is_active BOOLEAN DEFAULT 1
                )
            """)
            
            # Copy data from old table (only users with google_id)
            cursor.execute("""
                INSERT INTO users_new 
                SELECT * FROM users WHERE google_id IS NOT NULL
            """)
            
            # Drop old table and rename new one
            cursor.execute("DROP TABLE users")
            cursor.execute("ALTER TABLE users_new RENAME TO users")
            
            print("✅ Updated users table schema")
        
        conn.commit()
        print("🎉 Database migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()