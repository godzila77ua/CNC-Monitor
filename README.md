#CNC Monitor

## Призначення

CNC Monitor — event-driven система моніторингу CNC станків (NCStudio та Engrave), яка перетворює системні логи та файлові зміни у структуровані події з подальшою відправкою в Telegram.
Підтримується масштабування на довільну кількість станків через ENV-конфігурацію, а також можливість додавання нових типів станків через створення адаптерів.


## Архітектура системи

Log / File changes
        ↓
     Adapters
 (NCStudio / Engrave)
        ↓
   Event System
        ↓
  Rules Engine (JSON)
        ↓
   Formatter
        ↓
 Telegram / Console / Log


## NCStudio Adapter

Детекція запуску та завершення обробки
Детекція симуляції
Виявлення ручної зупинки
Обробка інформаційних подій:
CPU frequency
interrupt loss
internal errors
offset changes
Підтримка логів з різними кодуваннями (GBK / UTF-8 fallback)


## Engrave Adapter

File-based state machine для контролю гравіювання:
START — поява або зміна .grv файлу
PAUSE — відсутність змін протягом таймауту
RESUME — відновлення змін файлу
STOP — зникнення файлу

## Rules System

ncstudio_rules.json — правила обробки NCStudio подій
engrave_rules.json — правила форматування Engrave подій
дозволяє змінювати поведінку без зміни коду

## Output

Telegram notifications
Console logging
File logging (monitor.log)