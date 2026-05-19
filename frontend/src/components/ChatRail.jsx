import React, { useRef, useEffect, useState } from 'react';
import { AGENTS } from '../utils/constants.js';

/**
 * Terminal-style chat rail that streams agent messages in real-time.
 * Each message is color-coded by agent with sender→target notation.
 */
export default function ChatRail({ messages }) {
  const scrollRef = useRef(null);
  const [autoScroll, setAutoScroll] = useState(true);

  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, autoScroll]);

  const handleScroll = (e) => {
    const el = e.target;
    const isAtBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
    setAutoScroll(isAtBottom);
  };

  const formatTime = (timestamp) => {
    if (!timestamp) return '';
    try {
      const d = new Date(timestamp);
      return d.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return '';
    }
  };

  const getAgentInfo = (agentId) => {
    return AGENTS[agentId] || AGENTS.system;
  };

  if (messages.length === 0) {
    return (
      <div className="chat-rail">
        <div className="panel__header">
          <span className="panel__title">Agent Chat Rail</span>
        </div>
        <div className="empty-state">
          <div className="empty-state__icon">💬</div>
          <div className="empty-state__text">
            Agent communications will appear here in real-time once orchestration begins.
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="chat-rail">
      <div className="panel__header">
        <span className="panel__title">Agent Chat Rail</span>
        <span className="badge badge--running" style={{ fontSize: '10px' }}>
          {autoScroll ? 'AUTO-SCROLL' : 'SCROLL LOCKED'}
        </span>
      </div>
      <div className="chat-rail__messages" ref={scrollRef} onScroll={handleScroll}>
        {messages.map((msg, idx) => {
          const sender = getAgentInfo(msg.payload?.sender || msg.payload?.agent || 'system');
          const target = getAgentInfo(msg.payload?.target || 'system');
          const content = msg.payload?.content || msg.payload?.message || JSON.stringify(msg.payload);
          const time = formatTime(msg.timestamp);

          return (
            <div key={idx} className={`chat-message chat-message--${sender.cssClass}`}>
              <div className="chat-message__header">
                <span className={`chat-message__agent chat-message__agent--${sender.cssClass}`}>
                  {sender.label}
                </span>
                <span className="chat-message__arrow">➔</span>
                <span className={`chat-message__agent chat-message__agent--${target.cssClass}`}>
                  {target.label}
                </span>
                <span className="chat-message__time">{time}</span>
              </div>
              <div className="chat-message__content">{content}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
