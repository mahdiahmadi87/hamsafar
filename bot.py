import sqlite3
from telebot import TeleBot, types

# توکن ربات را اینجا قرار دهید
TOKEN = 'YOUR-TOKEN'

bot = TeleBot(TOKEN)

# اتصال به پایگاه داده
conn = sqlite3.connect('trips.db', check_same_thread=False)
c = conn.cursor()

# ایجاد جداول در پایگاه داده
c.execute('''CREATE TABLE IF NOT EXISTS trips
             (id INTEGER PRIMARY KEY AUTOINCREMENT, start_time TEXT, duration INTEGER, admin_id INTEGER, name TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS cars
             (id INTEGER PRIMARY KEY AUTOINCREMENT, trip_id INTEGER, capacity INTEGER, departure_time TEXT, owner_id INTEGER)''')
c.execute('''CREATE TABLE IF NOT EXISTS passengers
             (id INTEGER PRIMARY KEY AUTOINCREMENT, car_id INTEGER, user_id INTEGER, status TEXT)''')

conn.commit()

# لیست ادمین ها
admins = [1234567890]

# دستور شروع ربات
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton('مشاهده سفرها'))
    if message.chat.id in admins:
        markup.add(types.KeyboardButton('افزودن سفر جدید'))
        markup.add(types.KeyboardButton('حذف سفر'))
    msg = "به ربات مدیریت سفرها خوش آمدید!"
    bot.send_message(message.chat.id, msg, reply_markup=markup)

# افزودن سفر جدید (فقط برای ادمین ها)
@bot.message_handler(func=lambda message: message.text == 'افزودن سفر جدید' and message.chat.id in admins)
def add_trip(message):
    msg = bot.send_message(message.chat.id, "لطفا نام سفر خود را وارد کنید(مثال: صفادشت):")
    bot.register_next_step_handler(msg, get_start_time)

def get_start_time(message):
    name = message.text
    msg = bot.send_message(message.chat.id, "لطفا زمان شروع سفر را به فرمت YYYY-MM-DD HH:MM وارد کنید:")
    bot.register_next_step_handler(msg, get_duration, name)

def get_duration(message, name):
    try:
        start_time = message.text
        msg = bot.send_message(message.chat.id, "لطفا مدت سفر را به ساعت وارد کنید:")
        bot.register_next_step_handler(msg, add_trip_to_db, name, start_time)
    except ValueError:
        bot.send_message(message.chat.id, "فرمت زمان شروع اشتباه است. لطفا دوباره امتحان کنید.")
        add_trip(message)

def add_trip_to_db(message, name, start_time):
    try:
        duration = int(message.text)
        admin_id = message.chat.id
        c.execute("INSERT INTO trips (start_time, duration, admin_id, name) VALUES (?, ?, ?, ?)", (start_time, duration, admin_id, name))
        conn.commit()
        bot.send_message(message.chat.id, "سفر جدید با موفقیت ثبت شد.")
    except ValueError:
        bot.send_message(message.chat.id, "مدت سفر باید یک عدد صحیح باشد. لطفا دوباره امتحان کنید.")
        add_trip(message)

# حذف سفر (فقط برای ادمین ها)
@bot.message_handler(func=lambda message: message.text == 'حذف سفر' and message.chat.id in admins)
def del_trip(message):
    msg = bot.send_message(message.chat.id, "لطفا شماره سفر خود را وارد کنید(برای دیدن شماره سفر ها میتوانید از دکمه «مشاهده سفرها» استفاده کنید):")
    bot.register_next_step_handler(msg, del_trip_from_db)

def del_trip_from_db(message):
    try:
        trip_id = int(message.text)
        c.execute("DELETE FROM trips WHERE id = ?;", (trip_id, ))
        conn.commit()
        bot.send_message(message.chat.id, "سفر با موفقیت حذف شد.")
    except:
        bot.send_message(message.chat.id, "لطفا شماره سفر را درست وارد کنید.")
        add_trip(message)

# مشاهده سفرها
@bot.message_handler(func=lambda message: message.text == 'مشاهده سفرها')
def view_trips(message):
    c.execute("SELECT * FROM trips")
    trips = c.fetchall()
    if not trips:
        bot.send_message(message.chat.id, "هیچ سفری در حال حاضر وجود ندارد.")
    else:
        for trip in trips:
            trip_id, start_time, duration, admin_id, name = trip
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(f"مشاهده ماشین های سفر {name}", callback_data=f"view_cars_{trip_id}"))
            bot.send_message(message.chat.id, f"سفر {name}\nزمان شروع: {start_time}\nمدت سفر: {duration} ساعت\nشماره سفر: {trip_id}", reply_markup=markup)
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(types.KeyboardButton("افزودن ماشین جدید"))    
        markup.add(types.KeyboardButton("بازگشت به منوی اصلی"))
        msg = bot.send_message(message.chat.id, "برای اضافه کردن ماشین از دکمه های پایین صفحه استفاده کنید", reply_markup=markup)
        bot.register_next_step_handler(msg, add_view_car)


def add_view_car(message):
    if message.text == "بازگشت به منوی اصلی":
        send_welcome(message)
    elif message.text == "افزودن ماشین جدید":
        add_car(message)
 

# مشاهده ماشین های سفر
@bot.callback_query_handler(func=lambda call: call.data.startswith('view_cars_'))
def view_cars(call):
    trip_id = int(call.data.split('_')[2])
    c.execute("SELECT * FROM cars WHERE trip_id = ?", (trip_id,))
    cars = c.fetchall()
    if not cars:
        bot.send_message(call.message.chat.id, "هیچ ماشینی برای این سفر ثبت نشده است.")
    else:
        for car in cars:
            car_id, trip_id, capacity, departure_time, owner_id = car
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("درخواست سفر با این ماشین", callback_data=f"request_ride_{car_id}"))
            bot.send_message(call.message.chat.id, f"ماشین شماره {car_id}\nظرفیت: {capacity} نفر\nزمان حرکت: {departure_time}", reply_markup=markup)


# درخواست سفر با ماشین
@bot.callback_query_handler(func=lambda call: call.data.startswith('request_ride_'))
def request_ride(call):
    car_id = int(call.data.split('_')[2])
    c.execute("SELECT owner_id FROM cars WHERE id = ?", (car_id,))
    owner_id = c.fetchone()[0]
    if owner_id == call.message.chat.id:
        bot.send_message(call.message.chat.id, "شما نمی توانید برای ماشین خودتان درخواست سفر ارسال کنید.")
    else:
        c.execute("INSERT INTO passengers (car_id, user_id, status) VALUES (?, ?, ?)", (car_id, call.message.chat.id, 'pending'))
        conn.commit()
        bot.send_message(call.message.chat.id, "درخواست سفر شما با موفقیت ارسال شد. منتظر تایید صاحب ماشین باشید.")
        if (call.message.chat.username == None):
            bot.send_message(owner_id, f"کاربر {call.message.chat.first_name} {call.message.chat.last_name} برای سفر با ماشین شما درخواست ارسال کرده است.")
        else:
            bot.send_message(owner_id, f"کاربر {call.message.chat.first_name} {call.message.chat.last_name} (@{call.message.chat.username}) برای سفر با ماشین شما درخواست ارسال کرده است.")

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("تایید درخواست", callback_data=f"confirm_request_{car_id}_{call.message.chat.id}"))
        markup.add(types.InlineKeyboardButton("رد درخواست", callback_data=f"reject_request_{car_id}_{call.message.chat.id}"))
        bot.send_message(owner_id, "لطفا درخواست را تایید یا رد کنید:", reply_markup=markup)


# تایید یا رد درخواست
@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_request_') or call.data.startswith('reject_request_'))
def confirm_or_reject(call):
    data = call.data.split('_')
    action = data[0]
    car_id = int(data[2])
    user_id = int(data[3])

    if action == 'confirm':
        c.execute("UPDATE passengers SET status = 'confirmed' WHERE car_id = ? AND user_id = ?", (car_id, user_id))
        c.execute("SELECT capacity FROM cars WHERE id = ?", (car_id,))
        capacity = c.fetchone()[0]
        capacity -= 1
        c.execute("UPDATE cars SET capacity = ? WHERE id = ?", (capacity, car_id))
        conn.commit()
        bot.send_message(user_id, "درخواست سفر شما توسط صاحب ماشین تایید شد.")
        bot.send_message(call.message.chat.id, "شما درخواست سفر این کاربر را تایید کردید.")
    else:
        c.execute("DELETE FROM passengers WHERE car_id = ? AND user_id = ?", (car_id, user_id))
        conn.commit()
        bot.send_message(user_id, "متاسفانه درخواست سفر شما توسط صاحب ماشین رد شد.")
        bot.send_message(call.message.chat.id, "شما درخواست سفر این کاربر را رد کردید.")


# اضافه کردن ماشین جدید به سفر
# @bot.message_handler(func=lambda message: message.text == 'افزودن ماشین جدید')
def add_car(message):
    c.execute("SELECT id, start_time, name FROM trips")
    trips = c.fetchall()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for trip in trips:
        trip_id, start_time, name = trip
        markup.add(types.KeyboardButton(f"سفر {trip_id} ({name}) - {start_time}"))
    markup.add(types.KeyboardButton("بازگشت به منوی اصلی"))
    msg = bot.send_message(message.chat.id, "لطفا سفری را که می خواهید برای آن ماشین اضافه کنید انتخاب نمایید:", reply_markup=markup)
    bot.register_next_step_handler(msg, get_car_capacity)

def get_car_capacity(message):
    if message.text == "بازگشت به منوی اصلی":
        send_welcome(message)
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(types.KeyboardButton("بازگشت به منوی اصلی"))
        trip_id = int(message.text.split()[1])
        msg = bot.send_message(message.chat.id, "لطفا ظرفیت ماشین را وارد کنید:", reply_markup=markup)
        bot.register_next_step_handler(msg, get_car_departure_time, trip_id)
    
def get_car_departure_time(message, trip_id):
    if message.text == "بازگشت به منوی اصلی":
        send_welcome(message)
    else:
        try:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            markup.add(types.KeyboardButton("بازگشت به منوی اصلی"))
            capacity = int(message.text)
            msg = bot.send_message(message.chat.id, "لطفا زمان حرکت ماشین را به فرمت YYYY-MM-DD HH:MM وارد کنید:", reply_markup=markup)
            bot.register_next_step_handler(msg, add_car_to_db, trip_id, capacity)
        except ValueError:
            bot.send_message(message.chat.id, "ظرفیت ماشین باید یک عدد صحیح باشد. لطفا دوباره امتحان کنید.")
            add_car(message)

def add_car_to_db(message, trip_id, capacity):
    if message.text == "بازگشت به منوی اصلی":
        send_welcome(message)
    else:
        try:
            departure_time = message.text
            owner_id = message.chat.id
            c.execute("INSERT INTO cars (trip_id, capacity, departure_time, owner_id) VALUES (?, ?, ?, ?)",
                    (trip_id, capacity, departure_time, owner_id))
            conn.commit()
            bot.send_message(message.chat.id, "ماشین جدید با موفقیت به سفر اضافه شد.")
            send_welcome(message)
        except ValueError:
            bot.send_message(message.chat.id, "فرمت زمان حرکت اشتباه است. لطفا دوباره امتحان کنید.")
            add_car(message)

# راه اندازی ربات
bot.polling()