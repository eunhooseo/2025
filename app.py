import streamlit as st
import random
import datetime

# --------------------
# 스타일 (마법사 + 신비한 분위기)
# --------------------
st.set_page_config(page_title="현실적 조언 마법사", page_icon="🧙‍♂️", layout="centered")

st.markdown("""
    <style>
        body {
            background-color: #0a0f2c;
            color: #e0e0e0;
            font-family: 'Trebuchet MS', sans-serif;
        }
        .title {
            font-size: 36px;
            font-weight: bold;
            color: #c7bfff;
            text-align: center;
            margin-bottom: 10px;
        }
        .subtitle {
            font-size: 18px;
            text-align: center;
            color: #b0a8d6;
            margin-bottom: 30px;
        }
        .wizard-img {
            display: block;
            margin-left: auto;
            margin-right: auto;
            width: 250px;
        }
        .bubble {
            background: rgba(255, 255, 255, 0.1);
            padding: 20px;
            border-radius: 10px;
            margin-top: 20px;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="title">🧙‍♂️ 현실적 조언 마법사</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">마법사는 네 고민을 현실적으로 풀어줄 거야...</div>', unsafe_allow_html=True)

# 마법사 이미지 (github 같은 데서 이미지 url로 넣으면 됨)
st.image("https://i.imgur.com/vWgC6Ay.png", caption="마법사가 항아리를 휘젓는 중...", use_column_width=False, width=300)

# --------------------
# 고민 입력
# --------------------
user_text = st.text_area("✨ 고민을 적어봐 ✨", placeholder="예: 새벽 3시인데 불닭 먹어도 될까?...")

# --------------------
# 각 고민 유형별 조언 함수
# --------------------
def advise_food(text):
    return {
        "advice": "매운 라면은 피부에 안 좋아. 야식으로 먹으면 체중도 늘고 다음날 피곤할 거야.",
        "risk": f"여드름 위험 ↑, 체중 +{random.randint(0,1)}kg 예상"
    }

def advise_study(text):
    return {
        "advice": "지금 공부하는 게 힘들다면 25분만 집중하고 5분 쉬는 '포모도로' 추천!",
        "risk": "미루면 시험 때 후회 100%"
    }

def advise_love(text):
    return {
        "advice": "상대방이 네 신호를 모를 수도 있어. 솔직하게 말해보는 게 가장 빠르다.",
        "risk": "고백 안 하면 평생 후회 가능성 ↑"
    }

def advise_weather(text):
    return {
        "advice": "비 오는 날이니 우산 챙겨. 오늘 기온은 대략 25도 안팎일 듯.",
        "risk": "우산 안 챙기면 쫄딱 젖음"
    }

def advise_fashion(text):
    return {
        "advice": "빨간 블라우스엔 검은 바지가 제일 무난. 흰색은 튀고, 청바지도 잘 어울려.",
        "risk": "색 조합 실패 → 패션 테러 확률 ↑"
    }

def advise_late(text):
    return {
        "advice": "지금 남은 시간으론 전력질주해야 도착 가능. 뛰면 7분 안에 도착할 수도 있어.",
        "risk": "뛰다 넘어져서 더 늦을 위험 있음"
    }

def advise_fortune(text):
    fortunes = [
        "오늘은 새로운 시작을 하기 좋은 날이야.",
        "조금 조심하는 게 좋아. 특히 사람 사이에서.",
        "뜻밖의 행운이 찾아올 수도 있어.",
        "작은 실수를 크게 만들지 않도록 주의해."
    ]
    return {
        "advice": random.choice(fortunes),
        "risk": "운세는 재미로만 보자!"
    }

# --------------------
# 라우팅 함수 (무한재귀 ❌)
# --------------------
def route_and_reply(text: str):
    text = text.lower()
    if "불닭" in text or "야식" in text or "라면" in text:
        return advise_food(text)
    elif "공부" in text or "시험" in text:
        return advise_study(text)
    elif "좋아하는 사람" in text or "연애" in text or "고백" in text:
        return advise_love(text)
    elif "날씨" in text or "비" in text or "우산" in text:
        return advise_weather(text)
    elif "바지" in text or "옷" in text or "블라우스" in text:
        return advise_fashion(text)
    elif "학교" in text or "지각" in text or "늦" in text:
        return advise_late(text)
    elif "운세" in text or "점" in text:
        return advise_fortune(text)
    else:
        return {"advice": "마법사가 그 고민은 잘 모르겠어. 조금 더 구체적으로 말해줄래?", "risk": ""}

# --------------------
# 출력
# --------------------
if user_text:
    result = route_and_reply(user_text)
    st.markdown(f"<div class='bubble'><b>🔮 조언:</b> {result['advice']}<br><br><b>⚠️ 위험:</b> {result['risk']}</div>", unsafe_allow_html=True)
