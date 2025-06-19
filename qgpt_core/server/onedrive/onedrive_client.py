import msal
import requests
import io
import pandas as pd
import webbrowser
import json
import os
from qgpt_core.constants import PROJECT_ROOT_PATH


class OneDriveClient:    # def __init__(self, token_file="/home/srikar/QGPT_BE/QGPT/qgpt_core/tokenFolder/tokens.json"):
    def __init__(self, token_file = PROJECT_ROOT_PATH / "qgpt_core" / "tokenFolder" / "tokens.json"):
        self.CLIENT_ID = "7126642c-5253-4fc7-8ba5-96ae765a4bd9"  # Replace with your actual client ID
        self.AUTHORITY = "https://login.microsoftonline.com/common"
        self.SCOPES = ["Files.Read"]  # Added offline_access for refresh tokens
        self.access_token = None
        self.refresh_token = None
        self.token_file = token_file
        self.app = msal.PublicClientApplication(self.CLIENT_ID, authority=self.AUTHORITY)

    # Load tokens from file
    def _load_tokens(self):
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, "r") as f:
                    tokens = json.load(f)
                    return tokens.get("refresh_token")
            except Exception as e:
                print(f"⚠️ Error loading tokens: {e}")
        return None

    # Save tokens to file
    def _save_tokens(self):
        tokens = {"refresh_token": self.refresh_token}
        try:
            with open(self.token_file, "w") as f:
                json.dump(tokens, f)
            print(f"💾 Tokens saved to {self.token_file}")
        except Exception as e:
            print(f"⚠️ Error saving tokens: {e}")

    # Authenticate using device code flow
    def authenticate(self):
        try:
            flow = self.app.initiate_device_flow(scopes=self.SCOPES)
            
            if "user_code" not in flow:
                raise Exception(f"❌ Device code flow initiation failed: {flow}")
            
            print("🔐 Visit the following URL and enter the code:")
            print(f"👉 {flow['verification_uri']}")
            print(f"🧾 Code: {flow['user_code']}")
            webbrowser.open(flow['verification_uri'])
            
            result = self.app.acquire_token_by_device_flow(flow)
            
            if "access_token" in result:
                self.access_token = result["access_token"]
                self.refresh_token = result.get("refresh_token")  # Store refresh token
                print("✅ Authentication successful")
                print(f"Access Token: {self.access_token}")
                if self.refresh_token:
                    print(f"Refresh Token: {self.refresh_token}")
                    self._save_tokens()  # Save tokens to file
                return result
            else:
                raise Exception(f"❌ Authentication failed: {result.get('error_description')}")
        
        except Exception as e:
            print(f"Error: {e}")
            raise

    # Refresh access token using refresh token
    def refresh_access_token(self):
        if not self.refresh_token:
            raise Exception("❌ No refresh token available. Please authenticate first.")
        
        try:
            result = self.app.acquire_token_by_refresh_token(
                refresh_token=self.refresh_token,
                scopes=self.SCOPES  # Include offline_access to get a new refresh token
            )
            
            if "access_token" in result:
                self.access_token = result["access_token"]
                self.refresh_token = result.get("refresh_token", self.refresh_token)  # Update refresh token if provided
                print("✅ Access token refreshed successfully")
                print(f"New Access Token: {self.access_token}")
                if result.get("refresh_token"):
                    print(f"New Refresh Token: {self.refresh_token}")
                    self._save_tokens()  # Save new refresh token
                return result
            else:
                raise Exception(f"❌ Token refresh failed: {result.get('error_description')}")
        
        except Exception as e:
            print(f"Error: {e}")
            raise

    # Initialize authentication (try refresh token first, then authenticate if needed)
    def initialize(self):
        try:
            # Try loading refresh token from file
            self.refresh_token = self._load_tokens()
            if self.refresh_token:
                print("🔄 Attempting to refresh access token from stored refresh token...")
                result = self.refresh_access_token()
                return result
            else:
                print("ℹ️ No stored refresh token found. Initiating device code flow...")
                return self.authenticate()
        except Exception as e:
            print(f"⚠️ Refresh failed: {e}. Initiating device code flow...")
            return self.authenticate()
    
    # Download a file as bytes (no saving to disk)
    def download_file(self,access_token, file_id):
        print("359")
        headers = {'Authorization': f'Bearer {access_token}'}
        download_url = f'https://graph.microsoft.com/v1.0/me/drive/items/{file_id}/content'
        response = requests.get(download_url, headers=headers)
        print("362")
        print("363")
        if response.status_code == 200:
            return io.BytesIO(response.content)
        else:
            raise Exception(f"❌ Failed to download file. Status code: {response.status_code}")
    
    # # File preview helpers
    # def preview_txt(self, file_bytes):
    #     return file_bytes.read().decode('utf-8', errors='ignore')[:1000] + "..."
    def preview_txt(self, file_bytes):
        # Read only the first 1000 bytes for the preview
        preview_content = file_bytes.getvalue()[:1000].decode('utf-8', errors='ignore')
        return preview_content + "..."
    
    def preview_pdf(self,file_bytes):
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            text = ''.join([page.get_text() for page in doc])
            return text[:1000] + "..." if text else "[PDF is empty or non-textual]"
        except Exception as e:
            return f"[Error reading PDF: {e}]"
    
    def preview_csv(fself,ile_bytes):
        try:
            df = pd.read_csv(file_bytes)
            return df.head().to_string()
        except Exception as e:
            return f"[Error reading CSV: {e}]"
    
    def preview_excel(self,file_bytes):
        try:
            df = pd.read_excel(file_bytes)
            return df.head().to_string()
        except Exception as e:
            return f"[Error reading Excel: {e}]"
    
    # Smart handler to preview based on file extension
    def preview_file(self,file_bytes, file_name):
        ext = file_name.split('.')[-1].lower()
    
        if ext == 'txt':
            return self.preview_txt(file_bytes)
        elif ext == 'pdf':
            return self.preview_pdf(file_bytes)
        elif ext == 'csv':
            return self.preview_csv(file_bytes)
        elif ext in ['xls', 'xlsx']:
            return self.preview_excel(file_bytes)
        else:
            return f"⚠️ Unsupported file type: .{ext}"
    
    # Recursively list and preview files in OneDrive
    def list_and_preview_files(self, token, parent_id='root'):
        headers = {'Authorization': f'Bearer {token["access_token"]}'}
        url = f'https://graph.microsoft.com/v1.0/me/drive/items/{parent_id}/children'
        response = requests.get(url, headers=headers)
    
        if response.status_code != 200:
            raise Exception(f"❌ Error fetching files: {response.status_code}")
    
        items = response.json().get('value', [])
        if not items:
            print("📂 No items found.")
            return
        return items
    
        # for item in items:
        #     item_name = item.get('name')
        #     item_id = item.get('id')
        #     is_folder = 'folder' in item  # Recursively list contents of this folder
        #     print(f"\n🔹 File: {item_name} (ID: {item_id})")
        #     try:
        #         file_content = download_file(token['access_token'], item_id)
        #         preview = preview_file(file_content, item_name)
        #         print(f"📄 Preview:\n{preview}\n")
        #     except Exception as e:
        #         print(f"❌ Could not preview file {item_name}: {e}")
