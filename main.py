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
# 뉴스 수집
# =========================================
def fetch_news(query=None, country=None, language=None, limit=10):
    url = "https://newsapi.org/v2/top-headlines"

    params = {
        "pageSize": limit,
        "apiKey": NEWS_API_KEY,
    }

    if query:
        params["q"] = query
    if country:
        params["country"] = country
    if language:
        params["language"] = language

    response = requests.get(url, params=params)

    # HTTP 에러 확인
    if response.status_code != 200:
        print("HTTP ERROR:", response.status_code)
        print(response.text)
        return []

    data = response.json()

    # NewsAPI 내부 에러 확인
    if data.get("status") != "ok":
        print("NEWS API ERROR:", data)
        return []

    articles = data.get("articles", [])
    print("Fetched:", len(articles))
    return articles


# =========================================
# 전처리 (완화 버전)
# =========================================
def preprocess_articles(articles):
    unique = {}

    for a in articles:
        title = (a.get("title") or "").strip()
        description = (a.get("description") or "").strip()
        content = (a.get("content") or "").strip()

        if not title:
            continue

        # description 우선 사용, 없으면 content
        summary_text = description if description else content

        # 최소 길이 완화
        if not summary_text or len(summary_text) < 10:
            continue

        # 중복 제거
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
반드시 예: [1,3,5] 형식으로만 출력하라.
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
    except Exception as e:
        print("Selection parse error:", e)
        return list(range(min(3, len(articles))))


# =========================================
# 요약 + 분석
# =========================================
def summarize_and_predict(article):

    prompt = f"""
기사 제목:
{article['title']}

기사 내용:
{article['summary_text']}

1) 핵심 요약 (3~5줄)
2) 이벤트 유형
3) 영향 기업/산업
4) 주가 영향 방향 및 확률
5) 리스크 요인
"""

    response = client.responses.create(
        model=MODEL_NAME,
        input=prompt,
        max_output_tokens=700,
        temperature=0.2
    )

    return response.output_text


# =========================================
# 디스코드 전송
# =========================================
def send_to_discord(content):
    requests.post(DISCORD_WEBHOOK, json={"content": content})


# =========================================
# 메인 실행
# =========================================
def main():

    # 🔎 한국/해외 쿼리 분리
    kr_query = "인공지능 OR AI OR 스타트업 OR IT OR 프로그래밍"
    global_query = "AI OR startup OR programming OR technology"

    kr_news = fetch_news(query=kr_query, country="kr", limit=10)
    global_news = fetch_news(query=global_query, language="en", limit=10)

    print("KR raw:", len(kr_news))
    print("GLOBAL raw:", len(global_news))

    # 1차 검증
    if len(kr_news) == 0 and len(global_news) == 0:
        send_to_discord("NewsAPI 응답 없음 - API 또는 쿼리 확인 필요")
        return

    # 전처리
    articles = preprocess_articles(kr_news + global_news)

    print("After preprocess:", len(articles))

    # 2차 검증
    if len(articles) < 3:
        send_to_discord(f"전처리 후 기사 부족: {len(articles)}개")
        return

    # 중요 기사 선택
    selected_indices = select_top_articles(articles)

    message = "📌 오늘의 IT/AI 핵심 뉴스 TOP 3\n\n"

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
