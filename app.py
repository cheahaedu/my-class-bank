import streamlit as st
import gspread
import json
from datetime import datetime

# 1. 구글 시트 연동
key_dict = json.loads(st.secrets["json_key"])
gc = gspread.service_account_from_dict(key_dict)
sh = gc.open("우리 반 경제 앱") # ⭐️ 실제 시트 이름으로 수정

ws_student = sh.worksheet("학생 명단")
ws_history = sh.worksheet("거래 내역")

# 2. 화면 설정
st.set_page_config(page_title="우리반 은행", page_icon="🏦")
st.title("🏦 우리반 모바일 뱅킹")

# 3. 데이터 가져오기
students_data = ws_student.get_all_records()
student_names = [row['이름'] for row in students_data]

# 로그인 섹션
st.subheader("👤 로그인")
user_name = st.selectbox("본인의 이름을 선택하세요", ["선택해주세요"] + student_names)
user_pw_input = st.text_input("비밀번호 4자리를 입력하세요", type="password")

if user_name != "선택해주세요" and user_pw_input:
    # 해당 학생 데이터 찾기 (몇 번째 줄인지 확인하기 위해 enumerate 사용)
    user_index = next((i for i, item in enumerate(students_data) if item["이름"] == user_name), None)
    user_info = students_data[user_index]
    
    # 비밀번호 검증
    if str(user_info.get('비밀번호')) == user_pw_input:
        st.success(f"🔓 인증되었습니다. {user_name}님!")
        
        # 사이드바 또는 하단에 탭 구성 (잔액확인/송금/비밀번호변경)
        menu = st.tabs(["💰 잔액 및 송금", "⚙️ 비밀번호 변경"])
        
        # --- 탭 1: 잔액 및 송금 ---
        with menu[0]:
            st.metric(label="내 통장 잔액", value=f"{user_info['현재 잔액']} 원")
            st.divider()
            
            st.subheader("💸 송금하기")
            receiver_list = [name for name in student_names if name != user_name]
            receiver = st.selectbox("누구에게 보낼까요?", ["선택해주세요"] + receiver_list)
            amount = st.number_input("보낼 금액", min_value=0, step=100)
            memo = st.text_input("송금 사유")

            if st.button("보내기"):
                if receiver != "선택해주세요" and amount > 0:
                    if amount <= user_info['현재 잔액']:
                        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        ws_history.append_row([now, user_name, receiver, amount, memo])
                        st.success(f"{receiver}님에게 {amount}원을 보냈습니다!")
                        st.balloons()
                    else:
                        st.error("잔액이 부족합니다.")
        
        # --- 탭 2: 비밀번호 변경 ---
        with menu[1]:
            st.subheader("⚙️ 비밀번호 변경")
            new_pw = st.text_input("새로운 비밀번호 4자리", type="password", maxlength=4)
            confirm_pw = st.text_input("새 비밀번호 확인", type="password", maxlength=4)
            
            if st.button("비밀번호 변경하기"):
                if len(new_pw) == 4 and new_pw.isdigit():
                    if new_pw == confirm_pw:
                        # 구글 시트의 해당 셀 위치 계산 (헤더가 1번줄, 데이터는 2번줄부터 시작)
                        # 비밀번호 열이 C열이라면 3번째 열입니다.
                        row_to_update = user_index + 2 
                        col_to_update = 3 # ⭐️ 만약 시트에서 '비밀번호'가 C열이 아니면 이 숫자를 바꾸세요 (A=1, B=2, C=3...)
                        
                        ws_student.update_cell(row_to_update, col_to_update, new_pw)
                        st.success("✅ 비밀번호가 안전하게 변경되었습니다! 다음 로그인부터 사용하세요.")
                    else:
                        st.error("❌ 새 비밀번호가 서로 일치하지 않습니다.")
                else:
                    st.warning("⚠️ 숫자 4자리로 입력해주세요.")
    else:
        st.error("❌ 비밀번호가 틀렸습니다.")
