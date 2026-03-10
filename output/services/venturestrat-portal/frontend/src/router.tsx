import React, { lazy, Suspense } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import CircularProgress from '@mui/material/CircularProgress';
import Box from '@mui/material/Box';
import PortalShell from './layouts/PortalShell';
import LoginPage from './pages/LoginPage';
import GlobalHome from './pages/GlobalHome';
import ModuleHome from './pages/ModuleHome';
import { useAuth } from './auth/AuthProvider';

const S: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <Suspense
    fallback={
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', py: 8 }}>
        <CircularProgress size={24} />
      </Box>
    }
  >
    {children}
  </Suspense>
);

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

// ===== Built-in modules =====
const EventMonitorPage = lazy(() => import('./modules/events/pages/EventMonitorPage'));
const ForgeAdminPage = lazy(() => import('./modules/forge/ForgeAdminPage'));

// ===== Custom pages (Wave 11-14, in portal — never overwritten by codegen) =====
const InvestorListPage = lazy(() => import('./modules/investor/pages/InvestorListPage'));
const InvestorDetailPage = lazy(() => import('./modules/investor/pages/InvestorDetailPage'));
const KanbanPage = lazy(() => import('./modules/crm/pages/KanbanPage'));
const MailPage = lazy(() => import('./modules/outreach/pages/MailPage'));
const SubscriptionPage = lazy(() => import('./modules/billing/pages/SubscriptionPage'));
const PaymentPage = lazy(() => import('./modules/billing/pages/PaymentPage'));
const BillingSuccessPage = lazy(() => import('./modules/billing/pages/BillingSuccessPage'));
const SettingsPage = lazy(() => import('./modules/settings/pages/SettingsPage'));
const OnboardingPage = lazy(() => import('./modules/settings/pages/OnboardingPage'));
const OAuthCallbackPage = lazy(() => import('./modules/settings/pages/OAuthCallbackPage'));
const LandingPage = lazy(() => import('./modules/landing/pages/LandingPage'));
const LegalPage = lazy(() => import('./modules/legal/pages/LegalPage'));
const LegalWizardPage = lazy(() => import('./modules/legal/pages/LegalWizardPage'));
const HelpPage = lazy(() => import('./modules/help/pages/HelpPage'));

// ===== Codegen'd CRUD pages (from service frontends — regeneratable) =====
const InvestorInvestor = lazy(() => import('@inve/pages/InvestorPage').then((m) => ({ default: m.InvestorPage || m.default })));
const InvestorInvestorEmail = lazy(() => import('@inve/pages/InvestorEmailPage').then((m) => ({ default: m.InvestorEmailPage || m.default })));
const InvestorInvestorMarket = lazy(() => import('@inve/pages/InvestorMarketPage').then((m) => ({ default: m.InvestorMarketPage || m.default })));
const InvestorInvestorPastInvestment = lazy(() => import('@inve/pages/InvestorPastInvestmentPage').then((m) => ({ default: m.InvestorPastInvestmentPage || m.default })));
const InvestorMarket = lazy(() => import('@inve/pages/MarketPage').then((m) => ({ default: m.MarketPage || m.default })));
const InvestorPastInvestment = lazy(() => import('@inve/pages/PastInvestmentPage').then((m) => ({ default: m.PastInvestmentPage || m.default })));
const OutreachEmailAccount = lazy(() => import('@outr/pages/EmailAccountPage').then((m) => ({ default: m.EmailAccountPage || m.default })));
const OutreachEmailTemplate = lazy(() => import('@outr/pages/EmailTemplatePage').then((m) => ({ default: m.EmailTemplatePage || m.default })));
const OutreachLifecycleEmail = lazy(() => import('@outr/pages/LifecycleEmailPage').then((m) => ({ default: m.LifecycleEmailPage || m.default })));
const OutreachMessage = lazy(() => import('@outr/pages/MessagePage').then((m) => ({ default: m.MessagePage || m.default })));
const CrmActivity = lazy(() => import('@crm/pages/ActivityPage').then((m) => ({ default: m.ActivityPage || m.default })));
const CrmPipelineStage = lazy(() => import('@crm/pages/PipelineStagePage').then((m) => ({ default: m.PipelineStagePage || m.default })));
const CrmShortlist = lazy(() => import('@crm/pages/ShortlistPage').then((m) => ({ default: m.ShortlistPage || m.default })));
const CrmShortlistTag = lazy(() => import('@crm/pages/ShortlistTagPage').then((m) => ({ default: m.ShortlistTagPage || m.default })));
const CrmTag = lazy(() => import('@crm/pages/TagPage').then((m) => ({ default: m.TagPage || m.default })));
const BillingPlan = lazy(() => import('@bill/pages/PlanPage').then((m) => ({ default: m.PlanPage || m.default })));
const BillingSubscriptionCrud = lazy(() => import('@bill/pages/SubscriptionPage').then((m) => ({ default: m.SubscriptionPage || m.default })));
const BillingUsageRecord = lazy(() => import('@bill/pages/UsageRecordPage').then((m) => ({ default: m.UsageRecordPage || m.default })));

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      {/* Public pages (no auth) */}
      <Route path="/welcome" element={<S><LandingPage /></S>} />

      {/* Onboarding (no shell) */}
      <Route path="/onboarding" element={<ProtectedRoute><S><OnboardingPage /></S></ProtectedRoute>} />

      {/* OAuth callbacks — rendered without PortalShell, auth required */}
      <Route path="/settings/oauth/google/callback" element={<ProtectedRoute><S><OAuthCallbackPage /></S></ProtectedRoute>} />
      <Route path="/settings/oauth/microsoft/callback" element={<ProtectedRoute><S><OAuthCallbackPage /></S></ProtectedRoute>} />

      <Route
        path="/"
        element={
          <ProtectedRoute>
            <PortalShell />
          </ProtectedRoute>
        }
      >
        <Route index element={<GlobalHome />} />
        <Route path="dashboard" element={<S><GlobalHome /></S>} />

        {/* Built-in modules */}
        <Route path="events" element={<S><EventMonitorPage /></S>} />
        <Route path="forge/admin" element={<S><ForgeAdminPage /></S>} />

        {/* ===== Custom pages (product features) ===== */}

        {/* Investor discovery */}
        <Route path="investor" element={<S><ModuleHome moduleId="investor" /></S>} />
        <Route path="investor/search" element={<S><InvestorListPage /></S>} />
        <Route path="investor/discover/:id" element={<S><InvestorDetailPage /></S>} />

        {/* CRM pipeline */}
        <Route path="crm" element={<S><ModuleHome moduleId="crm" /></S>} />
        <Route path="crm/kanban" element={<S><KanbanPage /></S>} />

        {/* Outreach / Email */}
        <Route path="outreach" element={<S><ModuleHome moduleId="outreach" /></S>} />
        <Route path="outreach/mail" element={<S><MailPage /></S>} />

        {/* Billing */}
        <Route path="billing" element={<S><ModuleHome moduleId="billing" /></S>} />
        <Route path="billing/subscription" element={<S><SubscriptionPage /></S>} />
        <Route path="billing/payment/:planId" element={<S><PaymentPage /></S>} />
        <Route path="billing/success" element={<S><BillingSuccessPage /></S>} />

        {/* Settings */}
        <Route path="settings" element={<S><SettingsPage /></S>} />

        {/* Legal */}
        <Route path="legal" element={<S><ModuleHome moduleId="legal" /></S>} />
        <Route path="legal/wizard" element={<S><LegalWizardPage /></S>} />
        <Route path="legal/terms" element={<S><LegalPage /></S>} />

        {/* Help */}
        <Route path="help" element={<S><HelpPage /></S>} />

        {/* ===== Admin CRUD pages (codegen'd, from service frontends) ===== */}
        <Route path="investor/admin/investors" element={<S><InvestorInvestor /></S>} />
        <Route path="investor/admin/investor-emails" element={<S><InvestorInvestorEmail /></S>} />
        <Route path="investor/admin/investor-markets" element={<S><InvestorInvestorMarket /></S>} />
        <Route path="investor/admin/investor-past-investments" element={<S><InvestorInvestorPastInvestment /></S>} />
        <Route path="investor/admin/markets" element={<S><InvestorMarket /></S>} />
        <Route path="investor/admin/past-investments" element={<S><InvestorPastInvestment /></S>} />
        <Route path="outreach/admin/email-accounts" element={<S><OutreachEmailAccount /></S>} />
        <Route path="outreach/admin/email-templates" element={<S><OutreachEmailTemplate /></S>} />
        <Route path="outreach/admin/lifecycle-emails" element={<S><OutreachLifecycleEmail /></S>} />
        <Route path="outreach/admin/messages" element={<S><OutreachMessage /></S>} />
        <Route path="crm/admin/activities" element={<S><CrmActivity /></S>} />
        <Route path="crm/admin/pipeline-stages" element={<S><CrmPipelineStage /></S>} />
        <Route path="crm/admin/shortlists" element={<S><CrmShortlist /></S>} />
        <Route path="crm/admin/shortlist-tags" element={<S><CrmShortlistTag /></S>} />
        <Route path="crm/admin/tags" element={<S><CrmTag /></S>} />
        <Route path="billing/admin/plans" element={<S><BillingPlan /></S>} />
        <Route path="billing/admin/subscriptions" element={<S><BillingSubscriptionCrud /></S>} />
        <Route path="billing/admin/usage-records" element={<S><BillingUsageRecord /></S>} />
      </Route>
    </Routes>
  );
}
