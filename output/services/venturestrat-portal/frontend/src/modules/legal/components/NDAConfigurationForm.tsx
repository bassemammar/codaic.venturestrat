/**
 * Step 3: NDAConfigurationForm — 11 clause configuration questions.
 *
 * Each clause category has a RadioGroup (or Select/CheckboxGroup) for variant selection.
 */

import React from 'react'
import {
  Box,
  Typography,
  TextField,
  Radio,
  RadioGroup,
  FormControl,
  FormControlLabel,
  FormLabel,
  Select,
  MenuItem,
  Checkbox,
  FormGroup,
  Paper,
  Divider,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material'
import { ChevronDown } from 'lucide-react'
import { useWizardStore, useConfiguration } from '../../../stores/legal-wizard-store'

interface ClauseOption {
  value: string
  label: string
}

interface ClauseSectionProps {
  title: string
  description: string
  field: string
  options: ClauseOption[]
  value: string
  onChange: (value: string) => void
}

const ClauseSection: React.FC<ClauseSectionProps> = ({
  title,
  description,
  field,
  options,
  value,
  onChange,
}) => (
  <Box sx={{ mb: 3 }}>
    <FormControl component="fieldset" fullWidth>
      <FormLabel sx={{ fontWeight: 600, color: '#374151', mb: 0.5 }}>
        {title}
      </FormLabel>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
        {description}
      </Typography>
      <RadioGroup value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map((opt) => (
          <FormControlLabel
            key={opt.value}
            value={opt.value}
            control={<Radio size="small" />}
            label={
              <Typography variant="body2">
                <strong>Option {opt.value}:</strong> {opt.label}
              </Typography>
            }
          />
        ))}
      </RadioGroup>
    </FormControl>
  </Box>
)

const NDAConfigurationForm: React.FC = () => {
  const config = useConfiguration()
  const { setConfigField, toggleAdditionalClause } = useWizardStore()

  return (
    <Box>
      <Typography variant="h6" fontWeight={600} sx={{ mb: 1 }}>
        Configure NDA Terms
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Select the clause variants for each section of the agreement.
      </Typography>

      {/* Purpose */}
      <TextField
        label="Purpose Description"
        placeholder="Describe the purpose of sharing confidential information..."
        value={config.purpose}
        onChange={(e) => setConfigField('purpose', e.target.value)}
        multiline
        rows={2}
        fullWidth
        size="small"
        sx={{ mb: 2 }}
      />

      <ClauseSection
        title="1. Purpose Clause"
        description="Defines why confidential information is being shared."
        field="purposeOption"
        value={config.purposeOption}
        onChange={(v) => setConfigField('purposeOption', v)}
        options={[
          { value: 'A', label: 'General business relationship' },
          { value: 'B', label: 'Business collaboration and information exchange' },
          { value: 'C', label: 'Investment evaluation and due diligence' },
          { value: 'D', label: 'Merger or acquisition evaluation' },
        ]}
      />

      <Divider sx={{ my: 2 }} />

      <ClauseSection
        title="2. Data Protection"
        description="How personal data is handled under the agreement."
        field="personalDataSharing"
        value={config.personalDataSharing}
        onChange={(v) => setConfigField('personalDataSharing', v)}
        options={[
          { value: 'A', label: 'Standard GDPR compliance' },
          { value: 'B', label: 'Enhanced GDPR with separate DPA' },
          { value: 'C', label: 'No personal data shared' },
        ]}
      />

      <Divider sx={{ my: 2 }} />

      <ClauseSection
        title="3. Agreement Duration"
        description="How long the NDA remains in force."
        field="agreementDuration"
        value={config.agreementDuration}
        onChange={(v) => setConfigField('agreementDuration', v)}
        options={[
          { value: 'A', label: '2 years with 30-day notice' },
          { value: 'B', label: '3 years with 60-day notice' },
          { value: 'C', label: '5 years, mutual termination only' },
          { value: 'D', label: '1 year with 14-day notice' },
        ]}
      />

      <Divider sx={{ my: 2 }} />

      <ClauseSection
        title="4. Confidentiality Survival"
        description="How long obligations survive after termination."
        field="confidentialitySurvival"
        value={config.confidentialitySurvival}
        onChange={(v) => setConfigField('confidentialitySurvival', v)}
        options={[
          { value: 'A', label: '2 years post-termination' },
          { value: 'B', label: '3 years post-termination' },
          { value: 'C', label: '5 years post-termination' },
          { value: 'D', label: 'Indefinite with trade secret protection' },
        ]}
      />

      <Divider sx={{ my: 2 }} />

      <ClauseSection
        title="5. Permitted Recipients"
        description="Who may receive the confidential information."
        field="permittedRecipients"
        value={config.permittedRecipients}
        onChange={(v) => setConfigField('permittedRecipients', v)}
        options={[
          { value: 'A', label: 'Employees only (need-to-know)' },
          { value: 'B', label: 'Employees and professional advisors' },
          { value: 'C', label: 'Employees, advisors, and affiliated companies' },
          { value: 'D', label: 'Named individuals only' },
        ]}
      />

      <Divider sx={{ my: 2 }} />

      <ClauseSection
        title="6. Return or Destruction"
        description="What happens to confidential information on termination."
        field="returnOrDestruction"
        value={config.returnOrDestruction}
        onChange={(v) => setConfigField('returnOrDestruction', v)}
        options={[
          { value: 'A', label: 'Return all information' },
          { value: 'B', label: 'Destroy and certify destruction' },
          { value: 'C', label: 'Return or destroy at disclosing party\'s election' },
        ]}
      />

      <Divider sx={{ my: 2 }} />

      <ClauseSection
        title="7. AI/ML Restrictions"
        description="Restrictions on AI/ML use of confidential information."
        field="aiMlRestrictions"
        value={config.aiMlRestrictions}
        onChange={(v) => setConfigField('aiMlRestrictions', v)}
        options={[
          { value: 'A', label: 'Full prohibition on AI/ML training' },
          { value: 'B', label: 'Internal analysis with consent only' },
          { value: 'C', label: 'No specific AI/ML restrictions' },
        ]}
      />

      <Divider sx={{ my: 2 }} />

      {/* Governing Law — Select */}
      <Box sx={{ mb: 3 }}>
        <FormControl fullWidth size="small">
          <FormLabel sx={{ fontWeight: 600, color: '#374151', mb: 0.5 }}>
            8. Governing Law
          </FormLabel>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            Which jurisdiction's laws govern the agreement.
          </Typography>
          <Select
            value={config.governingLaw}
            onChange={(e) => setConfigField('governingLaw', e.target.value)}
          >
            <MenuItem value="england_wales">England and Wales</MenuItem>
            <MenuItem value="scotland">Scotland</MenuItem>
            <MenuItem value="new_york">New York, USA</MenuItem>
            <MenuItem value="delaware">Delaware, USA</MenuItem>
          </Select>
        </FormControl>
      </Box>

      <Divider sx={{ my: 2 }} />

      <ClauseSection
        title="9. Dispute Resolution"
        description="How disputes are resolved."
        field="disputeResolution"
        value={config.disputeResolution}
        onChange={(v) => setConfigField('disputeResolution', v)}
        options={[
          { value: 'A', label: 'English courts (exclusive jurisdiction)' },
          { value: 'B', label: 'Mediation then litigation' },
          { value: 'C', label: 'LCIA Arbitration (London)' },
          { value: 'D', label: 'Courts of agreed jurisdiction' },
          { value: 'E', label: 'Senior management escalation then arbitration' },
        ]}
      />

      <Divider sx={{ my: 2 }} />

      <ClauseSection
        title="10. Non-Solicitation"
        description="Restrictions on hiring each other's employees."
        field="nonSolicitation"
        value={config.nonSolicitation}
        onChange={(v) => setConfigField('nonSolicitation', v)}
        options={[
          { value: 'A', label: '12 months restriction' },
          { value: 'B', label: '24 months restriction' },
          { value: 'C', label: '6 months (key personnel only)' },
          { value: 'D', label: 'No restriction' },
        ]}
      />

      <Divider sx={{ my: 2 }} />

      {/* Additional Clauses — Checkboxes */}
      <Box>
        <FormLabel sx={{ fontWeight: 600, color: '#374151' }}>
          11. Additional Clauses (Optional)
        </FormLabel>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          Select any additional provisions to include.
        </Typography>
        <FormGroup>
          {[
            { value: 'no_partnership', label: 'No Partnership — clarifies no joint venture created' },
            { value: 'no_obligation', label: 'No Obligation to Proceed — no commitment to future deals' },
            { value: 'publicity', label: 'Publicity Restrictions — no public announcements' },
            { value: 'residual_info', label: 'Residual Information — protects unaided memory use' },
          ].map((item) => (
            <FormControlLabel
              key={item.value}
              control={
                <Checkbox
                  size="small"
                  checked={config.additionalClauses.includes(item.value)}
                  onChange={() => toggleAdditionalClause(item.value)}
                />
              }
              label={<Typography variant="body2">{item.label}</Typography>}
            />
          ))}
        </FormGroup>
      </Box>
    </Box>
  )
}

export default NDAConfigurationForm
