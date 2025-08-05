import yaml
import os
import random
import time
from typing import Dict, Any

def load_config(config_file: str = 'config/scraping_config.yaml') -> Dict[str, Any]:
    """設定ファイルを読み込む"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), config_file)
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def load_stores_config(stores_file: str = 'config/stores.yaml') -> Dict[str, Any]:
    """店舗設定ファイルを読み込む"""
    stores_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), stores_file)
    with open(stores_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def get_random_wait_time(min_time: float = 1.0, max_time: float = 3.0) -> None:
    """ランダムな待機時間を設ける"""
    wait_time = random.uniform(min_time, max_time)
    time.sleep(wait_time)

def ensure_data_directory(data_path: str) -> None:
    """データディレクトリが存在しない場合は作成"""
    os.makedirs(os.path.dirname(data_path), exist_ok=True)

def generate_mock_wait_count() -> int:
    """モックデータとして待ち人数を生成"""
    # 現在時刻に基づいて疑似的な待ち時間を生成
    hour = time.localtime().tm_hour
    if 10 <= hour <= 12 or 15 <= hour <= 18:  # 混雑時間帯
        return random.randint(3, 15)
    elif 13 <= hour <= 14:  # 昼休み
        return random.randint(8, 20)
    else:  # 空いている時間
        return random.randint(0, 5)