/**
 * Step 2: EntitySelection — Select Party A and Party B.
 *
 * Each party has a company Autocomplete and a signatory Autocomplete.
 * Company list comes from the legal_entity API; signatories from contact_person
 * filtered by the selected entity.
 */

import React, { useState, useEffect, useCallback } from 'react'
import {
  Box,
  Typography,
  TextField,
  Autocomplete,
  Paper,
  Button,
  Alert,
  CircularProgress,
} from '@mui/material'
import { Building2, User, ArrowLeftRight } from 'lucide-react'
import {
  useWizardStore,
  usePartyA,
  usePartyB,
  type PartySelection,
} from '../../../stores/legal-wizard-store'

interface CompanyOption {
  id: string
  label: string
  registrationNumber: string
  jurisdiction: string
}

interface PersonOption {
  id: string
  label: string
  role: string
  legalEntityId: string | null
}

const TENANT_ID = localStorage.getItem('tenant_id') || '00000000-0000-0000-0000-000000000000'
const AUTH_TOKEN = localStorage.getItem('auth_token') || ''

async function fetchJson<T>(url: string): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'X-Tenant-ID': TENANT_ID,
  }
  if (AUTH_TOKEN) headers['Authorization'] = `Bearer ${AUTH_TOKEN}`
  const resp = await fetch(url, { headers })
  if (!resp.ok) throw new Error(`API error ${resp.status}`)
  return resp.json()
}

interface PartySectionProps {
  label: string
  party: PartySelection
  onSetParty: (party: Partial<PartySelection>) => void
  onClear: () => void
  companies: CompanyOption[]
  persons: PersonOption[]
  loadingCompanies?: boolean
  loadingPersons?: boolean
}

const PartySection: React.FC<PartySectionProps> = ({
  label,
  party,
  onSetParty,
  onClear,
  companies,
  persons,
  loadingCompanies,
  loadingPersons,
}) => {
  const selectedCompany = companies.find(c => c.id === party.companyId) || null
  const filteredPersons = party.companyId
    ? persons.filter(p => p.legalEntityId === party.companyId)
    : []
  const selectedPerson = filteredPersons.find(p => p.id === party.signatoryId) || null

  return (
    <Paper variant="outlined" sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
        <Building2 size={20} color="#4f7df9" />
        <Typography variant="subtitle1" fontWeight={600}>
          {label}
        </Typography>
      </Box>

      <Autocomplete
        options={companies}
        value={selectedCompany}
        loading={loadingCompanies}
        getOptionLabel={(opt) => opt.label}
        isOptionEqualToValue={(opt, val) => opt.id === val.id}
        onChange={(_, value) => {
          if (value) {
            onSetParty({ companyId: value.id, companyName: value.label })
          } else {
            onClear()
          }
        }}
        renderInput={(params) => (
          <TextField
            {...params}
            label="Company / Legal Entity"
            placeholder="Search entities..."
            size="small"
          />
        )}
        renderOption={(props, option) => (
          <li {...props} key={option.id}>
            <Box>
              <Typography variant="body2">{option.label}</Typography>
              <Typography variant="caption" color="text.secondary">
                {option.registrationNumber} — {option.jurisdiction}
              </Typography>
            </Box>
          </li>
        )}
        sx={{ mb: 2 }}
      />

      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
        <User size={16} color="#6b7280" />
        <Typography variant="body2" color="text.secondary">
          Signatory (optional)
        </Typography>
      </Box>

      <Autocomplete
        options={filteredPersons}
        value={selectedPerson}
        loading={loadingPersons}
        disabled={!party.companyId}
        getOptionLabel={(opt) => opt.label}
        isOptionEqualToValue={(opt, val) => opt.id === val.id}
        onChange={(_, value) => {
          onSetParty({
            signatoryId: value?.id || null,
            signatoryName: value?.label || null,
          })
        }}
        renderInput={(params) => (
          <TextField
            {...params}
            label="Signatory Person"
            placeholder={party.companyId ? 'Select signatory...' : 'Select a company first'}
            size="small"
          />
        )}
        renderOption={(props, option) => (
          <li {...props} key={option.id}>
            <Box>
              <Typography variant="body2">{option.label}</Typography>
              <Typography variant="caption" color="text.secondary">
                {option.role}
              </Typography>
            </Box>
          </li>
        )}
        noOptionsText={
          party.companyId
            ? 'No contacts for this entity'
            : 'Select a company first'
        }
      />
    </Paper>
  )
}

const EntitySelection: React.FC = () => {
  const partyA = usePartyA()
  const partyB = usePartyB()
  const { setPartyA, setPartyB, clearPartyA, clearPartyB, swapParties } = useWizardStore()

  const [companies, setCompanies] = useState<CompanyOption[]>([])
  const [persons, setPersons] = useState<PersonOption[]>([])
  const [loadingCompanies, setLoadingCompanies] = useState(false)
  const [loadingPersons, setLoadingPersons] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadCompanies = useCallback(async () => {
    setLoadingCompanies(true)
    setError(null)
    try {
      const data = await fetchJson<any[]>('/api/v1/legal-entities/?page_size=200')
      const items = Array.isArray(data) ? data : (data as any).items || (data as any).legal_entities || []
      setCompanies(
        items.map((e: any) => ({
          id: e.id,
          label: e.legal_name,
          registrationNumber: e.registration_number || '',
          jurisdiction: e.jurisdiction || '',
        }))
      )
    } catch (err) {
      setError('Failed to load legal entities')
    } finally {
      setLoadingCompanies(false)
    }
  }, [])

  const loadPersons = useCallback(async () => {
    setLoadingPersons(true)
    try {
      const data = await fetchJson<any[]>('/api/v1/contact-persons/?page_size=200')
      const items = Array.isArray(data) ? data : (data as any).items || (data as any).contact_persons || []
      setPersons(
        items.map((p: any) => ({
          id: p.id,
          label: `${p.full_name} — ${p.role}`,
          role: p.role,
          legalEntityId: p.legal_entity_id,
        }))
      )
    } catch {
      // Non-critical — persons are optional
    } finally {
      setLoadingPersons(false)
    }
  }, [])

  useEffect(() => {
    loadCompanies()
    loadPersons()
  }, [loadCompanies, loadPersons])

  const sameCompany = partyA.companyId && partyB.companyId && partyA.companyId === partyB.companyId

  return (
    <Box>
      <Typography variant="h6" fontWeight={600} sx={{ mb: 1 }}>
        Select Parties
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Choose the two parties for this agreement. Each party needs a company and optionally a signatory.
      </Typography>

      {error && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          {error} — You can still proceed with manual entry.
        </Alert>
      )}

      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        <PartySection
          label="Party A"
          party={partyA}
          onSetParty={setPartyA}
          onClear={clearPartyA}
          companies={companies}
          persons={persons}
          loadingCompanies={loadingCompanies}
          loadingPersons={loadingPersons}
        />

        <Box sx={{ display: 'flex', justifyContent: 'center' }}>
          <Button
            size="small"
            startIcon={<ArrowLeftRight size={14} />}
            onClick={swapParties}
            disabled={!partyA.companyId && !partyB.companyId}
          >
            Swap Parties
          </Button>
        </Box>

        <PartySection
          label="Party B"
          party={partyB}
          onSetParty={setPartyB}
          onClear={clearPartyB}
          companies={companies}
          persons={persons}
          loadingCompanies={loadingCompanies}
          loadingPersons={loadingPersons}
        />
      </Box>

      {sameCompany && (
        <Alert severity="warning" sx={{ mt: 2 }}>
          Party A and Party B cannot be the same entity.
        </Alert>
      )}
    </Box>
  )
}

export default EntitySelection
