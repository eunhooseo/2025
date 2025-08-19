import streamlit as st
import random

# --------------------
# 페이지 설정 + 전체 어두운 배경
# --------------------
st.set_page_config(page_title="현실적 조언 마법사", page_icon="🧙‍♂️", layout="centered")

st.markdown("""
<style>
body {
    background-color: #0a0f2c;
    color: #e0e0e0;
    font-family: 'Trebuchet MS', sans-serif;
}
.stButton>button {
    background-color: #5c4fff;
    color: white;
    height: 50px;
    width: 100%;
    font-size: 18px;
    border-radius: 10px;
    margin-top: 20px;
}
.bubble {
    background: rgba(255, 255, 255, 0.1);
    padding: 20px;
    border-radius: 12px;
    margin-top: 20px;
}
input, textarea {
    background-color: #1c1c3c;
    color: #e0e0e0;
    border: 1px solid #5c4fff;
    border-radius: 8px;
    padding: 10px;
}
</style>
""", unsafe_allow_html=True)

st.title("🧙 현실적 조언 마법사")
st.subheader("고민을 입력하고 버튼 하나로 점지 받아보자 ✨")

# --------------------
# 고민 입력
# --------------------
user_text = st.text_area("💬 고민을 적어주세요", placeholder="예: 새벽 3시인데 불닭 먹어도 될까?")

# --------------------
# 고민 유형별 조언 함수
# --------------------
def advise_food(text):
    return "늦은 밤 매운 음식은 피부에 안 좋아. 체중도 조금 늘 수 있어."

def advise_study(text):
    return "25분 집중 + 5분 휴식 포모도로 방법 추천! 작은 목표부터 끝내자."

def advise_love(text):
    return "솔직하게 작은 제안부터 시작해봐. 반응 없으면 속도 줄이기."

def advise_weather(text):
    return "오늘은 비가 올 수 있어. 우산 챙기고, 옷은 따뜻하게 입어!"

def advise_fashion(text):
    if "빨간 블라우스" in text:
        return "빨간 블라우스엔 검정 바지나 흰색 바지가 제일 무난해."
    elif "청바지" in text:
        return "청바지엔 흰색이나 파스텔톤 상의가 잘 어울려."
    else:
        return "무난한 색(검정, 흰색, 회색)이면 대부분 잘 어울려."

def advise_late(text):
    return "지금 남은 시간으로 전력질주하면 도착 가능. 천천히 가면 늦을 수 있어."

def advise_fortune(text):
    fortunes = [
        "오늘은 새로운 시작을 해보기 좋은 날!",
        "조금 조심하는 게 좋아, 특히 사람 사이에서.",
        "뜻밖의 행운이 찾아올 수도 있어.",
        "작은 실수를 크게 만들지 않도록 주의!"
    ]
    return random.choice(fortunes)

# --------------------
# 라우팅 함수
# --------------------
def route_and_reply(text: str):
    text = text.lower()
    if any(word in text for word in ["불닭", "야식", "라면"]):
        return advise_food(text)
    elif any(word in text for word in ["공부", "시험"]):
        return advise_study(text)
    elif any(word in text for word in ["좋아하는 사람", "연애", "고백"]):
        return advise_love(text)
    elif any(word in text for word in ["날씨", "비", "우산"]):
        return advise_weather(text)
    elif any(word in text for word in ["바지", "옷", "블라우스", "코디"]):
        return advise_fashion(text)
    elif any(word in text for word in ["학교", "지각", "늦"]):
        return advise_late(text)
    elif any(word in text for word in ["운세", "점"]):
        return advise_fortune(text)
    else:
        return "마법사가 그 고민은 아직 잘 모르겠어. 조금 더 구체적으로 말해줘!"

# --------------------
# 버튼 클릭 시 답변
# --------------------
if st.button("점지 받기 ✨"):
    if user_text.strip():
        advice = route_and_reply(user_text)
        st.markdown(f"<div class='bubble'><b>🔮 조언:</b> {advice}</div>", unsafe_allow_html=True)
    else:
        st.warning("고민을 입력해야 점지를 받을 수 있어!")
