import os
import re
import zipfile
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

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
        await message.reply_text("Caption must contain 'kanan' or 'kiri'.")
        return

    if not cleared_folders:
        for f in [KANAN_DIR, KIRI_DIR]:
            for file in os.listdir(f):
                os.remove(os.path.join(f, file))
        cleared_folders = True
        await message.reply_text("Old images cleared. Starting fresh batch...")

    if message.photo:
        photo = message.photo[-1]
        file = await photo.get_file()

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
            for file in os.listdir(folder_name):
                zipf.write(os.path.join(folder_name, file), arcname=file)
        return zip_name

    for folder in [KANAN_DIR, KIRI_DIR]:
        if os.listdir(folder):
            zip_path = zip_folder(folder)
            await context.bot.send_document(chat_id=chat_id, document=open(zip_path, 'rb'))
        else:
            await context.bot.send_message(chat_id=chat_id, text=f"No files in {folder}/")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Forward me images with captions like '112-50-200 kanan' or '112+100 kiri'."
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
