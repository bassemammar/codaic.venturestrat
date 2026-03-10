/**
 * PastInvestmentPage Component
 *
 * Full-featured page for managing pastinvestments with:
 * - List view with search, pagination, and sorting
 * - Create/Edit forms in modal dialogs
 * - Delete confirmation
 * - Breadcrumb navigation
 * - React Query integration for data management
 *
 * Portfolio company that an investor has previously invested in
 *
 * @description Page component for PastInvestments management
 * @generated 2026-03-10T13:09:13.176583Z
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
import PastInvestmentList from '../components/PastInvestmentList';
import PastInvestmentForm from '../components/PastInvestmentForm';

// Hooks and types
import {
  useCreatePastInvestment,
  useUpdatePastInvestment,
  useDeletePastInvestment,
} from '../hooks/usePastInvestments';
import type { PastInvestment, PastInvestmentCreateRequest, PastInvestmentUpdateRequest } from '../types/past_investment.types';

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
 * PastInvestmentPage Component
 *
 * Renders the full pastinvestments management page including
 * list view and modal dialogs for CRUD operations.
 */
export function PastInvestmentPage(): React.ReactElement {
  const navigate = useNavigate();

  // -------------------------------------------------------------------------
  // State
  // -------------------------------------------------------------------------

  // Modal state
  const [modalMode, setModalMode] = useState<ModalMode>(null);
  const [selectedPastInvestment, setSelectedPastInvestment] = useState<PastInvestment | null>(null);

  // Delete confirmation state
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [pastInvestmentToDelete, setPastInvestmentToDelete] = useState<PastInvestment | null>(null);

  // Notification state
  const [notification, setNotification] = useState<NotificationState>({
    open: false,
    message: '',
    severity: 'success',
  });

  // -------------------------------------------------------------------------
  // Mutations
  // -------------------------------------------------------------------------

  const createMutation = useCreatePastInvestment();
  const updateMutation = useUpdatePastInvestment();
  const deleteMutation = useDeletePastInvestment();

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
    setSelectedPastInvestment(null);
    setModalMode('create');
  }, []);

  /**
   * Open edit modal
   */
  const handleOpenEdit = useCallback((pastInvestment: PastInvestment) => {
    setSelectedPastInvestment(pastInvestment);
    setModalMode('edit');
  }, []);


  /**
   * Close modal
   */
  const handleCloseModal = useCallback(() => {
    setModalMode(null);
    setSelectedPastInvestment(null);
  }, []);

  /**
   * Handle row click in list
   */
  const handleRowClick = useCallback((pastInvestment: PastInvestment) => {
    handleOpenEdit(pastInvestment);
  }, [handleOpenEdit]);

  /**
   * Handle create submission
   */
  const handleCreate = useCallback(
    async (data: PastInvestmentCreateRequest) => {
      try {
        await createMutation.mutateAsync(data);
        handleCloseModal();
        showNotification('PastInvestment created successfully');
      } catch (error) {
        showNotification(
          `Failed to create pastinvestment: ${(error as Error).message}`,
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
    async (data: PastInvestmentUpdateRequest) => {
      if (!selectedPastInvestment) return;

      try {
        await updateMutation.mutateAsync({
          id: selectedPastInvestment.id,
          data,
        });
        handleCloseModal();
        showNotification('PastInvestment updated successfully');
      } catch (error) {
        showNotification(
          `Failed to update pastinvestment: ${(error as Error).message}`,
          'error'
        );
      }
    },
    [selectedPastInvestment, updateMutation, handleCloseModal, showNotification]
  );

  /**
   * Open delete confirmation
   */
  const handleOpenDelete = useCallback((pastInvestment: PastInvestment) => {
    setPastInvestmentToDelete(pastInvestment);
    setDeleteDialogOpen(true);
  }, []);

  /**
   * Close delete confirmation
   */
  const handleCloseDelete = useCallback(() => {
    setDeleteDialogOpen(false);
    setPastInvestmentToDelete(null);
  }, []);

  /**
   * Handle delete confirmation
   */
  const handleConfirmDelete = useCallback(async () => {
    if (!pastInvestmentToDelete) return;

    try {
      await deleteMutation.mutateAsync(pastInvestmentToDelete.id);
      handleCloseDelete();
      showNotification('PastInvestment deleted successfully');
    } catch (error) {
      showNotification(
        `Failed to delete pastinvestment: ${(error as Error).message}`,
        'error'
      );
    }
  }, [pastInvestmentToDelete, deleteMutation, handleCloseDelete, showNotification]);

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
          Pastinvestments
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
            Pastinvestments
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Portfolio company that an investor has previously invested in
          </Typography>
        </Box>

        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={handleOpenCreate}
        >
          Add Pastinvestment
        </Button>
      </Box>

      {/* Entity List */}
      <PastInvestmentList
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
        data-testid="modal-past_investment-form"
      >
        <DialogTitle>
          <Box display="flex" justifyContent="space-between" alignItems="center">
            {modalMode === 'create'
              ? 'Create Pastinvestment'
              : 'Edit Pastinvestment'}
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
          <PastInvestmentForm
            pastInvestment={modalMode === 'edit' ? (selectedPastInvestment ?? undefined) : undefined}
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
            Are you sure you want to delete this pastinvestment?
            This action cannot be undone.
          </Typography>
          { pastInvestmentToDelete && (
            <Box
              mt={2}
              p={2}
              bgcolor="action.hover"
              borderRadius={1}
            >
              <Typography variant="body2" color="text.secondary">
                ID: { pastInvestmentToDelete.id}
              </Typography>
              <Typography variant="body2">
                Title: {pastInvestmentToDelete.title}
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

export default PastInvestmentPage;
