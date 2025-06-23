import msal
import requests
import webbrowser
import urllib.parse

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OneDriveClient:
    def __init__(self, authority="https://login.microsoftonline.com/common"):
        """Initialize OneDriveClient with Azure app credentials."""
        self.client_id = "7126642c-5253-4fc7-8ba5-96ae765a4bd9"
        self.client_secret = "29072293-6d70-4935-9f59-8c4ee9515f77"
        self.redirect_uri = "http://localhost:8001"
        self.authority = authority
        self.scopes = ["Files.ReadWrite.All", "User.Read"]
        self.graph_api_endpoint = "https://graph.microsoft.com/v1.0"
        self.access_token = None 
        self.refresh_token = None
        self.app = msal.ConfidentialClientApplication(
            self.client_id,
            authority=self.authority,
            client_credential=self.client_secret
        )
    def authenticate(self):
        app = msal.PublicClientApplication(self.client_id, authority=self.authority)
        flow = app.initiate_device_flow(scopes=self.scopes)
    
        if "user_code" not in flow:
            raise Exception("❌ Device code flow initiation failed:", flow)
    
        print("🔐 Visit the following URL and enter the code:")
        print(f"👉 {flow['verification_uri']}")
        print(f"🧾 Code: {flow['user_code']}")
    
        result = app.acquire_token_by_device_flow(flow)
    
        if "access_token" in result:
            print()
            print("✅ Authentication successful")
            return result
        else:
            raise Exception("❌ Authentication failed:", result.get("error_description"))

    def list_files(self, folder_path="root"):
        """List files in the specified OneDrive folder (default: root)."""
        if not self.access_token:
            raise Exception("Not authenticated. Call authenticate() first.")

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        # Construct the endpoint for the folder
        endpoint = f"{self.graph_api_endpoint}/me/drive/root/children" if folder_path == "root" else f"{self.graph_api_endpoint}/me/drive/root:/{folder_path}:/children"
        
        response = requests.get(endpoint, headers=headers)

        if response.status_code == 200:
            files = response.json().get("value", [])
            for file in files:
                print(f"File: {file['name']} (ID: {file['id']})")
            return files
        else:
            raise Exception(f"Error: {response.status_code} - {response.text}")

    def refresh_access_token(self):
        """Refresh the access token using the refresh token."""
        if not self.refresh_token:
            raise Exception("No refresh token available. Authenticate first.")

        result = self.app.acquire_token_by_refresh_token(
            self.refresh_token,
            scopes=self.scopes
        )

        if "access_token" not in result:
            raise Exception(f"Token refresh failed: {result.get('error_description')}")

        self.access_token = result["access_token"]
        self.refresh_token = result.get("refresh_token", self.refresh_token)
        return self.access_token