from playwright.sync_api import sync_playwright
import time
import csv
import os
from datetime import datetime, time as dt_time, timedelta, timezone
import requests

# ログイン情報
LOGIN_ID = "09024122802"
PASSWORD = "Astroboy01"

# Discord Webhook設定
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")

# JSTタイムゾーン設定 (UTC+9)
JST = timezone(timedelta(hours=9))

def now_jst():
    """現在時刻をJSTで返す"""
    return datetime.now(timezone.utc).astimezone(JST)

def send_discord_webhook(message):
    """Discord Webhookで通知を送信する関数"""
    if not DISCORD_WEBHOOK_URL:
        print("警告: DISCORD_WEBHOOK_URLが設定されていません。通知を送信できません。")
        return False
    
    try:
        data = {
            "content": message
        }
        
        response = requests.post(DISCORD_WEBHOOK_URL, json=data)
        
        if response.status_code == 204 or response.status_code == 200:
            print(f"Discord通知を送信しました: {message[:50]}...")
            return True
        else:
            print(f"Discord通知送信エラー: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"Discord通知送信エラー: {e}")
        return False

# 翌週金曜日の日付を計算する関数
def get_next_friday():
    """翌週金曜日の日付をYYYY-MM-DD形式で返す"""
    today = now_jst()
    # 今日が何曜日か（0=月曜日, 4=金曜日, 6=日曜日）
    days_until_friday = (4 - today.weekday()) % 7
    if days_until_friday == 0:
        # 今日が金曜日なら翌週の金曜日
        days_until_friday = 7
    next_friday = today + timedelta(days=days_until_friday)
    return next_friday.strftime('%Y-%m-%d')

# 次の日曜日を計算する関数
def get_next_sunday():
    """次の日曜日の日付をYYYY-MM-DD形式で返す"""
    today = now_jst()
    # 今日が何曜日か（0=月曜日, 6=日曜日）
    days_until_sunday = (6 - today.weekday()) % 7
    if days_until_sunday == 0:
        # 今日が日曜日なら翌週の日曜日
        days_until_sunday = 7
    next_sunday = today + timedelta(days=days_until_sunday)
    return next_sunday.strftime('%Y-%m-%d')

# 翌週金曜日の予定が公開されているかチェックする関数
def check_next_friday_schedule_published(page):
    """翌週金曜日の予定が公開されているかチェックする。公開されていればTrue、未公開ならFalseを返す"""
    try:
        next_friday = get_next_friday()
        print(f"翌週金曜日（{next_friday}）の予定公開状況をチェックします...")
        
        # 日付を選択
        date_select = page.locator('select[name="date"]')
        options = date_select.locator('option').all()
        
        available_dates = []
        for option in options:
            value = option.get_attribute('value')
            if value:
                available_dates.append(value)
        
        if next_friday in available_dates:
            page.select_option('select[name="date"]', next_friday)
            print(f"翌週金曜日（{next_friday}）を選択しました")
            time.sleep(2)
            
            # セラピストリストを確認
            cast_select = page.locator('select[name="cast"]')
            cast_options = cast_select.locator('option').all()
            
            is_only_free = True
            for option in cast_options:
                value = option.get_attribute('value')
                if value and value != '0':
                    is_only_free = False
                    break
            
            if is_only_free:
                print(f"翌週金曜日（{next_friday}）のセラピスト予定はまだ公開されていません")
                return False
            else:
                print(f"翌週金曜日（{next_friday}）のセラピスト予定は公開されています")
                return True
        else:
            print(f"警告: 翌週金曜日（{next_friday}）は利用可能な日付ではありません")
            return False
    except Exception as e:
        print(f"翌週金曜日の予定チェックエラー: {e}")
        return False

# CSVから予約設定を読み込み（複数希望対応）
def load_reservation_config(csv_file):
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        configs = list(reader)
    return configs


# CSVから予約設定を読み込み（初期化）
configs = load_reservation_config('reservation_config.csv')

# スキップフラグをチェック
if os.path.exists("skip_next_run.txt"):
    print("情報: スキップフラグが存在します。次の自動実行をスキップします。")
    os.remove("skip_next_run.txt")
    exit(0)

# 予約監視ループ関数
def try_reservation(page, config):
    """予約を試みる関数。成功したら予約内容を返す、失敗したらFalseを返す"""
    try:
        # ④ 「初めて、利用あり」ラジオボタンを選択
        page.click('#main_form > div:nth-child(10) > ul > li:nth-child(2) > label')
        time.sleep(1)
        
        # ⑤ 日付を選択
        date = config['date']
        date_select = page.locator('select[name="date"]')
        options = date_select.locator('option').all()
        
        available_dates = []
        for option in options:
            value = option.get_attribute('value')
            if value:
                available_dates.append(value)
        
        if date in available_dates:
            page.select_option('select[name="date"]', date)
            print(f"日付を選択: {date}")
        else:
            print(f"警告: CSVの日付 '{date}' は利用可能ではありません")
            return False
        
        time.sleep(2)
        
        # ⑥ セラピストを選択
        therapist_name = config['therapist']
        cast_select = page.locator('select[name="cast"]')
        cast_options = cast_select.locator('option').all()
        
        found_therapist = False
        therapist_value = None
        
        for option in cast_options:
            text = option.inner_text()
            value = option.get_attribute('value')
            if value and value != '0':
                if therapist_name in text:
                    found_therapist = True
                    therapist_value = value
        
        if found_therapist:
            page.select_option('select[name="cast"]', therapist_value)
            print(f"セラピストを選択: {therapist_name}")
        else:
            print(f"エラー: セラピスト '{therapist_name}' は見つかりませんでした")
            return False
        
        time.sleep(2)
        
        # ⑦ コースを選択
        course_minutes = config['course']
        course_value = "53" if course_minutes == "90" else "54" if course_minutes == "120" else ""
        
        course_select = page.locator('select[name="course"]')
        if course_select.is_visible():
            course_options = course_select.locator('option').all()
            found_course = False
            for option in course_options:
                value = option.get_attribute('value')
                if value == course_value:
                    found_course = True
                    break
            
            if found_course:
                page.select_option('select[name="course"]', course_value)
                print(f"コースを選択: {course_minutes}分")
            else:
                print(f"エラー: 指定したコース（{course_minutes}分）は選択できません")
                return False
        else:
            print(f"エラー: コース選択ができません")
            return False
        
        time.sleep(2)
        
        # ⑧ 開始時間を選択
        start_time = config['start_time']
        start_time_select = page.locator('select[name="start_time"]')
        
        if start_time_select.is_visible():
            start_time_options = start_time_select.locator('option').all()
            found_time = False
            start_time_value = None
            for option in start_time_options:
                text = option.inner_text()
                value = option.get_attribute('value')
                if value:
                    if start_time in text:
                        found_time = True
                        start_time_value = value
            
            if found_time:
                page.select_option('select[name="start_time"]', start_time_value)
                print(f"開始時間を選択: {start_time}")
            else:
                print(f"エラー: 指定した開始時間（{start_time}）は選択できません")
                return False
        else:
            print(f"エラー: 開始時間選択ができません")
            return False
        
        # ⑨ 「確認する」ボタンをクリック
        page.click('a.a_button:has-text("確認する")')
        print("「確認する」ボタンをクリックしました")
        
        time.sleep(2)
        
        # エラーメッセージを確認（予約が埋まっている場合など）
        error_elements = page.locator('font[color="red"]').all()
        for error in error_elements:
            error_text = error.inner_text()
            if error_text and ('満席' in error_text or '予約' in error_text or 'できません' in error_text):
                print(f"エラーメッセージ検知: {error_text}")
                return "fully_booked"  # 予約埋まっている
        
        # ⑩ 「上記の内容で予約を送信する」ボタンをクリック
        page.click('input[name="finish_button"]')
        print("「上記の内容で予約を送信する」ボタンをクリックしました")
        
        return config  # 予約成功、予約内容を返す
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        return False

# メイン処理
with sync_playwright() as p:
    # ヘッドレスモードで実行（GitHub Actions用）
    # ローカルで確認する場合は headless=False に変更
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    # ① サイトを開く
    page.goto("https://za-gin.mplus-system.info/guest/login.php")
    print(f"ページタイトル: {page.title()}")
    
    # ② ログイン情報を入力してログイン
    page.fill('input[name="guest_id"]', LOGIN_ID)
    page.fill('input[name="password"]', PASSWORD)
    page.click('input[name="auth"]')
    page.wait_for_load_state("networkidle")
    print(f"ログイン後のページタイトル: {page.title()}")
    
    # ③ ご予約フォームを選択
    page.click('a[href="reservation.php"]')
    page.wait_for_load_state("networkidle")
    print(f"予約フォームページタイトル: {page.title()}")
    
    # 11時から16時までループ
    print(f"\n監視開始: {now_jst().strftime('%Y-%m-%d %H:%M:%S')}")
    print("11時から16時まで常時監視します...")
    
    # 監視開始通知を送信
    csv_summary = "\n".join([f"第{i+1}希望: {c['date']} {c['therapist']} {c['course']}分 {c['start_time']}" for i, c in enumerate(configs)])
    send_discord_webhook(f"予約自動化: 監視開始\n{now_jst().strftime('%Y-%m-%d %H:%M:%S')}\n\n{csv_summary}")
    
    reservation_success = False
    skip_remaining_runs = False
    successful_config = None
    
    while True:
        current_time = now_jst().time()
        
        # CSVを再読み込み（実行中の変更に対応）
        configs = load_reservation_config('reservation_config.csv')
        print(f"予約設定（{len(configs)}件）: {configs}")
        
        # 11時前なら待機
        if current_time < dt_time(11, 0, 0):
            print("11時を待機中...")
            time.sleep(60)
            continue
        
        # 16時を過ぎたら終了
        if current_time >= dt_time(16, 0, 0):
            print("16時を過ぎました。監視を終了します。")
            break
        
        # CSV指定の日付が利用可能かチェック
        first_config_date = configs[0]['date']
        
        # CSVの日付が次の日曜日以前かチェック
        next_sunday = get_next_sunday()
        if first_config_date <= next_sunday:
            print(f"CSV指定の日付 '{first_config_date}' は次の日曜日（{next_sunday}）以前です。CSVが更新されるまで監視を続けます...")
            time.sleep(10)
            # 予約フォームに戻る
            page.click('a[href="reservation.php"]')
            page.wait_for_load_state("networkidle")
            continue  # 次のループで再チェック
        
        date_select = page.locator('select[name="date"]')
        options = date_select.locator('option').all()
        
        available_dates = []
        for option in options:
            value = option.get_attribute('value')
            if value:
                available_dates.append(value)
        
        if first_config_date not in available_dates:
            print(f"CSV指定の日付 '{first_config_date}' はまだ公開されていません。10秒後に再チェックします...")
            time.sleep(10)
            # 予約フォームに戻る
            page.click('a[href="reservation.php"]')
            page.wait_for_load_state("networkidle")
            continue  # 次のループで再チェック
        
        # 日付を選択してセラピスト予定が公開されているか確認
        page.select_option('select[name="date"]', first_config_date)
        print(f"日付 '{first_config_date}' を選択しました")
        time.sleep(2)
        
        # セラピストリストを確認
        cast_select = page.locator('select[name="cast"]')
        cast_options = cast_select.locator('option').all()
        
        is_only_free = True
        for option in cast_options:
            value = option.get_attribute('value')
            if value and value != '0':
                is_only_free = False
                break
        
        if is_only_free:
            print(f"日付 '{first_config_date}' のセラピスト予定はまだ公開されていません。10秒後に再チェックします...")
            time.sleep(10)
            # 予約フォームに戻る
            page.click('a[href="reservation.php"]')
            page.wait_for_load_state("networkidle")
            continue  # 次のループで再チェック
        
        print(f"日付 '{first_config_date}' のセラピスト予定は公開されています。予約を試行します...")
        
        # 複数希望を順に試行
        for i, config in enumerate(configs):
            print(f"\n第{i+1}希望を試行中: {config}")
            result = try_reservation(page, config)
            
            if result == config:
                print(f"第{i+1}希望で予約が成功しました！")
                reservation_success = True
                successful_config = result
                break  # 予約成功、ループ終了
            elif result == "fully_booked":
                print(f"第{i+1}希望は予約が埋まっています。次の希望を試行します...")
                # 予約フォームに戻る
                page.click('a[href="reservation.php"]')
                page.wait_for_load_state("networkidle")
                # 次の希望を試行
                continue
            else:
                print(f"第{i+1}希望で予約に失敗しました。次の希望を試行します...")
                # 予約フォームに戻る
                page.click('a[href="reservation.php"]')
                page.wait_for_load_state("networkidle")
                # 次の希望を試行
                continue
        
        # 予約成功したら終了
        if reservation_success:
            break
        
        # すべての希望が失敗した場合
        print("すべての希望で予約に失敗しました。CSV指定の通りに予約できません。")
        print("次の自動実行をスキップします。")
        skip_remaining_runs = True
        break
    
    # 結果に応じて処理
    if skip_remaining_runs:
        with open("skip_next_run.txt", "w") as f:
            f.write("skip")
        csv_summary = "\n".join([f"第{i+1}希望: {c['date']} {c['therapist']} {c['course']}分 {c['start_time']}" for i, c in enumerate(configs)])
        send_discord_webhook(f"予約自動化: 失敗\nCSV指定の通りに予約できませんでした。\n\n{csv_summary}")
        browser.close()
        exit(1)
    elif reservation_success:
        print("予約が完了しました。")
        reservation_detail = f"日付: {successful_config['date']}\nセラピスト: {successful_config['therapist']}\nコース: {successful_config['course']}分\n開始時間: {successful_config['start_time']}"
        send_discord_webhook(f"予約自動化: 成功\n予約が成功しました！\n\n{reservation_detail}\n\n時間: {now_jst().strftime('%Y-%m-%d %H:%M:%S')}")
        browser.close()
        exit(0)
    else:
        print("16時までに予約できませんでした。次週に持ち越します。")
        csv_summary = "\n".join([f"第{i+1}希望: {c['date']} {c['therapist']} {c['course']}分 {c['start_time']}" for i, c in enumerate(configs)])
        send_discord_webhook(f"予約自動化: タイムアウト\n16時までに予約できませんでした。\n\n{csv_summary}")
        browser.close()
        exit(0)
