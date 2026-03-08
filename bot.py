#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import requests
import schedule
import time
import datetime
import random
from bs4 import BeautifulSoup
import feedparser
import re
import json
import os
import sys

# ========== НАСТРОЙКИ ==========
TELEGRAM_BOT_TOKEN = '8643690344:AAFUp1aeqQMsP5l9a_GIzWUMrdCSBafr0Ns'
TELEGRAM_CHANNEL_ID = '3327629541'
DEEPSEEK_API_KEY = 'sk-09168cb710ee4c9f994f892dd8557d20'

# Расписание тем (время - тема)
SCHEDULE = {
    "09:00": "наука",
    "11:00": "кино",
    "13:00": "IT",
    "15:00": "наука",
    "17:00": "IT",
    "19:00": "кино"
}

# Твой промт
SYSTEM_PROMPT = """Ты — креативный редактор Telegram-канала. Твоя задача: писать короткие, вирусные и интересные посты на основе сырых новостей.

Правила:
1. Тематика: IT, киноиндустрия, технологии, а также общественные новости России, США и СНГ, которые НЕ касаются военных действий и политических конфликтов. Примеры тем: атаки БПЛА (как техногенное событие), выходы фильмов, открытия ученых, законы в IT, вирусные видео, курьезы.
2. Структура поста:
   - Заголовок (цепляющий).
   - Основная часть — максимум один абзац (3-5 предложений). Сжато, но интересно.
   - Обязательно использовать 2-3 эмодзи в тексте.
   - В конце, если новость НЕ грустная и НЕ трагическая, добавь ОДНУ забавную, ироничную или удивляющую фразу-«вишенку» на тему поста. Она должна начинаться с многоточия и смайлика.
3. Запрещено:
   - Не начинай пост с фраз "Конечно, вот статья:", "Вот новость:" и т.п.
   - Не пиши о войнах и политике.
   - Не делай пост грустным.
4. Важнейшее правило:
   НЕ НАЧИНАЙ ответ с фраз-паразитов. Начинай сразу с заголовка поста."""

# Сайты для поиска
SOURCES = {
    "IT": ["habr.com"],
    "наука": ["lenta.ru"],
    "кино": ["kinopoisk.ru"]
}

# ========== ЛОГИРОВАНИЕ ==========
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_current_date():
    return datetime.datetime.now().strftime("%d.%m.%Y")

def search_articles_by_topic(topic):
    """Ищет статьи по теме (упрощённая версия для Railway)"""
    logging.info(f"Поиск по теме: {topic}")
    
    sites = SOURCES.get(topic, SOURCES["IT"])
    test_urls = {
        "IT": "https://habr.com/ru/news/",
        "наука": "https://lenta.ru/rubrics/science/",
        "кино": "https://www.kinopoisk.ru/media/news/"
    }
    
    return [test_urls.get(topic, test_urls["IT"])]

def get_article_text(url):
    """Извлекает текст статьи"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        if "habr.com" in url:
            article = soup.find('div', class_='tm-article-body')
        elif "lenta.ru" in url:
            article = soup.find('div', class_='b-text')
        elif "kinopoisk.ru" in url:
            article = soup.find('div', class_='news_item_text')
        else:
            article = soup
        
        if article:
            paragraphs = article.find_all('p')
            text = ' '.join([p.get_text() for p in paragraphs])
            return text[:3000] if text else None
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        return None

def generate_post_with_deepseek(article_text, article_url, topic):
    """Генерирует пост через DeepSeek"""
    prompt = f"""{SYSTEM_PROMPT}

Сегодня {get_current_date()}, тема: {topic}.
Статья: {article_url}

{article_text}

Напиши пост строго по правилам выше. Начинай сразу с заголовка."""
    
    headers = {
        'Authorization': f'Bearer {DEEPSEEK_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    data = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.8,
        "max_tokens": 800
    }
    
    try:
        response = requests.post(
            'https://api.deepseek.com/v1/chat/completions',
            headers=headers,
            json=data,
            timeout=60
        )
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        logging.error(f"DeepSeek ошибка: {e}")
        return None

def send_to_telegram(message):
    """Отправляет пост в канал"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        'chat_id': TELEGRAM_CHANNEL_ID,
        'text': message,
        'parse_mode': 'HTML'
    }
    try:
        requests.post(url, json=data)
        logging.info("Пост отправлен")
    except Exception as e:
        logging.error(f"Ошибка отправки: {e}")

def job_for_topic(topic):
    """Задача для конкретной темы"""
    logging.info(f"Запуск задачи. Тема: {topic}")
    
    article_urls = search_articles_by_topic(topic)
    if not article_urls:
        return
    
    article_text = get_article_text(article_urls[0])
    if not article_text:
        return
    
    post = generate_post_with_deepseek(article_text, article_urls[0], topic)
    if post:
        send_to_telegram(post)

def run_scheduled_jobs():
    """Проверяет расписание"""
    while True:
        now = datetime.datetime.now().strftime("%H:%M")
        if now in SCHEDULE:
            topic = SCHEDULE[now]
            logging.info(f"Время {now}, тема {topic}")
            job_for_topic(topic)
            time.sleep(60)
        time.sleep(30)

if __name__ == "__main__":
    logging.info("Бот запущен")
    run_scheduled_jobs()
