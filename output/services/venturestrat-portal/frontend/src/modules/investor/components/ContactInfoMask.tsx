import React from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Stack from '@mui/material/Stack';
import { useNavigate } from 'react-router-dom';
import { Mail, Globe, Linkedin, Twitter, Lock } from 'lucide-react';

// Paid plans that receive full contact info
const PAID_PLAN_CODES = new Set(['starter', 'pro', 'scale']);

// Mask helpers -----------------------------------------------------------------

function maskEmail(email: string): string {
  const atIdx = email.indexOf('@');
  if (atIdx <= 0) return '***@***.com';
  const local = email.slice(0, atIdx);
  const domain = email.slice(atIdx); // includes '@'
  const visible = local.slice(0, Math.min(2, local.length));
  return `${visible}${'*'.repeat(Math.max(3, local.length - visible.length))}${domain}`;
}

function maskPhone(phone: string): string {
  // Keep first 3 chars and last 4 digits, mask the rest
  const digits = phone.replace(/\D/g, '');
  if (digits.length < 7) return '+* ***-***-****';
  const last4 = digits.slice(-4);
  const countryLen = digits.length > 10 ? digits.length - 10 : 0;
  const countryPart = countryLen > 0 ? `+${digits.slice(0, countryLen)} ` : '';
  return `${countryPart}***-***-${last4}`;
}

// Component -------------------------------------------------------------------

interface ContactInfoMaskProps {
  emails: Array<{ id: string; email: string; status: string }>;
  socialLinks: Record<string, any> | null;
  website: string | null;
  phone: string | null;
  hasSubscription: boolean;
  /** Plan code (free/starter/pro/scale). When absent, treated as free. */
  planCode?: string | null;
}

const ContactInfoMask: React.FC<ContactInfoMaskProps> = ({
  emails,
  socialLinks,
  website,
  phone,
  hasSubscription,
  planCode,
}) => {
  const navigate = useNavigate();

  const isPaidPlan =
    hasSubscription &&
    planCode != null &&
    PAID_PLAN_CODES.has(planCode.toLowerCase());

  // Free / no subscription: full overlay with blur -------------------------
  if (!hasSubscription) {
    return (
      <Box
        sx={{
          position: 'relative',
          p: 2,
          borderRadius: 2,
          bgcolor: 'rgba(79, 195, 247, 0.04)',
          border: '1px solid rgba(79, 195, 247, 0.1)',
        }}
      >
        <Box
          sx={{
            filter: 'blur(5px)',
            userSelect: 'none',
            pointerEvents: 'none',
          }}
        >
          <Typography variant="body2" sx={{ color: '#6b7280', mb: 0.5 }}>
            john.doe@example.com
          </Typography>
          <Typography variant="body2" sx={{ color: '#6b7280', mb: 0.5 }}>
            +1 (555) 123-4567
          </Typography>
          <Typography variant="body2" sx={{ color: '#6b7280' }}>
            linkedin.com/in/johndoe
          </Typography>
        </Box>

        <Box
          sx={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            bgcolor: 'rgba(10, 25, 41, 0.7)',
            borderRadius: 2,
          }}
        >
          <Lock size={24} color="#4f7df9" />
          <Typography
            variant="body2"
            sx={{ color: '#374151', mt: 1, fontWeight: 500 }}
          >
            Upgrade to view contact info
          </Typography>
          <Button
            variant="contained"
            size="small"
            onClick={() => navigate('/billing/subscription')}
            sx={{
              mt: 1,
              textTransform: 'none',
              bgcolor: '#4f7df9',
              color: '#f9fafb',
              fontWeight: 600,
              '&:hover': { bgcolor: '#81d4fa' },
            }}
          >
            View Plans
          </Button>
        </Box>
      </Box>
    );
  }

  // Free plan with active subscription (trialing): show masked data ----------
  if (!isPaidPlan) {
    const maskedEmail =
      emails.length > 0 ? maskEmail(emails[0].email) : null;
    const maskedPhone = phone ? maskPhone(phone) : null;

    return (
      <Box
        sx={{
          p: 2,
          borderRadius: 2,
          bgcolor: 'rgba(79, 195, 247, 0.04)',
          border: '1px solid rgba(79, 195, 247, 0.1)',
        }}
      >
        <Stack spacing={1} sx={{ mb: 1.5 }}>
          {maskedEmail && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Mail size={16} color="#4f7df9" />
              <Typography
                variant="body2"
                sx={{ color: '#6b7280', fontFamily: 'monospace' }}
              >
                {maskedEmail}
              </Typography>
            </Box>
          )}
          {maskedPhone && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Typography variant="body2" sx={{ color: '#6b7280', fontFamily: 'monospace' }}>
                {maskedPhone}
              </Typography>
            </Box>
          )}
        </Stack>

        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            gap: 0.75,
            pt: 1,
            borderTop: '1px solid rgba(79, 195, 247, 0.08)',
          }}
        >
          <Lock size={12} color="#6b7d8e" />
          <Typography variant="caption" sx={{ color: '#6b7d8e' }}>
            Upgrade to a paid plan to see full contact details.
          </Typography>
          <Button
            size="small"
            variant="text"
            onClick={() => navigate('/billing/subscription')}
            sx={{
              ml: 'auto',
              textTransform: 'none',
              fontSize: '0.7rem',
              color: '#4f7df9',
              p: 0,
              minWidth: 0,
              '&:hover': { bgcolor: 'transparent', textDecoration: 'underline' },
            }}
          >
            Upgrade
          </Button>
        </Box>
      </Box>
    );
  }

  // Paid plan: show full contact data ----------------------------------------
  const links = socialLinks ?? {};

  return (
    <Stack spacing={1}>
      {emails.map((e) => (
        <Box key={e.id} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Mail size={16} color="#4f7df9" />
          <Typography
            variant="body2"
            component="a"
            href={`mailto:${e.email}`}
            sx={{
              color: '#4f7df9',
              textDecoration: 'none',
              '&:hover': { textDecoration: 'underline' },
            }}
          >
            {e.email}
          </Typography>
          {e.status !== 'valid' && (
            <Typography variant="caption" sx={{ color: '#ff9800' }}>
              ({e.status})
            </Typography>
          )}
        </Box>
      ))}

      {phone && (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Typography variant="body2" sx={{ color: '#374151' }}>
            {phone}
          </Typography>
        </Box>
      )}

      {website && (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Globe size={16} color="#66bb6a" />
          <Typography
            variant="body2"
            component="a"
            href={website.startsWith('http') ? website : `https://${website}`}
            target="_blank"
            rel="noopener noreferrer"
            sx={{
              color: '#66bb6a',
              textDecoration: 'none',
              '&:hover': { textDecoration: 'underline' },
            }}
          >
            {website}
          </Typography>
        </Box>
      )}

      {links.linkedin && (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Linkedin size={16} color="#0a66c2" />
          <Typography
            variant="body2"
            component="a"
            href={
              links.linkedin.startsWith('http')
                ? links.linkedin
                : `https://${links.linkedin}`
            }
            target="_blank"
            rel="noopener noreferrer"
            sx={{
              color: '#6b7280',
              textDecoration: 'none',
              '&:hover': { textDecoration: 'underline' },
            }}
          >
            LinkedIn
          </Typography>
        </Box>
      )}

      {links.twitter && (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Twitter size={16} color="#1da1f2" />
          <Typography
            variant="body2"
            component="a"
            href={
              links.twitter.startsWith('http')
                ? links.twitter
                : `https://twitter.com/${links.twitter}`
            }
            target="_blank"
            rel="noopener noreferrer"
            sx={{
              color: '#6b7280',
              textDecoration: 'none',
              '&:hover': { textDecoration: 'underline' },
            }}
          >
            Twitter
          </Typography>
        </Box>
      )}

      {links.crunchbase && (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Globe size={16} color="#ff9800" />
          <Typography
            variant="body2"
            component="a"
            href={
              links.crunchbase.startsWith('http')
                ? links.crunchbase
                : `https://www.crunchbase.com/${links.crunchbase}`
            }
            target="_blank"
            rel="noopener noreferrer"
            sx={{
              color: '#6b7280',
              textDecoration: 'none',
              '&:hover': { textDecoration: 'underline' },
            }}
          >
            Crunchbase
          </Typography>
        </Box>
      )}

      {emails.length === 0 &&
        !phone &&
        !website &&
        Object.keys(links).length === 0 && (
          <Typography variant="body2" sx={{ color: '#6b7d8e' }}>
            No contact information available.
          </Typography>
        )}
    </Stack>
  );
};

export default ContactInfoMask;
