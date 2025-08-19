import streamlit as st
import requests
import datetime
from xml.etree import ElementTree as ET

# ====================
# 설정
# ====================
st.set_page_config(page_title="뉴스 & 책 + 커뮤니티", layout="wide")
st.markdown(
    """
    <style>
    body { background: #fff; color: #222; font-family: 'Noto Sans KR'; }
    .title { color: #FF6600; font-size: 32px; font-weight: 700; }
    .card { background: #fafafa; border-radius: 12px; padding: 18px; margin-bottom: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
    .sub { color: #FF6600; font-weight: bold; margin-top: 10px; }
    .buy-link { color: #0066cc; font-size: 0.9rem; }
    </style>
    """, unsafe_allow_html=True
)
st.markdown("<div class='title'>📰 뉴스 & 📚 책 추천 + 블로그</div>", unsafe_allow_html=True)

# ====================
# API 키 설정
# ====================
NEWS_KEY = st.secrets.get("NEWS_API_KEY", "")
ALADIN_KEY = st.secrets.get("ALADIN_TTBKEY", "")

# ====================
# NewsAPI 가져오기
# ====================
@st.cache_data(ttl=600)
def get_news():
    if not NEWS_KEY:
        return []
    url = f"https://newsapi.org/v2/top-headlines?country=kr&apiKey={NEWS_KEY}&pageSize=5"
    r = requests.get(url)
    return r.json().get("articles", []) if r.status_code == 200 else []

# ====================
# 알라딘 책 검색 함수
# ====================
@st.cache_data(ttl=3600)
def search_aladin_books(query, max_results=3):
    if not ALADIN_KEY:
        return []
    api = "http://www.aladin.co.kr/ttb/api/ItemSearch.aspx"
    params = {
        "ttbkey": ALADIN_KEY,
        "Query": query,
        "QueryType": "Keyword",
        "MaxResults": max_results,
        "Output": "js",  # 또는 'json' 가능
        "SearchTarget": "Book",
        "Version": "20131101"
    }
    r = requests.get(api, params=params)
    if r.status_code != 200:
        return []
    data = r.json()
    return data.get("item", [])

# ====================
# 뉴스 + 책 표시
# ====================
news = get_news()
if news:
    for n in news:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown(f"### {n['title']}")
        if n.get("urlToImage"):
            st.image(n["urlToImage"], use_column_width=True)
        st.write(n.get("description", "요약 없음"))
        st.markdown(f"[기사 보기]({n['url']})", unsafe_allow_html=True)

        st.markdown("<div class='sub'>관련 책 (알라딘 기준)</div>", unsafe_allow_html=True)
        books = search_aladin_books(n['title'])
        if books:
            for b in books:
                st.markdown(f"**{b.get('title')}** — {b.get('author')}")
                if b.get("cover"):
                    st.image(b["cover"], width=80)
                buy_link = b.get("link")
                if buy_link:
                    st.markdown(f"<div class='buy-link'>[구매하기 (알라딘)]({buy_link})</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

else:
    st.info("NewsAPI 키를 설정하면 최신 뉴스를 보여드립니다.")

# ====================
# 커뮤니티 글쓰기
# ====================
st.markdown("<div class='title'>✍️ 내 글 쓰기</div>", unsafe_allow_html=True)
if "posts" not in st.session_state:
    st.session_state["posts"] = []

with st.form("post_form"):
    title = st.text_input("글 제목")
    content = st.text_area("내용 (마크다운 지원)")
    visibility = st.radio("공개 여부", ["공개", "비공개"])
    submitted = st.form_submit_button("등록")
    if submitted and title and content:
        st.session_state["posts"].append({
            "title": title,
            "content": content,
            "visibility": visibility,
            "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        })
        st.success("등록 완료!")

st.markdown("<div class='title'>🌍 사용자 글</div>", unsafe_allow_html=True)
public_posts = [p for p in st.session_state["posts"] if p["visibility"] == "공개"]
if not public_posts:
    st.info("공개된 글이 없습니다. 첫 글을 작성해보세요!")
else:
    for p in reversed(public_posts):
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown(f"### {p['title']}")
        st.markdown(p['content'])
        st.caption(p['time'])
        st.markdown("</div>", unsafe_allow_html=True)
