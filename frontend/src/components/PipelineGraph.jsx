import React from 'react';
import { PIPELINE_NODES } from '../utils/constants.js';

/**
 * Visual state machine pipeline graph showing agent execution progress.
 * Active node pulses green, completed nodes show checkmarks.
 */
export default function PipelineGraph({ currentAgent, completedNodes, failedNodes, iterationCount }) {
  const completed = new Set(completedNodes || []);
  const failed = new Set(failedNodes || []);

  const getNodeState = (nodeId) => {
    if (currentAgent === nodeId) return 'active';
    if (failed.has(nodeId)) return 'failed';
    if (completed.has(nodeId)) return 'completed';
    return 'idle';
  };

  const getConnectorState = (idx) => {
    const node = PIPELINE_NODES[idx];
    const nextNode = PIPELINE_NODES[idx + 1];
    if (!nextNode) return '';
    if (completed.has(node.id)) return 'completed';
    if (currentAgent === nextNode.id) return 'active';
    return '';
  };

  const getStatusText = (nodeId, state) => {
    if (state === 'active') return 'Executing...';
    if (state === 'completed') return 'Completed ✓';
    if (state === 'failed') return `Failed (iter #${iterationCount || 0})`;
    return 'Waiting';
  };

  return (
    <div className="panel">
      <div className="panel__header">
        <span className="panel__title">Pipeline</span>
        {iterationCount > 0 && (
          <span className="badge badge--running" style={{ fontSize: '10px' }}>
            Iter #{iterationCount}
          </span>
        )}
      </div>
      <div className="panel__body">
        <div className="pipeline">
          {PIPELINE_NODES.map((node, idx) => {
            const state = getNodeState(node.id);
            return (
              <React.Fragment key={node.id}>
                <div className={`pipeline__node pipeline__node--${state}`}>
                  <div className="pipeline__node-dot" />
                  <div className="pipeline__node-info">
                    <div className="pipeline__node-name">{node.label}</div>
                    <div className="pipeline__node-status">
                      {getStatusText(node.id, state)}
                    </div>
                  </div>
                  {state === 'active' && <div className="spinner" />}
                </div>
                {idx < PIPELINE_NODES.length - 1 && (
                  <div className={`pipeline__connector pipeline__connector--${getConnectorState(idx)}`} />
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>
    </div>
  );
}
