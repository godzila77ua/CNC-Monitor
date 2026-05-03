# Example configuration file
# This file is safe to commit to Git (no real secrets)

TOKEN = "PUT_YOUR_TOKEN_HERE"
CHAT_ID = "PUT_YOUR_CHAT_ID_HERE"

MACHINES = [
    {
        "NAME": "NC STUDIO",
        "TYPE": "NCSTUDIO",
        "WATCH_FILE": r"Сюди вставляємо шлях до файлу\NCSTUDIO.DYN",
        "LOG_FILE": r"Сюди вставляємо шлях до файлу\NCSTUDIO.LOG",
        "IDLE_TIMEOUT": 15,
        "PAUSE_TIMEOUT": 15
    },
    {
        "NAME": "ENGRAVE 80E",
        "TYPE": "ENGRAVE",
        "WATCH_FILE": r"Сюди вставляємо шлях до файлу\ws080e1.grv",
        "IDLE_TIMEOUT": 20,
        "PAUSE_TIMEOUT": 10
    }
]