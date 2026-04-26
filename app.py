import streamlit as st
import gspread
import json
import pandas as pd
from datetime import datetime

# ---------------------------------------------------------
# 0. 관리자 및 시트 설정
# ---------------------------------------------------------
ADMIN_PASSWORD = "3309" 
SHEET_ID = "1a29VKE2DPG2u9-dhuZ5fCJXeO-jAyjObsItQg-eCTic" # 👈 여기에 따옴표 포함해서 ID 입력

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
# 3. 화면 구성
# ---------------------------------------------------------
st.set_page_config(page_title="우리반 은행", page_icon="🏦", layout="wide")
st.title("🏦 우리반 모바일 뱅킹")

# 데이터 불러오기
students_data = fetch_data("학생 명단")
student_names = [row['이름'] for row in students_data]

# 사이드바 관리자 로그인
st.sidebar.title("🔐 관리 센터")
admin_mode = st.sidebar.checkbox("관리자 모드 활성화")

if admin_mode:
    admin_pw = st.sidebar.text_input("관리자 암호", type="password")
    if admin_pw == ADMIN_PASSWORD:
        st.sidebar.success("✅ 인증 성공")
        st.header("👨‍🏫 관리자 페이지")
        at1, at2, at3 = st.tabs(["💰 상금/벌금 부과", "💸 주급 일괄 지급", "📊 전체 현황"])
        
        with at1:
            target = st.radio("대상", ["개별", "전체"])
            sel_std = st.multiselect("학생 선택", student_names) if target == "개별" else student_names
            act = st.selectbox("항목", ["상금(입금)", "벌금(출금)", "세금(출금)", "직접 입력"])
            amt = st.number_input("금액", min_value=0, step=100)
            memo = st.text_input("사유")
            if st.button("💰 일괄 적용"):
                rows = []
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                for s in sel_std:
                    if "입금" in act: rows.append([now, "중앙은행", s, amt, memo])
                    else: rows.append([now, s, "중앙은행", amt, memo])
                sh.worksheet("거래 내역").append_rows(rows)
                clear_cache()
                st.success("지급/부과 완료!")
                st.balloons()

        with at2:
            if st.button("💸 모든 학생 주급 이체 실행"):
                jobs = fetch_data("직업 관리")
                job_pay = {r['직업명']: r['주급'] for r in jobs}
                rows = []
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                for s in students_data:
                    if s.get('직업') in job_pay:
                        rows.append([now, "중앙은행", s['이름'], job_pay[s['직업']], f"[주급] {s['직업']}"])
                if rows:
                    sh.worksheet("거래 내역").append_rows(rows)
                    clear_cache()
                    st.success("모든 학생에게 주급이 지급되었습니다!")
                    st.balloons()

        with at3:
            st.dataframe(pd.DataFrame(students_data), use_container_width=True, hide_index=True)
            
    elif admin_pw != "": st.sidebar.error("❌ 비밀번호 틀림")

# ---------------------------------------------------------
# [학생용 모드]
# ---------------------------------------------------------
if not admin_mode or (admin_mode and admin_pw != ADMIN_PASSWORD):
    user_name = st.selectbox("본인 이름을 선택하세요", ["선택해주세요"] + student_names)
    user_pw_input = st.text_input("비밀번호", type="password")

    if user_name != "선택해주세요" and user_pw_input:
        user_info = next((i for i in students_data if i["이름"] == user_name), None)
        
        if user_info and str(user_info.get('비밀번호')) == user_pw_input:
            st.success(f"🔓 {user_name}님 환영합니다!")
            
            # 탭 배치 변경: [나의 정보]를 가장 앞으로! ⭐
            t0, t1, t2, t3 = st.tabs(["📋 나의 직업/주급", "💰 잔액 및 송금", "📜 내역 확인", "⚙️ 비번 변경"])
            
            # --- 탭 0: 나의 직업 정보 (첫 화면) ---
            with t0:
                st.subheader(f"📋 {user_name}님의 직업 정보")
                
                # 직업 관리 데이터에서 주급 정보 가져오기
                jobs_data = fetch_data("직업 관리")
                job_pay_dict = {row['직업명']: row['주급'] for row in jobs_data}
                
                user_job = user_info.get('직업', '없음')
                user_pay = job_pay_dict.get(user_job, 0)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.info(f"나의 현재 직업\n### {user_job}")
                with col2:
                    st.success(f"이번 주 받을 급여\n### {user_pay} 원")
                
                st.write("---")
                st.caption("💡 주급은 선생님이 '주급 이체' 버튼을 누르시면 입금됩니다.")

            # --- 탭 1: 잔액 및 송금 (클릭해야 보임) ---
            with t1:
                st.metric("현재 내 통장 잔액", f"{user_info['현재 잔액']} 원")
                st.divider()
                st.subheader("💸 친구에게 돈 보내기")
                rec = st.selectbox("누구에게 보낼까요?", [n for n in student_names if n != user_name])
                val = st.number_input("보낼 금액", min_value=0, step=100)
                msg = st.text_input("송금 메모 (예: 간식값)")
                if st.button("💸 송금하기"):
                    if 0 < val <= user_info['현재 잔액']:
                        sh.worksheet("거래 내역").append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_name, rec, val, msg])
                        clear_cache()
                        st.success(f"{rec}님에게 {val}원을 보냈습니다!")
                        st.balloons()
                    else: st.error("잔액이 부족하거나 금액을 확인하세요.")
            
            with t2:
                all_h = fetch_data("거래 내역")
                if all_h:
                    df = pd.DataFrame(all_h)
                    my_df = df[(df['보낸 사람'] == user_name) | (df['받는 사람'] == user_name)].iloc[::-1]
                    st.dataframe(my_df, use_container_width=True, hide_index=True)
            
            with t3:
                new_p = st.text_input("새 비번(4자리)", type="password")
                if st.button("변경 저장"):
                    if len(new_p) == 4 and new_p.isdigit():
                        idx = student_names.index(user_name) + 2
                        sh.worksheet("학생 명단").update_cell(idx, 3, new_p)
                        clear_cache()
                        st.success("비밀번호가 변경되었습니다.")
        elif user_pw_input: st.error("비밀번호가 틀렸습니다.")
