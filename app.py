# app.py
# -*- coding: utf-8 -*-
import re
import math
from datetime import datetime, timedelta

import streamlit as st

# ---------- 기본 설정 ----------
st.set_page_config(
    page_title="현실주의 마법사",
    page_icon="🧙‍♂️",
    layout="centered"
)

# ---------- 다크/남색 무드 CSS ----------
CSS = """
<style>
/* 전체 배경: 남색 그라디언트 + 은하 느낌 점 */
.stApp {
  background: radial-gradient(1200px 800px at 20% 10%, rgba(60,60,120,0.35) 0%, rgba(8,10,25,1) 60%),
              radial-gradient(1000px 600px at 80% 20%, rgba(10,30,80,0.25) 0%, rgba(8,10,25,1) 70%),
              #080a19;
  color: #E6E9F2;
}

/* 별 */
.stApp::before {
  content: "";
  position: fixed; inset: 0;
  background-image:
    radial-gradient(2px 2px at 20% 30%, rgba(255,255,255,0.6) 50%, transparent 51%),
    radial-gradient(1.5px 1.5px at 65% 15%, rgba(255,255,255,0.6) 50%, transparent 51%),
    radial-gradient(1.8px 1.8px at 80% 70%, rgba(255,255,255,0.5) 50%, transparent 51%),
    radial-gradient(1.1px 1.1px at 35% 80%, rgba(255,255,255,0.5) 50%, transparent 51%),
    radial-gradient(1.3px 1.3px at 50% 55%, rgba(255,255,255,0.4) 50%, transparent 51%);
  pointer-events:none;
  opacity: .7;
}

/* 카드/박스 느낌 */
.block {
  background: rgba(20,22,40,0.65);
  border: 1px solid rgba(120,130,180,0.25);
  border-radius: 16px;
  padding: 20px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.35);
}

/* 버튼, 입력 */
button, .stButton>button {
  border-radius: 10px !important;
}
textarea, input, select {
  background: rgba(15,18,35,0.7) !important;
  color: #E6E9F2 !important;
  border: 1px solid rgba(120,130,180,0.35) !important;
}

/* 작은 캡션 */
.small {
  font-size: 0.9rem;
  color: #AAB0C6;
}
.tiny {
  font-size: 0.8rem;
  color: #9aa1ba;
}

/* 헤더 내부 정렬 */
.header-wrap {
  display: grid;
  grid-template-columns: 120px 1fr;
  gap: 18px;
  align-items: center;
  margin-top: 14px;
}

/* SVG 색 */
svg .line { stroke: #A6B6FF; }
svg .fill { fill: #5E6B9E; }
svg .cauldron { fill: #1a2040; stroke: #7b84c6; }
svg .bubble { fill: #7bb8ff; opacity:.85; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ---------- 헤더(마법사+항아리 SVG) ----------
WIZARD_SVG = """
<svg width="120" height="120" viewBox="0 0 120 120" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <!-- 모자 -->
  <path class="fill" d="M60 10 L90 50 L30 50 Z" opacity="0.9"/>
  <circle class="bubble" cx="82" cy="20" r="2.5"/>
  <circle class="bubble" cx="75" cy="14" r="1.8"/>
  <!-- 얼굴 없는 로브 노인 실루엣 -->
  <path class="fill" d="M45 50 Q60 65 75 50 Q80 75 65 92 Q60 98 55 92 Q40 75 45 50 Z" opacity="0.85"/>
  <!-- 마술항아리 -->
  <ellipse class="cauldron" cx="60" cy="98" rx="28" ry="12"/>
  <ellipse class="cauldron" cx="60" cy="90" rx="24" ry="8"/>
  <!-- 국자 -->
  <path class="line" d="M85 68 C90 58, 96 55, 102 58" stroke-width="2"/>
  <circle class="bubble" cx="60" cy="84" r="2.8"/>
  <circle class="bubble" cx="68" cy="82" r="2.2"/>
</svg>
"""

st.markdown(
    f"""
<div class="header-wrap">
  <div>{WIZARD_SVG}</div>
  <div>
    <h1 style="margin-bottom:6px;">현실주의 마법사 🧙‍♂️</h1>
    <div class="small">신비한 항아리 속에서, 너의 상황을 <b>차갑게 계산</b>해서 말해주는 냉정한 조언가.</div>
  </div>
</div>
""",
    unsafe_allow_html=True
)

# ---------- 유틸: 포매팅 ----------
def fmt_kcal_to_kg(kcal: float) -> float:
    # 1 kg 지방 ≈ 7,700 kcal 가정 (대략적 추정)
    return kcal / 7700.0

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def extract_minutes(text):
    # "10분 남았는데 지금 7분밖에" 같은 문장에서 숫자 두 개 뽑기
    nums = list(map(int, re.findall(r'(\d+)\s*분', text)))
    if len(nums) >= 2:
        # 보통 "원래 X분, 지금 Y분" 순서로 들어온다고 가정
        return nums[0], nums[1]
    return None, None

def has_any(text, keywords):
    return any(k in text for k in keywords)

# ---------- 계산 모듈 1: 야식·라면·매운 음식 ----------
def advise_spicy_late_night(text):
    # 기본 한 봉지 kcal 추정
    base_kcal = 530  # 불닭볶음면 1봉 대략치 (브랜드/버전에 따라 다름)
    add_egg = has_any(text, ["계란", "달걀", "egg"])
    add_cheese = has_any(text, ["치즈", "cheese"])
    add_rice = has_any(text, ["밥", "공기밥", "rice"])

    extras_kcal = 0
    if add_egg: extras_kcal += 70
    if add_cheese: extras_kcal += 70
    if add_rice: extras_kcal += 210  # 작은 공기 가정

    total_kcal = base_kcal + extras_kcal
    est_gain_kg = fmt_kcal_to_kg(total_kcal)
    est_gain_g = est_gain_kg * 1000

    # 피부 관련: 과학적 확정X → 위험도 가이드(야식/수면교란/기름/당분)
    risk = 0.0
    # 늦은 시간 가중치
    now_h = datetime.now().hour
    if now_h >= 0 and now_h <= 5:
        risk += 0.3
    # 매운맛/기름/면류
    risk += 0.35
    # 추가 토핑
    if add_cheese: risk += 0.1
    if add_rice: risk += 0.05

    risk = clamp(risk, 0.05, 0.8)
    levels = [(0.15, "낮음"), (0.35, "보통"), (0.55, "약간 높음"), (0.75, "높음"), (1.1, "매우 높음")]
    skin_level = next(lbl for th, lbl in levels if risk <= th)

    # 대안 옵션 계산
    half_portion_kcal = total_kcal * 0.6  # 면 60%만
    glass_milk_kcal = 100  # 우유 200ml 대체 예시
    alt1_gain_g = fmt_kcal_to_kg(half_portion_kcal) * 1000
    alt2_gain_g = fmt_kcal_to_kg(glass_milk_kcal) * 1000

    return {
        "total_kcal": total_kcal,
        "gain_g": est_gain_g,
        "skin_level": skin_level,
        "half_kcal": half_portion_kcal,
        "half_gain_g": alt1_gain_g,
        "milk_gain_g": alt2_gain_g,
        "notes": [
            "여드름/트러블은 개인차가 큼. 야식·수면 부족·고지방/고정제/당분이 겹치면 악화 가능성↑.",
            "‘칼로리=체중’은 장기 평균의 단순화된 모델이야. 단기 수분변화(나트륨)로 내일 아침엔 더 무겁게 보일 수 있어.",
        ],
    }

# ---------- 계산 모듈 2: 지각/이동 속도 ----------
def advise_hurry(text):
    normal_min, left_min = extract_minutes(text)
    if not normal_min or not left_min:
        # 키워드는 있지만 숫자를 못 뽑았을 때의 기본값
        normal_min, left_min = 10, 7

    # 보행 속도 가정: 5 km/h
    walk_kmh = 5.0
    distance_km = walk_kmh * (normal_min / 60.0)
    required_kmh = distance_km / (left_min / 60.0)

    # 권장 행동 분기
    if required_kmh <= 6.0:
        plan = "빠른 걸음으로 가면 충분히 가능함. (파워워킹)"
        label = "가능"
    elif required_kmh <= 9.0:
        plan = "경보 수준으로 빠르게 + 30초 정도 가벼운 조깅 섞기."
        label = "애매하지만 가능"
    elif required_kmh <= 12.0:
        plan = "초반 3분 전력질주 후, 나머지 구간은 가볍게 유지. (호흡 관리)"
        label = "고통스럽지만 가능"
    else:
        plan = "현실적으로 힘듦. 바로 연락해서 양해 구하고, 다음부턴 3분 일찍 출발 루틴 만들기."
        label = "사실상 불가"

    # 페이스와 100m당 초 간단 환산
    pace_min_per_km = 60.0 / required_kmh
    sec_per_100m = (pace_min_per_km * 60) / 10.0

    return {
        "normal_min": normal_min,
        "left_min": left_min,
        "required_kmh": required_kmh,
        "pace_min_per_km": pace_min_per_km,
        "sec_per_100m": sec_per_100m,
        "plan": plan,
        "label": label
    }

# ---------- 계산 모듈 3: 학업/연애 현실 조언(룰기반) ----------
def advise_study(text):
    # 아주 짧고 실행가능하게
    tips = [
        "오늘 한도: ‘✕✕’만 한다 → 과제/개념/오답 중 하나만 택해 45분 집중 + 10분 휴식 × 2회.",
        "내일 점검: 오늘 푼 문제 중 3개만 다시 풀어 맞았는지 체크.",
        "막혔을 때: ‘내가 뭘 모르는지’ 한 줄로 쓰고, 그 문장에만 답을 찾기."
    ]
    return tips

def advise_love(text):
    # 상황 파악→선언/탐색→일정 제안 3스텝
    script = [
        "상황 파악(텍스트 2~3줄): 최근 대화 빈도·톤·응답속도를 메모.",
        "작게 던지기: ‘이번 주 수/목 중 30분 산책 어때?’ 같이 가벼운, yes/no로 답하기 쉬운 약속.",
        "한계선: 호응이 2회 연속 흐리면 마음 건강 위해 페이스 다운. 나를 좋아하는 사람을 내 시간으로 초대하자."
    ]
    return script

# ---------- 라우팅 ----------
def route_and_reply(text):
    t = text.strip().lower()

    spicy_kw = ["불닭", "라면", "매운", "자극", "야식"]
    late_kw = ["새벽", "밤", "3시", "2시", "4시"]
    skin_kw = ["피부", "여드름", "뾰루지", "트러블"]

    late_food = has_any(text, spicy_kw) or has_any(text, late_kw)
    skin_worry = has_any(text, skin_kw)

    rush_kw = ["남았", "지각", "늦", "뛰", "시간", "수업", "학교", "출근"]

    study_kw = ["학업", "공부", "성적", "시험", "모고", "내신", "수능"]
    love_kw = ["연애", "썸", "고백", "사귀", "데이트", "호감"]

    # 1) 늦은 시간 음식/피부
    if late_food or skin_worry:
        data = advise_spicy_late_night(text)
        st.subheader("🫠 야식 계산·현실 체크")
        st.markdown(
            f"""
<div class="block">
<b>예상 섭취 열량</b>: 약 <b>{int(data['total_kcal'])} kcal</b><br>
<b>이론상 체중 증가</b>: 약 <b>{data['gain_g']:.0f} g</b> (장기 평균 가정)<br>
<b>피부 트러블 위험도</b>: <b>{data['skin_level']}</b> (개인차 큼)
</div>
""",
            unsafe_allow_html=True
        )
        st.markdown("**대안 플랜**")
        st.markdown(
            f"- 면 60%만 먹기 → 약 **{int(data['half_kcal'])} kcal**, 예상 증량 **{data['half_gain_g']:.0f} g**\n"
            f"- 우유 200ml로 허기 달래기 → 예상 증량 **{data['milk_gain_g']:.0f} g**\n"
            f"- 먹는다면: 물 충분히 마시고, 면은 물 버리고 조리(나트륨↓), 취침 전 세안은 확실히."
        )
        with st.expander("참고 메모"):
            for n in data["notes"]:
                st.write("• " + n)
        return

    # 2) 지각/이동
    if has_any(text, rush_kw):
        data = advise_hurry(text)
        st.subheader("🏃 현실 속도 계산")
        st.markdown(
            f"""
<div class="block">
<b>원래 소요</b>: {data['normal_min']}분<br>
<b>남은 시간</b>: {data['left_min']}분<br>
<b>필요 속도</b>: <b>{data['required_kmh']:.1f} km/h</b> (100m당 {data['sec_per_100m']:.0f}초 페이스)<br>
<b>판정</b>: <b>{data['label']}</b> — {data['plan']}
</div>
""", unsafe_allow_html=True)
        st.caption("기본 보행 5 km/h 가정. 지형·신호등·가방 무게에 따라 체감 난이도는 크게 달라짐.")
        return

    # 3) 학업
    if has_any(text, study_kw):
        tips = advise_study(text)
        st.subheader("📚 학업: 오늘 당장 되는 것만")
        st.markdown('<div class="block">', unsafe_allow_html=True)
        for t in tips:
            st.write("• " + t)
        st.markdown('</div>', unsafe_allow_html=True)
        return

    # 4) 연애
    if has_any(text, love_kw):
        script = advise_love(text)
        st.subheader("💞 연애: 작은 신호 → 작게 시도")
        st.markdown('<div class="block">', unsafe_allow_html=True)
        for s in script:
            st.write("• " + s)
        st.markdown('</div>', unsafe_allow_html=True)
        return

    # 5) 기타: 기본 냉정 조언 템플릿
    st.subheader("🥶 기본 현실 점지")
    st.markdown(
        """
<div class="block">
1) <b>목표를 1문장</b>으로 줄여봐. (지금 당장 무엇?)<br>
2) <b>가장 짧은 버전</b>을 20분 안에 시작할 수 있게 쪼개.<br>
3) <b>실패 대비</b>: 망했을 때 손실을 어떻게 최소화할 건지 1줄로 써.<br>
4) 그다음, <b>타이머 20분</b> 켜고 시작. 끝나면 결과만 보고 다음 한 스텝 결정.
</div>
""",
        unsafe_allow_html=True
    )

# ---------- 사이드바 ----------
with st.sidebar:
    st.markdown("### 🔮 옵션")
    st.caption("계산 가정값을 네 상황에 맞게 살짝 조정할 수 있어.")
    # 칼로리 기준 조정(라면)
    base_kcal_user = st.slider("라면 1봉 칼로리 가정", 400, 700, 530, 10)
    # 전역 업데이트: 사용자가 조정하면 반영
    # (간단히 전역 변수처럼 사용)
    # 주의: 사용자가 본문에서 라면 키워드로 들어왔을 때만 실사용.
    # 편의상 monkey patch:
    def patched_advise_spicy_late_night(text):
        data = advise_spicy_late_night(text)
        # base만 바꿔 다시 계산
        spicy_kw = ["불닭", "라면", "매운", "자극", "야식", "ramen", "noodle"]
        add_egg = has_any(text, ["계란", "달걀", "egg"])
        add_cheese = has_any(text, ["치즈", "cheese"])
        add_rice = has_any(text, ["밥", "공기밥", "rice"])
        extras_kcal = (70 if add_egg else 0) + (70 if add_cheese else 0) + (210 if add_rice else 0)
        total_kcal = base_kcal_user + extras_kcal
        data['total_kcal'] = total_kcal
        data['gain_g'] = fmt_kcal_to_kg(total_kcal) * 1000
        data['half_kcal'] = total_kcal * 0.6
        data['half_gain_g'] = fmt_kcal_to_kg(data['half_kcal']) * 1000
        return data
    # 함수 바인딩 교체
    advise_spicy_late_night = patched_advise_spicy_late_night  # noqa

    # 걷기 속도 가정
    walk_kmh_user = st.slider("보통 걷기 속도 (km/h)", 3, 7, 5, 1)
    def patched_advise_hurry(text):
        normal_min, left_min = extract_minutes(text)
        if not normal_min or not left_min:
            normal_min, left_min = 10, 7
        distance_km = walk_kmh_user * (normal_min / 60.0)
        required_kmh = distance_km / (left_min / 60.0)
        if required_kmh <= 6.0:
            plan = "빠른 걸음으로 가면 충분히 가능함. (파워워킹)"
            label = "가능"
        elif required_kmh <= 9.0:
            plan = "경보 수준으로 빠르게 + 30초 조깅 섞기."
            label = "애매하지만 가능"
        elif required_kmh <= 12.0:
            plan = "초반 전력질주 후 유지. (호흡 관리)"
            label = "고통스럽지만 가능"
        else:
            plan = "현실적으로 힘듦. 바로 연락해서 양해 구하고, 다음부턴 3분 일찍 출발 루틴."
            label = "사실상 불가"
        pace_min_per_km = 60.0 / required_kmh
        sec_per_100m = (pace_min_per_km * 60) / 10.0
        return {
            "normal_min": normal_min,
            "left_min": left_min,
            "required_kmh": required_kmh,
            "pace_min_per_km": pace_min_per_km,
            "sec_per_100m": sec_per_100m,
            "plan": plan,
            "label": label
        }
    advise_hurry = patched_advise_hurry  # noqa

# ---------- 본문 입력 ----------
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    """
<div class="block">
<p class="small">예시: <i>“새벽 3시에 불닭볶음면 땡기는데 피부 망가질까?”</i> / 
<i>“원래 집→학교 10분인데 지금 7분 남음. 뛰면 가능?”</i> / 
<i>“수학 성적 올리고 싶은데 뭘 줄여야 해?”</i></p>
</div>
""",
    unsafe_allow_html=True
)

user_text = st.text_area("고민을 마법 항아리에 던져라 ✍️", height=120, placeholder="너의 현실을 적나라하게 써줘. 숫자가 있으면 더 좋아!")
go = st.button("점지 받기 ✨")

if go and user_text.strip():
    route_and_reply(user_text)
elif not user_text:
    st.caption("무엇이든 적어봐. 나는 감성 말고, ‘가능/불가/얼마나’로 답해줄게.")

# ---------- 푸터 ----------
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    """
<div class="tiny">
⚠️ 이 앱의 계산은 간단한 모델과 가정에 기반한 <b>현실 체크</b>야. 의학/영양/트레이닝의 전문적 진단이 아님.<br>
개인차가 크니 중요한 결정은 전문가와 상의해줘.
</div>
""",
    unsafe_allow_html=True
)
