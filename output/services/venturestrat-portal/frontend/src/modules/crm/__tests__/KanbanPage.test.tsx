import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../../../test-utils';
import type { PipelineStage } from '@crm/types/pipeline_stage.types';
import type { KanbanShortlist } from '../api/crmApi';
import type { Activity } from '@crm/types/activity.types';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockStages: PipelineStage[] = [
  {
    id: 'stage-1',
    name: 'Identified',
    code: 'identified',
    sequence: 1,
    color: '#3B82F6',
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 'stage-2',
    name: 'Contacted',
    code: 'contacted',
    sequence: 2,
    color: '#10B981',
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
];

const mockShortlists: KanbanShortlist[] = [
  {
    id: 'sl-1',
    user_id: 'user-1',
    investor_id: 'inv-1',
    stage_id: 'stage-1',
    status: 'target',
    notes: 'Important prospect',
    added_at: '2026-01-01T00:00:00Z',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    is_active: true,
    investor_name: 'Jane Doe',
    investor_company: 'Acme Capital',
    investor_location: 'San Francisco',
    stage_name: 'Identified',
    stage_color: '#3B82F6',
    stage_sequence: 1,
    last_activity_summary: 'Called yesterday',
    last_activity_date: '2026-03-09T00:00:00Z',
    tags: [{ id: 't1', name: 'Series A', color: '#4fc3f7' }],
    days_in_stage: 3,
  },
];

const mockActivities: Activity[] = [
  {
    id: 'act-1',
    shortlist_id: 'sl-1',
    activity_type: 'call',
    summary: 'Intro call with Jane',
    details: 'Discussed portfolio',
    date: '2026-03-09T14:00:00Z',
    user_id: 'user-1',
    reference_id: null,
    created_at: '2026-03-09T14:00:00Z',
    updated_at: '2026-03-09T14:00:00Z',
    is_active: true,
  },
  {
    id: 'act-2',
    shortlist_id: 'sl-1',
    activity_type: 'email',
    summary: 'Sent follow-up email',
    details: null,
    date: '2026-03-08T10:00:00Z',
    user_id: 'user-1',
    reference_id: null,
    created_at: '2026-03-08T10:00:00Z',
    updated_at: '2026-03-08T10:00:00Z',
    is_active: true,
  },
];

const mockMutateFn = vi.fn();
const mockCreateActivityMutate = vi.fn();

vi.mock('../hooks/usePipelineStages', () => ({
  usePipelineStages: () => ({
    data: mockStages,
    isLoading: false,
  }),
}));

vi.mock('../hooks/useUserShortlists', () => ({
  useUserShortlists: () => ({
    data: mockShortlists,
    isLoading: false,
  }),
}));

vi.mock('../hooks/useShortlistActivities', () => ({
  useShortlistActivities: (shortlistId: string | null) => ({
    data: shortlistId ? mockActivities : [],
    isLoading: false,
  }),
}));

vi.mock('../hooks/useUpdateShortlistStage', () => ({
  useUpdateShortlistStage: () => ({
    mutate: mockMutateFn,
    isPending: false,
  }),
}));

vi.mock('../hooks/useCreateActivity', () => ({
  useCreateActivity: () => ({
    mutate: mockCreateActivityMutate,
    isPending: false,
    isError: false,
  }),
}));

vi.mock('../api/crmApi', () => ({
  crmApi: {
    getTags: () => Promise.resolve([]),
  },
}));

vi.mock('@hello-pangea/dnd', () => ({
  DragDropContext: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
  Droppable: ({
    children,
    droppableId,
  }: {
    children: (provided: any, snapshot: any) => React.ReactNode;
    droppableId: string;
  }) => {
    const provided = {
      innerRef: vi.fn(),
      droppableProps: { 'data-testid': `droppable-${droppableId}` },
      placeholder: null,
    };
    return <div>{children(provided, { isDraggingOver: false })}</div>;
  },
  Draggable: ({
    children,
    draggableId,
  }: {
    children: (provided: any, snapshot: any) => React.ReactNode;
    draggableId: string;
  }) => {
    const provided = {
      innerRef: vi.fn(),
      draggableProps: { 'data-testid': `draggable-${draggableId}` },
      dragHandleProps: {},
    };
    return <div>{children(provided, { isDragging: false })}</div>;
  },
}));

// ---------------------------------------------------------------------------
// Lazy import the component AFTER mocks are registered
// ---------------------------------------------------------------------------
let KanbanPage: React.FC;

beforeEach(async () => {
  vi.clearAllMocks();
  const mod = await import('../pages/KanbanPage');
  KanbanPage = mod.KanbanPage;
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('KanbanPage', () => {
  it('renders the board with stage columns', () => {
    renderWithProviders(<KanbanPage />);

    // Title + breadcrumb both say "Fundraising"
    const fundElements = screen.getAllByText('Fundraising');
    expect(fundElements.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Identified')).toBeInTheDocument();
    expect(screen.getByText('Contacted')).toBeInTheDocument();
  });

  it('renders card with investor name', () => {
    renderWithProviders(<KanbanPage />);

    expect(screen.getByText('Jane Doe')).toBeInTheDocument();
    expect(screen.getByText('Acme Capital')).toBeInTheDocument();
  });

  it('opens sidebar on card click and shows investor details', async () => {
    const user = userEvent.setup();

    renderWithProviders(<KanbanPage />);

    // Click on the investor card
    await user.click(screen.getByText('Jane Doe'));

    // The drawer should show investor details
    await waitFor(() => {
      // The sidebar renders a second copy of the name as heading
      const nameElements = screen.getAllByText('Jane Doe');
      expect(nameElements.length).toBeGreaterThanOrEqual(2);
    });

    // Should show the company in the sidebar
    const companyElements = screen.getAllByText('Acme Capital');
    expect(companyElements.length).toBeGreaterThanOrEqual(2);
  });

  it('shows activity timeline in sidebar', async () => {
    const user = userEvent.setup();

    renderWithProviders(<KanbanPage />);

    await user.click(screen.getByText('Jane Doe'));

    await waitFor(() => {
      expect(screen.getByText('Activity Timeline')).toBeInTheDocument();
    });

    expect(screen.getByText('Intro call with Jane')).toBeInTheDocument();
    expect(screen.getByText('Sent follow-up email')).toBeInTheDocument();
  });

  it('handles activity form submission', async () => {
    const user = userEvent.setup();

    renderWithProviders(<KanbanPage />);

    // Open sidebar
    await user.click(screen.getByText('Jane Doe'));

    await waitFor(() => {
      expect(screen.getAllByText(/add activity/i).length).toBeGreaterThanOrEqual(1);
    });

    // Type in the activity summary field
    const summaryInput = screen.getByPlaceholderText('Activity summary...');
    await user.type(summaryInput, 'Sent pitch deck');

    // Click Add Activity button
    const addButton = screen.getByRole('button', { name: /add activity/i });
    await user.click(addButton);

    expect(mockCreateActivityMutate).toHaveBeenCalledWith(
      expect.objectContaining({
        shortlist_id: 'sl-1',
        activity_type: 'note',
        summary: 'Sent pitch deck',
      }),
      expect.any(Object),
    );
  });
});
