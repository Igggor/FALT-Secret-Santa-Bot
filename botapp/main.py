import logging
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
    ConversationHandler
)

from . import handlers, admin, scheduler, config


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[
        logging.FileHandler(config.LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


logger = logging.getLogger(__name__)


def main():
    token = config.TELEGRAM_TOKEN
    if not token:
        print("TELEGRAM_TOKEN Not found in environment variables. Please set it and restart the bot.")
        return

    app = ApplicationBuilder().token(token).build()

    async def error_handler(update, context):
        logging.exception("Unhandled exception:")

    app.add_error_handler(error_handler)

    # Conversation handler (регистрация)
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", handlers.start)],
        states={
            handlers.SURNAME_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.surname_name)
            ],
            handlers.GROUP: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.group_handler)
            ],
            handlers.ROOM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.room_handler)
            ],
            handlers.WISHES: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.wishes_handler)
            ],
        },
        fallbacks=[CommandHandler("cancel", handlers.cancel)],
    )

    app.add_handler(conv_handler)

    # Команда ручного распределения
    app.add_handler(CommandHandler("distribute_now", admin.distribute_command))

    app.add_handler(CommandHandler("help", handlers.help))

    # Логгер всех сообщений (не мешает работе ConversationHandler, т.к. group=1)
    app.add_handler(MessageHandler(filters.ALL, handlers.message_logger), group=1)

    # Fallback для незарегистрированных callback-кнопок
    app.add_handler(CallbackQueryHandler(handlers.callback_fallback), group=1)

    # Планировщик автоматического распределения
    scheduler.schedule_distribution(app)

    logger.info("Бот запущен botapp/main.py")
    print("Бот запущен. Нажмите Ctrl-C для остановки.")
    app.run_polling()
