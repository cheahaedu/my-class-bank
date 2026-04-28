import streamlit as st
import gspread
import json
import pandas as pd
from datetime import datetime
import plotly.express as px

# ---------------------------------------------------------
# 0. 설정 (비밀번호 및 시트 ID)
# ---------------------------------------------------------
TEACHER_PASSWORD = "3309"
MANAGER_PASSWORD = "st5678"
SHEET_ID = "1a29VKE2DPG2u9-dhuZ5fCJXeO-jAyjObsItQg-eCTic"

# 1. 구글 시트 연동 및 함수 정의
@st.cache_resource
def get_gspread_client():
    key_dict = json.loads(st.secrets["json_key"])
    return gspread.service_account_from_dict(key_dict)

try:
    gc = get_gspread_client()
    sh = gc.open_by_key(SHEET_ID)
except Exception as e:
    st.error(f"시트 연결 실패: {e}")
    st.stop()

@st.cache_data(ttl=60)
def fetch_data(worksheet_name):
    return sh.worksheet(worksheet_name).get_all_records()

def clear_cache():
    st.cache_data.clear()

# ---------------------------------------------------------
# 2. 화면 기본 설정 및 데이터 로드 (⭐ 중요: 가장 먼저 실행)
# ---------------------------------------------------------
st.set_page_config(page_title="우리반 은행", page_icon="🏦", layout="wide")
st.title("🏦 우리반 모바일 뱅킹 V3")

# 데이터 불러오기
students_data = fetch_data("학생 명단")
student_names = [row['이름'] for row in students_data]

# ---------------------------------------------------------
# 3. 사이드바 구성 (⭐ admin_mode 변수 정의 위치)
# ---------------------------------------------------------
st.sidebar.title("🔐 관리 센터")

# [교사 관리자]
t_admin = st.sidebar.checkbox("👨‍🏫 교사 마스터 모드")
t_pw = ""
if t_admin:
    t_pw = st.sidebar.text_input("교사 암호", type="password", key="t_pw")

# [중간 관리자]
m_admin = st.sidebar.checkbox("💼 중간 관리자 모드")
m_pw = ""
if m_admin:
    m_pw = st.sidebar.text_input("중간관리자 암호", type="password", key="m_pw")

# 🛑 에러 방지를 위해 통합 변수 생성
admin_mode = t_admin or m_admin 

st.sidebar.divider()

# ---------------------------------------------------------
# 4. 교사 마스터 페이지
# ---------------------------------------------------------
if t_admin and t_pw == TEACHER_PASSWORD:
    st.header("👨‍🏫 교사용 마스터 관리 페이지")
    at1, at2, at3, at4 = st.tabs(["💰 상금/벌금 부과", "💸 주급 이체", "📋 기록 검토", "📊 전체 현황"])
    
    with at1:
        st.subheader("📢 상금/벌금/세금 일괄 부과")
        col_btn1, col_btn2 = st.columns([1, 5])
        if col_btn1.button("✅ 전체 선택"): st.session_state.all_sel = True
        if col_btn2.button("❌ 전체 해제"): st.session_state.all_sel = False
        if 'all_sel' not in st.session_state: st.session_state.all_sel = False
        
        selected_stds = []
        cols = st.columns(5)
        for idx, name in enumerate(student_names):
            if cols[idx % 5].checkbox(name, value=st.session_state.all_sel):
                selected_stds.append(name)
        
        st.divider()
        c1, c2, c3 = st.columns(3)
        act_type = c1.selectbox("항목", ["상금(입금)", "벌금(출금)", "세금(출금)"])
        amount = c2.number_input("금액", step=100, key="t_amt")
        memo = c3.text_input("사유", key="t_memo")

        if st.button("💰 선택한 학생에게 적용"):
            if not selected_stds: st.warning("대상을 선택하세요.")
            else:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                rows = [[now, "중앙은행" if "입금" in act_type else s, s if "입금" in act_type else "중앙은행", amount, memo] for s in selected_stds]
                sh.worksheet("거래 내역").append_rows(rows)
                clear_cache()
                st.success(f"{len(selected_stds)}명 처리 완료!")

    with at2:
        if st.button("💸 전교생 주급 일괄 지급 실행"):
            jobs = fetch_data("직업 관리")
            job_pay = {r['직업명']: r['주급'] for r in jobs}
            rows = []
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for s in students_data:
                if s.get('직업') in job_pay:
                    rows.append([now, "중앙은행", s['이름'], job_pay[s['직업']], f"[주급] {s['직업']}"])
            sh.worksheet("거래 내역").append_rows(rows)
            clear_cache()
            st.success("지급 완료!")

    with at3:
        st.subheader("📋 중간 관리자 작성 기록")
        logs = fetch_data("업무 기록")
        if logs: st.dataframe(pd.DataFrame(logs), use_container_width=True)
        else: st.info("기록이 없습니다.")

    with at4:
        st.subheader("📊 학급 재산 현황")
        df_std = pd.DataFrame(students_data)
        fig = px.bar(df_std, x='이름', y='현재 잔액', color='현재 잔액', title="학생별 잔액 분포")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df_std, use_container_width=True, hide_index=True)

# ---------------------------------------------------------
# 5. 중간 관리자 페이지
# ---------------------------------------------------------
elif m_admin and m_pw == MANAGER_PASSWORD:
    st.header("💼 중간 관리자 업무 페이지")
    with st.expander("📝 새 업무 기록 작성하기", expanded=True):
        with st.form("mgr_form"):
            col1, col2, col3 = st.columns(3)
            m_worker = col1.selectbox("대상 학생", student_names)
            m_amt = col2.number_input("지급액(주급-벌금)", step=10)
            m_date = col3.date_input("날짜", datetime.now())
            m_memo = st.text_input("상세 내역")
            if st.form_submit_button("💾 기록 저장"):
                sh.worksheet("업무 기록").append_row([str(m_date), "중간관리자", m_worker, m_amt, m_memo])
                clear_cache()
                st.success("저장되었습니다.")
    
    st.subheader("📜 업무 기록 리스트")
    logs = fetch_data("업무 기록")
    if logs:
        df_log = pd.DataFrame(logs)
        st.dataframe(df_log.iloc[::-1], use_container_width=True)

# ---------------------------------------------------------
# 6. 학생용 모드 (⭐ admin_mode가 False일 때 실행)
# ---------------------------------------------------------
if not admin_mode:
    user_name = st.selectbox("본인 이름을 선택하세요", ["선택해주세요"] + student_names)
    user_pw_input = st.text_input("비밀번호", type="password")

    if user_name != "선택해주세요" and user_pw_input:
        user_info = next((i for i in students_data if i["이름"] == user_name), None)
        
        if user_info and str(user_info.get('비밀번호')) == user_pw_input:
            st.success(f"🔓 {user_name}님 환영합니다!")
            t0, t1, t2, t3 = st.tabs(["📋 나의 직업/주급", "💰 잔액 및 송금", "📜 내역 확인", "⚙️ 비번 변경"])
            
            with t0:
                jobs_data = fetch_data("직업 관리")
                job_pay_dict = {row['직업명']: row['주급'] for row in jobs_data}
                user_job = user_info.get('직업', '없음')
                user_pay = job_pay_dict.get(user_job, 0)
                c1, c2 = st.columns(2)
                c1.metric("현재 직업", user_job)
                c2.metric("이번 주급", f"{user_pay} 원")

            with t1:
                st.metric("현재 잔액", f"{user_info['현재 잔액']} 원")
                rec = st.selectbox("송금 대상", [n for n in student_names if n != user_name])
                val = st.number_input("금액", min_value=0, step=100)
                msg = st.text_input("메모")
                if st.button("💸 송금 실행"):
                    if 0 < val <= user_info['현재 잔액']:
                        sh.worksheet("거래 내역").append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_name, rec, val, msg])
                        clear_cache()
                        st.success("완료!")
                    else: st.error("잔액 부족")
            
            with t2:
                all_h = fetch_data("거래 내역")
                if all_h:
                    df = pd.DataFrame(all_h)
                    my_df = df[(df['보낸 사람'] == user_name) | (df['받는 사람'] == user_name)].iloc[::-1]
                    st.dataframe(my_df, use_container_width=True, hide_index=True)
            
            with t3:
                new_p = st.text_input("새 비번(4자리)", type="password")
                if st.button("변경 저장"):
                    idx = student_names.index(user_name) + 2
                    sh.worksheet("학생 명단").update_cell(idx, 3, new_p)
                    clear_cache()
                    st.success("변경 완료!")
        elif user_pw_input:
            st.error("비밀번호가 틀렸습니다.")
