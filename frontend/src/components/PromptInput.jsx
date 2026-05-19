import React from 'react';

/**
 * Prompt input section — landing screen for new sessions.
 */
export default function PromptInput({ onSubmit, loading }) {
  const [prompt, setPrompt] = React.useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (prompt.trim().length >= 10 && !loading) {
      onSubmit(prompt.trim());
    }
  };

  return (
    <div className="prompt-section">
      <div className="prompt-section__hero">
        <h1>FlowState Engine</h1>
        <p>
          Describe what you want to build. Our AI agents will architect,
          code, test, and iterate until your software passes QA — all autonomously.
        </p>
      </div>

      <form className="prompt-card" onSubmit={handleSubmit}>
        <textarea
          id="prompt-input"
          className="prompt-card__textarea"
          placeholder="Describe your project... e.g., 'Build a Redis-like in-memory caching library with TTL expiration, LRU eviction, and thread-safe operations.'"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          disabled={loading}
          autoFocus
        />
        <div className="prompt-card__actions">
          <span className="prompt-card__hint">
            {prompt.length < 10
              ? `${10 - prompt.length} more chars needed`
              : '✓ Ready to submit'}
          </span>
          <button
            type="submit"
            className="btn btn--primary"
            disabled={prompt.trim().length < 10 || loading}
            id="start-orchestration-btn"
          >
            {loading ? (
              <>
                <span className="spinner" /> Starting...
              </>
            ) : (
              <>⚡ Start Orchestration</>
            )}
          </button>
        </div>
      </form>

      <div style={{ display: 'flex', gap: '24px', color: 'var(--text-muted)', fontSize: '13px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ color: 'var(--agent-pm)' }}>●</span> PM Spec
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ color: 'var(--agent-swe)' }}>●</span> SWE Code
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ color: 'var(--agent-qa)' }}>●</span> QA Test
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ color: 'var(--agent-runtime-fail)' }}>●</span> Sandbox
        </div>
      </div>
    </div>
  );
}
