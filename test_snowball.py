import streamlit as st  # 匯入 Streamlit 套件，讓我們可以做網頁式應用

import pandas as pd     # 匯入 pandas 套件，用來顯示漂亮的表格

# 設定網頁標題
st.title("複利滾雪球投資計算器")

# 建立三個輸入框，讓用戶可以調整初始本金、年化報酬率、投資年數
# 使用 slider 讓調整體驗更直覺

# 初始本金輸入框（單位：萬元）
principal = st.slider('初始本金（萬元）', min_value=1, max_value=1000, value=100)
# 這一行如果想要完全對照之前 CLI 版 (文字介面) 的行為：
# principal = float(input("請輸入本金："))  # 讀使用者輸入的本金，並轉成浮點數（可有小數）
# 但在 Streamlit 版裡面，上面已經用 st.slider 讓使用者輸入本金，所以不用 input 了
# 如果真的要用，可以這樣：
# principal = float(st.text_input("請輸入本金：", value="100"))

# 預期年化報酬率輸入框（百分比）
rate = st.slider('預期年化報酬率（%）', min_value=1.0, max_value=20.0, value=7.0, step=0.1)

# 投資年數輸入框
years = st.slider('投資年數（年）', min_value=1, max_value=50, value=20)

# 建立一個按鈕，按下後才運算結果
if st.button("開始滾雪球"):
    # 建立一個 list 來存每年結束時的本金
    amounts = []

    # 用 for 逐年計算，每年都讓本金複利增長
    for year in range(1, years + 1):
        # 複利公式：本金 * (1 + 年化報酬率/100) 的 year 次方
        amount = principal * (1 + rate / 100) ** year
        # 把這筆金額加進列表，順便記錄本年資料
        amounts.append({"年份": year, "本金（萬元）": round(amount, 2)})

    # 利用 pandas DataFrame 把資料整理成表格
    df = pd.DataFrame(amounts)

    # 顯示漂亮的表格，index=False 讓表格不要再自帶序號
    st.dataframe(df, use_container_width=True)

    # 取得最後一年本金，準備顯示總結
    final_amount = round(amounts[-1]["本金（萬元）"], 2)
    # 用大白話顯示成果
    st.subheader(f"經過 {years} 年後，您的本金將會滾成 {final_amount} 萬元！")

# －－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－
# 大白話解釋：
# 這支小程式用 Streamlit 製作，畫面上三個滑桿分別讓你設定本金、年化報酬率、投資年數，
# 按下「開始滾雪球」就用複利公式一路算到第 N 年，
# 每年計算後的本金都記進 pandas 的 DataFrame，並用表格顯示每年會長多高，
# 最後用大的標題總結你投資下去會滾到多少，讓複利雪球的力量一目了然！
