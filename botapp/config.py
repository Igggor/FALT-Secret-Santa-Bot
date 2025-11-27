import os
from dotenv import load_dotenv

load_dotenv()

# Token and scheduling config
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
DISTRIBUTION_DATETIME = os.getenv("DISTRIBUTION_DATETIME")

# Admins (comma-separated list of numeric Telegram IDs)
raw_admins = os.getenv("ADMIN_IDS")
if raw_admins:
    try:
        ADMIN_IDS = {int(x.strip()) for x in raw_admins.split(",") if x.strip()}
    except Exception:
        ADMIN_IDS = set()
else:
    ADMIN_IDS = set()

# Data directory (project-level `data` folder)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

# Logging
LOG_FILE = os.path.join(PROJECT_ROOT, "log.txt")

# Sending / rate-limit settings
# Delay between individual send_message calls (seconds). Increase to be safer.
SEND_DELAY = float(os.getenv("SEND_DELAY", "0.5"))
# Max retries when transient error occurs
MAX_SEND_RETRIES = int(os.getenv("MAX_SEND_RETRIES", "3"))
# Backoff multiplier for retries
RETRY_BACKOFF = float(os.getenv("RETRY_BACKOFF", "2.0"))

# Queue send delays (random between min and max seconds)
QUEUE_MIN_DELAY = int(os.getenv("QUEUE_MIN_DELAY", "20"))
QUEUE_MAX_DELAY = int(os.getenv("QUEUE_MAX_DELAY", "40"))
