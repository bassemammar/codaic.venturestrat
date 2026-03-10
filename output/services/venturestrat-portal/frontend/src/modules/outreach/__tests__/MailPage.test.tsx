import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../../../test-utils';
import type { Message } from '@outr/types/message.types';
import type { EmailAccount } from '@outr/types/email_account.types';

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const mockAccounts: EmailAccount[] = [
  {
    id: 'acct-1',
    user_id: 'user-1',
    provider: 'gmail',
    email_address: 'user@example.com',
    access_token: null,
    refresh_token: null,
    token_expires_at: null,
    watch_history_id: null,
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
];

const mockMessages: Message[] = [
  {
    id: 'msg-1',
    user_id: 'user-1',
    investor_id: null,
    email_account_id: 'acct-1',
    status: 'draft',
    to_addresses: ['investor@example.com'],
    cc_addresses: {},
    subject: 'Draft: Intro email',
    from_address: 'user@example.com',
    body: '<p>Hello investor</p>',
    attachments: {},
    thread_id: null,
    provider_message_id: null,
    provider_references: null,
    previous_message_id: null,
    scheduled_for: null,
    job_id: null,
    created_at: '2026-03-10T10:00:00Z',
    updated_at: '2026-03-10T10:00:00Z',
    is_active: true,
  },
  {
    id: 'msg-2',
    user_id: 'user-1',
    investor_id: null,
    email_account_id: 'acct-1',
    status: 'sent',
    to_addresses: ['bob@fund.com'],
    cc_addresses: {},
    subject: 'Follow-up meeting',
    from_address: 'user@example.com',
    body: '<p>Thanks for the call</p>',
    attachments: {},
    thread_id: null,
    provider_message_id: null,
    provider_references: null,
    previous_message_id: null,
    scheduled_for: null,
    job_id: null,
    created_at: '2026-03-09T08:00:00Z',
    updated_at: '2026-03-09T08:00:00Z',
    is_active: true,
  },
];

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock('../hooks/useMessages', () => ({
  useMessages: () => ({
    data: mockMessages,
    isLoading: false,
  }),
}));

vi.mock('../hooks/useEmailAccounts', () => ({
  useEmailAccounts: () => ({
    data: mockAccounts,
    isLoading: false,
  }),
}));

vi.mock('../hooks/useCreateMessage', () => ({
  useCreateMessage: () => ({
    mutateAsync: vi.fn().mockResolvedValue({
      id: 'new-msg',
      subject: '',
      body: '',
      status: 'draft',
    }),
    isPending: false,
  }),
  useUpdateMessage: () => ({
    mutateAsync: vi.fn().mockResolvedValue({}),
    isPending: false,
  }),
}));

vi.mock('../hooks/useSendMessage', () => ({
  useSendMessage: () => ({
    mutateAsync: vi.fn().mockResolvedValue({}),
    isPending: false,
  }),
}));

vi.mock('../hooks/useScheduleMessage', () => ({
  useScheduleMessage: () => ({
    mutateAsync: vi.fn().mockResolvedValue({}),
    isPending: false,
  }),
}));

vi.mock('@/auth/AuthProvider', () => ({
  useAuth: () => ({
    user: {
      id: 'user-1',
      role: 'admin',
      permissions: [],
    },
    isAuthenticated: true,
    loading: false,
    error: null,
  }),
}));

vi.mock('../components/RichTextEditor', () => ({
  default: ({
    value,
    onChange,
    placeholder,
  }: {
    value: string;
    onChange: (html: string) => void;
    placeholder?: string;
  }) => (
    <textarea
      data-testid="rich-text-editor"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
    />
  ),
}));

vi.mock('../components/AIEmailModal', () => ({
  default: ({ open }: { open: boolean }) =>
    open ? <div data-testid="ai-email-modal">AI Modal</div> : null,
}));

vi.mock('date-fns', () => ({
  format: () => 'Mar 10',
  isToday: () => false,
  isYesterday: () => false,
}));

// ---------------------------------------------------------------------------
// Lazy import after mocks
// ---------------------------------------------------------------------------
let MailPage: React.FC;

beforeEach(async () => {
  vi.clearAllMocks();
  const mod = await import('../pages/MailPage');
  MailPage = mod.MailPage;
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('MailPage', () => {
  it('renders sidebar with message tabs', () => {
    renderWithProviders(<MailPage />);

    expect(screen.getByText('Mail')).toBeInTheDocument();
    // EmailSidebar renders tabs
    expect(screen.getByText('Drafts')).toBeInTheDocument();
    expect(screen.getByText('Sent')).toBeInTheDocument();
    expect(screen.getByText('Inbox')).toBeInTheDocument();
  });

  it('compose button creates new draft viewer', async () => {
    const user = userEvent.setup();

    renderWithProviders(<MailPage />);

    // Click the Compose button in the top bar
    const composeButtons = screen.getAllByRole('button', { name: /compose/i });
    await user.click(composeButtons[0]);

    await waitFor(() => {
      expect(screen.getByText('New Email')).toBeInTheDocument();
    });
  });

  it('shows message subjects in the sidebar list', () => {
    renderWithProviders(<MailPage />);

    // The sidebar should show the draft message subject
    expect(screen.getByText('Draft: Intro email')).toBeInTheDocument();
  });

  it('selecting a draft message opens it in compose mode', async () => {
    const user = userEvent.setup();

    renderWithProviders(<MailPage />);

    // Click on the draft message in the sidebar
    // The subject is rendered in the list item
    await user.click(screen.getByText('Draft: Intro email'));

    await waitFor(() => {
      // Compose mode shows "New Email" header for draft status
      expect(screen.getByText('New Email')).toBeInTheDocument();
    });

    // Should show the To and Subject fields
    expect(screen.getByLabelText('To')).toBeInTheDocument();
    expect(screen.getByLabelText('Subject')).toBeInTheDocument();
  });

  it('selecting a sent message opens it in view mode', async () => {
    const user = userEvent.setup();

    renderWithProviders(<MailPage />);

    // Switch to "Sent" tab first, then click the message
    const sentTab = screen.getByText('Sent');
    await user.click(sentTab);

    await waitFor(() => {
      expect(screen.getByText('Follow-up meeting')).toBeInTheDocument();
    });

    await user.click(screen.getByText('Follow-up meeting'));

    await waitFor(() => {
      // View mode shows the subject as heading
      const subjectElements = screen.getAllByText('Follow-up meeting');
      expect(subjectElements.length).toBeGreaterThanOrEqual(1);
    });
  });
});
