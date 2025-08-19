import json
from pathlib import Path
from datetime import datetime, timedelta, date
import math
import pandas as pd
import streamlit as st
import altair as alt

# =========================
# ---- 기본 설정/상수 -----
# =========================
APP_TITLE = "갓생 다마고치 (Study & Habit RPG)"
DATA_FILE = Path("user_data.json")

# XP 규칙
XP_PER_MINUTE = 0.5         # 공부 1분당 0.5 XP (예: 60분 = 30 XP)
DEFAULT_HABITS = [
    {"name": "수학 문제 20분", "xp": 10},
    {"name": "영어 단어 50개", "xp": 12},
    {"name": "운동 30분", "xp": 15},
    {"name": "정리/루틴 체크", "xp": 8},
]
LEVEL_XP = 100              # 레벨업 간격 (누적 XP 0~99 = Lv1, 100~199 = Lv2 ...)

# 펫 상태 규칙
MOOD_BY_GAP = {
    0: ("최고!", "😺"),
    1: ("괜찮아", "🙂"),
    2: ("살짝 지침", "😶"),
    3: ("외로움", "🥺"),
    4: ("위기", "😵"),
}
HUNGER_DECAY_PER_DAY = 20   # 활동 없을 때 하루 당 포만감 감소
HUNGER_GAIN_PER_ACTIVITY = 25  # 오늘 활동 기록하면 포만감 회복량 (최대 100)

# =========================
# ------- 유틸 함수 -------
# =========================
def today_str(d: date | None = None) -> str:
    d = d or date.today()
    return d.isoformat()

def load_data():
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    # 초기 데이터
    return {
        "habits": DEFAULT_HABITS,
        "logs": [],  # [{date, habits_completed:[], study_minutes:int, notes:str}]
        "pet": {
            "hunger": 80,      # 0~100
            "last_active": None,  # "YYYY-MM-DD"
        }
    }

def save_data(data: dict):
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def get_logs_df(data: dict) -> pd.DataFrame:
    if not data["logs"]:
        return pd.DataFrame(columns=["date", "study_minutes", "habits_completed", "notes"])
    df = pd.DataFrame(data["logs"])
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"]).dt.date
    else:
        df["date"] = pd.to_datetime(df.index).date
    # 보조 칼럼
    df["habits_count"] = df["habits_completed"].apply(lambda x: len(x) if isinstance(x, list) else 0)
    df["xp_from_study"] = df["study_minutes"].fillna(0) * XP_PER_MINUTE
    df["xp_from_habits"] = 0.0  # 실제 계산은 아래에서
    return df

def habit_xp_lookup(habits: list[dict]) -> dict:
    return {h["name"]: float(h.get("xp", 0)) for h in habits}

def compute_xp(df: pd.DataFrame, habits: list[dict]) -> pd.DataFrame:
    lookup = habit_xp_lookup(habits)
    def xp_from_habits(lst):
        if not isinstance(lst, list):
            return 0.0
        return sum(lookup.get(name, 0.0) for name in lst)
    if df.empty:
        return df
    df = df.copy()
    df["xp_from_habits"] = df["habits_completed"].apply(xp_from_habits)
    df["xp_total_day"] = df["xp_from_study"] + df["xp_from_habits"]
    df = df.sort_values("date")
    df["xp_cum"] = df["xp_total_day"].cumsum()
    return df

def total_xp(df: pd.DataFrame) -> float:
    if df.empty: return 0.0
    return float(df["xp_total_day"].sum())

def level_from_xp(xp: float) -> int:
    return int(xp // LEVEL_XP) + 1

def xp_to_next_level(xp: float) -> tuple[int, float, float]:
    """return (current_level, earned_in_level, needed_for_next)"""
    lvl = level_from_xp(xp)
    base = (lvl - 1) * LEVEL_XP
    earned_in_level = xp - base
    needed = LEVEL_XP - earned_in_level
    return lvl, earned_in_level, max(0.0, needed)

def current_streak(df: pd.DataFrame) -> int:
    """연속 활동일(오늘 포함). 활동 기준: 공부 분 > 0 또는 습관 1개 이상."""
    if df.empty: return 0
    # 활동 있는 날짜 집합
    active_dates = set(d for d, m, c in zip(df["date"], df["study_minutes"], df["habits_count"]) if (m and m>0) or (c and c>0))
    streak = 0
    day = date.today()
    while day in active_dates:
        streak += 1
        day -= timedelta(days=1)
    return streak

def days_since_activity(df: pd.DataFrame) -> int:
    if df.empty: 
        # 활동 전혀 없음
        return 999
    # 마지막 활동 있는 날짜
    active = df[(df["study_minutes"]>0) | (df["habits_count"]>0)]
    if active.empty:
        return 999
    last_day = active["date"].max()
    return (date.today() - last_day).days

def pet_status(data: dict, df: pd.DataFrame) -> dict:
    dgap = days_since_activity(df)
    # 무드 결정
    if dgap in MOOD_BY_GAP:
        mood_text, mood_emoji = MOOD_BY_GAP[dgap]
    else:
        mood_text, mood_emoji = ("기절 직전", "💀")
    # 허기 업데이트(표시용 계산)
    hunger = int(data["pet"].get("hunger", 80))
    # 최근 활동 여부로 오늘 허기움 보정 (표시 전용)
    if dgap == 0:
        hunger = min(100, hunger + HUNGER_GAIN_PER_ACTIVITY)
    else:
        hunger = max(0, hunger - min(100, dgap * HUNGER_DECAY_PER_DAY))
    return {"mood_text": mood_text, "emoji": mood_emoji, "hunger": hunger, "gap": dgap}

def upsert_log(data: dict, log_date: date, study_minutes: int, habits_completed: list[str], notes: str):
    logs = data["logs"]
    dstr = log_date.isoformat()
    found = False
    for row in logs:
        if row["date"] == dstr:
            row["study_minutes"] = int(study_minutes)
            row["habits_completed"] = habits_completed
            row["notes"] = notes
            found = True
            break
    if not found:
        logs.append({
            "date": dstr,
            "study_minutes": int(study_minutes),
            "habits_completed": habits_completed,
            "notes": notes
        })
    # 펫 last_active/hunger 반영
    if (study_minutes and study_minutes>0) or (habits_completed and len(habits_completed)>0):
        data["pet"]["last_active"] = dstr
        data["pet"]["hunger"] = min(100, int(data["pet"].get("hunger", 80)) + HUNGER_GAIN_PER_ACTIVITY)
    else:
        # 활동 없을 경우는 저장 시에는 굳이 깎지 않고 표시 시점에 계산
        pass
    save_data(data)

# =========================
# --------- UI ------------
# =========================
st.set_page_config(page_title=APP_TITLE, page_icon="🎮", layout="wide")
st.title(APP_TITLE)
st.caption("공부/습관을 기록하고 XP를 모아 레벨업! 펫을 행복하게 키우면서 성장 그래프로 갓생 달리기 🚀")

# 데이터 불러오기 & 세션 보관
if "data" not in st.session_state:
    st.session_state.data = load_data()
data = st.session_state.data

# 사이드바: 오늘 기록하기
st.sidebar.header("📘 오늘 기록")
today = date.today()
log_date = st.sidebar.date_input("날짜", value=today, max_value=today)
study_minutes = int(st.sidebar.number_input("공부 시간(분)", min_value=0, step=5))
habit_names = [h["name"] for h in data["habits"]]
selected_habits = st.sidebar.multiselect("완료한 습관", options=habit_names)
notes = st.sidebar.text_area("메모/회고", height=100, placeholder="느낀 점, 회고 한 줄 등")

if st.sidebar.button("✅ 기록 저장/업데이트"):
    upsert_log(data, log_date, study_minutes, selected_habits, notes)
    st.sidebar.success("저장 완료!")
    st.experimental_rerun()

# 메인 데이터프레임/지표 계산
df = get_logs_df(data)
df = compute_xp(df, data["habits"])
xp_sum = total_xp(df)
lvl, earned_in_level, needed = xp_to_next_level(xp_sum)
streak = current_streak(df)
pet = pet_status(data, df)

# 상단 KPI
c1, c2, c3, c4 = st.columns(4)
c1.metric("레벨", f"Lv. {lvl}", help=f"누적 XP {int(xp_sum)}")
c2.metric("누적 XP", f"{int(xp_sum)}")
c3.metric("연속 활동일", f"{streak}일")
c4.metric("펫 포만감", f"{pet['hunger']}/100", help="활동 시 ↑, 미활동 시 ↓")

# 탭 구성
tab_dash, tab_pet, tab_habits, tab_history, tab_settings = st.tabs(
    ["📊 대시보드", "🐾 펫", "🧩 습관·퀘스트", "🗂 기록", "⚙️ 설정"]
)

# =========================
# 1) 대시보드
# =========================
with tab_dash:
    st.subheader("성장 그래프")
    if df.empty:
        st.info("아직 데이터가 없어요. 왼쪽에서 오늘 기록을 추가해봐!")
    else:
        # 30일 범위로 필터
        d30 = date.today() - timedelta(days=29)
        df30 = df[df["date"] >= d30].copy()

        colA, colB = st.columns(2)

        with colA:
            st.markdown("**📈 일별 공부 시간(분)**")
            chart1 = alt.Chart(df30).mark_line(point=True).encode(
                x=alt.X('date:T', title='날짜'),
                y=alt.Y('study_minutes:Q', title='분'),
                tooltip=['date:T', 'study_minutes:Q']
            ).properties(height=260)
            st.altair_chart(chart1, use_container_width=True)

        with colB:
            st.markdown("**🧱 일별 완료 습관 수**")
            chart2 = alt.Chart(df30).mark_bar().encode(
                x=alt.X('date:T', title='날짜'),
                y=alt.Y('habits_count:Q', title='개수'),
                tooltip=['date:T', 'habits_count:Q']
            ).properties(height=260)
            st.altair_chart(chart2, use_container_width=True)

        colC, colD = st.columns(2)

        with colC:
            st.markdown("**⭐ 일별 XP & 누적 XP**")
            base = alt.Chart(df30).encode(x=alt.X('date:T', title='날짜'))
            line_total = base.mark_line(point=True).encode(
                y=alt.Y('xp_total_day:Q', title='일일 XP'),
                tooltip=['date:T', 'xp_total_day:Q']
            )
            cum = df.copy()
            cum_chart = alt.Chart(cum).mark_line().encode(
                x=alt.X('date:T', title='날짜'),
                y=alt.Y('xp_cum:Q', title='누적 XP'),
                tooltip=['date:T', 'xp_cum:Q']
            ).properties(height=220)
            st.altair_chart(line_total.properties(height=220), use_container_width=True)
            st.altair_chart(cum_chart, use_container_width=True)

        with colD:
            st.markdown("**🔥 레벨 진행도**")
            progress = 0.0 if LEVEL_XP == 0 else earned_in_level / LEVEL_XP
            st.progress(min(1.0, progress))
            st.write(f"다음 레벨까지 **{int(needed)} XP** 남음 (현재 레벨 내 {int(earned_in_level)}/{LEVEL_XP})")

# =========================
# 2) 펫
# =========================
with tab_pet:
    st.subheader("나의 다마고치")
    big = st.empty()
    big.markdown(f"<div style='font-size:5rem; text-align:center'>{pet['emoji']}</div>", unsafe_allow_html=True)
    st.markdown(f"**상태:** {pet['mood_text']} (최근 활동 공백: {pet['gap']}일)")
    st.markdown(f"**이 펫은 너의 성장을 먹고 자라!** 활동이 없으면 배고파하고 기운이 떨어져...")

    # 오늘의 퀘스트(추천)
    st.divider()
    st.markdown("### 🎯 오늘의 추천 퀘스트")
    # 부족 부분 찾아서 제안: 최근 7일 평균 공부시간이 60분 미만이면 공부 확대, 습관이 적으면 습관 추천
    if df.empty:
        st.write("- 공부 30~60분 기록해보기")
        st.write("- 습관 2개 만들고 오늘 1개 이상 완료하기")
    else:
        d7 = date.today() - timedelta(days=6)
        df7 = df[df["date"] >= d7]
        avg_min = 0 if df7.empty else int(df7["study_minutes"].mean())
        avg_hab = 0 if df7.empty else float(df7["habits_count"].mean())
        if avg_min < 60:
            st.write(f"- 최근 1주 평균 공부 {avg_min}분 ➜ **오늘 90분** 도전!")
        else:
            st.write(f"- 평균 {avg_min}분 유지 굿! ➜ **집중 25분 x 3세트** 해보기")
        if avg_hab < 1.5:
            st.write("- **루틴 2개** 선택해서 오늘 반드시 완료하기")
        else:
            st.write("- 기존 루틴 유지 + **새 습관 1개** 시범 도입")

# =========================
# 3) 습관·퀘스트
# =========================
with tab_habits:
    st.subheader("습관 관리 (XP 값 편집 가능)")
    st.caption("각 습관 완료 시 받을 XP를 설정해. 현실성 있게! (예: 난이도 높을수록 XP↑)")
    edited = st.data_editor(pd.DataFrame(data["habits"]), num_rows="dynamic", use_container_width=True, key="habit_editor")
    # 저장 버튼
    if st.button("💾 습관 저장"):
        # 유효성 검사
        new_habits = []
        names_seen = set()
        for _, row in edited.iterrows():
            name = str(row.get("name", "")).strip()
            xp = float(row.get("xp", 0))
            if name and name not in names_seen and xp >= 0:
                new_habits.append({"name": name, "xp": xp})
                names_seen.add(name)
        data["habits"] = new_habits if new_habits else data["habits"]
        save_data(data)
        st.success("습관 저장 완료!")
        st.experimental_rerun()

    st.divider()
    st.markdown("#### 빠른 퀘스트 추가 아이디어")
    st.write("- 아침 기상 직후 스트레칭 5분 (XP 5)")
    st.write("- 모의고사 오답노트 1회 (XP 15)")
    st.write("- 독서 20분 (XP 8)")

# =========================
# 4) 기록
# =========================
with tab_history:
    st.subheader("일자별 기록")
    if df.empty:
        st.info("기록이 아직 없어요.")
    else:
        show = df[["date", "study_minutes", "habits_completed", "notes", "xp_total_day"]].sort_values("date", ascending=False)
        st.dataframe(show, use_container_width=True, height=380)

        # 특정 날짜 삭제
        st.markdown("##### 🗑 특정 날짜 기록 삭제")
        del_date = st.date_input("삭제할 날짜 선택", value=today, max_value=today, key="delete_date")
        if st.button("삭제 실행"):
            before = len(data["logs"])
            data["logs"] = [r for r in data["logs"] if r["date"] != del_date.isoformat()]
            after = len(data["logs"])
            save_data(data)
            if after < before:
                st.success(f"{del_date.isoformat()} 기록 삭제됨.")
            else:
                st.warning("해당 날짜 기록이 없어요.")
            st.experimental_rerun()

# =========================
# 5) 설정
# =========================
with tab_settings:
    st.subheader("설정")
    colx, coly = st.columns(2)
    with colx:
        if st.button("🔄 오늘만 초기화(공부/습관 체크/메모)"):
            # 오늘 로그만 비우기
            data["logs"] = [r for r in data["logs"] if r["date"] != today_str()]
            save_data(data)
            st.success("오늘 기록을 초기화했어요.")
            st.experimental_rerun()
    with coly:
        if st.button("🧹 전체 초기화(되돌릴 수 없음)"):
            DATA_FILE.unlink(missing_ok=True)
            st.session_state.pop("data", None)
            st.warning("모든 데이터가 삭제됐어요. 페이지가 새로고침됩니다.")
            st.experimental_rerun()

# 푸터
st.caption("© 갓생 다마고치 — 루틴은 가볍게, 꾸준함은 강력하게.")
