# Gmail OTP Setup Guide

## How to Get Real OTP Emails on Your Gmail

### Step 1: Generate Gmail App Password

1. Go to: **https://myaccount.google.com/apppasswords**
   - ⚠️ You must have **2-Factor Authentication** enabled first
   - If not enabled, enable it first: https://myaccount.google.com/security

2. Select:
   - **App**: Mail
   - **Device**: Windows Computer (or your device)

3. Google will generate a **16-character password** (looks like: `abcd efgh ijkl mnop`)
   - Copy this password (without spaces)

### Step 2: Update `.env` File

Edit the `.env` file in your project root:

```
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your_actual_email@gmail.com
EMAIL_HOST_PASSWORD=abcdefghijklmnop
EMAIL_USE_TLS=True
```

**Replace:**
- `your_actual_email@gmail.com` → Your actual Gmail address
- `abcdefghijklmnop` → The 16-character app password (without spaces)

### Step 3: Install python-dotenv

```powershell
pip install python-dotenv
```

### Step 4: Restart Django Server

```powershell
python manage.py runserver
```

### Step 5: Test Signup Flow

1. Go to: http://127.0.0.1:8000/signup/
2. Fill in the form with your actual Gmail address
3. Click "Sign Up"
4. **Check your Gmail inbox** - OTP email will arrive in 1-2 seconds
5. Copy the 6-digit OTP from email
6. Paste into the verification page
7. Account created! ✅

---

## Troubleshooting

### ❌ "SMTP authentication failed"
- Make sure you used the **16-character app password** (not your regular password)
- Make sure 2-Factor Authentication is enabled on your Gmail account

### ❌ "Email not received"
- Check **Spam/Promotions** folder in Gmail
- Make sure EMAIL_HOST_USER matches the Gmail address where you generated the app password

### ❌ Can't find apppasswords page
- Make sure 2-Factor Authentication is enabled:
  - Go to: https://myaccount.google.com/security
  - Enable 2-Step Verification first

### ✅ If email arrives but OTP expires
- OTP is valid for **10 minutes** from generation
- Click "Resend OTP" if needed

---

## For Production

When deploying to production (Heroku, AWS, etc.):

Set these environment variables in your hosting platform:
- `EMAIL_HOST` = `smtp.gmail.com`
- `EMAIL_PORT` = `587`
- `EMAIL_HOST_USER` = your Gmail
- `EMAIL_HOST_PASSWORD` = your app password
- `EMAIL_USE_TLS` = `True`

The code will automatically use SMTP backend when these are set.
