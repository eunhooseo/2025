import os
import requests
import streamlit as st
from urllib.parse import quote
from typing import Dict, List, Tuple, Optional

# =============================
# 설정
# =============================
st.set_page_config(page_title="무드 기반 영화/드라마 추천", layout="wide")

# 다크 테마 + 초록 포인트 (넷플릭스/티빙 무드)
st.markdown(
    """
    <style>
      :root { --accent: #20e37b; }
      .block-container { padding-top: 1rem; }
      body { background: #0a0a0a; color: #e5e5e5; }
      h1,h2,h3,h4,h5 { color: var(--accent); }
      .green { color: var(--accent); }
      .pill { display:inline-block; padding:4px 10px; border-radius:999px; background:#111; color:#bfffdc; margin-right:6px; border:1px solid #1e1e1e }
      .card { background:#0f0f0f; border:1px solid #1a1a1a; border-radius:16px; padding:14px; }
      .card:hover { border-color:#2a2a2a }
      .provider { display:inline-block; padding:4px 8px; border-radius:10px; background:#111; border:1px solid #1f1f1f; margin-right:6px; margin-bottom:6px; }
      .rating-badge { background:#111; border:1px solid #1f1f1f; padding:6px 10px; border-radius:10px; display:inline-block; margin-right:6px; }
      .stButton>button { background: var(--accent); color:#04140b; border:0; border-radius:12px; font-weight:700; padding: 0.6rem 1rem; }
      .stMultiSelect>div>div, .stSelectbox>div>div, .stRadio>div { background:#0f0f0f; border:1px solid #1a1a1a; border-radius:12px; }
      .small { font-size: 0.9rem; color: #cfcfcf; }
      .tiny { font-size: 0.8rem; color: #a5a5a5; }
      a { color: #8af7bf; text-decoration: none; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🎬 무드 기반 영화/드라마 추천")
st.caption("오늘의 기분 · 장르 · 작품 느낌으로 딱 맞는 OTT 콘텐츠 찾기 — 검정 & 초록 테마")

# =============================
# API 키 입력 (TMDB)
# =============================
DEFAULT_LANG = "ko-KR"
IMAGE_BASE = "https://image.tmdb.org/t/p/w500"
TMDB_KEY = st.secrets.get("TMDB_API_KEY") or os.environ.get("TMDB_API_KEY")
if not TMDB_KEY:
    TMDB_KEY = st.text_input("TMDB API Key 입력", type="password")

@st.cache_data(show_spinner=False, ttl=60 * 60)
def tmdb(path: str, params: Dict=None):
    if not TMDB_KEY:
        return None
    url = f"https://api.themoviedb.org/3{path}"
    q = {"api_key": TMDB_KEY, "language": DEFAULT_LANG}
    if params:
        q.update(params)
    r = requests.get(url, params=q, timeout=15)
    r.raise_for_status()
    return r.json()

# =============================
# 장르/키워드 맵
# =============================
# TMDB 장르 ID (ko)
@st.cache_data(show_spinner=False, ttl=24*3600)
def get_genre_map() -> Tuple[Dict[str,int], Dict[str,int]]:
    mg = tmdb("/genre/movie/list") or {"genres": []}
    tg = tmdb("/genre/tv/list") or {"genres": []}
    movie_map = {g["name"]: g["id"] for g in mg.get("genres", [])}
    tv_map    = {g["name"]: g["id"] for g in tg.get("genres", [])}
    # 한국어 장르 alias 추가
    alias = {
        "로맨스": "Romance", "코미디": "Comedy", "액션": "Action", "스릴러": "Thriller",
        "SF": "Science Fiction", "드라마": "Drama", "애니메이션": "Animation",
        "가족": "Family", "범죄": "Crime", "모험": "Adventure", "공포": "Horror"
    }
    movie_map_ko = {}
    for k,v in movie_map.items():
        movie_map_ko[k] = v
    for ko,en in alias.items():
        if en in movie_map:
            movie_map_ko[ko] = movie_map[en]
    tv_map_ko = {}
    for k,v in tv_map.items():
        tv_map_ko[k] = v
    for ko,en in alias.items():
        if en in tv_map:
            tv_map_ko[ko] = tv_map[en]
    return movie_map_ko, tv_map_ko

MOVIE_GENRES, TV_GENRES = get_genre_map()

MOODS = [
    "즐거운","설레는","감동적인","화나는","따뜻한","어두운","신나는","진지한","희망적인","짜릿한",
    "여운있는","따끈한","몽환적인","유쾌한","긴장되는","스릴넘치는"
]
FEELS = ["가볍게","진지하게","감동적으로","웅장하게","밝게","신비롭게","잔잔하게","강렬하게"]

# 무드/느낌 → TMDB 키워드 후보 (간단 매핑)
MOOD_KEYWORDS = {
    "감동적인": [6278, 14643],       # touching, inspirational
    "진지한":   [9672, 180547],      # serious, bleak
    "유쾌한":   [1721, 9715],        # humorous, feel-good
    "스릴넘치는":[9717, 6075],       # suspense, thriller
    "잔잔하게": [14644, 4565],       # heartwarming, slice of life
    "강렬하게": [196451, 180956],    # intense, brutal
    "밝게":     [196083, 14967],     # light-hearted, cheerful
    "신나는":   [9719, 616],         # exciting, adventure
    "어두운":   [180547, 9716],      # bleak, dark comedy
}

# =============================
# 검색/발견 유틸
# =============================

def discover(kind: str, genre_id: Optional[int], keyword_ids: List[int], mood_weights: int, sort_by: str, page: int=1):
    """kind: 'movie' | 'tv'"""
    params = {
        "sort_by": sort_by,
        "with_watch_monetization_types": "flatrate|free|ads|rent|buy",
        "include_adult": False,
        "region": "KR",
        "page": page,
    }
    if genre_id:
        params["with_genres"] = genre_id
    if keyword_ids:
        params["with_keywords"] = ",".join(map(str, keyword_ids))
    return tmdb(f"/discover/{kind}", params)

@st.cache_data(show_spinner=False, ttl=3600)
def get_details(kind: str, _id: int):
    return tmdb(f"/{kind}/{_id}", {"append_to_response": "reviews,watch/providers"})

@st.cache_data(show_spinner=False, ttl=3600)
def get_providers_kr(item: dict) -> List[str]:
    prov = item.get("watch/providers", {}).get("results", {}).get("KR", {})
    names = []
    for k in ["flatrate","ads","free","rent","buy"]:
        for p in prov.get(k, []) or []:
            if p.get("provider_name") and p["provider_name"] not in names:
                names.append(p["provider_name"])    
    return names

# 위키 시청률 파서 (베스트 에포트)
@st.cache_data(show_spinner=False, ttl=24*3600)
def get_tv_ratings_kor(title: str) -> Optional[str]:
    """ko 위키 문서에서 '시청률' 표를 텍스트로 요약 (실패 시 None)"""
    try:
        # 문서 찾기
        url = (
            "https://ko.wikipedia.org/w/api.php?action=query&list=search&srprop=snippet&format=json&utf8=1&srsearch="
            + quote(title)
        )
        r = requests.get(url, timeout=10)
        page = r.json()["query"]["search"][0]
        pageid = page["pageid"]
        # 위키텍스트 파싱
        parse = requests.get(
            f"https://ko.wikipedia.org/w/api.php?action=parse&pageid={pageid}&prop=wikitext&format=json&utf8=1",
            timeout=10,
        ).json()
        wikitext = parse.get("parse", {}).get("wikitext", {}).get("*", "")
        if "시청률" not in wikitext:
            return None
        # 간단 추출: '시청률' 섹션 이후 표의 최고/평균 키워드 추정
        text = wikitext.split("시청률", 1)[-1]
        # 최고/최저/평균 키워드 라인 찾기
        best = None
        avg = None
        for line in text.splitlines():
            if "최고" in line and "%" in line and not best:
                best = line
            if ("평균" in line or "전국" in line) and "%" in line and not avg:
                avg = line
            if best and avg:
                break
        summary = []
        if avg:
            summary.append("평균 " + ''.join(ch for ch in avg if ch in "0123456789.%()한국전국시청률최고평균 " ).strip())
        if best:
            summary.append("최고 " + ''.join(ch for ch in best if ch in "0123456789.%()한국전국시청률최고평균 " ).strip())
        return " · ".join(summary) if summary else None
    except Exception:
        return None

# =============================
# 사이드바 - 필터
# =============================
with st.sidebar:
    st.header("필터")
    mood_sel = st.multiselect("오늘의 기분 (최대 5개)", MOODS, max_selections=5)
    feel_sel = st.selectbox("작품 느낌", FEELS, index=0)

    # 장르 선택
    col1, col2 = st.columns(2)
    with col1:
        movie_genre_name = st.selectbox("영화 장르", options=["(전체)"] + list(MOVIE_GENRES.keys()))
    with col2:
        tv_genre_name = st.selectbox("드라마 장르", options=["(전체)"] + list(TV_GENRES.keys()))

    sort_label = st.radio("정렬", ["인기순", "평점순"], horizontal=True)
    sort_by_movie = "popularity.desc" if sort_label == "인기순" else "vote_average.desc"
    sort_by_tv = sort_by_movie

    st.markdown("### OTT 필터 (표시용)")
    ott_filters = st.multiselect(
        "관심 OTT",
        ["Netflix","TVING","Disney Plus","Wavve","Coupang Play","Prime Video","Apple TV+"],
    )

# 키워드 구성
kw = []
for m in mood_sel:
    kw.extend(MOOD_KEYWORDS.get(m, []))
for f in FEELS:
    if f == feel_sel:
        kw.extend(MOOD_KEYWORDS.get(f, []))
kw = list(dict.fromkeys(kw))  # 중복 제거

movie_genre_id = MOVIE_GENRES.get(movie_genre_name) if movie_genre_name != "(전체)" else None
tv_genre_id = TV_GENRES.get(tv_genre_name) if tv_genre_name != "(전체)" else None

# =============================
# 결과 조회
# =============================
colA, colB = st.columns([1,1])

with colA:
    st.subheader("📽 영화 추천")
    if TMDB_KEY:
        mres = discover("movie", movie_genre_id, kw, 1, sort_by_movie, page=1) or {"results":[]}
        movies = mres.get("results", [])[:12]
        if not movies:
            st.info("조건에 맞는 영화 결과가 적어요. 무드/장르를 넓혀보세요.")
        for item in movies:
            det = get_details("movie", item["id"]) or {}
            title = det.get("title") or item.get("title")
            year = (det.get("release_date") or "")[:4]
            poster = det.get("poster_path")
            vote = det.get("vote_average") or 0
            overview = det.get("overview") or "요약 정보가 없습니다."
            prod = ", ".join([c.get("name") for c in det.get("production_companies", [])[:3]])
            prov_names = get_providers_kr(det)
            # 필터 적용 (표시용)
            if ott_filters:
                if not any(any(f.lower() in p.lower() for f in ott_filters) for p in prov_names):
                    continue
            with st.container():
                cols = st.columns([1,2])
                with cols[0]:
                    if poster:
                        st.image(IMAGE_BASE + poster, use_column_width=True)
                    st.markdown(f"<span class='rating-badge'>⭐ {vote:.1f}</span>", unsafe_allow_html=True)
                with cols[1]:
                    st.markdown(f"<div class='card'><h3>{title} <span class='tiny'>({year})</span></h3>"
                                f"<div class='tiny'>제작사: {prod or '-'} </div>"
                                f"<p class='small'>{overview}</p>", unsafe_allow_html=True)
                    if prov_names:
                        st.markdown("**시청 가능 OTT:** " + " ".join(f"<span class='provider'>{p}</span>" for p in prov_names), unsafe_allow_html=True)
                    # 리뷰 (TMDB)
                    revs = det.get("reviews", {}).get("results", [])
                    if revs:
                        snippet = revs[0].get("content", "").strip().split("\n")[0][:220]
                        st.markdown(f"> {snippet}…")
                    st.markdown("</div>", unsafe_allow_html=True)
                    st.divider()
    else:
        st.warning("TMDB API Key를 입력하면 영화 추천을 보여드려요.")

with colB:
    st.subheader("📺 드라마 추천")
    if TMDB_KEY:
        tres = discover("tv", tv_genre_id, kw, 1, sort_by_tv, page=1) or {"results":[]}
        tvs = tres.get("results", [])[:12]
        if not tvs:
            st.info("조건에 맞는 드라마 결과가 적어요. 무드/장르를 넓혀보세요.")
        for item in tvs:
            det = get_details("tv", item["id"]) or {}
            title = det.get("name") or item.get("name")
            year = (det.get("first_air_date") or "")[:4]
            poster = det.get("poster_path")
            vote = det.get("vote_average") or 0
            overview = det.get("overview") or "요약 정보가 없습니다."
            networks = ", ".join([n.get("name") for n in det.get("networks", [])])
            prov_names = get_providers_kr(det)
            ratings_text = get_tv_ratings_kor(title)
            if ott_filters:
                if not any(any(f.lower() in p.lower() for f in ott_filters) for p in prov_names):
                    continue
            with st.container():
                cols = st.columns([1,2])
                with cols[0]:
                    if poster:
                        st.image(IMAGE_BASE + poster, use_column_width=True)
                    st.markdown(f"<span class='rating-badge'>⭐ {vote:.1f}</span>", unsafe_allow_html=True)
                with cols[1]:
                    st.markdown(f"<div class='card'><h3>{title} <span class='tiny'>({year})</span></h3>"
                                f"<div class='tiny'>방송사/네트워크: {networks or '-'} </div>"
                                f"<p class='small'>{overview}</p>", unsafe_allow_html=True)
                    if ratings_text:
                        st.markdown(f"**시청률:** {ratings_text}")
                    if prov_names:
                        st.markdown("**시청 가능 OTT:** " + " ".join(f"<span class='provider'>{p}</span>" for p in prov_names), unsafe_allow_html=True)
                    # 리뷰 (TMDB)
                    revs = det.get("reviews", {}).get("results", [])
                    if revs:
                        snippet = revs[0].get("content", "").strip().split("\n")[0][:220]
                        st.markdown(f"> {snippet}…")
                    st.markdown("</div>", unsafe_allow_html=True)
                    st.divider()
    else:
        st.warning("TMDB API Key를 입력하면 드라마 추천을 보여드려요.")

st.caption("데이터 출처: TMDB API, (드라마 시청률은 한국어 위키백과에서 가능할 때만 일부 추출 — 정확도는 문서 구조에 따라 달라질 수 있어요)")
