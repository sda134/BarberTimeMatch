"""
Google Sheets API連携ユーティリティ
床屋データと気象データをGoogle Spreadsheetsに保存
"""

import os
import json
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import pandas as pd

# gspreadを試す（requirements.txtに含まれている）
try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_AVAILABLE = True
except ImportError:
    # フォールバック
    from googleapiclient.discovery import build
    from google.oauth2.service_account import Credentials
    GSPREAD_AVAILABLE = False

# 統一ヘッダー定義をインポート
from src.scraping.utils import BARBER_DATA_HEADERS, WEATHER_DATA_HEADERS

load_dotenv()

class GoogleSheetsManager:
    def __init__(self):
        self.credentials = self._get_credentials()
        
        # SpreadsheetのID
        self.barber_spreadsheet_id = os.getenv('BARBER_SPREADSHEET_ID')
        self.weather_spreadsheet_id = os.getenv('WEATHER_SPREADSHEET_ID')
        
        if not self.barber_spreadsheet_id or not self.weather_spreadsheet_id:
            raise ValueError("Spreadsheet IDs must be set in environment variables")
        
        # gspreadを優先使用
        if GSPREAD_AVAILABLE:
            self.gc = gspread.authorize(self.credentials)
            self.use_gspread = True
        else:
            self.service = build('sheets', 'v4', credentials=self.credentials)
            self.use_gspread = False
    
    def _get_credentials(self) -> Credentials:
        """Google Sheets API認証情報を取得"""
        # 環境変数からJSONを直接読み込む（GitHub Actions用）
        service_account_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
        if service_account_json:
            try:
                service_account_info = json.loads(service_account_json)
                # private_keyの改行文字を正規化
                if 'private_key' in service_account_info:
                    private_key = service_account_info['private_key']
                    # 改行文字がエスケープされている場合は置換
                    if '\\n' in private_key:
                        service_account_info['private_key'] = private_key.replace('\\n', '\n')
                    
                    # private_keyの形式をチェック
                    if not service_account_info['private_key'].startswith('-----BEGIN PRIVATE KEY-----'):
                        raise ValueError("private_key does not start with proper PEM header")
                
                # デバッグ：キーの存在確認
                required_keys = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email', 'client_id', 'auth_uri', 'token_uri']
                missing_keys = [key for key in required_keys if key not in service_account_info]
                if missing_keys:
                    raise ValueError(f"Missing required keys in service account JSON: {missing_keys}")
                
                return Credentials.from_service_account_info(
                    service_account_info,
                    scopes=['https://www.googleapis.com/auth/spreadsheets']
                )
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in GOOGLE_SERVICE_ACCOUNT_JSON: {e}")
            except Exception as e:
                raise ValueError(f"Error processing service account credentials: {e}")
        
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
        
        if self.use_gspread:
            self._append_barber_data_gspread(data)
        else:
            df = pd.DataFrame(data)
            self._append_data_to_sheet(
                self.barber_spreadsheet_id, 
                'barber_data',
                df,
                BARBER_DATA_HEADERS
            )
    
    def _append_barber_data_gspread(self, data: List[Dict[str, Any]]) -> None:
        """gspreadを使用して床屋データを追記"""
        try:
            sheet = self.gc.open_by_key(self.barber_spreadsheet_id)
            worksheet = sheet.worksheet('barber_data')
            
            # データをリスト形式に変換
            headers = BARBER_DATA_HEADERS
            rows = []
            for item in data:
                row = []
                for header in headers:
                    value = item.get(header, '')
                    if value is None:
                        value = ''
                    row.append(str(value))
                rows.append(row)
            
            # データを追記
            worksheet.append_rows(rows)
            print(f"Successfully appended {len(rows)} rows using gspread")
            
        except Exception as e:
            print(f"gspread append failed: {e}")
            # 既存のワークシートがない場合は作成を試みる
            try:
                sheet = self.gc.open_by_key(self.barber_spreadsheet_id)
                headers = BARBER_DATA_HEADERS
                worksheet = sheet.add_worksheet(title='barber_data', rows=1000, cols=len(headers))
                worksheet.append_row(headers)
                worksheet.append_rows(rows)
                print(f"Created new worksheet and appended {len(rows)} rows")
            except Exception as e2:
                raise Exception(f"Failed to create worksheet: {e2}")
    
    def append_weather_data(self, data: List[Dict[str, Any]]) -> None:
        """気象データをSpreadsheetに追記"""
        if not data:
            return
        
        if self.use_gspread:
            self._append_weather_data_gspread(data)
        else:
            df = pd.DataFrame(data)
            self._append_data_to_sheet(
                self.weather_spreadsheet_id,
                'weather_data', 
                df,
                WEATHER_DATA_HEADERS
            )
    
    def _append_weather_data_gspread(self, data: List[Dict[str, Any]]) -> None:
        """gspreadを使用して気象データを追記"""
        try:
            sheet = self.gc.open_by_key(self.weather_spreadsheet_id)
            worksheet = sheet.worksheet('weather_data')
            
            # データをリスト形式に変換
            headers = WEATHER_DATA_HEADERS
            rows = []
            for item in data:
                row = []
                for header in headers:
                    value = item.get(header, '')
                    if value is None:
                        value = ''
                    row.append(str(value))
                rows.append(row)
            
            # データを追記
            worksheet.append_rows(rows)
            print(f"Successfully appended {len(rows)} weather rows using gspread")
            
        except Exception as e:
            print(f"gspread weather append failed: {e}")
            # 既存のワークシートがない場合は作成を試みる
            try:
                sheet = self.gc.open_by_key(self.weather_spreadsheet_id)
                headers = WEATHER_DATA_HEADERS
                worksheet = sheet.add_worksheet(title='weather_data', rows=1000, cols=len(headers))
                worksheet.append_row(headers)
                worksheet.append_rows(rows)
                print(f"Created new weather worksheet and appended {len(rows)} rows")
            except Exception as e2:
                raise Exception(f"Failed to create weather worksheet: {e2}")
    
    def _append_data_to_sheet(self, spreadsheet_id: str, sheet_name: str, 
                            df: pd.DataFrame, expected_columns: List[str]) -> None:
        """データをシートに追記（ヘッダーがない場合は作成）"""
        # gspread使用時はこのメソッドは使わない
        if self.use_gspread:
            raise ValueError("This method should not be called when using gspread")
            
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
        # gspread使用時はこのメソッドは使わない
        if self.use_gspread:
            raise ValueError("This method should not be called when using gspread")
            
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
        try:
            self.service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"{sheet_name}!1:1",
                valueInputOption='RAW',
                body={'values': [header_columns]}
            ).execute()
            print(f"Created sheet '{sheet_name}' with headers")
        except Exception as e:
            print(f"Error adding headers to sheet '{sheet_name}': {e}")
            raise
    
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