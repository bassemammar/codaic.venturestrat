// Legacy navigation file — sidebar now uses flat navigation in ModuleSidebar.tsx
// Kept for reference; no longer imported by PortalShell.

export const crmNavigation = [
  {
    title: 'Features',
    items: [
      { path: '/crm/kanban', label: 'Pipeline Board' },
    ],
  },
  {
    title: 'Entities',
    collapsed: true,
    items: [
      { path: '/crm/admin/activities', label: 'Activity' },
      { path: '/crm/admin/pipeline-stages', label: 'Pipeline Stage' },
      { path: '/crm/admin/shortlists', label: 'Shortlist' },
      { path: '/crm/admin/shortlist-tags', label: 'Shortlist Tag' },
      { path: '/crm/admin/tags', label: 'Tag' },
    ],
  },
];
