# OAuth & SendGrid Configuration

> VentureStrat Outreach Service — Email Provider Setup

## 1. Google OAuth (Gmail Integration)

### Redirect URIs

| Environment | Redirect URI |
|-------------|-------------|
| Development | `http://localhost:8061/api/v1/email-accounts/oauth/google/callback` |
| Production  | `https://{DOMAIN}/api/v1/email-accounts/oauth/google/callback` |

### Required Scopes

- `https://www.googleapis.com/auth/gmail.send` — Send emails on behalf of user
- `https://www.googleapis.com/auth/gmail.readonly` — Read emails for reply detection
- `https://www.googleapis.com/auth/gmail.modify` — Mark emails as read, manage labels

### Google Cloud Console Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select or create a project for VentureStrat
3. Navigate to **APIs & Services > OAuth consent screen**
   - Choose **External** user type
   - Fill in app name: `VentureStrat`
   - Add authorized domains: your production domain
   - Add the three Gmail scopes listed above
   - Add test users during development
4. Navigate to **APIs & Services > Credentials**
   - Click **Create Credentials > OAuth 2.0 Client ID**
   - Application type: **Web application**
   - Name: `VentureStrat Outreach`
   - Authorized redirect URIs: add both dev and production URIs above
   - Click **Create**
5. Copy the **Client ID** and **Client Secret**
6. Set environment variables:
   ```
   GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your-client-secret
   ```
7. Enable the Gmail API:
   - Navigate to **APIs & Services > Library**
   - Search for "Gmail API"
   - Click **Enable**

### Verification Notes

- Apps requesting sensitive Gmail scopes require Google verification
- During development, add test users under OAuth consent screen
- For production, submit for verification with a privacy policy URL
- Verification typically takes 2-4 weeks

---

## 2. Microsoft OAuth (Outlook Integration)

### Redirect URIs

| Environment | Redirect URI |
|-------------|-------------|
| Development | `http://localhost:8061/api/v1/email-accounts/oauth/microsoft/callback` |
| Production  | `https://{DOMAIN}/api/v1/email-accounts/oauth/microsoft/callback` |

### Required Microsoft Graph Scopes

- `Mail.Send` — Send emails
- `Mail.Read` — Read emails for reply detection
- `Mail.ReadWrite` — Manage emails (mark read, move)
- `offline_access` — Refresh tokens for background operations
- `User.Read` — Basic profile info

### Azure AD Setup

1. Go to [Azure Portal](https://portal.azure.com/)
2. Navigate to **Azure Active Directory > App registrations**
3. Click **New registration**
   - Name: `VentureStrat Outreach`
   - Supported account types: **Accounts in any organizational directory and personal Microsoft accounts**
   - Redirect URI: select **Web**, enter the dev URI above
4. After creation, note the **Application (client) ID**
5. Navigate to **Certificates & secrets**
   - Click **New client secret**
   - Copy the secret value immediately (shown only once)
6. Navigate to **API permissions**
   - Click **Add a permission > Microsoft Graph > Delegated permissions**
   - Add: `Mail.Send`, `Mail.Read`, `Mail.ReadWrite`, `offline_access`, `User.Read`
   - Click **Grant admin consent** (if you have admin rights)
7. Navigate to **Authentication**
   - Add the production redirect URI
   - Under **Implicit grant and hybrid flows**, leave unchecked (we use authorization code flow)
8. Set environment variables:
   ```
   MICROSOFT_CLIENT_ID=your-application-client-id
   MICROSOFT_CLIENT_SECRET=your-client-secret
   MICROSOFT_TENANT_ID=common
   ```

### Notes

- Use `tenant_id=common` for multi-tenant (personal + work accounts)
- Use `tenant_id=organizations` for work/school accounts only
- Microsoft token refresh works via `offline_access` scope

---

## 3. SendGrid Configuration

### Domain Authentication

1. Go to [SendGrid Dashboard](https://app.sendgrid.com/)
2. Navigate to **Settings > Sender Authentication > Authenticate Your Domain**
3. Select your DNS host
4. Enter your sending domain (e.g., `mail.venturestrat.com`)
5. SendGrid provides DNS records to add:
   - 3 CNAME records for domain authentication
   - 1 CNAME record for link branding (optional)
6. Add the records to your DNS provider
7. Click **Verify** in SendGrid dashboard
8. Wait for DNS propagation (can take up to 48 hours)

### Sender Verification

- If not using domain authentication, verify individual sender addresses
- Go to **Settings > Sender Authentication > Single Sender Verification**
- Add and verify the email address used for outreach

### API Key Setup

1. Navigate to **Settings > API Keys**
2. Click **Create API Key**
   - Name: `VentureStrat Production` (or `VentureStrat Dev`)
   - Permissions: **Restricted Access**
     - Mail Send: **Full Access**
     - (Optional) Stats: **Read Access**
3. Copy the API key (shown only once)
4. Set environment variable:
   ```
   SENDGRID_API_KEY=SG.your-api-key-here
   ```

### Environment Variables Summary

```
SENDGRID_API_KEY=SG.your-api-key
SENDGRID_FROM_EMAIL=outreach@venturestrat.com
SENDGRID_FROM_NAME=VentureStrat
```

### Rate Limits

- Free tier: 100 emails/day
- Essentials: 100K emails/month
- Pro: 1.5M emails/month
- Choose a plan based on expected outreach volume

---

## Environment Variables Checklist

```bash
# Google OAuth
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

# Microsoft OAuth
MICROSOFT_CLIENT_ID=
MICROSOFT_CLIENT_SECRET=
MICROSOFT_TENANT_ID=common

# SendGrid
SENDGRID_API_KEY=
SENDGRID_FROM_EMAIL=
SENDGRID_FROM_NAME=VentureStrat
```

Add these to the outreach-service `.env` file or Docker Compose environment section.
