# =================================
# 갓생 다마고치 완전판 Streamlit
# =================================
import json
from pathlib import Path
from datetime import datetime, timedelta, date
import uuid
import pandas as pd
import streamlit as st
import altair as alt

# =========================
# ---- 기본 설정/상수 -----
# =========================
APP_TITLE = "갓생 다마고치 (Study & Habit RPG)"
DATA_FILE = Path("user_data.json")

XP_PER_MINUTE = 0.5
DEFAULT_HABITS = [
{"name": "수학 문제 20분", "xp": 10},
{"name": "영어 단어 50개", "xp": 12},
{"name": "운동 30분", "xp": 15},
{"name": "정리/루틴 체크", "xp": 8},
]
LEVEL_XP = 100

HUNGER_DECAY_PER_DAY = 20
HUNGER_GAIN_PER_ACTIVITY = 25

MOOD_BY_GAP = {
0: ("최고!", "😺"),
1: ("괜찮아", "🙂"),
2: ("살짝 지침", "😶"),
3: ("외로움", "🥺"),
4: ("위기", "😵"),
}

PET_EVOLUTION_XP = [0, 50, 120, 200, 300]
PET_STAGES = [
{"name": "알", "emoji": "🥚"},
{"name": "병아리", "emoji": "🐤"},
{"name": "닭", "emoji": "🐔"},
{"name": "고양이", "emoji": "🐱"},
{"name": "유니콘", "emoji": "🦄"}
]

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
"user": {"name": "사용자"},
"habits": DEFAULT_HABITS,
"logs": [],
"pet": {"hunger": 80, "stage":0, "name":"알", "emoji":"🥚", "last_active":None, "xp_total":0},
"timers": [],
"background_color": "#f5f5f5",
"friends": {}
}

def save_data(data: dict):
DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def get_logs_df(data: dict) -> pd.DataFrame:
if not data["logs"]:
return pd.DataFrame(columns=["date","study_minutes","habits_completed","notes"])
df = pd.DataFrame(data["logs"])
df["date"] = pd.to_datetime(df["date"]).dt.date
df["habits_count"] = df["habits_completed"].apply(lambda x: len(x) if isinstance(x,list) else 0)
df["xp_from_study"] = df["study_minutes"].fillna(0) * XP_PER_MINUTE
df["xp_from_habits"] = 0.0
return df

def habit_xp_lookup(habits: list[dict]) -> dict:
return {h["name"]: float(h.get("xp",0)) for h in habits}

def compute_xp(df: pd.DataFrame, habits: list[dict]) -> pd.DataFrame:
lookup = habit_xp_lookup(habits)
def xp_from_habits(lst):
if not isinstance(lst,list):
return 0.0
return sum(lookup.get(name,0.0) for name in lst)
if df.empty: return df
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
return int(xp//LEVEL_XP)+1

def xp_to_next_level(xp: float) -> tuple[int,float,float]:
lvl = level_from_xp(xp)
base = (lvl-1)*LEVEL_XP
earned_in_level = xp-base
needed = LEVEL_XP-earned_in_level
return lvl, earned_in_level, max(0.0, needed)

def current_streak(df: pd.DataFrame) -> int:
if df.empty: return 0
active_dates = set(d for d,m,c in zip(df["date"],df["study_minutes"],df["habits_count"]) if (m and m>0) or (c and c>0))
streak = 0
day = date.today()
while day in active_dates:
streak += 1
day -= timedelta(days=1)
return streak

def days_since_activity(df: pd.DataFrame) -> int:
if df.empty: return 999
active = df[(df["study_minutes"]>0)|(df["habits_count"]>0)]
if active.empty: return 999
last_day = active["date"].max()
return (date.today()-last_day).days

def pet_status(data: dict, df: pd.DataFrame) -> dict:
dgap = days_since_activity(df)
mood_text, mood_emoji = MOOD_BY_GAP.get(dgap,("기절 직전","💀"))
hunger = int(data["pet"].get("hunger",80))
if dgap==0: hunger=min(100,hunger+HUNGER_GAIN_PER_ACTIVITY)
else: hunger=max(0,hunger-min(100,dgap*HUNGER_DECAY_PER_DAY))
return {"mood_text":mood_text,"emoji":data["pet"].get("emoji","🥚"),"hunger":hunger,"gap":dgap}

def upsert_log(data: dict, log_date: date, study_minutes: int, habits_completed: list[str], notes: str):
logs = data["logs"]
dstr = log_date.isoformat()
found=False
for row in logs:
if row["date"]==dstr:
row["study_minutes"]=int(study_minutes)
row["habits_completed"]=habits_completed
row["notes"]=notes
found=True
break
if not found:
logs.append({"date":dstr,"study_minutes":int(study_minutes),"habits_completed":habits_completed,"notes":notes})
if (study_minutes>0) or (len(habits_completed)>0):
data["pet"]["last_active"]=dstr
data["pet"]["hunger"]=min(100,int(data["pet"].get("hunger",80))+HUNGER_GAIN_PER_ACTIVITY)
df=get_logs_df(data)
df=compute_xp(df,data["habits"])
data["pet"]["xp_total"]=float(df["xp_total_day"].sum())
for i,xp_req in enumerate(PET_EVOLUTION_XP):
if data["pet"]["xp_total"]>=xp_req:
stage=min(i,len(PET_STAGES)-1)
data["pet"]["stage"]=stage
data["pet"]["name"]=PET_STAGES[stage]["name"]
data["pet"]["emoji"]=PET_STAGES[stage]["emoji"]
save_data(data)

# =========================
# --------- UI ------------
# =========================
st.set_page_config(page_title=APP_TITLE, page_icon="🎮", layout="wide")
if "data" not in st.session_state:
st.session_state.data = load_data()
data = st.session_state.data

st.markdown(f"<style>body {{background-color: {data.get('background_color','#f5f5f5')}}}</style>",unsafe_allow_html=True)

st.title(APP_TITLE)
st.caption("공부/습관 기록 → XP → 펫 성장! 🐣 → 🦄")

# ---------------- 사용자/펫 이름 ----------------
with st.sidebar.expander("👤 사용자/펫 이름 설정"):
user_name=st.text_input("사용자 이름",value=data["user"].get("name","사용자"))
pet_name=st.text_input("펫 이름",value=data["pet"].get("name","알"))
if st.button("💾 이름 저장"):
data["user"]["name"]=user_name.strip() or "사용자"
data["pet"]["name"]=pet_name.strip() or data["pet"]["name"]
save_data(data)
st.success("이름 저장 완료!")
st.experimental_rerun()

# ---------------- 오늘 기록 ----------------
st.sidebar.header("📘 오늘 기록")
today=date.today()
log_date=st.sidebar.date_input("날짜",value=today,max_value=today)
study_minutes=int(st.sidebar.number_input("공부 시간(분)",min_value=0,step=5))
habit_names=[h["name"] for h in data["habits"]]
selected_habits=st.sidebar.multiselect("완료한 습관",options=habit_names)
notes=st.sidebar.text_area("메모/회고",height=100,placeholder="느낀 점, 회고 한 줄 등")

if st.sidebar.button("✅ 기록 저장/업데이트"):
upsert_log(data,log_date,study_minutes,selected_habits,notes)
st.sidebar.success("저장 완료!")
st.experimental_rerun()

# =========================
# 여기서부터 과목별 타이머, 대시보드, 펫 탭, 습관/퀘스트, 기록, 설정, 친구 초대, 배경색 변경 등 코드 이어서 붙이면 됩니다
# =========================
# =========================
# 메인 데이터 처리
# =========================
df=get_logs_df(data)
df=compute_xp(df,data["habits"])
xp_sum=total_xp(df)
lvl, earned_in_level, needed=xp_to_next_level(xp_sum)
streak=current_streak(df)
pet=pet_status(data,df)

# 상단 KPI
c1,c2,c3,c4=st.columns(4)
c1.metric("레벨",f"Lv. {lvl}",help=f"누적 XP {int(xp_sum)}")
c2.metric("누적 XP",f"{int(xp_sum)}")
c3.metric("연속 활동일",f"{streak}일")
c4.metric("펫 포만감",f"{pet['hunger']}/100",help="활동 시 ↑, 미활동 시 ↓")

# =========================
# 탭 구성
# =========================
tab_dash, tab_pet, tab_habits, tab_history, tab_timer, tab_settings, tab_friends = st.tabs(
["📊 대시보드","🐾 펫","🧩 습관·퀘스트","🗂 기록","⏱ 타이머","⚙️ 설정","👥 친구"]
)

# =========================
# 1) 대시보드
# =========================
with tab_dash:
st.subheader("성장 그래프")
if df.empty:
st.info("아직 데이터가 없어요. 왼쪽에서 오늘 기록을 추가해봐!")
else:
d30=date.today()-timedelta(days=29)
df30=df[df["date"]>=d30].copy()
colA,colB=st.columns(2)
with colA:
st.markdown("**📈 일별 공부 시간(분)**")
chart1=alt.Chart(df30).mark_line(point=True).encode(
x=alt.X('date:T',title='날짜'),
y=alt.Y('study_minutes:Q',title='분'),
tooltip=['date:T','study_minutes:Q']
).properties(height=260)
st.altair_chart(chart1,use_container_width=True)
with colB:
st.markdown("**🧱 일별 완료 습관 수**")
chart2=alt.Chart(df30).mark_bar().encode(
x=alt.X('date:T',title='날짜'),
y=alt.Y('habits_count:Q',title='개수'),
tooltip=['date:T','habits_count:Q']
).properties(height=260)
st.altair_chart(chart2,use_container_width=True)
colC,colD=st.columns(2)
with colC:
st.markdown("**⭐ 일별 XP & 누적 XP**")
line_total=alt.Chart(df30).mark_line(point=True).encode(
x=alt.X('date:T',title='날짜'),
y=alt.Y('xp_total_day:Q',title='일일 XP'),
tooltip=['date:T','xp_total_day:Q']
)
cum_chart=alt.Chart(df30).mark_line().encode(
x=alt.X('date:T',title='날짜'),
y=alt.Y('xp_cum:Q',title='누적 XP'),
tooltip=['date:T','xp_cum:Q']
).properties(height=220)
st.altair_chart(line_total.properties(height=220),use_container_width=True)
st.altair_chart(cum_chart,use_container_width=True)
with colD:
st.markdown("**🔥 레벨 진행도**")
progress=0.0 if LEVEL_XP==0 else earned_in_level/LEVEL_XP
st.progress(min(1.0,progress))
st.write(f"다음 레벨까지 **{int(needed)} XP** 남음 (현재 레벨 내 {int(earned_in_level)}/{LEVEL_XP})")

# =========================
# 2) 펫
# =========================
with tab_pet:
st.subheader(f"{data['pet']['name']} 상태")
st.markdown(f"<div style='font-size:6rem;text-align:center'>{data['pet']['emoji']}</div>",unsafe_allow_html=True)
st.markdown(f"**상태:** {pet['mood_text']} (최근 활동 공백: {pet['gap']}일)")
st.markdown(f"**XP 누적:** {int(data['pet']['xp_total'])}")
st.markdown("**펫 성장 단계:** "+ " → ".join([p["name"] for p in PET_STAGES]))
st.divider()
st.markdown("### 🎯 오늘 추천 퀘스트")
if df.empty:
st.write("- 공부 30~60분 기록")
st.write("- 습관 1~2개 완료")
else:
d7=date.today()-timedelta(days=6)
df7=df[df["date"]>=d7]
avg_min=int(df7["study_minutes"].mean()) if not df7.empty else 0
avg_hab=float(df7["habits_count"].mean()) if not df7.empty else 0
if avg_min<60: st.write(f"- 최근 1주 평균 {avg_min}분 → 오늘 90분 도전!")
else: st.write(f"- 평균 {avg_min}분 유지")
if avg_hab<1.5: st.write("- 루틴 2개 선택 완료")
else: st.write("- 기존 루틴 유지 + 새 습관 1개 시도")

# =========================
# 3) 습관·퀘스트
# =========================
with tab_habits:
st.subheader("습관 관리")
edited=st.data_editor(pd.DataFrame(data["habits"]),num_rows="dynamic",use_container_width=True,key="habit_editor")
if st.button("💾 습관 저장"):
new_habits=[]
names_seen=set()
for _,row in edited.iterrows():
name=str(row.get("name","")).strip()
xp=float(row.get("xp",0))
if name and name not in names_seen and xp>=0:
new_habits.append({"name":name,"xp":xp})
names_seen.add(name)
data["habits"]=new_habits if new_habits else data["habits"]
save_data(data)
st.success("습관 저장 완료!")
st.experimental_rerun()
st.divider()
st.markdown("#### 빠른 퀘스트 아이디어")
st.write("- 아침 스트레칭 5분 (XP5)")
st.write("- 모의고사 오답노트 1회 (XP15)")
st.write("- 독서 20분 (XP8)")

# =========================
# 4) 기록
# =========================
with tab_history:
st.subheader("일자별 기록")
if df.empty:
st.info("기록 없음")
else:
show=df[["date","study_minutes","habits_completed","notes","xp_total_day"]].sort_values("date",ascending=False)
st.dataframe(show,use_container_width=True,height=380)
st.markdown("##### 🗑 특정 날짜 삭제")
del_date=st.date_input("삭제할 날짜 선택",value=today,max_value=today,key="delete_date")
if st.button("삭제 실행"):
before=len(data["logs"])
data["logs"]=[r for r in data["logs"] if r["date"]!=del_date.isoformat()]
after=len(data["logs"])
save_data(data)
if after<before: st.success(f"{del_date.isoformat()} 기록 삭제됨")
else: st.warning("해당 날짜 기록 없음")
st.experimental_rerun()

# =========================
# 5) 타이머
# =========================
with tab_timer:
st.subheader("⏱ 과목별 타이머")
timer_title=st.text_input("타이머 이름/과목")
if st.button("➕ 타이머 추가"):
if timer_title.strip():
tid=str(uuid.uuid4())
data["timers"].append({"id":tid,"title":timer_title,"minutes":0,"running":False,"start_time":None})
save_data(data)
st.experimental_rerun()
for t in data["timers"]:
st.markdown(f"**{t['title']}** ({t['minutes']}분)")
col1,col2,col3=st.columns([1,1,1])
with col1:
if st.button(f"▶ 시작 {t['id']}"):
t["running"]=True
t["start_time"]=datetime.now().isoformat()
save_data(data)
st.experimental_rerun()
with col2:
if st.button(f"⏸ 중지 {t['id']}"):
if t["running"]:
delta=(datetime.now()-datetime.fromisoformat(t["start_time"])).total_seconds()/60
t["minutes"]+=int(delta)
t["running"]=False
t["start_time"]=None
save_data(data)
st.experimental_rerun()
with col3:
if st.button(f"🗑 삭제 {t['id']}"):
data["timers"]=[x for x in data["timers"] if x["id"]!=t["id"]]
save_data(data)
st.experimental_rerun()

# =========================
# 6) 설정
# =========================
with tab_settings:
st.subheader("설정")
color=st.color_picker("배경색 선택",value=data.get("background_color","#f5f5f5"))
if st.button("💾 배경색 저장"):
data["background_color"]=color
save_data(data)
st.experimental_rerun()
colx,coly=st.columns(2)
with colx:
if st.button("🔄 오늘만 초기화"):
data["logs"]=[r for r in data["logs"] if r["date"]!=today_str()]
save_data(data)
st.experimental_rerun()
with coly:
if st.button("🧹 전체 초기화"):
DATA_FILE.unlink(missing_ok=True)
st.session_state.pop("data",None)
st.experimental_rerun()

# =========================
# 7) 친구
# =========================
with tab_friends:
st.subheader("친구 초대 및 경쟁")
friend_name=st.text_input("친구 이름")
if st.button("➕ 친구 추가"):
if friend_name.strip():
fid=str(uuid.uuid4())
data["friends"][fid]={"name":friend_name,"xp":0}
save_data(data)
st.experimental_rerun()
if data["friends"]:
st.markdown("#### 친구 목록")
for fid,finfo in data["friends"].items():
st.write(f"{finfo['name']} - XP: {finfo['xp']}")

# =========================
# 푸터
# =========================
st.caption("© 갓생 다마고치 — 루틴은 가볍게, 꾸준함은 강력하게.")
