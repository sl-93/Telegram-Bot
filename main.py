# import necessary libraries
import telebot
import mysql.connector
import json

# create the database
mydb = mysql.connector.connect(
    host = "your host name",
    user = "your user name",
    passwd ="your password",
    database = "the database name",  # this line was added after creating database!
)

# create a cursor
my_cursor = mydb.cursor()

TOKEN = "the bot's token"
bot = telebot.TeleBot(TOKEN)

photos = []


@bot.message_handler(commands=['start'])
def start(message):
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True, row_width=2)
    markup.add(telebot.types.KeyboardButton(text='به اشتراک گذاری شماره همراه', request_contact=True))
    bot.send_message(message.chat.id, "خوش آمدید\n\n لطفا شماره همراه خود را وارد نمایید.", reply_markup=markup)


@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    # Get the user's phone number
    phone_number = message.contact.phone_number

    # Ask for the user's name
    bot.send_message(message.chat.id, "لطفا نام و نام خانوادگی خود را وارد نمایید.")

    # Register a new handler for the user's name
    bot.register_next_step_handler(message, handle_name, phone_number)

def handle_name(message, phone_number):
    # Get the user's name
    c_name = message.text
    phone_number = phone_number
    # Where clause
    my_cursor.execute("SELECT * FROM users WHERE iduser = %s", [message.chat.id]) # Also, we can use <name LIKE "j%", instead of WHERE
    result = my_cursor.fetchone()

    if result == None:
        # add a record to the table
        photo_list = []
        list_json = json.dumps(photo_list)
        sqlstuff = "INSERT INTO users(iduser, name, phone, amount, pending_amount, account_id, photo_list) VALUES (%s, %s, %s, %s, %s, %s, %s)"
        record1 = (message.chat.id, c_name, phone_number, 0, 0, 0, list_json)
        my_cursor.execute(sqlstuff, record1)
        mydb.commit()
    else:
        c_name = result[1]
        phone_number = result[2]
    
    markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add(telebot.types.KeyboardButton(text='ثبت سفارش'))
    markup.add(telebot.types.KeyboardButton(text='اعلام مبلغ واریزی'))
    bot.send_message(message.chat.id, 'لطفا یکی از دو گزینه زیر را انتخاب نمایید.', reply_markup=markup)

def handle_amount(message):
    pending_amount = message.text

    if  30 > float(pending_amount):
        my_cursor.execute("SELECT MIN(capacity) AS minimum FROM accounts") 
        result = my_cursor.fetchone() 
        my_cursor.execute("SELECT idaccounts FROM accounts WHERE capacity=%s", [result[0]]) 
        idaccounts = my_cursor.fetchone() 
        my_cursor.execute("SELECT * FROM accounts WHERE idaccounts = %s", [idaccounts[0]]) # Also, we can use <name LIKE "j%", instead of WHERE
        result = my_cursor.fetchone()
        bot.send_message(message.chat.id, f"لطفا مبلغ مورد نظر را به حساب زیر وارد کنید:\n\n{result[0]}")

    else:
        my_cursor.execute("SELECT MAX(capacity) AS minimum FROM accounts") 
        result = my_cursor.fetchone() 
        my_cursor.execute("SELECT idaccounts FROM accounts WHERE capacity=%s", [result[0]]) 
        idaccounts = my_cursor.fetchone() 
        my_cursor.execute("SELECT * FROM accounts WHERE idaccounts = %s", [idaccounts[0]]) # Also, we can use <name LIKE "j%", instead of WHERE
        result = my_cursor.fetchone()
        bot.send_message(message.chat.id, f"لطفا مبلغ مورد نظر را به حساب زیر وارد کنید:\n\n{result[0]}")
    

    my_cursor.execute("UPDATE users SET pending_amount =%s WHERE iduser = %s", (pending_amount, message.chat.id))
    mydb.commit()
    my_cursor.execute("UPDATE users SET account_id =%s WHERE iduser = %s", (idaccounts[0], message.chat.id))
    mydb.commit()

    markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add(telebot.types.KeyboardButton(text='ارسال عکس فیش واریزی'))
    markup.add(telebot.types.KeyboardButton(text='بازگشت'))
    bot.send_message(message.chat.id, 'برای ارسال عکس فیش واریزی از کلید زیر استفاده نمایید.', reply_markup=markup)

@bot.message_handler(content_types=['photo'])  
def announce_photo(message):
    if message.photo:
        my_cursor.execute("SELECT photo_list FROM users WHERE iduser = %s", [message.chat.id])
        result = my_cursor.fetchone()
        retrieved_list = json.loads(result[0])
        retrieved_list.append(message.photo[-1].file_id)
        updated_list_json = json.dumps(retrieved_list)
        my_cursor.execute("UPDATE users SET photo_list=%s WHERE iduser=%s", (updated_list_json, message.chat.id))
        mydb.commit()
        handle_photo(message)
    else:
        markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        markup.add(telebot.types.KeyboardButton(text='ارسال مجدد عکس فیش واریزی'))
        bot.send_message(message.chat.id, ' لطفا فقط عکس فیش واریزی را ارسال کنید!', reply_markup=markup)

def handle_photo(message):
    markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add(telebot.types.KeyboardButton(text='ارسال عکس دیگر'))
    markup.add(telebot.types.KeyboardButton(text='اتمام'))
    bot.send_message(message.chat.id, 'اگر برای مبلغ مورد نظر عکس دیگری می خواهید ارسال کنید، از کلید "ارسال عکس دیگر" استفاده نمایید.\n\nدر غیر این صورت برای اتمام واریز، از کلید "اتمام" استفااده کنید.', reply_markup=markup)


def exec_photo(message):
    # Where clause
    my_cursor.execute("SELECT * FROM users WHERE iduser = %s", [message.chat.id]) # Also, we can use <name LIKE "j%", instead of WHERE
    result = my_cursor.fetchone()
    u_amount = result[3]
    u_amount = u_amount + result[4]
    account_id = result[5]
    photos = json.loads(result[6])
    my_cursor.execute("UPDATE users SET amount =%s WHERE iduser = %s", (u_amount, message.chat.id))
    mydb.commit()
    bot.send_message("-1002070778640", f"نام کاربر: {result[1]}\n شماره کاربر: {result[2]}\n مقدار واریزی: {result[4]}\n\n👇👇👇")
    for photo in photos:
        bot.send_photo("-1002070778640", photo)

    photos = []
    photos = json.dumps(photos)
    my_cursor.execute("UPDATE users SET photo_list=%s WHERE iduser=%s", (photos, message.chat.id))
    mydb.commit()
    my_cursor.execute("SELECT * FROM accounts WHERE idaccounts = %s", [account_id]) # Also, we can use <name LIKE "j%", instead of WHERE
    result2 = my_cursor.fetchone()
    account_input = result2[2]
    account_input = account_input + result[4]
    capacity = result2[1]
    capacity = capacity - result[4]
    my_cursor.execute("UPDATE accounts SET account_input =%s WHERE idaccounts = %s", (account_input, account_id))
    mydb.commit()
    my_cursor.execute("UPDATE accounts SET capacity =%s WHERE idaccounts = %s", (capacity, account_id))
    mydb.commit()
    markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add(telebot.types.KeyboardButton(text='واریز مبلغ جدید'))
    bot.send_message(message.chat.id, 'در صورتی که می خواهید مبلغ جدیدی واریز کنید، از کلید زیر استفاده کنید.' ,reply_markup=markup)



# Admin's section
@bot.message_handler(commands=['AdminCommand'])
def Welcome(message):
    suggestions = [
        {'command': '/CreateAccount', 'text': 'افزودن حساب جدید'},
        {'command': '/EditAccounts', 'text': 'ویرایش حساب ها'},
        {'command': '/DeleteAccounts', 'text': 'حذف حساب ها'},
        {'command': '/Report', 'text': 'گزارش حساب ها'}
    ]
    markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    for suggestion in suggestions:
        markup.add(telebot.types.KeyboardButton(suggestion['text']))

    bot.send_message(message.chat.id, 'عملیات مورد نظر را انتخاب نمایید', reply_markup=markup)

@bot.message_handler(func=lambda message: True)
def handle_commands(message):
    # Handle the selected command
    command = message.text
    if command == 'افزودن حساب جدید':
        handle_create_accounts(message, edit=False, num = None)
    elif command == 'ویرایش حساب ها':
        handle_edit_accounts(message)
    elif command == 'حذف حساب ها':
        delete_accounts(message)
    elif command == 'گزارش حساب ها':
        gozaresh(message)
    elif command == 'انصراف':
        suggestions = [
        {'command': '/CreateAccount', 'text': 'افزودن حساب جدید'},
        {'command': '/EditAccounts', 'text': 'ویرایش حساب ها'},
        {'command': '/DeleteAccounts', 'text': 'حذف حساب ها'},
        {'command': '/Report', 'text': 'گزارش حساب ها'}
        ]
        markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        for suggestion in suggestions:
            markup.add(telebot.types.KeyboardButton(suggestion['text']))
        bot.send_message(message.chat.id, 'عملیات مورد نظر را انتخاب نمایید', reply_markup=markup)

    elif command == 'اعلام مبلغ واریزی':
        bot.send_message(message.chat.id, "لطفا مبلغی که می خواهید واریز نمایید را اعلام کنید:")
        bot.register_next_step_handler(message, handle_amount)
    elif command == 'بازگشت':
        bot.send_message(message.chat.id, "لطفا مبلغی که می خواهید واریز نمایید را اعلام کنید:")
        bot.register_next_step_handler(message, handle_amount)
    elif command == 'ثبت سفارش':
        markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        markup.add(telebot.types.KeyboardButton(text='اعلام مبلغ واریزی'))
        bot.send_message(message.chat.id, 'این قسمت در دست راه اندازی است.\n\nلطفا از کلید زیر استفاده نمایید!', reply_markup=markup)
    elif command == 'ارسال عکس فیش واریزی':
        bot.send_message(message.chat.id, " لطفا عکس فیش واریزی را ارسال نمایید.")
        bot.register_next_step_handler(message, announce_photo)
    elif command == 'ارسال مجدد عکس فیش واریزی':
        bot.send_message(message.chat.id, " لطفا عکس فیش واریزی را ارسال نمایید.")
        bot.register_next_step_handler(message, announce_photo)
    elif command == 'ارسال عکس دیگر':
        bot.send_message(message.chat.id, " لطفا عکس فیش واریزی را ارسال نمایید.")
        bot.register_next_step_handler(message, announce_photo)
    elif command == 'اتمام':
        exec_photo(message)
    elif command == 'واریز مبلغ جدید':
        bot.send_message(message.chat.id, "لطفا مبلغی که می خواهید واریز نمایید را اعلام کنید:")
        bot.register_next_step_handler(message, handle_amount)

    my_cursor.execute("SELECT COUNT(*) FROM accounts")
    number_of_rows = my_cursor.fetchone()
    for i in range(number_of_rows[0]):
        if command == f'حساب شماره {i + 1}':
            handle_create_accounts(message, edit=True, num = i+1)
    for i in range(number_of_rows[0]):
        if command == f'حذف حساب {i+1}':
            handle_delete_accounts(message, num = i+1)


def handle_create_accounts(message, edit, num):
    my_cursor.execute("SELECT COUNT(*) FROM accounts")
    number_of_rows = my_cursor.fetchone()
    if edit == False:
        msg = bot.send_message(message.chat.id, f"لطفا اطلاعات حساب {int(number_of_rows[0]) + 1} را وارد نمایید:")
        bot.register_next_step_handler(msg, set_cart_name, edit, int(number_of_rows[0]) + 1)
    elif edit == True:
        msg = bot.send_message(message.chat.id, f"لطفا اطلاعات حساب {num} را وارد نمایید:")
        bot.register_next_step_handler(msg, set_cart_name, edit, num)


def set_cart_name(message, edit, num):
    account_info = message.text
    if edit == False:
        sqlstuff = "INSERT INTO accounts(account_info, capacity, account_input) VALUES ( %s, %s, %s)"
        record1 = (account_info, 0, 0)
        my_cursor.execute(sqlstuff, record1)
        mydb.commit()
        my_cursor.execute("SELECT COUNT(*) FROM accounts")
        number_of_rows = my_cursor.fetchone()
        msg = bot.send_message(message.chat.id, f"ظرفیت حساب {number_of_rows[0]} را وارد نمایید")
        bot.register_next_step_handler(msg, set_cart_amount, edit, number_of_rows[0])
    elif edit == True:
        my_cursor.execute("UPDATE accounts SET account_info =%s WHERE idaccounts = %s", (account_info, num))
        mydb.commit()
        msg = bot.send_message(message.chat.id, f"ظرفیت حساب {num} را وارد نمایید")
        bot.register_next_step_handler(msg, set_cart_amount, edit, num)


def set_cart_amount(message, edit, num):
    amount_cart = message.text
    my_cursor.execute("SELECT COUNT(*) FROM accounts")
    number_of_rows = my_cursor.fetchone() 
    if edit == False:
        my_cursor.execute("UPDATE accounts SET capacity =%s WHERE idaccounts = %s", (float(amount_cart), number_of_rows[0]))
        mydb.commit()
        bot.send_message(message.chat.id, "مشخصات حساب مورد نظر با موفقیت ذخیره شد!")
    elif edit == True:
        my_cursor.execute("UPDATE accounts SET capacity =%s WHERE idaccounts = %s", (amount_cart, num))
        mydb.commit()
        bot.send_message(message.chat.id, "مشخصات حساب مورد نظر با موفقیت ویرایش شد!")

    suggestions = [
        {'command': '/CreateAccount', 'text': 'افزودن حساب جدید'},
        {'command': '/EditAccounts', 'text': 'ویرایش حساب ها'},
        {'command': '/DeleteAccounts', 'text': 'حذف حساب ها'},
        {'command': '/Report', 'text': 'گزارش حساب ها'}
    ]
    markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    for suggestion in suggestions:
        markup.add(telebot.types.KeyboardButton(suggestion['text']))
    bot.send_message(message.chat.id, 'عملیات مورد نظر را انتخاب نمایید', reply_markup=markup)


def gozaresh(message):
    list_accounts = []
    my_cursor.execute("SELECT * FROM accounts")
    result = my_cursor.fetchall()
    for row in result:
        list_accounts.append(f"حساب{row[3]}:\n{row[0]}\nظرفیت حساب:\n{row[1]}\nمقدار واریز شده به حساب:\n{row[2]}\n\n")
    list_string = '\n'.join(list_accounts)
    bot.send_message(message.chat.id, f'حساب ها\n\n{list_string}')

    suggestions = [
    {'command': '/CreateAccount', 'text': 'افزودن حساب جدید'},
    {'command': '/EditAccounts', 'text': 'ویرایش حساب ها'},
    {'command': '/DeleteAccounts', 'text': 'حذف حساب ها'},
    {'command': '/Report', 'text': 'گزارش حساب ها'}
    ]
    markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    for suggestion in suggestions:
        markup.add(telebot.types.KeyboardButton(suggestion['text']))
    bot.send_message(message.chat.id, 'عملیات مورد نظر را انتخاب نمایید', reply_markup=markup)


def handle_edit_accounts(message):
    markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    list_accounts = []
    my_cursor.execute("SELECT * FROM accounts")
    result = my_cursor.fetchall()
    for row in result:
        list_accounts.append(f"حساب{row[3]}:\n{row[0]}\n\nظرفیت حساب:\n{row[1]}\n\n")
        markup.add(telebot.types.KeyboardButton(f'حساب شماره {row[3]}'))
    list_string = '\n'.join(list_accounts)
    bot.send_message(message.chat.id, f'حساب ها\n\n{list_string}')
    markup.add(telebot.types.KeyboardButton(text='انصراف'))
    bot.send_message(message.chat.id, 'حساب مورد نظر را انتخاب نمایید.', reply_markup=markup)

def delete_accounts(message):
    markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    list_accounts = []
    my_cursor.execute("SELECT * FROM accounts")
    result = my_cursor.fetchall()
    for row in result:
        list_accounts.append(f"حساب{row[3]}:\n{row[0]}\n\nظرفیت حساب:\n{row[1]}\n\n")
        markup.add(telebot.types.KeyboardButton(f'حذف حساب {row[3]}'))
    list_string = '\n'.join(list_accounts)
    bot.send_message(message.chat.id, f'حساب ها\n\n{list_string}')
    markup.add(telebot.types.KeyboardButton(text='انصراف'))
    bot.send_message(message.chat.id, 'حساب مورد نظر را انتخاب نمایید.', reply_markup=markup)

def handle_delete_accounts(message, num):

    my_cursor.execute("DELETE FROM accounts WHERE idaccounts = %s", [num])
    my_cursor.execute("ALTER TABLE accounts DROP COLUMN idaccounts")
    my_cursor.execute("ALTER TABLE accounts ADD idaccounts INTEGER AUTO_INCREMENT PRIMARY KEY AFTER account_input")
    mydb.commit()
    bot.send_message(message.chat.id, "حساب مورد نظر حذف شد!")

    suggestions = [
    {'command': '/CreateAccount', 'text': 'افزودن حساب جدید'},
    {'command': '/EditAccounts', 'text': 'ویرایش حساب ها'},
    {'command': '/DeleteAccounts', 'text': 'حذف حساب ها'},
    {'command': '/Report', 'text': 'گزارش حساب ها'}
    ]
    markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    for suggestion in suggestions:
        markup.add(telebot.types.KeyboardButton(suggestion['text']))
    bot.send_message(message.chat.id, 'عملیات مورد نظر را انتخاب نمایید', reply_markup=markup)

bot.infinity_polling()
