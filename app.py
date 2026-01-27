import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# ---------------------------------------------------------
# [1] 컬럼 매핑 (구글 시트 헤더와 띄어쓰기/특수문자 100% 일치 필수)
# ---------------------------------------------------------
COL_NAME = "성함이 어떻게 되세요?"
COL_AGE = "나이가 어떻게 되세요? (숫자만 입력)"
COL_GENDER = "성별이 어떻게 되세요? (숫자만 입력)"
COL_DATE = "오늘의 날짜를 적어주세요 (예시: 2020.08.08)"
COL_STEPS = "오늘의 총 걸음 수를 적어주세요 (숫자만 입력)"
COL_BED_TIME = "어제 몇 시에 잠들었나요? (시간만 입력, ex: 22)"
COL_WAKE_TIME = "오늘 몇 시에 일어났나요? (시간 입력, ex: 07)"
COL_QUIZ_SCORE = "1분 동안 걸으면서 총 퀴즈 10개 중 몇 문제 맞혔나요? ( 숫자만 입력)"

# ---------------------------------------------------------
# [2] 분석 함수 정의 (객관적 지표 산출)
# ---------------------------------------------------------
def calculate_sleep_metrics(bed_time, wake_time):
    """
    수면 시간(Duration)과 수면 중간점(Midpoint)을 계산
    Midpoint는 생체 리듬(Circadian Rhythm)의 핵심 지표입니다.
    """
    # 24시간제 보정 (새벽 0~6시는 24~30으로 계산하여 뺄셈 용이하게 함)
    bed_time_calc = bed_time + 24 if bed_time < 12 else bed_time
    wake_time_calc = wake_time + 24

    # 수면 총량 계산
    if bed_time > wake_time: # 전날 밤 취침 ~ 다음날 아침 기상
        duration = (24 - bed_time) + wake_time
    else: # 새벽 취침 ~ 아침 기상 (예: 01시 -> 08시)
        duration = wake_time - bed_time
    
    # 수면 중간점 계산 (기상 시간에서 수면 시간의 절반을 뺌)
    # 예: 07시 기상, 8시간 수면 -> 중간점은 03시
    midpoint = wake_time - (duration / 2)
    if midpoint < 0: midpoint += 24 # 음수 방지

    return duration, midpoint

# ---------------------------------------------------------
# [3] 웹페이지 기본 설정
# ---------------------------------------------------------
st.set_page_config(page_title="투웰 두뇌 건강 비서", page_icon="🧠", layout="centered")

st.title("🧠 투웰(Two-Well) 두뇌 건강 비서")
st.markdown("### 데이터 기반 맞춤형 치매 예방 솔루션")
st.caption("한국외대 투어리즘&웰니스 학부 연구팀")
st.markdown("---")

# ---------------------------------------------------------
# [4] 데이터 가져오기
# ---------------------------------------------------------
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(ttl=0) # 실시간 데이터 반영
    df.columns = df.columns.str.strip() # 컬럼명 공백 제거 안전장치
except Exception as e:
    st.error("🚨 데이터베이스 연결 실패. secrets.toml 설정을 확인하세요.")
    st.stop()

# ---------------------------------------------------------
# [5] 사용자 인증 및 데이터 분석
# ---------------------------------------------------------
with st.form("login_form"):
    user_name_input = st.text_input("성함을 입력해주세요 (구글 폼과 동일하게)")
    submitted = st.form_submit_button("내 건강 리포트 조회")

if submitted and user_name_input:
    # 컬럼 검증
    if COL_NAME not in df.columns:
        st.error(f"⚠️ 엑셀 컬럼 매칭 오류. '{COL_NAME}' 컬럼을 찾을 수 없습니다.")
        st.code(df.columns.tolist())
    else:
        user_data = df[df[COL_NAME] == user_name_input]
        
        if user_data.empty:
            st.warning(f"'{user_name_input}'님의 기록이 없습니다. 먼저 구글 폼을 작성해주세요.")
        else:
            # 최신 데이터 추출
            last_row = user_data.iloc[-1]
            
            try:
                # --- A. 데이터 파싱 (숫자 변환 및 예외처리) ---
                steps = int(str(last_row[COL_STEPS]).replace(',', '')) # 콤마 제거
                quiz_score = float(last_row[COL_QUIZ_SCORE])
                bed_time = float(last_row[COL_BED_TIME])
                wake_time = float(last_row[COL_WAKE_TIME])
                date_log = last_row[COL_DATE]
                
                # --- B. 지표 계산 ---
                sleep_duration, sleep_midpoint = calculate_sleep_metrics(bed_time, wake_time)
                
                # --- C. 결과 대시보드 출력 ---
                st.success(f"✅ {user_name_input}님, {date_log} 기준 분석 결과입니다.")
                st.markdown("#### 📊 오늘의 생체 데이터")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.info("**🚶 보행 인지 기능**")
                    st.metric("걸음 수", f"{steps}보")
                    st.metric("듀얼 태스크 점수", f"{int(quiz_score)}점 / 10점")
                
                with col2:
                    st.info("**🌙 수면 생체 리듬**")
                    st.metric("총 수면 시간", f"{sleep_duration:.1f}시간")
                    st.metric("수면 중간점(Midpoint)", f"{sleep_midpoint:.1f}시", 
                              help="수면의 중심 시간입니다. 매일 03:00~04:00 사이로 일정해야 뇌 건강에 좋습니다.")

                st.markdown("---")

                # --- D. 닥터 투웰의 맞춤형 처방 (객관적 로직) ---
                st.subheader("💊 닥터 투웰의 AI 정밀 처방")

                # [알고리즘 1] 보행-인지 간섭 분석 (Dual-Task Cost)
                # 논리: 걸음수(신체)는 많으나 퀴즈(인지)가 낮으면 '낙상 고위험' 및 '전두엽 기능 저하'
                st.markdown("**1. 인지-운동 연결성 분석**")
                if steps >= 6000 and quiz_score >= 8:
                    st.success("🌟 **[최우수]** 신체와 두뇌가 완벽하게 연결되어 있습니다. 현재 활동을 유지하세요!")
                elif steps >= 6000 and quiz_score < 5:
                    st.error("🚨 **[주의] 인지-보행 간섭 발생**")
                    st.write("활동량은 많지만, 걷는 동안 두뇌 활용이 떨어집니다. 이는 낙상 위험 신호입니다.")
                    st.info("💡 **솔루션:** 내일은 걸음 수를 조금 줄이더라도, **'걷으면서 간판 이름 읽기'**를 하며 정확도에 집중하세요.")
                elif steps < 4000:
                    st.warning("⚠️ **[부족] 절대적 활동량 부족**")
                    st.write("뇌로 가는 혈류량이 부족할 수 있습니다.")
                    st.info("💡 **솔루션:** 집 앞 10분 산책부터 시작하여 뇌를 깨워주세요.")
                else:
                    st.info("✅ **[양호]** 균형 잡힌 활동을 하고 계십니다. 퀴즈 점수를 1점만 더 올려보세요!")

                # [알고리즘 2] 수면 리듬 분석 (Circadian Rhythm)
                # 논리: 수면 시간의 '양'보다 '중간점'의 위치와 7시간 확보 여부 확인
                st.markdown("**2. 뇌 청소(Glymphatic) 시스템 분석**")
                if 7 <= sleep_duration <= 9:
                    if 2 <= sleep_midpoint <= 4:
                        st.success("🌟 **[최우수]** 치매 예방에 가장 완벽한 수면 골든타임을 지키고 계십니다.")
                    else:
                        st.warning("⚠️ **[리듬 불균형]** 잠은 충분히 잤지만, 자고 깨는 시간이 다소 늦거나 빠릅니다.")
                        st.info(f"💡 **솔루션:** 수면 중간점이 {sleep_midpoint:.1f}시입니다. 오전 10시에 햇볕을 30분간 쬐어 생체시계를 맞추세요.")
                elif sleep_duration < 6:
                    st.error("🚨 **[위험] 수면 부족**")
                    st.write("수면 중 베타 아밀로이드(치매 원인 물질) 배출이 원활하지 않습니다.")
                    st.info("💡 **솔루션:** 낮잠은 20분 이내로 제한하고, 저녁 산책을 통해 수면 압력을 높이세요.")
                else:
                    st.warning("⚠️ **[과수면]** 9시간 이상의 수면은 인지 저하의 신호일 수 있습니다.")

            except ValueError:
                st.error("🚨 데이터 입력 오류: 시간이나 점수에 '숫자'가 아닌 문자가 포함되어 있습니다.")
                st.write("구글 폼에 숫자만 입력했는지 확인해주세요.")
            except Exception as e:
                st.error(f"알 수 없는 오류가 발생했습니다: {e}")

elif submitted and not user_name_input:
    st.warning("성함을 입력해주세요.")

# 새로고침 버튼
if st.button("결과 업데이트"):
    st.rerun()