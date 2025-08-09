
# 床屋データ分析プロジェクト

床屋の待ち時間データと天気データを自動収集し、最適な来店時間を分析するプロジェクト。

## 概要

- **対象地域**: 名古屋
- **収集データ**: 床屋待ち人数、天気予報、現在気温・湿度
- **収集頻度**: 2時間毎（9-17時）
- **自動化**: GitHub Actions

## セットアップ

```bash
# 依存関係インストール
pip install -r requirements.txt

# 手動実行テスト
python src/scraping/barber_scraper.py
python src/scraping/weather_scraper.py
```

## 設定

- `config/stores.yaml`: 床屋店舗設定
- `config/scraping_config.yaml`: スクレイピング設定

## データ

- `data/raw/barber_data.csv`: 床屋データ
- `data/raw/weather_data.csv`: 天気データ

## GitHub Actions

- データ収集: 毎日2時間毎
- 分析: 毎日0時（データ蓄積後に実装予定）


### 11. 自身をアーカイブ

```bash
zip -r ../barbartimematch_1.zip . -x "*venv*" -x ".git*"
zip -r ../ver250804.zip . -x ".venv/*" ".venv/**/*"
```
