#!/usr/bin/env python3
"""
簡単実行用スクリプト
"""

import subprocess
import sys
import os

def main():
    """簡単実行"""
    print("床屋データ分析プロジェクトを実行します...")
    
    # main.pyを実行
    try:
        result = subprocess.run([sys.executable, 'main.py'], 
                              cwd=os.path.dirname(__file__),
                              check=True)
        print("実行完了!")
    except subprocess.CalledProcessError as e:
        print(f"実行エラー: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()