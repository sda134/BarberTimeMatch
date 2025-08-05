# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# 床屋データ分析プロジェクト

## プロジェクト概要
大衆床屋チェーンの待ち時間データを定期的に収集し、最適な来店時間を分析するプロジェクト。GitHub Actionsを使用してPythonでスクレイピング、データ蓄積、分析、可視化まで一元管理。

## 学習目標
- lxml + XPathによる堅牢なスクレイピング
- GitHub Actionsでのワークフロー自動化
- pandas/matplotlib/seabornでのデータ分析
- 時系列分析と予測モデル構築
- 気象データとの相関分析

## リポジトリ構成
```
barber-analysis/
├── .github/workflows/
│   ├── scraping.yml              # データ収集ワークフロー
│   └── analysis.yml              # 分析・可視化ワークフロー
├── src/
│   ├── scraping/
│   │   ├── barber_scraper.py     # 床屋データ取得
│   │   ├── weather_scraper.py    # 気象データ取得
│   │   └── utils.py              # 共通ユーティリティ
│   ├── analysis/
│   │   ├── data_preprocessing.py # データクレンジング
│   │   ├── time_series_analysis.py # 時系列分析
│   │   └── visualization.py      # グラフ作成
│   └── models/
│       ├── wait_time_predictor.py # 待ち時間予測モデル
│       └── seasonal_analyzer.py   # 季節性分析
├── data/
│   ├── raw/
│   │   ├── barber_data.csv       # 床屋生データ
│   │   └── weather_data.csv      # 気象生データ
│   ├── processed/
│   │   └── merged_data.csv       # 結合・加工済みデータ
│   └── results/
│       ├── analysis_results.json # 分析結果
│       └── predictions.csv       # 予測結果
├── visualizations/
│   ├── heatmaps/                 # 時間帯別ヒートマップ
│   ├── trends/                   # トレンド分析グラフ
│   └── reports/                  # 分析レポート
├── config/
│   ├── scraping_config.yaml      # スクレイピング設定
│   └── stores.yaml               # 対象店舗情報
├── requirements.txt              # Python依存関係
├── README.md                     # プロジェクト説明
└── CLAUDE.md                     # このファイル
```

## 現在の状況
**注意**: このプロジェクトは現在、仕様書段階です。実装はまだ開始されていません。

## セットアップ手順

### 1. プロジェクト初期化
現在のディレクトリ構造を作成する必要があります:
```bash
# ディレクトリ構造作成
mkdir -p .github/workflows src/{scraping,analysis,models} data/{raw,processed,results} visualizations/{heatmaps,trends,reports} config
```

### 2. 依存関係定義 (requirements.txt)
```
requests==2.31.0
lxml==4.9.3
pandas==2.1.0
matplotlib==3.7.2
seaborn==0.12.2
scikit-learn==1.3.0
pyyaml==6.0.1
```

### 3. 設定ファイル作成

#### config/stores.yaml
```yaml
stores:
  - id: "main_store"
    name: "よく行く店舗"
    url: "https://example-barber.com/store/main"
    xpath_wait_count: "//div[@class='wait-number']/text()"
    area: "東京都"
    weather_area_code: "130000"  # 東京都の気象庁エリアコード
  - id: "nagoya_store"
    name: "名古屋店舗例"
    url: "https://example-barber.com/store/nagoya"
    xpath_wait_count: "//div[@class='wait-number']/text()"
    area: "愛知県"
    weather_area_code: "230000"  # 愛知県の気象庁エリアコード

# 主要エリアコード参考:
# 130000: 東京都
# 140000: 神奈川県  
# 230000: 愛知県
# 270000: 大阪府
# 280000: 兵庫県
# 400000: 福岡県
```

#### config/scraping_config.yaml
```yaml
scraping:
  user_agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
  timeout: 10
  retry_count: 3
  delay_between_requests: 2

weather:
  api_endpoint: "https://www.jma.go.jp/bosai/forecast/data/forecast/"
  # area_codeは各店舗のweather_area_codeから動的に取得
  
schedule:
  weekdays: [0, 1, 2, 3, 4, 5, 6]  # 月-日 (全曜日対象)
  hours: [9, 10, 11, 12, 13, 14, 15, 16, 17, 18]  # 営業時間内
  business_days_only: false  # 祝日も収集対象とする場合はfalse
```

### 4. GitHub Actions ワークフロー

#### .github/workflows/scraping.yml
```yaml
name: データ収集

on:
  schedule:
    # 毎日9-18時、毎時0分に実行 (UTC時間で設定)
    - cron: '0 0-9 * * *'  # JST 9-18時 (全曜日)
  workflow_dispatch:  # 手動実行も可能

jobs:
  scrape-data:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout
      uses: actions/checkout@v4
      
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
        
    - name: Install dependencies
      run: pip install -r requirements.txt
      
    - name: Run barber scraping
      run: python src/scraping/barber_scraper.py
      
    - name: Run weather scraping  
      run: python src/scraping/weather_scraper.py
      
    - name: Commit data
      run: |
        git config --local user.email "action@github.com"
        git config --local user.name "GitHub Action"
        git add data/raw/
        git commit -m "Add data: $(date '+%Y-%m-%d %H:%M')" || exit 0
        git push
```

#### .github/workflows/analysis.yml
```yaml
name: データ分析・可視化

on:
  schedule:
    # 毎日夜に分析実行
    - cron: '0 15 * * *'  # JST 0:00
  workflow_dispatch:

jobs:
  analyze-data:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout
      uses: actions/checkout@v4
      
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
        
    - name: Install dependencies
      run: pip install -r requirements.txt
      
    - name: Data preprocessing
      run: python src/analysis/data_preprocessing.py
      
    - name: Generate visualizations
      run: python src/analysis/visualization.py
      
    - name: Time series analysis
      run: python src/analysis/time_series_analysis.py
      
    - name: Update predictions
      run: python src/models/wait_time_predictor.py
      
    - name: Commit results
      run: |
        git config --local user.email "action@github.com"
        git config --local user.name "GitHub Action"
        git add data/processed/ data/results/ visualizations/
        git commit -m "Update analysis: $(date '+%Y-%m-%d')" || exit 0
        git push
```

## 主要なPythonスクリプト例

### src/scraping/barber_scraper.py
```python
import requests
from lxml import html
import pandas as pd
from datetime import datetime
import yaml
import time
import os

def load_config():
    with open('config/stores.yaml', 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def scrape_store_data(store_config):
    """単一店舗のデータを取得"""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        response = requests.get(store_config['url'], headers=headers, timeout=10)
        response.raise_for_status()
        
        tree = html.fromstring(response.content)
        wait_count_elements = tree.xpath(store_config['xpath_wait_count'])
        
        if wait_count_elements:
            wait_count = int(wait_count_elements[0].strip())
        else:
            wait_count = None
            
        return {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'store_id': store_config['id'],
            'store_name': store_config['name'],
            'wait_count': wait_count,
            'area': store_config['area'],
            'day_of_week': datetime.now().strftime('%A'),
            'hour': datetime.now().hour,
            'is_holiday': False  # 祝日判定は別途実装
        }
    except Exception as e:
        print(f"Error scraping {store_config['name']}: {e}")
        return None

def main():
    config = load_config()
    all_data = []
    
    for store in config['stores']:
        data = scrape_store_data(store)
        if data:
            all_data.append(data)
        time.sleep(2)  # レート制限対策
    
    if all_data:
        df = pd.DataFrame(all_data)
        
        # CSVに追記
        csv_path = 'data/raw/barber_data.csv'
        if os.path.exists(csv_path):
            df.to_csv(csv_path, mode='a', header=False, index=False)
        else:
            df.to_csv(csv_path, index=False)
        
        print(f"Collected data for {len(all_data)} stores")

if __name__ == "__main__":
    main()
```

### src/scraping/weather_scraper.py
```python
import requests
import pandas as pd
from datetime import datetime
import yaml
import os

def load_stores_config():
    """stores.yamlから店舗設定を読み込み"""
    with open('config/stores.yaml', 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def get_unique_area_codes():
    """設定されている店舗の重複しないエリアコードを取得"""
    config = load_stores_config()
    area_codes = set()
    for store in config['stores']:
        if 'weather_area_code' in store:
            area_codes.add(store['weather_area_code'])
    return list(area_codes)

def get_weather_data(area_code):
    """指定エリアコードの気象庁APIから天気データを取得"""
    url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{area_code}.json"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # 今日の天気情報を抽出
        today_weather = data[0]['timeSeries'][0]['areas'][0]['weathers'][0]
        today_temp_min = data[0]['timeSeries'][2]['areas'][0]['tempsMin'][0] if data[0]['timeSeries'][2]['areas'][0]['tempsMin'] else None
        today_temp_max = data[0]['timeSeries'][2]['areas'][0]['tempsMax'][0] if data[0]['timeSeries'][2]['areas'][0]['tempsMax'] else None
        area_name = data[0]['timeSeries'][0]['areas'][0]['area']['name']
        
        return {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'area_code': area_code,
            'area_name': area_name,
            'weather': today_weather,
            'temp_min': today_temp_min,
            'temp_max': today_temp_max,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        print(f"Error getting weather data for area {area_code}: {e}")
        return None

def main():
    """全ての対象エリアの天気データを収集"""
    area_codes = get_unique_area_codes()
    all_weather_data = []
    
    for area_code in area_codes:
        weather_data = get_weather_data(area_code)
        if weather_data:
            all_weather_data.append(weather_data)
    
    if all_weather_data:
        new_df = pd.DataFrame(all_weather_data)
        
        csv_path = 'data/raw/weather_data.csv'
        if os.path.exists(csv_path):
            # 同じ日・エリアのデータは上書き
            existing_df = pd.read_csv(csv_path)
            today = datetime.now().strftime('%Y-%m-%d')
            existing_df = existing_df[existing_df['date'] != today]
            df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            df = new_df
        
        df.to_csv(csv_path, index=False)
        print(f"Weather data collected for {len(all_weather_data)} areas")

if __name__ == "__main__":
    main()
```

## 実装方針・学習目標

### データ収集フェーズ
- GitHub Actions + Pythonによる自動化システムの構築
- lxml + XPathによるWebスクレイピング技術の習得
- YAML設定ファイルによる設定管理

### データ分析フェーズ
**重要**: データ分析部分の実装は学習目的のため、基本的に自力で行う。
- pandas, matplotlib, seabornを使った基礎分析
- 時系列分析・統計分析手法の習得
- 機械学習モデル構築の実践
- 可視化・レポート作成スキルの向上

Claude Codeの役割：
- データ収集システムの構築支援
- 分析手法やアプローチの相談・アドバイス
- エラー解決やコードレビュー
- 技術的な実装詳細の質問対応

## 分析フェーズ

### Phase 1: 基礎分析
- 曜日・時間帯別の待ち時間分布
- 天気と待ち時間の相関
- 月次・季節トレンドの把握

### Phase 2: 予測モデル
- scikit-learnでの回帰分析
- 時系列予測（ARIMA、Prophet）
- 特徴量エンジニアリング

### Phase 3: 高度な分析
- 季節性の分析
- 異常値検知
- クラスタリング分析

## 拡張予定
- 他の生活データとの連携（家計簿、行動ログ）
- リアルタイムダッシュボード（GitHub Pages）
- LINE Bot連携で最適時間通知
- 機械学習モデルの精度向上

## 注意事項
- スクレイピング対象サイトの利用規約遵守
- レート制限の実装（requests間隔制御）
- エラーハンドリングの充実
- データのバックアップ戦略

このプロジェクトを通じて、実践的なデータサイエンススキルと現代的な開発ワークフローを習得できます。
