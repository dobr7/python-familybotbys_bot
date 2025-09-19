import telebot
import requests
import feedparser  # type: ignore
import re

BOT_TOKEN = "8128313701:AAGbdvjIkfAZz1iqD4cnY9RMzqvXoICagYk"
WEATHER_API_KEY = "d9f27706e9fddf4e772de7674561bcfc"
FINANCE_API_KEY = "c693be22a0d0492e067be7c1"

bot = telebot.TeleBot(BOT_TOKEN)


waiting_for_city = {}  # user_id -> True/False


# Экранирование для MarkdownV2
def escape_md_v2(text):
    # Экранируем спецсимволы MarkdownV2
    return re.sub(r"([_*\[\]()~`>#+-=|{}.!])", r"\\\1", text)


# ===== ПОГОДА =====
def get_weather(city):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric&lang=ru"
    response = requests.get(url).json()

    if response.get("cod") != 200:
        return "Не могу найти погоду для этого города/страны 😕"

    temp = response["main"]["temp"]
    description = response["weather"][0]["description"]
    wind = response["wind"]["speed"]

    if "облачно" in description or "пасмурно" in description:
        emoji = "☁️"
    elif "ясно" in description or "солнечно" in description:
        emoji = "☀️"
    elif "дождь" in description:
        emoji = "🌧️"
    elif "снег" in description:
        emoji = "❄️"
    elif "туман" in description:
        emoji = "🌫️"
    else:
        emoji = "🌡️"

    if wind < 3:
        wind_emoji = "🍃"
    elif wind < 7:
        wind_emoji = "💨"
    else:
        wind_emoji = "🌬️"

    weather_message = (
        f"*Погода в {city}* {emoji}\n\n"
        f"🌡 *Температура:* {temp:.1f}°C\n\n"
        f"📝 *Описание:* {description}\n\n"
        f"🌀 *Скорость ветра:* {wind:.1f} м/с {wind_emoji}"
    )

    return weather_message


# ===== НОВОСТИ =====
def get_rss_news(count=5):
    url = "https://ria.ru/export/rss2/index.xml?page_type=google_newsstand"
    feed = feedparser.parse(url)
    news_items = []

    for entry in feed.entries[:count]:
        title = entry.get("title", "Без заголовка")
        link = entry.get("link", "")
        escaped_title = escape_md_v2(title)
        escaped_link = escape_md_v2(link)
        news_items.append(
            f"📰 *{escaped_title}*\n🔗 [Читать подробнее…]({escaped_link})"
        )

    if not news_items:
        return "⚠️ Не удалось получить новости 😕"

    return "🌎 *Свежие новости:*\n\n" + "\n\n".join(news_items)


# ===== КУРСЫ ВАЛЮТ =====
def get_exchange_rates_message():
    url = "https://v6.exchangerate-api.com/v6/c693be22a0d0492e067be7c1/latest/USD"
    try:
        resp = requests.get(url).json()
        rates = resp.get("conversion_rates")
        if not rates:
            return "⚠️ Не удалось получить курсы валют 😕"

        usd_to_rub = rates.get("RUB")  # 1 USD в RUB
        usd_to_eur = rates.get("EUR")  # 1 USD в EUR
        eur_to_rub = usd_to_rub / usd_to_eur  # 1 EUR в RUB

        return (
            "🏦 *Курсы валют:*\n\n"
            f"🇺🇸 USD → 🇷🇺 RUB: {usd_to_rub:.2f} ₽\n"
            f"🇪🇺 EUR → 🇷🇺 RUB: {eur_to_rub:.2f} ₽\n\n"
            f"🇷🇺 RUB → 🇺🇸 USD: {1/usd_to_rub:.4f} $\n"
            f"🇷🇺 RUB → 🇪🇺 EUR: {1/eur_to_rub:.4f} €"
        )
    except Exception as e:
        return f"⚠️ Ошибка при получении курсов валют: {e}"


# ===== КРИПТОВАЛЮТЫ =====
def get_crypto_rates_message():
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {"ids": "bitcoin,ethereum,tether", "vs_currencies": "usd,rub"}
    try:
        resp = requests.get(url, params=params).json()

        btc_usd = resp["bitcoin"]["usd"]
        btc_rub = resp["bitcoin"]["rub"]

        eth_usd = resp["ethereum"]["usd"]
        eth_rub = resp["ethereum"]["rub"]

        usdt_usd = resp["tether"]["usd"]
        usdt_rub = resp["tether"]["rub"]

        return (
            "💎 *Криптовалюты:*\n\n"
            f"₿ Bitcoin:\n{btc_usd:,.2f} $ | {btc_rub:,.2f} ₽\n\n"
            f"Ξ Ethereum:\n{eth_usd:,.2f} $ | {eth_rub:,.2f} ₽\n\n"
            f"💵 Tether (USDT):\n{usdt_usd:,.2f} $ | {usdt_rub:,.2f} ₽"
        )
    except Exception as e:
        return f"⚠️ Ошибка получения курсов криптовалют: {e}"


# ===== КОМАНДЫ =====


# команда /start
@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(
        message.chat.id,
        "👋 Привет! Я *бот-помощник*.\n\n"
        "Что я умею:\n\n"
        "🌤 /weather – показать погоду\n\n"
        "📰 /news – свежие новости\n\n"
        "💱 /finance – показать курсы валют и криптовалюту\n\n"
        "📌 /help – список команд\n\n",
        parse_mode="Markdown",
    )


# команда /news
@bot.message_handler(commands=["news"])
def send_news(message):
    news = get_rss_news()
    bot.send_message(message.chat.id, news, parse_mode="MarkdownV2")


# команда /exchange (валюты + крипта)
@bot.message_handler(commands=["finance"])
def send_exchange(message):
    currency_msg = get_exchange_rates_message()
    crypto_msg = get_crypto_rates_message()
    full_msg = currency_msg + "\n\n" + crypto_msg
    bot.send_message(message.chat.id, full_msg, parse_mode="Markdown")


# команда /help
@bot.message_handler(commands=["help"])
def send_help(message):
    help_text = (
        "📌 *Список команд бота:*\n\n"
        "🌤 /weather – показать погоду в выбранном городе\n\n"
        "📰 /news – свежие новости\n\n"
        "💱 /finance – курсы валют и криптовалюты\n\n"
        "ℹ️ /help – показать это сообщение"
    )
    bot.send_message(message.chat.id, help_text, parse_mode="Markdown")


# команда /weather
@bot.message_handler(commands=["weather"])
def ask_city(message):
    user_id = message.from_user.id
    waiting_for_city[user_id] = True
    bot.send_message(message.chat.id, "Напиши название города,\nи я покажу погоду 🌍")


# обработка текста только если ждём город
@bot.message_handler(func=lambda m: True)
def city_weather(message):
    user_id = message.from_user.id
    if waiting_for_city.get(user_id):
        city = message.text.strip()
        weather = get_weather(city)
        bot.send_message(
            message.chat.id, weather, parse_mode="Markdown"
        )  # <-- здесь добавили parse_mode
        waiting_for_city[user_id] = False
    else:
        # в других случаях бот молчит
        pass


bot.polling(none_stop=True, interval=0)
