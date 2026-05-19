import React, { useState } from 'react';
import { FILE_ICONS } from '../utils/constants.js';

/**
 * Dynamic workspace file tree that updates in real-time
 * as agents create and modify files.
 */
export default function FileTree({ files, testFiles, onFileSelect, selectedFile }) {
  const getFileIcon = (path) => {
    const ext = '.' + path.split('.').pop();
    const info = FILE_ICONS[ext] || { icon: '📄', cssClass: 'config' };

    // Override for test files
    if (path.includes('test_') || path.includes('.test.')) {
      return { icon: '🧪', cssClass: 'test' };
    }
    return info;
  };

  const buildTree = (filePaths, type) => {
    const tree = {};
    filePaths.forEach((path) => {
      const parts = path.split('/');
      let current = tree;
      parts.forEach((part, i) => {
        if (i === parts.length - 1) {
          current[part] = { __path: path, __type: type };
        } else {
          if (!current[part]) current[part] = {};
          current = current[part];
        }
      });
    });
    return tree;
  };

  const renderTree = (node, depth = 0) => {
    return Object.keys(node)
      .filter((key) => !key.startsWith('__'))
      .sort((a, b) => {
        // Folders first, then files
        const aIsFolder = typeof node[a] === 'object' && !node[a].__path;
        const bIsFolder = typeof node[b] === 'object' && !node[b].__path;
        if (aIsFolder && !bIsFolder) return -1;
        if (!aIsFolder && bIsFolder) return 1;
        return a.localeCompare(b);
      })
      .map((key) => {
        const item = node[key];
        const isFile = item.__path;

        if (isFile) {
          const icon = getFileIcon(item.__path);
          const isActive = selectedFile === item.__path;
          const isTest = item.__type === 'test';

          return (
            <div
              key={item.__path}
              className={`file-tree__item ${isActive ? 'file-tree__item--active' : ''}`}
              style={{ paddingLeft: `${16 + depth * 16}px` }}
              onClick={() => onFileSelect(item.__path, item.__type)}
            >
              <span className={`file-tree__icon file-tree__icon--${icon.cssClass}`}>
                {icon.icon}
              </span>
              <span className="file-tree__name">{key}</span>
              {isTest && (
                <span className="file-tree__badge file-tree__badge--new">TEST</span>
              )}
            </div>
          );
        }

        // Directory node
        return (
          <React.Fragment key={key}>
            <div
              className="file-tree__item"
              style={{ paddingLeft: `${16 + depth * 16}px` }}
            >
              <span className="file-tree__icon file-tree__icon--folder">📁</span>
              <span className="file-tree__name" style={{ fontWeight: 600 }}>{key}/</span>
            </div>
            {renderTree(item, depth + 1)}
          </React.Fragment>
        );
      });
  };

  const allSourceFiles = Object.keys(files || {});
  const allTestFiles = Object.keys(testFiles || {});
  const hasFiles = allSourceFiles.length > 0 || allTestFiles.length > 0;

  if (!hasFiles) {
    return (
      <div className="panel">
        <div className="panel__header">
          <span className="panel__title">Workspace</span>
        </div>
        <div className="empty-state">
          <div className="empty-state__icon">📁</div>
          <div className="empty-state__text">
            Files will appear here as agents write them.
          </div>
        </div>
      </div>
    );
  }

  const tree = {
    ...buildTree(allSourceFiles, 'source'),
    ...buildTree(allTestFiles, 'test'),
  };

  return (
    <div className="panel">
      <div className="panel__header">
        <span className="panel__title">Workspace</span>
        <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
          {allSourceFiles.length + allTestFiles.length} files
        </span>
      </div>
      <div className="panel__body" style={{ padding: 'var(--space-sm) 0' }}>
        <div className="file-tree">{renderTree(tree)}</div>
      </div>
    </div>
  );
}
