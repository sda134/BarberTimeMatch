import pandas as pd
import numpy as np
from datetime import datetime
import os
import sys

# プロジェクトルートをPythonパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.scraping.utils import ensure_data_directory

class DataPreprocessor:
    def __init__(self):
        self.barber_data_path = os.path.join('data', 'raw', 'barber_data.csv')
        self.weather_data_path = os.path.join('data', 'raw', 'weather_data.csv')
        self.merged_data_path = os.path.join('data', 'processed', 'merged_data.csv')
    
    def load_raw_data(self):
        """生データを読み込む"""
        barber_df = None
        weather_df = None
        
        if os.path.exists(self.barber_data_path):
            barber_df = pd.read_csv(self.barber_data_path)
            print(f"Loaded {len(barber_df)} barber records")
        else:
            print("No barber data found")
        
        if os.path.exists(self.weather_data_path):
            weather_df = pd.read_csv(self.weather_data_path)
            print(f"Loaded {len(weather_df)} weather records")
        else:
            print("No weather data found")
        
        return barber_df, weather_df
    
    def clean_barber_data(self, df):
        """床屋データのクリーニング"""
        if df is None or df.empty:
            return df
        
        # データ型の変換
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['date'] = pd.to_datetime(df['date'])
        
        # 数値データの処理
        df['wait_count'] = pd.to_numeric(df['wait_count'], errors='coerce')
        df['hour'] = pd.to_numeric(df['hour'], errors='coerce')
        df['minute'] = pd.to_numeric(df['minute'], errors='coerce')
        
        # 曜日情報の追加
        df['weekday'] = df['date'].dt.dayofweek  # 0=月曜日
        df['weekday_name'] = df['date'].dt.day_name()
        
        # 時間帯カテゴリの追加
        df['time_category'] = df['hour'].apply(self._categorize_time)
        
        # 異常値の除去（待ち人数が負数または異常に大きい値）
        df = df[(df['wait_count'].isna()) | 
                ((df['wait_count'] >= 0) & (df['wait_count'] <= 50))]
        
        # 重複データの除去
        df = df.drop_duplicates(subset=['timestamp', 'store_id'])
        
        print(f"Cleaned barber data: {len(df)} records")
        return df
    
    def clean_weather_data(self, df):
        """天気データのクリーニング"""
        if df is None or df.empty:
            return df
        
        # データ型の変換
        df['date'] = pd.to_datetime(df['date'])
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # 気温データの処理
        df['temp_min'] = pd.to_numeric(df['temp_min'], errors='coerce')
        df['temp_max'] = pd.to_numeric(df['temp_max'], errors='coerce')
        
        # 天気カテゴリの簡素化
        df['weather_category'] = df['weather'].apply(self._categorize_weather)
        
        # 重複データの除去（同じ日付の最新データを保持）
        df = df.sort_values('timestamp').drop_duplicates(subset=['date'], keep='last')
        
        print(f"Cleaned weather data: {len(df)} records")
        return df
    
    def _categorize_time(self, hour):
        """時間を カテゴリに分類"""
        if pd.isna(hour):
            return 'unknown'
        elif 6 <= hour < 9:
            return 'morning'
        elif 9 <= hour < 12:
            return 'morning_peak'
        elif 12 <= hour < 15:
            return 'afternoon'
        elif 15 <= hour < 18:
            return 'evening_peak'
        elif 18 <= hour < 21:
            return 'evening'
        else:
            return 'night'
    
    def _categorize_weather(self, weather):
        """天気を簡単なカテゴリに分類"""
        if pd.isna(weather):
            return 'unknown'
        
        weather = str(weather).lower()
        if '晴れ' in weather or 'sunny' in weather:
            return 'sunny'
        elif '雨' in weather or 'rain' in weather:
            return 'rainy'
        elif '曇り' in weather or 'cloud' in weather:
            return 'cloudy'
        elif '雪' in weather or 'snow' in weather:
            return 'snowy'
        else:
            return 'other'
    
    def merge_data(self, barber_df, weather_df):
        """床屋データと天気データを結合"""
        if barber_df is None or barber_df.empty:
            print("No barber data to merge")
            return None
        
        if weather_df is None or weather_df.empty:
            print("No weather data to merge, using barber data only")
            return barber_df
        
        # 日付でマージ
        merged_df = pd.merge(
            barber_df, 
            weather_df[['date', 'weather', 'weather_category', 'temp_min', 'temp_max']], 
            on='date', 
            how='left'
        )
        
        print(f"Merged data: {len(merged_df)} records")
        return merged_df
    
    def add_derived_features(self, df):
        """派生特徴量を追加"""
        if df is None or df.empty:
            return df
        
        # 平均気温
        df['temp_avg'] = (df['temp_min'] + df['temp_max']) / 2
        df['temp_avg'] = df['temp_avg'].fillna(df['temp_avg'].mean())
        
        # 月情報
        df['month'] = df['date'].dt.month
        df['season'] = df['month'].apply(self._get_season)
        
        # 時間特徴量
        df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
        df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
        
        # 曜日特徴量
        df['weekday_sin'] = np.sin(2 * np.pi * df['weekday'] / 7)
        df['weekday_cos'] = np.cos(2 * np.pi * df['weekday'] / 7)
        
        print(f"Added derived features: {df.shape[1]} columns")
        return df
    
    def _get_season(self, month):
        """月から季節を取得"""
        if month in [12, 1, 2]:
            return 'winter'
        elif month in [3, 4, 5]:
            return 'spring'
        elif month in [6, 7, 8]:
            return 'summer'
        else:
            return 'autumn'
    
    def save_processed_data(self, df):
        """処理済みデータを保存"""
        if df is None or df.empty:
            print("No data to save")
            return
        
        ensure_data_directory(self.merged_data_path)
        df.to_csv(self.merged_data_path, index=False)
        print(f"Processed data saved to {self.merged_data_path}")
    
    def generate_summary_stats(self, df):
        """データの概要統計を生成"""
        if df is None or df.empty:
            return {}
        
        stats = {
            'total_records': len(df),
            'date_range': {
                'start': df['date'].min().strftime('%Y-%m-%d'),
                'end': df['date'].max().strftime('%Y-%m-%d')
            },
            'stores': df['store_id'].nunique(),
            'avg_wait_count': df['wait_count'].mean(),
            'max_wait_count': df['wait_count'].max(),
            'data_completeness': {
                'wait_count': (df['wait_count'].notna().sum() / len(df)) * 100,
                'weather': (df['weather'].notna().sum() / len(df)) * 100 if 'weather' in df.columns else 0
            }
        }
        
        return stats

def main():
    """メイン処理"""
    processor = DataPreprocessor()
    
    print("Starting data preprocessing...")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # データ読み込み
    barber_df, weather_df = processor.load_raw_data()
    
    # データクリーニング
    barber_df = processor.clean_barber_data(barber_df)
    weather_df = processor.clean_weather_data(weather_df)
    
    # データ結合
    merged_df = processor.merge_data(barber_df, weather_df)
    
    # 派生特徴量の追加
    if merged_df is not None:
        merged_df = processor.add_derived_features(merged_df)
        
        # 概要統計の生成
        stats = processor.generate_summary_stats(merged_df)
        print("\nSummary Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        # 処理済みデータの保存
        processor.save_processed_data(merged_df)
    
    print("Data preprocessing completed!")

if __name__ == "__main__":
    main()