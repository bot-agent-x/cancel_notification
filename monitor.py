from playwright.sync_api import sync_playwright
import time
import csv
import os
from datetime import datetime, timedelta, timezone
import requests
from dotenv import load_dotenv
import json
import urllib3

# Disable SSL warnings for corporate network environments
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Load environment variables
load_dotenv()

# Configuration
LOGIN_URL = os.getenv("LOGIN_URL")
LOGIN_ID = os.getenv("LOGIN_ID")
PASSWORD = os.getenv("PASSWORD")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
CHECK_INTERVAL_MINUTES = 10
COURSE_MINUTES = 90
COURSE_VALUE = "53"  # 90-minute course value

# JST timezone (UTC+9)
JST = timezone(timedelta(hours=9))

# State file for tracking availability
STATE_FILE = "availability_state.json"


def now_jst():
    """Get current time in JST"""
    return datetime.now(timezone.utc).astimezone(JST)


def get_target_dates():
    """Get list of dates from today to next week's Friday"""
    today = now_jst()
    target_dates = []
    
    # Calculate days until next week's Friday
    # If today is Friday (4), next week's Friday is 7 days away
    # If today is Thursday (3), next week's Friday is 8 days away
    # etc.
    days_until_friday = (4 - today.weekday()) % 7
    if days_until_friday == 0:
        # Today is Friday, next week's Friday is 7 days away
        days_until_friday = 7
    else:
        # Next week's Friday (add 7 days to this week's Friday)
        days_until_friday = days_until_friday + 7
    
    # Generate dates from today to next week's Friday
    for i in range(days_until_friday + 1):
        date = today + timedelta(days=i)
        target_dates.append(date.strftime('%Y-%m-%d'))
    
    return target_dates


def load_targets(csv_file=None):
    """Load target list from CSV file or environment variable"""
    targets_json = os.getenv("TARGETS_JSON")
    
    if targets_json:
        # Load from GitHub Actions secret
        try:
            target_names = json.loads(targets_json)
            targets = [{"target_id": i+1, "target_name": name} for i, name in enumerate(target_names)]
            return targets
        except Exception as e:
            print(f"Error loading targets from environment variable: {e}")
    
    # Fallback to CSV file for local execution
    if csv_file and os.path.exists(csv_file):
        targets = []
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                targets.append(row)
        return targets
    
    raise ValueError("No target data available. Please set TARGETS_JSON environment variable or provide targets.csv file.")


def load_state():
    """Load previous availability state from file"""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading state file: {e}")
            return {}
    return {}


def save_state(state):
    """Save current availability state to file"""
    try:
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving state file: {e}")


def send_discord_notification(message):
    """Send notification to Discord via Webhook"""
    if not DISCORD_WEBHOOK_URL:
        print("Warning: DISCORD_WEBHOOK_URL not set. Cannot send notification.")
        return False
    
    try:
        data = {"content": message}
        # Disable SSL verification for corporate network environments
        response = requests.post(DISCORD_WEBHOOK_URL, json=data, verify=False)
        
        if response.status_code in [200, 204]:
            print(f"Discord notification sent: {message[:50]}...")
            return True
        else:
            print(f"Discord notification error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"Discord notification error: {e}")
        return False


def check_target_availability(page, target_name, date):
    """
    Check availability for a specific target on a specific date.
    Returns list of available start times, or empty list if not available.
    """
    try:
        # Select date
        date_select = page.locator('select[name="date"]')
        options = date_select.locator('option').all()
        
        available_dates = []
        for option in options:
            value = option.get_attribute('value')
            if value:
                available_dates.append(value)
        
        if date not in available_dates:
            print(f"  Date {date} not available in dropdown")
            return []
        
        page.select_option('select[name="date"]', date)
        time.sleep(1)
        
        # Select therapist
        cast_select = page.locator('select[name="cast"]')
        cast_options = cast_select.locator('option').all()
        
        found_therapist = False
        therapist_value = None
        
        for option in cast_options:
            text = option.inner_text()
            value = option.get_attribute('value')
            if value and value != '0':
                if target_name in text:
                    found_therapist = True
                    therapist_value = value
                    break
        
        if not found_therapist:
            print(f"  Target not found for date {date}")
            return []
        
        page.select_option('select[name="cast"]', therapist_value)
        time.sleep(1)
        
        # Check if course selection is available (indicates not fully booked)
        course_select = page.locator('select[name="course"]')
        
        if not course_select.is_visible():
            print(f"  Course selection not available for date {date} (fully booked)")
            return []
        
        # Try to select 90-minute course
        course_options = course_select.locator('option').all()
        found_course = False
        for option in course_options:
            value = option.get_attribute('value')
            if value == COURSE_VALUE:
                found_course = True
                break
        
        if not found_course:
            print(f"  90-minute course not available for date {date}")
            return []
        
        page.select_option('select[name="course"]', COURSE_VALUE)
        time.sleep(1)
        
        # Check start time options
        start_time_select = page.locator('select[name="start_time"]')
        
        if not start_time_select.is_visible():
            print(f"  Start time selection not available for date {date}")
            return []
        
        start_time_options = start_time_select.locator('option').all()
        available_times = []
        
        for option in start_time_options:
            value = option.get_attribute('value')
            text = option.inner_text()
            if value and text:
                available_times.append(text)
        
        if available_times:
            print(f"  Available for date {date}: {available_times}")
            return available_times
        else:
            print(f"  No available times for date {date}")
            return []
            
    except Exception as e:
        print(f"  Error checking availability for date {date}: {e}")
        return []


def reset_form(page):
    """Reset the form by navigating back to reservation page"""
    try:
        page.click('a[href="reservation.php"]')
        page.wait_for_load_state("networkidle")
        time.sleep(1)
    except Exception as e:
        print(f"Error resetting form: {e}")


def run_monitoring(page, state):
    """Run one availability check."""
    print(f"\n{'='*60}")
    print(f"Check at {now_jst().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Get target dates
    target_dates = get_target_dates()
    print(f"Target dates: {target_dates[0]} to {target_dates[-1]}")
    
    # Reload targets in case of changes
    targets = load_targets('targets.csv')
    
    new_slots = []
    
    # Check each target and date
    for target in targets:
        target_name = target['target_name']
        print(f"\nChecking target: {target['target_id']}")
        
        for date in target_dates:
            # Reset form before each check
            reset_form(page)
            
            # Check availability
            available_times = check_target_availability(page, target_name, date)
            
            # Create state key
            state_key = f"{target_name}_{date}"
            
            # Compare with previous state
            previous_times = state.get(state_key, [])
            
            # Detect new slots (available now but not before)
            for time_slot in available_times:
                if time_slot not in previous_times:
                    new_slots.append({
                        'target': target_name,
                        'date': date,
                        'time': time_slot
                    })
            
            # Update state
            state[state_key] = available_times
    
    # Save updated state
    save_state(state)
    
    # Send notifications for new slots (batch notification)
    if new_slots:
        # Filter out weekend slots (Saturday=5, Sunday=6)
        weekday_slots = []
        for slot in new_slots:
            date_obj = datetime.strptime(slot['date'], '%Y-%m-%d')
            if date_obj.weekday() < 5:  # Monday-Friday only
                weekday_slots.append(slot)
        
        if weekday_slots:
            print(f"\n[NEW] Found {len(weekday_slots)} new available slots (weekdays only)!")
            
            # Group by target
            slots_by_target = {}
            for slot in weekday_slots:
                target = slot['target']
                if target not in slots_by_target:
                    slots_by_target[target] = []
                slots_by_target[target].append(slot)
            
            # Send batch notification
            message_parts = ["[NEW] 空き発生！"]
            for target, slots in slots_by_target.items():
                message_parts.append(f"\n{target}")
                for slot in slots:
                    message_parts.append(f"  {slot['date']} {slot['time']}")
            
            message_parts.append(f"\n予約ページ: {LOGIN_URL.replace('login.php', 'reservation.php')}")
            send_discord_notification("\n".join(message_parts))
        else:
            print("No new weekday slots found (all new slots are on weekends)")
    else:
        print("No new slots found")
    
    print("\nCheck completed.")


if __name__ == "__main__":
    print("Script execution started")
    print(f"LOGIN_URL set: {bool(LOGIN_URL)}")
    print(f"LOGIN_ID set: {bool(LOGIN_ID)}")
    print(f"PASSWORD set: {bool(PASSWORD)}")
    
    if not LOGIN_URL or not LOGIN_ID or not PASSWORD:
        print("Error: LOGIN_URL, LOGIN_ID and PASSWORD must be set in .env file")
        exit(1)
    
    if not DISCORD_WEBHOOK_URL:
        print("Warning: DISCORD_WEBHOOK_URL not set. Notifications will not be sent.")
    
    try:
        print(f"Starting availability monitoring at {now_jst().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Check interval: {CHECK_INTERVAL_MINUTES} minutes")
        
        # Load targets
        targets = load_targets('targets.csv')
        print(f"Monitoring {len(targets)} targets")
        
        # Load previous state
        state = load_state()
        
        # Send start notification
        target_dates = get_target_dates()
        send_discord_notification(
            f"[START] 監視開始\n"
            f"時間: {now_jst().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"監視期間: {target_dates[0]} ～ {target_dates[-1]}\n"
            f"対象: {len(targets)}件\n"
            f"チェック間隔: {CHECK_INTERVAL_MINUTES}分"
        )
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Login
            page.goto(LOGIN_URL)
            print(f"Page title: {page.title()}")
            
            # Simple login (same as test_playwright.py)
            page.fill('input[name="guest_id"]', LOGIN_ID)
            page.fill('input[name="password"]', PASSWORD)
            page.click('input[name="auth"]')
            page.wait_for_load_state("networkidle")
            print(f"Logged in successfully, page title: {page.title()}")
            
            # Navigate to reservation form
            page.click('a[href="reservation.php"]')
            page.wait_for_load_state("networkidle")
            print("Navigated to reservation form")
            
            # Monitoring loop with timeout
            start_time = now_jst()
            max_duration_minutes = 5 * 60 + 50  # 5 hours 50 minutes
            
            while True:
                # Check if we've exceeded the maximum duration
                elapsed = (now_jst() - start_time).total_seconds() / 60
                if elapsed >= max_duration_minutes:
                    print(f"\nMaximum duration ({max_duration_minutes} minutes) reached. Stopping monitoring.")
                    send_discord_notification(
                        f"[TIMEOUT] 監視タイムアウト\n"
                        f"時間: {now_jst().strftime('%Y-%m-%d %H:%M:%S')}\n"
                        f"理由: {max_duration_minutes}分経過による自動停止"
                    )
                    break
                
                try:
                    run_monitoring(page, state)
                except Exception as e:
                    print(f"Monitoring iteration failed: {e}")
                    send_discord_notification(
                        f"[ERROR] 監視チェック失敗\n"
                        f"時間: {now_jst().strftime('%Y-%m-%d %H:%M:%S')}\n"
                        f"エラー: {str(e)}"
                    )
                
                print(f"Waiting {CHECK_INTERVAL_MINUTES} minutes before the next check. Press Ctrl+C to stop.")
                time.sleep(CHECK_INTERVAL_MINUTES * 60)
        
        browser.close()
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")
        send_discord_notification(
            f"[STOP] 監視停止\n"
            f"時間: {now_jst().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"理由: ユーザーによる手動停止"
        )
    except Exception as e:
        print(f"Fatal error: {e}")
        send_discord_notification(
            f"[ERROR] 監視エラー停止\n"
            f"時間: {now_jst().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"エラー: {str(e)}"
        )
        raise
