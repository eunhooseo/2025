import json
from pathlib import Path
from datetime import datetime, timedelta, date
import time
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

# 펫 진화 단계 (레벨 기준)
PET_EVOLUTION = {
    1: ("🥚", "알 단계"),
    3: ("😺", "아기"),
    6: ("🦊", "청소년"),
    10: ("🐉", "성체(완전체)"),
}

# 다양한 상태(허기 + 최근 활동 공백일 종합)
# 위에서부터 우선순위 판단
PET_STATES = [
    {"cond": lambda hunger, gap: hunger >= 90 and gap == 0, "emoji": "🤩", "text": "의욕 폭발"},
    {"cond": lambda hunger, gap: hunger >= 75 and gap <= 1, "emoji": "😸", "text": "행복해요"},
    {"cond": lambda hunger, gap: hunger >= 60 and gap <= 1, "emoji": "🙂", "text": "좋아요"},
    {"cond": lambda hunger, gap: hunger >= 45 and gap <= 2, "emoji": "😶", "text": "무난무난"},
    {"cond": lambda hunger, gap: hunger >= 30, "emoji": "🥺", "text": "외로워요"},
    {"cond": lambda hunger, gap: hunger > 0, "emoji": "😵", "text": "기운이 없어요"},
    {"cond": lambda hunger, gap: hunger <= 0, "emoji": "💀", "text": "기절 직전..."},
]

HUNGER_DECAY_PER_DAY = 20      # 활동 없을 때 하루 당 포만감 감소
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
        "user": {
            "name": "사용자",
            "pet_name": "다마고치",
            "bg_color": "#ffffff",
            "font_color": "#000000",
        },
        "habits": DEFAULT_HABITS,
        "logs": [],  # [{date, habits_completed:[], study_minutes:int, notes:str}]
        "pet": {
            "hunger": 80,           # 0~100
            "last_active": None,    # "YYYY-MM-DD"
            "last_level": 1,        # 마지막으로 확정된 레벨 (레벨업 연출용)
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
    df["study_minutes"] = df["study_minutes"].fillna(0).astype(int)
    df["xp_from_study"] = df["study_minutes"] * XP_PER_MINUTE
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
        return 999
    active = df[(df["study_minutes"]>0) | (df["habits_count"]>0)]
    if active.empty:
        return 999
    last_day = active["date"].max()
    return (date.today() - last_day).days

def get_pet_stage(level: int) -> tuple[str, str]:
    stage = ("🥚", "알 단계")
    for lvl, form in PET_EVOLUTION.items():
        if level >= lvl:
            stage = form
    return stage

def pet_status(data: dict, df: pd.DataFrame, xp_sum: float) -> dict:
    dgap = days_since_activity(df)
    # 허기 업데이트(표시용 계산: dgap 반영)
    hunger = int(data["pet"].get("hunger", 80))
    if dgap == 0:
        hunger = min(100, hunger + HUNGER_GAIN_PER_ACTIVITY)
    else:
        hunger = max(0, hunger - min(100, dgap * HUNGER_DECAY_PER_DAY))

    # 상태 결정
    status_text, status_emoji = "상태 불명", "❓"
    for s in PET_STATES:
        if s["cond"](hunger, dgap):
            status_text, status_emoji = s["text"], s["emoji"]
            break

    level = level_from_xp(xp_sum)
    form_emoji, form_name = get_pet_stage(level)
    return {
        "mood_text": status_text,
        "mood_emoji": status_emoji,
        "emoji": form_emoji,
        "form_name": form_name,
        "hunger": hunger,
        "gap": dgap,
        "level": level
    }

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
    # 펫 last_active/hunger 반영(저장 시 포만감 즉시 회복)
    if (study_minutes and study_minutes>0) or (habits_completed and len(habits_completed)>0):
        data["pet"]["last_active"] = dstr
        data["pet"]["hunger"] = min(100, int(data["pet"].get("hunger", 80)) + HUNGER_GAIN_PER_ACTIVITY)
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

# ============ 사용자/테마 ============
with st.sidebar:
    st.header("👤 사용자 & 테마")
    data["user"]["name"] = st.text_input("사용자 이름", value=data["user"].get("name","사용자"))
    data["user"]["pet_name"] = st.text_input("다마고치 이름", value=data["user"].get("pet_name","다마고치"))
    data["user"]["bg_color"] = st.color_picker("배경 색상(HEX)", value=data["user"].get("bg_color","#ffffff"))
    data["user"]["font_color"] = st.color_picker("글자 색상(HEX)", value=data["user"].get("font_color","#000000"))
    if st.button("🎨 테마 저장"):
        save_data(data)
        st.success("테마/이름 저장 완료!")

# 테마 CSS 반영
st.markdown(
    f"""
    <style>
    .stApp {{
        background-color: {data['user']['bg_color']};
        color: {data['user']['font_color']};
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# ============ 사이드바: 공부 기록 + ⏱ 타이머 ============
st.sidebar.header("📘 오늘 기록")
today = date.today()
log_date = st.sidebar.date_input("날짜", value=today, max_value=today)

# 타이머 상태 준비
if "timer_running" not in st.session_state:
    st.session_state.timer_running = False
if "timer_start" not in st.session_state:
    st.session_state.timer_start = None
if "timer_elapsed" not in st.session_state:
    st.session_state.timer_elapsed = 0.0  # seconds
if "input_minutes" not in st.session_state:
    st.session_state.input_minutes = 0

# 타이머 UI
st.sidebar.markdown("### ⏱ 공부 타이머")
c1, c2, c3, c4 = st.sidebar.columns(4)
with c1:
    if st.button("▶️ 시작"):
        if not st.session_state.timer_running:
            st.session_state.timer_running = True
            st.session_state.timer_start = time.time()
with c2:
    if st.button("⏸ 일시정지"):
        if st.session_state.timer_running:
            st.session_state.timer_elapsed += time.time() - st.session_state.timer_start
            st.session_state.timer_running = False
with c3:
    if st.button("↩️ 리셋"):
        st.session_state.timer_running = False
        st.session_state.timer_start = None
        st.session_state.timer_elapsed = 0.0
with c4:
    if st.button("💾 타이머 저장"):
        # 타이머 누적을 오늘 공부시간 입력에 반영
        total_sec = st.session_state.timer_elapsed + (time.time() - st.session_state.timer_start if st.session_state.timer_running else 0)
        add_min = int(total_sec // 60)
        st.session_state.input_minutes += add_min
        st.session_state.timer_running = False
        st.session_state.timer_start = None
        st.session_state.timer_elapsed = 0.0
        st.sidebar.success(f"타이머 {add_min}분을 오늘 공부시간에 추가!")

# 현재 타이머 표시
current_sec = st.session_state.timer_elapsed + (time.time() - st.session_state.timer_start if st.session_state.timer_running else 0)
st.sidebar.metric("현재 타이머", f"{int(current_sec//60)}분 {int(current_sec%60)}초")

# 수동 입력 + 타이머 반영 분
base_minutes = int(st.sidebar.number_input("공부 시간(분)", min_value=0, step=5, value=0))
study_minutes = base_minutes + st.session_state.input_minutes

habit_names = [h["name"] for h in data["habits"]]
selected_habits = st.sidebar.multiselect("완료한 습관", options=habit_names)
notes = st.sidebar.text_area("메모/회고", height=100, placeholder="느낀 점, 회고 한 줄 등")

if st.sidebar.button("✅ 기록 저장/업데이트"):
    upsert_log(data, log_date, study_minutes, selected_habits, notes)
    # 타이머 반영치 초기화
    st.session_state.input_minutes = 0
    st.sidebar.success("저장 완료!")
    st.experimental_rerun()

# 메인 데이터프레임/지표 계산
df = get_logs_df(data)
df = compute_xp(df, data["habits"])
xp_sum = total_xp(df)
lvl, earned_in_level, needed = xp_to_next_level(xp_sum)
streak = current_streak(df)
pet = pet_status(data, df, xp_sum)

# 레벨업 연출(💥 펑!)
prev_level = data["pet"].get("last_level", 1)
if pet["level"] > prev_level:
    st.balloons()
    st.markdown(
        f"<div style='text-align:center;font-size:2rem'>💥 펑! "
        f"{data['user']['pet_name']}가 <b>{pet['form_name']}</b>(으)로 진화했어요!</div>",
        unsafe_allow_html=True
    )
    data["pet"]["last_level"] = pet["level"]
    save_data(data)

# 상단 KPI
c1, c2, c3, c4 = st.columns(4)
c1.metric("레벨", f"Lv. {pet['level']}", help=f"누적 XP {int(xp_sum)}")
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
            cum_chart = alt.Chart(cum).mark_line(point=True).encode(
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
    st.subheader(f"나의 다마고치 — {data['user']['pet_name']}")
    big = st.empty()
    # 진화한 폼(큰 이모지)
    big.markdown(f"<div style='font-size:6rem; text-align:center'>{pet['emoji']}</div>", unsafe_allow_html=True)
    st.markdown(f"**단계:** {pet['form_name']} | **레벨:** Lv.{pet['level']}")
    st.markdown(f"**상태:** {pet['mood_text']} {pet['mood_emoji']} (최근 활동 공백: {pet['gap']}일)")
    st.progress(pet['hunger']/100.0)
    st.caption("※ 포만감은 활동이 없을수록 감소, 오늘 활동하면 회복해요.")

    # 오늘의 퀘스트(추천)
    st.divider()
    st.markdown("### 🎯 오늘의 추천 퀘스트")
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
    if st.button("💾 습관 저장"):
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
    st.write("- 아침 스트레칭 5분 (XP 5)")
    st.write("- 오답노트 1회 (XP 15)")
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
st.caption(f"© 갓생 다마고치 — 루틴은 가볍게, 꾸준함은 강력하게. | 사용자: {data['user']['name']} · 펫: {data['user']['pet_name']}")
