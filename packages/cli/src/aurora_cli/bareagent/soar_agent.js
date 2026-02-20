#!/usr/bin/env node
/**
 * soar-agent.js — SOAR orchestration via bare-agent components.
 *
 * Reads a single JSONL message from stdin with:
 *   { method: "soar", params: { query, context, complexity, model, tool } }
 *
 * Emits JSONL events to stdout:
 *   { type: "plan:ready", data: { steps: [...] } }
 *   { type: "step:start", data: { id, action } }
 *   { type: "step:done", data: { id, result } }
 *   { type: "step:fail", data: { id, error } }
 *   { type: "synthesis:done", data: { answer, confidence, traceability } }
 *   { type: "error", data: { message } }
 *
 * Uses bare-agent: CLIPipe, Planner, StateMachine, Retry, Stream, Loop, runPlan.
 */

'use strict';

const { Planner, StateMachine, Retry, Stream, Loop, runPlan, ProviderError, MaxRoundsError } = require('bare-agent');
const { CLIPipe } = require('bare-agent/providers');
const { JsonlTransport } = require('bare-agent/transports');
const readline = require('readline');

function log(msg) {
  process.stderr.write(`[soar-agent] ${msg}\n`);
}

/**
 * Build a CLIPipe provider with systemPromptFlag and streaming support.
 * v0.2.1: CLIPipe natively separates system messages via --system-prompt flag.
 * v0.3.0: onChunk streams output to stderr in real-time instead of buffering.
 */
function makeProvider(tool, model) {
  const env = { ...process.env };
  delete env.CLAUDECODE;

  return new CLIPipe({
    command: tool,
    args: ['--print', '--model', model],
    systemPromptFlag: '--system-prompt',
    onChunk: (chunk) => process.stderr.write(chunk),
    env,
    timeout: 120000,
  });
}

// ─── Main Orchestrator ─────────────────────────────────────────────

async function orchestrate(params) {
  const { query, context = [], complexity = 'MEDIUM', model = 'sonnet', tool = 'claude' } = params;

  // Wire up bare-agent components
  const provider = makeProvider(tool, model);
  const retry = new Retry({ maxAttempts: 2, backoff: 'exponential', jitter: 'full', timeout: 120000 });
  const stream = new Stream({ transport: new JsonlTransport() });
  const sm = new StateMachine();

  // Log state transitions to stderr for debugging
  sm.onTransition(({ taskId, from, to, event }) => {
    log(`${taskId}: ${from} → ${to} (${event})`);
  });

  const contextInfo = context.length > 0
    ? `Relevant context from memory:\n${context.join('\n---\n')}`
    : '';

  // SIMPLE path: skip Planner, answer directly via Loop
  if (complexity === 'SIMPLE') {
    log(`Simple path for: ${query.slice(0, 80)}...`);

    const steps = [{ id: 's1', action: 'Answer directly', dependsOn: [] }];
    stream.emit({ type: 'plan:ready', data: { steps } });
    stream.emit({ type: 'step:start', taskId: 's1', data: { id: 's1', action: 'Answer directly' } });

    const memContext = contextInfo ? `\n\n${contextInfo}` : '';
    const loop = new Loop({ provider, maxRounds: 1, retry, stream });
    try {
      // v0.3.0: Loop throws by default — no need to check result.error
      const result = await loop.run([{ role: 'user', content: `${query}${memContext}\n\nProvide a thorough answer. Use markdown formatting.` }]);
      const answer = result.text || '';
      stream.emit({ type: 'step:done', taskId: 's1', data: { id: 's1', result: answer.slice(0, 500) } });
      stream.emit({ type: 'synthesis:done', data: { answer, confidence: 0.85, traceability: [] } });
    } catch (err) {
      const errType = err instanceof MaxRoundsError ? 'max_rounds' : err instanceof ProviderError ? 'provider' : 'unknown';
      log(`Simple path ${errType} error: ${err.message}`);
      stream.emit({ type: 'step:fail', taskId: 's1', data: { id: 's1', error: err.message, code: err.code } });
      stream.emit({ type: 'error', data: { message: `Simple path failed: ${err.message}` } });
    }
    return;
  }

  // MEDIUM/COMPLEX/CRITICAL path: Planner → runPlan → Synthesize
  log(`Planning for: ${query.slice(0, 80)}...`);

  // v0.3.0: cacheTTL avoids re-planning identical queries within 60s
  const planner = new Planner({
    provider,
    cacheTTL: 60000,
    prompt: `You are a task planner. You MUST NOT answer the query. You MUST decompose it into research steps.

CRITICAL: Your ONLY output must be a JSON array of steps. No prose, no explanation, no markdown.

Rules:
- For MEDIUM queries: return 2-3 steps
- For COMPLEX queries: return 3-5 steps
- Each step should be independently executable
- Use dependsOn to express ordering constraints (step IDs)
- Steps without dependsOn can run in parallel
- Complexity level: ${complexity}

Output format (JSON array only):
[{"id": "s1", "action": "research step description", "dependsOn": []}, {"id": "s2", "action": "another step", "dependsOn": ["s1"]}]`,
  });

  let steps;
  try {
    steps = await retry.call(() => planner.plan(query, { info: contextInfo }));
  } catch (err) {
    stream.emit({ type: 'error', data: { message: `Planning failed: ${err.message}` } });
    return;
  }

  if (!steps || steps.length === 0) {
    stream.emit({ type: 'error', data: { message: 'Planner returned no steps' } });
    return;
  }

  stream.emit({
    type: 'plan:ready',
    data: {
      steps: steps.map(s => ({ id: s.id, action: s.action, dependsOn: s.dependsOn || [] })),
    },
  });

  // Phase 5: COLLECT — execute steps via runPlan (wave-parallel, dep-aware)
  // Collect results for synthesis — runPlan's executeFn receives step, returns result
  const stepResults = {};

  let waveNumber = 0;
  const planResults = await runPlan(steps, async (step) => {
    // Build context from prior step results (deps are guaranteed done by runPlan)
    let priorContext = '';
    if (step.dependsOn && step.dependsOn.length > 0) {
      const deps = step.dependsOn
        .filter(id => stepResults[id])
        .map(id => `[${id}]: ${stepResults[id]}`);
      if (deps.length > 0) {
        priorContext = `\n\nPrior step results:\n${deps.join('\n\n')}`;
      }
    }

    const memContext = context.length > 0
      ? `\n\nRelevant context from memory:\n${context.slice(0, 3).join('\n---\n')}`
      : '';

    const prompt = `You are executing a research/analysis step as part of answering: "${query}"

Your task for this step: ${step.action}${priorContext}${memContext}

Provide a thorough, focused answer for this specific step. Be concrete and specific.`;

    // v0.3.0: Loop throws by default — no need to check result.error
    const loop = new Loop({ provider, maxRounds: 1, retry, stream });
    const result = await loop.run([{ role: 'user', content: prompt }]);
    const text = result.text || '';
    stepResults[step.id] = text;
    return text;
  }, {
    stateMachine: sm,
    stepRetry: new Retry({ maxAttempts: 2, backoff: 'exponential', jitter: 'full' }),
    onWaveStart: (num, waveSteps) => {
      waveNumber = num;
      const ids = waveSteps.map(s => s.id).join(', ');
      stream.emit({ type: 'wave:start', data: { wave: num, steps: waveSteps.map(s => s.id) } });
      log(`Wave ${num}: ${ids}`);
    },
    onStepStart: (step) => {
      stream.emit({ type: 'step:start', taskId: step.id, data: { id: step.id, action: step.action } });
    },
    onStepDone: (step, result) => {
      const text = typeof result === 'string' ? result : '';
      stream.emit({ type: 'step:done', taskId: step.id, data: { id: step.id, result: text.slice(0, 500) } });
    },
    onStepFail: (step, err) => {
      stream.emit({ type: 'step:fail', taskId: step.id, data: { id: step.id, error: err.message } });
    },
  });

  // Check completed steps
  const completedSteps = planResults.filter(r => r.status === 'done');

  if (completedSteps.length === 0) {
    stream.emit({ type: 'error', data: { message: 'All steps failed, cannot synthesize' } });
    return;
  }

  // Phase 6: SYNTHESIZE — combine results via Loop
  log('Synthesizing results...');

  const findings = completedSteps.map(r => {
    const text = stepResults[r.id] || '(no result)';
    const step = steps.find(s => s.id === r.id);
    const truncated = text.length > 2000 ? text.slice(0, 2000) + '\n... (truncated)' : text;
    return `## Step ${r.id}: ${step ? step.action : r.id}\n${truncated}`;
  }).join('\n\n');

  const synthesisPrompt = `You are synthesizing research findings into a final answer.

Original query: ${query}

Research findings:
${findings}

Instructions:
1. Combine the findings into a coherent, well-structured answer
2. Use markdown formatting (## headers, bullet points, bold)
3. At the very end, on its own line, write: CONFIDENCE: 0.XX (your confidence score 0.0-1.0)

Write the answer directly in markdown. Do NOT wrap it in JSON.`;

  try {
    // v0.3.0: Loop throws ProviderError/MaxRoundsError on failure
    const synthesisLoop = new Loop({ provider, maxRounds: 1, retry, stream });
    const synthResult = await synthesisLoop.run([{ role: 'user', content: synthesisPrompt }]);
    const text = synthResult.text || '';

    // Extract confidence from trailing "CONFIDENCE: 0.XX" line
    let answer = text;
    let confidence = 0.7;
    const confMatch = text.match(/CONFIDENCE:\s*([\d.]+)\s*$/m);
    if (confMatch) {
      confidence = parseFloat(confMatch[1]) || 0.7;
      answer = text.slice(0, confMatch.index).trim();
    }

    stream.emit({
      type: 'synthesis:done',
      data: { answer, confidence, traceability: [] },
    });
  } catch (err) {
    const retryable = err instanceof ProviderError ? err.retryable : false;
    log(`Synthesis ${err.constructor.name} (retryable=${retryable}): ${err.message}`);
    stream.emit({ type: 'error', data: { message: `Synthesis failed: ${err.message}`, code: err.code } });
  }
}

// ─── Entry Point ───────────────────────────────────────────────────

async function main() {
  const rl = readline.createInterface({ input: process.stdin });

  for await (const line of rl) {
    const trimmed = line.trim();
    if (!trimmed) continue;

    let msg;
    try {
      msg = JSON.parse(trimmed);
    } catch (err) {
      process.stdout.write(JSON.stringify({ type: 'error', data: { message: `Invalid JSON: ${err.message}` } }) + '\n');
      continue;
    }

    if (msg.method === 'soar') {
      try {
        await orchestrate(msg.params || {});
      } catch (err) {
        process.stdout.write(JSON.stringify({ type: 'error', data: { message: `Orchestration error: ${err.message}` } }) + '\n');
      }
    } else {
      process.stdout.write(JSON.stringify({ type: 'error', data: { message: `Unknown method: ${msg.method}` } }) + '\n');
    }
  }
}

main().catch(err => {
  process.stdout.write(JSON.stringify({ type: 'error', data: { message: `Fatal: ${err.message}` } }) + '\n');
  process.exit(1);
});
