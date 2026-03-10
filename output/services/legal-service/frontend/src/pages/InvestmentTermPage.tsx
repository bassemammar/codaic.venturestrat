/**
 * InvestmentTermPage Component
 *
 * Full-featured page for managing investmentterms with:
 * - List view with search, pagination, and sorting
 * - Create/Edit forms in modal dialogs
 * - Delete confirmation
 * - Breadcrumb navigation
 * - React Query integration for data management
 *
 * SAFE or priced round investment terms linked to a legal entity and investor person
 *
 * @description Page component for InvestmentTerms management
 * @generated 2026-03-10T20:43:55.908960Z
 */

import React, { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Breadcrumbs,
  Link,
  Typography,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Snackbar,
  Alert as MuiAlert,
  IconButton,
} from '@mui/material';
import {
  Add as AddIcon,
  Close as CloseIcon,
  Home as HomeIcon,
  NavigateNext as NavigateNextIcon,
  List as EntityIcon,
} from '@mui/icons-material';

// Entity components
import InvestmentTermList from '../components/InvestmentTermList';
import InvestmentTermForm from '../components/InvestmentTermForm';

// Hooks and types
import {
  useCreateInvestmentTerm,
  useUpdateInvestmentTerm,
  useDeleteInvestmentTerm,
} from '../hooks/useInvestmentTerms';
import type { InvestmentTerm, InvestmentTermCreateRequest, InvestmentTermUpdateRequest } from '../types/investment_term.types';

// ============================================================================
// Types
// ============================================================================

/**
 * Modal mode for create/edit operations
 */
type ModalMode = 'create' | 'edit' | 'view' | null;

/**
 * Notification state
 */
interface NotificationState {
  open: boolean;
  message: string;
  severity: 'success' | 'error' | 'info' | 'warning';
}

// ============================================================================
// Component
// ============================================================================

/**
 * InvestmentTermPage Component
 *
 * Renders the full investmentterms management page including
 * list view and modal dialogs for CRUD operations.
 */
export function InvestmentTermPage(): React.ReactElement {
  const navigate = useNavigate();

  // -------------------------------------------------------------------------
  // State
  // -------------------------------------------------------------------------

  // Modal state
  const [modalMode, setModalMode] = useState<ModalMode>(null);
  const [selectedInvestmentTerm, setSelectedInvestmentTerm] = useState<InvestmentTerm | null>(null);

  // Delete confirmation state
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [investmentTermToDelete, setInvestmentTermToDelete] = useState<InvestmentTerm | null>(null);

  // Notification state
  const [notification, setNotification] = useState<NotificationState>({
    open: false,
    message: '',
    severity: 'success',
  });

  // -------------------------------------------------------------------------
  // Mutations
  // -------------------------------------------------------------------------

  const createMutation = useCreateInvestmentTerm();
  const updateMutation = useUpdateInvestmentTerm();
  const deleteMutation = useDeleteInvestmentTerm();

  // -------------------------------------------------------------------------
  // Handlers
  // -------------------------------------------------------------------------

  /**
   * Show notification
   */
  const showNotification = useCallback(
    (message: string, severity: NotificationState['severity'] = 'success') => {
      setNotification({ open: true, message, severity });
    },
    []
  );

  /**
   * Close notification
   */
  const handleCloseNotification = useCallback(() => {
    setNotification((prev) => ({ ...prev, open: false }));
  }, []);

  /**
   * Open create modal
   */
  const handleOpenCreate = useCallback(() => {
    setSelectedInvestmentTerm(null);
    setModalMode('create');
  }, []);

  /**
   * Open edit modal
   */
  const handleOpenEdit = useCallback((investmentTerm: InvestmentTerm) => {
    setSelectedInvestmentTerm(investmentTerm);
    setModalMode('edit');
  }, []);


  /**
   * Close modal
   */
  const handleCloseModal = useCallback(() => {
    setModalMode(null);
    setSelectedInvestmentTerm(null);
  }, []);

  /**
   * Handle row click in list
   */
  const handleRowClick = useCallback((investmentTerm: InvestmentTerm) => {
    handleOpenEdit(investmentTerm);
  }, [handleOpenEdit]);

  /**
   * Handle create submission
   */
  const handleCreate = useCallback(
    async (data: InvestmentTermCreateRequest) => {
      try {
        await createMutation.mutateAsync(data);
        handleCloseModal();
        showNotification('InvestmentTerm created successfully');
      } catch (error) {
        showNotification(
          `Failed to create investmentterm: ${(error as Error).message}`,
          'error'
        );
      }
    },
    [createMutation, handleCloseModal, showNotification]
  );

  /**
   * Handle update submission
   */
  const handleUpdate = useCallback(
    async (data: InvestmentTermUpdateRequest) => {
      if (!selectedInvestmentTerm) return;

      try {
        await updateMutation.mutateAsync({
          id: selectedInvestmentTerm.id,
          data,
        });
        handleCloseModal();
        showNotification('InvestmentTerm updated successfully');
      } catch (error) {
        showNotification(
          `Failed to update investmentterm: ${(error as Error).message}`,
          'error'
        );
      }
    },
    [selectedInvestmentTerm, updateMutation, handleCloseModal, showNotification]
  );

  /**
   * Open delete confirmation
   */
  const handleOpenDelete = useCallback((investmentTerm: InvestmentTerm) => {
    setInvestmentTermToDelete(investmentTerm);
    setDeleteDialogOpen(true);
  }, []);

  /**
   * Close delete confirmation
   */
  const handleCloseDelete = useCallback(() => {
    setDeleteDialogOpen(false);
    setInvestmentTermToDelete(null);
  }, []);

  /**
   * Handle delete confirmation
   */
  const handleConfirmDelete = useCallback(async () => {
    if (!investmentTermToDelete) return;

    try {
      await deleteMutation.mutateAsync(investmentTermToDelete.id);
      handleCloseDelete();
      showNotification('InvestmentTerm deleted successfully');
    } catch (error) {
      showNotification(
        `Failed to delete investmentterm: ${(error as Error).message}`,
        'error'
      );
    }
  }, [investmentTermToDelete, deleteMutation, handleCloseDelete, showNotification]);

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------

  return (
    <Box>
      {/* Breadcrumbs */}
      <Breadcrumbs
        separator={<NavigateNextIcon fontSize="small" />}
        aria-label="breadcrumb"
        sx={ { mb: 2 } }
      >
        <Link
          component="button"
          underline="hover"
          color="inherit"
          onClick={() => navigate('/')}
sx={{
            display: 'flex',
            alignItems: 'center',
            gap: 0.5,
            cursor: 'pointer',
            border: 'none',
            background: 'none',
            font: 'inherit',
          }}        >
          <HomeIcon fontSize="small" />
          Home
        </Link>
        <Typography
          color="text.primary"
          sx={ { display: 'flex', alignItems: 'center', gap: 0.5 } }
        >
          <EntityIcon fontSize="small" />
          Investmentterms
        </Typography>
      </Breadcrumbs>

      {/* Page Header */}
      <Box
        display="flex"
        justifyContent="space-between"
        alignItems="center"
        mb={3}
      >
        <Box>
          <Typography variant="h4" component="h1" gutterBottom>
            Investmentterms
          </Typography>
          <Typography variant="body2" color="text.secondary">
            SAFE or priced round investment terms linked to a legal entity and investor person
          </Typography>
        </Box>

        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={handleOpenCreate}
        >
          Add Investmentterm
        </Button>
      </Box>

      {/* Entity List */}
      <InvestmentTermList
        title=""
        showAddButton={false}
        onRowClick={handleRowClick}
        onDelete={handleOpenDelete}
      />

      {/* Create/Edit Modal (form_display: modal) */}
      <Dialog
        open={modalMode === 'create' || modalMode === 'edit'}
        onClose={handleCloseModal}
        maxWidth="sm"
        fullWidth
        data-testid="modal-investment_term-form"
      >
        <DialogTitle>
          <Box display="flex" justifyContent="space-between" alignItems="center">
            {modalMode === 'create'
              ? 'Create Investmentterm'
              : 'Edit Investmentterm'}
            <IconButton
              aria-label="close"
              onClick={handleCloseModal}
              size="small"
              data-testid="modal-close-button"
            >
              <CloseIcon />
            </IconButton>
          </Box>
        </DialogTitle>
        <DialogContent dividers>
          <InvestmentTermForm
            investmentTerm={modalMode === 'edit' ? (selectedInvestmentTerm ?? undefined) : undefined}
            onSubmit={modalMode === 'create' ? handleCreate : handleUpdate}
            onCancel={handleCloseModal}
            isLoading={
              modalMode === 'create'
                ? createMutation.isPending
                : updateMutation.isPending
            }
          />
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteDialogOpen}
        onClose={handleCloseDelete}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle>Confirm Delete</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete this investmentterm?
            This action cannot be undone.
          </Typography>
          { investmentTermToDelete && (
            <Box
              mt={2}
              p={2}
              bgcolor="action.hover"
              borderRadius={1}
            >
              <Typography variant="body2" color="text.secondary">
                ID: { investmentTermToDelete.id}
              </Typography>
              <Typography variant="body2">
                Legal Entity Id: {investmentTermToDelete.legal_entity_id}
              </Typography>
              <Typography variant="body2">
                Investor Person Id: {investmentTermToDelete.investor_person_id}
              </Typography>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDelete} disabled={deleteMutation.isPending}>
            Cancel
          </Button>
          <Button
            onClick={handleConfirmDelete}
            color="error"
            variant="contained"
            disabled={deleteMutation.isPending}
          >
            {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Notification Snackbar */}
      <Snackbar
        open={notification.open}
        autoHideDuration={6000}
        onClose={handleCloseNotification}
        anchorOrigin={ { vertical: 'bottom', horizontal: 'right' }}
      >
        <MuiAlert
          onClose={handleCloseNotification}
          severity={notification.severity}
          variant="filled"
          sx={ { width: '100%' } }
        >
          {notification.message}
        </MuiAlert>
      </Snackbar>
    </Box>
  );
}

export default InvestmentTermPage;
