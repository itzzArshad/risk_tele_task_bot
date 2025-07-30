import os
import re
import zipfile
import asyncio
from dotenv import load_dotenv
from aiohttp import web
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)


# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # e.g. "https://your-app.onrender.com"

KANAN_DIR = "kanan"
KIRI_DIR = "kiri"
cleared_folders = False
os.makedirs(KANAN_DIR, exist_ok=True)
os.makedirs(KIRI_DIR, exist_ok=True)

async def save_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global cleared_folders
    message = update.message
    caption = (message.caption or "").lower()

    if "kanan" in caption:
        folder = KANAN_DIR
    elif "kiri" in caption:
        folder = KIRI_DIR
    else:
        await message.reply_text("❌ Caption must contain 'kanan' or 'kiri'.")
        return

    if not cleared_folders:
        for f in [KANAN_DIR, KIRI_DIR]:
            for file in os.listdir(f):
                os.remove(os.path.join(f, file))
        cleared_folders = True
        await message.reply_text("🧹 Cleared old images. Ready for new batch.")

    if message.photo:
        photo = message.photo[-1]
        file = await photo.get_file()

        match = re.search(r"([0-9+\-]+)\s*(kanan|kiri)", caption)
        if match:
            filename_code = match.group(1)
        else:
            await message.reply_text("❌ Invalid caption format. Use 'code kanan/kiri'")
            return

        filename = f"{filename_code}.jpg"
        path = os.path.join(folder, filename)
        await file.download_to_drive(path)
        await message.reply_text(f"✅ Saved: `{filename}` in `{folder}/`", parse_mode="Markdown")

async def zip_and_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    def zip_folder(folder_name):
        zip_name = f"{folder_name}.zip"
        with zipfile.ZipFile(zip_name, 'w') as zipf:
            for file in os.listdir(folder_name):
                zipf.write(os.path.join(folder_name, file), arcname=file)
        return zip_name

    for folder in [KANAN_DIR, KIRI_DIR]:
        if os.listdir(folder):
            zip_path = zip_folder(folder)
            with open(zip_path, 'rb') as zf:
                await context.bot.send_document(chat_id=chat_id, document=zf)
        else:
            await context.bot.send_message(chat_id=chat_id, text=f"⚠️ No files in `{folder}/`", parse_mode="Markdown")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Send me images with captions like:\n`112-50 kanan` or `112+100 kiri`\nUse /zip to get zipped files.",
        parse_mode="Markdown"
    )

async def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("zip", zip_and_send))
    app.add_handler(MessageHandler(filters.PHOTO & filters.Caption(), save_image))

    # Set webhook (Telegram side)
    await app.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")

    # Aiohttp webhook handler
    async def handle(request):
        data = await request.json()
        update = Update.de_json(data, app.bot)
        await app.process_update(update)
        return web.Response(text="OK")

    # Run the web server on Render
    web_app = web.Application()
    web_app.add_routes([web.post("/webhook", handle)])
    port = int(os.environ.get("PORT", 10000))
    print(f"🚀 Starting webhook on port {port}...")
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    # Keep running
   
    while True:
        await asyncio.sleep(3600)
if __name__ == "__main__":
    asyncio.run(main())
