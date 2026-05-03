from dotenv import load_dotenv
import os

# =========================
# LOAD ENV
# =========================

env_path = os.path.join(os.path.dirname(__file__), "secrets.env")
load_dotenv(env_path, override=True)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


# =========================
# SAFETY CHECK (ВАЖЛИВО)
# =========================

if not TOKEN:
    raise Exception("TELEGRAM_TOKEN is missing or env file is broken")

if not CHAT_ID:
    raise Exception("TELEGRAM_CHAT_ID is missing or env file is broken")


# =========================
# MACHINES CONFIG
# =========================

MACHINES = [
    {
        "NAME": "NC STUDIO",
        "TYPE": "NCSTUDIO",
        "WATCH_FILE": r"D:\TEMP D\!Portable\NcStudio 5.5.60 simulation\NCSTUDIO.DYN",
        "LOG_FILE": r"D:\TEMP D\!Portable\NcStudio 5.5.60 simulation\NCSTUDIO.LOG",
        "IDLE_TIMEOUT": 15
    },

    {
       "NAME": "ENGRAVE 80E",
       "TYPE": "ENGRAVE",
       "WATCH_FILE": "C:\\Engrave80e\\ws080e1.grv",
       "IDLE_TIMEOUT": 20,
       "PAUSE_TIMEOUT": 10
    }
]


# =========================
# SYSTEM SETTINGS
# =========================

POLL_INTERVAL = 0.5
TELEGRAM_RETRY_DELAY = 2
TELEGRAM_MAX_RETRIES = 3

DEBUG_MODE = True
SHOW_RAW_LOGS = False