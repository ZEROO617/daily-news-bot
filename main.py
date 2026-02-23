import os
import requests
from datetime import datetime

# ==============================
# Config (환경변수 사용)
# ==============================
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
TOPIC = "AI"


# ==============================
# News Service
# ==============================
class NewsService:
    BASE_URL = "https://newsapi.org/v2/everything"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def fetch(self, topic: str, limit: int = 5):
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
# Message Builder
# ==============================
def build_message(topic: str, articles: list) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    header = f"📌 {today} {topic} 뉴스 요약\n"

    body = "\n".join(
        [f"- {a['title']}\n  {a['url']}" for a in articles]
    )

    return header + "\n" + body


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
