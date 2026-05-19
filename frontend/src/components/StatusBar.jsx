import React from 'react';

/**
 * Bottom status bar showing connection status, current agent, and session info.
 */
export default function StatusBar({ connected, currentAgent, sessionId, testStatus }) {
  return (
    <footer className="status-bar">
      <div className="status-bar__left">
        <div className="status-bar__indicator">
          <span className={`status-bar__dot ${!connected ? 'status-bar__dot--disconnected' : ''}`} />
          <span>{connected ? 'Connected' : 'Disconnected'}</span>
        </div>
        {sessionId && (
          <span style={{ fontFamily: 'var(--font-mono)' }}>
            Session: {sessionId}
          </span>
        )}
      </div>
      <div className="status-bar__right">
        {currentAgent && (
          <span>
            Active Agent: <strong style={{ textTransform: 'uppercase' }}>{currentAgent}</strong>
          </span>
        )}
        {testStatus && testStatus !== 'PENDING' && (
          <span>
            Tests: <strong>{testStatus}</strong>
          </span>
        )}
      </div>
    </footer>
  );
}
