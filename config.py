from dotenv import load_dotenv
import os

# =========================
# LOAD ENV
# =========================

env_path = os.path.join(os.path.dirname(__file__), "secrets.env")
load_dotenv(env_path, override=True)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TOKEN:
    raise Exception("TELEGRAM_TOKEN is missing or env file is broken")

if not CHAT_ID:
    raise Exception("TELEGRAM_CHAT_ID is missing or env file is broken")


# =========================
# ACTIVE MACHINES (ONLY ONE LIST)
# =========================

MACHINE_KEYS = os.getenv("MACHINES", "")
MACHINE_KEYS = [x.strip() for x in MACHINE_KEYS.split(",") if x.strip()]


# =========================
# MACHINE BUILDER
# =========================

def build_machine(prefix):

    mtype = os.getenv(f"{prefix}_TYPE")
    name = os.getenv(f"{prefix}_NAME")
    watch = os.getenv(f"{prefix}_WATCH")
    log = os.getenv(f"{prefix}_LOG")

    if not mtype:
        print(f"[ERROR] {prefix}_TYPE не заданий")
        return None

    if not name or not watch:
        print(f"[ERROR] {prefix} має неповний конфіг")
        return None

    if mtype == "ENGRAVE":
       return {
           "NAME": name,
           "TYPE": mtype,
           "WATCH_FILE": watch,
           "IDLE_TIMEOUT": int(os.getenv(f"{prefix}_IDLE_TIMEOUT", 10)),
           "PAUSE_TIMEOUT": int(os.getenv(f"{prefix}_PAUSE_TIMEOUT", 5))
        }

    if mtype == "NCSTUDIO":
        if not log:
            print(f"[ERROR] {prefix}_LOG не заданий")
            return None

        return {
            "NAME": name,
            "TYPE": mtype,
            "WATCH_FILE": watch,
            "LOG_FILE": log,
            "IDLE_TIMEOUT": int(os.getenv(f"{prefix}_IDLE_TIMEOUT", 15))
        }

    print(f"[ERROR] Невідомий тип {mtype} для {prefix}")
    return None


# =========================
# FINAL MACHINES LIST
# =========================

MACHINES = []

for key in MACHINE_KEYS:
    m = build_machine(key)
    if m:
        MACHINES.append(m)

if not MACHINES:
    print("[WARNING] Немає жодної активної машини!")


# =========================
# SYSTEM SETTINGS
# =========================

POLL_INTERVAL = float(os.getenv("CNC_POLL_INTERVAL", 1))
TELEGRAM_RETRY_DELAY = int(os.getenv("CNC_TELEGRAM_RETRY_DELAY", 2))
TELEGRAM_MAX_RETRIES = int(os.getenv("CNC_TELEGRAM_MAX_RETRIES", 3))

DEBUG_MODE = os.getenv("CNC_DEBUG_MODE", "true").lower() == "true"