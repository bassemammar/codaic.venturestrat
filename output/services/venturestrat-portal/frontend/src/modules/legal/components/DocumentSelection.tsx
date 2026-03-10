/**
 * Step 1: DocumentSelection — Choose document type (Mutual NDA, One-Way NDA).
 */

import React from 'react'
import {
  Box,
  Card,
  CardActionArea,
  CardContent,
  Typography,
  Grid,
  Chip,
} from '@mui/material'
import { Shield, FileText } from 'lucide-react'
import { useWizardStore, useDocumentType } from '../../../stores/legal-wizard-store'

const DOCUMENT_TYPES = [
  {
    id: 'mutual_nda',
    title: 'Mutual NDA',
    description: 'Both parties agree to keep shared information confidential. Suitable for business collaborations, partnerships, and joint ventures.',
    icon: Shield,
    available: true,
  },
  {
    id: 'one_way_nda',
    title: 'One-Way NDA',
    description: 'One party discloses confidential information to the other. Suitable for investor discussions, contractor engagements, and vendor evaluations.',
    icon: FileText,
    available: false,
  },
]

const DocumentSelection: React.FC = () => {
  const documentType = useDocumentType()
  const { setDocumentType, nextStep, setTitle } = useWizardStore()

  const handleSelect = (typeId: string) => {
    setDocumentType(typeId)
    const doc = DOCUMENT_TYPES.find(d => d.id === typeId)
    if (doc) {
      setTitle(doc.title)
    }
    nextStep()
  }

  return (
    <Box>
      <Typography variant="h6" fontWeight={600} sx={{ mb: 1 }}>
        Select Document Type
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Choose the type of legal document you want to generate.
      </Typography>

      <Grid container spacing={3}>
        {DOCUMENT_TYPES.map((doc) => (
          <Grid size={{ xs: 12, sm: 6 }} key={doc.id}>
            <Card
              variant="outlined"
              sx={{
                borderColor: documentType === doc.id ? 'primary.main' : '#e5e7eb',
                borderWidth: documentType === doc.id ? 2 : 1,
                opacity: doc.available ? 1 : 0.5,
                transition: 'border-color 0.2s',
              }}
            >
              <CardActionArea
                onClick={() => doc.available && handleSelect(doc.id)}
                disabled={!doc.available}
                sx={{ p: 1 }}
              >
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2 }}>
                    <doc.icon size={28} color={doc.available ? '#4f7df9' : '#9ca3af'} />
                    <Typography variant="h6" fontWeight={600}>
                      {doc.title}
                    </Typography>
                    {!doc.available && (
                      <Chip label="Coming Soon" size="small" color="default" />
                    )}
                  </Box>
                  <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.7 }}>
                    {doc.description}
                  </Typography>
                </CardContent>
              </CardActionArea>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  )
}

export default DocumentSelection
