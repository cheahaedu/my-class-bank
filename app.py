import streamlit as st
import gspread
import json
from datetime import datetime

# 1. 구글 시트 연동
key_dict = json.loads(st.secrets["json_key"])
gc = gspread.service_account_from_dict(key_dict)
sh = gc.open("우리 반 경제 앱") # ⭐️ 실제 이름으로 변경!

ws_student = sh.worksheet("학생 명단")
ws_history = sh.worksheet("거래 내역")

# 2. 화면 설정
st.set_page_config(page_title="우리반 은행", page_icon="🏦")
st.title("🏦 우리반 모바일 뱅킹")

# 3. 데이터 가져오기
students_data = ws_student.get_all_records()
student_names = [row['이름'] for row in students_data]

# ==========================================
# 👤 로그인 섹션 (이름 + 비밀번호)
# ==========================================
st.subheader("👤 로그인")
user_name = st.selectbox("본인의 이름을 선택하세요", ["선택해주세요"] + student_names)
user_pw = st.text_input("비밀번호 4자리를 입력하세요", type="password") # 입력 시 별표(*)로 표시됨

if user_name != "선택해주세요" and user_pw:
    # 선택한 학생의 정보 찾기
    user_info = next((item for item in students_data if item["이름"] == user_name), None)
    
    # 🔐 비밀번호 검증 (시트의 '비밀번호' 열과 비교)
    # 시트의 숫자가 문자로 인식될 수 있어 str()로 변환하여 비교합니다.
    if str(user_info.get('비밀번호')) == user_pw:
        st.success(f"🔓 인증되었습니다. {user_name}님 환영합니다!")
        
        # --- 잔액 표시 ---
        st.metric(label="내 통장 잔액", value=f"{user_info['현재 잔액']} 원")
        
        # --- 송금 기능 (기존과 동일) ---
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
            else:
                st.warning("정보를 올바르게 입력해주세요.")
    else:
        # 비밀번호가 틀렸을 때
        st.error("❌ 비밀번호가 일치하지 않습니다. 다시 입력해주세요.")
