/**
 * EmailViewer — compose / reply / forward / view email component
 *
 * Modes:
 *   compose — new email with to, subject, body fields
 *   reply   — shows original message, prefills threading (Re: subject, quoted body)
 *   forward — prefills Fwd: subject and quoted body, empty To
 *   view    — read-only display of sent/received email
 *
 * Features:
 *   - Auto-save: debounced 2s after last keystroke. Shows "Saving..." → "Saved ✓" indicator.
 *   - Reply / Forward buttons in view mode, triggering mode switch in the parent.
 *   - Thread display: collapsible quoted original below the email body in view mode.
 */

import React, { useState, useRef, useCallback, useEffect, useMemo } from 'react';
import Box from '@mui/material/Box';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import IconButton from '@mui/material/IconButton';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import Popover from '@mui/material/Popover';
import Stack from '@mui/material/Stack';
import CircularProgress from '@mui/material/CircularProgress';
import Divider from '@mui/material/Divider';
import LinearProgress from '@mui/material/LinearProgress';
import Tooltip from '@mui/material/Tooltip';
import Collapse from '@mui/material/Collapse';
import {
  Send,
  Schedule,
  Save,
  AutoAwesome,
  Edit,
  Close,
  AttachFile,
  InsertDriveFile,
  Reply,
  Forward,
  ExpandMore,
  ExpandLess,
} from '@mui/icons-material';
import { format } from 'date-fns';
import type { Message } from '@outr/types/message.types';
import type { EmailAccount } from '@outr/types/email_account.types';
import RichTextEditor from './RichTextEditor';
import AIEmailModal from './AIEmailModal';
import FollowUpModal from './FollowUpModal';
import FollowUpTimeline from './FollowUpTimeline';
import {
  uploadAttachment,
  listAttachments,
  downloadAttachment,
  removeAttachment,
  type Attachment,
} from '../api/outreachApi';

export type EmailViewerMode = 'compose' | 'reply' | 'forward' | 'view';

export interface EmailViewerProps {
  mode: EmailViewerMode;
  message?: Message | null;
  /**
   * The original message being replied to / forwarded.
   * Used to populate quoted body in reply/forward modes and to show
   * the collapsible thread section in view mode.
   */
  originalMessage?: Message | null;
  accounts: EmailAccount[];
  onSend: (messageId: string) => void;
  onSchedule: (messageId: string, scheduledFor: string) => void;
  onSaveDraft: (data: DraftData) => Promise<Message | void>;
  onClose?: () => void;
  onReply?: (message: Message) => void;
  onForward?: (message: Message) => void;
  isSending?: boolean;
  isScheduling?: boolean;
  isSaving?: boolean;
}

// Auto-save indicator state
type SaveState = 'idle' | 'pending' | 'saving' | 'saved' | 'error';

const AUTO_SAVE_DEBOUNCE_MS = 2000;
const SAVED_INDICATOR_HIDE_MS = 2000;

export interface DraftData {
  id?: string;
  to_addresses: string[];
  cc_addresses?: string[];
  subject: string;
  body: string;
  from_address: string;
  email_account_id: string;
  investor_id?: string;
  previous_message_id?: string;
  thread_id?: string;
}

const statusColors: Record<string, string> = {
  draft: '#78909c',
  sent: '#4f7df9',
  received: '#66bb6a',
  scheduled: '#ff9800',
  failed: '#f44336',
  cancelled: '#9e9e9e',
};

export const EmailViewer: React.FC<EmailViewerProps> = ({
  mode,
  message,
  originalMessage,
  accounts,
  onSend,
  onSchedule,
  onSaveDraft,
  onClose,
  onReply,
  onForward,
  isSending = false,
  isScheduling = false,
  isSaving = false,
}) => {
  // Form state
  const [toField, setToField] = useState('');
  const [ccField, setCcField] = useState('');
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [accountId, setAccountId] = useState('');
  const [fromAddress, setFromAddress] = useState('');

  // Schedule popover
  const [schedAnchor, setSchedAnchor] = useState<HTMLElement | null>(null);
  const [schedDateTime, setSchedDateTime] = useState('');

  // AI modal
  const [aiModalOpen, setAiModalOpen] = useState(false);
  const [aiEditOpen, setAiEditOpen] = useState(false);

  // Follow-up modal — opens after a successful send
  const [followUpModalOpen, setFollowUpModalOpen] = useState(false);
  // Capture the just-sent message ID and sent-at time for the modal
  const [justSentMessageId, setJustSentMessageId] = useState<string | null>(null);
  const [justSentAt, setJustSentAt] = useState<string | null>(null);
  const [justSentSubject, setJustSentSubject] = useState<string>('');

  // Attachments
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [attachError, setAttachError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Auto-save state
  const [saveState, setSaveState] = useState<SaveState>('idle');
  // Tracks the live draft id (may differ from message.id when composing new)
  const draftIdRef = useRef<string | undefined>(message?.id);
  // Debounce timer ref — avoids re-renders on each keystroke
  const autoSaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Hides "Saved" indicator after brief display
  const savedHideTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Fingerprint of last successfully saved content for dirty-checking
  const lastSavedContentRef = useRef<string>('');

  // Thread display
  const [threadExpanded, setThreadExpanded] = useState(false);

  const isReadOnly = mode === 'view';
  const isEditable = mode === 'compose' || mode === 'reply' || mode === 'forward';

  // Content fingerprint for dirty-checking
  const contentFingerprint = `${toField}|${ccField}|${subject}|${body}`;
  const hasContent = Boolean(toField.trim() || subject.trim() || body.trim());

  // Keep draftIdRef in sync with message prop (updated after first create returns an ID)
  useEffect(() => {
    draftIdRef.current = message?.id;
  }, [message?.id]);

  // Populate form from message
  useEffect(() => {
    if (!message) {
      // Reset for new compose / forward with no existing draft
      if (mode === 'compose' || mode === 'forward') {
        setToField('');
        setCcField('');
        setSubject('');
        setBody('');
        lastSavedContentRef.current = '';
        setSaveState('idle');
        if (accounts.length > 0 && !accountId) {
          setAccountId(accounts[0].id);
          setFromAddress(accounts[0].email_address);
        }
      }
      return;
    }

    const sourceMsg = originalMessage || message;

    if (mode === 'reply') {
      setToField(sourceMsg.from_address || '');
      setCcField('');
      setSubject(sourceMsg.subject.startsWith('Re: ') ? sourceMsg.subject : `Re: ${sourceMsg.subject}`);
      setBody(buildQuotedBody(sourceMsg));
    } else if (mode === 'forward') {
      setToField('');
      setCcField('');
      setSubject(sourceMsg.subject.startsWith('Fwd: ') ? sourceMsg.subject : `Fwd: ${sourceMsg.subject}`);
      setBody(buildQuotedBody(sourceMsg));
    } else {
      // compose (editing existing draft) or view
      const toArr = parseAddresses(message.to_addresses);
      const ccArr = parseAddresses(message.cc_addresses);
      setToField(toArr.join(', '));
      setCcField(ccArr.join(', '));
      setSubject(message.subject || '');
      setBody(message.body || '');
    }

    lastSavedContentRef.current = '';
    setSaveState('idle');

    if (message.email_account_id) {
      setAccountId(message.email_account_id);
      const acct = accounts.find((a) => a.id === message.email_account_id);
      if (acct) setFromAddress(acct.email_address);
    }
    if (message.from_address && mode !== 'reply' && mode !== 'forward') {
      setFromAddress(message.from_address);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [message?.id, mode, originalMessage?.id]);

  // Load attachments whenever the message changes
  useEffect(() => {
    if (!message?.id) {
      setAttachments([]);
      return;
    }
    listAttachments(message.id)
      .then(setAttachments)
      .catch(() => setAttachments([]));
  }, [message?.id]);

  // ---------------------------------------------------------------------------
  // Auto-save: fire 2s after last content change
  // ---------------------------------------------------------------------------

  const performAutoSave = useCallback(async (
    snapshot: { to: string; cc: string; subj: string; bd: string; from: string; acct: string; fp: string }
  ) => {
    if (snapshot.fp === lastSavedContentRef.current) return;

    setSaveState('saving');
    try {
      const draft: DraftData = {
        id: draftIdRef.current,
        to_addresses: snapshot.to.split(',').map((s) => s.trim()).filter(Boolean),
        cc_addresses: snapshot.cc ? snapshot.cc.split(',').map((s) => s.trim()).filter(Boolean) : undefined,
        subject: snapshot.subj,
        body: snapshot.bd,
        from_address: snapshot.from,
        email_account_id: snapshot.acct,
        previous_message_id: (mode === 'reply' || mode === 'forward') ? message?.id : undefined,
        thread_id: mode === 'reply' ? message?.thread_id || undefined : undefined,
      };

      const result = await onSaveDraft(draft);
      if (result && (result as Message).id && !draftIdRef.current) {
        draftIdRef.current = (result as Message).id;
      }

      lastSavedContentRef.current = snapshot.fp;
      setSaveState('saved');

      if (savedHideTimerRef.current) clearTimeout(savedHideTimerRef.current);
      savedHideTimerRef.current = setTimeout(() => setSaveState('idle'), SAVED_INDICATOR_HIDE_MS);
    } catch {
      setSaveState('error');
    }
  // mode and message?.id are stable within a compose session; include to satisfy exhaustive-deps
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, message?.id, message?.thread_id, onSaveDraft]);

  useEffect(() => {
    if (!isEditable || !hasContent) return;
    if (contentFingerprint !== lastSavedContentRef.current) {
      setSaveState('pending');
    }

    // Snapshot values so they don't change before the timeout fires
    const snapshot = { to: toField, cc: ccField, subj: subject, bd: body, from: fromAddress, acct: accountId, fp: contentFingerprint };

    if (autoSaveTimerRef.current) clearTimeout(autoSaveTimerRef.current);
    autoSaveTimerRef.current = setTimeout(() => performAutoSave(snapshot), AUTO_SAVE_DEBOUNCE_MS);

    return () => {
      if (autoSaveTimerRef.current) clearTimeout(autoSaveTimerRef.current);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [contentFingerprint, isEditable, hasContent]);

  // Cleanup timers on unmount
  useEffect(() => {
    return () => {
      if (autoSaveTimerRef.current) clearTimeout(autoSaveTimerRef.current);
      if (savedHideTimerRef.current) clearTimeout(savedHideTimerRef.current);
    };
  }, []);

  const handleAccountChange = useCallback(
    (id: string) => {
      setAccountId(id);
      const acct = accounts.find((a) => a.id === id);
      if (acct) setFromAddress(acct.email_address);
    },
    [accounts],
  );

  const buildDraft = useCallback((): DraftData => ({
    id: draftIdRef.current,
    to_addresses: toField.split(',').map((s) => s.trim()).filter(Boolean),
    cc_addresses: ccField ? ccField.split(',').map((s) => s.trim()).filter(Boolean) : undefined,
    subject,
    body,
    from_address: fromAddress,
    email_account_id: accountId,
    previous_message_id: (mode === 'reply' || mode === 'forward') ? message?.id : undefined,
    thread_id: mode === 'reply' ? message?.thread_id || undefined : undefined,
  }), [toField, ccField, subject, body, fromAddress, accountId, message, mode]);

  const handleFileSelect = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;
      const msgId = draftIdRef.current || message?.id;
      if (!msgId) return;

      setAttachError(null);
      setUploadProgress(0);

      try {
        const attachment = await uploadAttachment(msgId, file, setUploadProgress);
        setAttachments((prev) => [...prev, attachment]);
      } catch (err: unknown) {
        const msg =
          err && typeof err === 'object' && 'response' in err
            ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
            : undefined;
        setAttachError(msg || 'Upload failed');
      } finally {
        setUploadProgress(null);
        // Reset input so the same file can be re-selected after removal
        if (fileInputRef.current) fileInputRef.current.value = '';
      }
    },
    [message?.id],
  );

  const handleRemoveAttachment = useCallback(
    async (attachmentId: string) => {
      try {
        await removeAttachment(attachmentId);
        setAttachments((prev) => prev.filter((a) => a.id !== attachmentId));
      } catch {
        // Best-effort remove — keep local state updated regardless
        setAttachments((prev) => prev.filter((a) => a.id !== attachmentId));
      }
    },
    [],
  );

  const handleDownloadAttachment = useCallback(
    async (attachment: Attachment) => {
      await downloadAttachment(attachment.id, attachment.filename);
    },
    [],
  );

  const handleSend = useCallback(async () => {
    // Cancel any pending auto-save
    if (autoSaveTimerRef.current) clearTimeout(autoSaveTimerRef.current);

    const draft = buildDraft();
    const result = await onSaveDraft(draft);
    const targetId = (result as Message | undefined)?.id || draftIdRef.current;
    if (targetId) {
      onSend(targetId);
      // Offer follow-up scheduling after send
      setJustSentMessageId(targetId);
      setJustSentAt(new Date().toISOString());
      setJustSentSubject(draft.subject);
      setFollowUpModalOpen(true);
    }
  }, [buildDraft, onSaveDraft, onSend]);

  const handleScheduleConfirm = useCallback(() => {
    const targetId = draftIdRef.current || message?.id;
    if (!schedDateTime || !targetId) return;
    const iso = new Date(schedDateTime).toISOString();
    onSchedule(targetId, iso);
    setSchedAnchor(null);
  }, [schedDateTime, message?.id, onSchedule]);

  const handleSaveDraft = useCallback(async () => {
    // Cancel pending auto-save to avoid race
    if (autoSaveTimerRef.current) clearTimeout(autoSaveTimerRef.current);
    setSaveState('saving');
    try {
      const result = await onSaveDraft(buildDraft());
      if (result && (result as Message).id && !draftIdRef.current) {
        draftIdRef.current = (result as Message).id;
      }
      lastSavedContentRef.current = contentFingerprint;
      setSaveState('saved');
      if (savedHideTimerRef.current) clearTimeout(savedHideTimerRef.current);
      savedHideTimerRef.current = setTimeout(() => setSaveState('idle'), SAVED_INDICATOR_HIDE_MS);
    } catch {
      setSaveState('error');
    }
  }, [buildDraft, onSaveDraft, contentFingerprint]);

  const handleAIResult = useCallback(
    (generatedSubject: string, generatedBody: string) => {
      setSubject(generatedSubject);
      setBody(generatedBody);
      setAiModalOpen(false);
    },
    [],
  );

  const handleAIEditResult = useCallback(
    (editedText: string) => {
      setBody(editedText);
      setAiEditOpen(false);
    },
    [],
  );

  const selectedAccount = useMemo(
    () => accounts.find((a) => a.id === accountId),
    [accounts, accountId],
  );

  // Save indicator element
  const saveIndicator = useMemo(() => {
    if (saveState === 'idle') return null;
    if (saveState === 'pending') return (
      <Typography variant="caption" sx={{ color: '#6b7280', display: 'flex', alignItems: 'center', gap: 0.5, whiteSpace: 'nowrap' }}>
        <CircularProgress size={10} sx={{ color: '#6b7280' }} /> Unsaved
      </Typography>
    );
    if (saveState === 'saving') return (
      <Typography variant="caption" sx={{ color: '#6b7280', display: 'flex', alignItems: 'center', gap: 0.5, whiteSpace: 'nowrap' }}>
        <CircularProgress size={10} sx={{ color: '#6b7280' }} /> Saving...
      </Typography>
    );
    if (saveState === 'saved') return (
      <Typography variant="caption" sx={{ color: '#6b7280', whiteSpace: 'nowrap' }}>Saved ✓</Typography>
    );
    if (saveState === 'error') return (
      <Typography variant="caption" sx={{ color: '#f44336', whiteSpace: 'nowrap' }}>Save failed</Typography>
    );
    return null;
  }, [saveState]);

  // VIEW mode
  if (isReadOnly && message) {
    return (
      <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
        {/* Header */}
        <Box sx={{ p: 2, borderBottom: '1px solid', borderColor: 'divider' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
            <Typography variant="h6" sx={{ fontWeight: 600, fontSize: '1rem' }}>
              {message.subject}
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Chip
                label={message.status}
                size="small"
                sx={{
                  bgcolor: statusColors[message.status] || '#78909c',
                  color: '#fff',
                  fontWeight: 600,
                  fontSize: '0.7rem',
                }}
              />
              {onClose && (
                <IconButton size="small" onClick={onClose}>
                  <Close fontSize="small" />
                </IconButton>
              )}
            </Box>
          </Box>
          <Typography variant="body2" color="text.secondary">
            From: {message.from_address}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            To: {formatAddresses(message.to_addresses)}
          </Typography>
          {message.cc_addresses && Object.keys(message.cc_addresses).length > 0 && (
            <Typography variant="body2" color="text.secondary">
              CC: {formatAddresses(message.cc_addresses)}
            </Typography>
          )}
          <Typography variant="caption" color="text.disabled">
            {format(new Date(message.created_at), 'PPpp')}
          </Typography>
        </Box>

        {/* Body */}
        <Box
          sx={{
            flex: 1,
            overflow: 'auto',
            p: 2,
            '& a': { color: 'primary.main' },
          }}
          dangerouslySetInnerHTML={{ __html: message.body }}
        />

        {/* View-mode attachments */}
        {attachments.length > 0 && (
          <Box sx={{ p: 2, borderTop: '1px solid', borderColor: 'divider' }}>
            <Typography variant="caption" sx={{ color: '#6b7280', mb: 1, display: 'block' }}>
              Attachments ({attachments.length})
            </Typography>
            <Stack direction="row" flexWrap="wrap" gap={1}>
              {attachments.map((att) => (
                <Chip
                  key={att.id}
                  icon={<InsertDriveFile sx={{ fontSize: 14, color: '#6b7280 !important' }} />}
                  label={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                      <Typography
                        component="span"
                        sx={{ fontSize: '0.75rem', color: '#374151', cursor: 'pointer' }}
                        onClick={() => handleDownloadAttachment(att)}
                      >
                        {att.filename}
                      </Typography>
                      <Typography component="span" sx={{ fontSize: '0.7rem', color: '#6b7280' }}>
                        {formatFileSize(att.size)}
                      </Typography>
                    </Box>
                  }
                  size="small"
                  onClick={() => handleDownloadAttachment(att)}
                  sx={{
                    bgcolor: '#e5e7eb',
                    border: '1px solid #2a4a6f',
                    cursor: 'pointer',
                    '&:hover': { bgcolor: '#254b7a' },
                  }}
                />
              ))}
            </Stack>
          </Box>
        )}

        {/* Reply / Forward action bar */}
        {(onReply || onForward) && (
          <Box
            sx={{
              display: 'flex',
              gap: 1,
              px: 2,
              py: 1.5,
              borderTop: '1px solid',
              borderColor: 'divider',
            }}
          >
            {onReply && (
              <Button
                variant="outlined"
                size="small"
                startIcon={<Reply fontSize="small" />}
                onClick={() => onReply(message)}
                sx={{ textTransform: 'none', fontSize: '0.8rem' }}
              >
                Reply
              </Button>
            )}
            {onForward && (
              <Button
                variant="outlined"
                size="small"
                startIcon={<Forward fontSize="small" />}
                onClick={() => onForward(message)}
                sx={{ textTransform: 'none', fontSize: '0.8rem' }}
              >
                Forward
              </Button>
            )}
          </Box>
        )}

        {/* Thread: collapsible quoted original message */}
        {originalMessage && (
          <Box sx={{ borderTop: '1px solid', borderColor: 'divider' }}>
            <Button
              size="small"
              onClick={() => setThreadExpanded((v) => !v)}
              endIcon={threadExpanded ? <ExpandLess fontSize="small" /> : <ExpandMore fontSize="small" />}
              sx={{
                textTransform: 'none',
                color: '#6b7280',
                fontSize: '0.75rem',
                px: 2,
                py: 0.75,
                width: '100%',
                justifyContent: 'flex-start',
              }}
            >
              {threadExpanded ? 'Hide' : 'Show'} original message — {originalMessage.from_address}
            </Button>
            <Collapse in={threadExpanded}>
              <Box sx={{ mx: 2, mb: 1.5, borderLeft: '3px solid #e5e7eb', pl: 1.5 }}>
                <Typography variant="caption" sx={{ color: '#6b7d8e', display: 'block', mb: 0.5 }}>
                  From: {originalMessage.from_address} &nbsp;·&nbsp;{' '}
                  {format(new Date(originalMessage.created_at), 'PPpp')}
                </Typography>
                <Box
                  sx={{
                    fontSize: '0.8rem',
                    color: '#6b7d8e',
                    '& a': { color: 'primary.main' },
                  }}
                  dangerouslySetInnerHTML={{ __html: originalMessage.body }}
                />
              </Box>
            </Collapse>
          </Box>
        )}

        {/* Follow-up timeline — shown for sent messages */}
        {message.status === 'sent' && (
          <FollowUpTimeline messageId={message.id} />
        )}
      </Box>
    );
  }

  // COMPOSE / REPLY / FORWARD mode
  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header bar */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          p: 1.5,
          borderBottom: '1px solid',
          borderColor: 'divider',
        }}
      >
        <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
          {mode === 'reply' ? 'Reply' : mode === 'forward' ? 'Forward' : 'New Email'}
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {/* Auto-save indicator — tiny, unobtrusive */}
          {saveIndicator}
          {onClose && (
            <IconButton size="small" onClick={onClose}>
              <Close fontSize="small" />
            </IconButton>
          )}
        </Box>
      </Box>

      {/* Form Fields */}
      <Box sx={{ flex: 1, overflow: 'auto', p: 2, display: 'flex', flexDirection: 'column', gap: 1.5 }}>
        {/* From Account */}
        <FormControl size="small" fullWidth>
          <InputLabel>From</InputLabel>
          <Select
            value={accountId}
            label="From"
            onChange={(e) => handleAccountChange(e.target.value)}
            sx={{ fontSize: '0.875rem' }}
          >
            {accounts.map((acct) => (
              <MenuItem key={acct.id} value={acct.id}>
                {acct.email_address} ({acct.provider})
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        {/* To */}
        <TextField
          size="small"
          fullWidth
          label="To"
          placeholder="investor@example.com"
          value={toField}
          onChange={(e) => setToField(e.target.value)}
          sx={{ '& .MuiInputBase-input': { fontSize: '0.875rem' } }}
        />

        {/* CC */}
        <TextField
          size="small"
          fullWidth
          label="CC"
          placeholder="cc@example.com"
          value={ccField}
          onChange={(e) => setCcField(e.target.value)}
          sx={{ '& .MuiInputBase-input': { fontSize: '0.875rem' } }}
        />

        {/* Subject */}
        <TextField
          size="small"
          fullWidth
          label="Subject"
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
          sx={{ '& .MuiInputBase-input': { fontSize: '0.875rem' } }}
        />

        {/* Body */}
        <Box sx={{ flex: 1, minHeight: 0 }}>
          <RichTextEditor
            value={body}
            onChange={setBody}
            placeholder="Write your email..."
            minHeight={200}
          />
        </Box>

        {/* Attachment chips */}
        {(attachments.length > 0 || uploadProgress !== null || attachError) && (
          <Box>
            {/* Upload progress bar */}
            {uploadProgress !== null && (
              <Box sx={{ mb: 0.5 }}>
                <LinearProgress
                  variant="determinate"
                  value={uploadProgress}
                  sx={{
                    height: 3,
                    borderRadius: 2,
                    bgcolor: '#e5e7eb',
                    '& .MuiLinearProgress-bar': { bgcolor: '#4f7df9' },
                  }}
                />
                <Typography variant="caption" sx={{ color: '#6b7280' }}>
                  Uploading… {uploadProgress}%
                </Typography>
              </Box>
            )}

            {/* Error */}
            {attachError && (
              <Typography variant="caption" sx={{ color: '#f44336', display: 'block', mb: 0.5 }}>
                {attachError}
              </Typography>
            )}

            {/* Chips */}
            {attachments.length > 0 && (
              <Stack direction="row" flexWrap="wrap" gap={0.75}>
                {attachments.map((att) => (
                  <Chip
                    key={att.id}
                    icon={<InsertDriveFile sx={{ fontSize: 14, color: '#6b7280 !important' }} />}
                    label={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        <Typography
                          component="span"
                          sx={{ fontSize: '0.75rem', color: '#374151', cursor: 'pointer' }}
                          onClick={(e) => { e.stopPropagation(); handleDownloadAttachment(att); }}
                        >
                          {att.filename}
                        </Typography>
                        <Typography component="span" sx={{ fontSize: '0.7rem', color: '#6b7280' }}>
                          {formatFileSize(att.size)}
                        </Typography>
                      </Box>
                    }
                    onDelete={() => handleRemoveAttachment(att.id)}
                    size="small"
                    sx={{
                      bgcolor: '#e5e7eb',
                      border: '1px solid #2a4a6f',
                      '& .MuiChip-deleteIcon': { color: '#6b7280', fontSize: 14 },
                      '&:hover': { bgcolor: '#254b7a' },
                    }}
                  />
                ))}
              </Stack>
            )}
          </Box>
        )}

        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          style={{ display: 'none' }}
          accept=".pdf,.doc,.docx,.xls,.xlsx,.csv,.png,.jpg,.jpeg,.gif,.txt"
          onChange={handleFileSelect}
        />
      </Box>

      {/* Action Bar */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          p: 1.5,
          borderTop: '1px solid',
          borderColor: 'divider',
        }}
      >
        <Button
          variant="contained"
          size="small"
          startIcon={isSending ? <CircularProgress size={16} color="inherit" /> : <Send />}
          onClick={handleSend}
          disabled={isSending || !toField || !subject}
          sx={{ textTransform: 'none' }}
        >
          Send
        </Button>

        <Button
          variant="outlined"
          size="small"
          startIcon={<Schedule />}
          onClick={(e) => setSchedAnchor(e.currentTarget)}
          disabled={isScheduling || (!draftIdRef.current && !message?.id)}
          sx={{ textTransform: 'none' }}
        >
          Schedule
        </Button>

        <Button
          variant="outlined"
          size="small"
          startIcon={isSaving ? <CircularProgress size={16} color="inherit" /> : <Save />}
          onClick={handleSaveDraft}
          disabled={isSaving}
          sx={{ textTransform: 'none' }}
        >
          Save Draft
        </Button>

        <Tooltip title="Attach file">
          <span>
            <IconButton
              size="small"
              onClick={() => fileInputRef.current?.click()}
              disabled={!message?.id || uploadProgress !== null}
              sx={{ color: '#6b7280', '&:hover': { color: '#b0c0d0' } }}
            >
              <AttachFile fontSize="small" />
            </IconButton>
          </span>
        </Tooltip>

        <Divider orientation="vertical" flexItem sx={{ mx: 0.5 }} />

        <Button
          variant="text"
          size="small"
          startIcon={<AutoAwesome />}
          onClick={() => setAiModalOpen(true)}
          sx={{
            textTransform: 'none',
            color: '#ab47bc',
          }}
        >
          AI Draft
        </Button>

        <Button
          variant="text"
          size="small"
          startIcon={<Edit />}
          onClick={() => setAiEditOpen(true)}
          disabled={!body}
          sx={{
            textTransform: 'none',
            color: '#ab47bc',
          }}
        >
          AI Edit
        </Button>

        <Divider orientation="vertical" flexItem sx={{ mx: 0.5 }} />

        <Tooltip title="Schedule automatic follow-up emails after sending">
          <span>
            <Button
              variant="text"
              size="small"
              startIcon={<Schedule />}
              onClick={() => {
                const id = draftIdRef.current || message?.id || null;
                setJustSentMessageId(id);
                setJustSentAt(null);
                setJustSentSubject(subject);
                setFollowUpModalOpen(true);
              }}
              sx={{
                textTransform: 'none',
                color: '#42a5f5',
                fontSize: '0.8rem',
              }}
            >
              Follow-ups
            </Button>
          </span>
        </Tooltip>
      </Box>

      {/* Schedule Popover */}
      <Popover
        open={Boolean(schedAnchor)}
        anchorEl={schedAnchor}
        onClose={() => setSchedAnchor(null)}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
        transformOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Box sx={{ p: 2, width: 280 }}>
          <Typography variant="subtitle2" sx={{ mb: 1.5 }}>
            Schedule Send
          </Typography>
          <TextField
            type="datetime-local"
            size="small"
            fullWidth
            value={schedDateTime}
            onChange={(e) => setSchedDateTime(e.target.value)}
            InputLabelProps={{ shrink: true }}
            inputProps={{
              min: new Date().toISOString().slice(0, 16),
            }}
            sx={{ mb: 1.5 }}
          />
          <Stack direction="row" spacing={1} justifyContent="flex-end">
            <Button
              size="small"
              onClick={() => setSchedAnchor(null)}
              sx={{ textTransform: 'none' }}
            >
              Cancel
            </Button>
            <Button
              size="small"
              variant="contained"
              onClick={handleScheduleConfirm}
              disabled={!schedDateTime}
              sx={{ textTransform: 'none' }}
            >
              Confirm
            </Button>
          </Stack>
        </Box>
      </Popover>

      {/* AI Generate Modal */}
      <AIEmailModal
        open={aiModalOpen}
        onClose={() => setAiModalOpen(false)}
        onUse={handleAIResult}
        mode="generate"
      />

      {/* AI Edit Modal */}
      <AIEmailModal
        open={aiEditOpen}
        onClose={() => setAiEditOpen(false)}
        onUse={(_subj, editedBody) => handleAIEditResult(editedBody)}
        mode="edit"
        existingText={body}
      />

      {/* Follow-up scheduling modal */}
      <FollowUpModal
        open={followUpModalOpen}
        messageId={justSentMessageId}
        sentAt={justSentAt}
        originalSubject={justSentSubject}
        onClose={() => setFollowUpModalOpen(false)}
        onScheduled={() => setFollowUpModalOpen(false)}
      />
    </Box>
  );
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Build the quoted-body block for reply / forward compose.
 * Styled with a left border and muted colour to match the dark theme.
 */
function buildQuotedBody(original: Message): string {
  const dateStr = format(new Date(original.created_at), 'PPpp');
  return [
    '<br/>',
    '<br/>',
    '<div style="border-left:3px solid #e5e7eb;padding-left:12px;margin-left:0">',
    `<p style="color:#6b7d8e;font-size:0.85em;margin:0 0 6px">`,
    `--- Original Message ---<br/>`,
    `From: ${original.from_address}<br/>`,
    `Date: ${dateStr}<br/>`,
    `Subject: ${original.subject}`,
    `</p>`,
    `<div style="color:#6b7d8e;font-size:0.85em">${original.body}</div>`,
    '</div>',
  ].join('');
}

function parseAddresses(val: unknown): string[] {
  if (!val) return [];
  if (Array.isArray(val)) return val as string[];
  if (typeof val === 'string') {
    try {
      const parsed = JSON.parse(val);
      if (Array.isArray(parsed)) return parsed;
    } catch {
      return val.split(',').map((s) => s.trim()).filter(Boolean);
    }
  }
  return [];
}

function formatAddresses(val: unknown): string {
  return parseAddresses(val).join(', ') || '(none)';
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default EmailViewer;
