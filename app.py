import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# ---------------------------------------------------------
# [1] 사용자 설정 구간 (구글 시트 헤더와 100% 일치해야 함)
# 공유해주신 시트의 질문 내용을 반영했습니다.
# ---------------------------------------------------------

COL_NAME = "성함이 어떻게 되세요?"
COL_QUIZ_SCORE = "보행 과제 후 1분 동안 걸으면서 퀴즈를 몇 문제 맞혔나요? ( 숫자만 입력)"
COL_SLEEP_TIME = "어제 몇 시에 잤나요? (시간 입력, ex: 22)"
COL_AWAKE_TIME = "어제 몇 시에 일어났나요? (시간 입력, ex: 7)"  # 예시 숫자 수정 (22 -> 7)
COL_FEELING = "오늘의 컨디션"

# ---------------------------------------------------------
# [2] 웹페이지 기본 설정
# ---------------------------------------------------------
st.set_page_config(
    page_title="두뇌 건강 비서",
    page_icon="🧠",
    layout="centered"
)

st.title("🧠 두뇌 건강 비서")
st.markdown("쉬운 활동으로 기억을 잊지 말아요!")
st.markdown("---")

# ---------------------------------------------------------
# [3] 구글 시트 데이터 가져오기
# ---------------------------------------------------------
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(ttl=0) # 실시간 새로고침
    
    # 데이터 전처리: 컬럼명 앞뒤 공백 제거 (에러 방지용)
    df.columns = df.columns.str.strip()
    
except Exception as e:
    st.error("🚨 구글 시트 연결에 실패했습니다.")
    st.error(f"에러 메시지: {e}")
    st.info("Tip: .streamlit/secrets.toml 파일에 구글 시트 주소가 올바른지 확인해주세요.")
    st.stop()

# ---------------------------------------------------------
# [4] 사용자 인증 (이름 입력)
# ---------------------------------------------------------
with st.form("login_form"):
    user_name_input = st.text_input("성함을 입력해주세요 (구글 폼에 적은 것과 동일하게)")
    submitted = st.form_submit_button("내 기록 확인하기")

if submitted and user_name_input:
    # 해당 이름 컬럼이 엑셀에 있는지 확인
    if COL_NAME not in df.columns:
        st.error(f"엑셀에서 '{COL_NAME}' 컬럼을 찾을 수 없습니다. 구글 폼의 질문 제목과 코드가 일치하는지 확인해주세요.")
        st.write("현재 엑셀의 컬럼 목록:", df.columns.tolist()) # 디버깅용 힌트 제공
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
            
            try:
                # 1. 점수 파싱 (숫자 변환)
                score = float(last_row[COL_QUIZ_SCORE])
                
                # 2. 수면 시간 계산 로직 추가
                # 엑셀에서 가져온 값을 정수(int)로 변환
                bed_time = float(last_row[COL_SLEEP_TIME]) 
                wake_time = float(last_row.get(COL_AWAKE_TIME, 0)) # 기상 시간 없으면 0 처리
                
                # 수면 시간 계산 (예: 22시 취침, 7시 기상 -> 9시간)
                if bed_time > wake_time:
                    sleep_duration = (24 - bed_time) + wake_time
                else:
                    sleep_duration = wake_time - bed_time
                
                # 3. 컨디션 가져오기
                feeling = last_row.get(COL_FEELING, "-")

                st.success(f"✅ {user_name_input}님의 최신 기록이 업데이트되었습니다.")
                st.markdown("---")
                
                # 대시보드 (메트릭 표시)
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("🧩 듀얼태스크 점수", f"{int(score)}점")
                with col2:
                    # 총 수면 시간을 표시하고, 아래 작은 글씨로 취침/기상 시간 표시
                    st.metric("😴 총 수면 시간", f"{int(sleep_duration)}시간", f"{int(bed_time)}시 ~ {int(wake_time)}시")
                with col3:
                    st.metric("Condition", f"{feeling}")

                st.markdown("---")
                
                # 맞춤형 솔루션 (Pre-DTx 알고리즘)
                st.subheader("💡 오늘의 AI 건강 처방")
                
                # 점수별 피드백
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
                st.error("입력된 데이터 중 숫자가 아닌 값이 있습니다. 구글 폼에 숫자만 입력했는지 확인해주세요.")
            except KeyError as e:
                st.error(f"데이터를 불러오는 중 오류가 발생했습니다. 컬럼명을 확인해주세요: {e}")

elif submitted and not user_name_input:
    st.warning("이름을 입력해야 결과를 볼 수 있습니다.")

# ---------------------------------------------------------
# [6] 하단 리프레시 버튼
# ---------------------------------------------------------
if st.button("결과 새로고침"):
    st.rerun()