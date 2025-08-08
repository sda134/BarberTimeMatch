#!/usr/bin/env python3
"""Google Sheets権限テスト用スクリプト"""

import os
import json
import gspread
from google.oauth2.service_account import Credentials

def test_sheets_permission():
    """Google Sheetsの権限をテスト"""
    print("=== Google Sheets 権限テスト ===")
    
    # .envファイルから直接読み取り
    env_file = '.env'
    credentials_json = None
    spreadsheet_id = None
    
    try:
        with open(env_file, 'r') as f:
            content = f.read()
            
        # JSONを抽出 (複数行対応)
        json_start = content.find('GOOGLE_SERVICE_ACCOUNT_JSON={')
        if json_start != -1:
            json_start += len('GOOGLE_SERVICE_ACCOUNT_JSON=')
            json_end = content.find('\n}', json_start) + 2
            credentials_json = content[json_start:json_end]
            
        # Spreadsheet IDを抽出
        id_match = content.find('BARBER_SPREADSHEET_ID=')
        if id_match != -1:
            id_start = id_match + len('BARBER_SPREADSHEET_ID=')
            id_end = content.find('\n', id_start)
            spreadsheet_id = content[id_start:id_end].strip()
            
    except FileNotFoundError:
        print("❌ .envファイルが見つかりません")
        return False
    
    if not credentials_json:
        print("❌ GOOGLE_SERVICE_ACCOUNT_JSON が設定されていません")
        return False
        
    if not spreadsheet_id:
        print("❌ BARBER_SPREADSHEET_ID が設定されていません")
        return False
    
    print("✅ 環境変数は設定されています")
    
    try:
        # 認証情報をパース
        credentials_dict = json.loads(credentials_json)
        service_email = credentials_dict.get('client_email')
        project_id = credentials_dict.get('project_id')
        
        print(f"📧 Service Account Email: {service_email}")
        print(f"🔧 Project ID: {project_id}")
        
        # スコープ設定
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        # 認証
        credentials = Credentials.from_service_account_info(
            credentials_dict, 
            scopes=scopes
        )
        
        client = gspread.authorize(credentials)
        print("✅ 認証成功")
        
        # スプレッドシートにアクセス
        spreadsheet = client.open_by_key(spreadsheet_id)
        print(f"✅ スプレッドシートアクセス成功: {spreadsheet.title}")
        
        # ワークシート一覧
        worksheets = spreadsheet.worksheets()
        print(f"📊 利用可能なワークシート: {[ws.title for ws in worksheets]}")
        
        # 最初のワークシートから1行読み取りテスト
        if worksheets:
            first_sheet = worksheets[0]
            try:
                values = first_sheet.get_all_values()
                print(f"✅ データ読み取り成功: {len(values)}行")
            except Exception as e:
                print(f"❌ データ読み取りエラー: {e}")
                
        print("🎉 すべてのテストが完了しました")
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON形式エラー: {e}")
        return False
    except Exception as e:
        print(f"❌ エラー: {e}")
        return False

if __name__ == "__main__":
    test_sheets_permission()