/**
 * LifecycleEmailPage Component
 *
 * Full-featured page for managing lifecycleemails with:
 * - List view with search, pagination, and sorting
 * - Create/Edit forms in modal dialogs
 * - Delete confirmation
 * - Breadcrumb navigation
 * - React Query integration for data management
 *
 * Tracks drip campaign email execution per user
 *
 * @description Page component for LifecycleEmails management
 * @generated 2026-03-10T13:09:41.930152Z
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
import LifecycleEmailList from '../components/LifecycleEmailList';
import LifecycleEmailForm from '../components/LifecycleEmailForm';

// Hooks and types
import {
  useCreateLifecycleEmail,
  useUpdateLifecycleEmail,
  useDeleteLifecycleEmail,
} from '../hooks/useLifecycleEmails';
import type { LifecycleEmail, LifecycleEmailCreateRequest, LifecycleEmailUpdateRequest } from '../types/lifecycle_email.types';

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
 * LifecycleEmailPage Component
 *
 * Renders the full lifecycleemails management page including
 * list view and modal dialogs for CRUD operations.
 */
export function LifecycleEmailPage(): React.ReactElement {
  const navigate = useNavigate();

  // -------------------------------------------------------------------------
  // State
  // -------------------------------------------------------------------------

  // Modal state
  const [modalMode, setModalMode] = useState<ModalMode>(null);
  const [selectedLifecycleEmail, setSelectedLifecycleEmail] = useState<LifecycleEmail | null>(null);

  // Delete confirmation state
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [lifecycleEmailToDelete, setLifecycleEmailToDelete] = useState<LifecycleEmail | null>(null);

  // Notification state
  const [notification, setNotification] = useState<NotificationState>({
    open: false,
    message: '',
    severity: 'success',
  });

  // -------------------------------------------------------------------------
  // Mutations
  // -------------------------------------------------------------------------

  const createMutation = useCreateLifecycleEmail();
  const updateMutation = useUpdateLifecycleEmail();
  const deleteMutation = useDeleteLifecycleEmail();

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
    setSelectedLifecycleEmail(null);
    setModalMode('create');
  }, []);

  /**
   * Open edit modal
   */
  const handleOpenEdit = useCallback((lifecycleEmail: LifecycleEmail) => {
    setSelectedLifecycleEmail(lifecycleEmail);
    setModalMode('edit');
  }, []);


  /**
   * Close modal
   */
  const handleCloseModal = useCallback(() => {
    setModalMode(null);
    setSelectedLifecycleEmail(null);
  }, []);

  /**
   * Handle row click in list
   */
  const handleRowClick = useCallback((lifecycleEmail: LifecycleEmail) => {
    handleOpenEdit(lifecycleEmail);
  }, [handleOpenEdit]);

  /**
   * Handle create submission
   */
  const handleCreate = useCallback(
    async (data: LifecycleEmailCreateRequest) => {
      try {
        await createMutation.mutateAsync(data);
        handleCloseModal();
        showNotification('LifecycleEmail created successfully');
      } catch (error) {
        showNotification(
          `Failed to create lifecycleemail: ${(error as Error).message}`,
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
    async (data: LifecycleEmailUpdateRequest) => {
      if (!selectedLifecycleEmail) return;

      try {
        await updateMutation.mutateAsync({
          id: selectedLifecycleEmail.id,
          data,
        });
        handleCloseModal();
        showNotification('LifecycleEmail updated successfully');
      } catch (error) {
        showNotification(
          `Failed to update lifecycleemail: ${(error as Error).message}`,
          'error'
        );
      }
    },
    [selectedLifecycleEmail, updateMutation, handleCloseModal, showNotification]
  );

  /**
   * Open delete confirmation
   */
  const handleOpenDelete = useCallback((lifecycleEmail: LifecycleEmail) => {
    setLifecycleEmailToDelete(lifecycleEmail);
    setDeleteDialogOpen(true);
  }, []);

  /**
   * Close delete confirmation
   */
  const handleCloseDelete = useCallback(() => {
    setDeleteDialogOpen(false);
    setLifecycleEmailToDelete(null);
  }, []);

  /**
   * Handle delete confirmation
   */
  const handleConfirmDelete = useCallback(async () => {
    if (!lifecycleEmailToDelete) return;

    try {
      await deleteMutation.mutateAsync(lifecycleEmailToDelete.id);
      handleCloseDelete();
      showNotification('LifecycleEmail deleted successfully');
    } catch (error) {
      showNotification(
        `Failed to delete lifecycleemail: ${(error as Error).message}`,
        'error'
      );
    }
  }, [lifecycleEmailToDelete, deleteMutation, handleCloseDelete, showNotification]);

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
          Lifecycleemails
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
            Lifecycleemails
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Tracks drip campaign email execution per user
          </Typography>
        </Box>

        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={handleOpenCreate}
        >
          Add Lifecycleemail
        </Button>
      </Box>

      {/* Entity List */}
      <LifecycleEmailList
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
        data-testid="modal-lifecycle_email-form"
      >
        <DialogTitle>
          <Box display="flex" justifyContent="space-between" alignItems="center">
            {modalMode === 'create'
              ? 'Create Lifecycleemail'
              : 'Edit Lifecycleemail'}
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
          <LifecycleEmailForm
            lifecycleEmail={modalMode === 'edit' ? (selectedLifecycleEmail ?? undefined) : undefined}
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
            Are you sure you want to delete this lifecycleemail?
            This action cannot be undone.
          </Typography>
          { lifecycleEmailToDelete && (
            <Box
              mt={2}
              p={2}
              bgcolor="action.hover"
              borderRadius={1}
            >
              <Typography variant="body2" color="text.secondary">
                ID: { lifecycleEmailToDelete.id}
              </Typography>
              <Typography variant="body2">
                User Id: {lifecycleEmailToDelete.user_id}
              </Typography>
              <Typography variant="body2">
                Template Code: {lifecycleEmailToDelete.template_code}
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

export default LifecycleEmailPage;
