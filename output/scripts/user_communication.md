# User Communication — Migration Notice

> Email template and FAQ for notifying existing users about the VentureStrat platform migration.

---

## Email Template

**Subject:** VentureStrat Platform Upgrade — Action Required

---

Hi {first_name},

We have upgraded VentureStrat to a new platform architecture that brings significant performance improvements, better reliability, and new features.

**What changed:**

- Faster investor search (sub-500ms, even at scale)
- Improved email delivery and tracking
- New CRM pipeline with drag-and-drop stages
- Better subscription and billing management

**What you need to do:**

Your data (investors, shortlists, messages, subscription) has been migrated automatically. However, you will need to **re-authorize your email connection** so VentureStrat can continue sending emails on your behalf.

### Re-authorize Gmail

1. Log in to VentureStrat at {app_url}
2. Go to **Settings > Email Accounts**
3. Click **Reconnect** next to your Gmail account
4. You will be redirected to Google — click **Allow**
5. You will be redirected back to VentureStrat — done

### Re-authorize Outlook

1. Log in to VentureStrat at {app_url}
2. Go to **Settings > Email Accounts**
3. Click **Reconnect** next to your Outlook account
4. You will be redirected to Microsoft — click **Accept**
5. You will be redirected back to VentureStrat — done

**Why is re-authorization needed?**

The upgrade moved our email integration to a new, more secure OAuth application. Your previous authorization tokens are tied to the old application and cannot be transferred. Re-authorizing takes less than 30 seconds and only needs to be done once.

If you have any questions, reply to this email or reach out at {support_email}.

Best,
The VentureStrat Team

---

## FAQ

### Will I lose any data?

No. All your data has been migrated: investor profiles, email addresses, shortlists, pipeline stages, tags, messages, email templates, and your subscription. Row counts have been verified for every table.

### What changes will I notice?

- The URL remains the same
- The UI has been refreshed with a new design system
- Investor search is significantly faster
- The CRM pipeline has a new visual board view
- Email scheduling and threading are more reliable

### Is there any downtime?

We are performing the migration during a maintenance window. You will be notified of the exact time. Expected downtime is under 30 minutes.

### Do I need to update my password?

No. Your login credentials remain the same. If you use SSO (Google/Microsoft sign-in), that continues to work as before.

### What about my Stripe subscription?

Your subscription, billing period, and payment method have been migrated. No action is needed on billing. Your next invoice will process normally.

### What about scheduled emails?

Any emails that were scheduled before the migration will be re-queued on the new platform. There may be a slight delay (up to 1 hour) for emails scheduled during the maintenance window.

### What if re-authorization fails?

1. Clear your browser cookies for accounts.google.com (or login.microsoftonline.com)
2. Try the re-authorization flow again
3. If the issue persists, contact {support_email}

### Who do I contact for help?

Reply to this email or reach out at {support_email}. We are monitoring closely during the migration period and will respond within 1 hour.
