# Телеграм-бот для проверки статуса домашней работы 

## Описание

Бот периодически опрашивает API Яндекс.домашка и присылает изменения статуса последней домашней работы. Также бот логгирует важные события

## Установка проекта

Установить зависимости из файла `requirements.txt` и запустить локально или на удалённом сервере (например, [heroku.com]()). Для работы нужны токены telegram и [Я.домашки](https://practicum.yandex.ru/api/user_api/homework_statuses/)

## Пример .env файла
```
TELEGRAM_TOKEN = 3174677406:AAHx7ijkmekXILBbfYzn7nAaNqtiQjU63q8
YANDEX_TOKEN = AQAABAABaT4WcAYckdSYm5vyn27g8TKtITc
USER_ID = 123896774
```

## Стек

Django, Telegram Python lib

## Автор

Семён Егоров  


[LinkedIn](https://www.linkedin.com/in/simonegorov/)  
[Email](simon.egorov.job@gmail.com)  
[Telegram](https://t.me/SamePersoon)
