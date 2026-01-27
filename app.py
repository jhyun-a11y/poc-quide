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
COL_FEELING = "오늘의 컨디션" # 엑셀에 없으면 자동 처리됨

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
# [관리자 모드] 학생 연구원 전용
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
# [사용자 모드] 로그인 및 리포트 조회
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
                    
                    # -------------------------------------------------
                    # [데이터 전처리]
                    # -------------------------------------------------
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

                    # -------------------------------------------------
                    # [탭 구성] 리포트 & 기록실
                    # -------------------------------------------------
                    tab1, tab2 = st.tabs(["📝 최신 리포트", "📈 종합 기록실"])
                    
                    # === TAB 1: 최신 리포트 (상세 처방 적용) ===
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
                        
                        # --- [업데이트됨] D. 닥터 Chemi-Well의 정밀 처방 ---
                        st.subheader("💊 닥터 Chemi-Well의 AI 정밀 처방")

                        # [분석 1] 인지-운동 연결성 분석
                        st.markdown("#### 1. 인지-운동 연결성 분석")
                        
                        # CASE 1: 최우수
                        if steps >= 6000 and quiz_score >= 8:
                            st.success("🌟 **[최우수] 신체-두뇌 완전 동기화**")
                            with st.expander("🔍 상세 진단 및 추천 활동 보기", expanded=True):
                                st.markdown("""
                                **[상태 설명]**
                                걸으면서 생각하는 능력(이중 과제 수행력)이 20대 수준으로 매우 뛰어납니다. 뇌의 전두엽이 아주 활발하게 작동하고 있어요.
                                
                                **[유지 전략]**
                                현재의 산책 코스와 난이도를 유지하세요. 너무 쉬워지면 뇌 자극이 줄어드니, 가끔은 새로운 길로 다녀보세요.
                                """)
                                st.info("🏃‍♀️ **추천 활동: [오리엔티어링]**\n\n"
                                        "단순 산책 대신, 공원 내 특정 조형물이나 나무 3곳을 순서대로 찾아가서 인증샷을 찍는 미션을 스스로에게 부여해보세요.")

                        # CASE 2: 주의 (낙상 위험)
                        elif steps >= 6000 and quiz_score < 5:
                            st.error("🚨 **[주의] 인지-보행 간섭 발생 (낙상 위험)**")
                            with st.expander("🔍 상세 진단 및 추천 활동 보기", expanded=True):
                                st.markdown("""
                                **[상태 설명]**
                                체력은 좋으시지만, **걷는 동안 두뇌가 발에 집중하느라 생각할 여유가 없습니다.** 이 상태로 복잡한 길을 가면 넘어질 위험(낙상)이 큽니다.
                                
                                **[개선 솔루션]**
                                1. **'멈춰서 말하기'**: 걷다가 전화가 오거나 누군가 말을 걸면, 반드시 **멈춰서** 대답하세요.
                                2. **'앉아서 훈련'**: 걷기 전에 집에서 TV를 보며 숫자 세기 연습부터 먼저 하세요.
                                """)
                                st.info("🧘‍♀️ **추천 활동: [맨발 걷기 & 명상]**\n\n"
                                        "복잡한 과제보다는 '감각'에 집중해야 합니다. 안전한 황토길에서 맨발로 걸으며 발바닥의 자극에만 오롯이 집중하는 '마인드풀 워킹'을 추천합니다.")

                        # CASE 3: 활동 부족
                        elif steps < 4000:
                            st.warning("⚠️ **[부족] 절대적 활동량 부족**")
                            with st.expander("🔍 상세 진단 및 추천 활동 보기", expanded=True):
                                st.markdown("""
                                **[상태 설명]**
                                하루 4천 보 미만은 뇌로 가는 산소와 영양분이 부족해질 수 있는 단계입니다. 다리 근육이 빠지면 뇌 용적도 같이 줄어든다는 연구 결과가 있습니다.
                                
                                **[개선 솔루션]**
                                거창한 운동이 아닙니다. 식사 후 **'혈당 스파이크 방지 산책'**으로 10분만 동네 한 바퀴를 돌아주세요.
                                """)
                                st.info("📸 **추천 활동: [동네 포토그래퍼]**\n\n"
                                        "운동이라고 생각하면 하기 싫습니다. 카메라를 들고 나가서 오늘 핀 꽃이나 특이한 간판을 3장 찍어오는 '수집 여행'을 떠나보세요.")

                        # CASE 4: 양호
                        else:
                            st.info("✅ **[양호] 밸런스 유지 중**")
                            with st.expander("🔍 상세 진단 및 추천 활동 보기", expanded=True):
                                st.markdown("""
                                **[상태 설명]**
                                신체와 인지 기능이 적절하게 균형을 이루고 있습니다. 여기서 조금만 더 노력하면 '최우수' 단계로 갈 수 있습니다.
                                
                                **[개선 솔루션]**
                                걸음 속도를 평소보다 **10%만 빠르게** 걸어보세요. 숨이 약간 찰 정도의 속도가 뇌 신경세포(BDNF) 생성을 촉진합니다.
                                """)
                                st.info("🎶 **추천 활동: [리듬 워킹]**\n\n"
                                        "좋아하는 트로트나 경쾌한 음악을 들으며 박자에 맞춰 걸어보세요. 청각 자극과 운동을 결합하면 뇌가 더 즐거워합니다.")

                        st.markdown("---")

                        # [분석 2] 수면 생체 리듬 분석
                        st.markdown("#### 2. 뇌 청소(Glymphatic) 시스템 분석")

                        # CASE 1: 최우수
                        if 7 <= c_dur <= 9 and 2 <= c_mid <= 4:
                            st.success("🌟 **[최우수] 뇌 청소 시스템 최적 가동**")
                            with st.expander("🔍 상세 진단 및 추천 활동 보기", expanded=True):
                                st.markdown("""
                                **[상태 설명]**
                                완벽합니다! 주무시는 동안 뇌 속의 노폐물을 청소하는 '글림프 시스템'이 최고 효율로 작동하고 있습니다.
                                
                                **[유지 전략]**
                                주말에도 지금처럼 기상 시간을 일정하게 유지해주세요. 규칙성이 최고의 보약입니다.
                                """)
                                st.info("🍵 **추천 활동: [모닝 티 테라피]**\n\n"
                                        "일어나자마자 따뜻한 물이나 차 한 잔을 마셔, 밤새 배출된 노폐물이 소변으로 잘 나가도록 도와주세요.")

                        # CASE 2: 리듬 불균형
                        elif 7 <= c_dur <= 9:
                            st.warning("⚠️ **[리듬 불균형] 사회적 시차(Social Jetlag)**")
                            with st.expander("🔍 상세 진단 및 추천 활동 보기", expanded=True):
                                st.markdown(f"""
                                **[상태 설명]**
                                잠은 충분히 잤지만 개운하지 않으시죠? 생체 시계가 꼬여 있어 멜라토닌 분비 타이밍이 맞지 않습니다. (현재 중간점: {c_mid:.1f}시)
                                
                                **[개선 솔루션]**
                                가장 중요한 건 **'아침 햇볕'**입니다. 기상 직후 1시간 이내에 창문을 열거나 밖으로 나가 **눈으로 빛을 쬐세요.**
                                """)
                                st.info("☀️ **추천 활동: [선샤인 샤워]**\n\n"
                                        "오전 10시~11시 사이, 공원 벤치에 앉아 20분간 햇볕을 쬐세요. 불면증 치료제보다 강력한 효과가 있습니다.")

                        # CASE 3: 수면 부족
                        elif c_dur < 6:
                            st.error("🚨 **[위험] 수면 부족 및 독소 축적**")
                            with st.expander("🔍 상세 진단 및 추천 활동 보기", expanded=True):
                                st.markdown("""
                                **[상태 설명]**
                                수면이 6시간보다 적으면 뇌가 청소를 다 끝내지 못하고 억지로 깨는 것과 같습니다. 이 찌꺼기가 쌓이면 기억력이 떨어집니다.
                                
                                **[개선 솔루션]**
                                1. **'낮잠 제한'**: 낮잠은 오후 3시 이전, 20분만 주무세요.
                                2. **'수면 압력'**: 저녁 식사 후 가벼운 산책을 해서 몸을 약간 피곤하게 만드세요.
                                """)
                                st.info("🛁 **추천 활동: [족욕 & 아로마]**\n\n"
                                        "자기 전 40도 정도의 따뜻한 물에 발을 담그고, 라벤더 향 등을 맡으며 뇌에게 '이제 잘 시간이야'라는 신호를 보내세요.")

                        # CASE 4: 과수면
                        else:
                            st.warning("⚠️ **[과수면] 활력 저하 주의**")
                            with st.expander("🔍 상세 진단 및 추천 활동 보기", expanded=True):
                                st.markdown("""
                                **[상태 설명]**
                                너무 오래 누워있는 것은 오히려 뇌를 멍하게 만들고, 우울감과 연관이 깊습니다. 수면의 질이 낮아 오래 누워만 있을 가능성도 있습니다.
                                
                                **[개선 솔루션]**
                                알람이 울리면 힘들더라도 벌떡 일어나서 이불을 개세요. 침대는 '잘 때만' 눕는 곳으로 뇌에 각인시켜야 합니다.
                                """)
                                st.info("🤝 **추천 활동: [소셜 다이닝]**\n\n"
                                        "혼자 계시면 더 주무시게 됩니다. 점심 약속을 잡거나 복지관에 나가서 사람들과 대화하며 활동량을 늘리세요.")

                    # === TAB 2: 종합 기록실 (그래프) ===
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
                        
                        # 안전한 기준선 생성
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