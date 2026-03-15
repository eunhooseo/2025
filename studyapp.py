import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import random

st.set_page_config(page_title="Study Manager", layout="wide")

# -----------------------------
# 테마 설정
# -----------------------------

st.sidebar.title("🎨 테마 설정")

bg_color = st.sidebar.color_picker("배경색", "#F5F5F5")
text_color = st.sidebar.color_picker("글씨 색", "#000000")

st.markdown(
    f"""
    <style>
    .stApp {{
        background-color: {bg_color};
        color: {text_color};
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# -----------------------------
# 캐릭터 선택
# -----------------------------

characters = ["🐰 Rabbit","🐱 Cat","🐻 Bear"]
character = st.sidebar.selectbox("캐릭터 선택", characters)

good_messages = [
"오늘 정말 잘했어!",
"꾸준함이 너의 무기야!",
"계속 이렇게만 가자!"
]

bad_messages = [
"오늘 조금 게을렀네!",
"내일은 더 집중하자!",
"포기하지 말자!"
]

# -----------------------------
# 세션 상태
# -----------------------------

if "todos" not in st.session_state:
    st.session_state.todos = []

if "memos" not in st.session_state:
    st.session_state.memos = []

if "calendar" not in st.session_state:
    st.session_state.calendar = []

if "books" not in st.session_state:
    st.session_state.books = []

if "study" not in st.session_state:
    st.session_state.study = []

if "page" not in st.session_state:
    st.session_state.page = "홈"

# -----------------------------
# 홈 화면
# -----------------------------

if st.session_state.page == "홈":

    today = datetime.datetime.now().date()

    target_date = st.date_input("목표 날짜")

    if target_date:
        dday = (target_date - today).days
        st.caption(f"🎯 D-Day : {dday}")

    st.markdown("##")
    st.markdown(f"# {character}")

    message = random.choice(good_messages)

    st.chat_message("assistant").write(message)

    st.markdown("---")

    col1,col2,col3,col4,col5 = st.columns(5)

    with col1:
        if st.button("✔️ ToDo"):
            st.session_state.page="ToDo"

    with col2:
        if st.button("📝 메모"):
            st.session_state.page="메모"

    with col3:
        if st.button("📅 일정"):
            st.session_state.page="일정"

    with col4:
        if st.button("📚 독서"):
            st.session_state.page="생기부 독서"

    with col5:
        if st.button("📊 통계"):
            st.session_state.page="공부 통계"

# -----------------------------
# ToDo
# -----------------------------

elif st.session_state.page == "ToDo":

    st.title("✔️ ToDo List")

    task = st.text_input("할 일 입력")

    if st.button("추가"):
        st.session_state.todos.append({
            "task":task,
            "done":False
        })

    for i,todo in enumerate(st.session_state.todos):

        done = st.checkbox(todo["task"],value=todo["done"],key=i)

        st.session_state.todos[i]["done"] = done

    if st.button("홈으로"):
        st.session_state.page="홈"

# -----------------------------
# 메모
# -----------------------------

elif st.session_state.page == "메모":

    st.title("📝 메모")

    title = st.text_input("제목")
    content = st.text_area("내용")

    if st.button("저장"):

        st.session_state.memos.append({
            "title":title,
            "content":content,
            "date":str(datetime.date.today())
        })

    for memo in st.session_state.memos[::-1]:

        col1,col2 = st.columns([4,1])

        with col1:
            st.subheader(memo["title"])

        with col2:
            st.caption(memo["date"])

        st.write(memo["content"])

    if st.button("홈으로"):
        st.session_state.page="홈"

# -----------------------------
# 일정 (달력)
# -----------------------------

elif st.session_state.page == "일정":

    st.title("📅 일정 관리")

    date = st.date_input("날짜")
    schedule = st.text_input("일정")

    if st.button("일정 추가"):

        st.session_state.calendar.append({
            "date":date,
            "schedule":schedule
        })

    df = pd.DataFrame(st.session_state.calendar)

    if not df.empty:

        st.subheader("이번 달 일정")

        calendar_df = df.copy()
        calendar_df["date"] = pd.to_datetime(calendar_df["date"])

        st.dataframe(calendar_df)

    if st.button("홈으로"):
        st.session_state.page="홈"

# -----------------------------
# 생기부 독서
# -----------------------------

elif st.session_state.page == "생기부 독서":

    st.title("📚 생기부 독서 기록")

    book = st.text_input("책 제목")
    subject = st.text_input("과목")
    thought = st.text_area("느낀 점")

    if st.button("기록"):

        st.session_state.books.append({
            "title":book,
            "subject":subject,
            "thought":thought,
            "date":str(datetime.date.today())
        })

    for b in st.session_state.books[::-1]:

        col1,col2 = st.columns([4,1])

        with col1:
            st.subheader(b["title"])

        with col2:
            st.caption(b["date"])

        st.write("과목:",b["subject"])
        st.write(b["thought"])

    if st.button("홈으로"):
        st.session_state.page="홈"

# -----------------------------
# 공부 통계
# -----------------------------

elif st.session_state.page == "공부 통계":

    st.title("📊 공부 통계")

    day = st.date_input("날짜")
    hours = st.number_input("공부 시간",0,24)

    if st.button("기록"):

        st.session_state.study.append({
            "date":day,
            "hours":hours
        })

    df = pd.DataFrame(st.session_state.study)

    if not df.empty:

        fig = px.bar(
            df,
            x="date",
            y="hours",
            title="공부 시간 통계"
        )

        st.plotly_chart(fig)

        dates = sorted(df["date"])

        streak = 1

        for i in range(len(dates)-1,0,-1):

            if (dates[i] - dates[i-1]).days == 1:
                streak += 1
            else:
                break

        st.subheader("🔥 연속 공부")

        st.metric("스트릭",f"{streak}일")

        if streak == 7:
            st.balloons()
            st.success("🎉 7일 연속 공부! 대단해!")

        if streak == 30:
            st.snow()
            st.success("🏆 30일 연속 공부!")

        if streak >= 30:
            level = 5
        elif streak >= 21:
            level = 4
        elif streak >= 14:
            level = 3
        elif streak >= 7:
            level = 2
        else:
            level = 1

        st.subheader("⭐ 캐릭터 레벨")

        st.write(f"{character} Lv.{level}")

    if st.button("홈으로"):
        st.session_state.page="홈"
