import time
import requests
import importlib
import os

from config import MACHINES, TOKEN, CHAT_ID


# =========================
# LOG FILE
# =========================

LOG_FILE = os.path.join(os.path.dirname(__file__), "monitor.log")
LOG_MAX_SIZE = 5 * 1024 * 1024  # 5 MB


def write_log(text):

    try:

        # ---------------- ROTATE ----------------
        if os.path.exists(LOG_FILE):

            size = os.path.getsize(LOG_FILE)

            if size > LOG_MAX_SIZE:

                timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")

                old_log = os.path.join(
                    os.path.dirname(LOG_FILE),
                    f"monitor.log.{timestamp}"
                )

                os.rename(LOG_FILE, old_log)

        # ---------------- WRITE ----------------
        with open(LOG_FILE, "a", encoding="utf-8") as f:

            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

            f.write(f"[{timestamp}] {text}\n")

    except Exception as e:
        print("[ERR] LOG:", e)


# =========================
# PRINT + LOG
# =========================

def log_print(*args):

    text = " ".join(str(a) for a in args)

    print(text)
    write_log(text)


# =========================
# TELEGRAM
# =========================

def send(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={
                "chat_id": CHAT_ID,
                "text": msg
            },
            timeout=5
        )
    except Exception as e:
        log_print("[TELEGRAM ERROR]", e)


# =========================
# ADAPTER FACTORY
# =========================

def create_adapter(m):

    t = m["TYPE"]

    if t == "NCSTUDIO":
        mod = importlib.import_module("ncstudio_adapter")
        return mod.NCStudioAdapter(
            m["NAME"],
            m["WATCH_FILE"],
            m.get("LOG_FILE"),
            m["IDLE_TIMEOUT"]
        )

    if t == "ENGRAVE":
        mod = importlib.import_module("engrave_adapter")
        return mod.EngraveAdapter(
            m["NAME"],
            m["WATCH_FILE"],
            m.get("LOG_FILE"),
            m["IDLE_TIMEOUT"],
            m.get("PAUSE_TIMEOUT", m["IDLE_TIMEOUT"])
        )

    raise Exception("Unknown TYPE: " + str(t))


# =========================
# INIT
# =========================

monitors = []

for m in MACHINES:
    try:
        mon = create_adapter(m)
        monitors.append(mon)
        log_print("[OK] Підключено:", m["NAME"])
    except Exception as e:
        log_print("[ERR] INIT:", m.get("NAME"), e)

log_print("CNC MONITOR запущено...")


# =========================
# MAIN LOOP
# =========================

while True:

    for mon in monitors:

        try:
            events = mon.update()

            if not events:
                continue

            if not isinstance(events, list):
                events = [events]

            for event in events:

                msg = mon.format_message(event)

                if not msg:
                    continue

                # ---------------- ROUTING ----------------
                rule = mon.message_rules.get(event.get("type"), {})

                to_console = rule.get("console", True)
                to_telegram = rule.get("telegram", True)

                if to_console:
                    log_print(msg)

                if to_telegram:
                    send(msg)

        except Exception as e:
            log_print("[ERR] runtime:", e)

    time.sleep(1)