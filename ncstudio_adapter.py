import os
import time
import re
import json


class NCStudioAdapter:

    def __init__(self, name, watch_file, log_file, timeout):

        self.name = name
        self.watch_file = watch_file
        self.log_file = log_file
        self.timeout = timeout

        self.last_pos = 0

        # стан
        self.state = "IDLE"
        self.current_file = "Невідомо"
        self.start_time = None
        self.simulation_running = False
        self.simulation_file = "Невідомо"

        self.rules_config = self._load_rules()
        self.markers = self.rules_config["markers"]
        self.message_rules = self.rules_config["messages"]

        # старт з кінця логу
        try:
            if self.log_file and os.path.exists(self.log_file):
                with open(self.log_file, "rb") as f:
                    f.seek(0, os.SEEK_END)
                    self.last_pos = f.tell()
        except:
            self.last_pos = 0

        # ---------------- RULES ----------------
        self.rules = []
        for name, marker in self.markers.items():
            if name in self.rules_config["rules"]:
                self.rules.append({
                    "marker": marker,
                    "rule": self.rules_config["rules"][name]
                })

    # ---------------- LOAD RULES ----------------
    def _load_rules(self):

        path = os.path.join(os.path.dirname(__file__), "ncstudio_rules.json")
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)

    # ---------------- FILE NAME ----------------
    def _extract_filename(self, text):

        matches = re.findall(
            r"[A-Z]:\\[^'\n\r]+?\.NC",
            text,
            re.IGNORECASE
        )

        if matches:
            path = matches[-1]
            name = os.path.basename(path)
            return name.rsplit(".", 1)[0].strip()

        return self.current_file

    # ---------------- CLEAN DATE ----------------
    def _remove_datetime(self, text):

        return re.sub(
            r"^M\s+\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\s*",
            "",
            text
        ).strip()

    # ---------------- MARKER MATCH ----------------
    def _has_marker(self, marker, line):

        if isinstance(marker, list):
            return all(part in line for part in marker)

        return marker in line

    # ---------------- RULE ENGINE ----------------
    def _apply_rule(self, line):

        for item in self.rules:
            key = item["marker"]
            rule = item["rule"]
            if self._has_marker(key, line):
                replace_key = key[0] if isinstance(key, list) else key
                return {
                    "key": key,
                    "text": line.replace(replace_key, rule["text"]),
                    "telegram": rule["telegram"],
                    "console": rule["console"]
                }

        return {
            "key": None,
            "text": line,
            "telegram": True,
            "console": True
        }

    # ---------------- TIME ----------------
    def _format_time(self, sec):

        h = sec // 3600
        m = (sec % 3600) // 60
        s = sec % 60

        if h == 0:
            return f"{m} хв {s} сек"

        return f"{h} год {m} хв {s} сек"

    # ---------------- UPDATE ----------------
    def update(self):

        if not self.log_file or not os.path.exists(self.log_file):
            return None

        events = []

        try:
            with open(self.log_file, "rb") as f:

                f.seek(self.last_pos)
                data = f.read()
                self.last_pos = f.tell()

                try:
                    text = data.decode("cp1251")
                except:
                    try:
                        text = data.decode("gbk")
                    except:
                        text = data.decode("utf-8", errors="ignore")

                lines = text.splitlines()

                for raw in lines:

                    line = self._remove_datetime(raw)

                    if not line:
                        continue

                    rule = self._apply_rule(line)

                    # ---------------- START ----------------
                    if self._has_marker(self.markers["machining_start"], line):

                        file_name = self._extract_filename(line)

                        self.current_file = file_name
                        self.start_time = time.time()
                        self.state = "RUNNING"
                        self.simulation_running = False
                        self.simulation_file = "Невідомо"

                        if rule["console"]:
                            print(f"{self.name} START")

                        if rule["telegram"]:
                            events.append({
                                "type": "START",
                                "file": file_name
                            })

                        continue

                    # ---------------- SIMULATION START ----------------
                    if self._has_marker(self.markers["simulation_start"], line):

                        file_name = self._extract_filename(line)

                        self.simulation_running = True
                        self.simulation_file = file_name

                        if rule["console"]:
                            print(f"{self.name} SIMULATION START")

                        if rule["telegram"]:
                            events.append({
                                "type": "SIMULATION_START",
                                "file": file_name
                            })

                        continue

                    # ---------------- STOP NORMAL ----------------
                    if self._has_marker(self.markers["stop"], line):

                        file_name = self._extract_filename(line)

                        if self.simulation_running and self.state != "RUNNING":
                            self.simulation_running = False
                            self.simulation_file = file_name

                            if rule["console"]:
                                print(f"{self.name} SIMULATION STOP")

                            events.append({
                                "type": "SIMULATION_STOP",
                                "file": self.simulation_file
                            })

                            continue

                        self.current_file = file_name

                        duration = 0
                        if self.start_time:
                            duration = int(time.time() - self.start_time)

                        self.state = "IDLE"

                        if rule["console"]:
                            print(f"{self.name} STOP")

                        events.append({
                            "type": "STOP",
                            "file": self.current_file,
                            "duration": duration
                        })

                        continue

                    # ---------------- STOP MANUAL ----------------
                    if self._has_marker(self.markers["manual_stop"], line):

                        file_name = self._extract_filename(line)
                        self.current_file = file_name

                        duration = 0
                        if self.start_time:
                            duration = int(time.time() - self.start_time)

                        self.state = "IDLE"

                        if rule["console"]:
                            print(f"{self.name} STOP MANUAL")

                        events.append({
                            "type": "STOP_MANUAL",
                            "file": self.current_file,
                            "duration": duration
                        })

                        continue

                    # ---------------- INFO ----------------
                    if rule["console"]:
                        print(f"{self.name} {rule['text']}")

                    if rule["telegram"]:
                        events.append({
                            "type": "INFO",
                            "msg": rule["text"]
                        })

        except Exception as e:
            print("NC adapter error:", e)
            return None

        return events if events else None

    # ---------------- FORMAT ----------------
    def format_message(self, event):

        t = event.get("type")
        rule = self.message_rules.get(t)

        if t == "INFO" and rule:
            return (
                f"{rule.get('icon', '⚪')} {self.name}\n"
                f"{event.get('msg')}"
            )

        if not rule:
            return ""

        lines = [
            f"{rule.get('icon', '')} {self.name}".strip(),
            rule.get("text", "")
        ]

        if rule.get("include_file"):
            lines.append(f"Файл: {event['file']}")

        if rule.get("include_duration"):
            time_str = self._format_time(event.get("duration", 0))
            lines.append(f"Час роботи: {time_str}")

        return "\n".join(lines)
