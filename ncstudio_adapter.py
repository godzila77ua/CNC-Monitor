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

        self.state = "IDLE"
        self.current_file = "Невідомо"
        self.start_time = None

        self.simulation_running = False
        self.simulation_file = "Невідомо"

        self.rules_config = self._load_rules()
        self.markers = self.rules_config["markers"]
        self.message_rules = self.rules_config["messages"]

        try:
            if self.log_file and os.path.exists(self.log_file):
                with open(self.log_file, "rb") as f:
                    f.seek(0, os.SEEK_END)
                    self.last_pos = f.tell()
        except:
            self.last_pos = 0

        self.SKIP_PATTERNS = [
            "CPU ticks",
            "INTERRUPTLOSS"
        ]

    # ---------------- LOAD RULES ----------------
    def _load_rules(self):
        path = os.path.join(os.path.dirname(__file__), "ncstudio_rules.json")
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)

    # ---------------- CLEAN ----------------
    def _remove_datetime(self, text):
        return re.sub(
            r"^[A-Z]\s+\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\s*",
            "",
            text
        ).strip()

    # ---------------- MARKER ----------------
    def _has_marker(self, marker, line):

        line = re.sub(r"\s+", " ", line).strip().lower()

        if isinstance(marker, list):
            return all(m.strip().lower() in line for m in marker)

        return marker.strip().lower() in line

    # ---------------- FILE NAME ----------------
    def _extract_filename(self, text):

        matches = re.findall(r"[A-Z]:\\[^'\n\r]+?\.NC", text, re.IGNORECASE)

        if matches:
            path = matches[-1]
            return os.path.basename(path).rsplit(".", 1)[0].strip()

        return self.current_file

    # ---------------- L RANGE ----------------
    def _parse_l_range(self, text):

        match = re.search(
            r"from\s+(L\d+)\s+to\s+(L\d+|<last line>)",
            text,
            re.IGNORECASE
        )

        if not match:
            return None

        start = match.group(1)
        end = match.group(2)

        if "<last line>" in end:
            return f"з {start} до кінця програми"

        return f"з {start} до {end}"

    # ---------------- TIME ----------------
    def _format_time(self, sec):
        h = sec // 3600
        m = (sec % 3600) // 60
        s = sec % 60
        return f"{h} год {m} хв {s} сек" if h else f"{m} хв {s} сек"

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

                for raw in text.splitlines():

                    line = self._remove_datetime(raw)
                    if not line:
                        continue

                    # CPU (console only)
                    if "CPU Freq" in line:
                        line = line.replace("CPU Freq =", "").strip()
                        print(f"{self.name} ⚙ Частота процесора: {line}")
                        continue

                    # noise
                    if any(p in line for p in self.SKIP_PATTERNS):
                        print(f"{self.name} {line}")
                        continue

                    # NC START
                    if self._has_marker(self.markers["ncstudio_start"], line):
                        print(f"{self.name} NC STUDIO START")
                        events.append({"type": "NCSTUDIO_START"})
                        continue

                    # NC EXIT
                    if self._has_marker(self.markers["ncstudio_exit"], line):
                        print(f"{self.name} NC STUDIO EXIT")
                        events.append({"type": "NCSTUDIO_EXIT"})
                        continue

                    # SIMULATION START
                    if self._has_marker(self.markers["simulation_start"], line):
                        self.simulation_running = True
                        self.simulation_file = self._extract_filename(line)

                        print(f"{self.name} ⚪ SIMULATION START")

                        events.append({
                            "type": "SIMULATION_START",
                            "file": self.simulation_file
                        })
                        continue

                    # STOP
                    if self._has_marker(self.markers["stop"], line):

                        file_name = self._extract_filename(line)

                        if self.simulation_running:
                            self.simulation_running = False
                            print(f"{self.name} ⚪ SIMULATION STOP")

                            events.append({
                                "type": "SIMULATION_STOP",
                                "file": file_name
                            })
                            continue

                        duration = int(time.time() - self.start_time) if self.start_time else 0
                        self.state = "IDLE"

                        print(f"{self.name} 🔴 STOP")

                        events.append({
                            "type": "STOP",
                            "file": file_name,
                            "duration": duration
                        })
                        continue

                    # MANUAL STOP
                    if self._has_marker(self.markers["manual_stop"], line):

                        file_name = self._extract_filename(line)
                        duration = int(time.time() - self.start_time) if self.start_time else 0

                        self.state = "IDLE"

                        print(f"{self.name} 🟠 STOP MANUAL")

                        events.append({
                            "type": "STOP_MANUAL",
                            "file": file_name,
                            "duration": duration
                        })
                        continue

                    # START / ADVANCED
                    if self._has_marker(self.markers["machining_start"], line):

                        file_name = self._extract_filename(line)

                        self.current_file = file_name
                        self.start_time = time.time()
                        self.state = "RUNNING"

                        is_adv = "(advanced)" in line.lower()
                        l_range = self._parse_l_range(line)

                        if is_adv:
                            print(f"{self.name} 🟡 START ADVANCED")

                            # 🔥 ВАЖЛИВО: ТЕПЕР ТІЛЬКИ ОДИН ТЕКСТ
                            text = "Обробку продовжено"
                            if l_range:
                                text = f"{text}\n{l_range}"

                            events.append({
                                "type": "START_ADVANCED",
                                "file": file_name,
                                "text": text
                            })

                        else:
                            print(f"{self.name} 🟢 START")

                            events.append({
                                "type": "START",
                                "file": file_name
                            })

                        continue

                    # INFO
                    print(f"{self.name} {line}")
                    events.append({"type": "INFO", "msg": line})

        except Exception as e:
            print("NC adapter error:", e)
            return None

        return events if events else None

    # ---------------- FORMAT MESSAGE ----------------
    def format_message(self, event):

        t = event.get("type")
        rule = self.message_rules.get(t)

        if t == "INFO":
            return f"{self.name}\n{event.get('msg')}"

        if not rule:
            return f"{self.name}\n{t}"

        icon = rule.get("icon", "")

        lines = [
            f"{icon} {self.name}".strip(),
            rule.get("text", t)
        ]

        # ✅ ТІЛЬКИ ОДИН БЛОК ТЕКСТУ (без дублювання)
        if "text" in event:
            lines = [
                f"{icon} {self.name}".strip(),
                event["text"]
            ]

        if rule.get("include_file"):
            lines.append(f"Файл: {event.get('file','Невідомо')}")

        if rule.get("include_duration"):
            lines.append(f"Час роботи: {self._format_time(event.get('duration',0))}")

        return "\n".join(lines)