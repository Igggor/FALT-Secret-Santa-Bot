import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from . import storage
from botapp.config import DISTRIBUTION_DATETIME as distribution_datetime

logger = logging.getLogger(__name__)

# Conversation states
SURNAME_NAME, GROUP, ROOM, WISHES = range(4)


async def message_logger(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        text = None
        if update.message and update.message.text:
            text = update.message.text
        elif update.edited_message and update.edited_message.text:
            text = update.edited_message.text
        else:
            # Логируем тип сообщения (sticker/photo/etc.)
            text = f"<non-text message: {type(update.message).__name__ if update.message else 'unknown'}>"
        logging.info(f"Received message from {getattr(user, 'id', 'unknown')}: {text}")
    except Exception:
        logging.exception("Error in message_logger")


async def callback_fallback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        cq = update.callback_query
        if not cq:
            return
        data = cq.data
        logging.info(f"Unhandled CallbackQuery reached fallback: {data}")
        try:
            await cq.answer(text="Кнопка нажата (fallback)")
        except Exception:
            # старые версии могут не принимать text — безопасно молча ответить
            try:
                await cq.answer()
            except Exception:
                pass
        try:
            if cq.message:
                await cq.message.reply_text(f"Нажата кнопка: {data}")
        except Exception:
            pass
    except Exception:
        logging.exception("Error in callback_fallback")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Защита: если вызов не содержит message (например, inline), просто проигнорировать
    if not update.message:
        return ConversationHandler.END

    user = update.effective_user
    users = storage.load_users()
    uid = str(user.id)
    
    logger.info(f"Пользователь {user.id} (@{user.username}) вызвал команду /start")
    
    if uid in users:
        msg = (
            "Вы уже зарегистрированы на Тайного Санту.\n"
            "Заглушка: здесь будет информация для зарегистрированных участников.\n"
            "(Вы можете изменить этот текст позже)"
        )
        await update.message.reply_text(msg)
        logger.info(f"Пользователь {user.id} уже зарегистрирован, показано сообщение для зарегистрированных")
        return ConversationHandler.END

    await update.message.reply_text(
        "Добро пожаловать! Чтобы зарегистрироваться на Тайного Санту, пожалуйста укажите Фамилию и Имя."
    )
    logger.info(f"Начата регистрация для пользователя {user.id}")
    return SURNAME_NAME


async def surname_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        # если нет текста — спросить снова
        await update.effective_message.reply_text("Пожалуйста, введите Фамилию и Имя.")
        return SURNAME_NAME

    user = update.effective_user
    text = update.message.text.strip()
    context.user_data["full_name"] = text
    
    logger.info(f"Пользователь {user.id} указал ФИО: {text}")
    
    await update.message.reply_text("Введите номер вашей группы (введите вручную):")
    return GROUP


async def group_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        await update.effective_message.reply_text("Пожалуйста, номер вашей группы.")
        return GROUP

    user = update.effective_user
    group = update.message.text.strip()
    context.user_data["group"] = group
    
    logger.info(f"Пользователь {user.id} указал группу: {group}")
    
    await update.message.reply_text("Укажите комнату, в которой вы живете в общежитии:")
    return ROOM


async def room_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        await update.effective_message.reply_text("Пожалуйста, укажите номер вашей комнаты.")
        return ROOM

    user = update.effective_user
    room = update.message.text.strip()
    context.user_data["room"] = room
    
    logger.info(f"Пользователь {user.id} указал комнату: {room}")
    
    await update.message.reply_text(
        "Укажите пожелания к подарку для Вас:"
    )
    return WISHES


async def wishes_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Может быть не текст (стикер/фото) — защититься
    text = ""
    if update.message and update.message.text:
        text = update.message.text
    wishes = text.strip()
    context.user_data["wishes"] = wishes

    user = update.effective_user
    logger.info(f"Пользователь {getattr(user, 'id', 'unknown')} указал пожелания: {wishes if wishes else '(пусто)'}")

    uid = str(user.id) if user else None
    if not uid:
        logging.warning("Не удалось определить user.id при завершении регистрации.")
        await update.effective_message.reply_text("Ошибка регистрации — повторите позже.")
        return ConversationHandler.END

    users = storage.load_users()
    user_data = {
        "tg_id": int(user.id) if user else None,
        "username": user.username if user else None,
        "first_name": user.first_name if user else None,
        "last_name": user.last_name if user else None,
        "full_name": context.user_data.get("full_name"),
        "group": context.user_data.get("group"),
        "room": context.user_data.get("room"),
        "wishes": context.user_data.get("wishes"),
        "registered_at": datetime.utcnow().isoformat(),
    }
    users[uid] = user_data
    storage.save_users(users)

    logger.info(
        f"Пользователь {user.id} (@{user.username}) успешно зарегистрирован. "
        f"Данные: ФИО={user_data['full_name']}, Группа={user_data['group']}, "
        f"Комната={user_data['room']}, Пожелания={user_data['wishes'] or 'нет'}"
    )

    

    dt = datetime.strptime(distribution_datetime, "%Y-%m-%d %H:%M")

    months = {
        1: "января",
        2: "февраля",
        3: "марта",
        4: "апреля",
        5: "мая",
        6: "июня",
        7: "июля",
        8: "августа",
        9: "сентября",
        10: "октября",
        11: "ноября",
        12: "декабря"
    }

    formatted = f"{dt.day} {months[dt.month]} {dt.year}"

    await update.message.reply_text(
        "Вы успешно зарегистрированы на участие в Тайном Санте ФАЛТа.\n"
        f"Распределение произойдет {formatted}.\n\n"
        "Если у Вас появятся вопросы, свяжитесь с организаторами @org_id."
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Защита на случай отсутствия message
    if update.message:
        user = update.effective_user
        logger.info(f"Пользователь {getattr(user, 'id', 'unknown')} отменил регистрацию")
        await update.message.reply_text("Регистрация отменена.")
    return ConversationHandler.END
