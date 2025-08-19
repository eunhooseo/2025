import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="책 추천 & 커뮤니티", layout="wide")

# 📚 추천 도서 데이터 (예시: CSV 대신 코드에 직접 넣음)
books = pd.DataFrame([
    {"제목": "정의란 무엇인가", "저자": "마이클 샌델", 
     "이미지": "https://image.aladin.co.kr/product/37/4/cover.jpg",
     "구매링크": "https://www.aladin.co.kr/shop/wproduct.aspx?ItemId=374"},
    {"제목": "넛지", "저자": "리처드 세일러", 
     "이미지": "https://image.aladin.co.kr/product/500/200/cover.jpg",
     "구매링크": "https://www.aladin.co.kr/shop/wproduct.aspx?ItemId=200"},
])

# 사용자 글 저장소 (임시: 세션)
if "posts" not in st.session_state:
    st.session_state["posts"] = []

# 🎨 제목
st.markdown(
    "<h1 style='color:#FF6600;'>📚 책 추천 & ✍️ 나의 생각</h1>", 
    unsafe_allow_html=True
)

# ==============================
# 📌 책 추천
# ==============================
st.subheader("오늘의 추천 도서")
for _, row in books.iterrows():
    col1, col2 = st.columns([1, 3])
    with col1:
        st.image(row["이미지"], width=100)
    with col2:
        st.write(f"**{row['제목']}** — {row['저자']}")
        st.markdown(f"[구매하기]({row['구매링크']})")

st.markdown("---")

# ==============================
# ✍️ 사용자 글쓰기
# ==============================
st.subheader("내 생각 남기기")

title = st.text_input("글 제목")
content = st.text_area("내용을 작성하세요")
is_public = st.checkbox("공개하기", value=True)

if st.button("등록"):
    new_post = {
        "제목": title,
        "내용": content,
        "공개": is_public,
        "작성일": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    st.session_state["posts"].append(new_post)
    st.success("글이 등록되었습니다!")

st.markdown("---")

# ==============================
# 🌍 공개 글 모아보기
# ==============================
st.subheader("커뮤니티 글")

for post in reversed(st.session_state["posts"]):
    if post["공개"]:
        with st.container():
            st.markdown(f"### {post['제목']}")
            st.write(post["내용"])
            st.caption(f"작성일: {post['작성일']}")
            st.markdown("---")
