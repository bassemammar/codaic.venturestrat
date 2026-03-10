import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { useWizardStore, INITIAL_STATE } from '../../../stores/legal-wizard-store'
import DocumentSelection from '../components/DocumentSelection'
import NDAConfigurationForm from '../components/NDAConfigurationForm'
import ReviewGenerate from '../components/ReviewGenerate'
import WizardLayout from '../components/WizardLayout'

// Reset store before each test
beforeEach(() => {
  useWizardStore.getState().reset()
})

describe('DocumentSelection', () => {
  it('renders document type cards', () => {
    render(<DocumentSelection />)
    expect(screen.getByText('Mutual NDA')).toBeDefined()
    expect(screen.getByText('One-Way NDA')).toBeDefined()
  })

  it('renders descriptions', () => {
    render(<DocumentSelection />)
    expect(screen.getByText(/Both parties agree/i)).toBeDefined()
  })

  it('shows Coming Soon for unavailable types', () => {
    render(<DocumentSelection />)
    expect(screen.getByText('Coming Soon')).toBeDefined()
  })

  it('sets document type on click', () => {
    render(<DocumentSelection />)
    fireEvent.click(screen.getByText('Mutual NDA'))
    expect(useWizardStore.getState().documentType).toBe('mutual_nda')
  })

  it('advances to next step on click', () => {
    render(<DocumentSelection />)
    fireEvent.click(screen.getByText('Mutual NDA'))
    expect(useWizardStore.getState().currentStep).toBe(1)
  })
})

describe('NDAConfigurationForm', () => {
  it('renders all clause sections', () => {
    render(<NDAConfigurationForm />)
    expect(screen.getByText('1. Purpose Clause')).toBeDefined()
    expect(screen.getByText('2. Data Protection')).toBeDefined()
    expect(screen.getByText('3. Agreement Duration')).toBeDefined()
    expect(screen.getByText(/4\. Confidentiality/)).toBeDefined()
    expect(screen.getByText(/5\. Permitted/)).toBeDefined()
    expect(screen.getByText(/6\. Return/)).toBeDefined()
    expect(screen.getByText(/7\. AI\/ML/)).toBeDefined()
    expect(screen.getByText('8. Governing Law')).toBeDefined()
    expect(screen.getByText('9. Dispute Resolution')).toBeDefined()
    expect(screen.getByText('10. Non-Solicitation')).toBeDefined()
    expect(screen.getByText(/11\. Additional/)).toBeDefined()
  })

  it('renders purpose text field', () => {
    render(<NDAConfigurationForm />)
    expect(screen.getByLabelText('Purpose Description')).toBeDefined()
  })

  it('renders additional clause checkboxes', () => {
    render(<NDAConfigurationForm />)
    expect(screen.getByText(/No Partnership/)).toBeDefined()
    expect(screen.getByText(/Publicity Restrictions/)).toBeDefined()
  })
})

describe('ReviewGenerate', () => {
  it('renders review heading', () => {
    render(<ReviewGenerate />)
    expect(screen.getByText('Review & Generate')).toBeDefined()
  })

  it('renders preview button', () => {
    render(<ReviewGenerate />)
    expect(screen.getByText('Preview')).toBeDefined()
  })

  it('renders generate button', () => {
    render(<ReviewGenerate />)
    expect(screen.getByText('Generate Document')).toBeDefined()
  })

  it('shows preview content when available', () => {
    useWizardStore.getState().setPreviewContent('# Test NDA Preview')
    render(<ReviewGenerate />)
    expect(screen.getByText('# Test NDA Preview')).toBeDefined()
  })

  it('shows generated document success alert', () => {
    useWizardStore.getState().setGeneratedDocument({
      id: 'test-123',
      downloadUrl: '/download/test-123',
      wordCount: 500,
      pageCount: 2,
      clauseCount: 10,
    })
    render(<ReviewGenerate />)
    expect(screen.getByText('Document Generated')).toBeDefined()
    expect(screen.getByText(/500 words/)).toBeDefined()
    expect(screen.getByText('Download DOCX')).toBeDefined()
  })

  it('shows validation errors', () => {
    useWizardStore.getState().setValidation({
      valid: false,
      errors: [{
        ruleId: '2.1',
        severity: 'CRITICAL',
        message: 'Total equity exceeds 100%',
        field: 'percentage',
        blocking: true,
      }],
    })
    render(<ReviewGenerate />)
    expect(screen.getByText('Validation Errors')).toBeDefined()
    expect(screen.getByText('Total equity exceeds 100%')).toBeDefined()
  })

  it('shows validation warnings', () => {
    useWizardStore.getState().setValidation({
      valid: true,
      warnings: [{
        ruleId: '1.3',
        severity: 'HIGH',
        message: 'Duplicate email found',
        field: 'email',
        blocking: false,
      }],
    })
    render(<ReviewGenerate />)
    expect(screen.getByText('Warnings')).toBeDefined()
    expect(screen.getByText('Duplicate email found')).toBeDefined()
  })

  it('shows error message from UI state', () => {
    useWizardStore.getState().setError('Network error')
    render(<ReviewGenerate />)
    expect(screen.getByText('Network error')).toBeDefined()
  })
})

describe('WizardLayout', () => {
  it('renders step labels', () => {
    render(<WizardLayout>Content</WizardLayout>)
    expect(screen.getByText('Document Type')).toBeDefined()
    expect(screen.getByText('Select Parties')).toBeDefined()
    expect(screen.getByText('Configure NDA')).toBeDefined()
    expect(screen.getByText('Review & Generate')).toBeDefined()
  })

  it('renders children content', () => {
    render(<WizardLayout><div>Step Content</div></WizardLayout>)
    expect(screen.getByText('Step Content')).toBeDefined()
  })

  it('shows step counter', () => {
    render(<WizardLayout>Content</WizardLayout>)
    expect(screen.getByText('Step 1 of 4')).toBeDefined()
  })

  it('disables Back at step 0', () => {
    render(<WizardLayout>Content</WizardLayout>)
    const backBtn = screen.getByText('Back')
    expect(backBtn.closest('button')?.disabled).toBe(true)
  })

  it('shows Generate button at last step', () => {
    useWizardStore.getState().goToStep(3)
    render(<WizardLayout>Content</WizardLayout>)
    expect(screen.getByText('Generate')).toBeDefined()
  })

  it('shows Next button at non-last steps', () => {
    render(<WizardLayout>Content</WizardLayout>)
    expect(screen.getByText('Next')).toBeDefined()
  })
})
