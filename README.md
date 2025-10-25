# IPATool WebUI Python

A feature-first web interface for interacting with the Apple App Store IPA files: search apps with configurable result limits (including tvOS), view versions and metadata, acquire free app licenses automatically, and download IPA files (including older and tvOS releases) with optional automatic license purchase. Supports Apple ID sign‑in with two‑factor authentication and exposes a REST API for programmatic use. Implemented as a clean, responsive frontend served by a Python Flask backend.

## Features

- **Authentication**: Sign in with your Apple ID (supports two-factor authentication)
- **App Search**: Search the App Store with customizable result limits including tvOS apps
- **License Management**: Acquire free app licenses automatically
- **Version Control**: List all available versions of an app
- **Metadata Access**: View version-specific metadata (display version, release date)
- **IPA Downloads**: Download IPA files with optional automatic license purchasing
- **Modern UI**: Clean, responsive interface for simple usage

<img width="2018" height="4448" alt="image" src="https://github.com/user-attachments/assets/ec40a529-51bb-4032-9ec5-6bce70532a71" />

<img width="1931" height="1145" alt="image" src="https://github.com/user-attachments/assets/362fdf7c-57df-435e-a386-78929d833e27" />

## Prerequisites

- Python 3.8 or higher
- An Apple ID account
- Internet connection

## Installation

1. **Clone or download this repository**

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Starting the Server

Run the Flask application:

```bash
python app.py
```

The web interface will be available at `http://127.0.0.1:5002`

### Authentication

1. Navigate to the web interface
2. Enter your Apple ID email and password
3. Click "Sign In"
4. If two-factor authentication is enabled, a modal will appear:
   - Enter the 6-digit verification code sent to your trusted device
   - Click "Verify"

### Searching for Apps

1. After signing in, the search section will appear
2. Enter a search term
3. Optionally adjust the results limit (1-50) and choose whether to search tvOS apps vs just iOS/iPadOS apps
4. Click "Search"

### Listing App Versions

1. Click on any app in search results, or use Direct Lookup to list versions to a specifc app id and optionally version id (to find related versions)
2. View the latest version and complete version list

### Viewing Version Metadata

1. Click on a version to expand its metadata

### Downloading IPAs

1. In the expanded metadata view, click Download IPA
2. It will first prepare (by downloading to the server cache), then pass that along to the browser to download

### Installing IPAs

- Use a tool like iMazing or 3uTools to "officially" install the ipa. You cannot and do not need to "sideload" these as that tries to sign them and these are already signed as they are from the app store. They can be installed and will not expire.
- Some people have also had success simply Airdropping it from a macOS computer and it will actually install it without any prompt, although I've had inconsistent results.
- Another user also mentioned Sideloadly with Advanced Options > Signing Mode > Normal Install.

## tvOS Notes

- In the UI we can only search for tvOS apps which doesn't give back the internal versionID needed for downloads or finding other versions
- To find that versionID, use iMazing to connect to your ATV, go to Manage Apps, right click or use option menu to Export to CSV, then use the StoreID as the App ID and the VersionID as the Version ID in this interface to both download and also find other tvOS versions
1. Make sure you have the current version of the app downloaded on your Apple TV.
2. Install **iMazing** on your Mac or PC
3. Follow iMazing’s steps for connecting your Mac/PC to the Apple TV.
4. In iMazing, go to **Tools → Manage Apps**.
5. Right‑click (or use the options menu) and select **Export List to CSV**.
6. Open the CSV file. For the app’s row:
   - **Store ID** = `AppID` for IPATool  
   - **Version ID** = `External Version ID` for IPATool
7. Use those values to do a Direct Lookup
8. Choose the version you want and download it

## Storage Locations

The application stores data in `~/.ipatool/`:
- `keychain.json` - Account credentials
- `cookies.lwp` - Session cookies
- `ca-bundle.pem` - Optional custom CA certificate

## API Endpoints

The application provides a REST API for programmatic access:

### Authentication
- `POST /api/auth/login` - Sign in with Apple ID
- `POST /api/auth/logout` - Sign out
- `GET /api/account` - Get current account info

### App Operations
- `GET /api/search` - Search for apps
- `POST /api/purchase` - Acquire app license
- `POST /api/download` - Download IPA file
- `GET /api/versions` - List app versions
- `GET /api/version-metadata` - Get version metadata

## Security Notes

- Credentials are stored locally in `~/.ipatool/keychain.json`
- Session cookies are persisted in `~/.ipatool/cookies.lwp`
- The application uses password tokens for App Store authentication
- Two-factor authentication is fully supported

## Optional Configuration

### SSL/TLS Verification

The application supports custom SSL certificates:

- **Disable SSL verification** (not recommended):
  ```bash
  export IPATOOL_SSL_NO_VERIFY=1
  ```

- **Use custom CA bundle**:
  ```bash
  export IPATOOL_CA_BUNDLE=/path/to/ca-bundle.pem
  ```

- **Default CA bundle location**:
  Place your certificate at `~/.ipatool/ca-bundle.pem`
  

## Troubleshooting

### "Password token expired" error
- Sign out and sign in again to refresh the authentication token

### "License required" error
- A popup will prompt you to aquire the license
- This only works for free apps, if it is a paid app you must buy the app first in the App Store with the same account, then you can see it on here.

### Two-factor authentication not working
- Ensure you're entering the code correctly (spaces are automatically removed)
- Try requesting a new code if the current one expires

### Download fails
- Check that you have sufficient disk space
- Verify the app is available in your account's storefront
- Ensure you have the necessary license for the app

## Architecture

- **Backend**: Flask (Python)
- **Frontend**: Vanilla JavaScript with modern CSS
- **Storage**: File-based keychain and cookie persistence
- **App Store Integration**: Custom Python implementation of IPATool protocol

## Acknowledgments

Based on the [IPATool by Majd](https://github.com/majd/ipatool) for interacting with the Apple App Store.
