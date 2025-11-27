import logging
import random
import asyncio
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import RetryAfter, Forbidden, BadRequest, TimedOut
from . import storage, config

logger = logging.getLogger(__name__)


async def distribute(context: ContextTypes.DEFAULT_TYPE):
    """
    Выполняет распределение тайного санты и рассылает сообщения.
    Вызывается job_queue или вручную через distribute_command.
    """
    app = context.application
    users = storage.load_users()
    ids = list(users.keys())
    if len(ids) < 2:
        logger.info("Недостаточно участников для распределения.")
        return {}

    giver_ids = ids[:]
    recipient_ids = giver_ids[:]

    # Попытка случайного распределения без совпадений свои→свои
    success = False
    for _ in range(1000):
        random.shuffle(recipient_ids)
        if all(giver_ids[i] != recipient_ids[i] for i in range(len(giver_ids))):
            success = True
            break

    # Если 1000 попыток не помогли — циклический сдвиг (гарантированный вариант)
    if not success:
        recipient_ids = giver_ids[1:] + giver_ids[:1]

    assignments = {g: r for g, r in zip(giver_ids, recipient_ids)}
    storage.save_assignments(assignments)

    # Обновить users.json (очистить старые и записать новые назначения)
    try:
        users = storage.load_users()
        now_iso = datetime.utcnow().isoformat()

        for uid in list(users.keys()):
            users[uid].pop("assigned", None)

        for giver, recv in assignments.items():
            if giver in users and recv in users:
                receiver = users[recv]
                users[giver]["assigned"] = {
                    "tg_id": int(recv),
                    "username": receiver.get("username"),
                    "full_name": receiver.get("full_name")
                    or f"{receiver.get('first_name','')} {receiver.get('last_name','')}",
                    "group": receiver.get("group"),
                    "room": receiver.get("room"),
                    "wishes": receiver.get("wishes"),
                    "assigned_at": now_iso,
                }
        storage.save_users(users)
    except Exception:
        logger.exception("Ошибка при обновлении users.json с назначениями:")

    # Рассылка уведомлений
    for giver, recv in assignments.items():
        receiver = users.get(recv)
        if not receiver:
            logger.warning("Receiver %s not found for giver %s", recv, giver)
            continue

        text = (
            "Вам назначено дарить подарок: {name}\n"
            "Телеграм: @{username} (id: {tid})\n"
            "Группа: {group}\n"
            "Комната: {room}\n"
            "Пожелания: {wishes}"
        ).format(
            name=receiver.get("full_name") or
                 f"{receiver.get('first_name', '')} {receiver.get('last_name', '')}",
            username=receiver.get("username") or "-",
            tid=receiver.get("tg_id"),
            group=receiver.get("group") or "-",
            room=receiver.get("room") or "-",
            wishes=receiver.get("wishes") or "не указаны",
        )

        attempt = 0
        delay = config.SEND_DELAY

        while attempt <= config.MAX_SEND_RETRIES:
            try:
                await app.bot.send_message(chat_id=int(giver), text=text)
                break

            except RetryAfter as e:
                wait = int(getattr(e, "retry_after", 1))
                logger.warning("RetryAfter for %s: sleeping %s seconds", giver, wait)
                await asyncio.sleep(wait)
                attempt += 1
                delay *= config.RETRY_BACKOFF

            except Forbidden:
                logger.info("Cannot send to %s: Forbidden (bot blocked?)", giver)
                break

            except (TimedOut, BadRequest) as e:
                logger.warning("Temporary error sending to %s: %s (attempt %s)", giver, e, attempt)
                attempt += 1
                await asyncio.sleep(delay)
                delay *= config.RETRY_BACKOFF

            except Exception:
                logger.exception("Unexpected error sending to %s:", giver)
                attempt += 1
                await asyncio.sleep(delay)
                delay *= config.RETRY_BACKOFF

    return assignments


async def distribute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обёртка для запуска распределения вручную через команду /distribute_now
    (так как distribute(context) принимает только один аргумент).
    """
    await distribute(context)
    await update.message.reply_text("Распределение выполнено вручную.")
