/**
 * WizardLayout — MUI Stepper shell for the 4-step NDA wizard.
 *
 * Renders step labels, navigation buttons (Back/Next/Generate),
 * and the active step content via children.
 */

import React from 'react'
import {
  Box,
  Stepper,
  Step,
  StepLabel,
  Button,
  Paper,
  Typography,
  LinearProgress,
} from '@mui/material'
import { ArrowLeft, ArrowRight, FileDown } from 'lucide-react'
import {
  useWizardStore,
  useCurrentStep,
  useWizardLoading,
  STEP_LABELS,
} from '../../../stores/legal-wizard-store'

interface WizardLayoutProps {
  children: React.ReactNode
  onGenerate?: () => void
}

const WizardLayout: React.FC<WizardLayoutProps> = ({ children, onGenerate }) => {
  const currentStep = useCurrentStep()
  const loading = useWizardLoading()
  const { nextStep, prevStep, canGoNext, canGoBack } = useWizardStore()

  const isLastStep = currentStep === STEP_LABELS.length - 1
  const progress = ((currentStep + 1) / STEP_LABELS.length) * 100

  return (
    <Box sx={{ maxWidth: 900, mx: 'auto', py: 3 }}>
      <Paper
        elevation={0}
        sx={{
          border: '1px solid #e5e7eb',
          borderRadius: 2,
          overflow: 'hidden',
        }}
      >
        {/* Progress bar */}
        <LinearProgress
          variant="determinate"
          value={progress}
          sx={{ height: 4 }}
        />

        {/* Stepper */}
        <Box sx={{ px: 4, pt: 3, pb: 2 }}>
          <Stepper activeStep={currentStep} alternativeLabel>
            {STEP_LABELS.map((label) => (
              <Step key={label}>
                <StepLabel>{label}</StepLabel>
              </Step>
            ))}
          </Stepper>
        </Box>

        {/* Step content */}
        <Box sx={{ px: 4, py: 3, minHeight: 400 }}>
          {loading && (
            <LinearProgress sx={{ mb: 2 }} />
          )}
          {children}
        </Box>

        {/* Navigation buttons */}
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            px: 4,
            py: 2,
            borderTop: '1px solid #e5e7eb',
            bgcolor: '#f9fafb',
          }}
        >
          <Button
            variant="outlined"
            startIcon={<ArrowLeft size={16} />}
            onClick={prevStep}
            disabled={!canGoBack() || loading}
          >
            Back
          </Button>

          <Typography variant="body2" color="text.secondary">
            Step {currentStep + 1} of {STEP_LABELS.length}
          </Typography>

          {isLastStep ? (
            <Button
              variant="contained"
              startIcon={<FileDown size={16} />}
              onClick={onGenerate}
              disabled={loading}
              color="primary"
            >
              Generate
            </Button>
          ) : (
            <Button
              variant="contained"
              endIcon={<ArrowRight size={16} />}
              onClick={nextStep}
              disabled={!canGoNext() || loading}
            >
              Next
            </Button>
          )}
        </Box>
      </Paper>
    </Box>
  )
}

export default WizardLayout
