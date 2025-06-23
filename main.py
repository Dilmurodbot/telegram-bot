import os
import telebot
from telebot import types
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Tokenni atrof-muhitdan olish
TOKEN = os.getenv("TOKEN")
bot = telebot.TeleBot(TOKEN)

# Google Sheets ulanish
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json", scope)
client = gspread.authorize(creds)

# Google Sheet URL
sheet_url = "https://docs.google.com/spreadsheets/d/1WXIS0c9Rpqqe3FWSaRQTb8VeezD_3drEqGIvh1JUjR0/edit"

# Foydalanuvchi ma’lumotlarini saqlash
users_data = {}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    button = types.KeyboardButton("📲 Kontakt yuborish", request_contact=True)
    markup.add(button)
    bot.send_message(message.chat.id, "Salom! Davom etish uchun kontakt yuboring:", reply_markup=markup)

@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    phone = message.contact.phone_number
    if not phone.startswith('+'):
        phone = '+' + phone
    users_data[message.chat.id] = phone

    bot.send_message(message.chat.id, f"📲 Kontakt qabul qilindi: {phone}", reply_markup=main_menu())

@bot.message_handler(func=lambda msg: msg.text == "📥 Balance")
def show_balance(message):
    chat_id = message.chat.id
    phone = users_data.get(chat_id)

    if not phone:
        bot.send_message(chat_id, "❌ Iltimos, avval kontakt yuboring /start")
        return

    try:
        users_sheet = client.open_by_url(sheet_url).worksheet("users")
        users_data_all = users_sheet.get_all_records()

        user_name = None
        for row in users_data_all:
            if str(row["Telefon"]).strip() == phone.strip():
                user_name = row["Ism"].strip()
                break

        if not user_name:
            bot.send_message(chat_id, "❌ Siz ro‘yxatdan o‘tmagansiz.")
            return

        sheet = client.open_by_url(sheet_url).worksheet(user_name)
        records = sheet.get_all_records()

        if not records:
            bot.send_message(chat_id, "📭 Sizda hali ma'lumot yo‘q.")
            return

        text = "✅ Ma'lumotlar:\n\n"
        balance = 0

        for row in records:
            sana = row['sana']
            tavsif = row['tavsif']
            summa = row['summa']
            summa_str = str(summa).replace(" ", "").replace(",", "")
            try:
                value = float(summa_str)
                balance += value
                if value >= 0:
                    text += f"{sana} | {tavsif} | 💰+{int(value)}\n"
                else:
                    text += f"{sana} | {tavsif} | 💸{int(value)}\n"
            except:
                continue

        text += f"\n💼 Jami balans: {int(balance)}"
        bot.send_message(chat_id, text)

    except Exception as e:
        bot.send_message(chat_id, f"❌ Xatolik: {e}")

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📥 Balance")
    return markup

# Botni ishga tushiramiz
print("🤖 Bot ishga tushdi...")
bot.infinity_polling()
