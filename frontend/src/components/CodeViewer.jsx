import React from 'react';

/**
 * Code viewer panel for displaying file contents with syntax-aware styling.
 */
export default function CodeViewer({ filePath, content, onClose }) {
  if (!filePath) {
    return (
      <div className="empty-state" style={{ padding: 'var(--space-xl)' }}>
        <div className="empty-state__icon">👈</div>
        <div className="empty-state__text">
          Select a file from the tree to view its contents.
        </div>
      </div>
    );
  }

  return (
    <div className="code-viewer">
      <div className="code-viewer__header">
        <span className="code-viewer__filename">{filePath}</span>
        <button
          className="btn btn--ghost"
          style={{ padding: '4px 8px', fontSize: '11px' }}
          onClick={onClose}
        >
          ✕ Close
        </button>
      </div>
      <pre className="code-viewer__content">{content || '// Empty file'}</pre>
    </div>
  );
}
