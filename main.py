# app.py
import streamlit as st

st.set_page_config(page_title="MBTI 음악 추천", layout="wide")

# --- CSS: 초록 테마 + 애플 시스템 글꼴 느낌 ---
css = """
/* 시스템 폰트 스택(맥에서는 애플 글꼴 사용) */
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700;900&display=swap');
html, body, [data-testid="stAppViewContainer"] {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Apple SD Gothic Neo", "Noto Sans KR", sans-serif;
  background-color: #E9F9EF;
  color: #1F2D2D;
}
.header {
  background: linear-gradient(90deg, #2ECC71, #1ABC60);
  color: white;
  padding: 22px;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(27, 188, 155, 0.12);
}
.playlist-card {
  background: #FFFFFF;
  border-radius: 12px;
  padding: 14px;
  box-shadow: 0 6px 18px rgba(31,45,45,0.06);
  margin-bottom: 12px;
}
.btn {
  background: linear-gradient(90deg,#1ABC60,#2ECC71);
  color: #fff !important;
  padding: 8px 14px;
  border-radius: 10px;
  font-weight: 700;
}
.small-muted { color: #6B8E6B; font-size:0.9rem; }
"""

st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

# --- 헤더 ---
st.markdown('<div class="header"><h1 style="margin:0">MBTI 음악 추천</h1><div class="small-muted">초록 테마 · 애플 시스템 글꼴 느낌</div></div>', unsafe_allow_html=True)

st.sidebar.title("설정")
mbti = st.sidebar.selectbox("내 MBTI 선택", ["INFP","ENFP","INTP","ENTP","ISFP","ESFP","ISTJ","ISFJ","INTJ","INFJ","ESTJ","ESFJ","ENTJ","ENFJ","ISTP","ESTP"])
mood = st.sidebar.selectbox("무드 필터", ["전체","차분한", "잔잔한", "업템포", "신나는"])

# --- MBTI 프리셋 플레이리스트(예시) ---
# 실제 서비스는 Spotify API로 플레이리스트 ID를 불러와서 연결하면 됨.
playlists = {
    "INFP": [
        {"title":"INFP - Dreamy Indie", "reason":"잔잔한 감성/포근한 보컬 중심", "embed":"https://open.spotify.com/embed/playlist/37i9dQZF1DX2sUQwD7tbmL"},
        {"title":"INFP - Acoustic Evenings", "reason":"어쿠스틱/조용한 밤에 좋음", "embed":"https://open.spotify.com/embed/playlist/37i9dQZF1DWYF8xQ8v2FN2"}
    ],
    "ENFP": [
        {"title":"ENFP - Bright Indie Pop", "reason":"활기차고 밝은 멜로디", "embed":"https://open.spotify.com/embed/playlist/37i9dQZF1DX5Ozry5U6G0H"},
        {"title":"ENFP - Upbeat Mix", "reason":"에너제틱한 리듬", "embed":"https://open.spotify.com/embed/playlist/37i9dQZF1DWT6MhXz0jw61"}
    ],
    # ... 나머지 MBTI도 같은 형식으로 추가 가능
}

st.markdown(f"## {mbti}님을 위한 추천 플레이리스트")
cols = st.columns([1,1,1])

items = playlists.get(mbti, [])
if not items:
    st.info("아직 해당 MBTI의 플레이리스트가 등록되지 않았어요. 기본 추천을 보여줄게요.")
    # 기본 추천 샘플
    items = [
        {"title":"Chill Vibes", "reason":"편안한 분위기", "embed":"https://open.spotify.com/embed/playlist/37i9dQZF1DX4WYpdgoIcn6"}
    ]

for i, pl in enumerate(items):
    with cols[i % 3]:
        st.markdown(f'<div class="playlist-card"><h3 style="margin:6px 0">{pl["title"]}</h3><div class="small-muted">{pl["reason"]}</div></div>', unsafe_allow_html=True)
        # Spotify 임베드
        st.markdown(f'<iframe src="{pl["embed"]}" width="100%" height="80" frameborder="0" allowtransparency="true" allow="encrypted-media"></iframe>', unsafe_allow_html=True)

st.markdown("---")
st.markdown("앱 데모는 간단한 프리셋 기반이야. 실제로는 Spotify API로 플레이리스트/트랙 정보를 가져오고, 사용자 청취 기록을 반영하면 개인화된 추천 가능!")

# 하단: 다음 단계 안내
st.info("다음으로 원하면 Spotify API 연동, 사용자별 추천(협업필터링/임베딩) 또는 플레이리스트 직접 업로드 기능을 만들어줄게. 어떤걸 먼저 할래?")
