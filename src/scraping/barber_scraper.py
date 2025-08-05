import requests
from lxml import html
import pandas as pd
from datetime import datetime
import yaml
import time
import os
import sys
import re
from pathlib import Path

def load_config():
    """設定ファイルを読み込み"""
    config_path = Path(__file__).parent.parent.parent / 'config'
    
    with open(config_path / 'stores.yaml', 'r', encoding='utf-8') as f:
        stores_config = yaml.safe_load(f)
    
    with open(config_path / 'scraping_config.yaml', 'r', encoding='utf-8') as f:
        scraping_config = yaml.safe_load(f)
    
    return stores_config, scraping_config

def scrape_store_data(store_config, scraping_config):
    """単一店舗のデータを取得"""
    headers = {'User-Agent': scraping_config['scraping']['user_agent']}
    timeout = scraping_config['scraping']['timeout']
    
    timestamp = datetime.now()
    
    try:
        response = requests.get(store_config['url'], headers=headers, timeout=timeout)
        response.raise_for_status()
        
        tree = html.fromstring(response.content)
        wait_count_elements = tree.xpath(store_config['xpath_wait_count'])
        
        if wait_count_elements:
            # 数値部分を抽出
            wait_text = str(wait_count_elements[0]).strip()
            # 数字のみを抽出（例: "3組" → "3"）
            numbers = re.findall(r'\d+', wait_text)
            wait_count = int(numbers[0]) if numbers else None
        else:
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
    except requests.exceptions.RequestException as e:
        print(f"Network error scraping {store_config['name']}: {e}")
        return create_error_record(store_config, timestamp, f"network_error: {str(e)}")
    except Exception as e:
        print(f"Error scraping {store_config['name']}: {e}")
        return create_error_record(store_config, timestamp, f"parse_error: {str(e)}")

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
    """データをCSVファイルに保存"""
    if not data_list:
        print("No data to save")
        return
    
    df = pd.DataFrame(data_list)
    
    # データディレクトリの作成
    data_dir = Path(__file__).parent.parent.parent / 'data' / 'raw'
    data_dir.mkdir(parents=True, exist_ok=True)
    
    csv_path = data_dir / 'barber_data.csv'
    
    # CSVに追記
    if csv_path.exists():
        df.to_csv(csv_path, mode='a', header=False, index=False, encoding='utf-8')
    else:
        df.to_csv(csv_path, index=False, encoding='utf-8')
    
    print(f"Saved {len(data_list)} records to {csv_path}")

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