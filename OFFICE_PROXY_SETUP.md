# Office Proxy Setup Guide

## 🔧 Fixed: OpenAI Client Proxy Issue

The error `Client.__init__() got an unexpected keyword argument 'proxies'` has been **fixed**! 

The newer OpenAI client (v1.12.0) doesn't support `proxies` in the constructor, but I've updated the code to handle office proxy environments properly.

## ✅ What's Fixed

1. **Updated `recommend.py`** - Now detects proxy environment and uses `httpx.Client` with proxy support
2. **Updated `book_detector.py`** - Book analysis now works with office proxies
3. **Updated test script** - Better proxy detection and error handling

## 🚀 How to Set Up for Office Environment

### Step 1: Check Your Current Proxy Settings

Run this command to see your current proxy settings:

```powershell
# Check current proxy settings
echo $env:HTTP_PROXY
echo $env:HTTPS_PROXY
```

### Step 2: Set Proxy Environment Variables (if needed)

If your office uses specific proxy settings, set them:

```powershell
# Set proxy environment variables
$env:HTTP_PROXY = "http://your-proxy-server:port"
$env:HTTPS_PROXY = "http://your-proxy-server:port"
```

### Step 3: Create .env File with API Key

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=sk-your-actual-api-key-here
```

### Step 4: Test the Setup

Run the updated test script:

```bash
python test_openai_setup.py
```

You should now see:
```
🔧 Detected proxy environment, testing with proxy support...
✅ OpenAI client initialized with proxy support
✅ OpenAI API connection successful!
```

## 🔍 Troubleshooting Office Network Issues

### Common Office Network Issues:

1. **Firewall blocking OpenAI API**
   - Contact IT to whitelist `api.openai.com`
   - Ports needed: 443 (HTTPS)

2. **Corporate proxy authentication**
   - May need username/password in proxy URL
   - Format: `http://username:password@proxy-server:port`

3. **SSL certificate issues**
   - Corporate firewalls often intercept SSL
   - May need to add corporate CA certificates

### Test Network Connectivity:

```bash
# Test if you can reach OpenAI API
curl -I https://api.openai.com/v1/models

# Or test with PowerShell
Invoke-WebRequest -Uri "https://api.openai.com/v1/models" -Method Head
```

## 🎯 Current Status

After the fix, your system will:

- ✅ **Auto-detect proxy environment**
- ✅ **Configure OpenAI client with proxy support**
- ✅ **Work with office network restrictions**
- ✅ **Provide detailed error messages** if issues persist

## 🚀 Next Steps

1. **Set your OpenAI API key** in `.env` file
2. **Restart the server**: `python run.py`
3. **Test the complete flow**:
   - Select genres
   - Upload book image
   - Get AI-powered recommendations

## 💡 Office-Specific Tips

- **Use company VPN** if required
- **Check with IT** about API access policies
- **Test during off-peak hours** if network is slow
- **Use fallback system** if OpenAI is blocked (still works!)

The system now handles office proxy environments automatically! 🎉
