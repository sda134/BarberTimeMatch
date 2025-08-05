#!/usr/bin/env python3
"""
床屋データ分析プロジェクト - ローカル実行用メインスクリプト

このスクリプトを実行することで、データ収集から分析・可視化まで
一連の処理をローカル環境で実行できます。
"""

import argparse
import sys
import os
from datetime import datetime

# プロジェクトルートをPythonパスに追加
sys.path.append(os.path.dirname(__file__))

def run_data_collection():
    """データ収集を実行"""
    print("="*60)
    print("STEP 1: データ収集")
    print("="*60)
    
    try:
        # 床屋データ収集
        print("\n[1/2] 床屋データを収集中...")
        from src.scraping.barber_scraper import main as barber_main
        barber_main()
        
        # 天気データ収集
        print("\n[2/2] 天気データを収集中...")
        from src.scraping.weather_scraper import main as weather_main
        weather_main()
        
        print("\n✅ データ収集が完了しました")
        return True
        
    except Exception as e:
        print(f"\n❌ データ収集でエラーが発生しました: {e}")
        return False

def run_data_processing():
    """データ前処理を実行"""
    print("\n" + "="*60)
    print("STEP 2: データ前処理")
    print("="*60)
    
    try:
        from src.analysis.data_preprocessing import main as preprocessing_main
        preprocessing_main()
        
        print("\n✅ データ前処理が完了しました")
        return True
        
    except Exception as e:
        print(f"\n❌ データ前処理でエラーが発生しました: {e}")
        return False

def run_visualization():
    """データ可視化を実行"""
    print("\n" + "="*60)
    print("STEP 3: データ可視化・分析")
    print("="*60)
    
    try:
        from src.analysis.visualization import main as visualization_main
        visualization_main()
        
        print("\n✅ データ可視化・分析が完了しました")
        return True
        
    except Exception as e:
        print(f"\n❌ データ可視化・分析でエラーが発生しました: {e}")
        return False

def check_dependencies():
    """必要な依存関係をチェック"""
    required_packages = [
        'requests', 'lxml', 'pandas', 'matplotlib', 
        'seaborn', 'scikit-learn', 'pyyaml', 'numpy'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ 以下のパッケージがインストールされていません:")
        for package in missing_packages:
            print(f"  - {package}")
        print("\n以下のコマンドでインストールしてください:")
        print("pip install -r requirements.txt")
        return False
    
    print("✅ 必要な依存関係がすべて揃っています")
    return True

def show_results():
    """結果を表示"""
    print("\n" + "="*60)
    print("実行結果")
    print("="*60)
    
    # データファイルの存在確認
    data_files = [
        ('data/raw/barber_data.csv', '床屋データ'),
        ('data/raw/weather_data.csv', '天気データ'),
        ('data/processed/merged_data.csv', '結合済みデータ')
    ]
    
    print("\n📊 生成されたデータファイル:")
    for filepath, description in data_files:
        if os.path.exists(filepath):
            size = os.path.getsize(filepath)
            print(f"  ✅ {description}: {filepath} ({size:,} bytes)")
        else:
            print(f"  ❌ {description}: {filepath} (存在しません)")
    
    # 可視化ファイルの確認
    viz_files = [
        'visualizations/heatmaps/hourly_wait_heatmap.png',
        'visualizations/trends/daily_wait_trend.png',
        'visualizations/trends/weather_analysis.png',
        'visualizations/trends/time_analysis.png',
        'visualizations/reports/analysis_summary.md'
    ]
    
    print("\n📈 生成された可視化ファイル:")
    for filepath in viz_files:
        if os.path.exists(filepath):
            print(f"  ✅ {filepath}")
        else:
            print(f"  ❌ {filepath} (生成されませんでした)")
    
    # レポートの内容を表示
    report_path = 'visualizations/reports/analysis_summary.md'
    if os.path.exists(report_path):
        print("\n📋 分析レポート:")
        print("-" * 40)
        with open(report_path, 'r', encoding='utf-8') as f:
            print(f.read())
        print("-" * 40)

def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(
        description='床屋データ分析プロジェクト - ローカル実行用',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python main.py                    # 全処理を実行
  python main.py --collect-only     # データ収集のみ
  python main.py --process-only     # データ前処理のみ
  python main.py --visualize-only   # 可視化のみ
  python main.py --check-deps       # 依存関係チェックのみ
        """
    )
    
    parser.add_argument('--collect-only', action='store_true',
                       help='データ収集のみ実行')
    parser.add_argument('--process-only', action='store_true',
                       help='データ前処理のみ実行')
    parser.add_argument('--visualize-only', action='store_true',
                       help='データ可視化のみ実行')
    parser.add_argument('--check-deps', action='store_true',
                       help='依存関係チェックのみ実行')
    parser.add_argument('--no-results', action='store_true',
                       help='結果表示をスキップ')
    
    args = parser.parse_args()
    
    print("🏪 床屋データ分析プロジェクト")
    print(f"開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 依存関係チェック
    if args.check_deps:
        check_dependencies()
        return
    
    if not check_dependencies():
        sys.exit(1)
    
    # 実行フラグの設定
    run_collect = args.collect_only or not any([args.process_only, args.visualize_only])
    run_process = args.process_only or not any([args.collect_only, args.visualize_only])
    run_viz = args.visualize_only or not any([args.collect_only, args.process_only])
    
    success = True
    
    # データ収集
    if run_collect:
        if not run_data_collection():
            success = False
    
    # データ前処理
    if run_process and success:
        if not run_data_processing():
            success = False
    
    # データ可視化
    if run_viz and success:
        if not run_visualization():
            success = False
    
    # 結果表示
    if not args.no_results:
        show_results()
    
    # 最終結果
    print("\n" + "="*60)
    if success:
        print("🎉 すべての処理が正常に完了しました！")
        print("\nNext Steps:")
        print("- visualizations/ フォルダ内のグラフを確認してください")
        print("- visualizations/reports/analysis_summary.md でサマリーレポートを確認してください")
        print("- 必要に応じて config/stores.yaml で実際の店舗情報を設定してください")
    else:
        print("❌ 一部の処理でエラーが発生しました")
        sys.exit(1)
    
    print(f"完了時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()