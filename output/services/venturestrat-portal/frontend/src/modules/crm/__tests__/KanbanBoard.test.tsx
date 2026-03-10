import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../../../test-utils';
import { KanbanBoard } from '../components/KanbanBoard';
import type { PipelineStage } from '@crm/types/pipeline_stage.types';
import type { KanbanShortlist } from '../api/crmApi';

// ---------------------------------------------------------------------------
// Mock @hello-pangea/dnd — render children directly, expose drag callbacks
// ---------------------------------------------------------------------------

const mockOnDragEnd = vi.fn();

vi.mock('@hello-pangea/dnd', () => ({
  DragDropContext: ({
    children,
    onDragEnd,
  }: {
    children: React.ReactNode;
    onDragEnd: (result: any) => void;
  }) => {
    // Expose onDragEnd via the module-level ref so tests can call it
    mockOnDragEnd.mockImplementation(onDragEnd);
    return <div data-testid="dnd-context">{children}</div>;
  },
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
    const snapshot = { isDraggingOver: false };
    return <div>{children(provided, snapshot)}</div>;
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
    const snapshot = { isDragging: false };
    return <div>{children(provided, snapshot)}</div>;
  },
}));

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

function makeStage(overrides: Partial<PipelineStage> = {}): PipelineStage {
  return {
    id: 'stage-1',
    name: 'Identified',
    code: 'identified',
    sequence: 1,
    color: '#3B82F6',
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

function makeShortlist(overrides: Partial<KanbanShortlist> = {}): KanbanShortlist {
  return {
    id: 'sl-1',
    user_id: 'user-1',
    investor_id: 'inv-1',
    stage_id: 'stage-1',
    status: 'target',
    notes: null,
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
    last_activity_summary: undefined,
    last_activity_date: undefined,
    tags: [],
    days_in_stage: 3,
    ...overrides,
  };
}

const stages: PipelineStage[] = [
  makeStage({ id: 'stage-1', name: 'Identified', sequence: 1, color: '#3B82F6' }),
  makeStage({ id: 'stage-2', name: 'Contacted', sequence: 2, color: '#10B981' }),
  makeStage({ id: 'stage-3', name: 'Meeting', sequence: 3, color: '#F59E0B' }),
];

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('KanbanBoard', () => {
  const onDrop = vi.fn();
  const onCardClick = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders correct number of columns matching pipeline stages', () => {
    renderWithProviders(
      <KanbanBoard
        stages={stages}
        shortlists={[]}
        isLoading={false}
        onDrop={onDrop}
        onCardClick={onCardClick}
      />,
    );

    expect(screen.getByText('Identified')).toBeInTheDocument();
    expect(screen.getByText('Contacted')).toBeInTheDocument();
    expect(screen.getByText('Meeting')).toBeInTheDocument();
  });

  it('renders cards in correct columns', () => {
    const shortlists = [
      makeShortlist({ id: 'sl-1', stage_id: 'stage-1', investor_name: 'Alice' }),
      makeShortlist({ id: 'sl-2', stage_id: 'stage-2', investor_name: 'Bob' }),
      makeShortlist({ id: 'sl-3', stage_id: 'stage-1', investor_name: 'Charlie' }),
    ];

    renderWithProviders(
      <KanbanBoard
        stages={stages}
        shortlists={shortlists}
        isLoading={false}
        onDrop={onDrop}
        onCardClick={onCardClick}
      />,
    );

    // All card names should be rendered
    expect(screen.getByText('Alice')).toBeInTheDocument();
    expect(screen.getByText('Bob')).toBeInTheDocument();
    expect(screen.getByText('Charlie')).toBeInTheDocument();

    // Stage-1 droppable should contain Alice and Charlie
    const droppable1 = screen.getByTestId('droppable-stage-1');
    expect(within(droppable1).getByText('Alice')).toBeInTheDocument();
    expect(within(droppable1).getByText('Charlie')).toBeInTheDocument();

    // Stage-2 droppable should contain Bob
    const droppable2 = screen.getByTestId('droppable-stage-2');
    expect(within(droppable2).getByText('Bob')).toBeInTheDocument();
  });

  it('displays investor name and company on card', () => {
    const shortlists = [
      makeShortlist({
        id: 'sl-1',
        stage_id: 'stage-1',
        investor_name: 'Jane Doe',
        investor_company: 'Acme Capital',
      }),
    ];

    renderWithProviders(
      <KanbanBoard
        stages={stages}
        shortlists={shortlists}
        isLoading={false}
        onDrop={onDrop}
        onCardClick={onCardClick}
      />,
    );

    expect(screen.getByText('Jane Doe')).toBeInTheDocument();
    expect(screen.getByText('Acme Capital')).toBeInTheDocument();
  });

  it('calls onDrop with correct params when drag ends on a different stage', () => {
    const shortlists = [
      makeShortlist({ id: 'sl-1', stage_id: 'stage-1', investor_name: 'Alice' }),
    ];

    renderWithProviders(
      <KanbanBoard
        stages={stages}
        shortlists={shortlists}
        isLoading={false}
        onDrop={onDrop}
        onCardClick={onCardClick}
      />,
    );

    // Simulate a drag-end event
    mockOnDragEnd({
      draggableId: 'sl-1',
      destination: { droppableId: 'stage-2', index: 0 },
      source: { droppableId: 'stage-1', index: 0 },
    });

    expect(onDrop).toHaveBeenCalledWith('sl-1', 'stage-2');
  });

  it('does not call onDrop when dropped in the same stage', () => {
    const shortlists = [
      makeShortlist({ id: 'sl-1', stage_id: 'stage-1', investor_name: 'Alice' }),
    ];

    renderWithProviders(
      <KanbanBoard
        stages={stages}
        shortlists={shortlists}
        isLoading={false}
        onDrop={onDrop}
        onCardClick={onCardClick}
      />,
    );

    mockOnDragEnd({
      draggableId: 'sl-1',
      destination: { droppableId: 'stage-1', index: 0 },
      source: { droppableId: 'stage-1', index: 0 },
    });

    expect(onDrop).not.toHaveBeenCalled();
  });

  it('shows empty state in columns with no cards', () => {
    renderWithProviders(
      <KanbanBoard
        stages={stages}
        shortlists={[]}
        isLoading={false}
        onDrop={onDrop}
        onCardClick={onCardClick}
      />,
    );

    const emptyTexts = screen.getAllByText('No investors');
    expect(emptyTexts).toHaveLength(3);
  });

  it('shows count badges on column headers', () => {
    const shortlists = [
      makeShortlist({ id: 'sl-1', stage_id: 'stage-1', investor_name: 'Alice' }),
      makeShortlist({ id: 'sl-2', stage_id: 'stage-1', investor_name: 'Bob' }),
      makeShortlist({ id: 'sl-3', stage_id: 'stage-2', investor_name: 'Charlie' }),
    ];

    renderWithProviders(
      <KanbanBoard
        stages={stages}
        shortlists={shortlists}
        isLoading={false}
        onDrop={onDrop}
        onCardClick={onCardClick}
      />,
    );

    // MUI Chip labels for counts
    // Stage-1 has 2 items, stage-2 has 1, stage-3 has 0
    const chips = screen.getAllByRole('generic');
    // Check by text content — the Chip renders the count as its label
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('0')).toBeInTheDocument();
  });

  it('shows loading spinner when isLoading is true', () => {
    renderWithProviders(
      <KanbanBoard
        stages={stages}
        shortlists={[]}
        isLoading={true}
        onDrop={onDrop}
        onCardClick={onCardClick}
      />,
    );

    expect(screen.getByRole('progressbar')).toBeInTheDocument();
    expect(screen.queryByText('Identified')).not.toBeInTheDocument();
  });

  it('calls onCardClick when a card is clicked', async () => {
    const user = userEvent.setup();
    const shortlist = makeShortlist({
      id: 'sl-1',
      stage_id: 'stage-1',
      investor_name: 'Alice',
    });

    renderWithProviders(
      <KanbanBoard
        stages={stages}
        shortlists={[shortlist]}
        isLoading={false}
        onDrop={onDrop}
        onCardClick={onCardClick}
      />,
    );

    await user.click(screen.getByText('Alice'));
    expect(onCardClick).toHaveBeenCalledWith(shortlist);
  });
});
