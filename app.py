import streamlit as st
import gspread
import json
import pandas as pd
from datetime import datetime

# ---------------------------------------------------------
# 0. 관리자 설정 및 시트 ID (교사/관리자 비밀번호 설정 ⭐)
# ---------------------------------------------------------
TEACHER_PASSWORD = "3309"       # 교사 전용 (마스터 권한)
MANAGER_PASSWORD = "st5678"  # 중간 관리자용 (총무/재무 권한)
SHEET_ID = "1a29VKE2DPG2u9-dhuZ5fCJXeO-jAyjObsItQg-eCTic"

# 1. 구글 시트 연동 (캐싱 적용)
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

# 2. 데이터 불러오기 함수 (캐싱 적용)
@st.cache_data(ttl=60)
def fetch_data(worksheet_name):
    return sh.worksheet(worksheet_name).get_all_records()

def clear_cache():
    st.cache_data.clear()

# ---------------------------------------------------------
# 3. 화면 기본 구성 및 데이터 로드 (변수 정의를 상단으로 ⭐)
# ---------------------------------------------------------
st.set_page_config(page_title="우리반 은행", page_icon="🏦", layout="wide")
st.title("🏦 우리반 모바일 뱅킹")

# 앱 실행에 필요한 핵심 데이터를 먼저 로드합니다 (에러 방지)
students_data = fetch_data("학생 명단")
student_names = [row['이름'] for row in students_data]

# 사이드바 관리자 로그인 UI
st.sidebar.title("🔐 관리 센터")
admin_mode = st.sidebar.checkbox("관리자 모드 활성화")

# ---------------------------------------------------------
# 4. 관리자 모드 로직 (권한 분리 ⭐)
# ---------------------------------------------------------
if admin_mode:
    input_pw = st.sidebar.text_input("관리자 암호를 입력하세요", type="password")
    
    # [A] 교사 권한 (모든 페이지 접근)
    if input_pw == TEACHER_PASSWORD:
        st.sidebar.success("👨‍🏫 교사 권한 인증 성공")
        st.header("👨‍🏫 교사용 마스터 관리 페이지")
        at1, at2, at3, at4 = st.tabs(["💰 상금/벌금", "💸 주급 일괄 지급", "📋 기록 검토", "📊 전체 현황"])
        
        with at1:
            target = st.radio("대상", ["개별", "전체"])
            sel_std = st.multiselect("학생 선택", student_names) if target == "개별" else student_names
            act = st.selectbox("항목", ["상금(입금)", "벌금(출금)", "세금(출금)"])
            amt = st.number_input("금액", min_value=0, step=100, key="teacher_amt")
            memo = st.text_input("사유", key="teacher_memo")
            if st.button("💰 일괄 적용"):
                rows = []
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                for s in sel_std:
                    if "입금" in act: rows.append([now, "중앙은행", s, amt, memo])
                    else: rows.append([now, s, "중앙은행", amt, memo])
                sh.worksheet("거래 내역").append_rows(rows)
                clear_cache()
                st.success("완료!")
                st.balloons()

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
            st.subheader("📋 중간 관리자(총무/재무) 작성 기록")
            logs = fetch_data("업무 기록")
            if logs: st.dataframe(pd.DataFrame(logs), use_container_width=True)
            else: st.info("기록이 없습니다.")

        with at4:
            st.dataframe(pd.DataFrame(students_data), use_container_width=True, hide_index=True)

    # [B] 중간 관리자 권한 (일 기록표 작성만 가능)
    elif input_pw == MANAGER_PASSWORD:
        st.sidebar.info("💼 중간 관리자 권한 인증 성공")
        st.header("📋 중간 관리자 업무 페이지")
        m_tab1, m_tab2 = st.tabs(["📝 일 기록표 작성", "📊 작성 내역 확인"])
        
        with m_tab1:
            with st.form("mgr_work_form"):
                worker = st.selectbox("학생 선택", student_names)
                w_date = st.date_input("업무 날짜", datetime.now())
                pay_val = st.number_input("최종 지급액 (주급-벌금)", step=10)
                detail = st.text_input("업무 수행 상태 상세 내역")
                if st.form_submit_button("💾 기록 저장"):
                    sh.worksheet("업무 기록").append_row([str(w_date), "중간관리자", worker, pay_val, detail])
                    clear_cache()
                    st.success("기록되었습니다.")
        with m_tab2:
            logs = fetch_data("업무 기록")
            if logs: st.table(pd.DataFrame(logs).tail(10))

    elif input_pw != "":
        st.sidebar.error("❌ 비밀번호가 틀렸습니다.")

# ---------------------------------------------------------
# 5. 학생용 모드 (로그인 시 직업/주급 먼저 노출 ⭐)
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
                st.caption("💡 주급은 선생님이 최종 승인 후 입금해 주십니다.")

            with t1:
                st.metric("현재 잔액", f"{user_info['현재 잔액']} 원")
                st.divider()
                rec = st.selectbox("송금 대상", [n for n in student_names if n != user_name])
                val = st.number_input("송금 금액", min_value=0, step=100)
                msg = st.text_input("송금 메모")
                if st.button("💸 송금 실행"):
                    if 0 < val <= user_info['현재 잔액']:
                        sh.worksheet("거래 내역").append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_name, rec, val, msg])
                        clear_cache()
                        st.success("송금 완료!")
                    else: st.error("잔고 부족")
            
            with t2:
                all_h = fetch_data("거래 내역")
                if all_h:
                    df = pd.DataFrame(all_h)
                    my_df = df[(df['보낸 사람'] == user_name) | (df['받는 사람'] == user_name)].iloc[::-1]
                    st.dataframe(my_df, use_container_width=True, hide_index=True)
            
            with t3:
                new_p = st.text_input("새 비번(4자리)", type="password")
                if st.button("비번 변경"):
                    if len(new_p) == 4 and new_p.isdigit():
                        idx = student_names.index(user_name) + 2
                        sh.worksheet("학생 명단").update_cell(idx, 3, new_p)
                        clear_cache()
                        st.success("변경되었습니다.")
        elif user_pw_input:
            st.error("비밀번호가 틀렸습니다.")
