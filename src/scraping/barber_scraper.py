import requests
from lxml import html
import csv
from datetime import datetime
import time
import os
import sys
import json

# プロジェクトルートをPythonパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.scraping.utils import (
    load_config, 
    load_stores_config, 
    get_random_wait_time, 
    ensure_data_directory,
    generate_mock_wait_count
)

class BarberScraper:
    def __init__(self):
        self.config = load_config()
        self.stores_config = load_stores_config()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.config['scraping']['user_agent']
        })
    
    def scrape_store_data(self, store_config):
        """単一店舗のデータを取得"""
        try:
            # デバッグモードまたはサンプル店舗の場合はモックデータを使用
            if self.config.get('debug', {}).get('mock_data', False) or store_config.get('type') == 'sample':
                return self._generate_mock_data(store_config)
            
            # 実際のスクレイピング処理
            response = self.session.get(
                store_config['url'], 
                timeout=self.config['scraping']['timeout']
            )
            response.raise_for_status()
            
            # レスポンスを保存（デバッグ用）
            if self.config.get('debug', {}).get('save_responses', False):
                self._save_response(store_config['id'], response.text)
            
            tree = html.fromstring(response.content)
            wait_count_elements = tree.xpath(store_config['xpath_wait_count'])
            
            if wait_count_elements:
                wait_count = int(wait_count_elements[0].strip())
            else:
                wait_count = None
                
            return self._create_data_record(store_config, wait_count)
            
        except Exception as e:
            print(f"Error scraping {store_config['name']}: {e}")
            # エラー時はモックデータを返す
            return self._generate_mock_data(store_config, error=True)
    
    def _generate_mock_data(self, store_config, error=False):
        """テスト用のモックデータを生成"""
        if error:
            wait_count = None
        else:
            wait_count = generate_mock_wait_count()
        
        return self._create_data_record(store_config, wait_count)
    
    def _create_data_record(self, store_config, wait_count):
        """データレコードを作成"""
        now = datetime.now()
        return {
            'timestamp': now.strftime('%Y-%m-%d %H:%M:%S'),
            'store_id': store_config['id'],
            'store_name': store_config['name'],
            'wait_count': wait_count,
            'area': store_config['area'],
            'day_of_week': now.strftime('%A'),
            'hour': now.hour,
            'minute': now.minute,
            'is_weekend': now.weekday() >= 5,
            'date': now.strftime('%Y-%m-%d')
        }
    
    def _save_response(self, store_id, response_text):
        """デバッグ用にレスポンスを保存"""
        debug_dir = os.path.join('data', 'debug')
        os.makedirs(debug_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{store_id}_{timestamp}_response.html"
        filepath = os.path.join(debug_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(response_text)
    
    def scrape_all_stores(self):
        """全店舗のデータを取得"""
        all_data = []
        
        for store in self.stores_config['stores']:
            print(f"Scraping {store['name']}...")
            data = self.scrape_store_data(store)
            if data:
                all_data.append(data)
                print(f"  - Wait count: {data['wait_count']}")
            
            # レート制限
            get_random_wait_time(
                self.config['scraping']['delay_between_requests'] - 0.5,
                self.config['scraping']['delay_between_requests'] + 0.5
            )
        
        return all_data
    
    def save_data(self, data):
        """データをCSVに保存"""
        if not data:
            print("No data to save")
            return
        
        csv_path = os.path.join('data', 'raw', 'barber_data.csv')
        ensure_data_directory(csv_path)
        
        # ヘッダー行の定義
        fieldnames = ['timestamp', 'store_id', 'store_name', 'wait_count', 'area', 
                     'day_of_week', 'hour', 'minute', 'is_weekend', 'date']
        
        # ファイルが存在するかチェック
        file_exists = os.path.exists(csv_path)
        
        # CSVに書き込み
        with open(csv_path, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            # ファイルが新規作成の場合はヘッダーを書き込み
            if not file_exists:
                writer.writeheader()
            
            # データを書き込み
            writer.writerows(data)
        
        print(f"Data saved to {csv_path}")
        print(f"Total records collected: {len(data)}")

def main():
    """メイン処理"""
    scraper = BarberScraper()
    
    print("Starting barber data collection...")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # データ収集
    all_data = scraper.scrape_all_stores()
    
    # データ保存
    scraper.save_data(all_data)
    
    print("Barber data collection completed!")

if __name__ == "__main__":
    main()