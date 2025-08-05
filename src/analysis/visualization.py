import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from datetime import datetime
import os
import sys

# プロジェクトルートをPythonパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.scraping.utils import ensure_data_directory

# 日本語フォント設定
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.style.use('seaborn-v0_8')

class DataVisualizer:
    def __init__(self):
        self.processed_data_path = os.path.join('data', 'processed', 'merged_data.csv')
        self.viz_base_path = 'visualizations'
        
        # 出力ディレクトリを作成
        for subdir in ['heatmaps', 'trends', 'reports']:
            ensure_data_directory(os.path.join(self.viz_base_path, subdir, 'dummy.txt'))
    
    def load_processed_data(self):
        """処理済みデータを読み込む"""
        if not os.path.exists(self.processed_data_path):
            print(f"Processed data not found: {self.processed_data_path}")
            return None
        
        df = pd.read_csv(self.processed_data_path)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['date'] = pd.to_datetime(df['date'])
        
        print(f"Loaded {len(df)} records for visualization")
        return df
    
    def create_hourly_heatmap(self, df):
        """時間帯別待ち時間のヒートマップを作成"""
        if df is None or df.empty:
            return
        
        # 時間帯と曜日の待ち時間平均を計算
        pivot_data = df.groupby(['weekday_name', 'hour'])['wait_count'].mean().unstack()
        
        # 曜日の順序を調整
        weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        pivot_data = pivot_data.reindex(weekday_order)
        
        plt.figure(figsize=(12, 6))
        sns.heatmap(pivot_data, annot=True, fmt='.1f', cmap='YlOrRd', 
                   cbar_kws={'label': 'Average Wait Count'})
        plt.title('Average Wait Time by Hour and Day of Week')
        plt.xlabel('Hour of Day')
        plt.ylabel('Day of Week')
        plt.tight_layout()
        
        filepath = os.path.join(self.viz_base_path, 'heatmaps', 'hourly_wait_heatmap.png')
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Hourly heatmap saved: {filepath}")
    
    def create_daily_trends(self, df):
        """日別トレンドグラフを作成"""
        if df is None or df.empty:
            return
        
        # 日別平均待ち時間
        daily_avg = df.groupby('date')['wait_count'].agg(['mean', 'std']).reset_index()
        
        plt.figure(figsize=(12, 6))
        plt.plot(daily_avg['date'], daily_avg['mean'], marker='o', linewidth=2, markersize=4)
        plt.fill_between(daily_avg['date'], 
                        daily_avg['mean'] - daily_avg['std'], 
                        daily_avg['mean'] + daily_avg['std'], 
                        alpha=0.3)
        
        plt.title('Daily Average Wait Time Trend')
        plt.xlabel('Date')
        plt.ylabel('Average Wait Count')
        plt.xticks(rotation=45)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        filepath = os.path.join(self.viz_base_path, 'trends', 'daily_wait_trend.png')
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Daily trend saved: {filepath}")
    
    def create_weather_analysis(self, df):
        """天気と待ち時間の関係分析"""
        if df is None or df.empty or 'weather_category' not in df.columns:
            print("Weather data not available for analysis")
            return
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # 天気別待ち時間の箱ひげ図
        weather_data = df[df['weather_category'].notna()]
        if not weather_data.empty:
            sns.boxplot(data=weather_data, x='weather_category', y='wait_count', ax=ax1)
            ax1.set_title('Wait Time by Weather Category')
            ax1.set_xlabel('Weather Category')
            ax1.set_ylabel('Wait Count')
            ax1.tick_params(axis='x', rotation=45)
        
        # 気温と待ち時間の散布図
        temp_data = df[df['temp_avg'].notna() & df['wait_count'].notna()]
        if not temp_data.empty:
            ax2.scatter(temp_data['temp_avg'], temp_data['wait_count'], alpha=0.6)
            
            # 回帰線を追加
            z = np.polyfit(temp_data['temp_avg'], temp_data['wait_count'], 1)
            p = np.poly1d(z)
            ax2.plot(temp_data['temp_avg'], p(temp_data['temp_avg']), "r--", alpha=0.8)
            
            ax2.set_title('Wait Time vs Temperature')
            ax2.set_xlabel('Average Temperature (°C)')
            ax2.set_ylabel('Wait Count')
            ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        filepath = os.path.join(self.viz_base_path, 'trends', 'weather_analysis.png')
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Weather analysis saved: {filepath}")
    
    def create_store_comparison(self, df):
        """店舗間比較分析"""
        if df is None or df.empty:
            return
        
        if df['store_id'].nunique() <= 1:
            print("Only one store available, skipping store comparison")
            return
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # 店舗別平均待ち時間
        store_avg = df.groupby('store_name')['wait_count'].mean().sort_values(ascending=False)
        store_avg.plot(kind='bar', ax=ax1, color='skyblue')
        ax1.set_title('Average Wait Time by Store')
        ax1.set_xlabel('Store')
        ax1.set_ylabel('Average Wait Count')
        ax1.tick_params(axis='x', rotation=45)
        
        # 店舗別時間帯分析
        store_hourly = df.groupby(['store_name', 'time_category'])['wait_count'].mean().unstack()
        store_hourly.plot(kind='bar', ax=ax2, stacked=True)
        ax2.set_title('Wait Time by Store and Time Category')
        ax2.set_xlabel('Store')
        ax2.set_ylabel('Average Wait Count')
        ax2.tick_params(axis='x', rotation=45)
        ax2.legend(title='Time Category', bbox_to_anchor=(1.05, 1), loc='upper left')
        
        plt.tight_layout()
        filepath = os.path.join(self.viz_base_path, 'trends', 'store_comparison.png')
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Store comparison saved: {filepath}")
    
    def create_time_analysis(self, df):
        """時間分析（時間帯、曜日別）"""
        if df is None or df.empty:
            return
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
        
        # 時間帯別平均待ち時間
        hourly_avg = df.groupby('hour')['wait_count'].mean()
        ax1.plot(hourly_avg.index, hourly_avg.values, marker='o', linewidth=2)
        ax1.set_title('Average Wait Time by Hour')
        ax1.set_xlabel('Hour of Day')
        ax1.set_ylabel('Average Wait Count')
        ax1.grid(True, alpha=0.3)
        
        # 曜日別平均待ち時間
        weekday_avg = df.groupby('weekday_name')['wait_count'].mean()
        weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        weekday_avg = weekday_avg.reindex(weekday_order)
        weekday_avg.plot(kind='bar', ax=ax2, color='lightcoral')
        ax2.set_title('Average Wait Time by Day of Week')
        ax2.set_xlabel('Day of Week')
        ax2.set_ylabel('Average Wait Count')
        ax2.tick_params(axis='x', rotation=45)
        
        # 月別トレンド
        if 'month' in df.columns:
            monthly_avg = df.groupby('month')['wait_count'].mean()
            ax3.plot(monthly_avg.index, monthly_avg.values, marker='s', linewidth=2, color='green')
            ax3.set_title('Average Wait Time by Month')
            ax3.set_xlabel('Month')
            ax3.set_ylabel('Average Wait Count')
            ax3.set_xticks(range(1, 13))
            ax3.grid(True, alpha=0.3)
        
        # 時間カテゴリ別分布
        time_cat_avg = df.groupby('time_category')['wait_count'].mean().sort_values(ascending=False)
        time_cat_avg.plot(kind='bar', ax=ax4, color='orange')
        ax4.set_title('Average Wait Time by Time Category')
        ax4.set_xlabel('Time Category')
        ax4.set_ylabel('Average Wait Count')
        ax4.tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        filepath = os.path.join(self.viz_base_path, 'trends', 'time_analysis.png')
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Time analysis saved: {filepath}")
    
    def generate_summary_report(self, df):
        """サマリーレポートを生成"""
        if df is None or df.empty:
            return
        
        # 基本統計
        stats = {
            'total_records': len(df),
            'date_range': f"{df['date'].min().strftime('%Y-%m-%d')} to {df['date'].max().strftime('%Y-%m-%d')}",
            'stores_count': df['store_id'].nunique(),
            'avg_wait_time': df['wait_count'].mean(),
            'max_wait_time': df['wait_count'].max(),
            'min_wait_time': df['wait_count'].min(),
        }
        
        # 最適な来店時間
        best_hours = df.groupby('hour')['wait_count'].mean().sort_values().head(3)
        best_days = df.groupby('weekday_name')['wait_count'].mean().sort_values().head(3)
        
        # レポート作成
        report = f"""
# Barber Shop Analysis Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary Statistics
- Total Records: {stats['total_records']:,}
- Date Range: {stats['date_range']}
- Number of Stores: {stats['stores_count']}
- Average Wait Time: {stats['avg_wait_time']:.1f} people
- Maximum Wait Time: {stats['max_wait_time']:.0f} people
- Minimum Wait Time: {stats['min_wait_time']:.0f} people

## Best Times to Visit
### Best Hours (lowest wait times):
"""
        
        for hour, wait_time in best_hours.items():
            report += f"- {hour:02d}:00 - Average wait: {wait_time:.1f} people\n"
        
        report += "\n### Best Days (lowest wait times):\n"
        for day, wait_time in best_days.items():
            report += f"- {day} - Average wait: {wait_time:.1f} people\n"
        
        # レポートを保存
        report_path = os.path.join(self.viz_base_path, 'reports', 'analysis_summary.md')
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"Summary report saved: {report_path}")
        return report

def main():
    """メイン処理"""
    visualizer = DataVisualizer()
    
    print("Starting data visualization...")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # データ読み込み
    df = visualizer.load_processed_data()
    
    if df is not None and not df.empty:
        # 各種可視化を実行
        visualizer.create_hourly_heatmap(df)
        visualizer.create_daily_trends(df)
        visualizer.create_weather_analysis(df)
        visualizer.create_store_comparison(df)
        visualizer.create_time_analysis(df)
        
        # サマリーレポート生成
        report = visualizer.generate_summary_report(df)
        print("\n" + "="*50)
        print(report)
        print("="*50)
    
    print("Data visualization completed!")

if __name__ == "__main__":
    main()