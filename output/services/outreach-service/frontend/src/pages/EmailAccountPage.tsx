/**
 * EmailAccountPage Component
 *
 * Full-featured page for managing emailaccounts with:
 * - List view with search, pagination, and sorting
 * - Create/Edit forms in modal dialogs
 * - Delete confirmation
 * - Breadcrumb navigation
 * - React Query integration for data management
 *
 * OAuth email account for sending via Gmail, Microsoft, or SendGrid
 *
 * @description Page component for EmailAccounts management
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
import EmailAccountList from '../components/EmailAccountList';
import EmailAccountForm from '../components/EmailAccountForm';

// Hooks and types
import {
  useCreateEmailAccount,
  useUpdateEmailAccount,
  useDeleteEmailAccount,
} from '../hooks/useEmailAccounts';
import type { EmailAccount, EmailAccountCreateRequest, EmailAccountUpdateRequest } from '../types/email_account.types';

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
 * EmailAccountPage Component
 *
 * Renders the full emailaccounts management page including
 * list view and modal dialogs for CRUD operations.
 */
export function EmailAccountPage(): React.ReactElement {
  const navigate = useNavigate();

  // -------------------------------------------------------------------------
  // State
  // -------------------------------------------------------------------------

  // Modal state
  const [modalMode, setModalMode] = useState<ModalMode>(null);
  const [selectedEmailAccount, setSelectedEmailAccount] = useState<EmailAccount | null>(null);

  // Delete confirmation state
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [emailAccountToDelete, setEmailAccountToDelete] = useState<EmailAccount | null>(null);

  // Notification state
  const [notification, setNotification] = useState<NotificationState>({
    open: false,
    message: '',
    severity: 'success',
  });

  // -------------------------------------------------------------------------
  // Mutations
  // -------------------------------------------------------------------------

  const createMutation = useCreateEmailAccount();
  const updateMutation = useUpdateEmailAccount();
  const deleteMutation = useDeleteEmailAccount();

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
    setSelectedEmailAccount(null);
    setModalMode('create');
  }, []);

  /**
   * Open edit modal
   */
  const handleOpenEdit = useCallback((emailAccount: EmailAccount) => {
    setSelectedEmailAccount(emailAccount);
    setModalMode('edit');
  }, []);


  /**
   * Close modal
   */
  const handleCloseModal = useCallback(() => {
    setModalMode(null);
    setSelectedEmailAccount(null);
  }, []);

  /**
   * Handle row click in list
   */
  const handleRowClick = useCallback((emailAccount: EmailAccount) => {
    handleOpenEdit(emailAccount);
  }, [handleOpenEdit]);

  /**
   * Handle create submission
   */
  const handleCreate = useCallback(
    async (data: EmailAccountCreateRequest) => {
      try {
        await createMutation.mutateAsync(data);
        handleCloseModal();
        showNotification('EmailAccount created successfully');
      } catch (error) {
        showNotification(
          `Failed to create emailaccount: ${(error as Error).message}`,
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
    async (data: EmailAccountUpdateRequest) => {
      if (!selectedEmailAccount) return;

      try {
        await updateMutation.mutateAsync({
          id: selectedEmailAccount.id,
          data,
        });
        handleCloseModal();
        showNotification('EmailAccount updated successfully');
      } catch (error) {
        showNotification(
          `Failed to update emailaccount: ${(error as Error).message}`,
          'error'
        );
      }
    },
    [selectedEmailAccount, updateMutation, handleCloseModal, showNotification]
  );

  /**
   * Open delete confirmation
   */
  const handleOpenDelete = useCallback((emailAccount: EmailAccount) => {
    setEmailAccountToDelete(emailAccount);
    setDeleteDialogOpen(true);
  }, []);

  /**
   * Close delete confirmation
   */
  const handleCloseDelete = useCallback(() => {
    setDeleteDialogOpen(false);
    setEmailAccountToDelete(null);
  }, []);

  /**
   * Handle delete confirmation
   */
  const handleConfirmDelete = useCallback(async () => {
    if (!emailAccountToDelete) return;

    try {
      await deleteMutation.mutateAsync(emailAccountToDelete.id);
      handleCloseDelete();
      showNotification('EmailAccount deleted successfully');
    } catch (error) {
      showNotification(
        `Failed to delete emailaccount: ${(error as Error).message}`,
        'error'
      );
    }
  }, [emailAccountToDelete, deleteMutation, handleCloseDelete, showNotification]);

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
          Emailaccounts
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
            Emailaccounts
          </Typography>
          <Typography variant="body2" color="text.secondary">
            OAuth email account for sending via Gmail, Microsoft, or SendGrid
          </Typography>
        </Box>

        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={handleOpenCreate}
        >
          Add Emailaccount
        </Button>
      </Box>

      {/* Entity List */}
      <EmailAccountList
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
        data-testid="modal-email_account-form"
      >
        <DialogTitle>
          <Box display="flex" justifyContent="space-between" alignItems="center">
            {modalMode === 'create'
              ? 'Create Emailaccount'
              : 'Edit Emailaccount'}
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
          <EmailAccountForm
            emailAccount={modalMode === 'edit' ? (selectedEmailAccount ?? undefined) : undefined}
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
            Are you sure you want to delete this emailaccount?
            This action cannot be undone.
          </Typography>
          { emailAccountToDelete && (
            <Box
              mt={2}
              p={2}
              bgcolor="action.hover"
              borderRadius={1}
            >
              <Typography variant="body2" color="text.secondary">
                ID: { emailAccountToDelete.id}
              </Typography>
              <Typography variant="body2">
                User Id: {emailAccountToDelete.user_id}
              </Typography>
              <Typography variant="body2">
                Provider: {emailAccountToDelete.provider}
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

export default EmailAccountPage;
