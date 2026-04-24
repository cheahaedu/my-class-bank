import streamlit as st
import gspread
import json
import pandas as pd
from datetime import datetime

# ---------------------------------------------------------
# 0. 관리자 설정
# ---------------------------------------------------------
ADMIN_PASSWORD = "3309" # 👈 선생님 비밀번호

# 1. 구글 시트 연동
key_dict = json.loads(st.secrets["json_key"])
gc = gspread.service_account_from_dict(key_dict)
sh = gc.open("우리 반 경제 앱") #

ws_student = sh.worksheet("학생 명단")
ws_history = sh.worksheet("거래 내역")
try:
    ws_job = sh.worksheet("직업 관리")
except:
    st.error("'직업 관리' 시트 탭을 찾을 수 없습니다. 구글 시트 이름을 확인해주세요.")

# 2. 화면 설정
st.set_page_config(page_title="우리반 은행", page_icon="🏦", layout="wide")
st.title("🏦 우리반 모바일 뱅킹")

# 3. 데이터 가져오기
students_data = ws_student.get_all_records()
student_names = [row['이름'] for row in students_data]

# 사이드바 관리자 로그인
st.sidebar.title("🔐 관리 센터")
admin_mode = st.sidebar.checkbox("관리자 모드 활성화")

# ---------------------------------------------------------
# [관리자 모드]
# ---------------------------------------------------------
if admin_mode:
    admin_pw = st.sidebar.text_input("관리자 암호를 입력하세요", type="password")
    
    if admin_pw == ADMIN_PASSWORD:
        st.sidebar.success("✅ 관리자 인증 성공")
        st.header("👨‍🏫 학급 화폐 관리자 페이지")
        
        admin_tab1, admin_tab2, admin_tab3 = st.tabs(["💰 상금/벌금 부과", "💸 주급 일괄 지급", "📊 전체 현황"])
        
        with admin_tab1:
            st.subheader("📢 상금 및 벌금 부과")
            target_type = st.radio("적용 대상", ["개별 학생", "전체 학생"])
            selected_students = st.multiselect("학생 선택", student_names) if target_type == "개별 학생" else student_names
            
            action_type = st.selectbox("항목 선택", ["상금(입금)", "벌금(출금)", "세금(출금)", "직접 입력"])
            custom_action = st.text_input("항목 명칭 입력") if action_type == "직접 입력" else ""
            
            amount = st.number_input("금액", min_value=0, step=100, key="admin_amount")
            memo = st.text_input("상세 사유", placeholder="예: 주번 활동 우수")
            
            if st.button("💰 일괄 적용하기"):
                if not selected_students or amount <= 0:
                    st.warning("대상과 금액을 확인해주세요.")
                else:
                    with st.spinner("처리 중..."):
                        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        category = custom_action if action_type == "직접 입력" else action_type
                        rows = []
                        for student in selected_students:
                            if "입금" in action_type or action_type == "상금(입금)":
                                rows.append([now, "중앙은행", student, amount, f"[{category}] {memo}"])
                            else:
                                rows.append([now, student, "중앙은행", amount, f"[{category}] {memo}"])
                        ws_history.append_rows(rows)
                        st.success("처리가 완료되었습니다!")
                        st.balloons()

        with admin_tab2:
            st.subheader("🏢 직업별 주급 일괄 지급")
            st.info("이 버튼을 누르면 [학생 명단]의 직업을 확인하여 [직업 관리]에 적힌 금액을 모든 학생에게 입금합니다.")
            
            if st.button("💸 주급 이체 실행"):
                with st.spinner("데이터 분석 중..."):
                    jobs_data = ws_job.get_all_records()
                    job_pay_dict = {row['직업명']: row['주급'] for row in jobs_data}
                    
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    rows = []
                    for student in students_data:
                        s_name = student['이름']
                        s_job = student.get('직업', '')
                        
                        if s_job in job_pay_dict:
                            pay = job_pay_dict[s_job]
                            rows.append([now, "중앙은행", s_name, pay, f"[주급] {s_job} 급여"])
                    
                    if rows:
                        ws_history.append_rows(rows)
                        st.success(f"총 {len(rows)}명에게 주급 지급 완료!")
                        st.balloons()
                    else:
                        st.error("지급할 대상을 찾지 못했습니다. 시트의 직업명을 확인하세요.")

        with admin_tab3:
            st.subheader("📊 우리반 잔액 현황판")
            st.dataframe(pd.DataFrame(students_data), use_container_width=True, hide_index=True)
            
    elif admin_pw != "":
        st.sidebar.error("❌ 암호가 틀렸습니다.")

# ---------------------------------------------------------
# [학생용 모드]
# ---------------------------------------------------------
if not admin_mode or (admin_mode and admin_pw != ADMIN_PASSWORD):
    st.subheader("👤 학생 로그인")
    user_name = st.selectbox("이름 선택", ["선택해주세요"] + student_names)
    user_pw_input = st.text_input("비밀번호", type="password")

    if user_name != "선택해주세요" and user_pw_input:
        user_index = next((i for i, item in enumerate(students_data) if item["이름"] == user_name), None)
        user_info = students_data[user_index]
        
        if str(user_info.get('비밀번호')) == user_pw_input:
            st.success(f"🔓 {user_name}님 환영합니다!")
            tab1, tab2, tab3 = st.tabs(["💰 잔액 및 송금", "📜 내 거래 내역", "⚙️ 비밀번호 변경"])
            
            with tab1:
                st.metric(label="내 통장 잔액", value=f"{user_info['현재 잔액']} 원")
                st.divider()
                st.subheader("💸 친구에게 송금")
                receiver = st.selectbox("누구에게?", ["선택해주세요"] + [n for n in student_names if n != user_name])
                amount = st.number_input("금액", min_value=0, step=100)
                memo = st.text_input("사유")
                if st.button("보내기"):
                    if receiver != "선택해주세요" and 0 < amount <= user_info['현재 잔액']:
                        ws_history.append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_name, receiver, amount, memo])
                        st.success("송금 완료!")
                        st.balloons()
                    else: st.error("잔액이 부족하거나 정보를 확인하세요.")
            
            with tab2:
                all_h = ws_history.get_all_records()
                if all_h:
                    df = pd.DataFrame(all_h)
                    my_df = df[(df['보낸 사람'] == user_name) | (df['받는 사람'] == user_name)].iloc[::-1]
                    st.dataframe(my_df, use_container_width=True, hide_index=True)
            
            with tab3:
                new_pw = st.text_input("새 비밀번호(4자리)", type="password")
                if st.button("변경 저장"):
                    if len(new_pw) == 4 and new_pw.isdigit():
                        ws_student.update_cell(user_index + 2, 3, new_pw)
                        st.success("비밀번호가 변경되었습니다.")
        else: st.error("비밀번호가 틀렸습니다.")
