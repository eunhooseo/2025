import streamlit as st

st.set_page_config(page_title="MBTI 커뮤니티", layout="wide")

css = """
/* Google Fonts : Noto Sans KR (대체) */
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&display=swap');

html, body, [data-testid="stAppViewContainer"] {
  font-family: 'Pretendard', 'Noto Sans KR', sans-serif;
  background: linear-gradient(135deg, #FFF6F4 0%, #FFF0EB 100%);
}

/* 헤더 스타일 */
.header {
  background: linear-gradient(135deg, #FF4D00, #FF8A3D);
  color: white;
  padding: 24px;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(255,77,0,0.15);
}

/* CTA 버튼 */
.css-cta-button {
  background: linear-gradient(90deg,#FF4D00,#FF8A3D);
  color: #fff !important;
  font-weight: 700;
  border-radius: 12px;
  padding: 10px 18px;
  box-shadow: 0 6px 16px rgba(255,77,0,0.18);
}

/* 채팅 버블(내 메시지 / 상대 메시지) */
.chat-bubble {
  border-radius: 14px;
  padding: 10px 12px;
  margin: 6px 0;
  display: inline-block;
}
.chat-me { background: #FF8A3D; color: white; font-weight: 600; }
.chat-other { background: #FFF; color: #212121; border: 1px solid #FFE7D9; }

/* MBTI 뱃지 */
.mbti-badge {
  background: linear-gradient(90deg,#FF4D00,#FFC857);
  color: white;
  padding: 6px 10px;
  border-radius: 999px;
  font-weight: 700;
  font-size: 0.9rem;
}
"""
st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

# 예시 UI
st.markdown('<div class="header"><h1>같은 MBTI 사람 찾기</h1></div>', unsafe_allow_html=True)
col1, col2 = st.columns([2,3])
with col1:
    st.markdown('<button class="css-cta-button">근처 찾기</button>', unsafe_allow_html=True)
with col2:
    st.markdown('<div class="mbti-badge">ENFP</div>', unsafe_allow_html=True)
