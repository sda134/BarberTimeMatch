from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from datetime import datetime
import yaml
import time
import os
import sys
import re
from pathlib import Path

# Google Sheets連携用のimport
# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
from src.utils.google_sheets import GoogleSheetsManager

def load_config():
    """設定ファイルを読み込み"""
    config_path = Path(__file__).parent.parent.parent / 'config'
    
    with open(config_path / 'stores.yaml', 'r', encoding='utf-8') as f:
        stores_config = yaml.safe_load(f)
    
    with open(config_path / 'scraping_config.yaml', 'r', encoding='utf-8') as f:
        scraping_config = yaml.safe_load(f)
    
    return stores_config, scraping_config

def create_driver(scraping_config):
    """Selenium WebDriverを作成"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # ヘッドレスモード
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument(f"--user-agent={scraping_config['scraping']['user_agent']}")
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(scraping_config['scraping']['timeout'])
    return driver

def scrape_store_data(store_config, scraping_config):
    """単一店舗のデータを取得（Selenium使用）"""
    timestamp = datetime.now()
    driver = None
    
    try:
        driver = create_driver(scraping_config)
        driver.get(store_config['url'])
        
        # JavaScriptの実行を待つ（最大10秒）
        wait = WebDriverWait(driver, 10)
        
        try:
            # 待ち時間数字の要素を取得（クラス名で直接指定）
            element = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "waiting-view__number")))
            wait_text = element.text.strip()
            
            if wait_text:
                if wait_text == '-':
                    # 営業時間外または閉店時は0とする
                    wait_count = 0
                    print(f"Found wait count text: '{wait_text}' (closed/after-hours) -> {wait_count}")
                else:
                    # 数字のみを抽出（例: "3組" → "3"）
                    numbers = re.findall(r'\d+', wait_text)
                    wait_count = int(numbers[0]) if numbers else None
                    print(f"Found wait count text: '{wait_text}' -> {wait_count}")
            else:
                wait_count = None
                print("Wait text is empty")
                
        except TimeoutException:
            print("Timeout waiting for waiting-view__number element")
            wait_count = None
        except NoSuchElementException:
            print("waiting-view__number element not found")
            wait_count = None
            
        return {
            'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'date': timestamp.strftime('%Y-%m-%d'),
            'time': timestamp.strftime('%H:%M'),
            'store_id': store_config['id'],
            'store_name': store_config['name'],
            'wait_count': wait_count,
            'area': store_config['area'],
            'day_of_week': timestamp.strftime('%A'),
            'hour': timestamp.hour,
            'weekday_num': timestamp.weekday(),  # 0=月曜
            'is_weekend': timestamp.weekday() >= 5,
            'scraping_status': 'success'
        }
        
    except Exception as e:
        print(f"Error scraping {store_config['name']}: {e}")
        return create_error_record(store_config, timestamp, f"selenium_error: {str(e)}")
    finally:
        if driver:
            driver.quit()

def create_error_record(store_config, timestamp, error_msg):
    """エラー時のレコードを作成"""
    return {
        'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        'date': timestamp.strftime('%Y-%m-%d'),
        'time': timestamp.strftime('%H:%M'),
        'store_id': store_config['id'],
        'store_name': store_config['name'],
        'wait_count': None,
        'area': store_config['area'],
        'day_of_week': timestamp.strftime('%A'),
        'hour': timestamp.hour,
        'weekday_num': timestamp.weekday(),
        'is_weekend': timestamp.weekday() >= 5,
        'scraping_status': error_msg
    }

def save_data(data_list):
    """データをGoogle Sheetsに保存"""
    if not data_list:
        print("No data to save")
        return
    
    try:
        sheets_manager = GoogleSheetsManager()
        sheets_manager.append_barber_data(data_list)
        print(f"Successfully saved {len(data_list)} records to Google Sheets")
    except Exception as e:
        print(f"Error saving to Google Sheets: {e}")
        # フォールバック：CSV保存
        save_data_csv(data_list)

def save_data_csv(data_list):
    """データをCSVファイルに保存（フォールバック用）"""
    if not data_list:
        print("No data to save")
        return
    
    # データディレクトリの作成
    data_dir = Path(__file__).parent.parent.parent / 'data' / 'raw'
    data_dir.mkdir(parents=True, exist_ok=True)
    
    csv_path = data_dir / 'barber_data_backup.csv'
    
    # CSVヘッダー
    header = [
        'timestamp', 'date', 'time', 'store_id', 'store_name', 'wait_count',
        'area', 'day_of_week', 'hour', 'weekday_num', 'is_weekend', 'scraping_status'
    ]
    
    # ファイルが存在しない場合はヘッダーを書き込み
    file_exists = csv_path.exists()
    
    with open(csv_path, 'a', encoding='utf-8') as f:
        if not file_exists:
            f.write(','.join(header) + '\n')
        
        for data in data_list:
            row = []
            for col in header:
                value = data.get(col, '')
                if value is None:
                    value = ''
                row.append(str(value))
            f.write(','.join(row) + '\n')
    
    print(f"Fallback: Saved {len(data_list)} records to {csv_path}")

def main():
    """メイン処理"""
    try:
        stores_config, scraping_config = load_config()
        all_data = []
        
        # 床屋タイプの店舗のみ対象
        barber_stores = [store for store in stores_config['stores'] 
                        if store.get('type') == 'barber']
        
        if not barber_stores:
            print("No barber stores found in configuration")
            return
        
        for store in barber_stores:
            print(f"Scraping {store['name']}...")
            data = scrape_store_data(store, scraping_config)
            if data:
                all_data.append(data)
                print(f"  - Wait count: {data['wait_count']}")
            
            # レート制限
            delay = scraping_config['scraping']['delay_between_requests']
            if len(barber_stores) > 1:  # 複数店舗がある場合のみ待機
                time.sleep(delay)
        
        # データ保存
        save_data(all_data)
        
        print(f"Successfully collected data for {len(all_data)} stores")
        
    except Exception as e:
        print(f"Error in main process: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()