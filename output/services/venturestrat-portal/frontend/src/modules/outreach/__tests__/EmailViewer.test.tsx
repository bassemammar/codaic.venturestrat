import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../../../test-utils';
import { EmailViewer, type EmailViewerProps } from '../components/EmailViewer';
import type { Message } from '@outr/types/message.types';
import type { EmailAccount } from '@outr/types/email_account.types';

// ---------------------------------------------------------------------------
// Mock child components
// ---------------------------------------------------------------------------

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
  default: ({
    open,
    onClose,
    onUse,
    mode,
  }: {
    open: boolean;
    onClose: () => void;
    onUse: (subject: string, body: string) => void;
    mode: string;
  }) =>
    open ? (
      <div data-testid="ai-email-modal">
        <span>AI Modal ({mode})</span>
        <button onClick={onClose}>Close Modal</button>
        <button onClick={() => onUse('AI Subject', '<p>AI Body</p>')}>
          Use AI Draft
        </button>
      </div>
    ) : null,
}));

// Mock date-fns to avoid timezone issues in tests
vi.mock('date-fns', async (importOriginal) => {
  const actual = await importOriginal() as Record<string, unknown>;
  return {
    ...actual,
    format: (_date: Date, _fmt: string) => 'Mar 10, 2026, 10:00 AM',
  };
});

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
  {
    id: 'acct-2',
    user_id: 'user-1',
    provider: 'outlook',
    email_address: 'user@outlook.com',
    access_token: null,
    refresh_token: null,
    token_expires_at: null,
    watch_history_id: null,
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
];

const mockMessage: Message = {
  id: 'msg-1',
  user_id: 'user-1',
  investor_id: 'inv-1',
  email_account_id: 'acct-1',
  status: 'sent',
  to_addresses: ['investor@example.com'],
  cc_addresses: {},
  subject: 'Follow-up on our call',
  from_address: 'user@example.com',
  body: '<p>Dear Investor, thank you for your time.</p>',
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
};

const defaultProps: EmailViewerProps = {
  mode: 'compose',
  message: null,
  accounts: mockAccounts,
  onSend: vi.fn(),
  onSchedule: vi.fn(),
  onSaveDraft: vi.fn(),
  onClose: vi.fn(),
  isSending: false,
  isScheduling: false,
  isSaving: false,
};

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('EmailViewer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('compose mode', () => {
    it('renders To, Subject, and Body fields', () => {
      renderWithProviders(<EmailViewer {...defaultProps} mode="compose" />);

      expect(screen.getByLabelText('To')).toBeInTheDocument();
      expect(screen.getByLabelText('Subject')).toBeInTheDocument();
      expect(screen.getByTestId('rich-text-editor')).toBeInTheDocument();
    });

    it('renders From account selector', () => {
      renderWithProviders(<EmailViewer {...defaultProps} mode="compose" />);

      // The From label is rendered via MUI InputLabel inside a Select
      const fromLabels = screen.getAllByText(/From/);
      expect(fromLabels.length).toBeGreaterThanOrEqual(1);
    });

    it('send button calls onSaveDraft and onSend when message has id', async () => {
      const onSend = vi.fn();
      const onSaveDraft = vi.fn();
      const user = userEvent.setup();

      const messageWithId: Message = {
        ...mockMessage,
        id: 'msg-draft-1',
        status: 'draft',
      };

      renderWithProviders(
        <EmailViewer
          {...defaultProps}
          mode="compose"
          message={messageWithId}
          onSend={onSend}
          onSaveDraft={onSaveDraft}
        />,
      );

      const sendButton = screen.getByRole('button', { name: /send/i });
      await user.click(sendButton);

      expect(onSaveDraft).toHaveBeenCalled();
      expect(onSend).toHaveBeenCalledWith('msg-draft-1');
    });

    it('schedule button opens datetime picker popover', async () => {
      const user = userEvent.setup();

      renderWithProviders(
        <EmailViewer
          {...defaultProps}
          mode="compose"
          message={mockMessage}
        />,
      );

      const scheduleButton = screen.getByRole('button', { name: /schedule/i });
      await user.click(scheduleButton);

      await waitFor(() => {
        expect(screen.getByText('Schedule Send')).toBeInTheDocument();
      });
    });
  });

  describe('reply mode', () => {
    it('prefills subject with "Re: " prefix', () => {
      renderWithProviders(
        <EmailViewer
          {...defaultProps}
          mode="reply"
          message={mockMessage}
        />,
      );

      const subjectInput = screen.getByLabelText('Subject');
      expect(subjectInput).toHaveValue('Re: Follow-up on our call');
    });

    it('shows "Reply" in the header', () => {
      renderWithProviders(
        <EmailViewer
          {...defaultProps}
          mode="reply"
          message={mockMessage}
        />,
      );

      expect(screen.getByText('Reply')).toBeInTheDocument();
    });
  });

  describe('view mode', () => {
    it('renders read-only content with subject and body', () => {
      renderWithProviders(
        <EmailViewer
          {...defaultProps}
          mode="view"
          message={mockMessage}
        />,
      );

      expect(screen.getByText('Follow-up on our call')).toBeInTheDocument();
      expect(screen.getByText(/From:/)).toBeInTheDocument();
      expect(screen.getByText(/To:/)).toBeInTheDocument();
    });

    it('shows status chip', () => {
      renderWithProviders(
        <EmailViewer
          {...defaultProps}
          mode="view"
          message={mockMessage}
        />,
      );

      expect(screen.getByText('sent')).toBeInTheDocument();
    });

    it('does not show compose form fields in view mode', () => {
      renderWithProviders(
        <EmailViewer
          {...defaultProps}
          mode="view"
          message={mockMessage}
        />,
      );

      expect(screen.queryByLabelText('To')).not.toBeInTheDocument();
      expect(screen.queryByTestId('rich-text-editor')).not.toBeInTheDocument();
    });
  });

  describe('AI Draft', () => {
    it('opens AI modal when AI Draft button is clicked', async () => {
      const user = userEvent.setup();

      renderWithProviders(
        <EmailViewer {...defaultProps} mode="compose" />,
      );

      const aiDraftButton = screen.getByRole('button', { name: /ai draft/i });
      await user.click(aiDraftButton);

      await waitFor(() => {
        expect(screen.getByTestId('ai-email-modal')).toBeInTheDocument();
        expect(screen.getByText('AI Modal (generate)')).toBeInTheDocument();
      });
    });
  });
});
