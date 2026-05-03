import time
import requests
import importlib

from config import MACHINES, TOKEN, CHAT_ID


# ---------------- TELEGRAM ----------------
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
        print("[TELEGRAM ERROR]", e)


# ---------------- ADAPTER FACTORY ----------------
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
            m["IDLE_TIMEOUT"]
        )

    raise Exception("Unknown TYPE: " + str(t))


# ---------------- INIT ----------------
monitors = []

for m in MACHINES:
    try:
        mon = create_adapter(m)
        monitors.append(mon)
        print("[OK] Підключено:", m["NAME"])
    except Exception as e:
        print("[ERR] INIT:", m.get("NAME"), e)

print("CNC MONITOR запущено...")


# ---------------- MAIN LOOP ----------------
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

                if msg:
                    print(msg)
                    send(msg)

        except Exception as e:
            print("[ERR] runtime:", e)

    time.sleep(1)