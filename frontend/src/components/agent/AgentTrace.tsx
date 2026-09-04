'use client';

/**
 * AgentTrace — vertical execution timeline with colored dots per agent type.
 * Shows step action text + result preview with active step pulse animation.
 */

import type { AgentStep } from '@/lib/types';

interface AgentTraceProps {
  steps: AgentStep[];
}

const AGENT_COLORS: Record<string, string> = {
  supervisor: 'supervisor',
  rag_agent: 'rag',
  data_agent: 'data',
  file_agent: 'file',
  code_agent: 'code',
  vision_agent: 'vision',
};

export default function AgentTrace({ steps }: AgentTraceProps) {
  if (!steps || steps.length === 0) return null;

  return (
    <div className="agent-trace">
      {steps.map((step, i) => {
        const colorClass = AGENT_COLORS[step.agent] || 'default';
        const isActive = i === steps.length - 1;

        return (
          <div
            key={i}
            className={`trace-step trace-${colorClass} ${isActive ? 'trace-active' : ''}`}
          >
            <div className="trace-dot" />
            <div className="trace-body">
              <span className="trace-agent">{step.agent}</span>
              <span className="trace-action">{step.action}</span>
              {step.result && (
                <div className="trace-result">
                  {step.result.length > 120
                    ? step.result.substring(0, 120) + '...'
                    : step.result}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
