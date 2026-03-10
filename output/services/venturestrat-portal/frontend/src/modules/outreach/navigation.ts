// Legacy navigation file — sidebar now uses flat navigation in ModuleSidebar.tsx
// Kept for reference; no longer imported by PortalShell.

export const outreachNavigation = [
  {
    title: 'Features',
    items: [
      { path: '/outreach/mail', label: 'Email Client' },
    ],
  },
  {
    title: 'Entities',
    collapsed: true,
    items: [
      { path: '/outreach/admin/email-accounts', label: 'Email Account' },
      { path: '/outreach/admin/email-templates', label: 'Email Template' },
      { path: '/outreach/admin/lifecycle-emails', label: 'Lifecycle Email' },
      { path: '/outreach/admin/messages', label: 'Message' },
    ],
  },
];
