/**
 * Agent display names, colors, and icon mappings.
 */
export const AGENTS = {
  pm: { label: 'PM', fullName: 'Product Manager', color: '#60a5fa', cssClass: 'pm' },
  swe: { label: 'SWE', fullName: 'Software Engineer', color: '#34d399', cssClass: 'swe' },
  qa: { label: 'QA', fullName: 'QA Engineer', color: '#fbbf24', cssClass: 'qa' },
  runtime: { label: 'RUNTIME', fullName: 'Sandbox Runtime', color: '#f87171', cssClass: 'runtime' },
  system: { label: 'SYSTEM', fullName: 'System', color: '#94a3b8', cssClass: 'system' },
};

/**
 * Pipeline node definitions.
 */
export const PIPELINE_NODES = [
  { id: 'pm', label: 'Product Manager', description: 'Generating specification' },
  { id: 'swe', label: 'Software Engineer', description: 'Writing source code' },
  { id: 'qa', label: 'QA Engineer', description: 'Writing test suite' },
  { id: 'sandbox', label: 'Sandbox Execution', description: 'Running tests in Docker' },
  { id: 'deployment', label: 'Deployment', description: 'All tests passed' },
];

/**
 * File extension to icon/color mapping.
 */
export const FILE_ICONS = {
  '.py': { icon: '🐍', cssClass: 'py' },
  '.js': { icon: '📜', cssClass: 'js' },
  '.ts': { icon: '📘', cssClass: 'ts' },
  '.jsx': { icon: '⚛️', cssClass: 'js' },
  '.tsx': { icon: '⚛️', cssClass: 'ts' },
  '.go': { icon: '🔵', cssClass: 'js' },
  '.json': { icon: '📋', cssClass: 'config' },
  '.txt': { icon: '📄', cssClass: 'config' },
  '.md': { icon: '📝', cssClass: 'config' },
  '.yml': { icon: '⚙️', cssClass: 'config' },
  '.yaml': { icon: '⚙️', cssClass: 'config' },
};

export const API_BASE = '/api';
export const WS_BASE = `ws://${window.location.host}/ws`;
