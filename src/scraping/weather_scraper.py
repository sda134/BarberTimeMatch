import requests
import pandas as pd
from datetime import datetime
import os
import sys
import json

# プロジェクトルートをPythonパスに追加  
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.scraping.utils import load_config, ensure_data_directory

class WeatherScraper:
    def __init__(self):
        self.config = load_config()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.config['scraping']['user_agent']
        })
    
    def get_weather_data(self):
        """気象庁APIから天気データを取得"""
        area_code = self.config['weather']['area_code']
        url = f"{self.config['weather']['api_endpoint']}{area_code}.json"
        
        try:
            # デバッグモードの場合はモックデータを使用
            if self.config.get('debug', {}).get('mock_data', False):
                return self._generate_mock_weather_data()
            
            response = self.session.get(url, timeout=self.config['scraping']['timeout'])
            response.raise_for_status()
            data = response.json()
            
            # レスポンスを保存（デバッグ用）
            if self.config.get('debug', {}).get('save_responses', False):
                self._save_response(data)
            
            # 今日の天気情報を抽出
            today_weather = data[0]['timeSeries'][0]['areas'][0]['weathers'][0]
            
            # 気温データの取得（存在する場合）
            today_temp_min = None
            today_temp_max = None
            if len(data[0]['timeSeries']) > 2 and data[0]['timeSeries'][2]['areas'][0].get('tempsMin'):
                today_temp_min = data[0]['timeSeries'][2]['areas'][0]['tempsMin'][0]
            if len(data[0]['timeSeries']) > 2 and data[0]['timeSeries'][2]['areas'][0].get('tempsMax'):
                today_temp_max = data[0]['timeSeries'][2]['areas'][0]['tempsMax'][0]
            
            return self._create_weather_record(today_weather, today_temp_min, today_temp_max)
            
        except Exception as e:
            print(f"Error getting weather data: {e}")
            # エラー時はモックデータを返す
            return self._generate_mock_weather_data(error=True)
    
    def _generate_mock_weather_data(self, error=False):
        """テスト用のモック天気データを生成"""
        import random
        
        if error:
            weather = "データ取得エラー"
            temp_min = None
            temp_max = None
        else:
            weathers = ["晴れ", "曇り", "雨", "晴れのち曇り", "曇りのち雨"]
            weather = random.choice(weathers)
            temp_min = random.randint(5, 15)
            temp_max = random.randint(temp_min + 5, temp_min + 15)
        
        return self._create_weather_record(weather, temp_min, temp_max)
    
    def _create_weather_record(self, weather, temp_min, temp_max):
        """天気データレコードを作成"""
        now = datetime.now()
        return {
            'date': now.strftime('%Y-%m-%d'),
            'weather': weather,
            'temp_min': temp_min,
            'temp_max': temp_max,
            'timestamp': now.strftime('%Y-%m-%d %H:%M:%S'),
            'area': 'Tokyo',  # 設定から取得可能にしても良い
        }
    
    def _save_response(self, response_data):
        """デバッグ用にレスポンスを保存"""
        debug_dir = os.path.join('data', 'debug')
        os.makedirs(debug_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"weather_{timestamp}_response.json"
        filepath = os.path.join(debug_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(response_data, f, ensure_ascii=False, indent=2)
    
    def save_weather_data(self, weather_data):
        """天気データをCSVに保存"""
        if not weather_data:
            print("No weather data to save")
            return
        
        df = pd.DataFrame([weather_data])
        csv_path = os.path.join('data', 'raw', 'weather_data.csv')
        ensure_data_directory(csv_path)
        
        # 同じ日のデータは上書き
        if os.path.exists(csv_path):
            existing_df = pd.read_csv(csv_path)
            existing_df = existing_df[existing_df['date'] != weather_data['date']]
            df = pd.concat([existing_df, df], ignore_index=True)
        
        df.to_csv(csv_path, index=False)
        print(f"Weather data saved to {csv_path}")

def main():
    """メイン処理"""
    scraper = WeatherScraper()
    
    print("Starting weather data collection...")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 天気データ取得
    weather_data = scraper.get_weather_data()
    
    if weather_data:
        print(f"Weather: {weather_data['weather']}")
        print(f"Temperature: {weather_data['temp_min']}°C - {weather_data['temp_max']}°C")
        
        # データ保存
        scraper.save_weather_data(weather_data)
    
    print("Weather data collection completed!")

if __name__ == "__main__":
    main()