import telebot
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os
import schedule
import time
import threading

# 🔐 Bot token
TOKEN = "7865664873:AAF1f-If8c3WhLazmsTsaKt6hioYHK3kJGY
"
bot = telebot.TeleBot(TOKEN)

# 📄 Google Sheets sozlamalari
sheet_url = "https://docs.google.com/spreadsheets/d/1WXIS0c9Rpqqe3FWSaRQTb8VeezD_3drEqGIvh1JUjR0/edit"
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json", scope)
client = gspread.authorize(creds)

# 📁 Telefon raqamlar bazasi fayli
DB_FILE = "user_db.json"

# 🧩 JSONdan o‘qish
def load_user_data():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    return {}

# 🧩 JSONga yozish
def save_user_data(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f)

# 🔄 Avtomatik xabar yuboruvchi funksiya
def auto_notify_users():
    try:
        users_sheet = client.open_by_url(sheet_url).worksheet("users")
        users = users_sheet.get_all_records()

        for row in users:
            phone = str(row.get("Telefon", "")).strip()
            user_name = str(row.get("Ism", "")).strip()
            chat_id = str(row.get("chat_id", "")).strip()

            if not user_name or not chat_id:
                continue

            try:
                user_sheet = client.open_by_url(sheet_url).worksheet(user_name)
                data = user_sheet.get_all_records()

                total = 0
                for row_data in data:
                    summa = str(row_data.get("summa", "")).replace(" ", "").replace(",", "").strip()
                    try:
                        total += int(summa)
                    except:
                        continue

                if total > -100:
                    sign = "+" if total >= 0 else "-"
                    balans = f"{sign}{abs(total):,}".replace(",", " ")
                    text = f"📢 Sizning hozirgi balansingiz: {balans}"
                    bot.send_message(int(chat_id), text)

            except Exception as e:
                print(f"❌ {user_name} uchun xatolik:", e)

    except Exception as e:
        print("❌ Auto-notify xatolik:", e)

# ▶️ /start komandasi
@bot.message_handler(commands=['start'])
def start(message):
    user_data = load_user_data()
    chat_id = str(message.chat.id)

    if chat_id not in user_data:
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        contact_btn = telebot.types.KeyboardButton("📱 Kontakt yuborish", request_contact=True)
        markup.add(contact_btn)
        bot.send_message(message.chat.id, "Salom! Avval kontakt yuboring:", reply_markup=markup)
    else:
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📥 Balance")
        bot.send_message(message.chat.id, "📥 Balansni ko‘rish uchun tugmani bosing:", reply_markup=markup)

# 📱 Kontakt yuborish
@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    try:
        phone = message.contact.phone_number.strip()
        chat_id = str(message.chat.id)

        user_data = load_user_data()
        user_data[chat_id] = phone
        save_user_data(user_data)

        # chat_id ni Sheetga yozish
        try:
            users_sheet = client.open_by_url(sheet_url).worksheet("users")
            all_users = users_sheet.get_all_records()
            for i, row in enumerate(all_users, start=2):  # 2-qatordan boshlab
                if str(row.get("Telefon", "")).strip() == phone:
                    users_sheet.update_cell(i, 3, str(chat_id))  # 3-ustun = chat_id
                    break
        except Exception as e:
            print("❌ chat_id yozishda xatolik:", e)

        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📥 Balance")
        bot.send_message(chat_id, "✅ Kontakt saqlandi. Endi '📥 Balance' tugmasini bosing.", reply_markup=markup)

    except Exception as e:
        print("❌ Xatolik:", e)
        bot.send_message(message.chat.id, "❌ Kontaktni qabul qilishda xatolik.")

# 📥 Balance tugmasi
@bot.message_handler(func=lambda message: message.text == "📥 Balance")
def send_balance(message):
    try:
        chat_id = str(message.chat.id)
        user_data = load_user_data()
        phone = user_data.get(chat_id)

        if not phone:
            bot.send_message(message.chat.id, "❌ Avval kontakt yuboring.")
            return

        # Ismni topamiz
        users_sheet = client.open_by_url(sheet_url).worksheet("users")
        users = users_sheet.get_all_records()

        user_name = None
        for row in users:
            row_lower = {k.lower().strip(): str(v).strip() for k, v in row.items()}
            if row_lower["telefon"] == phone:
                user_name = row_lower["ism"]
                break

        if not user_name:
            bot.send_message(message.chat.id, "❌ Telefon raqamingiz topilmadi.")
            return

        # Ma'lumotlar
        user_sheet = client.open_by_url(sheet_url).worksheet(user_name)
        data = user_sheet.get_all_records()

        rows = []
        total = 0
        for row in data:
            sana = str(row.get("sana", "")).strip()
            tavsif = str(row.get("tavsif", "")).strip()
            summa = str(row.get("summa", "")).replace(" ", "").replace(",", "").strip()

            try:
                qiymat = int(summa)
                total += qiymat
                formatted = f"{abs(qiymat):,}".replace(",", " ")
                belgi = "💰" if qiymat >= 0 else "💸"
                rows.append(f"{sana} | {tavsif} | {belgi}{'+' if qiymat >= 0 else '-'}{formatted}")
            except:
                continue

        text = "✅ Ma'lumotlar:\n\n" + "\n".join(rows) + f"\n\n💼 Jami balans: {'+' if total >= 0 else '-'}{abs(total):,}".replace(",", " ")
        bot.send_message(message.chat.id, text)

    except Exception as e:
        print("❌ Xatolik:", e)
        bot.send_message(message.chat.id, "❌ Xatolik yuz berdi. Admin bilan bog‘laning.")

# ⏰ Schedule ishga tushirish
schedule.every().day.at("09:00").do(auto_notify_users)
# Test uchun: har 1 daqiqada (hozircha)
# schedule.every(1).minutes.do(auto_notify_users)

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(60)

threading.Thread(target=run_scheduler).start()

# 🚀 Bot ishga tushadi
print("🤖 Bot ishga tushdi...")
bot.infinity_polling()
