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


    # ---------------- LOAD RULES ----------------
    def _load_rules(self):
        path = os.path.join(os.path.dirname(__file__), "ncstudio_rules.json")
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)


    # ---------------- CLEAN (ONLY FOR OUTPUT) ----------------
    def _remove_datetime(self, text):

        text = re.sub(
            r"^[A-Z]\s+\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\s*",
            "",
            text
        )

        text = re.sub(
            r"[^\x00-\x7F\u0400-\u04FF\u4e00-\u9fff\s\[\]\:\-\.\>\=\/\\]+",
            "",
            text
        )

        return text.strip()


    # ---------------- MARKER (RAW ONLY) ----------------
    def _has_marker(self, marker, raw_line):

        line = re.sub(r"\s+", " ", raw_line).strip()

        if isinstance(marker, list):
            return any(m in line for m in marker)

        return marker in line


    # ---------------- OFFSET PARSER ----------------
    def _parse_offset(self, raw):

        match = re.search(r"\[(.*?)\]:\s*(.+)", raw)
        if not match:
            return raw

        coord = match.group(1)
        data = match.group(2).strip()

        return f"[{coord}]: {data}"


    # ---------------- L RANGE PARSER ----------------
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


    # ---------------- FILE NAME ----------------
    def _extract_filename(self, text):

        matches = re.findall(r"[A-Z]:\\[^'\n\r]+?\.NC", text, re.IGNORECASE)

        if matches:
            path = matches[-1]
            return os.path.basename(path).rsplit(".", 1)[0].strip()

        return self.current_file


    # ---------------- TIME ----------------
    def _format_time(self, sec):
        h = sec // 3600
        m = (sec % 3600) // 60
        s = sec % 60
        return f"{h} год {m} хв {s} сек" if h else f"{m} хв {s} сек"


    # ---------------- EVENT WRAPPER ----------------
    def _event(self, category, event_type, **data):
        return {
            "category": category,
            "type": event_type,
            **data
        }


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

                raw_lines = data.splitlines()

                for raw_bytes in raw_lines:

                    try:
                        raw = raw_bytes.decode("gbk")
                    except:
                        try:
                            raw = raw_bytes.decode("utf-8", errors="ignore")
                        except:
                            raw = raw_bytes.decode("cp1251", errors="ignore")

                    try:
                        raw_file = raw_bytes.decode("cp1251")
                    except:
                        raw_file = raw

                    if not raw:
                        continue

                    clean = self._remove_datetime(raw)
                    clean_file = self._remove_datetime(raw_file)

                    handled = False

                    # ---------------- CPU ----------------
                    if self._has_marker(self.markers.get("cpu_freq"), raw):

                        value = clean.replace("CPU Freq =", "").strip()

                        match = re.search(r"(\d+)M,\s*(\d+)\s*CPU ticks per 5000us", value)
                        if match:
                            value = f"{match.group(1)}M, {match.group(2)} ticks/5ms"

                        events.append(
                            self._event("INFO", "CPU_FREQ", msg=value)
                        )
                        handled = True


                    # ---------------- OFFSET ----------------
                    elif self._has_marker(self.markers.get("offset_change"), raw):

                        events.append(
                            self._event("INFO", "OFFSET_CHANGE", msg=self._parse_offset(clean))
                        )
                        handled = True


                    # ---------------- NC START ----------------
                    elif self._has_marker(self.markers["ncstudio_start"], raw):

                        events.append(self._event("STATE", "NCSTUDIO_START"))
                        handled = True


                    # ---------------- NC EXIT ----------------
                    elif self._has_marker(self.markers["ncstudio_exit"], raw):

                        events.append(self._event("STATE", "NCSTUDIO_EXIT"))
                        handled = True


                    # ---------------- SIMULATION START ----------------
                    elif self._has_marker(self.markers["simulation_start"], raw):

                        self.simulation_running = True
                        self.simulation_file = self._extract_filename(clean_file)

                        events.append(
                            self._event(
                                "INFO",
                                "SIMULATION_START",
                                file=self.simulation_file
                            )
                        )
                        handled = True


                    # ---------------- STOP ----------------
                    elif self._has_marker(self.markers["stop"], raw):

                        file_name = self._extract_filename(clean_file)

                        event_type = "SIMULATION_STOP" if self.simulation_running else "STOP"

                        if self.simulation_running:
                            self.simulation_running = False

                        duration = int(time.time() - self.start_time) if self.start_time else 0
                        self.state = "IDLE"

                        events.append(
                            self._event(
                                "STATE" if event_type == "STOP" else "INFO",
                                event_type,
                                file=file_name,
                                duration=duration
                            )
                        )
                        handled = True


                    # ---------------- MANUAL STOP ----------------
                    elif self._has_marker(self.markers["manual_stop"], raw):

                        file_name = self._extract_filename(clean_file)
                        duration = int(time.time() - self.start_time) if self.start_time else 0

                        self.state = "IDLE"

                        events.append(
                            self._event(
                                "STATE",
                                "STOP_MANUAL",
                                file=file_name,
                                duration=duration
                            )
                        )
                        handled = True


                    # ---------------- START / ADVANCED ----------------
                    elif self._has_marker(self.markers["machining_start"], raw):

                        file_name = self._extract_filename(clean_file)

                        self.current_file = file_name
                        self.start_time = time.time()
                        self.state = "RUNNING"

                        is_adv = "(advanced)" in raw.lower()
                        l_range = self._parse_l_range(raw)

                        text = None
                        if is_adv:
                            text = "Обробку продовжено"
                            if l_range:
                                text = f"{text}\n{l_range}"

                        events.append(
                            self._event(
                                "STATE",
                                "START_ADVANCED" if is_adv else "START",
                                file=file_name,
                                text=text
                            )
                        )
                        handled = True


                    # ---------------- RAW INFO ----------------
                    if not handled:
                        events.append(
                            self._event("RAW", "RAW_INFO", msg=clean)
                        )

        except Exception as e:
            return [self._event("RAW", "RAW_INFO", msg=f"Adapter error: {e}")]

        return events if events else None


    # ---------------- FORMAT MESSAGE ----------------
    def format_message(self, event):

        t = event.get("type")
        rule = self.message_rules.get(t, {})

        icon = rule.get("icon", "")

        if t in ["RAW_INFO", "CPU_FREQ", "OFFSET_CHANGE"]:
            text = rule.get("text", "")
            msg = event.get("msg", "")

            if text:
                return f"{icon} {self.name}\n{text}: {msg}"

            return f"{icon} {self.name}\n{msg}"

        lines = [
            f"{icon} {self.name}".strip(),
            rule.get("text", t)
        ]

        if event.get("text"):
            lines = [
                f"{icon} {self.name}".strip(),
                event["text"]
            ]

        if rule.get("include_file"):
            lines.append(f"Файл: {event.get('file','Невідомо')}")

        if rule.get("include_duration"):
            lines.append(f"Час роботи: {self._format_time(event.get('duration',0))}")

        return "\n".join(lines)