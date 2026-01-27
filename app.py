import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import altair as alt

# ---------------------------------------------------------
# [1] 컬럼 매핑 (구글 시트 헤더와 100% 일치)
# ---------------------------------------------------------
COL_NAME = "성함이 어떻게 되세요?"
COL_PASSWORD = "비밀번호 4자리를 입력해주세요."
COL_DATE = "오늘의 날짜를 적어주세요."
COL_STEPS = "오늘의 총 걸음 수를 적어주세요"
COL_BED_TIME = "어제 몇 시에 잠들었나요?"
COL_WAKE_TIME = "오늘 몇 시에 일어났나요?"
COL_QUIZ_SCORE = "10문제 중 1분 동안 걸으면서 퀴즈를 몇 문제 맞혔나요?"
COL_FEELING = "오늘의 컨디션" # 산점도 툴팁용 (엑셀에 없으면 자동 처리됨)

# ---------------------------------------------------------
# [2] 분석 함수
# ---------------------------------------------------------
def calculate_sleep_metrics(bed_time, wake_time):
    bed_time_calc = bed_time + 24 if bed_time < 12 else bed_time
    wake_time_calc = wake_time + 24

    if bed_time > wake_time:
        duration = (24 - bed_time) + wake_time
    else:
        duration = wake_time - bed_time
    
    midpoint = wake_time - (duration / 2)
    if midpoint < 0: midpoint += 24

    return duration, midpoint

# ---------------------------------------------------------
# [3] 웹페이지 기본 설정
# ---------------------------------------------------------
st.set_page_config(page_title="Chemi-Well 두뇌 건강 비서", page_icon="🧠", layout="centered")

st.title("🧠 Chemi-Well 두뇌 건강 비서")
st.markdown("### 🏃‍♂️ 몸과 마음이 함께 건강해지는 습관")
st.caption("한국외대 Chemi-Well, PoC 프로젝트")
st.markdown("---")

# ---------------------------------------------------------
# [4] 데이터 로드
# ---------------------------------------------------------
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(ttl=0)
    df.columns = df.columns.str.strip()
except Exception as e:
    st.error("데이터 연결 실패. secrets.toml을 확인하세요.")
    st.stop()

# ---------------------------------------------------------
# [5] 메인 로직
# ---------------------------------------------------------
st.markdown("### 🔒 본인 확인")

# =========================================================
# [추가 기능] 관리자(학생 연구원) 전용 대시보드
# =========================================================
with st.sidebar:
    st.header("👮‍♂️ 관리자 메뉴")
    admin_pw = st.text_input("관리자 암호", type="password")
    
    if admin_pw == "hufs1234":
        st.success("관리자 모드 접속")
        show_admin = True
    else:
        show_admin = False

if show_admin:
    st.markdown("---")
    st.header("🚨 전체 대상자 모니터링")
    
    latest_df = df.copy()
    latest_df[COL_STEPS] = latest_df[COL_STEPS].astype(str).str.replace(',', '').astype(int)
    latest_df[COL_QUIZ_SCORE] = pd.to_numeric(latest_df[COL_QUIZ_SCORE], errors='coerce').fillna(0)
    
    summary_df = latest_df.sort_values(COL_DATE).groupby(COL_NAME).tail(1)
    
    danger_group = summary_df[
        ((summary_df[COL_STEPS] >= 6000) & (summary_df[COL_QUIZ_SCORE] < 5)) | 
        (summary_df[COL_STEPS] < 4000)
    ]
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.error(f"🔴 집중 케어 대상 ({len(danger_group)}명)")
        if not danger_group.empty:
            display_cols = [COL_NAME, COL_DATE, COL_STEPS, COL_QUIZ_SCORE]
            st.dataframe(danger_group[display_cols], hide_index=True)
        else:
            st.write("현재 위험군 대상자가 없습니다.")
            
    with col_b:
        st.info(f"🟢 전체 관리 대상 ({len(summary_df)}명)")
        st.metric("평균 걸음 수", f"{int(summary_df[COL_STEPS].mean())}보")
        st.metric("평균 퀴즈 점수", f"{summary_df[COL_QUIZ_SCORE].mean():.1f}점")

    csv_all = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("전체 데이터 통합 다운로드", csv_all, "total_data.csv")
    st.markdown("---")

# =========================================================
# 사용자 로그인
# =========================================================
with st.form("login_form"):
    col1, col2 = st.columns(2)
    with col1:
        user_name_input = st.text_input("성함")
    with col2:
        user_pw_input = st.text_input("비밀번호 (전화번호 뒷자리)", type="password")
    submitted = st.form_submit_button("내 기록 조회하기")

if submitted:
    if not user_name_input or not user_pw_input:
        st.warning("성함과 비밀번호를 입력해주세요.")
    else:
        if COL_NAME not in df.columns:
            st.error("컬럼 매칭 오류. 엑셀 헤더를 확인해주세요.")
        else:
            user_data = df[df[COL_NAME] == user_name_input]
            
            if user_data.empty:
                st.error("가입된 정보가 없습니다.")
            else:
                last_row = user_data.iloc[-1]
                sheet_pw = str(last_row.get(COL_PASSWORD, "")).strip()
                if sheet_pw.endswith('.0'): sheet_pw = sheet_pw[:-2]
                input_pw = str(user_pw_input).strip()

                if sheet_pw != input_pw:
                    st.error("비밀번호가 틀렸습니다.")
                else:
                    st.success(f"🔓 {user_name_input}님 환영합니다!")
                    
                    # 데이터 전처리
                    history_df = user_data.copy()
                    history_df[COL_STEPS] = history_df[COL_STEPS].astype(str).str.replace(',', '').astype(int)
                    history_df[COL_QUIZ_SCORE] = pd.to_numeric(history_df[COL_QUIZ_SCORE], errors='coerce').fillna(0)
                    
                    history_df['temp_date'] = pd.to_datetime(history_df[COL_DATE], format='%Y.%m.%d', errors='coerce')
                    history_df = history_df.sort_values('temp_date')
                    
                    history_df['수면시간'] = history_df.apply(
                        lambda x: calculate_sleep_metrics(float(x[COL_BED_TIME]), float(x[COL_WAKE_TIME]))[0], axis=1
                    )
                    
                    if COL_FEELING not in history_df.columns:
                        history_df[COL_FEELING] = "-"

                    # 탭 구성
                    tab1, tab2 = st.tabs(["📝 최신 리포트", "📈 종합 기록실"])
                    
                    # --- TAB 1: 최신 리포트 ---
                    with tab1:
                        steps = int(str(last_row[COL_STEPS]).replace(',', ''))
                        quiz_score = float(last_row[COL_QUIZ_SCORE])
                        c_bed = float(last_row[COL_BED_TIME])
                        c_wake = float(last_row[COL_WAKE_TIME])
                        c_date = last_row.get(COL_DATE, "최근")
                        c_dur, c_mid = calculate_sleep_metrics(c_bed, c_wake)
                        
                        st.markdown(f"#### 📊 {c_date} 건강 리포트")
                        c1, c2 = st.columns(2)
                        with c1:
                            st.metric("걸음 수", f"{steps}보")
                            st.metric("퀴즈 점수", f"{int(quiz_score)}점")
                        with c2:
                            st.metric("수면 시간", f"{c_dur:.1f}시간")
                            st.metric("수면 중간점", f"{c_mid:.1f}시")
                        st.markdown("---")
                        
                        st.subheader("💊 닥터 Chemi-Well 처방")
                        if steps >= 6000 and quiz_score >= 8:
                            st.success("🌟 [최우수] 완벽한 밸런스입니다!")
                        elif steps >= 6000:
                            st.error("🚨 [주의] 낙상 위험! 걷는 동안 생각하는 연습이 필요합니다.")
                        elif steps < 4000:
                            st.warning("⚠️ [부족] 활동량이 너무 적습니다. 산책을 시작하세요.")
                        else:
                            st.info("✅ [양호] 좋은 습관입니다. 속도를 조금만 높여보세요.")

                    # --- TAB 2: 종합 기록실 ---
                    with tab2:
                        st.subheader(f"{user_name_input}님의 변화 그래프")
                        
                        period = st.radio("조회 기간", ["최근 7일", "전체 보기"], horizontal=True)
                        if period == "최근 7일":
                            chart_df = history_df.tail(7)
                        else:
                            chart_df = history_df

                        # 1. 목표 기준선 포함 이중 축 그래프
                        st.markdown("**1. 활동량과 인지 기능 변화**")
                        
                        base = alt.Chart(chart_df).encode(x=alt.X(COL_DATE, title='날짜'))
                        
                        bar_steps = base.mark_bar(color='#ffbd88', opacity=0.5).encode(
                            y=alt.Y(COL_STEPS, title='걸음 수')
                        )
                        
                        line_score = base.mark_line(color='#1f77b4', point=True).encode(
                            y=alt.Y(COL_QUIZ_SCORE, title='퀴즈 점수')
                        )
                        
                        # [안전한 기준선 생성 방식]
                        rule_data = pd.DataFrame({COL_DATE: chart_df[COL_DATE].unique(), 'goal': 6000})
                        rule = alt.Chart(rule_data).mark_rule(color='red', strokeDash=[5, 5]).encode(y='goal')
                        
                        combo_chart = alt.layer(bar_steps, rule, line_score).resolve_scale(
                            y='independent'
                        ).properties(height=350)
                        
                        st.altair_chart(combo_chart, use_container_width=True)
                        st.caption("🧡주황막대: 걸음수 / 💙파란선: 퀴즈점수 / 🚩빨간점선: 목표(6000보)")

                        st.markdown("---")
                        
                        # 2. 상관관계 산점도
                        st.markdown("**2. 수면과 활동의 상관관계**")
                        
                        scatter = alt.Chart(chart_df).mark_circle(size=120).encode(
                            x=alt.X(COL_STEPS, title='걸음 수'),
                            y=alt.Y('수면시간', title='수면 시간 (시간)', scale=alt.Scale(domain=[3, 12])),
                            color=alt.Color(COL_QUIZ_SCORE, title='퀴즈 점수', scale=alt.Scale(scheme='viridis')),
                            tooltip=[COL_DATE, COL_STEPS, '수면시간', COL_QUIZ_SCORE, COL_FEELING]
                        ).interactive().properties(height=350)
                        
                        st.altair_chart(scatter, use_container_width=True)
                        st.caption("점이 우측 상단에 있을수록 '많이 걷고 잘 잔' 날입니다.")
                        
                        csv = history_df.drop(columns=['temp_date']).to_csv(index=False).encode('utf-8-sig')
                        st.download_button("내 기록 엑셀로 저장", csv, "my_health_log.csv", "text/csv")