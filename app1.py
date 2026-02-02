import streamlit as st
import random

# 設定網頁標題與風格
st.set_page_config(
    page_title="AI 時代的猜數字", 
    page_icon="🤖",
    layout="centered"
)

# 套用一點 CSS 讓介面更有質感
st.markdown(unsafe_allow_html=True)
    <style>
    .main {
        background-color: #f0f2f6;
    }
    .stButton>button {
        border-radius: 20px;
        height: 3em;
        transition: 0.3s;
    }
    .stButton>button:hover {
        border-color: #ff4b4b;
        color: #ff4b4b;
    }
    </style>
    """, unsafe_allow_html=True)

# 初始化遊戲狀態
if "target" not in st.session_state:
    st.session_state.target = random.randint(1, 100)
if "history" not in st.session_state:
    st.session_state.history = []
if "game_over" not in st.session_state:
    st.session_state.game_over = False

def restart():
    st.session_state.target = random.randint(1, 100)
    st.session_state.history = []
    st.session_state.game_over = False

# 頁面內容
st.title("🤖 智慧型猜數字系統")
st.write(f"這是一個運行在雲端的 Python 應用。目前 AI 已經選好了一個 1~100 的數字。")

# 側邊欄：顯示紀錄
with st.sidebar:
    st.header("📊 猜測紀錄")
    if st.session_state.history:
        for i, val in enumerate(st.session_state.history):
            st.write(f"第 {i+1} 次: {val}")
    else:
        st.write("目前尚無紀錄")
    
    if st.button("重置遊戲"):
        restart()
        st.rerun()

# 主要遊戲區
if not st.session_state.game_over:
    # 使用 columns 讓排版漂亮一點
    col1, col2 = st.columns([3, 1])
    
    with col1:
        guess = st.number_input("輸入你的直覺數字：", min_value=1, max_value=100, step=1)
    
    with col2:
        st.write("##") # 墊高一點對齊按鈕
        submit = st.button("確認")

    if submit:
        st.session_state.history.append(guess)
        if guess < st.session_state.target:
            st.warning("🔮 太小了，再試一次！")
        elif guess > st.session_state.target:
            st.warning("🔮 太大了，挑戰極限！")
        else:
            st.success(f"🎊 恭喜！你猜中了！答案就是 {st.session_state.target}")
            st.balloons()
            st.session_state.game_over = True
else:
    st.info(f"遊戲結束！你總共猜了 {len(st.session_state.history)} 次。")
    if st.button("開啟下一局挑戰", use_container_width=True):
        restart()
        st.rerun()

# 頁尾說明
st.divider()
st.caption("Developed by Python Class Student | 伺服器運行中 🚀")
