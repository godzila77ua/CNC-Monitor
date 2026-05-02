import time
import json
import requests
import importlib
import sys


try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass


with open("config.json", "r", encoding="utf-8-sig") as f:
    cfg = json.load(f)

TOKEN = cfg["TOKEN"]
CHAT_ID = cfg["CHAT_ID"]
machines = cfg["MACHINES"]


def send(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg},
            timeout=5
        )
    except:
        pass


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

    raise Exception("Unknown TYPE")


monitors = []

for m in machines:
    try:
        mon = create_adapter(m)
        monitors.append(mon)
        print("[OK] Підключено:", m["NAME"])
    except Exception as e:
        print("[ERR] INIT:", m.get("NAME"), e)

print("CNC MONITOR запущено...")


while True:

    for mon in monitors:

        try:
            e = mon.update()

            if not e:
                continue

            if isinstance(e, list):

                for item in e:
                    msg = mon.format_message(item)
                    if msg:
                        print(msg)
                        send(msg)

            else:

                msg = mon.format_message(e)
                if msg:
                    print(msg)
                    send(msg)

        except Exception as e:
            print("[ERR] runtime:", e)

    time.sleep(1)