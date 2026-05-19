import React from 'react';

/**
 * App header with logo, session info, and iteration counter.
 */
export default function Header({ sessionId, iterationCount, maxIterations, testStatus }) {
  const getStatusBadge = () => {
    if (!sessionId) return null;
    const statusMap = {
      PENDING: 'pending',
      PASSED: 'passed',
      FAILED: 'failed',
    };
    const cls = statusMap[testStatus] || 'pending';
    return <span className={`badge badge--${cls}`}>{testStatus || 'IDLE'}</span>;
  };

  return (
    <header className="app-header">
      <div className="app-header__logo">
        <div className="app-header__logo-icon">⚡</div>
        <div>
          <div className="app-header__title">FlowState-Engine</div>
          <div className="app-header__subtitle">Multi-Agent Orchestration</div>
        </div>
      </div>

      <div className="app-header__meta">
        {sessionId && (
          <>
            <div className="iteration-display">
              <span>Iteration</span>
              <span className="iteration-display__count">
                {iterationCount || 0}/{maxIterations || 5}
              </span>
            </div>
            {getStatusBadge()}
          </>
        )}
      </div>
    </header>
  );
}
