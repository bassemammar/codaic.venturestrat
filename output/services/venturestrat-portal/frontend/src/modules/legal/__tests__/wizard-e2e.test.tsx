/**
 * E2E-style test: Full document generation flow through the wizard store.
 *
 * Simulates: select NDA → select parties → configure clauses → preview → generate → download.
 * Uses the store directly (no HTTP calls) to verify the full state flow.
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { useWizardStore, DEFAULT_NDA_CONFIG, STEP_LABELS } from '../../../stores/legal-wizard-store'

beforeEach(() => {
  useWizardStore.getState().reset()
})

describe('Full Document Generation Flow', () => {
  it('completes full wizard flow from type selection to generation', () => {
    const store = useWizardStore

    // Step 0: Select document type
    expect(store.getState().currentStep).toBe(0)
    expect(store.getState().canGoNext()).toBe(false)

    store.getState().setDocumentType('mutual_nda')
    expect(store.getState().canGoNext()).toBe(true)
    store.getState().nextStep()

    // Step 1: Select parties
    expect(store.getState().currentStep).toBe(1)
    expect(store.getState().canGoNext()).toBe(false)

    store.getState().setPartyA({
      companyId: 'acme-uuid',
      companyName: 'Acme Corporation Ltd',
      signatoryId: 'jane-uuid',
      signatoryName: 'Jane Doe',
    })
    expect(store.getState().canGoNext()).toBe(false) // need both parties

    store.getState().setPartyB({
      companyId: 'beta-uuid',
      companyName: 'Beta Technologies Inc',
      signatoryId: 'john-uuid',
      signatoryName: 'John Smith',
    })
    expect(store.getState().canGoNext()).toBe(true)
    store.getState().nextStep()

    // Step 2: Configure NDA
    expect(store.getState().currentStep).toBe(2)

    store.getState().setConfiguration({
      purpose: 'To explore joint AI research collaboration',
      purposeOption: 'B',
      personalDataSharing: 'A',
      agreementDuration: 'B', // 3 years
      confidentialitySurvival: 'C', // 5 years
      permittedRecipients: 'B',
      returnOrDestruction: 'B',
      aiMlRestrictions: 'A', // Full prohibition
      governingLaw: 'england_wales',
      disputeResolution: 'C', // LCIA
      nonSolicitation: 'A',
    })
    store.getState().toggleAdditionalClause('no_partnership')
    store.getState().toggleAdditionalClause('no_obligation')

    const config = store.getState().configuration
    expect(config.agreementDuration).toBe('B')
    expect(config.aiMlRestrictions).toBe('A')
    expect(config.additionalClauses).toContain('no_partnership')
    expect(config.additionalClauses).toContain('no_obligation')
    expect(config.additionalClauses).toHaveLength(2)

    store.getState().nextStep()

    // Step 3: Review & Generate
    expect(store.getState().currentStep).toBe(3)

    // Simulate preview result
    store.getState().setPreviewContent('# Mutual Non-Disclosure Agreement\n\n...')
    expect(store.getState().ui.previewContent).toContain('Mutual Non-Disclosure Agreement')

    // Simulate validation
    store.getState().setValidation({
      valid: true,
      errors: [],
      warnings: [],
    })
    expect(store.getState().validation.valid).toBe(true)

    // Simulate generation result
    store.getState().setGeneratedDocument({
      id: 'doc-uuid-123',
      downloadUrl: '/api/v1/documents/doc-uuid-123/download?format=docx',
      previewUrl: '/api/v1/documents/doc-uuid-123/download?format=md',
      wordCount: 980,
      pageCount: 4,
      clauseCount: 14,
    })

    const generated = store.getState().generatedDocument
    expect(generated.id).toBe('doc-uuid-123')
    expect(generated.downloadUrl).toContain('download')
    expect(generated.wordCount).toBe(980)
    expect(generated.pageCount).toBe(4)

    // Verify all state is consistent
    expect(store.getState().documentType).toBe('mutual_nda')
    expect(store.getState().partyA.companyName).toBe('Acme Corporation Ltd')
    expect(store.getState().partyB.companyName).toBe('Beta Technologies Inc')
  })

  it('handles validation errors in flow', () => {
    const store = useWizardStore

    store.getState().setDocumentType('mutual_nda')
    store.getState().nextStep()
    store.getState().setPartyA({ companyId: 'a' })
    store.getState().setPartyB({ companyId: 'b' })
    store.getState().nextStep()
    store.getState().nextStep()

    // Step 3: Validation returns errors
    store.getState().setValidation({
      valid: false,
      errors: [
        {
          ruleId: '2.1',
          severity: 'CRITICAL',
          message: 'Total equity exceeds 100%',
          field: 'percentage',
          blocking: true,
        },
      ],
      warnings: [
        {
          ruleId: '1.3',
          severity: 'HIGH',
          message: 'Duplicate founder email',
          field: 'email',
          blocking: false,
        },
      ],
    })

    expect(store.getState().validation.valid).toBe(false)
    expect(store.getState().validation.errors).toHaveLength(1)
    expect(store.getState().validation.warnings).toHaveLength(1)
    expect(store.getState().validation.errors[0].blocking).toBe(true)
  })

  it('supports reset and restart', () => {
    const store = useWizardStore

    // Go through flow
    store.getState().setDocumentType('mutual_nda')
    store.getState().nextStep()
    store.getState().setPartyA({ companyId: 'a', companyName: 'Alpha' })
    store.getState().setPartyB({ companyId: 'b', companyName: 'Beta' })
    store.getState().nextStep()
    store.getState().setConfigField('agreementDuration', 'D')
    store.getState().nextStep()
    store.getState().setGeneratedDocument({ id: 'doc-1' })

    // Reset keeping type
    store.getState().resetKeepType()
    expect(store.getState().documentType).toBe('mutual_nda')
    expect(store.getState().currentStep).toBe(1) // back to party selection
    expect(store.getState().partyA.companyId).toBeNull()
    expect(store.getState().generatedDocument.id).toBeNull()
    expect(store.getState().configuration.agreementDuration).toBe(DEFAULT_NDA_CONFIG.agreementDuration)

    // Full reset
    store.getState().reset()
    expect(store.getState().documentType).toBeNull()
    expect(store.getState().currentStep).toBe(0)
  })

  it('handles loading states correctly', () => {
    const store = useWizardStore

    expect(store.getState().ui.loading).toBe(false)
    store.getState().setLoading(true)
    expect(store.getState().ui.loading).toBe(true)
    store.getState().setLoading(false)
    expect(store.getState().ui.loading).toBe(false)
  })

  it('handles error states correctly', () => {
    const store = useWizardStore

    expect(store.getState().ui.error).toBeNull()
    store.getState().setError('Network timeout')
    expect(store.getState().ui.error).toBe('Network timeout')
    store.getState().setError(null)
    expect(store.getState().ui.error).toBeNull()
  })
})
