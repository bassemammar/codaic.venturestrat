import { describe, it, expect, beforeEach } from 'vitest'
import { useWizardStore, INITIAL_STATE, DEFAULT_NDA_CONFIG, STEP_LABELS } from '../legal-wizard-store'

// Reset store before each test
beforeEach(() => {
  useWizardStore.getState().reset()
})

describe('Initial State', () => {
  it('starts at step 0', () => {
    expect(useWizardStore.getState().currentStep).toBe(0)
  })

  it('has no document type selected', () => {
    expect(useWizardStore.getState().documentType).toBeNull()
  })

  it('has empty parties', () => {
    const { partyA, partyB } = useWizardStore.getState()
    expect(partyA.companyId).toBeNull()
    expect(partyB.companyId).toBeNull()
  })

  it('has default NDA configuration', () => {
    const { configuration } = useWizardStore.getState()
    expect(configuration.purposeOption).toBe('B')
    expect(configuration.agreementDuration).toBe('A')
    expect(configuration.disputeResolution).toBe('C')
    expect(configuration.additionalClauses).toEqual([])
  })

  it('has 4 step labels', () => {
    expect(STEP_LABELS).toHaveLength(4)
  })
})

describe('Step Navigation', () => {
  it('increments step with nextStep', () => {
    useWizardStore.getState().nextStep()
    expect(useWizardStore.getState().currentStep).toBe(1)
  })

  it('decrements step with prevStep', () => {
    useWizardStore.getState().goToStep(2)
    useWizardStore.getState().prevStep()
    expect(useWizardStore.getState().currentStep).toBe(1)
  })

  it('does not go below 0', () => {
    useWizardStore.getState().prevStep()
    expect(useWizardStore.getState().currentStep).toBe(0)
  })

  it('does not exceed max step', () => {
    for (let i = 0; i < 10; i++) {
      useWizardStore.getState().nextStep()
    }
    expect(useWizardStore.getState().currentStep).toBe(STEP_LABELS.length - 1)
  })

  it('goToStep navigates directly', () => {
    useWizardStore.getState().goToStep(3)
    expect(useWizardStore.getState().currentStep).toBe(3)
  })

  it('goToStep ignores invalid steps', () => {
    useWizardStore.getState().goToStep(-1)
    expect(useWizardStore.getState().currentStep).toBe(0)
    useWizardStore.getState().goToStep(99)
    expect(useWizardStore.getState().currentStep).toBe(0)
  })

  it('canGoBack returns false at step 0', () => {
    expect(useWizardStore.getState().canGoBack()).toBe(false)
  })

  it('canGoBack returns true at step 1+', () => {
    useWizardStore.getState().goToStep(1)
    expect(useWizardStore.getState().canGoBack()).toBe(true)
  })

  it('canGoNext requires document type at step 0', () => {
    expect(useWizardStore.getState().canGoNext()).toBe(false)
    useWizardStore.getState().setDocumentType('mutual_nda')
    expect(useWizardStore.getState().canGoNext()).toBe(true)
  })

  it('canGoNext requires both parties at step 1', () => {
    useWizardStore.getState().setDocumentType('mutual_nda')
    useWizardStore.getState().goToStep(1)
    expect(useWizardStore.getState().canGoNext()).toBe(false)
    useWizardStore.getState().setPartyA({ companyId: 'id-a' })
    expect(useWizardStore.getState().canGoNext()).toBe(false)
    useWizardStore.getState().setPartyB({ companyId: 'id-b' })
    expect(useWizardStore.getState().canGoNext()).toBe(true)
  })
})

describe('Document Type', () => {
  it('sets document type', () => {
    useWizardStore.getState().setDocumentType('mutual_nda')
    expect(useWizardStore.getState().documentType).toBe('mutual_nda')
  })
})

describe('Party Selection', () => {
  it('sets party A fields', () => {
    useWizardStore.getState().setPartyA({
      companyId: 'company-1',
      companyName: 'Acme Corp',
    })
    const { partyA } = useWizardStore.getState()
    expect(partyA.companyId).toBe('company-1')
    expect(partyA.companyName).toBe('Acme Corp')
  })

  it('sets party B fields', () => {
    useWizardStore.getState().setPartyB({
      companyId: 'company-2',
      signatoryId: 'person-1',
      signatoryName: 'John Smith',
    })
    const { partyB } = useWizardStore.getState()
    expect(partyB.companyId).toBe('company-2')
    expect(partyB.signatoryId).toBe('person-1')
  })

  it('clears party A', () => {
    useWizardStore.getState().setPartyA({ companyId: 'x' })
    useWizardStore.getState().clearPartyA()
    expect(useWizardStore.getState().partyA.companyId).toBeNull()
  })

  it('clears party B', () => {
    useWizardStore.getState().setPartyB({ companyId: 'x' })
    useWizardStore.getState().clearPartyB()
    expect(useWizardStore.getState().partyB.companyId).toBeNull()
  })

  it('swaps parties', () => {
    useWizardStore.getState().setPartyA({ companyId: 'a', companyName: 'Alpha' })
    useWizardStore.getState().setPartyB({ companyId: 'b', companyName: 'Beta' })
    useWizardStore.getState().swapParties()
    expect(useWizardStore.getState().partyA.companyId).toBe('b')
    expect(useWizardStore.getState().partyB.companyId).toBe('a')
  })
})

describe('Configuration Updates', () => {
  it('sets individual config field', () => {
    useWizardStore.getState().setConfigField('purposeOption', 'C')
    expect(useWizardStore.getState().configuration.purposeOption).toBe('C')
  })

  it('sets multiple config fields', () => {
    useWizardStore.getState().setConfiguration({
      purposeOption: 'D',
      governingLaw: 'scotland',
    })
    const { configuration } = useWizardStore.getState()
    expect(configuration.purposeOption).toBe('D')
    expect(configuration.governingLaw).toBe('scotland')
  })

  it('resets configuration to defaults', () => {
    useWizardStore.getState().setConfigField('purposeOption', 'Z')
    useWizardStore.getState().resetConfiguration()
    expect(useWizardStore.getState().configuration.purposeOption).toBe(DEFAULT_NDA_CONFIG.purposeOption)
  })

  it('toggles additional clause on', () => {
    useWizardStore.getState().toggleAdditionalClause('no_partnership')
    expect(useWizardStore.getState().configuration.additionalClauses).toContain('no_partnership')
  })

  it('toggles additional clause off', () => {
    useWizardStore.getState().toggleAdditionalClause('no_partnership')
    useWizardStore.getState().toggleAdditionalClause('no_partnership')
    expect(useWizardStore.getState().configuration.additionalClauses).not.toContain('no_partnership')
  })

  it('handles multiple additional clauses', () => {
    useWizardStore.getState().toggleAdditionalClause('no_partnership')
    useWizardStore.getState().toggleAdditionalClause('publicity')
    const clauses = useWizardStore.getState().configuration.additionalClauses
    expect(clauses).toHaveLength(2)
    expect(clauses).toContain('no_partnership')
    expect(clauses).toContain('publicity')
  })
})

describe('Generated Document', () => {
  it('sets generated document fields', () => {
    useWizardStore.getState().setGeneratedDocument({
      id: 'doc-123',
      downloadUrl: '/download/doc-123',
      wordCount: 980,
    })
    const { generatedDocument } = useWizardStore.getState()
    expect(generatedDocument.id).toBe('doc-123')
    expect(generatedDocument.downloadUrl).toBe('/download/doc-123')
    expect(generatedDocument.wordCount).toBe(980)
  })

  it('clears generated document', () => {
    useWizardStore.getState().setGeneratedDocument({ id: 'doc-123' })
    useWizardStore.getState().clearGeneratedDocument()
    expect(useWizardStore.getState().generatedDocument.id).toBeNull()
  })
})

describe('Validation', () => {
  it('sets validation results', () => {
    useWizardStore.getState().setValidation({
      valid: false,
      errors: [{ ruleId: '2.1', severity: 'CRITICAL', message: 'Over 100%', field: 'percentage', blocking: true }],
    })
    const { validation } = useWizardStore.getState()
    expect(validation.valid).toBe(false)
    expect(validation.errors).toHaveLength(1)
  })

  it('clears validation', () => {
    useWizardStore.getState().setValidation({ valid: false })
    useWizardStore.getState().clearValidation()
    expect(useWizardStore.getState().validation.valid).toBe(true)
  })
})

describe('UI State', () => {
  it('sets loading', () => {
    useWizardStore.getState().setLoading(true)
    expect(useWizardStore.getState().ui.loading).toBe(true)
  })

  it('sets error', () => {
    useWizardStore.getState().setError('Something went wrong')
    expect(useWizardStore.getState().ui.error).toBe('Something went wrong')
  })

  it('sets preview content', () => {
    useWizardStore.getState().setPreviewContent('# NDA Preview')
    expect(useWizardStore.getState().ui.previewContent).toBe('# NDA Preview')
  })
})

describe('Reset', () => {
  it('resets all state', () => {
    useWizardStore.getState().setDocumentType('mutual_nda')
    useWizardStore.getState().goToStep(2)
    useWizardStore.getState().setPartyA({ companyId: 'x' })
    useWizardStore.getState().reset()

    const state = useWizardStore.getState()
    expect(state.currentStep).toBe(0)
    expect(state.documentType).toBeNull()
    expect(state.partyA.companyId).toBeNull()
  })

  it('resetKeepType preserves document type', () => {
    useWizardStore.getState().setDocumentType('mutual_nda')
    useWizardStore.getState().goToStep(2)
    useWizardStore.getState().setPartyA({ companyId: 'x' })
    useWizardStore.getState().resetKeepType()

    const state = useWizardStore.getState()
    expect(state.documentType).toBe('mutual_nda')
    expect(state.currentStep).toBe(1)
    expect(state.partyA.companyId).toBeNull()
  })
})

describe('Title', () => {
  it('sets title', () => {
    useWizardStore.getState().setTitle('NDA - Acme Corp')
    expect(useWizardStore.getState().title).toBe('NDA - Acme Corp')
  })
})
