# Deployment Guide - Bajaj Finserv API

## Quick Recommendation

For your hackathon submission, I recommend **Render** because:
- ✅ Free tier available (no credit card required)
- ✅ Easy GitHub integration
- ✅ Supports system dependencies (Tesseract, Poppler)
- ✅ Provides HTTPS out of the box
- ✅ Your webhook URL will be: `https://your-app-name.onrender.com/extract-bill-data`

## Option 1: Deploy to Render (Recommended) ⭐

### Steps:

1. **Push your code to GitHub**
   ```bash
   cd d:/PROJECTS/Devanand_Bajaj_Finserv
   git init
   git add .
   git commit -m "Initial commit - Medical bill extraction API"
   # Create a new repo on GitHub, then:
   git remote add origin https://github.com/YOUR_USERNAME/bajaj-finserv-api.git
   git push -u origin main
   ```

2. **Sign up for Render**
   - Go to https://render.com
   - Sign up with your GitHub account (free)

3. **Create a New Web Service**
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Select the `bajaj-finserv-api` repository

4. **Configure the service**
   - **Name**: `bajaj-extraction-api` (or any name you prefer)
   - **Environment**: `Python 3`
   - **Build Command**: 
     ```bash
     apt-get update && apt-get install -y tesseract-ocr poppler-utils && pip install -r requirements.txt
     ```
   - **Start Command**: 
     ```bash
     uvicorn app:app --host 0.0.0.0 --port $PORT
     ```
   - **Plan**: Free

5. **Deploy**
   - Click "Create Web Service"
   - Wait 5-10 minutes for deployment
   - Your URL will be: `https://bajaj-extraction-api.onrender.com`

6. **Test your webhook**
   ```bash
   curl -X POST https://bajaj-extraction-api.onrender.com/extract-bill-data \
     -H "Content-Type: application/json" \
     -d '{"document": "https://example.com/bill.pdf"}'
   ```

7. **Submit this URL**: `https://bajaj-extraction-api.onrender.com/extract-bill-data`

---

## Option 2: Railway (Alternative)

### Steps:

1. **Install Railway CLI**
   ```bash
   npm install -g @railway/cli
   ```

2. **Login and Deploy**
   ```bash
   cd d:/PROJECTS/Devanand_Bajaj_Finserv
   railway login
   railway init
   railway up
   ```

3. **Get your URL**
   ```bash
   railway domain
   ```

4. **Submit**: `https://your-app.up.railway.app/extract-bill-data`

---

## Option 3: Ngrok (For Quick Testing)

**Use this ONLY for testing or if deployment services are down**

### Steps:

1. **Download and Install ngrok**
   - Go to https://ngrok.com/download
   - Sign up for free account
   - Download Windows version
   - Extract to a folder

2. **Get your auth token**
   - Copy from https://dashboard.ngrok.com/get-started/your-authtoken
   - Run: `ngrok authtoken YOUR_TOKEN`

3. **Start your local API**
   ```bash
   cd d:/PROJECTS/Devanand_Bajaj_Finserv
   python -m uvicorn app:app --host 0.0.0.0 --port 8000
   ```

4. **In another terminal, start ngrok**
   ```bash
   ngrok http 8000
   ```

5. **Copy the HTTPS URL**
   - You'll see something like: `https://abc123.ngrok.io`
   - Your webhook URL: `https://abc123.ngrok.io/extract-bill-data`

⚠️ **Important**: 
- Keep both terminals running during evaluation
- The URL changes every time you restart ngrok
- Free tier has session limits (2 hours)

---

## Option 4: Google Cloud Run (For Production)

### Steps:

1. **Install Google Cloud SDK**
   - Download from: https://cloud.google.com/sdk/docs/install

2. **Build and Deploy**
   ```bash
   cd d:/PROJECTS/Devanand_Bajaj_Finserv
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   
   gcloud run deploy bajaj-extraction-api \
     --source . \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated
   ```

3. **Get your URL**
   - It will output something like: `https://bajaj-extraction-api-xxx.run.app`

4. **Submit**: `https://bajaj-extraction-api-xxx.run.app/extract-bill-data`

---

## Troubleshooting

### Issue: "Tesseract not found"
**Solution**: Make sure the build command includes:
```bash
apt-get install -y tesseract-ocr
```

### Issue: "PDF conversion failed"
**Solution**: Make sure the build command includes:
```bash
apt-get install -y poppler-utils
```

### Issue: "Port already in use"
**Solution**: 
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### Issue: "Module not found"
**Solution**: Ensure all files are committed to Git:
```bash
git status
git add bajaj_pipeline/
git commit -m "Add pipeline modules"
git push
```

---

## Testing Your Deployed API

Once deployed, test with:

```bash
# Test health endpoint
curl https://your-app-url.com/health

# Test extraction
curl -X POST https://your-app-url.com/extract-bill-data \
  -H "Content-Type: application/json" \
  -d '{"document": "https://hackrx.blob.core.windows.net/assets/datathon-IIT/sample_2.png"}'
```

---

## Final Checklist

- [ ] Code pushed to GitHub
- [ ] Service deployed successfully
- [ ] `/health` endpoint returns 200 OK
- [ ] `/extract-bill-data` endpoint tested with sample document
- [ ] Webhook URL submitted to competition
- [ ] README.md is complete and clear
- [ ] Repository is public (for submission)

Good luck! 🚀
