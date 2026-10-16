# Bangla Page Maker

ওয়েব অ্যাপ: টেক্সট/ TXT → বাংলা-সমর্থিত ফন্টে JPG পৃষ্ঠা → ZIP download.

## ফোল্ডার কাঠামো

- `frontend/` — Netlify-তে ডেপ্লয়যোগ্য HTML/CSS/JS
- `backend/` — Render-এ ডেপ্লয়যোগ্য FastAPI + Pillow

## 1. বাংলা ফন্ট যোগ করা জরুরি

`backend/fonts/`-এ Unicode Bengali `.ttf` ফন্ট রাখো, ফাইলের নাম:
`NotoSansBengali-Regular.ttf`

একটি উপযুক্ত উৎস হলো Google Fonts-এর Noto Sans Bengali family:
https://fonts.google.com/noto/specimen/Noto+Sans+Bengali

ফন্টের লাইসেন্স/অ্যাট্রিবিউশন ফাইলও ডাউনলোড করে প্রোজেক্টে রাখো। ফন্ট ফাইল অন্তর্ভুক্ত না করলে Render-এর পরিবেশে বাংলা glyph ঠিকভাবে রেন্ডার নাও হতে পারে।

## 2. লোকালভাবে backend পরীক্ষা

Python 3.11+ প্রস্তাবিত।

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

তারপর `http://127.0.0.1:8000/health` খুলে `{"status":"ok"}` দেখো।

## 3. Frontend-কে backend-এর সঙ্গে যুক্ত করো

`frontend/config.js.example`-এর কপি `frontend/config.js` নামে তৈরি করো, তারপর:

```js
window.BPM_CONFIG = {
  API_BASE_URL: "https://YOUR-RENDER-SERVICE.onrender.com"
};
```

লোকাল পরীক্ষায় API_BASE_URL `http://127.0.0.1:8000` দিতে পারো। ব্রাউজারে HTML সরাসরি `file://` দিয়ে না খুলে একটি local static server ব্যবহার করো (যেমন `python -m http.server 5500` frontend ফোল্ডার থেকে)।

## 4. Render deploy

1. প্রোজেক্ট GitHub repository-তে push করো।
2. Render-এ New → Blueprint অথবা Python Web Service তৈরি করো।
3. Blueprint ব্যবহার করলে root-এর `render.yaml` নির্বাচন করো।
4. `FRONTEND_ORIGIN`-এ তোমার Netlify URL দাও, যেমন `https://your-app.netlify.app`।
5. ডেপ্লয় শেষে Render service URL কপি করো।

## 5. Netlify deploy

1. Render backend URL পাওয়ার পর `frontend/config.js.example`-কে `config.js` নামে কপি করে URL বসাও।
2. `frontend/` ফোল্ডারটি Netlify-তে deploy করো (বা GitHub repo-র base directory `frontend` নির্ধারণ করো)।
3. Netlify URL পাওয়ার পর Render-এর `FRONTEND_ORIGIN` environment variable-এ সেই URL বসিয়ে backend redeploy/restart করো।

> সতর্কতা: `config.js`-এ backend URL public হওয়া স্বাভাবিক; এতে কোনো secret/token রাখবে না।

## 6. ব্যবহার

- বড় লেখা textarea-তে paste করো অথবা TXT ফাইল drop করো।
- পৃষ্ঠা width/height, lines, font size ও JPG quality বেছে নাও।
- Generate চাপো; backend JPG তৈরি করে ZIP response ফেরত দেয়।
- ZIP ডাউনলোড করে extract করো; `0001.jpg`, `0002.jpg`… ক্রমানুসারে থাকবে।

## সীমাবদ্ধতা / পরবর্তী উন্নতি

- এই MVP-তে progress indicator ধাপে ধাপে UI আপডেট দেখায়; backend-এর ভেতরের প্রতিটি পৃষ্ঠার প্রকৃত progress stream করে না।
- API-তে text body সর্বোচ্চ 1,000,000 character। খুব বড় ফাইলের জন্য reverse proxy/request limit পরীক্ষা করা দরকার।
- Render free instance idle থাকলে প্রথম request ধীর হতে পারে।
- Request-এর জন্য authentication/rate limit যোগ করা হয়নি; public deployment-এ অপব্যবহার ঠেকাতে পরে rate limiting যোগ করো।
- Browser-এর বাংলা preview আনুমানিক; আসল layout backend-এর font metrics দিয়ে তৈরি হয়।
