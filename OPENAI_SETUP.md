# OpenAI API Setup Guide

## Why OpenAI Client is Not Available

The OpenAI client is not available because the API key is not configured. The system is currently using fallback recommendations instead of AI-powered ones.

## How to Fix This

### Step 1: Get Your OpenAI API Key

1. Go to [OpenAI Platform](https://platform.openai.com/api-keys)
2. Sign in or create an account
3. Click "Create new secret key"
4. Copy the API key (it starts with `sk-`)

### Step 2: Create Environment File

Create a file named `.env` in the project root directory with the following content:

```env
# OpenAI API Key (Required for book analysis and recommendations)
OPENAI_API_KEY=sk-your-actual-api-key-here

# Optional: Goodreads API Key
GOODREADS_API_KEY=your_goodreads_api_key_here

# Model Configuration
MODEL_PATH=models/yolo_weights/best.pt
```

### Step 3: Replace the Placeholder

Replace `sk-your-actual-api-key-here` with your actual OpenAI API key.

### Step 4: Restart the Server

After creating the `.env` file, restart the server:

```bash
# Stop the current server (Ctrl+C)
# Then restart it
python run.py
```

## Verification

Once configured, you should see this message when the server starts:
```
✅ OpenAI client initialized for recommendations
```

Instead of:
```
⚠️ OpenAI API key not set - will use fallback recommendations
```

## Current Status

- ✅ **Book Detection**: Working (uses OpenAI Vision API)
- ⚠️ **Recommendations**: Using fallback system (needs OpenAI API key)
- ✅ **Frontend**: Fully functional
- ✅ **Filtering**: Working with fallback data

## Benefits of OpenAI Integration

With the API key configured, you'll get:
- **AI-powered book recommendations** based on your preferences
- **Intelligent exclusion** of books you already have
- **Personalized suggestions** with detailed reasoning
- **Better genre matching** and book discovery

## Troubleshooting

If you still see issues after setting up the API key:

1. **Check file location**: Make sure `.env` is in the project root
2. **Check API key format**: Should start with `sk-`
3. **Check API key validity**: Test it at https://platform.openai.com/api-keys
4. **Restart server**: Always restart after changing environment variables
5. **Check console output**: Look for initialization messages

## Cost Information

OpenAI API usage costs:
- **GPT-4o-mini**: ~$0.00015 per 1K tokens (very affordable)
- **Vision API**: ~$0.0001 per image (for book analysis)
- **Typical cost**: Less than $0.01 per recommendation session
