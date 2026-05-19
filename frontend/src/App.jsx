import React, { useState, useCallback } from 'react';
import { useWebSocket } from './hooks/useWebSocket.js';
import { API_BASE } from './utils/constants.js';
import Header from './components/Header.jsx';
import PromptInput from './components/PromptInput.jsx';
import ChatRail from './components/ChatRail.jsx';
import FileTree from './components/FileTree.jsx';
import PipelineGraph from './components/PipelineGraph.jsx';
import CodeViewer from './components/CodeViewer.jsx';
import StatusBar from './components/StatusBar.jsx';

/**
 * FlowState-Engine — Root Application Component.
 *
 * Orchestrates the full UI: prompt input → dashboard with
 * chat rail, file tree, pipeline graph, and code viewer.
 */
export default function App() {
  // ── Session State ────────────────────────────────────
  const [sessionId, setSessionId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [view, setView] = useState('prompt'); // 'prompt' | 'dashboard'

  // ── Orchestration State ──────────────────────────────
  const [currentAgent, setCurrentAgent] = useState(null);
  const [iterationCount, setIterationCount] = useState(0);
  const [testStatus, setTestStatus] = useState('PENDING');
  const [files, setFiles] = useState({});
  const [testFiles, setTestFiles] = useState({});
  const [completedNodes, setCompletedNodes] = useState([]);
  const [failedNodes, setFailedNodes] = useState([]);

  // ── UI State ─────────────────────────────────────────
  const [selectedFile, setSelectedFile] = useState(null);
  const [selectedFileContent, setSelectedFileContent] = useState('');
  const [chatMessages, setChatMessages] = useState([]);

  // ── WebSocket Event Handlers ─────────────────────────
  const wsHandlers = {
    agent_message: (event) => {
      setChatMessages((prev) => [...prev, event]);
    },
    file_created: (event) => {
      const { path, content, agent } = event.payload;
      if (path?.startsWith('tests/') || path?.includes('test_')) {
        setTestFiles((prev) => ({ ...prev, [path]: content || '' }));
      } else {
        setFiles((prev) => ({ ...prev, [path]: content || '' }));
      }
      setChatMessages((prev) => [...prev, {
        ...event,
        event_type: 'agent_message',
        payload: {
          sender: agent || 'system',
          target: 'system',
          content: `📄 Created file: ${path}`,
        },
      }]);
    },
    file_modified: (event) => {
      const { path, agent } = event.payload;
      setChatMessages((prev) => [...prev, {
        ...event,
        event_type: 'agent_message',
        payload: {
          sender: agent || 'system',
          target: 'system',
          content: `✏️ Modified file: ${path}`,
        },
      }]);
    },
    state_transition: (event) => {
      const { to_node, label } = event.payload;
      if (currentAgent && currentAgent !== to_node) {
        setCompletedNodes((prev) => [...new Set([...prev, currentAgent])]);
      }
      setCurrentAgent(to_node);
      setChatMessages((prev) => [...prev, {
        ...event,
        event_type: 'agent_message',
        payload: {
          sender: 'system',
          target: to_node || 'system',
          content: `🔄 Transitioned to: ${label || to_node}`,
        },
      }]);
    },
    test_result: (event) => {
      const { status, iteration, logs } = event.payload;
      setTestStatus(status);
      setIterationCount(iteration || 0);
      if (status === 'FAILED') {
        setFailedNodes((prev) => [...prev, 'sandbox']);
      }
      setChatMessages((prev) => [...prev, {
        ...event,
        event_type: 'agent_message',
        payload: {
          sender: 'runtime',
          target: status === 'PASSED' ? 'qa' : 'swe',
          content: status === 'PASSED'
            ? `✅ ALL TESTS PASSED (iteration #${iteration})`
            : `❌ TESTS FAILED (iteration #${iteration})\n${(logs || '').substring(0, 500)}`,
        },
      }]);
    },
    iteration_update: (event) => {
      setIterationCount(event.payload.iteration_count || 0);
      setTestStatus(event.payload.test_status || 'PENDING');
    },
    session_complete: (event) => {
      setCompletedNodes((prev) => [...new Set([...prev, 'deployment'])]);
      setChatMessages((prev) => [...prev, {
        ...event,
        event_type: 'agent_message',
        payload: {
          sender: 'system',
          target: 'system',
          content: `🎉 Session complete! ${event.payload.file_count} files, ${event.payload.test_count} tests, ${event.payload.iterations} iterations.`,
        },
      }]);
    },
    error: (event) => {
      setChatMessages((prev) => [...prev, {
        ...event,
        event_type: 'agent_message',
        payload: {
          sender: 'system',
          target: 'system',
          content: `⚠️ ${event.payload.message || 'An error occurred.'}`,
        },
      }]);
    },
  };

  const { connected } = useWebSocket(sessionId, wsHandlers);

  // ── API Calls ────────────────────────────────────────
  const startOrchestration = useCallback(async (userPrompt) => {
    setLoading(true);
    try {
      // 1. Create session
      const createRes = await fetch(`${API_BASE}/session/create`, { method: 'POST' });
      const createData = await createRes.json();
      const newSessionId = createData.id;
      setSessionId(newSessionId);

      // Brief delay to let WebSocket connect
      await new Promise((r) => setTimeout(r, 500));

      // 2. Start orchestration
      const startRes = await fetch(`${API_BASE}/session/${newSessionId}/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_requirement: userPrompt }),
      });

      if (startRes.ok) {
        setView('dashboard');
      } else {
        const err = await startRes.json();
        alert(`Failed to start: ${err.detail || 'Unknown error'}`);
      }
    } catch (err) {
      console.error('Failed to start orchestration:', err);
      alert('Failed to connect to the backend. Is the server running?');
    } finally {
      setLoading(false);
    }
  }, []);

  // ── File Selection ───────────────────────────────────
  const handleFileSelect = useCallback((path, type) => {
    setSelectedFile(path);
    const allFiles = { ...files, ...testFiles };
    setSelectedFileContent(allFiles[path] || '// Content not yet available');
  }, [files, testFiles]);

  const handleCloseFile = useCallback(() => {
    setSelectedFile(null);
    setSelectedFileContent('');
  }, []);

  // ── Render ───────────────────────────────────────────
  if (view === 'prompt') {
    return (
      <div className="app-container">
        <PromptInput onSubmit={startOrchestration} loading={loading} />
      </div>
    );
  }

  return (
    <div className="app-container">
      <Header
        sessionId={sessionId}
        iterationCount={iterationCount}
        maxIterations={5}
        testStatus={testStatus}
      />

      <main className="app-main">
        {/* Left Panel — File Tree */}
        <FileTree
          files={files}
          testFiles={testFiles}
          onFileSelect={handleFileSelect}
          selectedFile={selectedFile}
        />

        {/* Center Panel — Chat Rail + Code Viewer */}
        <div className="panel" style={{ display: 'flex', flexDirection: 'column' }}>
          {selectedFile ? (
            <div style={{ flex: 1, overflow: 'auto', padding: 'var(--space-md)' }}>
              <CodeViewer
                filePath={selectedFile}
                content={selectedFileContent}
                onClose={handleCloseFile}
              />
            </div>
          ) : (
            <ChatRail messages={chatMessages} />
          )}
        </div>

        {/* Right Panel — Pipeline Graph */}
        <PipelineGraph
          currentAgent={currentAgent}
          completedNodes={completedNodes}
          failedNodes={failedNodes}
          iterationCount={iterationCount}
        />
      </main>

      <StatusBar
        connected={connected}
        currentAgent={currentAgent}
        sessionId={sessionId}
        testStatus={testStatus}
      />
    </div>
  );
}
