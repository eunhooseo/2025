# app.py
import json
import time
import uuid
from pathlib import Path
from datetime import datetime, timedelta, date
import math

import pandas as pd
import streamlit as st
import altair as alt

# =========================
# ---- 설정/상수 ----------
# =========================
APP_TITLE = "갓생 다마고치 (Study & Habit RPG)"
DATA_FILE = Path("user_data.json")

XP_PER_MINUTE = 0.5
LEVEL_XP = 100

DEFAULT_HABITS = [
    {"name": "수학 문제 20분", "xp": 10},
    {"name": "영어 단어 50개", "xp": 12},
    {"name": "운동 30분", "xp": 15},
    {"name": "정리/루틴 체크", "xp": 8},
]

# 펫 진화 단계
PET_EVOLUTION = {
    1: ("🥚", "알 단계"),
    3: ("😺", "아기"),
    6: ("🦊", "청소년"),
    10: ("🐉", "완전체"),
}

# 펫 상태 판단 규칙 (허기 + 활동 공백일)
PET_STATES = [
    {"cond": lambda hunger, gap: hunger >= 90 and gap == 0, "emoji": "🤩", "text": "의욕 폭발"},
    {"cond": lambda hunger, gap: hunger >= 75 and gap <= 1, "emoji": "😸", "text": "행복해요"},
    {"cond": lambda hunger, gap: hunger >= 60 and gap <= 1, "emoji": "🙂", "text": "좋아요"},
    {"cond": lambda hunger, gap: hunger >= 45 and gap <= 2, "emoji": "😶", "text": "무난무난"},
    {"cond": lambda hunger, gap: hunger >= 30, "emoji": "🥺", "text": "외로워요"},
    {"cond": lambda hunger, gap: hunger > 0, "emoji": "😵", "text": "기운이 없어요"},
    {"cond": lambda hunger, gap: hunger <= 0, "emoji": "💀", "text": "기절 직전..."},
]

HUNGER_DECAY_PER_DAY = 20
HUNGER_GAIN_PER_ACTIVITY = 25

# =========================
# ---- 유틸 함수 ----------
# =========================
def today_str(d: date | None = None) -> str:
    d = d or date.today()
    return d.isoformat()

def load_data():
    if DATA_FILE.exists():
        try:
            raw = DATA_FILE.read_text(encoding="utf-8")
            return json.loads(raw)
        except Exception:
            pass
    # 기본 구조: user, habits, logs, pet, timer_defs
    return {
        "user": {
            "name": "사용자",
            "pet_name": "다마고치",
            "bg_color": "#ffffff",
            "font_color": "#000000",
        },
        "habits": DEFAULT_HABITS,
        "logs": [],  # 리스트 of {date, study_minutes:int, habits_completed:list, notes:str}
        "pet": {
            "hunger": 80,
            "last_active": None,
            "last_level": 1,
        },
        "timer_defs": []  # persistent timer definitions: {id, title, subject}
    }

def save_data(data: dict):
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def get_logs_df(data: dict) -> pd.DataFrame:
    if not data.get("logs"):
        return pd.DataFrame(columns=["date", "study_minutes", "habits_completed", "notes"])
    df = pd.DataFrame(data["logs"])
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"]).dt.date
    else:
        df["date"] = pd.to_datetime(df.index).date
    df["habits_completed"] = df["habits_completed"].apply(lambda x: x if isinstance(x, list) else [])
    df["habits_count"] = df["habits_completed"].apply(lambda x: len(x))
    df["study_minutes"] = df["study_minutes"].fillna(0).astype(int)
    df["xp_from_study"] = df["study_minutes"] * XP_PER_MINUTE
    df["xp_from_habits"] = 0.0
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
    lvl = level_from_xp(xp)
    base = (lvl - 1) * LEVEL_XP
    earned_in_level = xp - base
    needed = LEVEL_XP - earned_in_level
    return lvl, earned_in_level, max(0.0, needed)

def current_streak(df: pd.DataFrame) -> int:
    if df.empty: return 0
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

def add_minutes_to_log(data: dict, log_date: date, minutes: int, habits_completed: list[str]=None, notes: str=""):
    if minutes <= 0 and (not habits_completed):
        return False
    dstr = log_date.isoformat()
    found = False
    for row in data["logs"]:
        if row["date"] == dstr:
            # 기존에 더하기
            row["study_minutes"] = int(row.get("study_minutes", 0)) + int(minutes)
            if habits_completed:
                existing = row.get("habits_completed", [])
                if not isinstance(existing, list): existing = []
                row["habits_completed"] = existing + habits_completed
            if notes:
                row["notes"] = (row.get("notes","") + " | " + notes).strip(" | ")
            found = True
            break
    if not found:
        data["logs"].append({
            "date": dstr,
            "study_minutes": int(minutes),
            "habits_completed": habits_completed or [],
            "notes": notes or ""
        })
    # 펫 last_active/hunger 반영
    if minutes > 0 or (habits_completed and len(habits_completed)>0):
        data["pet"]["last_active"] = dstr
        data["pet"]["hunger"] = min(100, int(data["pet"].get("hunger", 80)) + HUNGER_GAIN_PER_ACTIVITY)
    save_data(data)
    return True

def set_log(data: dict, log_date: date, study_minutes: int, habits_completed: list[str], notes: str):
    # 기존에 덮어쓰기(upsert)
    dstr = log_date.isoformat()
    found = False
    for row in data["logs"]:
        if row["date"] == dstr:
            row["study_minutes"] = int(study_minutes)
            row["habits_completed"] = habits_completed
            row["notes"] = notes
            found = True
            break
    if not found:
        data["logs"].append({
            "date": dstr,
            "study_minutes": int(study_minutes),
            "habits_completed": habits_completed or [],
            "notes": notes or ""
        })
    # 반영
    if (study_minutes and study_minutes>0) or (habits_completed and len(habits_completed)>0):
        data["pet"]["last_active"] = dstr
        data["pet"]["hunger"] = min(100, int(data["pet"].get("hunger", 80)) + HUNGER_GAIN_PER_ACTIVITY)
    save_data(data)

# =========================
# ---- 세션 초기화 -------
# =========================
st.set_page_config(page_title=APP_TITLE, page_icon="🎮", layout="wide")
st.title(APP_TITLE)
st.caption("공부/습관을 기록하고 XP를 모아 레벨업! 과목별 타이머로 다마고치를 키우자 🚀")

if "data" not in st.session_state:
    st.session_state.data = load_data()
data = st.session_state.data

# Persistent timer definitions loaded from data; runtime states in session_state['timers']
if "timers" not in st.session_state:
    st.session_state.timers = {}  # id -> {id,title,subject,elapsed_sec, running(bool), start_time}
# sync timer defs into session_state.timers (create runtime entries if missing)
for td in data.get("timer_defs", []):
    tid = td["id"]
    if tid not in st.session_state.timers:
        st.session_state.timers[tid] = {
            "id": tid,
            "title": td.get("title", "무제"),
            "subject": td.get("subject", "일반"),
            "elapsed_sec": 0.0,
            "running": False,
            "start_time": None
        }

# =========================
# ---- 사이드바: 사용자, 테마, 기록(수동) 및 타이머 추가 ----
# =========================
with st.sidebar:
    st.header("👤 사용자 · 테마")
    data["user"]["name"] = st.text_input("사용자 이름", value=data["user"].get("name","사용자"))
    data["user"]["pet_name"] = st.text_input("다마고치 이름", value=data["user"].get("pet_name","다마고치"))
    data["user"]["bg_color"] = st.color_picker("배경 색상(HEX)", value=data["user"].get("bg_color","#ffffff"))
    data["user"]["font_color"] = st.color_picker("글자 색상(HEX)", value=data["user"].get("font_color","#000000"))
    if st.button("🎨 저장(테마/이름)"):
        save_data(data)
        st.success("저장 완료!")
        st.rerun()

    st.markdown("---")
    st.header("📘 오늘 기록 (수동 or 타이머 저장)")
    # 수동 입력
    manual_minutes = int(st.number_input("수동으로 추가할 공부시간(분)", min_value=0, step=5, value=0, key="manual_min"))
    manual_habits = st.multiselect("수동으로 완료한 습관(선택)", options=[h["name"] for h in data.get("habits", [])])
    manual_notes = st.text_area("메모/회고(선택)", height=80, placeholder="오늘의 회고를 적어보자", key="manual_notes")
    if st.button("✅ 수동 기록 저장"):
        added = add_minutes_to_log(data, date.today(), manual_minutes, habits_completed=manual_habits, notes=manual_notes)
        if added:
            st.success(f"오늘 {manual_minutes}분이 추가되었어요!")
            st.rerun()
        else:
            st.warning("추가할 내용이 없어 저장되지 않았어요.")

    st.markdown("---")
    st.header("⏱ 과목별 타이머 추가")
    new_title = st.text_input("타이머 제목 (ex: 수학, 영어 - 개념)", key="new_timer_title")
    new_subject = st.text_input("과목/카테고리 (ex: 수학, 영어, 국어)", key="new_timer_subject")
    if st.button("➕ 타이머 추가"):
        if not new_title.strip():
            st.warning("타이틀을 입력해줘!")
        else:
            tid = str(uuid.uuid4())
            tdef = {"id": tid, "title": new_title.strip(), "subject": new_subject.strip() or "일반"}
            data.setdefault("timer_defs", []).append(tdef)
            save_data(data)
            # create runtime timer
            st.session_state.timers[tid] = {
                "id": tid,
                "title": tdef["title"],
                "subject": tdef["subject"],
                "elapsed_sec": 0.0,
                "running": False,
                "start_time": None
            }
            st.success(f"타이머 '{tdef['title']}' 추가됨")
            st.rerun()

# 테마 CSS 적용 (body 배경/글자 색)
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

# =========================
# ---- 메인: 데이터/지표 계산 ----
# =========================
df = get_logs_df(data)
df = compute_xp(df, data.get("habits", []))
xp_sum = total_xp(df)
lvl, earned_in_level, needed = xp_to_next_level(xp_sum)
streak = current_streak(df)
pet = pet_status(data, df, xp_sum)

# 레벨업 연출 (저장된 last_level 기준)
prev_level = int(data["pet"].get("last_level", 1))
if pet["level"] > prev_level:
    st.balloons()
    st.markdown(
        f"<div style='text-align:center;font-size:1.6rem'>💥 펑! {data['user']['pet_name']}가 <b>{pet['form_name']}</b>로 진화했어요!</div>",
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
tab_dash, tab_pet, tab_timers, tab_habits, tab_history, tab_settings = st.tabs(
    ["📊 대시보드", "🐾 펫", "⏱ 타이머(과목별)", "🧩 습관·퀘스트", "🗂 기록", "⚙️ 설정"]
)

# =========================
# ---- 1) 대시보드 -------
# =========================
with tab_dash:
    st.subheader("성장 그래프")
    if df.empty:
        st.info("아직 데이터가 없어요. 사이드바에서 오늘 기록을 추가하거나 타이머로 공부시간을 저장해보세요.")
    else:
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
# ---- 2) 펫 탭 ---------
# =========================
with tab_pet:
    st.subheader(f"나의 다마고치 — {data['user']['pet_name']}")
    st.markdown(f"<div style='font-size:6rem; text-align:center'>{pet['emoji']}</div>", unsafe_allow_html=True)
    st.markdown(f"**단계:** {pet['form_name']} | **레벨:** Lv.{pet['level']}")
    st.markdown(f"**상태:** {pet['mood_text']} {pet['mood_emoji']} (최근 활동 공백: {pet['gap']}일)")
    st.progress(pet['hunger']/100.0)
    st.caption("※ 포만감은 활동이 없을수록 감소하고, 활동하면 회복됩니다.")

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
# ---- 3) 타이머 탭 -----
# =========================
with tab_timers:
    st.subheader("과목별 타이머 ⏱ (복수 지원)")
    st.markdown("타이머를 시작→일시정지→저장(오늘 기록에 분 단위로 추가) 방식으로 사용하세요.")
    if not st.session_state.timers:
        st.info("아직 타이머가 없어요. 사이드바에서 타이머를 추가해보세요.")
    else:
        # 정렬: 최근 추가 순
        for tid, t in list(st.session_state.timers.items()):
            col_title, col_controls = st.columns([3, 5])
            with col_title:
                st.markdown(f"### {t['title']}  —  *{t['subject']}*")
                # 현재 elapsed 계산
                elapsed = t["elapsed_sec"]
                if t["running"] and t["start_time"]:
                    elapsed += time.time() - t["start_time"]
                hh = int(elapsed // 3600)
                mm = int((elapsed % 3600) // 60)
                ss = int(elapsed % 60)
                st.markdown(f"<div style='font-size:1.4rem'>{hh:02d}:{mm:02d}:{ss:02d}</div>", unsafe_allow_html=True)

            with col_controls:
                b1, b2, b3, b4, b5 = st.columns(5)
                # Start (resume)
                if b1.button("▶️ 시작", key=f"start_{tid}"):
                    if not st.session_state.timers[tid]["running"]:
                        st.session_state.timers[tid]["running"] = True
                        st.session_state.timers[tid]["start_time"] = time.time()
                        st.success(f"'{t['title']}' 시작")
                        st.rerun()
                # Pause
                if b2.button("⏸ 일시정지", key=f"pause_{tid}"):
                    if st.session_state.timers[tid]["running"]:
                        elapsed_add = time.time() - st.session_state.timers[tid]["start_time"]
                        st.session_state.timers[tid]["elapsed_sec"] += elapsed_add
                        st.session_state.timers[tid]["running"] = False
                        st.session_state.timers[tid]["start_time"] = None
                        st.success(f"'{t['title']}' 일시정지 (세션 저장: {int(elapsed_add//60)}분)")
                        st.rerun()
                # Save -> add minutes to today's log and reset timer elapsed
                if b3.button("💾 저장(오늘에 추가)", key=f"save_{tid}"):
                    # compute total seconds
                    total_sec = st.session_state.timers[tid]["elapsed_sec"]
                    if st.session_state.timers[tid]["running"] and st.session_state.timers[tid]["start_time"]:
                        total_sec += time.time() - st.session_state.timers[tid]["start_time"]
                    add_min = int(total_sec // 60)
                    if add_min > 0:
                        notes = f"타이머: {t['title']}({t['subject']})"
                        added = add_minutes_to_log(data, date.today(), add_min, habits_completed=None, notes=notes)
                        if added:
                            # subtract saved seconds (so leftover seconds remain)
                            leftover = total_sec - add_min * 60
                            st.session_state.timers[tid]["elapsed_sec"] = leftover
                            st.session_state.timers[tid]["running"] = False
                            st.session_state.timers[tid]["start_time"] = None
                            st.success(f"오늘 {add_min}분이 '{t['title']}'에서 저장되었어요!")
                            st.rerun()
                        else:
                            st.warning("저장 실패함.")
                    else:
                        st.warning("저장할 분(min)이 0분이에요. 최소 1분 이상이어야 저장됩니다.")
                # Reset
                if b4.button("↩️ 리셋", key=f"reset_{tid}"):
                    st.session_state.timers[tid]["elapsed_sec"] = 0.0
                    st.session_state.timers[tid]["running"] = False
                    st.session_state.timers[tid]["start_time"] = None
                    st.success(f"'{t['title']}' 리셋됨")
                    st.rerun()
                # Remove timer definition (영구 삭제)
                if b5.button("🗑 타이머 삭제", key=f"del_{tid}"):
                    # remove from persistent defs
                    data["timer_defs"] = [x for x in data.get("timer_defs", []) if x["id"] != tid]
                    save_data(data)
                    # remove runtime
                    if tid in st.session_state.timers:
                        del st.session_state.timers[tid]
                    st.success(f"타이머 '{t['title']}' 삭제됨")
                    st.rerun()

# =========================
# ---- 4) 습관 탭 -------
# =========================
with tab_habits:
    st.subheader("습관 관리 (XP 값 편집 가능)")
    st.caption("각 습관 완료 시 받을 XP를 설정하세요. 난이도 높을수록 XP를 높게!")
    edited = st.data_editor(pd.DataFrame(data.get("habits", [])), num_rows="dynamic", use_container_width=True, key="habit_editor")
    if st.button("💾 습관 저장"):
        new_habits = []
        names_seen = set()
        for _, row in edited.iterrows():
            name = str(row.get("name", "")).strip()
            try:
                xp = float(row.get("xp", 0))
            except Exception:
                xp = 0.0
            if name and name not in names_seen and xp >= 0:
                new_habits.append({"name": name, "xp": xp})
                names_seen.add(name)
        data["habits"] = new_habits if new_habits else data.get("habits", DEFAULT_HABITS)
        save_data(data)
        st.success("습관 저장 완료!")
        st.rerun()

    st.divider()
    st.markdown("#### 빠른 퀘스트 아이디어")
    st.write("- 아침 스트레칭 5분 (XP 5)")
    st.write("- 오답노트 1회 (XP 15)")
    st.write("- 독서 20분 (XP 8)")

# =========================
# ---- 5) 기록 탭 -------
# =========================
with tab_history:
    st.subheader("일자별 기록")
    if df.empty:
        st.info("기록이 아직 없어요.")
    else:
        show = df[["date", "study_minutes", "habits_completed", "notes", "xp_total_day"]].sort_values("date", ascending=False)
        st.dataframe(show, use_container_width=True, height=380)

        st.markdown("##### 🗑 특정 날짜 기록 삭제")
        del_date = st.date_input("삭제할 날짜 선택", value=date.today(), max_value=date.today(), key="delete_date")
        if st.button("삭제 실행"):
            before = len(data["logs"])
            data["logs"] = [r for r in data["logs"] if r["date"] != del_date.isoformat()]
            after = len(data["logs"])
            save_data(data)
            if after < before:
                st.success(f"{del_date.isoformat()} 기록 삭제됨.")
            else:
                st.warning("해당 날짜 기록이 없어요.")
            st.rerun()

# =========================
# ---- 6) 설정 탭 -------
# =========================
with tab_settings:
    st.subheader("설정")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔄 오늘만 초기화"):
            data["logs"] = [r for r in data["logs"] if r["date"] != today_str()]
            save_data(data)
            st.success("오늘 기록만 초기화됨")
            st.rerun()
    with c2:
        if st.button("🧹 전체 초기화 (되돌릴 수 없음)"):
            try:
                DATA_FILE.unlink(missing_ok=True)
            except Exception:
                pass
            st.session_state.pop("data", None)
            st.success("전체 데이터 삭제됨 — 페이지 재시작합니다.")
            st.rerun()

    st.markdown("---")
    st.caption("팁: 타이머는 분 단위로 기록됩니다. 1분 미만은 저장되지 않으니 주의!")

# 푸터
st.caption(f"© 갓생 다마고치 — 사용자: {data['user']['name']} · 펫: {data['user']['pet_name']}")
