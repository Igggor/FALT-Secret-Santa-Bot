from datetime import datetime
from . import config


def schedule_distribution(app):
    raw = config.DISTRIBUTION_DATETIME
    if not raw:
        print("Переменная окружения DISTRIBUTION_DATETIME не установлена. Распределение не запланировано.")
        return
    try:
        try:
            run_dt = datetime.fromisoformat(raw)
        except Exception:
            # Поддержка формата "YYYY-MM-DD HH:MM"
            from datetime import datetime as _dt
            run_dt = _dt.strptime(raw, "%Y-%m-%d %H:%M")
    except Exception as e:
        print(f"Не удалось распарсить DISTRIBUTION_DATETIME: {e}")
        return

    now = datetime.now()
    delay = (run_dt - now).total_seconds()
    if delay <= 0:
        # выполнить с небольшой задержкой, чтобы бот успел полностью стартануть
        async def immediate_job(context):
            from .admin import distribute
            await distribute(context)

        # when=1 чтобы не запускать немедленно в момент старта (практичнее)
        app.job_queue.run_once(immediate_job, when=1)
        print(f"Распределение выполнено (запрошено на {run_dt.isoformat()}).")
        return

    async def job_callback(context):
        from .admin import distribute
        await distribute(context)

    app.job_queue.run_once(job_callback, when=delay)
    print(f"Распределение запланировано на {run_dt.isoformat()} (через {int(delay)} секунд)")
