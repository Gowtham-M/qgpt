import requests
import webbrowser
import urllib.parse
import json
import os

# Configuration
CLIENT_ID = "your_client_id"  # Replace with your Azure App Client ID
REDIRECT_URI = "http://localhost:8080/"
SCOPES = ["Files.ReadWrite.All", "offline_access"]
AUTHORITY_URL = "https://login.microsoftonline.com/common/oauth2/v2.0"
TOKEN_URL = f"{AUTHORITY_URL}/token"

def get_auth_code():
    # Construct the authorization URL
    auth_url = (
        f"{AUTHORITY_URL}/authorize?"
        f"client_id={CLIENT_ID}&"
        f"scope={' '.join(SCOPES)}&"
        f"response_type=code&"
        f"redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
    )
    
    print("Opening browser for authentication...")
    webbrowser.open(auth_url)
    
    # Prompt user to paste the redirected URL
    redirected_url = input("Paste the full redirected URL here: ")
    
    # Extract the code from the URL
    code = redirected_url.split("code=")[1].split("&")[0]
    return code

def get_access_token(code):
    # Prepare token request
    token_params = {
        "client_id": CLIENT_ID,
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
        "scope": " ".join(SCOPES)
    }
    
    # Request access token
    response = requests.post(TOKEN_URL, data=token_params)
    response_data = response.json()
    
    if "access_token" in response_data:
        return response_data["access_token"], response_data.get("refresh_token")
    else:
        raise Exception(f"Error getting token: {response_data.get('error_description')}")

def refresh_access_token(refresh_token):
    # Prepare refresh token request
    token_params = {
        "client_id": CLIENT_ID,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
        "scope": " ".join(SCOPES)
    }
    
    # Request new access token
    response = requests.post(TOKEN_URL, data=token_params)
    response_data = response.json()
    
    if "access_token" in response_data:
        return response_data["access_token"], response_data.get("refresh_token")
    else:
        raise Exception(f"Error refreshing token: {response_data.get('error_description')}")

def list_files(access_token):
    # List files in OneDrive root
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get("https://graph.microsoft.com/v1.0/me/drive/root/children", headers=headers)
    
    if response.status_code == 200:
        files = response.json().get("value", [])
        for item in files:
            print(f"Name: {item['name']}, ID: {item['id']}")
    else:
        print(f"Error listing files: {response.json().get('error')}")

def upload_file(access_token, local_path, onedrive_path):
    # Upload a file to OneDrive
    headers = {"Authorization": f"Bearer {access_token}"}
    upload_url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{onedrive_path}:/content"
    
    with open(local_path, "rb") as file:
        response = requests.put(upload_url, headers=headers, data=file)
    
    if response.status_code in [200, 201]:
        print(f"File uploaded successfully to {onedrive_path}")
    else:
        print(f"Error uploading file: {response.json().get('error')}")

def main():
    # Step 1: Authenticate and get tokens
    code = get_auth_code()
    access_token, refresh_token = get_access_token(code)
    
    # Save refresh token for future use
    with open("refresh_token.txt", "w") as f:
        f.write(refresh_token)
    
    # Step 2: List files
    print("Listing files in OneDrive root:")
    list_files(access_token)
    
    # Step 3: Example upload (uncomment to use)
    # local_file = "example.txt"
    # onedrive_path = "Documents/example.txt"
    # upload_file(access_token, local_file, onedrive_path)

if __name__ == "__main__":
    main()