/**
 * Step 4: ReviewGenerate — Preview, validate, generate, and download.
 */

import React from 'react'
import {
  Box,
  Typography,
  Paper,
  Button,
  Alert,
  AlertTitle,
  Chip,
  Divider,
  CircularProgress,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
} from '@mui/material'
import {
  Eye,
  FileDown,
  AlertTriangle,
  CheckCircle,
  XCircle,
  FileText,
} from 'lucide-react'
import {
  useWizardStore,
  useGeneratedDocument,
  useValidation,
  useWizardUi,
  usePartyA,
  usePartyB,
  useConfiguration,
  useDocumentType,
} from '../../../stores/legal-wizard-store'

const ReviewGenerate: React.FC = () => {
  const documentType = useDocumentType()
  const partyA = usePartyA()
  const partyB = usePartyB()
  const config = useConfiguration()
  const generated = useGeneratedDocument()
  const validation = useValidation()
  const ui = useWizardUi()
  const {
    setLoading,
    setError,
    setPreviewContent,
    setGeneratedDocument,
    setValidation,
  } = useWizardStore()

  const handlePreview = async () => {
    setLoading(true)
    setError(null)
    try {
      const tenantId = localStorage.getItem('tenant_id') || '00000000-0000-0000-0000-000000000000'
      const authToken = localStorage.getItem('auth_token') || ''
      const apiHeaders: Record<string, string> = {
        'Content-Type': 'application/json',
        'X-Tenant-ID': tenantId,
      }
      if (authToken) apiHeaders['Authorization'] = `Bearer ${authToken}`
      const resp = await fetch('/api/v1/documents/preview', {
        method: 'POST',
        headers: apiHeaders,
        body: JSON.stringify({
          document_type: documentType,
          title: `NDA - ${partyA.companyName || 'Party A'} and ${partyB.companyName || 'Party B'}`,
          document_data: {
            party_a: {
              company_id: partyA.companyId,
              signatory_person_id: partyA.signatoryId,
            },
            party_b: {
              company_id: partyB.companyId,
              signatory_person_id: partyB.signatoryId,
            },
            configuration: {
              purpose_option: config.purposeOption,
              personal_data_sharing: config.personalDataSharing,
              agreement_duration: config.agreementDuration,
              confidentiality_survival: config.confidentialitySurvival,
              permitted_recipients: config.permittedRecipients,
              return_or_destruction: config.returnOrDestruction,
              ai_ml_restrictions: config.aiMlRestrictions,
              governing_law: config.governingLaw,
              dispute_resolution: config.disputeResolution,
              non_solicitation: config.nonSolicitation,
              additional_clauses: config.additionalClauses,
            },
          },
        }),
      })
      if (!resp.ok) throw new Error('Preview failed')
      const data = await resp.json()
      setPreviewContent(data.content_preview)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Preview failed')
    } finally {
      setLoading(false)
    }
  }

  const handleGenerate = async () => {
    setLoading(true)
    setError(null)
    try {
      const tenantId2 = localStorage.getItem('tenant_id') || '00000000-0000-0000-0000-000000000000'
      const authToken2 = localStorage.getItem('auth_token') || ''
      const genHeaders: Record<string, string> = {
        'Content-Type': 'application/json',
        'X-Tenant-ID': tenantId2,
      }
      if (authToken2) genHeaders['Authorization'] = `Bearer ${authToken2}`
      const resp = await fetch('/api/v1/documents/generate', {
        method: 'POST',
        headers: genHeaders,
        body: JSON.stringify({
          document_type: documentType,
          title: `NDA - ${partyA.companyName || 'Party A'} and ${partyB.companyName || 'Party B'}`,
          document_data: {
            party_a: {
              company_id: partyA.companyId,
              signatory_person_id: partyA.signatoryId,
            },
            party_b: {
              company_id: partyB.companyId,
              signatory_person_id: partyB.signatoryId,
            },
            configuration: {
              purpose_option: config.purposeOption,
              personal_data_sharing: config.personalDataSharing,
              agreement_duration: config.agreementDuration,
              confidentiality_survival: config.confidentialitySurvival,
              permitted_recipients: config.permittedRecipients,
              return_or_destruction: config.returnOrDestruction,
              ai_ml_restrictions: config.aiMlRestrictions,
              governing_law: config.governingLaw,
              dispute_resolution: config.disputeResolution,
              non_solicitation: config.nonSolicitation,
              additional_clauses: config.additionalClauses,
            },
          },
        }),
      })
      if (!resp.ok) throw new Error('Generation failed')
      const data = await resp.json()
      setGeneratedDocument({
        id: data.document.id,
        downloadUrl: data.download_url,
        previewUrl: data.preview_url,
        wordCount: data.metadata.word_count,
        pageCount: data.metadata.page_count,
        clauseCount: data.metadata.clause_count,
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Generation failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Box>
      <Typography variant="h6" fontWeight={600} sx={{ mb: 1 }}>
        Review & Generate
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Preview your document, then generate the final version.
      </Typography>

      {/* Summary */}
      <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
        <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 1 }}>
          Document Summary
        </Typography>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
          <Chip label={`Type: ${documentType}`} size="small" variant="outlined" />
          <Chip label={`Party A: ${partyA.companyName || 'Not selected'}`} size="small" variant="outlined" />
          <Chip label={`Party B: ${partyB.companyName || 'Not selected'}`} size="small" variant="outlined" />
          <Chip label={`Law: ${config.governingLaw}`} size="small" variant="outlined" />
          <Chip label={`Duration: Option ${config.agreementDuration}`} size="small" variant="outlined" />
        </Box>
      </Paper>

      {/* Validation Summary */}
      {!validation.valid && (
        <Alert severity="error" sx={{ mb: 2 }}>
          <AlertTitle>Validation Errors</AlertTitle>
          <List dense disablePadding>
            {validation.errors.map((err, i) => (
              <ListItem key={i} disableGutters>
                <ListItemIcon sx={{ minWidth: 28 }}>
                  <XCircle size={16} color="#ef4444" />
                </ListItemIcon>
                <ListItemText
                  primary={err.message}
                  secondary={`Rule ${err.ruleId} — ${err.severity}`}
                />
              </ListItem>
            ))}
          </List>
        </Alert>
      )}

      {validation.warnings.length > 0 && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          <AlertTitle>Warnings</AlertTitle>
          <List dense disablePadding>
            {validation.warnings.map((warn, i) => (
              <ListItem key={i} disableGutters>
                <ListItemIcon sx={{ minWidth: 28 }}>
                  <AlertTriangle size={16} color="#f59e0b" />
                </ListItemIcon>
                <ListItemText
                  primary={warn.message}
                  secondary={`Rule ${warn.ruleId}`}
                />
              </ListItem>
            ))}
          </List>
        </Alert>
      )}

      {ui.error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {ui.error}
        </Alert>
      )}

      {/* Preview Panel */}
      {ui.previewContent && (
        <Paper
          variant="outlined"
          sx={{
            p: 3,
            mb: 2,
            maxHeight: 400,
            overflow: 'auto',
            bgcolor: '#fafafa',
            fontFamily: 'monospace',
            fontSize: 13,
            whiteSpace: 'pre-wrap',
          }}
        >
          {ui.previewContent}
        </Paper>
      )}

      {/* Action Buttons */}
      <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
        <Button
          variant="outlined"
          startIcon={ui.loading ? <CircularProgress size={16} /> : <Eye size={16} />}
          onClick={handlePreview}
          disabled={ui.loading}
        >
          Preview
        </Button>

        {!generated.id && (
          <Button
            variant="contained"
            startIcon={ui.loading ? <CircularProgress size={16} color="inherit" /> : <FileText size={16} />}
            onClick={handleGenerate}
            disabled={ui.loading}
            color="primary"
          >
            Generate Document
          </Button>
        )}
      </Box>

      {/* Generated Document Info */}
      {generated.id && (
        <Alert
          severity="success"
          sx={{ mb: 2 }}
          action={
            <Button
              size="small"
              startIcon={<FileDown size={14} />}
              href={generated.downloadUrl || '#'}
              color="inherit"
            >
              Download DOCX
            </Button>
          }
        >
          <AlertTitle>Document Generated</AlertTitle>
          {generated.wordCount} words, {generated.pageCount} pages, {generated.clauseCount} clauses
        </Alert>
      )}
    </Box>
  )
}

export default ReviewGenerate
