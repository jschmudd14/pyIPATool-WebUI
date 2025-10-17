# IPATool WebUI Python

A modern web interface for IPATool, built with Flask and Python. This application provides a user-friendly way to interact with the Apple App Store, allowing you to search for apps, purchase licenses, and download IPA files.

## Features

- **Authentication**: Sign in with your Apple ID (supports two-factor authentication)
- **App Search**: Search the App Store with customizable result limits including tvOS apps
- **License Management**: Acquire free app licenses automatically
- **Version Control**: List all available versions of an app
- **Metadata Access**: View version-specific metadata (display version, release date)
- **IPA Downloads**: Download IPA files with optional automatic license purchasing
- **Modern UI**: Clean, responsive interface with dark mode support

  <img width="2749" height="6308" alt="image" src="https://github.com/user-attachments/assets/434b3bbf-21ba-42fc-a6f9-e65781ec8798" />


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

The web interface will be available at `http://127.0.0.1:5000`

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
5. Results will display: Name, Bundle ID, Version, Price, and App ID

### Purchasing Licenses

1. Enter either:
   - **App ID** (numeric identifier from search results)
   - **Bundle Identifier** (e.g., `com.example.app`)
2. Click "Acquire License"
3. Note: Only free apps can be purchased

### Listing App Versions

1. Enter either App ID or Bundle Identifier
2. Optionally enter an External Version ID to filter related versions
3. Click "Fetch Versions"
4. View the latest version and complete version list

### Viewing Version Metadata

1. Enter App ID or Bundle Identifier
2. Enter the External Version ID (obtained from version listing)
3. Click "Fetch Metadata"
4. View display version and release date

### Downloading IPAs

1. Enter App ID or Bundle Identifier
2. Optionally specify:
   - External Version ID (defaults to latest)
   - Output path (defaults to current directory)
   - Enable "Purchase license automatically if required"
3. Click "Download"
4. IPA saves to device (not through browser)

## Configuration

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

### Storage Locations

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

## Troubleshooting

### "Password token expired" error
- Sign out and sign in again to refresh the authentication token

### "License required" error
- Enable "Purchase license automatically if required" when downloading
- Or manually acquire the license first using the Purchase section

### Two-factor authentication not working
- Ensure you're entering the code correctly (spaces are automatically removed)
- Try requesting a new code if the current one expires

### Download fails
- Check that you have sufficient disk space
- Verify the app is available in your account's storefront
- Ensure you have the necessary license for the app

## tvOS Notes

- In the UI we can only search for tvOS apps which doesn't give back the internal versionID needed for downloads or finding other versions
- To find that versionID, use iMazing to connect to your ATV, go to Manage Apps, right click or use option menu to Export to CSV, then use the StoreID as the App ID and the VersionID as the Version ID in this interface to both download and also find other tvOS versions

## Architecture

- **Backend**: Flask (Python)
- **Frontend**: Vanilla JavaScript with modern CSS
- **Storage**: File-based keychain and cookie persistence
- **App Store Integration**: Custom Python implementation of IPATool protocol

## Acknowledgments

Based on the [IPATool by Majd](https://github.com/majd/ipatool) for interacting with the Apple App Store.
