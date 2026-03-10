// Legacy navigation file — sidebar now uses flat navigation in ModuleSidebar.tsx
// Kept for reference; no longer imported by PortalShell.

export const investorNavigation = [
  {
    title: 'Features',
    items: [
      { path: '/investor/search', label: 'Search Investors' },
    ],
  },
  {
    title: 'Entities',
    collapsed: true,
    items: [
      { path: '/investor/admin/investors', label: 'Investor' },
      { path: '/investor/admin/investor-emails', label: 'Investor Email' },
      { path: '/investor/admin/investor-markets', label: 'Investor Market' },
      { path: '/investor/admin/investor-past-investments', label: 'Investor Past Investment' },
      { path: '/investor/admin/markets', label: 'Market' },
      { path: '/investor/admin/past-investments', label: 'Past Investment' },
    ],
  },
];
