/**
 * RichTextEditor — contentEditable-based rich text editor with MUI toolbar
 *
 * Uses document.execCommand for formatting (bold, italic, underline, link).
 * No extra dependencies — pure React 18 + MUI.
 */

import React, { useRef, useCallback, useEffect } from 'react';
import Box from '@mui/material/Box';
import Paper from '@mui/material/Paper';
import ToggleButton from '@mui/material/ToggleButton';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';
import Tooltip from '@mui/material/Tooltip';
import {
  FormatBold,
  FormatItalic,
  FormatUnderlined,
  InsertLink,
  FormatListBulleted,
  FormatListNumbered,
} from '@mui/icons-material';

export interface RichTextEditorProps {
  value: string;
  onChange: (html: string) => void;
  placeholder?: string;
  minHeight?: number;
  readOnly?: boolean;
}

export const RichTextEditor: React.FC<RichTextEditorProps> = ({
  value,
  onChange,
  placeholder = 'Write your email...',
  minHeight = 200,
  readOnly = false,
}) => {
  const editorRef = useRef<HTMLDivElement>(null);
  const isInternalUpdate = useRef(false);

  // Sync external value into the editor when it changes externally
  useEffect(() => {
    if (isInternalUpdate.current) {
      isInternalUpdate.current = false;
      return;
    }
    if (editorRef.current && editorRef.current.innerHTML !== value) {
      editorRef.current.innerHTML = value;
    }
  }, [value]);

  const handleInput = useCallback(() => {
    if (editorRef.current) {
      isInternalUpdate.current = true;
      onChange(editorRef.current.innerHTML);
    }
  }, [onChange]);

  const execCommand = useCallback((command: string, val?: string) => {
    editorRef.current?.focus();
    document.execCommand(command, false, val);
    // Trigger change after command
    if (editorRef.current) {
      isInternalUpdate.current = true;
      onChange(editorRef.current.innerHTML);
    }
  }, [onChange]);

  const handleFormat = useCallback(
    (_: React.MouseEvent<HTMLElement>, formats: string[]) => {
      // ToggleButtonGroup gives us the currently active set.
      // We just use the buttons as triggers — no state tracking needed.
      void formats;
    },
    [],
  );

  const handleBold = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    execCommand('bold');
  }, [execCommand]);

  const handleItalic = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    execCommand('italic');
  }, [execCommand]);

  const handleUnderline = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    execCommand('underline');
  }, [execCommand]);

  const handleLink = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    const url = prompt('Enter URL:');
    if (url) {
      execCommand('createLink', url);
    }
  }, [execCommand]);

  const handleBulletList = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    execCommand('insertUnorderedList');
  }, [execCommand]);

  const handleNumberedList = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    execCommand('insertOrderedList');
  }, [execCommand]);

  const showPlaceholder = !value || value === '<br>' || value === '<div><br></div>';

  return (
    <Paper
      variant="outlined"
      sx={{
        border: '1px solid',
        borderColor: 'divider',
        borderRadius: 1,
        overflow: 'hidden',
        bgcolor: 'background.paper',
      }}
    >
      {/* Toolbar */}
      {!readOnly && (
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            px: 0.5,
            py: 0.5,
            borderBottom: '1px solid',
            borderColor: 'divider',
            bgcolor: 'rgba(255,255,255,0.02)',
          }}
        >
          <ToggleButtonGroup
            size="small"
            onChange={handleFormat}
            sx={{
              '& .MuiToggleButton-root': {
                border: 'none',
                borderRadius: 1,
                px: 1,
                py: 0.5,
                color: 'text.secondary',
                '&:hover': { bgcolor: 'rgba(79,195,247,0.08)' },
              },
            }}
          >
            <ToggleButton value="bold" onMouseDown={handleBold}>
              <Tooltip title="Bold (Ctrl+B)">
                <FormatBold fontSize="small" />
              </Tooltip>
            </ToggleButton>
            <ToggleButton value="italic" onMouseDown={handleItalic}>
              <Tooltip title="Italic (Ctrl+I)">
                <FormatItalic fontSize="small" />
              </Tooltip>
            </ToggleButton>
            <ToggleButton value="underline" onMouseDown={handleUnderline}>
              <Tooltip title="Underline (Ctrl+U)">
                <FormatUnderlined fontSize="small" />
              </Tooltip>
            </ToggleButton>
            <ToggleButton value="link" onMouseDown={handleLink}>
              <Tooltip title="Insert Link">
                <InsertLink fontSize="small" />
              </Tooltip>
            </ToggleButton>
            <ToggleButton value="bullet" onMouseDown={handleBulletList}>
              <Tooltip title="Bullet List">
                <FormatListBulleted fontSize="small" />
              </Tooltip>
            </ToggleButton>
            <ToggleButton value="numbered" onMouseDown={handleNumberedList}>
              <Tooltip title="Numbered List">
                <FormatListNumbered fontSize="small" />
              </Tooltip>
            </ToggleButton>
          </ToggleButtonGroup>
        </Box>
      )}

      {/* Editable Area */}
      <Box sx={{ position: 'relative' }}>
        {showPlaceholder && !readOnly && (
          <Box
            sx={{
              position: 'absolute',
              top: 12,
              left: 12,
              color: 'text.disabled',
              pointerEvents: 'none',
              fontSize: '0.875rem',
            }}
          >
            {placeholder}
          </Box>
        )}
        <Box
          ref={editorRef}
          contentEditable={!readOnly}
          suppressContentEditableWarning
          onInput={handleInput}
          sx={{
            minHeight,
            p: 1.5,
            outline: 'none',
            fontSize: '0.875rem',
            lineHeight: 1.6,
            color: 'text.primary',
            '& a': { color: 'primary.main' },
            '& ul, & ol': { pl: 2.5 },
            overflow: 'auto',
          }}
        />
      </Box>
    </Paper>
  );
};

export default RichTextEditor;
