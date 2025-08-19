import streamlit as st
import requests

# ==============================
# 🔑 API KEY 입력
# ==============================
# 방법 1: 여기에 직접 입력 (테스트용)
NEWS_API_KEY = "여기에_뉴스API키"
ALADIN_TTB_KEY = "여기에_알라딘_TTB키"

# 방법 2: secrets.toml 방식 (추천)
# NEWS_API_KEY = st.secrets["NEWS_API_KEY"]
# ALADIN_TTB_KEY = st.secrets["ALADIN_TTBKEY"]


# ==============================
# 📌 함수: 뉴스 가져오기 (NewsAPI)
# ==============================
def get_news(query="한국", page_size=5):
    url = f"https://newsapi.org/v2/everything?q={query}&language=ko&pageSize={page_size}&apiKey={NEWS_API_KEY}"
    response = requests.get(url)
    data = response.json()
    return data.get("articles", [])


# ==============================
# 📌 함수: 책 추천 (알라딘 OpenAPI)
# ==============================
def get_books(query, max_results=3):
    url = (
        f"http://www.aladin.co.kr/ttb/api/ItemSearch.aspx?"
        f"ttbkey={ALADIN_TTB_KEY}&Query={query}&QueryType=Keyword"
        f"&MaxResults={max_results}&start=1&SearchTarget=Book&output=js&Version=20131101"
    )
    response = requests.get(url)
    data = response.json()
    return data.get("item", [])


# ==============================
# 🎨 Streamlit UI
# ==============================
st.set_page_config(page_title="뉴스 + 책 추천", layout="wide")

st.markdown(
    """
    <h1 style='color:#FF6600;'>📰 오늘의 뉴스 & 📚 관련 도서 추천</h1>
    <p>최신 뉴스를 보고, 관련된 책을 바로 찾아보세요.</p>
    """,
    unsafe_allow_html=True,
)

# 검색어 입력
query = st.text_input("검색할 키워드를 입력하세요 (예: 경제, 환경, 인공지능)", "경제")

if st.button("검색"):
    news_list = get_news(query=query, page_size=5)

    if not news_list:
        st.warning("뉴스를 불러오지 못했습니다. 키워드나 API 키를 확인해주세요.")
    else:
        for news in news_list:
            # 뉴스 카드
            with st.container():
                st.markdown(f"### 📰 {news['title']}")
                st.write(news.get("description", "내용 없음"))
                if news.get("urlToImage"):
                    st.image(news["urlToImage"], width=400)
                st.markdown(f"[👉 전체 기사 보기]({news['url']})")

                # 책 추천
                st.write("#### 📚 관련 책 추천")
                books = get_books(query)
                if books:
                    for book in books:
                        col1, col2 = st.columns([1, 3])
                        with col1:
                            st.image(book["cover"], width=100)
                        with col2:
                            st.write(f"**{book['title']}** ({book['author']})")
                            st.write(book.get("publisher", "출판사 정보 없음"))
                            st.markdown(f"[구매하기]({book['link']})")
                else:
                    st.info("관련 책을 찾을 수 없습니다.")
                st.markdown("---")
