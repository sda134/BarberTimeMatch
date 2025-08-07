"""
Google Sheets API連携ユーティリティ
床屋データと気象データをGoogle Spreadsheetsに保存
"""

import os
import json
from typing import List, Dict, Any, Optional
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

class GoogleSheetsManager:
    def __init__(self):
        self.credentials = self._get_credentials()
        self.service = build('sheets', 'v4', credentials=self.credentials)
        
        # SpreadsheetのID
        self.barber_spreadsheet_id = os.getenv('BARBER_SPREADSHEET_ID')
        self.weather_spreadsheet_id = os.getenv('WEATHER_SPREADSHEET_ID')
        
        if not self.barber_spreadsheet_id or not self.weather_spreadsheet_id:
            raise ValueError("Spreadsheet IDs must be set in environment variables")
    
    def _get_credentials(self) -> Credentials:
        """Google Sheets API認証情報を取得"""
        # 環境変数からJSONを直接読み込む（GitHub Actions用）
        service_account_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
        if service_account_json:
            try:
                service_account_info = json.loads(service_account_json)
                return Credentials.from_service_account_info(
                    service_account_info,
                    scopes=['https://www.googleapis.com/auth/spreadsheets']
                )
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON in GOOGLE_SERVICE_ACCOUNT_JSON")
        
        # ローカル開発用：JSONファイルから読み込み
        credentials_file = os.getenv('GOOGLE_CREDENTIALS_FILE')
        if credentials_file and os.path.exists(credentials_file):
            return Credentials.from_service_account_file(
                credentials_file,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
        
        raise ValueError("Google credentials not found. Set GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_CREDENTIALS_FILE")
    
    def append_barber_data(self, data: List[Dict[str, Any]]) -> None:
        """床屋データをSpreadsheetに追記"""
        if not data:
            return
        
        df = pd.DataFrame(data)
        self._append_data_to_sheet(
            self.barber_spreadsheet_id, 
            'barber_data',
            df,
            ['timestamp', 'store_id', 'store_name', 'wait_count', 'area', 'day_of_week', 'hour', 'is_holiday']
        )
    
    def append_weather_data(self, data: List[Dict[str, Any]]) -> None:
        """気象データをSpreadsheetに追記"""
        if not data:
            return
        
        df = pd.DataFrame(data)
        self._append_data_to_sheet(
            self.weather_spreadsheet_id,
            'weather_data', 
            df,
            ['date', 'area_code', 'area_name', 'weather', 'temp_min', 'temp_max', 'timestamp']
        )
    
    def _append_data_to_sheet(self, spreadsheet_id: str, sheet_name: str, 
                            df: pd.DataFrame, expected_columns: List[str]) -> None:
        """データをシートに追記（ヘッダーがない場合は作成）"""
        try:
            # シートの存在確認・作成
            self._ensure_sheet_exists(spreadsheet_id, sheet_name, expected_columns)
            
            # データを準備（欠損カラムは空文字で埋める）
            for col in expected_columns:
                if col not in df.columns:
                    df[col] = ''
            
            # カラム順を統一
            df_ordered = df[expected_columns]
            
            # データを2次元リストに変換
            values = df_ordered.values.tolist()
            
            # Spreadsheetにデータ追記
            self.service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=f"{sheet_name}!A:A",
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body={'values': values}
            ).execute()
            
            print(f"Successfully appended {len(values)} rows to {sheet_name}")
            
        except Exception as e:
            print(f"Error appending data to {sheet_name}: {e}")
            raise
    
    def _ensure_sheet_exists(self, spreadsheet_id: str, sheet_name: str, 
                           header_columns: List[str]) -> None:
        """シートの存在確認、なければ作成してヘッダー設定"""
        try:
            # 既存シート一覧を取得
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()
            
            sheet_names = [sheet['properties']['title'] 
                          for sheet in spreadsheet['sheets']]
            
            # シートが存在しない場合は作成
            if sheet_name not in sheet_names:
                self._create_sheet_with_headers(spreadsheet_id, sheet_name, header_columns)
            else:
                # 既存シートにヘッダーがあるかチェック
                self._check_and_add_headers(spreadsheet_id, sheet_name, header_columns)
                
        except Exception as e:
            print(f"Error ensuring sheet {sheet_name} exists: {e}")
            raise
    
    def _create_sheet_with_headers(self, spreadsheet_id: str, sheet_name: str, 
                                 header_columns: List[str]) -> None:
        """新しいシートを作成してヘッダーを設定"""
        # シート作成
        body = {
            'requests': [{
                'addSheet': {
                    'properties': {
                        'title': sheet_name
                    }
                }
            }]
        }
        self.service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=body
        ).execute()
        
        # ヘッダー追加
        self.service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet_name}!1:1",
            valueInputOption='RAW',
            body={'values': [header_columns]}
        ).execute()
        
        print(f"Created sheet '{sheet_name}' with headers")
    
    def _check_and_add_headers(self, spreadsheet_id: str, sheet_name: str, 
                             header_columns: List[str]) -> None:
        """既存シートにヘッダーがない場合は追加"""
        try:
            # 1行目を取得
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=f"{sheet_name}!1:1"
            ).execute()
            
            values = result.get('values', [])
            
            # ヘッダーがない、または期待するヘッダーと異なる場合
            if not values or values[0] != header_columns:
                # データが存在する場合は1行挿入してヘッダーを追加
                if values:  # データがある場合
                    self.service.spreadsheets().batchUpdate(
                        spreadsheetId=spreadsheet_id,
                        body={
                            'requests': [{
                                'insertDimension': {
                                    'range': {
                                        'sheetId': self._get_sheet_id(spreadsheet_id, sheet_name),
                                        'dimension': 'ROWS',
                                        'startIndex': 0,
                                        'endIndex': 1
                                    },
                                    'inheritFromBefore': False
                                }
                            }]
                        }
                    ).execute()
                
                # ヘッダー設定
                self.service.spreadsheets().values().update(
                    spreadsheetId=spreadsheet_id,
                    range=f"{sheet_name}!1:1",
                    valueInputOption='RAW',
                    body={'values': [header_columns]}
                ).execute()
                
                print(f"Added headers to existing sheet '{sheet_name}'")
                
        except Exception as e:
            # エラーが発生した場合はヘッダーなしでスキップ
            print(f"Warning: Could not check/add headers for {sheet_name}: {e}")
    
    def _get_sheet_id(self, spreadsheet_id: str, sheet_name: str) -> int:
        """シート名からシートIDを取得"""
        spreadsheet = self.service.spreadsheets().get(
            spreadsheetId=spreadsheet_id
        ).execute()
        
        for sheet in spreadsheet['sheets']:
            if sheet['properties']['title'] == sheet_name:
                return sheet['properties']['sheetId']
        
        raise ValueError(f"Sheet '{sheet_name}' not found")