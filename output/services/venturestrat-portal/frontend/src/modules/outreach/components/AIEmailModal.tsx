/**
 * AIEmailModal — dialog for AI email generation and editing
 *
 * Two modes:
 *   generate — investor name, company, tone, instructions -> subject + body
 *   edit     — takes existing text + instruction -> edited text
 */

import React, { useState, useCallback } from 'react';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Paper from '@mui/material/Paper';
import CircularProgress from '@mui/material/CircularProgress';
import Fade from '@mui/material/Fade';
import { AutoAwesome, Refresh } from '@mui/icons-material';
import { useAIGenerate } from '../hooks/useAIGenerate';
import { useAIEdit } from '../hooks/useAIEdit';

export interface AIEmailModalProps {
  open: boolean;
  onClose: () => void;
  onUse: (subject: string, body: string) => void;
  mode: 'generate' | 'edit';
  existingText?: string;
}

type Tone = 'professional' | 'friendly' | 'casual';

export const AIEmailModal: React.FC<AIEmailModalProps> = ({
  open,
  onClose,
  onUse,
  mode,
  existingText = '',
}) => {
  // Generate mode fields
  const [investorName, setInvestorName] = useState('');
  const [company, setCompany] = useState('');
  const [tone, setTone] = useState<Tone>('professional');
  const [instructions, setInstructions] = useState('');

  // Edit mode fields
  const [editInstruction, setEditInstruction] = useState('');

  // Result state
  const [resultSubject, setResultSubject] = useState('');
  const [resultBody, setResultBody] = useState('');
  const [hasResult, setHasResult] = useState(false);

  const generateMutation = useAIGenerate();
  const editMutation = useAIEdit();

  const isLoading = generateMutation.isPending || editMutation.isPending;

  const handleGenerate = useCallback(async () => {
    if (mode === 'generate') {
      try {
        const result = await generateMutation.mutateAsync({
          investor_name: investorName,
          company: company || undefined,
          tone,
          custom_instructions: instructions || undefined,
        });
        setResultSubject(result.subject);
        setResultBody(result.body);
        setHasResult(true);
      } catch {
        // Error handled by mutation state
      }
    } else {
      try {
        const result = await editMutation.mutateAsync({
          text: existingText,
          instruction: editInstruction,
        });
        setResultSubject('');
        setResultBody(result.text);
        setHasResult(true);
      } catch {
        // Error handled by mutation state
      }
    }
  }, [mode, investorName, company, tone, instructions, editInstruction, existingText, generateMutation, editMutation]);

  const handleUse = useCallback(() => {
    onUse(resultSubject, resultBody);
    handleReset();
  }, [resultSubject, resultBody, onUse]);

  const handleReset = useCallback(() => {
    setResultSubject('');
    setResultBody('');
    setHasResult(false);
  }, []);

  const handleClose = useCallback(() => {
    handleReset();
    setInvestorName('');
    setCompany('');
    setTone('professional');
    setInstructions('');
    setEditInstruction('');
    onClose();
  }, [onClose, handleReset]);

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="sm"
      fullWidth
      PaperProps={{
        sx: {
          bgcolor: '#ffffff',
          backgroundImage: 'none',
          border: '1px solid',
          borderColor: 'rgba(171,71,188,0.3)',
        },
      }}
    >
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <AutoAwesome sx={{ color: '#ab47bc' }} />
        <Typography variant="h6" sx={{ fontWeight: 600 }}>
          {mode === 'generate' ? 'AI Email Draft' : 'AI Edit'}
        </Typography>
      </DialogTitle>

      <DialogContent>
        {/* Input Form */}
        {!hasResult && (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
            {mode === 'generate' ? (
              <>
                <TextField
                  size="small"
                  fullWidth
                  label="Investor Name"
                  placeholder="John Smith"
                  value={investorName}
                  onChange={(e) => setInvestorName(e.target.value)}
                  required
                />
                <TextField
                  size="small"
                  fullWidth
                  label="Company"
                  placeholder="Acme Capital"
                  value={company}
                  onChange={(e) => setCompany(e.target.value)}
                />
                <FormControl size="small" fullWidth>
                  <InputLabel>Tone</InputLabel>
                  <Select
                    value={tone}
                    label="Tone"
                    onChange={(e) => setTone(e.target.value as Tone)}
                  >
                    <MenuItem value="professional">Professional</MenuItem>
                    <MenuItem value="friendly">Friendly</MenuItem>
                    <MenuItem value="casual">Casual</MenuItem>
                  </Select>
                </FormControl>
                <TextField
                  size="small"
                  fullWidth
                  label="Custom Instructions"
                  placeholder="Mention our Series A round, focus on fintech sector..."
                  multiline
                  rows={3}
                  value={instructions}
                  onChange={(e) => setInstructions(e.target.value)}
                />
              </>
            ) : (
              <>
                <Paper
                  variant="outlined"
                  sx={{
                    p: 1.5,
                    maxHeight: 120,
                    overflow: 'auto',
                    bgcolor: 'rgba(255,255,255,0.02)',
                    fontSize: '0.8rem',
                    color: 'text.secondary',
                  }}
                >
                  <Typography variant="caption" color="text.disabled" sx={{ display: 'block', mb: 0.5 }}>
                    Current text:
                  </Typography>
                  <Box
                    sx={{ fontSize: '0.8rem' }}
                    dangerouslySetInnerHTML={{ __html: existingText.slice(0, 500) }}
                  />
                </Paper>
                <TextField
                  size="small"
                  fullWidth
                  label="Edit Instructions"
                  placeholder="Make it more concise, fix grammar, add a call-to-action..."
                  multiline
                  rows={3}
                  value={editInstruction}
                  onChange={(e) => setEditInstruction(e.target.value)}
                  required
                />
              </>
            )}

            {/* Loading state */}
            {isLoading && (
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', py: 3 }}>
                <Box sx={{ textAlign: 'center' }}>
                  <Box
                    sx={{
                      position: 'relative',
                      display: 'inline-flex',
                      mb: 1,
                    }}
                  >
                    <CircularProgress
                      size={40}
                      sx={{ color: '#ab47bc' }}
                    />
                    <Box
                      sx={{
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        right: 0,
                        bottom: 0,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                      }}
                    >
                      <AutoAwesome sx={{ fontSize: 16, color: '#ab47bc' }} />
                    </Box>
                  </Box>
                  <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.8rem' }}>
                    {mode === 'generate' ? 'Crafting your email...' : 'Editing your text...'}
                  </Typography>
                </Box>
              </Box>
            )}

            {/* Error */}
            {(generateMutation.isError || editMutation.isError) && (
              <Typography variant="body2" color="error" sx={{ fontSize: '0.8rem' }}>
                Failed to generate. Please try again.
              </Typography>
            )}
          </Box>
        )}

        {/* Result Preview */}
        {hasResult && (
          <Fade in={hasResult}>
            <Box sx={{ mt: 1 }}>
              {resultSubject && (
                <Box sx={{ mb: 1.5 }}>
                  <Typography variant="caption" color="text.disabled">
                    Subject
                  </Typography>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>
                    {resultSubject}
                  </Typography>
                </Box>
              )}
              <Typography variant="caption" color="text.disabled">
                Body
              </Typography>
              <Paper
                variant="outlined"
                sx={{
                  p: 1.5,
                  mt: 0.5,
                  maxHeight: 300,
                  overflow: 'auto',
                  bgcolor: 'rgba(255,255,255,0.02)',
                }}
              >
                <Box
                  sx={{ fontSize: '0.875rem', lineHeight: 1.6, '& a': { color: 'primary.main' } }}
                  dangerouslySetInnerHTML={{ __html: resultBody }}
                />
              </Paper>
            </Box>
          </Fade>
        )}
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button
          onClick={handleClose}
          size="small"
          sx={{ textTransform: 'none' }}
        >
          Cancel
        </Button>
        {hasResult ? (
          <>
            <Button
              startIcon={<Refresh />}
              onClick={handleReset}
              size="small"
              sx={{ textTransform: 'none' }}
            >
              Regenerate
            </Button>
            <Button
              variant="contained"
              onClick={handleUse}
              size="small"
              sx={{
                textTransform: 'none',
                bgcolor: '#ab47bc',
                '&:hover': { bgcolor: '#9c27b0' },
              }}
            >
              Use This
            </Button>
          </>
        ) : (
          <Button
            variant="contained"
            startIcon={isLoading ? <CircularProgress size={16} color="inherit" /> : <AutoAwesome />}
            onClick={handleGenerate}
            disabled={
              isLoading ||
              (mode === 'generate' && !investorName) ||
              (mode === 'edit' && !editInstruction)
            }
            size="small"
            sx={{
              textTransform: 'none',
              bgcolor: '#ab47bc',
              '&:hover': { bgcolor: '#9c27b0' },
            }}
          >
            Generate
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
};

export default AIEmailModal;
