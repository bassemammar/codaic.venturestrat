/**
 * Legal Wizard Store — Zustand with Immer + Persist.
 *
 * Manages the 4-step NDA generation wizard state:
 * Step 0: Document type selection
 * Step 1: Entity (party) selection
 * Step 2: NDA configuration form
 * Step 3: Review & generate
 */

import { create } from 'zustand'
import { immer } from 'zustand/middleware/immer'
import { persist } from 'zustand/middleware'

// --- Types ---

export interface PartySelection {
  companyId: string | null
  companyName: string | null
  signatoryId: string | null
  signatoryName: string | null
}

export interface NdaConfiguration {
  purpose: string
  purposeOption: string
  personalDataSharing: string
  agreementDuration: string
  confidentialitySurvival: string
  permittedRecipients: string
  returnOrDestruction: string
  aiMlRestrictions: string
  governingLaw: string
  disputeResolution: string
  nonSolicitation: string
  additionalClauses: string[]
}

export interface GeneratedDocument {
  id: string | null
  downloadUrl: string | null
  previewUrl: string | null
  wordCount: number
  pageCount: number
  clauseCount: number
}

export interface ValidationState {
  valid: boolean
  errors: Array<{
    ruleId: string
    severity: string
    message: string
    field: string
    blocking: boolean
  }>
  warnings: Array<{
    ruleId: string
    severity: string
    message: string
    field: string
    blocking: boolean
  }>
}

export interface UiState {
  loading: boolean
  error: string | null
  previewContent: string | null
}

export interface WizardState {
  currentStep: number
  documentType: string | null
  title: string
  partyA: PartySelection
  partyB: PartySelection
  configuration: NdaConfiguration
  generatedDocument: GeneratedDocument
  validation: ValidationState
  ui: UiState
}

// --- Default Values ---

export const DEFAULT_NDA_CONFIG: NdaConfiguration = {
  purpose: '',
  purposeOption: 'B',
  personalDataSharing: 'A',
  agreementDuration: 'A',
  confidentialitySurvival: 'A',
  permittedRecipients: 'B',
  returnOrDestruction: 'B',
  aiMlRestrictions: 'A',
  governingLaw: 'england_wales',
  disputeResolution: 'C',
  nonSolicitation: 'A',
  additionalClauses: [],
}

const EMPTY_PARTY: PartySelection = {
  companyId: null,
  companyName: null,
  signatoryId: null,
  signatoryName: null,
}

const EMPTY_GENERATED: GeneratedDocument = {
  id: null,
  downloadUrl: null,
  previewUrl: null,
  wordCount: 0,
  pageCount: 0,
  clauseCount: 0,
}

const EMPTY_VALIDATION: ValidationState = {
  valid: true,
  errors: [],
  warnings: [],
}

const EMPTY_UI: UiState = {
  loading: false,
  error: null,
  previewContent: null,
}

export const INITIAL_STATE: WizardState = {
  currentStep: 0,
  documentType: null,
  title: '',
  partyA: { ...EMPTY_PARTY },
  partyB: { ...EMPTY_PARTY },
  configuration: { ...DEFAULT_NDA_CONFIG },
  generatedDocument: { ...EMPTY_GENERATED },
  validation: { ...EMPTY_VALIDATION },
  ui: { ...EMPTY_UI },
}

export const STEP_LABELS = [
  'Document Type',
  'Select Parties',
  'Configure NDA',
  'Review & Generate',
]

// --- Actions Interface ---

export interface WizardActions {
  // Navigation
  nextStep: () => void
  prevStep: () => void
  goToStep: (step: number) => void
  canGoNext: () => boolean
  canGoBack: () => boolean

  // Document type
  setDocumentType: (type: string) => void

  // Title
  setTitle: (title: string) => void

  // Party selection
  setPartyA: (party: Partial<PartySelection>) => void
  setPartyB: (party: Partial<PartySelection>) => void
  clearPartyA: () => void
  clearPartyB: () => void
  swapParties: () => void

  // Configuration
  setConfigField: (field: keyof NdaConfiguration, value: string | string[]) => void
  setConfiguration: (config: Partial<NdaConfiguration>) => void
  resetConfiguration: () => void
  toggleAdditionalClause: (clause: string) => void

  // Generation
  setGeneratedDocument: (doc: Partial<GeneratedDocument>) => void
  clearGeneratedDocument: () => void

  // Validation
  setValidation: (validation: Partial<ValidationState>) => void
  clearValidation: () => void

  // UI
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  setPreviewContent: (content: string | null) => void

  // Reset
  reset: () => void
  resetKeepType: () => void
}

// --- Store ---

export const useWizardStore = create<WizardState & WizardActions>()(
  persist(
    immer((set, get) => ({
      ...INITIAL_STATE,

      // Navigation
      nextStep: () => set(s => {
        if (s.currentStep < STEP_LABELS.length - 1) {
          s.currentStep += 1
        }
      }),
      prevStep: () => set(s => {
        if (s.currentStep > 0) {
          s.currentStep -= 1
        }
      }),
      goToStep: (step: number) => set(s => {
        if (step >= 0 && step < STEP_LABELS.length) {
          s.currentStep = step
        }
      }),
      canGoNext: () => {
        const s = get()
        if (s.currentStep === 0) return s.documentType !== null
        if (s.currentStep === 1) return s.partyA.companyId !== null && s.partyB.companyId !== null
        if (s.currentStep === 2) return true
        return false
      },
      canGoBack: () => get().currentStep > 0,

      // Document type
      setDocumentType: (type: string) => set(s => {
        s.documentType = type
      }),

      // Title
      setTitle: (title: string) => set(s => {
        s.title = title
      }),

      // Party selection
      setPartyA: (party: Partial<PartySelection>) => set(s => {
        Object.assign(s.partyA, party)
      }),
      setPartyB: (party: Partial<PartySelection>) => set(s => {
        Object.assign(s.partyB, party)
      }),
      clearPartyA: () => set(s => {
        s.partyA = { ...EMPTY_PARTY }
      }),
      clearPartyB: () => set(s => {
        s.partyB = { ...EMPTY_PARTY }
      }),
      swapParties: () => set(s => {
        const temp = { ...s.partyA }
        s.partyA = { ...s.partyB }
        s.partyB = temp
      }),

      // Configuration
      setConfigField: (field, value) => set(s => {
        (s.configuration as Record<string, unknown>)[field] = value
      }),
      setConfiguration: (config: Partial<NdaConfiguration>) => set(s => {
        Object.assign(s.configuration, config)
      }),
      resetConfiguration: () => set(s => {
        s.configuration = { ...DEFAULT_NDA_CONFIG }
      }),
      toggleAdditionalClause: (clause: string) => set(s => {
        const idx = s.configuration.additionalClauses.indexOf(clause)
        if (idx >= 0) {
          s.configuration.additionalClauses.splice(idx, 1)
        } else {
          s.configuration.additionalClauses.push(clause)
        }
      }),

      // Generation
      setGeneratedDocument: (doc: Partial<GeneratedDocument>) => set(s => {
        Object.assign(s.generatedDocument, doc)
      }),
      clearGeneratedDocument: () => set(s => {
        s.generatedDocument = { ...EMPTY_GENERATED }
      }),

      // Validation
      setValidation: (validation: Partial<ValidationState>) => set(s => {
        Object.assign(s.validation, validation)
      }),
      clearValidation: () => set(s => {
        s.validation = { ...EMPTY_VALIDATION }
      }),

      // UI
      setLoading: (loading: boolean) => set(s => {
        s.ui.loading = loading
      }),
      setError: (error: string | null) => set(s => {
        s.ui.error = error
      }),
      setPreviewContent: (content: string | null) => set(s => {
        s.ui.previewContent = content
      }),

      // Reset
      reset: () => set(() => ({ ...INITIAL_STATE })),
      resetKeepType: () => set(s => {
        const type = s.documentType
        Object.assign(s, { ...INITIAL_STATE, documentType: type, currentStep: 1 })
      }),
    })),
    {
      name: 'legal-wizard-state',
      partialize: (state) => ({
        currentStep: state.currentStep,
        documentType: state.documentType,
        title: state.title,
        partyA: state.partyA,
        partyB: state.partyB,
        configuration: state.configuration,
      }),
    }
  )
)

// --- Selector Hooks ---

export const useCurrentStep = () => useWizardStore(s => s.currentStep)
export const useDocumentType = () => useWizardStore(s => s.documentType)
export const usePartyA = () => useWizardStore(s => s.partyA)
export const usePartyB = () => useWizardStore(s => s.partyB)
export const useConfiguration = () => useWizardStore(s => s.configuration)
export const useGeneratedDocument = () => useWizardStore(s => s.generatedDocument)
export const useValidation = () => useWizardStore(s => s.validation)
export const useWizardUi = () => useWizardStore(s => s.ui)
export const useWizardLoading = () => useWizardStore(s => s.ui.loading)
