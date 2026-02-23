import os
import requests
from datetime import datetime
from openai import OpenAI

# ==============================
# Config
# ==============================
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TOPIC = "AI"

client = OpenAI(api_key=OPENAI_API_KEY)


# ==============================
# News Service
# ==============================
class NewsService:
    BASE_URL = "https://newsapi.org/v2/everything"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def fetch(self, topic: str, limit: int = 3):
        params = {
            "q": topic,
            "sortBy": "publishedAt",
            "language": "ko",
            "apiKey": self.api_key,
            "pageSize": limit,
        }
        response = requests.get(self.BASE_URL, params=params)
        response.raise_for_status()
        return response.json()["articles"]


# ==============================
# AI Summarizer
# ==============================
def summarize(text: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "뉴스를 3줄로 간결하게 요약해라."},
            {"role": "user", "content": text}
        ],
        max_tokens=150
    )
    return response.choices[0].message.content.strip()


# ==============================
# Message Builder
# ==============================
def build_message(topic: str, articles: list) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    result = f"📌 {today} {topic} 뉴스 요약\n\n"

    for article in articles:
        summary = summarize(article["title"] + "\n" + (article.get("description") or ""))
        result += f"🔹 {article['title']}\n"
        result += f"{summary}\n"
        result += f"{article['url']}\n\n"

    return result


# ==============================
# Sender
# ==============================
def send_to_discord(webhook_url: str, content: str):
    requests.post(webhook_url, json={"content": content})


# ==============================
# Main
# ==============================
def main():
    service = NewsService(NEWS_API_KEY)
    articles = service.fetch(TOPIC)
    message = build_message(TOPIC, articles)
    send_to_discord(DISCORD_WEBHOOK, message)


if __name__ == "__main__":
    main()
