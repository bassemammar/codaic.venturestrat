// Outreach Module — barrel export

// Pages
export { MailPage } from './pages/MailPage';

// Components
export { RichTextEditor } from './components/RichTextEditor';
export { EmailViewer } from './components/EmailViewer';
export { EmailSidebar } from './components/EmailSidebar';
export { AIEmailModal } from './components/AIEmailModal';

// Hooks
export { useMessages } from './hooks/useMessages';
export { useEmailAccounts } from './hooks/useEmailAccounts';
export { useSendMessage } from './hooks/useSendMessage';
export { useScheduleMessage, useCancelSchedule } from './hooks/useScheduleMessage';
export { useAIGenerate } from './hooks/useAIGenerate';
export { useAIEdit } from './hooks/useAIEdit';
export { useCreateMessage, useUpdateMessage, useDeleteMessage } from './hooks/useCreateMessage';

// API
export type {
  SendMessageRequest,
  SendMessageResponse,
  ScheduleMessageRequest,
  ScheduleMessageResponse,
  AIGenerateEmailRequest,
  AIGenerateEmailResponse,
  AIEditTextRequest,
  AIEditTextResponse,
} from './api/outreachApi';
