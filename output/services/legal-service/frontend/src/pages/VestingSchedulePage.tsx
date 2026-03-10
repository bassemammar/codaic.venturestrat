/**
 * VestingSchedulePage Component
 *
 * Full-featured page for managing vestingschedules with:
 * - List view with search, pagination, and sorting
 * - Create/Edit forms in modal dialogs
 * - Delete confirmation
 * - Breadcrumb navigation
 * - React Query integration for data management
 *
 * Vesting schedule for equity grants — cliff period, total period, and acceleration triggers
 *
 * @description Page component for VestingSchedules management
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
import VestingScheduleList from '../components/VestingScheduleList';
import VestingScheduleForm from '../components/VestingScheduleForm';

// Hooks and types
import {
  useCreateVestingSchedule,
  useUpdateVestingSchedule,
  useDeleteVestingSchedule,
} from '../hooks/useVestingSchedules';
import type { VestingSchedule, VestingScheduleCreateRequest, VestingScheduleUpdateRequest } from '../types/vesting_schedule.types';

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
 * VestingSchedulePage Component
 *
 * Renders the full vestingschedules management page including
 * list view and modal dialogs for CRUD operations.
 */
export function VestingSchedulePage(): React.ReactElement {
  const navigate = useNavigate();

  // -------------------------------------------------------------------------
  // State
  // -------------------------------------------------------------------------

  // Modal state
  const [modalMode, setModalMode] = useState<ModalMode>(null);
  const [selectedVestingSchedule, setSelectedVestingSchedule] = useState<VestingSchedule | null>(null);

  // Delete confirmation state
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [vestingScheduleToDelete, setVestingScheduleToDelete] = useState<VestingSchedule | null>(null);

  // Notification state
  const [notification, setNotification] = useState<NotificationState>({
    open: false,
    message: '',
    severity: 'success',
  });

  // -------------------------------------------------------------------------
  // Mutations
  // -------------------------------------------------------------------------

  const createMutation = useCreateVestingSchedule();
  const updateMutation = useUpdateVestingSchedule();
  const deleteMutation = useDeleteVestingSchedule();

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
    setSelectedVestingSchedule(null);
    setModalMode('create');
  }, []);

  /**
   * Open edit modal
   */
  const handleOpenEdit = useCallback((vestingSchedule: VestingSchedule) => {
    setSelectedVestingSchedule(vestingSchedule);
    setModalMode('edit');
  }, []);


  /**
   * Close modal
   */
  const handleCloseModal = useCallback(() => {
    setModalMode(null);
    setSelectedVestingSchedule(null);
  }, []);

  /**
   * Handle row click in list
   */
  const handleRowClick = useCallback((vestingSchedule: VestingSchedule) => {
    handleOpenEdit(vestingSchedule);
  }, [handleOpenEdit]);

  /**
   * Handle create submission
   */
  const handleCreate = useCallback(
    async (data: VestingScheduleCreateRequest) => {
      try {
        await createMutation.mutateAsync(data);
        handleCloseModal();
        showNotification('VestingSchedule created successfully');
      } catch (error) {
        showNotification(
          `Failed to create vestingschedule: ${(error as Error).message}`,
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
    async (data: VestingScheduleUpdateRequest) => {
      if (!selectedVestingSchedule) return;

      try {
        await updateMutation.mutateAsync({
          id: selectedVestingSchedule.id,
          data,
        });
        handleCloseModal();
        showNotification('VestingSchedule updated successfully');
      } catch (error) {
        showNotification(
          `Failed to update vestingschedule: ${(error as Error).message}`,
          'error'
        );
      }
    },
    [selectedVestingSchedule, updateMutation, handleCloseModal, showNotification]
  );

  /**
   * Open delete confirmation
   */
  const handleOpenDelete = useCallback((vestingSchedule: VestingSchedule) => {
    setVestingScheduleToDelete(vestingSchedule);
    setDeleteDialogOpen(true);
  }, []);

  /**
   * Close delete confirmation
   */
  const handleCloseDelete = useCallback(() => {
    setDeleteDialogOpen(false);
    setVestingScheduleToDelete(null);
  }, []);

  /**
   * Handle delete confirmation
   */
  const handleConfirmDelete = useCallback(async () => {
    if (!vestingScheduleToDelete) return;

    try {
      await deleteMutation.mutateAsync(vestingScheduleToDelete.id);
      handleCloseDelete();
      showNotification('VestingSchedule deleted successfully');
    } catch (error) {
      showNotification(
        `Failed to delete vestingschedule: ${(error as Error).message}`,
        'error'
      );
    }
  }, [vestingScheduleToDelete, deleteMutation, handleCloseDelete, showNotification]);

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
          Vestingschedules
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
            Vestingschedules
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Vesting schedule for equity grants — cliff period, total period, and acceleration triggers
          </Typography>
        </Box>

        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={handleOpenCreate}
        >
          Add Vestingschedule
        </Button>
      </Box>

      {/* Entity List */}
      <VestingScheduleList
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
        data-testid="modal-vesting_schedule-form"
      >
        <DialogTitle>
          <Box display="flex" justifyContent="space-between" alignItems="center">
            {modalMode === 'create'
              ? 'Create Vestingschedule'
              : 'Edit Vestingschedule'}
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
          <VestingScheduleForm
            vestingSchedule={modalMode === 'edit' ? (selectedVestingSchedule ?? undefined) : undefined}
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
            Are you sure you want to delete this vestingschedule?
            This action cannot be undone.
          </Typography>
          { vestingScheduleToDelete && (
            <Box
              mt={2}
              p={2}
              bgcolor="action.hover"
              borderRadius={1}
            >
              <Typography variant="body2" color="text.secondary">
                ID: { vestingScheduleToDelete.id}
              </Typography>
              <Typography variant="body2">
                Equity Grant Id: {vestingScheduleToDelete.equity_grant_id}
              </Typography>
              <Typography variant="body2">
                Total Period Months: {vestingScheduleToDelete.total_period_months}
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

export default VestingSchedulePage;
