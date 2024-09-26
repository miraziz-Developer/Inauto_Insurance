# main.py
import logging

import telebot
from django.core.management.base import BaseCommand

from app.management.commands.config import API_TOKEN
from app.management.commands.handlers import register_handlers

logging.basicConfig(level=logging.INFO)

bot = telebot.TeleBot(API_TOKEN)


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        # Register the handlers
        register_handlers(bot)

        # Start polling
        bot.polling(none_stop=True)


if __name__ == '__main__':
    # Register the handlers
    register_handlers(bot)

    # Run the bot
    bot.polling(none_stop=True)
