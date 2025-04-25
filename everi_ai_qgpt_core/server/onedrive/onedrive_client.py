import msal
import requests
import io
import pandas as pd
import webbrowser



class OneDriveClient:
    def __init__(self):
        self.CLIENT_ID = "7126642c-5253-4fc7-8ba5-96ae765a4bd9"  # Replace with your actual client ID
        self.AUTHORITY = "https://login.microsoftonline.com/common"
        self.SCOPES = ["Files.Read"]
        self.access_token = None
 
    # Authenticate using device code flow
    def authenticate(self):
        app = msal.PublicClientApplication(self.CLIENT_ID, authority=self.AUTHORITY)
        flow = app.initiate_device_flow(scopes=self.SCOPES)
    
        if "user_code" not in flow:
            raise Exception("❌ Device code flow initiation failed:", flow)
    
        print("🔐 Visit the following URL and enter the code:")
        print(f"👉 {flow['verification_uri']}")
        print(f"🧾 Code: {flow['user_code']}")
        webbrowser.open(flow['verification_uri'])
    
        result = app.acquire_token_by_device_flow(flow)
    
        if "access_token" in result:
            self.access_token = result["access_token"]
            print("✅ Authentication successful")
            return result
        else:
            raise Exception("❌ Authentication failed:", result.get("error_description"))
    
    # Download a file as bytes (no saving to disk)
    def download_file(self,access_token, file_id):
        headers = {'Authorization': f'Bearer {access_token}'}
        download_url = f'https://graph.microsoft.com/v1.0/me/drive/items/{file_id}/content'
        response = requests.get(download_url, headers=headers)
    
        if response.status_code == 200:
            return io.BytesIO(response.content)
        else:
            raise Exception(f"❌ Failed to download file. Status code: {response.status_code}")
    
    # File preview helpers
    def preview_txt(self, file_bytes):
        return file_bytes.read().decode('utf-8', errors='ignore')[:1000] + "..."
    
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
