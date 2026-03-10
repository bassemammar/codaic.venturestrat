export type ModuleId = 'investor' | 'outreach' | 'crm' | 'billing' | 'legal';

export interface ModuleConfig {
  id: ModuleId;
  label: string;
  accent: string;
  icon: string;
  description: string;
}

export const MODULE_CONFIGS: Record<ModuleId, ModuleConfig> = {
  'investor': {
    id: 'investor',
    label: 'Investor',
    accent: '#4f7df9',
    icon: 'Box',
    description: 'Investor entities',
  },
  'outreach': {
    id: 'outreach',
    label: 'Outreach',
    accent: '#66bb6a',
    icon: 'Box',
    description: 'Outreach entities',
  },
  'crm': {
    id: 'crm',
    label: 'Crm',
    accent: '#ff9800',
    icon: 'UserCheck',
    description: 'Crm entities',
  },
  'billing': {
    id: 'billing',
    label: 'Billing',
    accent: '#f44336',
    icon: 'Box',
    description: 'Billing entities',
  },
  'legal': {
    id: 'legal',
    label: 'Legal',
    accent: '#7c3aed',
    icon: 'Scale',
    description: 'Legal document drafting',
  },
};

export const MODULE_LIST: ModuleConfig[] = Object.values(MODULE_CONFIGS);
