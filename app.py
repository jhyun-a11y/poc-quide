import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# ---------------------------------------------------------
# [1] 사용자 설정 구간 (여기만 실제 엑셀과 똑같이 고치세요!)
# 구글 시트 1행에 적힌 '글자'를 띄어쓰기까지 정확하게 적어야 합니다.
# ---------------------------------------------------------

COL_NAME = "성함"                  # 예: 이름, 성명, 대상자명
COL_QUIZ_SCORE = "퀴즈 정답 개수"   # 예: 퀴즈 점수, 미션 성공 횟수 (숫자만 입력받는 칸)
COL_SLEEP_TIME = "수면 시간"        # 예: 어제 잔 시간, 수면 시간(시간)
COL_FEELING = "오늘의 컨디션"       # 예: 걷기 후 기분, 주관적 느낌

# ---------------------------------------------------------
# [2] 웹페이지 기본 설정
# ---------------------------------------------------------
st.set_page_config(
    page_title="투웰 두뇌 건강 비서",
    page_icon="🧠",
    layout="centered"
)

st.title("🧠 투웰(Tourism&Wellness) 두뇌 건강 비서")
st.markdown("### 매일 걷고, 매일 기억하세요!")
st.markdown("---")

# ---------------------------------------------------------
# [3] 구글 시트 데이터 가져오기
# ---------------------------------------------------------
try:
    # ttl=0 옵션은 캐시를 남기지 않고 매번 새로고침 한다는 뜻입니다 (실시간성)
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(ttl=0)
    
    # 데이터 전처리: 혹시 모를 공백 제거 (엑셀 헤더에 스페이스바가 껴있을 경우 대비)
    df.columns = df.columns.str.strip()
    
except Exception as e:
    st.error("🚨 구글 시트 연결에 실패했습니다.")
    st.error(f"에러 메시지: {e}")
    st.info("Tip: secrets.toml 파일에 구글 시트 주소가 정확히 들어갔는지 확인해주세요.")
    st.stop()

# ---------------------------------------------------------
# [4] 사용자 인증 (이름 입력)
# ---------------------------------------------------------
with st.form("login_form"):
    user_name_input = st.text_input("성함을 입력해주세요 (구글 폼에 적은 것과 동일하게)")
    submitted = st.form_submit_button("내 기록 확인하기")

if submitted and user_name_input:
    # 해당 이름이 데이터에 있는지 확인
    if COL_NAME not in df.columns:
        st.error(f"엑셀에 '{COL_NAME}'이라는 컬럼이 없습니다. 코드 상단 변수를 수정해주세요.")
    else:
        # 이름으로 필터링
        user_data = df[df[COL_NAME] == user_name_input]
        
        if user_data.empty:
            st.warning(f"'{user_name_input}'님의 데이터가 아직 없습니다. 먼저 구글 폼을 제출해주세요.")
        else:
            # ---------------------------------------------------------
            # [5] 분석 및 결과 출력 (가장 최신 데이터 1줄 기준)
            # ---------------------------------------------------------
            last_row = user_data.iloc[-1] # 가장 마지막 행 가져오기
            
            # 데이터 추출 (에러 방지를 위한 예외처리 포함)
            try:
                score = float(last_row[COL_QUIZ_SCORE]) # 숫자로 변환
                sleep = last_row[COL_SLEEP_TIME]
                feeling = last_row.get(COL_FEELING, "-") # 없으면 - 표시
                
                st.success(f"✅ {user_name_input}님의 최신 기록이 업데이트되었습니다.")
                
                # 1. 대시보드 (메트릭 표시)
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("🧩 듀얼태스크 점수", f"{int(score)}점")
                with col2:
                    st.metric("😴 수면 시간", f"{sleep}")
                with col3:
                    st.metric("Condition", f"{feeling}")
                
                st.markdown("---")
                
                # 2. 맞춤형 솔루션 (Pre-DTx 알고리즘)
                st.subheader("💡 오늘의 AI 건강 처방")
                
                # 점수에 따른 분기 (if-else logic)
                if score >= 8:
                    st.balloons()
                    st.info(f"**[최우수 단계]** 인지-운동 연결성이 매우 좋습니다! \n\n"
                            "👍 **추천 활동:** 현재의 산책 코스를 유지하되, 내일은 조금 더 빠른 걸음으로 도전해보세요.")
                elif score >= 5:
                    st.warning(f"**[주의 단계]** 걷는 동안 인지 과제 수행이 조금 불안정합니다. \n\n"
                               "💊 **추천 활동:** 걷는 속도를 조금 늦추고, 퀴즈 정답을 맞히는 데 더 집중해보세요.")
                else:
                    st.error(f"**[위험 단계]** 이중 과제(Dual-task) 수행 비용이 높게 나타났습니다. \n\n"
                             "🏥 **강력 추천:** 낙상 위험이 있으니 내일은 평지 위주로 천천히 걸으시고, 보호자와 함께 산책하세요.")
            
            except ValueError:
                st.error("점수 데이터가 숫자가 아닙니다. 구글 폼에서 점수를 '숫자'로만 입력했는지 확인해주세요.")
            except KeyError as e:
                st.error(f"엑셀에서 컬럼을 찾을 수 없습니다: {e}")

elif submitted and not user_name_input:
    st.warning("이름을 입력해야 결과를 볼 수 있습니다.")

# ---------------------------------------------------------
# [6] 하단 리프레시 버튼
# ---------------------------------------------------------
if st.button("결과 새로고침"):
    st.rerun()