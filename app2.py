import random
import sys

def play_game():
    """猜數字遊戲主程式"""
    # 設定遊戲參數
    min_num = 1
    max_num = 100
    target = random.randint(min_num, max_num)
    attempts = 0
    max_attempts = 7  # 給朋友 7 次機會，增加緊張感

    print("=" * 30)
    print("      終極猜數字遊戲")
    print("=" * 30)
    print(f"我已經選好了一個 {min_num} 到 {max_num} 之間的數字。")
    print(f"你有 {max_attempts} 次機會，挑戰看看吧！\n")

    while attempts < max_attempts:
        try:
            # 取得玩家輸入
            guess_input = input(f"第 {attempts + 1} 次嘗試 - 請輸入數字: ")

            # 讓玩家可以輸入 'q' 提早結束
            if guess_input.lower() == 'q':
                print("玩家選擇中途退出遊戲。")
                break

            guess = int(guess_input)
            attempts += 1

            # 檢查是否超出範圍
            if guess < min_num or guess > max_num:
                print(f"哎呀！請輸入 {min_num} 到 {max_num} 之間的數字。")
                continue

            # 判斷結果
            if guess < target:
                print("太小了！再大一點。\n")
            elif guess > target:
                print("太大了！再小一點。\n")
            else:
                print(f"\n🎉 厲害喔！你只花了 {attempts} 次就猜對了！")
                print(f"正確答案就是: {target}")
                return # 猜對了直接結束函數

        except ValueError:
            print("❌ 錯誤：請輸入『整數數字』，不要輸入文字或其他符號。\n")

    if attempts >= max_attempts:
        print("\n😱 殘念！機會用完囉。")
        print(f"正確答案其實是: {target}")

if __name__ == "__main__":
    try:
        play_game()
    except KeyboardInterrupt:
        print("\n遊戲被強制中止。")

    # 這是打包成 .exe 的關鍵：防止程式跑完直接閃退
    print("\n" + "=" * 30)
    input("遊戲結束，按 Enter 鍵關閉視窗...")
    sys.exit()
