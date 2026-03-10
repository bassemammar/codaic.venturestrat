/**
 * LegalWizardPage — Main page for the NDA generation wizard.
 *
 * Renders the WizardLayout with the appropriate step component
 * based on the current wizard step.
 */

import React from 'react'
import { Box, Typography, Button } from '@mui/material'
import { Scale, RotateCcw } from 'lucide-react'
import { useCurrentStep, useWizardStore, useGeneratedDocument } from '../../../stores/legal-wizard-store'
import WizardLayout from '../components/WizardLayout'
import DocumentSelection from '../components/DocumentSelection'
import EntitySelection from '../components/EntitySelection'
import NDAConfigurationForm from '../components/NDAConfigurationForm'
import ReviewGenerate from '../components/ReviewGenerate'

const STEP_COMPONENTS = [
  DocumentSelection,
  EntitySelection,
  NDAConfigurationForm,
  ReviewGenerate,
]

const LegalWizardPage: React.FC = () => {
  const currentStep = useCurrentStep()
  const generated = useGeneratedDocument()
  const { reset } = useWizardStore()
  const StepComponent = STEP_COMPONENTS[currentStep]

  return (
    <Box sx={{ py: 2 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2, px: 2 }}>
        <Scale size={24} color="#7c3aed" />
        <Typography variant="h5" fontWeight={700} sx={{ color: '#374151', flex: 1 }}>
          Legal Document Wizard
        </Typography>
        {(currentStep > 0 || generated.id) && (
          <Button
            size="small"
            variant="outlined"
            startIcon={<RotateCcw size={14} />}
            onClick={reset}
            sx={{ textTransform: 'none' }}
          >
            New Document
          </Button>
        )}
      </Box>

      <WizardLayout>
        <StepComponent />
      </WizardLayout>
    </Box>
  )
}

export default LegalWizardPage
