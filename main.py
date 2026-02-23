import os
import requests
import json
from openai import OpenAI

# =========================================
# 환경 변수
# =========================================
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

MODEL_NAME = "gpt-4o-mini"

client = OpenAI(api_key=OPENAI_API_KEY)


# =========================================
# 뉴스 수집 (성공했던 안정 구조 유지)
# =========================================
def fetch_news(country=None, language=None, limit=10):
    url = "https://newsapi.org/v2/top-headlines"

    params = {
        "pageSize": limit,
        "sortBy": "popularity",
        "apiKey": NEWS_API_KEY,
    }

    if country:
        params["country"] = country
    if language:
        params["language"] = language

    response = requests.get(url, params=params)

    if response.status_code != 200:
        print("HTTP ERROR:", response.status_code)
        print(response.text)
        return []

    data = response.json()

    if data.get("status") != "ok":
        print("NEWS API ERROR:", data)
        return []

    articles = data.get("articles", [])
    print("Fetched:", len(articles))
    return articles


# =========================================
# 전처리 (최소 필터)
# =========================================
def preprocess_articles(articles):
    unique = {}

    for a in articles:
        title = (a.get("title") or "").strip()
        description = (a.get("description") or "").strip()
        content = (a.get("content") or "").strip()

        if not title:
            continue

        summary_text = description if description else content

        if not summary_text:
            continue

        if title in unique:
            continue

        unique[title] = {
            "title": title,
            "summary_text": summary_text,
            "url": a.get("url", "")
        }

    return list(unique.values())


# =========================================
# 중요 기사 선택
# =========================================
def select_top_articles(articles, top_n=3):

    prompt = """
다음 뉴스 중 IT/AI/산업/개발자 관점에서 가장 의미 있는 기사 3개의 번호만 JSON 배열로 반환하라.
가십성 기사 제외.
반드시 예: [1,3,5] 형식으로만 출력.
"""

    for i, a in enumerate(articles):
        prompt += f"\n[{i}] 제목: {a['title']} 요약: {a['summary_text']}"

    response = client.responses.create(
        model=MODEL_NAME,
        input=prompt,
        max_output_tokens=120,
        temperature=0.2
    )

    try:
        indices = json.loads(response.output_text.strip())
        print("Selected indices:", indices)
        return indices[:top_n]
    except:
        return list(range(min(3, len(articles))))


# =========================================
# 🔥 업그레이드 분석 부분
# =========================================
def summarize_and_predict(article):

    prompt = f"""
당신은 금융 이벤트 기반 분석 시스템이다.
기사에 명시되지 않은 정보는 생성하지 말 것.
추측 금지.

기사 제목:
{article['title']}

기사 내용:
{article['summary_text']}

분석 절차:

1) 기사 핵심 요약 (3~5줄)
2) 핵심 이벤트 한 줄 정의
3) 이벤트 유형 분류
4) 영향 기업 또는 산업
5) 산업 파급력 분석
6) 주가 영향 평가
   - 방향 (상승/하락/중립)
   - 강도 (약/중/강)
   - 확률 (% 숫자)
   - 시간 범위 (단기/중기)
   - 근거
7) 리스크 요인

구조화된 형식으로 출력.
"""

    response = client.responses.create(
        model=MODEL_NAME,
        input=prompt,
        max_output_tokens=900,
        temperature=0.2
    )

    return response.output_text


# =========================================
# 디스코드 전송
# =========================================
def send_to_discord(content):
    requests.post(DISCORD_WEBHOOK, json={"content": content})


# =========================================
# 메인
# =========================================
def main():

    # 🇰🇷 한국 10개
    kr_news = fetch_news(country="kr", limit=10)

    # 🌍 해외 10개
    global_news = fetch_news(language="en", limit=10)

    print("KR raw:", len(kr_news))
    print("GLOBAL raw:", len(global_news))

    if len(kr_news) == 0 and len(global_news) == 0:
        send_to_discord("NewsAPI 응답 없음")
        return

    articles = preprocess_articles(kr_news + global_news)

    print("After preprocess:", len(articles))

    if len(articles) < 3:
        send_to_discord(f"전처리 후 기사 부족: {len(articles)}개")
        return

    selected_indices = select_top_articles(articles)

    message = "📌 오늘의 IT/AI 핵심 뉴스 TOP 3 (고급 분석)\n\n"

    for idx in selected_indices:
        if idx >= len(articles):
            continue

        article = articles[idx]
        result = summarize_and_predict(article)

        message += f"🔹 {article['title']}\n"
        message += result
        message += "\n\n"

    send_to_discord(message)


if __name__ == "__main__":
    main()
