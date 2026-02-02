import streamlit as st
import random

# 設定網頁標題與風格
st.set_page_config(
    page_title="我們的 Python 課作品", 
    page_icon="🐍",
    layout="centered"
)

# 初始化遊戲狀態（這是確保網頁不會報錯的關鍵）
if "target_number" not in st.session_state:
    st.session_state.target_number = random.randint(1, 100)
if "counter" not in st.session_state:
    st.session_state.counter = 0
if "is_finished" not in st.session_state:
    st.session_state.is_finished = False
if "msg" not in st.session_state:
    st.session_state.msg = "請在下方輸入 1~100 的數字開始遊戲！"

def reset_game():
    """重新開始遊戲的函式"""
    st.session_state.target_number = random.randint(1, 100)
    st.session_state.counter = 0
    st.session_state.is_finished = False
    st.session_state.msg = "遊戲已重置，請開始新的一局！"

# UI 介面設計
st.title("🐍 Python 課成果展示：猜數字遊戲")
st.info(f"💡 目前狀態：{st.session_state.msg}")

if not st.session_state.is_finished:
    # 數字輸入框
    user_input = st.number_input("你覺得是多少？", min_value=1, max_value=100, key="input_box")
    
    if st.button("我猜這個！", use_container_width=True):
        st.session_state.counter += 1
        if user_input < st.session_state.target_number:
            st.session_state.msg = f"太小了！(已猜 {st.session_state.counter} 次)"
        elif user_input > st.session_state.target_number:
            st.session_state.msg = f"太大了！(已猜 {st.session_state.counter} 次)"
        else:
            st.session_state.msg = f"🎉 答對了！答案就是 {st.session_state.target_number}！"
            st.session_state.is_finished = True
            st.balloons()
        st.rerun() # 強制刷新畫面顯示最新訊息
else:
    st.success(st.session_state.msg)
    st.write(f"你總共花了 {st.session_state.counter} 次嘗試。")
    if st.button("再玩一局", on_click=reset_game, use_container_width=True):
        st.rerun()

# 頁尾資訊
st.divider()
st.caption("這是一個由 Streamlit 驅動的 Python 網頁應用程式。")
