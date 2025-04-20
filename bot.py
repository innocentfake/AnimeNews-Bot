import aiohttp
import asyncio
import pymongo
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import subprocess
import threading
import feedparser
from config import API_ID, API_HASH, BOT_TOKEN, URL_A, START_PIC, MONGO_URI, ADMINS

from webhook import start_webhook
from modules.rss.rss import news_feed_loop

# MongoDB connection
try:
    mongo_client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    mongo_client.server_info()  # This throws an exception if the database is not reachable
    print("MongoDB connection successful!")
except pymongo.errors.ServerSelectionTimeoutError as err:
    print(f"Error: {err}")
    exit(1)

db = mongo_client["AnimeNewsBot"]
user_settings_collection = db["user_settings"]
global_settings_collection = db["global_settings"]

# Bot initialization
app = Client("AnimeNewsBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Start webhook in a separate thread
webhook_thread = threading.Thread(target=start_webhook, daemon=True)
webhook_thread.start()

# Escape Markdown function (No changes needed here)
async def escape_markdown_v2(text: str) -> str:
    return text

# Function to send messages to users
async def send_message_to_user(chat_id: int, message: str, image_url: str = None):
    try:
        if image_url:
            await app.send_photo(
                chat_id,
                image_url,
                caption=message,
            )
        else:
            await app.send_message(chat_id, message)
    except Exception as e:
        print(f"Error sending message: {e}")

# Start command
@app.on_message(filters.command("start"))
async def start(client, message):
    chat_id = message.chat.id
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("ᴍᴀɪɴ ʜᴜʙ", url="https://t.me/Manga_sect"),
            InlineKeyboardButton("ꜱᴜᴩᴩᴏʀᴛ ᴄʜᴀɴɴᴇʟ", url="https://t.me/Manga_sectgc"),
        ],
        [
            InlineKeyboardButton("ᴅᴇᴠᴇʟᴏᴩᴇʀ", url="https://t.me/darkxside78"),
        ],
    ])

    photo_url = START_PIC

    await app.send_photo(
        chat_id,
        photo_url,
        caption=(
            f"**ʙᴀᴋᴋᴀᴀᴀ {message.from_user.username}!!!**\n"
            f"**ɪ ᴀᴍ ᴀɴ ᴀɴɪᴍᴇ ɴᴇᴡs ʙᴏᴛ.**\n"
            f"**ɪ ᴛᴀᴋᴇ ᴀɴɪᴍᴇ ɴᴇᴡs ᴄᴏᴍɪɴɢ ғʀᴏᴍ ʀss ꜰᴇᴇᴅs ᴀɴᴅ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ᴜᴘʟᴏᴀᴅ ɪᴛ ᴛᴏ ᴍʏ ᴍᴀsᴛᴇʀ's ᴀɴɪᴍᴇ ɴᴇᴡs ᴄʜᴀɴɴᴇʟ.**"
        ),
        reply_markup=buttons
    )

# News command (only for admins)
@app.on_message(filters.command("news"))
async def connect_news(client, message):
    chat_id = message.chat.id

    if message.from_user.id not in ADMINS:
        await app.send_message(chat_id, "You do not have permission to use this command.")
        return
    if len(message.text.split()) == 1:
        await app.send_message(chat_id, "Please provide a channel id or username (without @).")
        return

    channel = " ".join(message.text.split()[1:]).strip()
    global_settings_collection.update_one({"_id": "config"}, {"$set": {"news_channel": channel}}, upsert=True)
    await app.send_message(chat_id, f"News channel set to: @{channel}")

# The set of sent news entries to avoid sending duplicates
sent_news_entries = set()

# Main event loop
async def main():
    try:
        await app.start()
        print("Bot is running...")
        # Start the news feed loop in the background
        asyncio.create_task(news_feed_loop(app, db, global_settings_collection, [URL_A]))
        await asyncio.Event().wait()
    except Exception as e:
        print(f"Error occurred: {e}")
        await app.stop()  # Stop the bot if there's a critical error

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
