import logging

from telebot import types

from app.management.commands.function import handle_image_upload, forward_user_data_to_group, \
    process_cancellation_reason, save_user_data, handle_receipt
from app.management.commands.payment_info import *
from app.models import BotUser, TgUser

logging.basicConfig(level=logging.INFO)


def register_handlers(bot):
    from app.management.commands.shared import user_states
    @bot.message_handler(commands=['get_group_id'])
    def get_group_id(message):
        group_id = message.chat.id
        bot.reply_to(message, f"Guruh ID: {group_id}")

    @bot.message_handler(commands=['start'])
    def handle_start(message):
        user_id = message.from_user.id
        user_states[user_id] = UserState()
        # Welcome message with bot functionalities
        welcome_message = (
            "👋 Salom!\n"
            "Bu bot sizga avtomobilingizni online sug'urtalashda yordam beradi.\n\n"
            "Iltimos, ism Familyangzni kiriting:"
        )

        bot.reply_to(message, welcome_message, parse_mode='Markdown', reply_markup=types.ReplyKeyboardRemove())
        user_states[user_id].step = 1

    @bot.message_handler(func=lambda message: True, content_types=['text', 'photo'])
    def handle_response(message):
        user_id = message.from_user.id
        state = user_states.get(user_id)

        if not state:
            bot.reply_to(message, "Iltimos, /start bilan boshlang.", reply_markup=types.ReplyKeyboardRemove())
            return

        if state.step == 1:
            if isinstance(message.text, str) and message.text.strip():  # Check if the message is a non-empty string
                full_name = message.text.split()
                state.data['first_name'] = full_name[0]
                state.data['last_name'] = full_name[1] if len(full_name) > 1 else ''  # Check for last name
                state.data['username'] = message.from_user.username or ''
                # reply_markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
                # reply_markup.add(types.KeyboardButton(text='Share my phone number', request_contact=True))

                bot.send_message(user_id, "Iltimos, telefon raqamingizni kiriting:",
                                 reply_markup=types.ReplyKeyboardRemove())
                state.step = 3

            else:
                bot.reply_to(message, "Iltimos, matn shaklida yozing.", reply_markup=types.ReplyKeyboardRemove())

        elif state.step == 3:
            if message.contact:
                bot.reply_to(message, message)
                state.data['phone_number'] = message.contact.phone_number
                state.step = 4
                bot.reply_to(message, "Pasportning old qismining suratini yuklang:")
            if  message.text.isdigit() and message.text.strip():
                state.data['phone_number'] = message.text
                state.step = 4
                bot.reply_to(message, "Pasportning old qismining suratini yuklang:")
            else:
                bot.reply_to(message, "Iltimos, to'g'ri shaklda yozing.", reply_markup=types.ReplyKeyboardRemove())
                state.step = 3


        elif state.step in [4, 5, 6, 7, 8]:
            handle_image_upload(message, state)

        elif state.step == 9:
            bot.reply_to(message, "Rahmat! Ma'lumotlaringiz saqlanmoqda.", reply_markup=types.ReplyKeyboardRemove())
            save_user_data(user_id, state)
            del user_states[user_id]

    @bot.callback_query_handler(func=lambda call: call.data.startswith('complete_'))
    def handle_complete_callback(call):
        user_id = int(call.data.split('_')[1])
        user = BotUser.objects.get(id=user_id)
        user_tg = TgUser.objects.get(id=user_id)

        user.status = 'finished'
        user.save()

        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text=f"🔔 {user.first_name} {user.last_name} tugatildi!", )

        # Bot orqali foydalanuvchiga xabar yuborish
        bot.send_message(chat_id=user_tg.telegram_id, text="Tabriklarymiz Sizning jarayoningiz tugatildi!",
                         reply_markup=types.ReplyKeyboardRemove())



    @bot.callback_query_handler(func=lambda call: call.data.startswith('accept_') or call.data.startswith('reject_'))
    def handle_callback(call: types.CallbackQuery):
        user_id = int(call.data.split('_')[1])
        user = BotUser.objects.get(id=user_id)

        accepting_admin_chat_id = call.from_user.id
        if call.data.startswith('accept_'):
            user.status = 'accepted'
            user.save()

            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text=f"✅ {user.first_name} {user.last_name} qabul qilindi!")

            bot.send_message(chat_id=user.tg_user.telegram_id,
                             text=f"Tabriklaymiz, arizangiz qabul qilindi!\n\n"
                                  f"To'lov uchun quyidagi ma'lumotlar:\n"
                                  f"Karta raqami: {card_number}\n"
                                  f"Karta egasi: {card_holder_name} {card_holder_surname}\n"
                                  f"Summa: {amount} so'm.\n"
                                  f"Iltimos, to'lovni amalga oshirgandan so'ng, chekni yuboring!",
                             reply_markup=types.ReplyKeyboardRemove())

            msg = bot.send_message(chat_id=user.tg_user.telegram_id, text="Iltimos, to'lov chekingizni yuboring.")
            bot.register_next_step_handler(msg, handle_receipt, accepting_admin_chat_id)


        elif call.data.startswith('reject_'):
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text="Iltimos, bekor qilish sababini yozing:")
            bot.register_next_step_handler(call.message, process_cancellation_reason, user)

    #     ///////////////////
    @bot.callback_query_handler(
        func=lambda call: call.data.startswith('payReject_') or call.data.startswith('payAccept_'))
    def handle_callback(call: types.CallbackQuery):
        user_id = int(call.data.split('_')[1])
        accepting_admin_chat_id = call.from_user.id

        if call.message:
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                          reply_markup=None)


            if call.data.startswith('payAccept_'):
                bot.send_message(chat_id=call.message.chat.id, text='Tolov tasdiqlandi ✅', reply_markup=None)
                print(user_id)

                tg_id = TgUser.objects.get(telegram_id=user_id)
                user = BotUser.objects.filter(tg_user=tg_id.id).first()

                if user:

                    forward_user_data_to_group(user, tg_id.username, accepting_admin_chat_id)
                    bot.send_message(chat_id=user_id,
                                     text="Tabriklaymiz\nSizning to'lovingiz tasdiqlandi. ✅\nTez orada sug'urta jarayonidan o'tasiz.")
                else:
                    bot.send_message(chat_id=accepting_admin_chat_id, text="Xato: Foydalanuvchi topilmadi.")

            # Agar to'lov rad etilgan bo'lsa
            elif call.data.startswith('payReject_'):
                bot.send_message(chat_id=call.message.chat.id, text="❌ To'lov qabul qilinmagan", reply_markup=None)
                bot.send_message(chat_id=user_id, text="Sizning to'lovingiz tasdiqlanmadi. Qayta urinib ko'ring!")




class UserState:
    def __init__(self):
        self.step = 0
        self.data = {
            'first_name': None,
            'last_name': None,
            'username': None,
            'phone_number': None,
            'passport_fronts': [],
            'passport_backs': [],
            'front_tex_passports': [],
            'back_tex_passports': [],
            'pravas': []
        }
