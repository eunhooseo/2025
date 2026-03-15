import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import random
import sqlite3

st.set_page_config(page_title="Study Manager", layout="wide")

# -----------------------------
# 데이터베이스 연결 (SQLite)
# -----------------------------

conn = sqlite3.connect("study.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS todos(
id INTEGER PRIMARY KEY AUTOINCREMENT,
task TEXT,
done INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS memos(
id INTEGER PRIMARY KEY AUTOINCREMENT,
title TEXT,
content TEXT,
date TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS books(
id INTEGER PRIMARY KEY AUTOINCREMENT,
title TEXT,
subject TEXT,
thought TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS studytime(
id INTEGER PRIMARY KEY AUTOINCREMENT,
date TEXT,
hours INTEGER
)
""")

conn.commit()

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
# 메뉴
# -----------------------------

menu = st.sidebar.radio(
    "메뉴",
    ["홈","ToDo","메모","일정","생기부 독서","공부 통계"]
)

# -----------------------------
# 홈 화면
# -----------------------------

if menu == "홈":

    st.title("📚 Study Manager")

    st.subheader("🎯 D-Day 설정")

    target_date = st.date_input("목표 날짜")

    today = datetime.date.today()

    if target_date:

        dday = (target_date - today).days

        if dday > 0:
            st.metric("D-Day",f"D-{dday}")
        elif dday == 0:
            st.success("🎉 오늘이 목표일!")
        else:
            st.write(f"D+{abs(dday)}")

    st.subheader("⭐ 캐릭터")

    st.write(character)

    cursor.execute("SELECT COUNT(*) FROM studytime")
    count = cursor.fetchone()[0]

    if count > 0:
        st.success(random.choice(good_messages))
    else:
        st.warning(random.choice(bad_messages))

# -----------------------------
# ToDo
# -----------------------------

elif menu == "ToDo":

    st.title("✔️ ToDo List")

    task = st.text_input("할 일 입력")

    if st.button("추가"):

        cursor.execute(
        "INSERT INTO todos(task,done) VALUES(?,?)",
        (task,0)
        )

        conn.commit()

    cursor.execute("SELECT * FROM todos")
    rows = cursor.fetchall()

    for row in rows:

        done = st.checkbox(row[1],value=row[2])

        cursor.execute(
        "UPDATE todos SET done=? WHERE id=?",
        (int(done),row[0])
        )

    conn.commit()

# -----------------------------
# 메모
# -----------------------------

elif menu == "메모":

    st.title("📝 메모")

    title = st.text_input("제목")
    content = st.text_area("내용")

    if st.button("저장"):

        cursor.execute(
        "INSERT INTO memos(title,content,date) VALUES(?,?,?)",
        (title,content,str(datetime.date.today()))
        )

        conn.commit()

    cursor.execute("SELECT * FROM memos ORDER BY id DESC")
    rows = cursor.fetchall()

    for memo in rows:

        st.subheader(memo[1])
        st.write(memo[2])
        st.caption(memo[3])

# -----------------------------
# 일정
# -----------------------------

elif menu == "일정":

    st.title("📅 일정")

    date = st.date_input("날짜")
    schedule = st.text_input("일정")

    if st.button("일정 추가"):

        cursor.execute(
        "INSERT INTO memos(title,content,date) VALUES(?,?,?)",
        ("일정",schedule,str(date))
        )

        conn.commit()

# -----------------------------
# 생기부 독서
# -----------------------------

elif menu == "생기부 독서":

    st.title("📚 생기부 독서 기록")

    book = st.text_input("책 제목")
    subject = st.text_input("과목")
    thought = st.text_area("느낀 점")

    if st.button("기록"):

        cursor.execute(
        "INSERT INTO books(title,subject,thought) VALUES(?,?,?)",
        (book,subject,thought)
        )

        conn.commit()

    cursor.execute("SELECT * FROM books")
    rows = cursor.fetchall()

    for b in rows[::-1]:

        st.subheader(b[1])
        st.write("과목:",b[2])
        st.write(b[3])

# -----------------------------
# 공부 통계
# -----------------------------

elif menu == "공부 통계":

    st.title("📊 공부 통계")

    day = st.date_input("날짜")
    hours = st.number_input("공부 시간",0,24)

    if st.button("기록"):

        cursor.execute(
        "INSERT INTO studytime(date,hours) VALUES(?,?)",
        (str(day),hours)
        )

        conn.commit()

    df = pd.read_sql_query("SELECT * FROM studytime",conn)

    if not df.empty:

        fig = px.bar(
            df,
            x="date",
            y="hours",
            title="공부 시간 통계"
        )

        st.plotly_chart(fig)

        dates = sorted(pd.to_datetime(df["date"]))

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
