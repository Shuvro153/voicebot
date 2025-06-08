import os
import telebot
import requests
from telebot import types
from dotenv import load_dotenv
from generate_voice import generate_voice_with_fallback, delete_history_item

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

user_voice_ids = {}
user_states = {}
user_settings = {}
user_last_history = {}

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "👋 Welcome! Use /menu to see available commands.")

@bot.message_handler(commands=['menu'])
def show_menu(message):
    menu_text = "*Available Commands:*\n\n" \
                "/start - Welcome message\n" \
                "/menu - Show this command list\n" \
                "/credit - Show ElevenLabs credit balance\n" \
                "/gen - Start voice generation"
    bot.send_message(message.chat.id, menu_text, parse_mode="Markdown")

@bot.message_handler(commands=['credit'])
def check_credit(message):
    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
    url = "https://api.elevenlabs.io/v1/user/subscription"
    headers = {"xi-api-key": ELEVENLABS_API_KEY}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            total = data.get("character_limit", 0)
            used = data.get("character_count", 0)
            remaining = total - used
            msg = "*ElevenLabs API Credit Summary:*\n" \
                  f"Total Characters: {total}\n" \
                  f"Used Characters: {used}\n" \
                  f"Remaining Characters: {remaining}"
            bot.send_message(message.chat.id, msg, parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, f"Error: {response.status_code}")
    except Exception as e:
        bot.send_message(message.chat.id, f"Exception: {e}")

@bot.message_handler(commands=['gen'])
def handle_gen(message):
    chat_id = message.chat.id
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("1. Your Set Voice ID", callback_data="use_voice_id"))
    markup.add(types.InlineKeyboardButton("2. Change Your Voice ID", callback_data="change_voice_id"))
    bot.send_message(chat_id, "🎙️ Voice Generation Options:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ["use_voice_id", "change_voice_id"])
def handle_voice_selection(call):
    chat_id = call.message.chat.id
    if call.data == "change_voice_id":
        user_states[chat_id] = "awaiting_voice_id"
        bot.send_message(chat_id, "✏️ Enter your new ElevenLabs Voice ID:")
    else:
        if chat_id not in user_voice_ids:
            bot.send_message(chat_id, "⚠️ No voice ID set. Please set one first.")
            return
        show_gen_options(chat_id)

@bot.message_handler(func=lambda message: user_states.get(message.chat.id) == "awaiting_voice_id")
def set_voice_id(message):
    user_voice_ids[message.chat.id] = message.text.strip()
    user_states.pop(message.chat.id, None)
    bot.send_message(message.chat.id, f"✅ Voice ID set: `{message.text.strip()}`", parse_mode="Markdown")
    show_gen_options(message.chat.id)

def show_gen_options(chat_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("1. Voice Settings", callback_data="voice_settings"))
    markup.add(types.InlineKeyboardButton("2. Input Your Text", callback_data="input_text"))
    bot.send_message(chat_id, "➡️ Select what to do next:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "voice_settings")
def ask_settings(call):
    chat_id = call.message.chat.id
    user_states[chat_id] = "awaiting_settings"
    bot.send_message(chat_id, "⚙️ Enter settings as:\n`stability similarity style boost`\nExample: `50 70 0 1`", parse_mode="Markdown")

@bot.message_handler(func=lambda message: user_states.get(message.chat.id) == "awaiting_settings")
def save_settings(message):
    try:
        stability, similarity, style, boost = map(float, message.text.strip().split())
        user_settings[message.chat.id] = {
            "stability": stability / 100,
            "similarity_boost": similarity / 100,
            "style": style / 100,
            "use_speaker_boost": bool(boost)
        }
        user_states.pop(message.chat.id, None)
        bot.send_message(message.chat.id, "✅ Settings saved.")
        show_gen_options(message.chat.id)
    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid input. Please enter 4 numbers like: `50 70 0 1`", parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "input_text")
def ask_text(call):
    chat_id = call.message.chat.id
    user_states[chat_id] = "awaiting_text"
    bot.send_message(chat_id, "✏️ Send the text you want to convert to voice:")

@bot.message_handler(func=lambda message: user_states.get(message.chat.id) == "awaiting_text")
def generate_voice(message):
    chat_id = message.chat.id
    text = message.text.strip()
    voice_id = user_voice_ids.get(chat_id)

    if not voice_id:
        bot.send_message(chat_id, "⚠️ No voice ID found.")
        return

    settings = user_settings.get(chat_id, {
        "stability": 0.5,
        "similarity_boost": 0.75,
        "style": 0.0,
        "use_speaker_boost": True
    })

    bot.send_message(chat_id, "🎧 Generating voice... Please wait.")
    try:
        audio_data, used_api_key, history_item_id = generate_voice_with_fallback(text, voice_id, settings)
        filename = f"output_{chat_id}.mp3"
        with open(filename, "wb") as f:
            f.write(audio_data)

        with open(filename, "rb") as audio_msg:
            sent = bot.send_audio(chat_id, audio_msg, title="Generated Voice")

        os.remove(filename)

        user_last_history[chat_id] = (history_item_id, used_api_key)

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🗑️ Delete from ElevenLabs", callback_data="delete_history"))
        bot.send_message(chat_id, "✅ Done. Choose an action:", reply_markup=markup)
    except Exception as e:
        bot.send_message(chat_id, f"❌ Error: {e}")
    user_states.pop(chat_id, None)

@bot.callback_query_handler(func=lambda call: call.data == "delete_history")
def delete_voice(call):
    chat_id = call.message.chat.id
    info = user_last_history.get(chat_id)
    if not info:
        bot.send_message(chat_id, "⚠️ No previous history found.")
        return

    history_id, api_key = info
    try:
        success = delete_history_item(history_id, api_key)
        if success:
            bot.send_message(chat_id, "🗑️ Deleted from ElevenLabs history.")
        else:
            bot.send_message(chat_id, "❌ Failed to delete from history.")
    except Exception as e:
        bot.send_message(chat_id, f"❌ Exception: {e}")

bot.infinity_polling()
