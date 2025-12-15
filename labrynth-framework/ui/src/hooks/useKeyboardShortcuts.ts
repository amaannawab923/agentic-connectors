import { useEffect } from 'react';

interface KeyboardShortcutHandlers {
  onSave?: () => void;
  onUndo?: () => void;
  onRedo?: () => void;
  onDelete?: () => void;
  onCopy?: () => void;
  onPaste?: () => void;
  onDuplicate?: () => void;
  onSelectAll?: () => void;
  onEscape?: () => void;
  onFitView?: () => void;
}

export function useKeyboardShortcuts({
  onSave,
  onUndo,
  onRedo,
  onDelete,
  onCopy,
  onPaste,
  onDuplicate,
  onSelectAll,
  onEscape,
  onFitView,
}: KeyboardShortcutHandlers) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // Ignore if typing in input/textarea
      const target = e.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') {
        return;
      }

      const isMod = e.metaKey || e.ctrlKey;

      // Save: Cmd+S
      if (isMod && e.key === 's') {
        e.preventDefault();
        onSave?.();
      }

      // Undo: Cmd+Z
      if (isMod && e.key === 'z' && !e.shiftKey) {
        e.preventDefault();
        onUndo?.();
      }

      // Redo: Cmd+Shift+Z
      if (isMod && e.key === 'z' && e.shiftKey) {
        e.preventDefault();
        onRedo?.();
      }

      // Delete: Backspace or Delete
      if (e.key === 'Backspace' || e.key === 'Delete') {
        e.preventDefault();
        onDelete?.();
      }

      // Copy: Cmd+C
      if (isMod && e.key === 'c') {
        onCopy?.();
      }

      // Paste: Cmd+V
      if (isMod && e.key === 'v') {
        onPaste?.();
      }

      // Duplicate: Cmd+D
      if (isMod && e.key === 'd') {
        e.preventDefault();
        onDuplicate?.();
      }

      // Select All: Cmd+A
      if (isMod && e.key === 'a') {
        e.preventDefault();
        onSelectAll?.();
      }

      // Escape: Deselect
      if (e.key === 'Escape') {
        onEscape?.();
      }

      // Fit View: F
      if (e.key === 'f' && !isMod) {
        onFitView?.();
      }
    };

    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [onSave, onUndo, onRedo, onDelete, onCopy, onPaste, onDuplicate, onSelectAll, onEscape, onFitView]);
}
