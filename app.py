import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import altair as alt

# ---------------------------------------------------------
# 1. 컬럼 매핑
# ---------------------------------------------------------
COL_NAME = "성함이 어떻게 되세요?"
COL_PASSWORD = "비밀번호 4자리를 입력해주세요."
COL_DATE = "오늘의 날짜를 적어주세요."
COL_STEPS = "오늘의 총 걸음 수를 적어주세요"
COL_BALANCE = "오늘의 균형 운동 시간(분)을 적어주세요"
COL_NUTRITION = "항산화 및 오메가3 식단 달성률(%)"
COL_AUDITORY_SCORE = "웹 기반 청각인지 훈련 점수(100점 만점)"

# ---------------------------------------------------------
# 2. 웹페이지 기본 설정
# ---------------------------------------------------------
st.set_page_config(page_title="청력 및 인지 건강 비서", layout="centered")

st.title("청력 및 인지 건강 비서")
st.markdown("### 노인성 난청 예방 및 관리 5단계 프로그램")
st.caption("한국외대 난청 예방 PoC 프로젝트")
st.markdown("---")

# ---------------------------------------------------------
# 3. 데이터 로드
# ---------------------------------------------------------
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(ttl=0)
    df.columns = df.columns.str.strip()
except Exception as e:
    st.error("데이터 연결 실패. secrets.toml을 확인하세요.")
    st.stop()

# ---------------------------------------------------------
# 4. 메인 로직
# ---------------------------------------------------------
st.markdown("### 본인 확인")

# =========================================================
# 관리자 모드
# =========================================================
with st.sidebar:
    st.header("관리자 메뉴")
    admin_pw = st.text_input("관리자 암호", type="password")
    
    if admin_pw == "hufs1234":
        st.success("관리자 모드 접속 완료")
        show_admin = True
    else:
        show_admin = False

if show_admin:
    st.markdown("---")
    st.header("전체 대상자 모니터링")
    
    latest_df = df.copy()
    latest_df[COL_STEPS] = latest_df[COL_STEPS].astype(str).str.replace(',', '').astype(int)
    latest_df[COL_AUDITORY_SCORE] = pd.to_numeric(latest_df[COL_AUDITORY_SCORE], errors='coerce').fillna(0)
    
    summary_df = latest_df.sort_values(COL_DATE).groupby(COL_NAME).tail(1)
    
    danger_group = summary_df[
        (summary_df[COL_STEPS] < 4000) | 
        (summary_df[COL_AUDITORY_SCORE] < 60)
    ]
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.error(f"집중 케어 대상 ({len(danger_group)}명)")
        if not danger_group.empty:
            display_cols = [COL_NAME, COL_DATE, COL_STEPS, COL_AUDITORY_SCORE]
            st.dataframe(danger_group[display_cols], hide_index=True)
        else:
            st.write("현재 위험군 대상자가 없습니다.")
            
    with col_b:
        st.info(f"전체 관리 대상 ({len(summary_df)}명)")
        st.metric("평균 걸음 수", f"{int(summary_df[COL_STEPS].mean())}보")
        st.metric("평균 청각훈련 점수", f"{summary_df[COL_AUDITORY_SCORE].mean():.1f}점")

    csv_all = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("전체 데이터 통합 다운로드", csv_all, "total_hearing_data.csv")
    st.markdown("---")

# =========================================================
# 사용자 모드
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
                    st.success(f"{user_name_input}님 환영합니다.")
                    
                    history_df = user_data.copy()
                    history_df[COL_STEPS] = history_df[COL_STEPS].astype(str).str.replace(',', '').astype(int)
                    history_df[COL_BALANCE] = pd.to_numeric(history_df[COL_BALANCE], errors='coerce').fillna(0)
                    history_df[COL_NUTRITION] = pd.to_numeric(history_df[COL_NUTRITION], errors='coerce').fillna(0)
                    history_df[COL_AUDITORY_SCORE] = pd.to_numeric(history_df[COL_AUDITORY_SCORE], errors='coerce').fillna(0)
                    
                    history_df['temp_date'] = pd.to_datetime(history_df[COL_DATE], format='%Y.%m.%d', errors='coerce')
                    history_df = history_df.sort_values('temp_date')

                    tab1, tab2 = st.tabs(["최신 리포트", "종합 기록실"])
                    
                    with tab1:
                        steps = int(str(last_row[COL_STEPS]).replace(',', ''))
                        bal_time = float(last_row[COL_BALANCE])
                        nut_score = float(last_row[COL_NUTRITION])
                        aud_score = float(last_row[COL_AUDITORY_SCORE])
                        c_date = last_row.get(COL_DATE, "최근")
                        
                        st.markdown(f"#### {c_date} 청력 건강 리포트")
                        c1, c2 = st.columns(2)
                        with c1:
                            st.metric("걸음 수", f"{steps}보")
                            st.metric("균형 운동 시간", f"{int(bal_time)}분")
                        with c2:
                            st.metric("식단 달성률", f"{int(nut_score)}%")
                            st.metric("청각 훈련 점수", f"{int(aud_score)}점")
                        st.markdown("---")
                        
                        st.subheader("맞춤형 청력 건강 처방")

                        st.markdown("1. 신체 활동 및 균형 능력 분석")
                        if steps >= 6000 and bal_time >= 15:
                            st.success("[최우수] 낙상 예방 및 청각 신경 자극이 원활합니다.")
                            st.info("유지 전략: 현재의 걷기와 균형 운동 패턴을 유지하세요. 게이미피케이션 배지 획득에 도전해보세요.")
                        elif steps >= 6000 and bal_time < 15:
                            st.warning("[주의] 보행량은 충분하나 균형 능력이 부족합니다.")
                            st.info("개선 전략: 의자를 잡고 한 발로 서기 등 하체 근력 및 균형 운동 시간을 15분 이상으로 늘리세요.")
                        else:
                            st.error("[부족] 전반적인 신체 활동량이 부족합니다.")
                            st.info("개선 전략: 스마트 밴드를 착용하고 주 3회 30분 이상 걷기를 실천하세요.")

                        st.markdown("---")

                        st.markdown("2. 청각 인지 및 영양 상태 분석")
                        if aud_score >= 80 and nut_score >= 80:
                            st.success("[최우수] 언어 처리 능력과 식습관이 매우 우수합니다.")
                            st.info("유지 전략: 오메가3 식단과 웹 기반 소음 속 단어 찾기 훈련의 현재 난이도를 유지하세요.")
                        elif aud_score < 80 and nut_score >= 80:
                            st.warning("[주의] 영양은 우수하나 청각 변별력이 떨어집니다.")
                            st.info("개선 전략: 짧은 문장 기억하기 등 웹 기반 청각 훈련의 집중도를 높이세요.")
                        else:
                            st.error("[위험] 항산화 영양 섭취와 청각 훈련 모두 관리가 필요합니다.")
                            st.info("개선 전략: 가공식품을 줄이고 생선 섭취를 늘리며, 매일 10분씩 소리 방향 맞히기 훈련을 진행하세요.")

                    with tab2:
                        st.subheader(f"{user_name_input}님의 변화 그래프")
                        
                        period = st.radio("조회 기간", ["최근 7일", "전체 보기"], horizontal=True)
                        if period == "최근 7일":
                            chart_df = history_df.tail(7)
                        else:
                            chart_df = history_df

                        st.markdown("1. 활동량과 청각 인지 점수 변화")
                        
                        base = alt.Chart(chart_df).encode(x=alt.X(COL_DATE, title='날짜'))
                        
                        bar_steps = base.mark_bar(color='#ffbd88', opacity=0.5).encode(
                            y=alt.Y(COL_STEPS, title='걸음 수')
                        )
                        
                        line_score = base.mark_line(color='#1f77b4', point=True).encode(
                            y=alt.Y(COL_AUDITORY_SCORE, title='청각 훈련 점수')
                        )
                        
                        rule_data = pd.DataFrame({COL_DATE: chart_df[COL_DATE].unique(), 'goal': 6000})
                        rule = alt.Chart(rule_data).mark_rule(color='red', strokeDash=[5, 5]).encode(y='goal')
                        
                        combo_chart = alt.layer(bar_steps, rule, line_score).resolve_scale(
                            y='independent'
                        ).properties(height=350)
                        
                        st.altair_chart(combo_chart, use_container_width=True)
                        st.caption("주황막대: 걸음수 / 파란선: 청각점수 / 빨간점선: 목표 6000보")

                        st.markdown("---")
                        
                        st.markdown("2. 영양 달성률과 청각 점수의 상관관계")
                        
                        scatter = alt.Chart(chart_df).mark_circle(size=120).encode(
                            x=alt.X(COL_NUTRITION, title='식단 달성률(%)'),
                            y=alt.Y(COL_AUDITORY_SCORE, title='청각 훈련 점수', scale=alt.Scale(domain=[0, 100])),
                            tooltip=[COL_DATE, COL_NUTRITION, COL_AUDITORY_SCORE]
                        ).interactive().properties(height=350)
                        
                        st.altair_chart(scatter, use_container_width=True)
                        
                        csv = history_df.drop(columns=['temp_date']).to_csv(index=False).encode('utf-8-sig')
                        st.download_button("내 기록 엑셀로 저장", csv, "my_hearing_log.csv", "text/csv")