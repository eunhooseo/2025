streamlit==1.38.0
pandas==2.2.2
numpy==1.26.4
matplotlib==3.9.2
plotly==5.24.0
scikit-learn==1.5.1

import streamlit as st
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

st.set_page_config(page_title="MBTI 분위기 추천", layout="wide")

# 모의 장소 데이터(간단)
places = pd.DataFrame([
    {"id":1, "name":"달빛카페", "lat":37.5, "lon":127.0, "reviews":["조용하고 조명이 부드러워서 독서하기 좋아요","작은 창가 자리 추천"]},
    {"id":2, "name":"햇살 브런치", "lat":37.51, "lon":127.01, "reviews":["음악이 활기차고 인테리어가 화사함","테라스 자리 느낌 좋아요"]},
    {"id":3, "name":"미니멀 테이블", "lat":37.49, "lon":127.02, "reviews":["깔끔하고 조용한 분위기","직장인 점심에 적당"]},
])

mbti_presets = {
    "INFP": "아늑한 조명 창가 감성 차분한 음악",
    "ENFP": "활기찬 음악 밝은 인테리어 테라스",
    "INTJ": "미니멀 깔끔 집중하기 좋은 조용함",
}

def text_to_vec(texts, vocab=None):
    vec = CountVectorizer(vocabulary=vocab).fit_transform(texts)
    return vec.toarray(), CountVectorizer(vocabulary=vocab).vocabulary_

# 사전(간단한 분위기 키워드)
vocab = ["조용","조명","창가","아늑","활기","테라스","밝","깔끔","집중","음악"]

# 장소 분위기 벡터
place_texts = [" ".join(r) for r in places["reviews"]]
place_vecs, _ = text_to_vec(place_texts, vocab=vocab)

st.sidebar.title("설정")
user_mbti = st.sidebar.selectbox("내 MBTI", list(mbti_presets.keys()))
radius_km = st.sidebar.slider("반경(km)", 1, 20, 5)

# MBTI 프리셋 -> 벡터
mbti_vec, _ = text_to_vec([mbti_presets[user_mbti]], vocab=vocab)

sims = cosine_similarity(mbti_vec, place_vecs)[0]
places["score"] = sims
places = places.sort_values("score", ascending=False)

st.markdown(f"### 추천 결과 — {user_mbti}님에게 어울리는 분위기")
for _, row in places.iterrows():
    st.markdown(f"**{row['name']}** — 매칭 점수: {row['score']:.2f}")
    st.info(", ".join(row["reviews"]))
