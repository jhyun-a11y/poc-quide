import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import altair as alt

COL_NAME = "성함이 어떻게 되세요?"
COL_PASSWORD = "비밀번호 4자리를 입력해주세요. (전화번호 뒷자리 등)"
COL_DATE = "오늘의 날짜를 적어주세요."
COL_STEPS = "오늘의 총 걸음 수를 적어주세요. (스마트 밴드 확인)"
COL_BALANCE = "오늘의 균형 운동 시간(분)을 적어주세요. (예: 의자 잡고 한 발 서기 등)"
COL_NUTRITION = "항산화 및 오메가3 식단 섭취 목표를 얼마나 달성하셨나요? (0~100 사이 숫자 입력)"
COL_AUDITORY_SCORE = "웹 기반 청각인지 훈련 점수를 적어주세요. (100점 만점 기준)"

st.set_page_config(page_title="청력 및 인지 건강 비서", layout="centered")

st.title("청력 및 인지 건강 비서")
st.markdown("### 노인성 난청 예방 및 관리 5단계 프로그램")
st.caption("한국외대 난청 예방 PoC 프로젝트")
st.markdown("---")

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(ttl=0)
    df.columns = df.columns.str.strip()
except Exception as e:
    st.error("데이터 연결 실패. secrets.toml을 확인하세요.")
    st.stop()

st.markdown("### 본인 확인")

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
                    history_df[COL_BALANCE] = pd.to_numeric(history_df[COL