import streamlit as st
import gspread
import json
import pandas as pd
from datetime import datetime

# ---------------------------------------------------------
# 0. 관리자 및 시트 설정
# ---------------------------------------------------------
ADMIN_PASSWORD = "teacher1234"  # 선생님 비밀번호
SHEET_ID = "여기에_선생님_시트_ID를_입력하세요" # 주소창 d/ 와 /edit 사이 문자열

# 1. 구글 시트 연동 (최초 1회 실행)
@st.cache_resource
def get_gspread_client():
    key_dict = json.loads(st.secrets["json_key"])
    return gspread.service_account_from_dict(key_dict)

try:
    gc = get_gspread_client()
    sh = gc.open_by_key(1a29VKE2DPG2u9-dhuZ5fCJXeO-jAyjObsItQg-eCTic) # ⭐️ 반드시 시트 ID 사용

except gspread.exceptions.SpreadsheetNotFound:
    st.error("❌ 시트 파일을 찾을 수 없습니다. 코드의 SHEET_ID를 다시 확인해주세요.")
    st.stop()
except gspread.exceptions.APIError as e:
    st.error("❌ 권한 에러! 구글 시트 [공유] 설정에서 봇 이메일이 편집자로 잘 등록되었는지 확인하세요.")
    st.stop()
except Exception as e:
    st.error(f"❌ 알 수 없는 연결 에러 발생: {e}")
    st.stop()

# ---------------------------------------------------------
# 2. 데이터 불러오기 함수 (캐싱 적용 ⭐)
# ---------------------------------------------------------
# ttl=60은 60초 동안 데이터를 기억한다는 뜻입니다.
# 25명이 동시에 들어와도 1명만 시트에서 읽어오고 나머지는 기억한 걸 봅니다.
@st.cache_data(ttl=60)
def fetch_data(worksheet_name):
    return sh.worksheet(worksheet_name).get_all_records()

# 데이터 갱신이 필요할 때 호출하는 함수 (송금, 주급 등 실행 후)
def clear_cache():
    st.cache_data.clear()

# ---------------------------------------------------------
# 3. 화면 구성
# ---------------------------------------------------------
st.set_page_config(page_title="우리반 은행", page_icon="🏦", layout="wide")
st.title("🏦 우리반 모바일 뱅킹 (최적화 버전)")

# 최신 데이터 불러오기
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
        at1, at2, at3 = st.tabs(["💰 상금/벌금", "💸 주급 지급", "📊 전체 현황"])
        
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
                clear_cache() # 데이터가 바뀌었으므로 캐시 삭제
                st.success("완료!")
                st.balloons()

        with at2:
            if st.button("💸 모든 학생 주급 이체"):
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
            st.dataframe(pd.DataFrame(students_data), use_container_width=True, hide_index=True)
            
    elif admin_pw != "": st.sidebar.error("❌ 비밀번호 틀림")

# ---------------------------------------------------------
# [학생용 모드]
# ---------------------------------------------------------
if not admin_mode or (admin_mode and admin_pw != ADMIN_PASSWORD):
    user_name = st.selectbox("이름 선택", ["선택해주세요"] + student_names)
    user_pw_input = st.text_input("비밀번호", type="password")

    if user_name != "선택해주세요" and user_pw_input:
        user_info = next((i for i in students_data if i["이름"] == user_name), None)
        if user_info and str(user_info.get('비밀번호')) == user_pw_input:
            st.success(f"🔓 {user_name}님 환영합니다!")
            t1, t2, t3 = st.tabs(["💰 잔액/송금", "📜 내역", "⚙️ 비번변경"])
            
            with t1:
                st.metric("내 잔액", f"{user_info['현재 잔액']} 원")
                st.divider()
                rec = st.selectbox("받는 사람", [n for n in student_names if n != user_name])
                val = st.number_input("송금액", min_value=0, step=100)
                msg = st.text_input("메모")
                if st.button("💸 보내기"):
                    if 0 < val <= user_info['현재 잔액']:
                        sh.worksheet("거래 내역").append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_name, rec, val, msg])
                        clear_cache()
                        st.success("송금 성공!")
                        st.balloons()
                    else: st.error("잔액 부족")
            
            with t2:
                all_h = fetch_data("거래 내역")
                if all_h:
                    df = pd.DataFrame(all_h)
                    my_df = df[(df['보낸 사람'] == user_name) | (df['받는 사람'] == user_name)].iloc[::-1]
                    st.dataframe(my_df, use_container_width=True, hide_index=True)
            
            with t3:
                new_p = st.text_input("새 비번(4자리)", type="password")
                if st.button("저장"):
                    if len(new_p) == 4 and new_p.isdigit():
                        idx = student_names.index(user_name) + 2
                        sh.worksheet("학생 명단").update_cell(idx, 3, new_p)
                        clear_cache()
                        st.success("변경 완료!")
        elif user_pw_input: st.error("비밀번호 틀림")
