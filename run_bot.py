from telegram.ext import (
    Filters,
    MessageHandler,
    Updater,
)
import os, django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bot_conf.settings')
django.setup()

from telegram_django_bot.tg_dj_bot import TG_DJ_Bot
from telegram_django_bot.routing import RouterCallbackMessageCommandHandler

from bot_conf.settings import TELEGRAM_TOKEN, TELEGRAM_LOG, DEBUG
import logging

from base.views import create_file_from_message


def add_handlers(updater):
    dp = updater.dispatcher
    dp.add_handler(RouterCallbackMessageCommandHandler())
    dp.add_handler(MessageHandler(Filters.all, create_file_from_message))


def main():
    if not DEBUG:
        logging.basicConfig(
            filename=TELEGRAM_LOG,
            filemode='a',
            format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
            datefmt='%Y.%m.%d %H:%M:%S',
            level=logging.INFO
        )

    updater = Updater(bot=TG_DJ_Bot(TELEGRAM_TOKEN), workers=8)
    add_handlers(updater)
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()

