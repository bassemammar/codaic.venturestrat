/**
 * LegalEntityPage Component
 *
 * Full-featured page for managing legalentities with:
 * - List view with search, pagination, and sorting
 * - Create/Edit forms in modal dialogs
 * - Delete confirmation
 * - Breadcrumb navigation
 * - React Query integration for data management
 *
 * Legal entity (company or organization) that acts as party in legal documents
 *
 * @description Page component for LegalEntities management
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
import LegalEntityList from '../components/LegalEntityList';
import LegalEntityForm from '../components/LegalEntityForm';

// Hooks and types
import {
  useCreateLegalEntity,
  useUpdateLegalEntity,
  useDeleteLegalEntity,
} from '../hooks/useLegalEntities';
import type { LegalEntity, LegalEntityCreateRequest, LegalEntityUpdateRequest } from '../types/legal_entity.types';

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
 * LegalEntityPage Component
 *
 * Renders the full legalentities management page including
 * list view and modal dialogs for CRUD operations.
 */
export function LegalEntityPage(): React.ReactElement {
  const navigate = useNavigate();

  // -------------------------------------------------------------------------
  // State
  // -------------------------------------------------------------------------

  // Modal state
  const [modalMode, setModalMode] = useState<ModalMode>(null);
  const [selectedLegalEntity, setSelectedLegalEntity] = useState<LegalEntity | null>(null);

  // Delete confirmation state
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [legalEntityToDelete, setLegalEntityToDelete] = useState<LegalEntity | null>(null);

  // Notification state
  const [notification, setNotification] = useState<NotificationState>({
    open: false,
    message: '',
    severity: 'success',
  });

  // -------------------------------------------------------------------------
  // Mutations
  // -------------------------------------------------------------------------

  const createMutation = useCreateLegalEntity();
  const updateMutation = useUpdateLegalEntity();
  const deleteMutation = useDeleteLegalEntity();

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
    setSelectedLegalEntity(null);
    setModalMode('create');
  }, []);

  /**
   * Open edit modal
   */
  const handleOpenEdit = useCallback((legalEntity: LegalEntity) => {
    setSelectedLegalEntity(legalEntity);
    setModalMode('edit');
  }, []);


  /**
   * Close modal
   */
  const handleCloseModal = useCallback(() => {
    setModalMode(null);
    setSelectedLegalEntity(null);
  }, []);

  /**
   * Handle row click in list
   */
  const handleRowClick = useCallback((legalEntity: LegalEntity) => {
    handleOpenEdit(legalEntity);
  }, [handleOpenEdit]);

  /**
   * Handle create submission
   */
  const handleCreate = useCallback(
    async (data: LegalEntityCreateRequest) => {
      try {
        await createMutation.mutateAsync(data);
        handleCloseModal();
        showNotification('LegalEntity created successfully');
      } catch (error) {
        showNotification(
          `Failed to create legalentity: ${(error as Error).message}`,
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
    async (data: LegalEntityUpdateRequest) => {
      if (!selectedLegalEntity) return;

      try {
        await updateMutation.mutateAsync({
          id: selectedLegalEntity.id,
          data,
        });
        handleCloseModal();
        showNotification('LegalEntity updated successfully');
      } catch (error) {
        showNotification(
          `Failed to update legalentity: ${(error as Error).message}`,
          'error'
        );
      }
    },
    [selectedLegalEntity, updateMutation, handleCloseModal, showNotification]
  );

  /**
   * Open delete confirmation
   */
  const handleOpenDelete = useCallback((legalEntity: LegalEntity) => {
    setLegalEntityToDelete(legalEntity);
    setDeleteDialogOpen(true);
  }, []);

  /**
   * Close delete confirmation
   */
  const handleCloseDelete = useCallback(() => {
    setDeleteDialogOpen(false);
    setLegalEntityToDelete(null);
  }, []);

  /**
   * Handle delete confirmation
   */
  const handleConfirmDelete = useCallback(async () => {
    if (!legalEntityToDelete) return;

    try {
      await deleteMutation.mutateAsync(legalEntityToDelete.id);
      handleCloseDelete();
      showNotification('LegalEntity deleted successfully');
    } catch (error) {
      showNotification(
        `Failed to delete legalentity: ${(error as Error).message}`,
        'error'
      );
    }
  }, [legalEntityToDelete, deleteMutation, handleCloseDelete, showNotification]);

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
          Legalentities
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
            Legalentities
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Legal entity (company or organization) that acts as party in legal documents
          </Typography>
        </Box>

        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={handleOpenCreate}
        >
          Add Legalentity
        </Button>
      </Box>

      {/* Entity List */}
      <LegalEntityList
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
        data-testid="modal-legal_entity-form"
      >
        <DialogTitle>
          <Box display="flex" justifyContent="space-between" alignItems="center">
            {modalMode === 'create'
              ? 'Create Legalentity'
              : 'Edit Legalentity'}
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
          <LegalEntityForm
            legalEntity={modalMode === 'edit' ? (selectedLegalEntity ?? undefined) : undefined}
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
            Are you sure you want to delete this legalentity?
            This action cannot be undone.
          </Typography>
          { legalEntityToDelete && (
            <Box
              mt={2}
              p={2}
              bgcolor="action.hover"
              borderRadius={1}
            >
              <Typography variant="body2" color="text.secondary">
                ID: { legalEntityToDelete.id}
              </Typography>
              <Typography variant="body2">
                User Id: {legalEntityToDelete.user_id}
              </Typography>
              <Typography variant="body2">
                Legal Name: {legalEntityToDelete.legal_name}
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

export default LegalEntityPage;
