import os
import time
import re
import json


class EngraveAdapter:

    def __init__(self, name, watch_file, log_file, timeout, pause_timeout):

        self.name = name
        self.file = watch_file

        self.timeout = timeout
        self.pause_timeout = pause_timeout

        self.log_file = log_file

        # ---------------- RULES ----------------
        self.rules_config = self._load_rules()
        self.message_rules = self.rules_config["messages"]
        self.markers = self.rules_config["markers"]

        # ---------------- STATE ----------------
        self.state = "IDLE"

        # ---------------- TIMERS ----------------
        self.start_time = None
        self.missing_since = None
        self.pause_since = None

        # ---------------- TRACKING ----------------
        self.last_exists = os.path.exists(self.file)
        self.last_mod = self._get_mod()

        self.current_file = "Невідомо"


    # ---------------- LOAD RULES ----------------
    def _load_rules(self):
        path = os.path.join(os.path.dirname(__file__), "engrave_rules.json")
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)


    # ---------------- FILE MOD ----------------
    def _get_mod(self):
        try:
            return os.path.getmtime(self.file)
        except:
            return None


    # ---------------- FILE NAME ----------------
    def _get_filename(self):

        try:
            with open(self.file, "rb") as f:
                data = f.read()

            text = data.decode("cp1251", errors="ignore")

            matches = re.findall(
                r"[A-Z]:\\[^\"\n\r]+?\.bmp",
                text,
                re.IGNORECASE
            )

            if matches:
                path = matches[-1]
                name = os.path.basename(path)
                return name.rsplit(".", 1)[0].strip()

        except:
            pass

        return "Невідомо"


    # ---------------- TIME FORMAT ----------------
    def _format_time(self, sec):

        h = sec // 3600
        m = (sec % 3600) // 60
        s = sec % 60

        if h == 0:
            return f"{m} хв {s} сек"

        return f"{h} год {m} хв {s} сек"


    # ---------------- UPDATE ----------------
    def update(self):

        now = time.time()
        exists = os.path.exists(self.file)
        mod = self._get_mod()

        event = None

        # =========================
        # 🟩 START
        # =========================
        file_appeared = exists and not self.last_exists
        file_changed = mod is not None and mod != self.last_mod

        if exists and self.state == "IDLE" and (file_appeared or file_changed):

            self.state = "RUNNING"
            self.start_time = now
            self.missing_since = None
            self.pause_since = None

            self.current_file = self._get_filename()

            print(f"{self.name} START")

            event = {
                "type": "START",
                "file": self.current_file
            }

        # =========================
        # 🟩 RUNNING
        # =========================
        if exists:

            self.missing_since = None

            if mod != self.last_mod:
                self.pause_since = None
            else:
                if self.state == "RUNNING" and self.pause_since is None:
                    self.pause_since = now

        # =========================
        # 🟨 PAUSE
        # =========================
        if self.state == "RUNNING" and exists and self.pause_since is not None:

            if now - self.pause_since > self.pause_timeout:

                self.state = "PAUSED"
                self.pause_since = None

                print(f"{self.name} PAUSE")

                event = {
                    "type": "PAUSE",
                    "file": self.current_file
                }

        # =========================
        # 🟦 RESUME
        # =========================
        if self.state == "PAUSED" and exists and mod != self.last_mod:

            self.state = "RUNNING"
            self.pause_since = None

            print(f"{self.name} RESUME")

            event = {
                "type": "RESUME",
                "file": self.current_file
            }

        # =========================
        # 🟥 STOP (FIXED - NO SPAM)
        # =========================
        if not exists:

            if self.state == "IDLE":
                # 🔒 вже зупинено → нічого не робимо
                self.missing_since = None
            else:

                if self.missing_since is None:
                    self.missing_since = now

                if now - self.missing_since > self.timeout:

                    self.state = "IDLE"

                    duration = 0
                    if self.start_time:
                        duration = int(now - self.start_time)

                    print(f"{self.name} STOP")

                    event = {
                        "type": "STOP",
                        "file": self.current_file,
                        "duration": duration
                    }

                    self.start_time = None
                    self.missing_since = None
                    self.pause_since = None

        # =========================
        # TRACK UPDATE
        # =========================
        self.last_exists = exists
        self.last_mod = mod

        return event


    # ---------------- FORMAT MESSAGE ----------------
    def format_message(self, event):

        if not isinstance(event, dict):
            return ""

        t = event["type"]

        if t == "START":
            return (
                f"🟩 {self.name}\n"
                f"Запуск гравіювання\n"
                f"Файл: {event['file']}"
            )

        if t == "PAUSE":
            return (
                f"🟨 {self.name}\n"
                f"Пауза обробки\n"
                f"Файл: {event['file']}"
            )

        if t == "RESUME":
            return (
                f"🟦 {self.name}\n"
                f"Гравіювання продовжено\n"
                f"Файл: {event['file']}"
            )

        if t == "STOP":

            tstr = self._format_time(event.get("duration", 0))

            return (
                f"🟥 {self.name}\n"
                f"Гравіювання завершено\n"
                f"Файл: {event['file']}\n"
                f"Час роботи: {tstr}"
            )

        return ""