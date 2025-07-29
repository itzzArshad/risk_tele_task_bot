import os
import re
import shutil
import zipfile
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
)

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

KANAN_DIR = "kanan"
KIRI_DIR = "kiri"
os.makedirs(KANAN_DIR, exist_ok=True)
os.makedirs(KIRI_DIR, exist_ok=True)

cleared_folders = False
timeout_task = None


async def reset_cleared_flag_after_timeout(timeout_seconds=300):  # 5 minutes
    global cleared_folders, timeout_task
    await asyncio.sleep(timeout_seconds)
    cleared_folders = False
    timeout_task = None
    print("Timeout reached. cleared_folders reset.")


async def save_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global cleared_folders, timeout_task
    message = update.message
    caption = (message.caption or "").lower()

    if "kanan" in caption:
        folder = KANAN_DIR
    elif "kiri" in caption:
        folder = KIRI_DIR
    else:
        await message.reply_text("Caption must contain 'kanan' or 'kiri'.")
        return

    # Clear both folders only once per batch
    if not cleared_folders:
        for f in [KANAN_DIR, KIRI_DIR]:
            for file in os.listdir(f):
                file_path = os.path.join(f, file)
                if os.path.isfile(file_path):
                    os.remove(file_path)
        cleared_folders = True
        await message.reply_text("Old images cleared. Starting fresh batch...")

        # Start/reset timeout
        if timeout_task:
            timeout_task.cancel()
        timeout_task = asyncio.create_task(reset_cleared_flag_after_timeout())

    # Save the new image
    if message.photo:
        photo = message.photo[-1]
        file = await photo.get_file()

        # Extract filename from caption
        match = re.search(r"([0-9+\-]+)\s*(kanan|kiri)", caption)
        if match:
            filename_code = match.group(1)
        else:
            await message.reply_text("Invalid caption format.")
            return

        filename = f"{filename_code}.jpg"
        path = os.path.join(folder, filename)
        await file.download_to_drive(path)
        await message.reply_text(f"Saved: {filename} in {folder}/")


async def zip_and_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    def zip_folder(folder_name):
        zip_name = f"{folder_name}.zip"
        with zipfile.ZipFile(zip_name, 'w') as zipf:
            for root, _, files in os.walk(folder_name):
                for file in files:
                    zipf.write(os.path.join(root, file), arcname=file)
        return zip_name

    for folder in [KANAN_DIR, KIRI_DIR]:
        if os.listdir(folder):
            zip_path = zip_folder(folder)
            await context.bot.send_document(chat_id=chat_id, document=open(zip_path, 'rb'))
        else:
            await context.bot.send_message(chat_id=chat_id, text=f"No files in {folder}/")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Send images with captions like '112-50 kanan' or '112+100 kiri'. Use /zip to get all files zipped."
    )


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("zip", zip_and_send))
    app.add_handler(MessageHandler(filters.PHOTO & filters.Caption(), save_image))

    print("Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()
