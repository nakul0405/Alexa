import os
import time
import requests
import asyncio
import json
import random
import traceback
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from dotenv import load_dotenv
from datetime import datetime
from zoneinfo import ZoneInfo

# 🌟 Load environment variables
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT")
FORWARD_BOT_TOKEN = os.getenv("FORWARD_BOT_TOKEN")
FORWARD_CHAT_ID = os.getenv("FORWARD_CHAT_ID")

chat_history = {}
usage_count = {}

# 🧸 Load emoji-sticker mappings
with open("stickers.json", "r", encoding="utf-8") as f:
    sticker_data = json.load(f)

def get_matching_sticker(text):
    for item in sticker_data:
        emoji = item.get("emoji")
        if emoji in text:
            return item["file_id"]
    return None

def forward_to_private_log(user, user_input, bot_reply):
    try:
        name = user.full_name
        username = f"@{user.username}" if user.username else "NoUsername"
        time_now = datetime.now().strftime("%I:%M %p")

        text = f"""📩 *New Alexa Chat*\n
👤 *User:* {name} ({username}) 
🕒 *Time:* {time_now}  
💬 *Message:*  
`{user_input}`  
🤖 *Alexa's Reply:*  
`{bot_reply}`"""

        requests.post(
            f"https://api.telegram.org/bot{FORWARD_BOT_TOKEN}/sendMessage",
            json={"chat_id": FORWARD_CHAT_ID, "text": text, "parse_mode": "Markdown"}
        )
    except Exception as e:
        print("❌ Error forwarding:", e)

# ✅ OpenRouter integration with debug logging
def get_openrouter_reply(user_id, user_input):
    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://yourdomain.com",
            "X-Title": "AlexaTGOpenRouter"
        }

        url = "https://openrouter.ai/api/v1/chat/completions"
        past = chat_history.get(user_id, [])[-9:]

        system_prompt = {
            "role": "system",
            "content": SYSTEM_PROMPT or "You are Alexa, a human-like emotional AI who helps warmly and naturally."
        }

        messages = [system_prompt] + past + [{"role": "user", "content": user_input}]
        data = {
            "model": "mistralai/mistral-7b-instruct",
            "messages": messages,
            "temperature": 0.9,
            "top_p": 1
        }

        # 🐞 Debug logs
        print("📦 Payload being sent:")
        print(json.dumps(data, indent=2))
        print("🔐 Key starts with:", OPENROUTER_API_KEY[:10] + "...")

        res = requests.post(url, headers=headers, json=data)

        if res.status_code != 200:
            print(f"❌ Status Code: {res.status_code}")
            print("❌ Response:", res.text)
            return "🥺 Alexa thoda confuse ho gayi hai. Kuch galti ho gayi hai OpenRouter ke side se."

        reply = res.json()['choices'][0]['message']['content']

        chat_history[user_id] = chat_history.get(user_id, []) + [
            {"role": "user", "content": user_input},
            {"role": "assistant", "content": reply}
        ]
        usage_count[user_id] = usage_count.get(user_id, 0) + 1

        return reply

    except Exception as e:
        print("❌ OpenRouter API error:")
        traceback.print_exc()
        return "🥺 Alexa thoda confuse ho gayi hai. Thoda ruk jaa..."

# ---------------------- COMMANDS -----------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_full_name = update.effective_user.full_name
    welcome_msg = (
        f"Hey, {user_full_name}! 👋\n\n"
        "Main hoon *Alexa* — par asli wali nahi, *AI* wali 😎\n\n"
        "Sawaal poochho, coding karao, ya life ke confusion suljhao... sab kuch *Free Hand* hai! 🥹\n\n"
        "*2 minute me reply mil jaayega* — bas *dil se puchhna!* ❤️‍🔥\n"
        "_Made with ❤️ and Madness by @Nakulrathod0405_"
    )
    await update.message.reply_text(welcome_msg, parse_mode="Markdown")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_history.pop(user_id, None)
    usage_count.pop(user_id, None)
    await update.message.reply_text("🔄 Chat history reset!")

async def usage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    count = usage_count.get(user_id, 0)
    await update.message.reply_text(f"📊 Total messages: {count}")

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
        msg = await update.message.reply_text(
            "🤖 *Bot Info:*\n\n"
            " 🍬 Version: `OpenRouter + DeepSeek`\n"
            " 👩‍⚖️ Model: `deepseek-chat`\n"
            " 👨‍💻 Developer: [Nakul Rathod](https://t.me/Nakulrathod0405)\n"
            " 🧬 API: `https://openrouter.ai/api/v1/chat/completions`",
            parse_mode="Markdown"
        )
        await asyncio.sleep(10)
        await context.bot.delete_message(chat_id=msg.chat_id, message_id=msg.message_id)
    except Exception as e:
        print("❌ Error in /info command:", e)

# ---------------------- MESSAGE HANDLER -----------------------

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_input = update.message.text
    user_id = user.id
    name = user.full_name
    username = f"@{user.username}" if user.username else "NoUsername"
    time_now = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%d %b %Y, %I:%M %p")

    thinking = await update.message.reply_text("👩‍💻 Alexa is typing...")

    reply = get_openrouter_reply(user_id, user_input)

    await context.bot.delete_message(chat_id=thinking.chat_id, message_id=thinking.message_id)

    sticker_id = get_matching_sticker(user_input)
    if sticker_id:
        await update.message.reply_sticker(sticker_id)

    await update.message.reply_text(reply)
    forward_to_private_log(user, user_input, reply)

    print(f"🗣️ User: [{name} ({username})] at {time_now}")
    print(f"💬 Message: {user_input}")
    print(f"🤖 Bot reply: {reply}")
    print("-" * 40)

# ---------------------- RUN -----------------------

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("usage", usage))
    app.add_handler(CommandHandler("info", info))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🤖 Alexa is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
