import json
import os
from datetime import datetime

class AccountingApp:
    def __init__(self):
        self.filename = 'accounting_data.json'
        self.records = self.load_data()
    
    def load_data(self):
        """載入資料"""
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def save_data(self):
        """儲存資料"""
        with open(self.filename, 'w', encoding='utf-8') as f:
            json.dump(self.records, f, ensure_ascii=False, indent=2)
    
    def add_record(self):
        """新增記錄"""
        print("\n=== 新增記錄 ===")
        
        # 選擇類型
        while True:
            record_type = input("類型 (1.收入 / 2.支出): ").strip()
            if record_type in ['1', '2']:
                record_type = '收入' if record_type == '1' else '支出'
                break
            print("請輸入 1 或 2")
        
        # 輸入金額
        while True:
            try:
                amount = float(input("金額: "))
                if amount > 0:
                    break
                print("金額必須大於 0")
            except ValueError:
                print("請輸入有效的數字")
        
        # 選擇類別
        if record_type == '收入':
            categories = ['薪水', '獎金', '投資', '其他']
        else:
            categories = ['飲食', '交通', '購物', '娛樂', '醫療', '其他']
        
        print("\n類別選項:", ' / '.join([f"{i+1}.{c}" for i, c in enumerate(categories)]))
        category_input = input("選擇類別編號或自行輸入: ").strip()
        
        if category_input.isdigit() and 1 <= int(category_input) <= len(categories):
            category = categories[int(category_input) - 1]
        else:
            category = category_input if category_input else '其他'
        
        # 備註
        note = input("備註 (可選): ").strip()
        
        # 建立記錄
        record = {
            'id': len(self.records) + 1,
            'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'type': record_type,
            'amount': amount,
            'category': category,
            'note': note
        }
        
        self.records.append(record)
        self.save_data()
        print(f"\n✓ 已新增{record_type}記錄：${amount:,.0f}")
    
    def view_records(self):
        """查看所有記錄"""
        if not self.records:
            print("\n目前沒有任何記錄")
            return
        
        print("\n=== 所有記錄 ===")
        print(f"{'編號':<5} {'日期':<17} {'類型':<6} {'金額':<12} {'類別':<10} {'備註'}")
        print("-" * 80)
        
        for record in self.records:
            print(f"{record['id']:<5} {record['date']:<17} {record['type']:<6} "
                  f"${record['amount']:>10,.0f} {record['category']:<10} {record['note']}")
    
    def view_statistics(self):
        """查看統計"""
        if not self.records:
            print("\n目前沒有任何記錄")
            return
        
        income = sum(r['amount'] for r in self.records if r['type'] == '收入')
        expense = sum(r['amount'] for r in self.records if r['type'] == '支出')
        balance = income - expense
        
        print("\n=== 統計資訊 ===")
        print(f"總收入：${income:>12,.0f}")
        print(f"總支出：${expense:>12,.0f}")
        print(f"{'結餘：' if balance >= 0 else '虧損：'}${abs(balance):>12,.0f}")
        print(f"記錄筆數：{len(self.records)} 筆")
    
    def delete_record(self):
        """刪除記錄"""
        if not self.records:
            print("\n目前沒有任何記錄")
            return
        
        self.view_records()
        
        try:
            record_id = int(input("\n請輸入要刪除的記錄編號: "))
            record = next((r for r in self.records if r['id'] == record_id), None)
            
            if record:
                self.records.remove(record)
                self.save_data()
                print(f"\n✓ 已刪除記錄 #{record_id}")
            else:
                print("\n✗ 找不到該記錄")
        except ValueError:
            print("\n✗ 請輸入有效的編號")
    
    def clear_all(self):
        """清除所有記錄"""
        confirm = input("\n確定要清除所有記錄嗎？(y/n): ").lower()
        if confirm == 'y':
            self.records = []
            self.save_data()
            print("\n✓ 已清除所有記錄")
        else:
            print("\n✗ 已取消")
    
    def run(self):
        """主程式"""
        while True:
            print("\n" + "=" * 40)
            print("💰 記帳 App")
            print("=" * 40)
            print("1. 新增記錄")
            print("2. 查看所有記錄")
            print("3. 查看統計")
            print("4. 刪除記錄")
            print("5. 清除所有記錄")
            print("6. 退出")
            print("=" * 40)
            
            choice = input("請選擇功能 (1-6): ").strip()
            
            if choice == '1':
                self.add_record()
            elif choice == '2':
                self.view_records()
            elif choice == '3':
                self.view_statistics()
            elif choice == '4':
                self.delete_record()
            elif choice == '5':
                self.clear_all()
            elif choice == '6':
                print("\n感謝使用！再見👋")
                break
            else:
                print("\n✗ 無效的選項，請輸入 1-6")

# 執行程式
if __name__ == "__main__":
    app = AccountingApp()
    app.run()
