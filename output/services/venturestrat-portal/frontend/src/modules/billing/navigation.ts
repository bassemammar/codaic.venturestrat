// Legacy navigation file — sidebar now uses flat navigation in ModuleSidebar.tsx
// Kept for reference; no longer imported by PortalShell.

export const billingNavigation = [
  {
    title: 'Features',
    items: [
      { path: '/billing/subscription', label: 'My Subscription' },
    ],
  },
  {
    title: 'Entities',
    collapsed: true,
    items: [
      { path: '/billing/admin/plans', label: 'Plan' },
      { path: '/billing/admin/subscriptions', label: 'Subscription' },
      { path: '/billing/admin/usage-records', label: 'Usage Record' },
    ],
  },
];
