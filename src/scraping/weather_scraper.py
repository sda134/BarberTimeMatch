import requests
import pandas as pd
from datetime import datetime
import yaml
import time
import sys
from pathlib import Path

def load_config():
    """設定ファイルを読み込み"""
    config_path = Path(__file__).parent.parent.parent / 'config'
    
    with open(config_path / 'stores.yaml', 'r', encoding='utf-8') as f:
        stores_config = yaml.safe_load(f)
    
    with open(config_path / 'scraping_config.yaml', 'r', encoding='utf-8') as f:
        scraping_config = yaml.safe_load(f)
    
    return stores_config, scraping_config

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
            if 'tempsMin' in temp_areas and temp_areas['tempsMin']:
                today_temp_min = temp_areas['tempsMin'][0] if temp_areas['tempsMin'][0] != '' else None
            if 'tempsMax' in temp_areas and temp_areas['tempsMax']:
                today_temp_max = temp_areas['tempsMax'][0] if temp_areas['tempsMax'][0] != '' else None
        
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

def get_observation_data(area_code, timeout=15):
    """指定エリアの観測データを取得（現在の気温・湿度など）"""
    # 名古屋周辺の観測所IDを複数試行
    observation_stations = {
        '230000': ['47636', '47635', '47651']  # 名古屋、岡崎、半田など
    }
    
    station_ids = observation_stations.get(area_code, [])
    if not station_ids:
        print(f"No observation stations found for area code {area_code}")
        return None
    
    # 現在時刻と1時間前の時刻を試行（データ更新のタイミング考慮）
    import datetime as dt
    now = datetime.now()
    time_candidates = [
        now,
        now.replace(minute=0, second=0, microsecond=0) - dt.timedelta(hours=1)
    ]
    
    for time_to_try in time_candidates:
        date_str = time_to_try.strftime('%Y%m%d')
        hour_str = time_to_try.strftime('%H')
        
        # 観測データAPIのURL
        url = f"https://www.jma.go.jp/bosai/amedas/data/map/{date_str}{hour_str}0000.json"
        
        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            
            # 複数の観測所を試行
            for station_id in station_ids:
                if station_id in data:
                    station_data = data[station_id]
                    
                    # データが存在するかチェック
                    if station_data:
                        # 現在気温
                        current_temp = None
                        if 'temp' in station_data and station_data['temp'] is not None:
                            current_temp = station_data['temp'][0]  # [値, 品質情報]の形式
                        
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
                        
                        # 何かしらのデータが取得できた場合は返す
                        if any([current_temp, humidity, precipitation, wind_speed]):
                            return {
                                'station_id': station_id,
                                'observation_time': time_to_try.strftime('%Y-%m-%d %H:%M'),
                                'current_temp': current_temp,
                                'humidity': humidity,
                                'precipitation_1h': precipitation,
                                'wind_speed': wind_speed,
                            }
                        
        except Exception as e:
            print(f"Error getting observation data for {time_to_try}: {e}")
            continue
    
    print(f"No observation data found for area {area_code}")
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
        'data_status': 'success' if (forecast_data or observation_data) else 'error'
    }
    
    return weather_record

def save_data(data_list):
    """データをCSVファイルに保存"""
    if not data_list:
        print("No weather data to save")
        return
    
    df = pd.DataFrame(data_list)
    
    # データディレクトリの作成
    data_dir = Path(__file__).parent.parent.parent / 'data' / 'raw'
    data_dir.mkdir(parents=True, exist_ok=True)
    
    csv_path = data_dir / 'weather_data.csv'
    
    # CSVに追記
    if csv_path.exists():
        df.to_csv(csv_path, mode='a', header=False, index=False, encoding='utf-8')
    else:
        df.to_csv(csv_path, index=False, encoding='utf-8')
    
    print(f"Saved {len(data_list)} weather records to {csv_path}")

def main():
    """メイン処理"""
    try:
        stores_config, scraping_config = load_config()
        
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