/**
 * DocumentTemplatePage Component
 *
 * Full-featured page for managing documenttemplates with:
 * - List view with search, pagination, and sorting
 * - Create/Edit forms in modal dialogs
 * - Delete confirmation
 * - Breadcrumb navigation
 * - React Query integration for data management
 *
 * Legal document template definition — NDA, founders agreement, SAFE, employment, etc.
 *
 * @description Page component for DocumentTemplates management
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
import DocumentTemplateList from '../components/DocumentTemplateList';
import DocumentTemplateForm from '../components/DocumentTemplateForm';

// Hooks and types
import {
  useCreateDocumentTemplate,
  useUpdateDocumentTemplate,
  useDeleteDocumentTemplate,
} from '../hooks/useDocumentTemplates';
import type { DocumentTemplate, DocumentTemplateCreateRequest, DocumentTemplateUpdateRequest } from '../types/document_template.types';

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
 * DocumentTemplatePage Component
 *
 * Renders the full documenttemplates management page including
 * list view and modal dialogs for CRUD operations.
 */
export function DocumentTemplatePage(): React.ReactElement {
  const navigate = useNavigate();

  // -------------------------------------------------------------------------
  // State
  // -------------------------------------------------------------------------

  // Modal state
  const [modalMode, setModalMode] = useState<ModalMode>(null);
  const [selectedDocumentTemplate, setSelectedDocumentTemplate] = useState<DocumentTemplate | null>(null);

  // Delete confirmation state
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [documentTemplateToDelete, setDocumentTemplateToDelete] = useState<DocumentTemplate | null>(null);

  // Notification state
  const [notification, setNotification] = useState<NotificationState>({
    open: false,
    message: '',
    severity: 'success',
  });

  // -------------------------------------------------------------------------
  // Mutations
  // -------------------------------------------------------------------------

  const createMutation = useCreateDocumentTemplate();
  const updateMutation = useUpdateDocumentTemplate();
  const deleteMutation = useDeleteDocumentTemplate();

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
    setSelectedDocumentTemplate(null);
    setModalMode('create');
  }, []);

  /**
   * Open edit modal
   */
  const handleOpenEdit = useCallback((documentTemplate: DocumentTemplate) => {
    setSelectedDocumentTemplate(documentTemplate);
    setModalMode('edit');
  }, []);


  /**
   * Close modal
   */
  const handleCloseModal = useCallback(() => {
    setModalMode(null);
    setSelectedDocumentTemplate(null);
  }, []);

  /**
   * Handle row click in list
   */
  const handleRowClick = useCallback((documentTemplate: DocumentTemplate) => {
    handleOpenEdit(documentTemplate);
  }, [handleOpenEdit]);

  /**
   * Handle create submission
   */
  const handleCreate = useCallback(
    async (data: DocumentTemplateCreateRequest) => {
      try {
        await createMutation.mutateAsync(data);
        handleCloseModal();
        showNotification('DocumentTemplate created successfully');
      } catch (error) {
        showNotification(
          `Failed to create documenttemplate: ${(error as Error).message}`,
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
    async (data: DocumentTemplateUpdateRequest) => {
      if (!selectedDocumentTemplate) return;

      try {
        await updateMutation.mutateAsync({
          id: selectedDocumentTemplate.id,
          data,
        });
        handleCloseModal();
        showNotification('DocumentTemplate updated successfully');
      } catch (error) {
        showNotification(
          `Failed to update documenttemplate: ${(error as Error).message}`,
          'error'
        );
      }
    },
    [selectedDocumentTemplate, updateMutation, handleCloseModal, showNotification]
  );

  /**
   * Open delete confirmation
   */
  const handleOpenDelete = useCallback((documentTemplate: DocumentTemplate) => {
    setDocumentTemplateToDelete(documentTemplate);
    setDeleteDialogOpen(true);
  }, []);

  /**
   * Close delete confirmation
   */
  const handleCloseDelete = useCallback(() => {
    setDeleteDialogOpen(false);
    setDocumentTemplateToDelete(null);
  }, []);

  /**
   * Handle delete confirmation
   */
  const handleConfirmDelete = useCallback(async () => {
    if (!documentTemplateToDelete) return;

    try {
      await deleteMutation.mutateAsync(documentTemplateToDelete.id);
      handleCloseDelete();
      showNotification('DocumentTemplate deleted successfully');
    } catch (error) {
      showNotification(
        `Failed to delete documenttemplate: ${(error as Error).message}`,
        'error'
      );
    }
  }, [documentTemplateToDelete, deleteMutation, handleCloseDelete, showNotification]);

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
          Documenttemplates
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
            Documenttemplates
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Legal document template definition — NDA, founders agreement, SAFE, employment, etc.
          </Typography>
        </Box>

        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={handleOpenCreate}
        >
          Add Documenttemplate
        </Button>
      </Box>

      {/* Entity List */}
      <DocumentTemplateList
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
        data-testid="modal-document_template-form"
      >
        <DialogTitle>
          <Box display="flex" justifyContent="space-between" alignItems="center">
            {modalMode === 'create'
              ? 'Create Documenttemplate'
              : 'Edit Documenttemplate'}
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
          <DocumentTemplateForm
            documentTemplate={modalMode === 'edit' ? (selectedDocumentTemplate ?? undefined) : undefined}
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
            Are you sure you want to delete this documenttemplate?
            This action cannot be undone.
          </Typography>
          { documentTemplateToDelete && (
            <Box
              mt={2}
              p={2}
              bgcolor="action.hover"
              borderRadius={1}
            >
              <Typography variant="body2" color="text.secondary">
                ID: { documentTemplateToDelete.id}
              </Typography>
              <Typography variant="body2">
                Name: {documentTemplateToDelete.name}
              </Typography>
              <Typography variant="body2">
                Document Type: {documentTemplateToDelete.document_type}
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

export default DocumentTemplatePage;
