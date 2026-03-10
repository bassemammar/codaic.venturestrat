/**
 * MailPage — three-panel email client layout
 *
 * Left:   EmailSidebar (300px, collapsible on mobile)
 * Center: EmailViewer (flex)
 *
 * Features:
 *   - Reply / Forward mode switching
 *   - Auto-save: onSaveDraft returns the saved Message so EmailViewer can
 *     track the draft id for subsequent auto-saves
 *   - originalMessage passed through for quoted-body and thread display
 */

import React, { useState, useCallback, useMemo } from 'react';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import FormControl from '@mui/material/FormControl';
import IconButton from '@mui/material/IconButton';
import useMediaQuery from '@mui/material/useMediaQuery';
import { useTheme } from '@mui/material/styles';
import { Add, Menu as MenuIcon, ArrowBack, Mail } from '@mui/icons-material';
import type { Message, MessageCreateRequest } from '@outr/types/message.types';
import { useMessages } from '../hooks/useMessages';
import { useEmailAccounts } from '../hooks/useEmailAccounts';
import { useCreateMessage, useUpdateMessage } from '../hooks/useCreateMessage';
import { useSendMessage } from '../hooks/useSendMessage';
import { useScheduleMessage } from '../hooks/useScheduleMessage';
import { useAuth } from '@/auth/AuthProvider';
import EmailSidebar from '../components/EmailSidebar';
import EmailViewer, { type DraftData, type EmailViewerMode } from '../components/EmailViewer';

const SIDEBAR_WIDTH = 300;

export const MailPage: React.FC = () => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const { user } = useAuth();

  // Data
  const { data: messages = [], isLoading: messagesLoading } = useMessages();
  const { data: accounts = [] } = useEmailAccounts();

  // Mutations
  const createMsg = useCreateMessage();
  const updateMsg = useUpdateMessage();
  const sendMsg = useSendMessage();
  const scheduleMsg = useScheduleMessage();

  // UI state
  const [selectedMessage, setSelectedMessage] = useState<Message | null>(null);
  // The message being replied to / forwarded — kept separately so we can pass
  // it as originalMessage to EmailViewer for threading display.
  const [originalMessage, setOriginalMessage] = useState<Message | null>(null);
  const [viewerMode, setViewerMode] = useState<EmailViewerMode>('compose');
  const [showSidebar, setShowSidebar] = useState(true);
  const [accountFilter, setAccountFilter] = useState<string>('all');

  // Filter messages by account
  const filteredMessages = useMemo(() => {
    if (accountFilter === 'all') return messages;
    return messages.filter((m) => m.email_account_id === accountFilter);
  }, [messages, accountFilter]);

  const handleSelectMessage = useCallback((msg: Message) => {
    setSelectedMessage(msg);
    setOriginalMessage(null);
    setViewerMode(msg.status === 'draft' ? 'compose' : 'view');
    if (isMobile) setShowSidebar(false);
  }, [isMobile]);

  const handleCompose = useCallback(() => {
    setSelectedMessage(null);
    setOriginalMessage(null);
    setViewerMode('compose');
    if (isMobile) setShowSidebar(false);
  }, [isMobile]);

  const handleClose = useCallback(() => {
    setSelectedMessage(null);
    setOriginalMessage(null);
    setViewerMode('compose');
    if (isMobile) setShowSidebar(true);
  }, [isMobile]);

  const handleReply = useCallback((msg: Message) => {
    // Keep original for threading display; selected becomes a fresh draft
    setOriginalMessage(msg);
    setSelectedMessage(null);
    setViewerMode('reply');
    if (isMobile) setShowSidebar(false);
  }, [isMobile]);

  const handleForward = useCallback((msg: Message) => {
    setOriginalMessage(msg);
    setSelectedMessage(null);
    setViewerMode('forward');
    if (isMobile) setShowSidebar(false);
  }, [isMobile]);

  /**
   * Save (create or update) a draft.
   * Returns the saved Message so EmailViewer's auto-save can obtain the ID
   * on the first create and use it for subsequent PUT calls.
   */
  const handleSaveDraft = useCallback(
    async (draft: DraftData): Promise<Message> => {
      const payload = {
        user_id: user?.id || '',
        to_addresses: draft.to_addresses as unknown as Record<string, any>,
        cc_addresses: (draft.cc_addresses || []) as unknown as Record<string, any>,
        subject: draft.subject,
        body: draft.body,
        from_address: draft.from_address,
        email_account_id: draft.email_account_id || undefined,
        status: 'draft',
        previous_message_id: draft.previous_message_id || undefined,
        thread_id: draft.thread_id || undefined,
      };

      if (draft.id) {
        const updated = await updateMsg.mutateAsync({
          id: draft.id,
          data: payload,
        });
        setSelectedMessage(updated);
        return updated;
      } else {
        const created = await createMsg.mutateAsync(
          payload as MessageCreateRequest,
        );
        setSelectedMessage(created);
        return created;
      }
    },
    [user, createMsg, updateMsg],
  );

  const handleSend = useCallback(
    async (messageId: string) => {
      await sendMsg.mutateAsync({ id: messageId });
      setSelectedMessage(null);
      setOriginalMessage(null);
      setViewerMode('compose');
    },
    [sendMsg],
  );

  const handleSchedule = useCallback(
    async (messageId: string, scheduledFor: string) => {
      await scheduleMsg.mutateAsync({
        id: messageId,
        payload: { scheduled_for: scheduledFor },
      });
    },
    [scheduleMsg],
  );

  // Determine what to show in center
  const showEmptyState = !selectedMessage && viewerMode !== 'compose' && viewerMode !== 'reply' && viewerMode !== 'forward';

  return (
    <Box
      sx={{
        height: 'calc(100vh - 64px)',
        display: 'flex',
        flexDirection: 'column',
        bgcolor: '#f9fafb',
      }}
    >
      {/* Top Bar */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1.5,
          px: 2,
          py: 1,
          borderBottom: '1px solid',
          borderColor: 'divider',
          bgcolor: '#ffffff',
          flexShrink: 0,
        }}
      >
        {isMobile && !showSidebar && (
          <IconButton
            size="small"
            onClick={() => setShowSidebar(true)}
          >
            <ArrowBack fontSize="small" />
          </IconButton>
        )}
        {isMobile && showSidebar && (
          <IconButton
            size="small"
            onClick={() => setShowSidebar(false)}
          >
            <MenuIcon fontSize="small" />
          </IconButton>
        )}

        <Mail sx={{ color: 'primary.main', fontSize: 20 }} />
        <Typography variant="subtitle1" sx={{ fontWeight: 600, mr: 'auto' }}>
          Mail
        </Typography>

        {/* Account Filter */}
        <FormControl size="small" sx={{ minWidth: 180 }}>
          <Select
            value={accountFilter}
            onChange={(e) => setAccountFilter(e.target.value)}
            displayEmpty
            sx={{ fontSize: '0.8rem' }}
          >
            <MenuItem value="all">All Accounts</MenuItem>
            {accounts.map((acct) => (
              <MenuItem key={acct.id} value={acct.id}>
                {acct.email_address}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <Button
          variant="contained"
          size="small"
          startIcon={<Add />}
          onClick={handleCompose}
          sx={{ textTransform: 'none', flexShrink: 0 }}
        >
          Compose
        </Button>
      </Box>

      {/* Main Content */}
      <Box sx={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {/* Sidebar */}
        {(showSidebar || !isMobile) && (
          <Box
            sx={{
              width: isMobile ? '100%' : SIDEBAR_WIDTH,
              flexShrink: 0,
              overflow: 'hidden',
            }}
          >
            <EmailSidebar
              messages={filteredMessages}
              selectedId={selectedMessage?.id}
              onSelect={handleSelectMessage}
              isLoading={messagesLoading}
            />
          </Box>
        )}

        {/* Email Viewer / Empty State */}
        {(!isMobile || !showSidebar) && (
          <Box sx={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            {showEmptyState ? (
              <Box
                sx={{
                  flex: 1,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexDirection: 'column',
                  gap: 2,
                }}
              >
                <Mail sx={{ fontSize: 48, color: 'text.disabled' }} />
                <Typography variant="body1" color="text.disabled">
                  Select a message or compose a new one
                </Typography>
                <Button
                  variant="outlined"
                  size="small"
                  startIcon={<Add />}
                  onClick={handleCompose}
                  sx={{ textTransform: 'none' }}
                >
                  Compose
                </Button>
              </Box>
            ) : (
              <EmailViewer
                mode={viewerMode}
                message={selectedMessage}
                originalMessage={originalMessage}
                accounts={accounts}
                onSend={handleSend}
                onSchedule={handleSchedule}
                onSaveDraft={handleSaveDraft}
                onClose={handleClose}
                onReply={handleReply}
                onForward={handleForward}
                isSending={sendMsg.isPending}
                isScheduling={scheduleMsg.isPending}
                isSaving={createMsg.isPending || updateMsg.isPending}
              />
            )}
          </Box>
        )}
      </Box>
    </Box>
  );
};

export default MailPage;
