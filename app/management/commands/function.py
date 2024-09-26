import logging

from telebot import types
from telebot.types import InputMediaPhoto

from app.models import BotUser, TgUser


def handle_image_upload(message, state):
    from app.management.commands.shared import user_states
    from app.management.commands.bot import bot
    user_id = message.from_user.id
    image_storage = [
        'passport_fronts', 'passport_backs',
        'front_tex_passports', 'back_tex_passports', 'pravas'
    ]
    steps = {
        4: ('Pasport old qismini', 5),
        5: ('Pasport orqa qismini', 6),
        6: ('Tex pasport old qismini', 7),
        7: ('Tex pasport orqa qismini', 8),
        8: ('Prava suratini', 9),
        9: ('Ma’lumotlaringiz saqlandi.', None)
    }

    if message.photo:
        state.data[image_storage[state.step - 4]].append(message.photo[-1].file_id)

        # Tugmalarni yaratish
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add('Yana', 'Davom etish')

        # Foydalanuvchiga yuborish
        bot.reply_to(message, f"{steps[state.step][0]} yana yuklashni xohlaysizmi?", reply_markup=markup)

    elif message.text == 'Yana':
        bot.reply_to(message, f"{steps[state.step][0]} suratini yuklang:", reply_markup=types.ReplyKeyboardRemove())

    elif message.text == 'Davom etish':
        if state.step == 8:
            bot.reply_to(message, f"{steps[9][0]}", reply_markup=types.ReplyKeyboardRemove())
            save_user_data(user_id, state)
            del user_states[user_id]
        else:
            state.step = steps[state.step][1]
            bot.reply_to(message, f"{steps[state.step][0]} yuklashni boshlang:")
    else:
        bot.reply_to(message, "Iltimos, 'Yana' yoki 'Davom etish' ni tanlang.")


def save_user_data(user_id, state):
    from django.db import IntegrityError

    try:
        tg_user1, created = TgUser.objects.get_or_create(telegram_id=user_id, username=state.data['username'])
        user = BotUser(
            first_name=state.data['first_name'],
            tg_user=tg_user1,  # Assign the instance here
            last_name=state.data['last_name'],
            phone_number=state.data['phone_number'],
            passport_front_ids=state.data['passport_fronts'],
            passport_back_ids=state.data['passport_backs'],
            front_tex_passport_ids=state.data['front_tex_passports'],
            back_tex_passport_ids=state.data['back_tex_passports'],
            prava_ids=state.data['pravas'],
        )
        user.save()
        logging.info(f"User {user_id} ma'lumotlari saqlandi.")
        send_group_message(user)
    except IntegrityError as e:
        logging.error(f"Error saving user {user_id}: {e}")


def send_group_message(user_data):
    from app.management.commands.bot import bot
    group_id = '-1002323979403'

    # Print the tg_user for debugging

    # Fetch the related TgUser instance
    user = TgUser.objects.get(id=user_data.tg_user.id)  # Assuming tg_user is a foreign key

    # Build the message
    message = (
        f"Ismi: {user_data.first_name}\n"
        f"Familiyasi: {user_data.last_name}\n"
        f"Username: @{user.username}\n"
        f"Telefon raqami: {user_data.phone_number}\n"
    )

    # Prepare media group
    media_group = []
    for category in ['passport_front_ids', 'passport_back_ids', 'front_tex_passport_ids', 'back_tex_passport_ids',
                     'prava_ids']:
        for file_id in getattr(user_data, category, []):
            media_group.append(InputMediaPhoto(file_id))

    # Send media group if available
    msg = None
    if media_group:
        media_group[0].caption = message
        msg = bot.send_media_group(chat_id=group_id, media=media_group)

    # Prepare inline buttons
    markup = types.InlineKeyboardMarkup()
    accept_button = types.InlineKeyboardButton("✅ Qabul qilish", callback_data=f"accept_{user_data.id}")
    reject_button = types.InlineKeyboardButton("❌ Bekor qilish", callback_data=f"reject_{user_data.id}")
    markup.add(accept_button, reject_button)

    # Send message with or without media
    if msg:
        bot.reply_to(msg[0], text='Iltimos, tanlang:', reply_markup=markup)
    else:
        bot.send_message(chat_id=group_id, text=message, reply_markup=markup)


def forward_user_data_to_group(user_data,username, user_id):
    from app.management.commands.bot import bot  # Use consistent group ID
    message = (
        f"Ismi: {user_data.first_name}\n"
        f"Familiyasi: {user_data.last_name}\n"
        f"Username: @{username}\n"
        f"Telefon raqami: {user_data.phone_number}\n"
    )

    # Prepare media group
    media_group = []
    for category in ['passport_front_ids', 'passport_back_ids', 'front_tex_passport_ids', 'back_tex_passport_ids',
                     'prava_ids']:
        for file_id in getattr(user_data, category, []):
            media_group.append(InputMediaPhoto(file_id))

    # Send media group if available
    if media_group:
        media_group[0].caption = message
        bot.send_media_group(chat_id=user_id, media=media_group)

    markup = types.InlineKeyboardMarkup()
    complete_button = types.InlineKeyboardButton("Tugatilgan", callback_data=f"complete_{user_data.id}")
    markup.add(complete_button)

    # Send message with the inline button after media group
    bot.send_message(chat_id=user_id, text='jarayon tugagandan song tugmani bosing', reply_markup=markup)


def process_cancellation_reason(message, user):
    from app.management.commands.bot import bot
    cancellation_reason = message.text

    user.status = 'canceled'
    user.save()

    # Guruhga holatni yangilash haqida xabar
    bot.send_message(message.chat.id, f"❌ {user.first_name} {user.last_name} bekor qilindi!")

    # Bot orqali foydalanuvchiga xabar yuborish
    bot.send_message(user.telegram_id, f"Sizning arizangiz bekor qilindi. Sababi: {cancellation_reason}")


def handle_receipt(message, accepting_admin_chat_id):
    from app.management.commands.bot import bot
    receipt_image = message.photo[-1].file_id if message.photo else None

    markup = types.InlineKeyboardMarkup()
    accept_button = types.InlineKeyboardButton("✅ qabul qilindi", callback_data=f"payAccept_{message.from_user.id}")
    reject_button = types.InlineKeyboardButton("❌ amalga oshmagan", callback_data=f"payReject_{message.from_user.id}")
    markup.add(accept_button, reject_button)

    if receipt_image:
        bot.send_photo(chat_id=accepting_admin_chat_id, photo=receipt_image,
                       caption=f"@{message.from_user.username} foydalanuvchi tomonidan taqdim etilgan to'lov cheki:",
                       reply_markup=markup)
        bot.send_message(chat_id=message.from_user.id, text="Chek jonatildi, iltimos kuting, to'lov tekshirilmoqda.")
    else:
        bot.send_message(chat_id=accepting_admin_chat_id,
                         text="Chek qabul qilinmadi, iltimos, to'g'ri formatda jo'nating.")
