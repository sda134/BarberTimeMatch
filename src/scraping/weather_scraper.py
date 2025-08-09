import requests
from datetime import datetime
import yaml
import time
import sys
from pathlib import Path

# Google Sheets連携用のimport
# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
from src.utils.google_sheets import GoogleSheetsManager
from src.scraping.utils import load_config, load_stores_config

def simplify_weather(weather_text):
    """複雑な天気予報文を簡単な表現に変換"""
    if not weather_text:
        return "不明"
    
    # 主要な天気キーワードで判定
    weather_text = weather_text.replace('　', ' ')  # 全角スペースを半角に
    
    if '晴れ' in weather_text:
        if 'くもり' in weather_text or '曇り' in weather_text:
            return "晴れ時々曇り"
        elif '雨' in weather_text:
            return "晴れ時々雨"
        else:
            return "晴れ"
    elif 'くもり' in weather_text or '曇り' in weather_text:
        if '雨' in weather_text:
            return "曇り時々雨"
        else:
            return "曇り"
    elif '雨' in weather_text:
        if '雷' in weather_text:
            return "雨時々雷雨"
        else:
            return "雨"
    elif '雪' in weather_text:
        return "雪"
    else:
        return weather_text[:10] + "..." if len(weather_text) > 10 else weather_text

def get_unique_area_codes(stores_config):
    """設定されている店舗の重複しないエリアコードを取得"""
    area_codes = set()
    for store in stores_config['stores']:
        if 'weather_area_code' in store:
            area_codes.add(store['weather_area_code'])
    return list(area_codes)

def get_forecast_data(area_code, timeout=15):
    """指定エリアコードの気象庁予報APIから天気データを取得"""
    url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{area_code}.json"
    
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        
        # 今日の天気情報を抽出
        today_weather_raw = data[0]['timeSeries'][0]['areas'][0]['weathers'][0]
        area_name = data[0]['timeSeries'][0]['areas'][0]['area']['name']
        
        # 天気を簡略化
        today_weather = simplify_weather(today_weather_raw)
        
        # 気温データの抽出（存在する場合）
        today_temp_min = None
        today_temp_max = None
        
        if len(data[0]['timeSeries']) > 2 and 'areas' in data[0]['timeSeries'][2]:
            temp_areas = data[0]['timeSeries'][2]['areas'][0]
            if 'temps' in temp_areas and temp_areas['temps']:
                temps_list = temp_areas['temps']
                if temps_list and len(temps_list) >= 2:
                    # temps配列は [今日午前, 今日午後, 明日午前, 明日午後] の順
                    # 今日の最高気温は午後の値（インデックス1）
                    # 今日の最低気温は午前の値（インデックス0）だが、実際は明日の最低気温がインデックス2にある場合が多い
                    try:
                        today_temp_max = int(temps_list[1]) if temps_list[1] and temps_list[1] != '' else None
                        # 最低気温は通常、翌日の早朝値として提供される
                        today_temp_min = int(temps_list[2]) if len(temps_list) > 2 and temps_list[2] and temps_list[2] != '' else None
                    except (ValueError, IndexError):
                        today_temp_max = None
                        today_temp_min = None
        
        return {
            'area_code': area_code,
            'area_name': area_name,
            'weather_forecast': today_weather,
            'temp_min_forecast': today_temp_min,
            'temp_max_forecast': today_temp_max,
        }
    except Exception as e:
        print(f"Error getting forecast data for area {area_code}: {e}")
        return None

def get_latest_timestamp():
    """最新のアメダスデータタイムスタンプを取得"""
    try:
        response = requests.get("https://www.jma.go.jp/bosai/amedas/data/latest_time.txt", timeout=10)
        response.raise_for_status()
        timestamp_str = response.text.strip()
        # ISO形式のタイムスタンプを解析
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.strftime('%Y%m%d%H%M00')
    except Exception as e:
        print(f"最新タイムスタンプ取得エラー: {e}")
        # フォールバック: 現在時刻から推定（10分単位に調整）
        now = datetime.now()
        return now.strftime('%Y%m%d%H%M00')

def get_observation_data(area_code, timeout=15):
    """指定エリアの観測データを取得（現在の気温・湿度など）"""
    # 正確な観測所IDマッピング（調査結果に基づく）
    observation_stations = {
        '230000': ['51106', '51116', '51216']  # 名古屋、豊田、大府
    }
    
    station_ids = observation_stations.get(area_code, [])
    if not station_ids:
        print(f"No observation stations found for area code {area_code}")
        return None
    
    # 最新タイムスタンプと複数の候補時刻を試行
    latest_timestamp = get_latest_timestamp()
    
    import datetime as dt
    now = datetime.now()
    
    # 複数の時刻候補を生成（10分間隔で過去1時間）
    time_candidates = []
    for i in range(7):  # 現在から60分前まで10分刻み
        candidate_time = now - dt.timedelta(minutes=i*10)
        timestamp = candidate_time.strftime('%Y%m%d%H%M00')
        time_candidates.append(timestamp)
    
    # 最新タイムスタンプも追加
    if latest_timestamp not in time_candidates:
        time_candidates.insert(0, latest_timestamp)
    
    for timestamp in time_candidates:
        url = f"https://www.jma.go.jp/bosai/amedas/data/map/{timestamp}.json"
        
        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            
            # 複数の観測所を試行
            for station_id in station_ids:
                if station_id in data:
                    station_data = data[station_id]
                    
                    if station_data:
                        # 気温
                        current_temp = None
                        if 'temp' in station_data and station_data['temp'] is not None:
                            current_temp = station_data['temp'][0]
                        
                        # 湿度
                        humidity = None
                        if 'humidity' in station_data and station_data['humidity'] is not None:
                            humidity = station_data['humidity'][0]
                        
                        # 降水量
                        precipitation = None
                        if 'precipitation1h' in station_data and station_data['precipitation1h'] is not None:
                            precipitation = station_data['precipitation1h'][0]
                        
                        # 風速
                        wind_speed = None
                        if 'wind' in station_data and station_data['wind'] is not None:
                            wind_speed = station_data['wind'][0]
                        
                        # 気圧
                        pressure = None
                        if 'pressure' in station_data and station_data['pressure'] is not None:
                            pressure = station_data['pressure'][0]
                        
                        # 何かしらのデータが取得できた場合は返す
                        if any([current_temp, humidity, precipitation, wind_speed, pressure]):
                            print(f"観測データ取得成功: 観測所{station_id}, 時刻{timestamp}")
                            return {
                                'station_id': station_id,
                                'observation_timestamp': timestamp,
                                'current_temp': current_temp,
                                'humidity': humidity,
                                'precipitation_1h': precipitation,
                                'wind_speed': wind_speed,
                                'pressure': pressure,
                            }
                        
        except Exception as e:
            print(f"観測データ取得エラー ({timestamp}): {e}")
            continue
    
    print(f"観測データが見つかりませんでした (area: {area_code})")
    return None

def get_weather_data(area_code, scraping_config):
    """指定エリアの予報・観測データを統合して取得"""
    timestamp = datetime.now()
    timeout = scraping_config['scraping']['timeout']
    
    # 予報データ取得
    forecast_data = get_forecast_data(area_code, timeout)
    
    # 観測データ取得
    observation_data = get_observation_data(area_code, timeout)
    
    # データを統合
    weather_record = {
        'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        'date': timestamp.strftime('%Y-%m-%d'),
        'time': timestamp.strftime('%H:%M'),
        'hour': timestamp.hour,
        'area_code': area_code,
        'area_name': forecast_data['area_name'] if forecast_data else None,
        'weather_forecast': forecast_data['weather_forecast'] if forecast_data else None,
        'temp_min_forecast': forecast_data['temp_min_forecast'] if forecast_data else None,
        'temp_max_forecast': forecast_data['temp_max_forecast'] if forecast_data else None,
        'current_temp': observation_data['current_temp'] if observation_data else None,
        'humidity': observation_data['humidity'] if observation_data else None,
        'precipitation_1h': observation_data['precipitation_1h'] if observation_data else None,
        'wind_speed': observation_data['wind_speed'] if observation_data else None,
        'pressure': observation_data['pressure'] if observation_data else None,
        'observation_station': observation_data['station_id'] if observation_data else None,
        'data_status': 'success' if (forecast_data or observation_data) else 'error'
    }
    
    return weather_record

def save_data(data_list):
    """データをGoogle Sheetsに保存"""
    if not data_list:
        print("No weather data to save")
        return
    
    try:
        sheets_manager = GoogleSheetsManager()
        sheets_manager.append_weather_data(data_list)
        print(f"Successfully saved {len(data_list)} weather records to Google Sheets")
    except Exception as e:
        print(f"Error saving weather data to Google Sheets: {e}")
        # フォールバック：CSV保存
        save_data_csv(data_list)

def save_data_csv(data_list):
    """データをCSVファイルに保存（フォールバック用）"""
    if not data_list:
        print("No weather data to save")
        return
    
    # データディレクトリの作成
    data_dir = Path(__file__).parent.parent.parent / 'data' / 'raw'
    data_dir.mkdir(parents=True, exist_ok=True)
    
    csv_path = data_dir / 'weather_data.csv'
    
    # CSVヘッダー
    header = [
        'timestamp', 'date', 'time', 'hour', 'area_code', 'area_name',
        'weather_forecast', 'temp_min_forecast', 'temp_max_forecast',
        'current_temp', 'humidity', 'precipitation_1h', 'wind_speed',
        'pressure', 'observation_station', 'data_status'
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
    
    print(f"Saved {len(data_list)} weather records to {csv_path}")

def main():
    """メイン処理"""
    try:
        stores_config = load_stores_config()
        scraping_config = load_config()
        
        # 対象エリアコードを取得
        area_codes = get_unique_area_codes(stores_config)
        
        if not area_codes:
            print("No area codes found in store configuration")
            return
        
        all_weather_data = []
        
        for area_code in area_codes:
            print(f"Collecting weather data for area {area_code}...")
            weather_data = get_weather_data(area_code, scraping_config)
            if weather_data:
                all_weather_data.append(weather_data)
                print(f"  - Current temp: {weather_data['current_temp']}°C")
                print(f"  - Humidity: {weather_data['humidity']}%")
                print(f"  - Weather: {weather_data['weather_forecast']}")
            
            # レート制限
            delay = scraping_config['scraping']['delay_between_requests']
            if len(area_codes) > 1:
                time.sleep(delay)
        
        # データ保存
        save_data(all_weather_data)
        
        print(f"Successfully collected weather data for {len(all_weather_data)} areas")
        
    except Exception as e:
        print(f"Error in weather data collection: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()