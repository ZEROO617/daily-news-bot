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

KEYWORDS = "IT OR AI OR startup OR programming OR computer"


# =========================================
# 뉴스 수집
# =========================================
def fetch_news(country=None, language=None, limit=10):
    url = "https://newsapi.org/v2/top-headlines"

    params = {
        "q": KEYWORDS,
        "pageSize": limit,
        "sortBy": "popularity",
        "apiKey": NEWS_API_KEY,
    }

    if country:
        params["country"] = country
    if language:
        params["language"] = language

    response = requests.get(url, params=params)
    data = response.json()

    return data.get("articles", [])


# =========================================
# 전처리 (토큰 최소화 + 품질 유지)
# =========================================
def preprocess_articles(articles):
    unique = {}

    for a in articles:
        title = (a.get("title") or "").strip()
        description = (a.get("description") or "").strip()
        content = (a.get("content") or "").strip()

        if not title:
            continue

        summary_text = description if len(description) > 30 else content

        if len(summary_text) < 30:
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
# 1차: 중요 기사 선택 (구조적 기준 적용)
# =========================================
def select_top_articles(articles, top_n=3):

    prompt = """
다음 뉴스 중 IT/AI/산업/개발자 관점에서 가장 의미 있는 기사 3개의 번호만 JSON 배열로 반환하라.

판단 기준:
- 산업적 파급력
- 기술 혁신성
- 시장/주식 영향 가능성
- 개발자 생태계 영향
- 단순 가십/홍보성 기사 제외

반드시 JSON 배열만 반환.
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
        return indices[:top_n]
    except:
        return [0, 1, 2]


# =========================================
# 2차: 고급 분석 + 주가 영향 평가
# =========================================
def summarize_and_predict(article):

    prompt = f"""
당신은 금융 이벤트 기반 분석 시스템이다.
기사에 명시되지 않은 정보는 생성하지 말 것.
추측, 과장, 외부 정보 추가 금지.

기사 제목:
{article['title']}

기사 내용:
{article['summary_text']}

분석 절차:

1) 기사 핵심 요약 (3~5줄)
   - 사실 중심
   - 수치, 기업명, 정책명은 유지

2) 핵심 이벤트 정의 (한 문장)

3) 이벤트 유형 분류
   (투자, 인수합병, 실적, 신제품, 규제, 정책, 기술혁신, 보안사고, 파트너십, 기타)

4) 직접 영향 기업 또는 산업 식별
   - 기사에 명시된 기업만 사용
   - 없으면 산업 단위로 분석

5) 산업 파급력 분석
   - 경쟁구도 변화
   - 시장 점유율 영향 가능성
   - 기술적 진입장벽 변화

6) 주가 영향 평가
   - 방향: 상승 / 하락 / 중립
   - 강도: 약 / 중 / 강
   - 확률 범위 (% 숫자로 제시)
   - 시간 범위: 단기(1~7일) / 중기(1~3개월)
   - 근거: 기사 내용 기반으로 설명

7) 불확실성 및 리스크 요인
   - 정보 부족
   - 정책 변수
   - 거시경제 변수
   - 실행 리스크

출력 형식:

[기사 요약]
...

[핵심 이벤트]
...

[이벤트 유형]
...

[영향 기업/산업]
...

[산업 파급력]
...

[주가 영향 평가]
- 방향:
- 강도:
- 확률:
- 시간 범위:
- 근거:

[리스크 요인]
...
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
# 메인 실행
# =========================================
def main():

    kr_news = fetch_news(country="kr", limit=10)
    global_news = fetch_news(language="en", limit=10)

    articles = preprocess_articles(kr_news + global_news)

    if len(articles) < 3:
        send_to_discord("뉴스 수집 실패 또는 기사 부족")
        return

    selected_indices = select_top_articles(articles)

    message = "📌 오늘의 IT/AI 핵심 뉴스 TOP 3 (고급 분석)\n\n"

    for idx in selected_indices:
        article = articles[idx]
        result = summarize_and_predict(article)

        message += f"🔹 {article['title']}\n"
        message += result
        message += "\n\n"

    send_to_discord(message)


if __name__ == "__main__":
    main()
