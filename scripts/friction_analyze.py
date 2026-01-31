#!/usr/bin/env python3
"""
Friction analyzer - Extract signals and analyze patterns.

Usage:
    python friction_analyze.py <sessions-directory>
    python friction_analyze.py session.jsonl
"""

import json
import re
import sys
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone

def load_config(config_path=None):
    """Load weights from JSON config."""
    if config_path is None:
        config_path = Path(__file__).parent / 'friction_config.json'

    with open(config_path) as f:
        return json.load(f)

def derive_session_name(session_file, metadata):
    """Derive a human-readable session name from path and metadata."""
    # Get project name from parent directory
    parent = session_file.parent.name

    # Extract project name from Claude Code directory format
    # Format: -home-user-path-to-project-name or just project-name
    if parent.startswith('-'):
        # Look for common path prefixes to strip
        for prefix in ['-home-hamr-PycharmProjects-', '-home-hamr-Documents-PycharmProjects-',
                       '-home-hamr-', '-home-', '-']:
            if parent.startswith(prefix):
                project = parent[len(prefix):]
                break
        else:
            # Fallback: just remove leading dash
            project = parent[1:]
    else:
        project = parent

    # Get date from metadata or file
    date_str = ''
    if metadata.get('started_at'):
        try:
            dt = datetime.fromisoformat(metadata['started_at'].replace('Z', '+00:00'))
            date_str = dt.strftime('%m%d-%H%M')
        except:
            pass

    if not date_str:
        # Fallback to file mtime
        try:
            mtime = datetime.fromtimestamp(session_file.stat().st_mtime)
            date_str = mtime.strftime('%m%d-%H%M')
        except:
            date_str = 'unknown'

    # Short UUID suffix for uniqueness
    short_id = session_file.stem[:8]

    return f'{project}/{date_str}-{short_id}'


def extract_signals(session_file):
    """Extract raw signals from session JSONL."""
    signals = []
    llm_claimed_success = False
    tool_history = []
    metadata = {}

    with open(session_file) as f:
        events = [json.loads(line) for line in f if line.strip()]

    # Extract metadata and count turns
    turn_count = 0
    user_messages = []  # Track for repeated_question detection
    prev_user_ts = None  # Track for long_silence detection

    for event in events:
        if 'gitBranch' in event:
            metadata['git_branch'] = event['gitBranch']
        if 'cwd' in event:
            metadata['cwd'] = event['cwd']
        if 'timestamp' in event:
            if 'started_at' not in metadata:
                metadata['started_at'] = event['timestamp']
            metadata['ended_at'] = event['timestamp']

        # Count user turns and track messages
        if event.get('type') == 'user':
            content = event.get('message', {}).get('content', {})
            ts = event.get('timestamp', '')

            if isinstance(content, str):
                turn_count += 1
                # Store for repeated question detection (first 100 chars normalized)
                msg_key = content[:100].lower().strip()
                user_messages.append((ts, msg_key))

                # Check for long silence (>10 min gap)
                if prev_user_ts and ts:
                    try:
                        t1 = datetime.fromisoformat(prev_user_ts.replace('Z', '+00:00'))
                        t2 = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                        gap_min = (t2 - t1).total_seconds() / 60
                        if gap_min > 10:
                            signals.append({
                                'ts': ts,
                                'source': 'user',
                                'signal': 'long_silence',
                                'details': f'{gap_min:.0f} min gap',
                                'gap_minutes': gap_min
                            })
                    except:
                        pass
                prev_user_ts = ts

        # Check for compaction/summary events (context overflow indicator)
        if event.get('type') == 'summary':
            summary_text = event.get('summary', '')
            # Ignore normal exit summaries
            if summary_text and 'exited' not in summary_text.lower():
                ts = event.get('timestamp', metadata.get('ended_at', ''))
                signals.append({
                    'ts': ts,
                    'source': 'system',
                    'signal': 'compaction',
                    'details': summary_text[:50]
                })

    metadata['turn_count'] = turn_count
    is_interactive = turn_count > 1

    # Detect repeated questions (same message asked twice)
    seen_messages = {}
    for ts, msg_key in user_messages:
        if msg_key in seen_messages and len(msg_key) > 20:  # Ignore very short messages
            signals.append({
                'ts': ts,
                'source': 'user',
                'signal': 'repeated_question',
                'details': msg_key[:50]
            })
        seen_messages[msg_key] = ts

    # Extract signals
    for event in events:
        ts = event.get('timestamp', '')

        # Tool results (OBJECTIVE)
        if event.get('type') == 'user':
            content = event.get('message', {}).get('content', {})

            # Handle list of content blocks (Claude Code format)
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get('type') == 'tool_result':
                        result = str(block.get('content', ''))

                        # Check for user interruption (Ctrl+C, Escape, SIGKILL)
                        if re.search(r'Exit code 137|Request interrupted|interrupted by user', result, re.I):
                            signals.append({
                                'ts': ts,
                                'source': 'user',
                                'signal': 'request_interrupted',
                                'details': result[:100]
                            })
                        # Match non-zero exit codes or Python tracebacks (excluding 137 which is interruption)
                        elif (re.search(r'Exit code [1-9]', result) and 'Exit code 137' not in result) or \
                             re.search(r'Traceback \(most recent|CalledProcessError', result):
                            signals.append({
                                'ts': ts,
                                'source': 'tool',
                                'signal': 'exit_error',
                                'details': result[:100]
                            })

                            if llm_claimed_success:
                                signals.append({
                                    'ts': ts,
                                    'source': 'llm',
                                    'signal': 'false_success',
                                    'details': 'LLM claimed success but tool failed'
                                })
                            llm_claimed_success = False

                        elif re.search(r'Exit code 0', result):
                            signals.append({
                                'ts': ts,
                                'source': 'tool',
                                'signal': 'exit_success',
                                'details': ''
                            })
                            llm_claimed_success = False

                    elif isinstance(block, dict) and block.get('type') == 'text':
                        # User text in a list block
                        text = block.get('text', '')
                        if text:
                            content = text  # Fall through to user message handling below
                            break
                else:
                    content = None  # No user text found in list

            # Handle single dict tool_result (legacy format)
            if isinstance(content, dict) and content.get('type') == 'tool_result':
                result = str(content.get('content', ''))

                if re.search(r'Exit code [1-9]|Traceback \(most recent|CalledProcessError', result):
                    signals.append({
                        'ts': ts,
                        'source': 'tool',
                        'signal': 'exit_error',
                        'details': result[:100]
                    })

                    if llm_claimed_success:
                        signals.append({
                            'ts': ts,
                            'source': 'llm',
                            'signal': 'false_success',
                            'details': 'LLM claimed success but tool failed'
                        })

                elif re.search(r'Exit code 0', result):
                    signals.append({
                        'ts': ts,
                        'source': 'tool',
                        'signal': 'exit_success',
                        'details': ''
                    })

                llm_claimed_success = False

            # User messages (GOLD)
            if isinstance(content, str):
                if '/stash' in content.lower():
                    signals.append({
                        'ts': ts,
                        'source': 'user',
                        'signal': 'user_intervention',
                        'details': 'stash'
                    })

                # Check for interruption in text messages (ESC / Ctrl+C)
                if re.search(r'Request interrupted|interrupted by user', content, re.I):
                    signals.append({
                        'ts': ts,
                        'source': 'user',
                        'signal': 'request_interrupted',
                        'details': content[:100]
                    })

                if re.search(r'\b(fuck|shit|damn)\b', content, re.I):
                    signals.append({
                        'ts': ts,
                        'source': 'user',
                        'signal': 'user_curse',
                        'details': content[:50]
                    })

                # Only count negation in multi-turn sessions (one-shot = system prompt noise)
                if is_interactive and re.search(r'\b(no|didn\'t work|still broken)\b', content, re.I):
                    signals.append({
                        'ts': ts,
                        'source': 'user',
                        'signal': 'user_negation',
                        'details': content[:50]
                    })

        # Assistant messages (LLM patterns)
        if event.get('type') == 'assistant':
            content = event.get('message', {}).get('content', [])

            if isinstance(content, list):
                # Success claims
                text = ' '.join(b.get('text', '') for b in content if b.get('type') == 'text')
                if re.search(r'\b(done|complete|success|✅)\b', text, re.I):
                    llm_claimed_success = True

                # Tool loops
                for block in content:
                    if block.get('type') == 'tool_use':
                        tool_name = block['name']
                        sig = (tool_name, json.dumps(block.get('input', {})))
                        tool_history.append(sig)

                        count = tool_history.count(sig)
                        if count >= 3:
                            signals.append({
                                'ts': ts,
                                'source': 'llm',
                                'signal': 'tool_loop',
                                'details': f"{tool_name} called {count}x",
                                'tool': tool_name,
                                'loop_count': count
                            })

    # === POST-PROCESSING SIGNALS (session-level analysis) ===

    # 1. interrupt_cascade: 2+ request_interrupted within 60s
    interrupt_times = []
    for sig in signals:
        if sig['signal'] == 'request_interrupted' and sig.get('ts'):
            try:
                t = datetime.fromisoformat(sig['ts'].replace('Z', '+00:00'))
                interrupt_times.append(t)
            except:
                pass

    for i in range(1, len(interrupt_times)):
        gap_sec = (interrupt_times[i] - interrupt_times[i-1]).total_seconds()
        if gap_sec <= 60:
            signals.append({
                'ts': interrupt_times[i].isoformat(),
                'source': 'user',
                'signal': 'interrupt_cascade',
                'details': f'{gap_sec:.0f}s between interrupts',
                'gap_seconds': gap_sec
            })

    # 2. Analyze signal sequence for session-end patterns
    has_errors = any(s['signal'] == 'exit_error' for s in signals)
    has_success = any(s['signal'] == 'exit_success' for s in signals)
    has_intervention = any(s['signal'] == 'user_intervention' for s in signals)

    # Get last few signals
    last_5_signals = [s['signal'] for s in signals[-5:]] if signals else []

    # Calculate friction in last 5 signals
    friction_weights = {
        'exit_error': 1, 'user_curse': 5, 'user_negation': 1,
        'tool_loop': 6, 'false_success': 8, 'request_interrupted': 4,
        'interrupt_cascade': 7, 'repeated_question': 3
    }
    last_5_friction = sum(friction_weights.get(s, 0) for s in last_5_signals)

    # 3. rapid_exit: < 3 turns, ends with error or interruption
    if turn_count <= 3 and turn_count > 0:
        if last_5_signals and last_5_signals[-1] in ('exit_error', 'request_interrupted'):
            signals.append({
                'ts': metadata.get('ended_at', ''),
                'source': 'session',
                'signal': 'rapid_exit',
                'details': f'{turn_count} turns, ended with {last_5_signals[-1]}'
            })

    # 4. no_resolution: errors without subsequent success (and no intervention)
    if has_errors and not has_success and not has_intervention and turn_count > 1:
        signals.append({
            'ts': metadata.get('ended_at', ''),
            'source': 'session',
            'signal': 'no_resolution',
            'details': f'{sum(1 for s in signals if s["signal"] == "exit_error")} errors, no success'
        })

    # 5. session_abandoned: high friction at end, no clean exit
    if last_5_friction >= 8 and not has_success and not has_intervention and turn_count > 2:
        signals.append({
            'ts': metadata.get('ended_at', ''),
            'source': 'session',
            'signal': 'session_abandoned',
            'details': f'friction {last_5_friction} in last 5 signals, no resolution'
        })

    return signals, metadata

def analyze_session(session_id, signals, metadata, config):
    """Calculate friction breakdown from signals."""
    weights = config['weights']

    # Calculate friction by source
    by_source = defaultdict(lambda: {
        'total_friction': 0,
        'signal_count': 0,
        'signals': defaultdict(lambda: {'count': 0, 'total_weight': 0})
    })

    friction_trajectory = []
    running_friction = 0

    # Track momentum separately (positive signals don't cancel friction)
    momentum = 0
    error_count = 0
    success_count = 0

    for sig in signals:
        source = sig['source']
        signal_type = sig['signal']
        weight = weights.get(signal_type, 0)

        # Track success/error counts for ratio
        if signal_type == 'exit_success':
            success_count += 1
            momentum += 1
        elif signal_type == 'exit_error':
            error_count += 1

        # Update by source
        by_source[source]['total_friction'] += weight
        by_source[source]['signal_count'] += 1
        by_source[source]['signals'][signal_type]['count'] += 1
        by_source[source]['signals'][signal_type]['total_weight'] += weight

        # Trajectory (only accumulate positive weights as friction)
        if weight > 0:
            running_friction += weight
            friction_trajectory.append(running_friction)
        elif friction_trajectory:
            friction_trajectory.append(friction_trajectory[-1])
        else:
            friction_trajectory.append(0)

    # Convert defaultdicts to regular dicts
    by_source = {
        source: {
            'total_friction': data['total_friction'],
            'signal_count': data['signal_count'],
            'signals': dict(data['signals'])
        }
        for source, data in by_source.items()
    }

    # Detect patterns
    patterns = []
    peak_friction = max(friction_trajectory) if friction_trajectory else 0
    final_friction = friction_trajectory[-1] if friction_trajectory else 0

    # Learning moment detection
    if peak_friction >= config['thresholds']['friction_peak'] and final_friction < 5:
        patterns.append({
            'type': 'learning_moment',
            'friction_before': peak_friction,
            'friction_after': final_friction
        })

    # Sequence detection
    signal_seq = [s['signal'] for s in signals]
    for i in range(len(signal_seq) - 2):
        seq = tuple(signal_seq[i:i+3])
        if seq == ('exit_error', 'false_success', 'user_curse'):
            patterns.append({
                'type': 'false_success_loop',
                'sequence': list(seq),
                'count': 1
            })

    # Calculate duration
    duration_min = 0
    if metadata.get('started_at') and metadata.get('ended_at'):
        try:
            start = datetime.fromisoformat(metadata['started_at'].replace('Z', '+00:00'))
            end = datetime.fromisoformat(metadata['ended_at'].replace('Z', '+00:00'))
            duration_min = int((end - start).total_seconds() / 60)
        except:
            pass

    metadata['duration_min'] = duration_min

    # Calculate error ratio (errors / total tool runs)
    total_tool_runs = success_count + error_count
    error_ratio = error_count / total_tool_runs if total_tool_runs > 0 else 0

    # Session quality assessment
    has_intervention = any(s['signal'] == 'user_intervention' for s in signals)
    has_abandoned = any(s['signal'] == 'session_abandoned' for s in signals)
    has_curse = any(s['signal'] == 'user_curse' for s in signals)
    has_false_success = any(s['signal'] == 'false_success' for s in signals)

    if has_intervention or has_abandoned:
        quality = 'BAD'  # User gave up (explicit or silent)
    elif has_curse or has_false_success:
        quality = 'FRICTION'  # Frustration detected
    elif peak_friction >= config['thresholds']['friction_peak']:
        quality = 'ROUGH'  # High friction but completed
    elif error_ratio > 0.5 and error_count > 3:
        quality = 'ROUGH'  # Many errors
    elif metadata.get('turn_count', 0) <= 1:
        quality = 'ONE-SHOT'  # Not interactive
    else:
        quality = 'OK'  # No significant friction

    return {
        'session_id': session_id,
        'session_metadata': metadata,
        'friction_summary': {
            'peak': peak_friction,
            'final': final_friction,
            'total_signals': len(signals),
            'learning_moments': len([p for p in patterns if p['type'] == 'learning_moment'])
        },
        'momentum': {
            'success_count': success_count,
            'error_count': error_count,
            'error_ratio': round(error_ratio, 2)
        },
        'quality': quality,
        'by_source': by_source,
        'friction_trajectory': friction_trajectory,
        'patterns_detected': patterns
    }

def aggregate_sessions(analyses, config):
    """Aggregate across all sessions."""
    aggregate_by_source = defaultdict(lambda: {
        'sessions_with_signals': 0,
        'total_friction': 0,
        'top_signals': Counter()
    })

    # Per-project aggregation
    by_project = defaultdict(lambda: {
        'total_sessions': 0,
        'interactive_sessions': 0,
        'bad_sessions': 0,
        'total_friction': 0,
        'total_duration_min': 0,
        'total_turns': 0
    })

    all_patterns = []
    high_friction_count = 0
    intervention_count = 0

    for analysis in analyses:
        peak = analysis['friction_summary']['peak']
        quality = analysis.get('quality', 'UNKNOWN')
        session_id = analysis.get('session_id', '')
        metadata = analysis.get('session_metadata', {})

        # Extract project name from session_id (format: "project/date-id")
        project = session_id.split('/')[0] if '/' in session_id else 'unknown'

        # Per-project stats
        by_project[project]['total_sessions'] += 1
        if metadata.get('turn_count', 0) > 1:
            by_project[project]['interactive_sessions'] += 1
        if quality == 'BAD':
            by_project[project]['bad_sessions'] += 1
        by_project[project]['total_friction'] += peak
        by_project[project]['total_duration_min'] += metadata.get('duration_min', 0)
        by_project[project]['total_turns'] += metadata.get('turn_count', 0)

        if peak >= config['thresholds']['friction_peak']:
            high_friction_count += 1

        # By source aggregation
        for source, data in analysis['by_source'].items():
            aggregate_by_source[source]['sessions_with_signals'] += 1
            aggregate_by_source[source]['total_friction'] += data['total_friction']

            for signal_type, signal_data in data['signals'].items():
                aggregate_by_source[source]['top_signals'][signal_type] += signal_data['count']

        # Patterns
        all_patterns.extend(analysis['patterns_detected'])

        # Interventions (explicit /stash OR silent abandonment)
        if 'user' in analysis['by_source']:
            if 'user_intervention' in analysis['by_source']['user']['signals']:
                intervention_count += 1
        if 'session' in analysis['by_source']:
            if 'session_abandoned' in analysis['by_source']['session']['signals']:
                intervention_count += 1

    # Calculate metrics
    intervention_pred = intervention_count / high_friction_count if high_friction_count > 0 else 0

    total_objective = (aggregate_by_source.get('tool', {}).get('total_friction', 0) +
                      aggregate_by_source.get('user', {}).get('total_friction', 0))
    total_llm = aggregate_by_source.get('llm', {}).get('total_friction', 1)  # Avoid division by zero
    snr = abs(total_objective / total_llm) if total_llm != 0 else 0

    # Verdict
    thresholds = config['thresholds']
    reasons = []
    actions = []

    if snr < thresholds['signal_noise_ratio']:
        status = 'BLOAT'
        reasons.append(f'Signal/noise ratio: {snr:.1f} (threshold: {thresholds["signal_noise_ratio"]})')
    elif intervention_pred < thresholds['intervention_predictability']:
        status = 'INCONCLUSIVE'
        reasons.append(f'Intervention predictability: {intervention_pred:.0%} (threshold: {thresholds["intervention_predictability"]:.0%})')
    else:
        status = 'USEFUL'
        reasons.append(f'Intervention predictability: {intervention_pred:.0%} (threshold: {thresholds["intervention_predictability"]:.0%})')
        reasons.append(f'Signal/noise ratio: {snr:.1f} (threshold: {thresholds["signal_noise_ratio"]})')

        # Recommendations
        user_curses = aggregate_by_source.get('user', {}).get('top_signals', {}).get('user_curse', 0)
        if user_curses > 5:
            actions.append('Consider increasing user_curse weight (high occurrence)')

        false_success_loops = len([p for p in all_patterns if p.get('type') == 'false_success_loop'])
        if false_success_loops > 3:
            actions.append('Create antigen for false_success pattern')

    # Convert to regular dicts
    aggregate_by_source_dict = {}
    for source, data in aggregate_by_source.items():
        sessions_count = data['sessions_with_signals']
        aggregate_by_source_dict[source] = {
            'sessions_with_signals': sessions_count,
            'total_friction': data['total_friction'],
            'avg_friction_per_session': data['total_friction'] / sessions_count if sessions_count > 0 else 0,
            'top_signals': dict(data['top_signals'].most_common())
        }

    # Common sequences
    sequence_counts = Counter()
    for analysis in analyses:
        signal_seq = []
        for sig in []:  # Would need raw signals, simplified for now
            signal_seq.append(sig['signal'])
        for i in range(len(signal_seq) - 2):
            seq = tuple(signal_seq[i:i+3])
            sequence_counts[seq] += 1

    common_sequences = [
        {'pattern': list(seq), 'occurrences': count}
        for seq, count in sequence_counts.most_common(5)
    ]

    # Calculate per-project averages
    project_stats = {}
    for project, data in by_project.items():
        total = data['total_sessions']
        interactive = data['interactive_sessions']
        project_stats[project] = {
            'total_sessions': total,
            'interactive_sessions': interactive,
            'bad_sessions': data['bad_sessions'],
            'bad_rate': round(data['bad_sessions'] / interactive, 2) if interactive > 0 else 0,
            'avg_friction': round(data['total_friction'] / total, 1) if total > 0 else 0,
            'avg_duration_min': round(data['total_duration_min'] / total, 1) if total > 0 else 0,
            'avg_turns': round(data['total_turns'] / total, 1) if total > 0 else 0
        }

    # Overall averages (interactive sessions only)
    total_interactive = sum(d['interactive_sessions'] for d in by_project.values())
    total_bad = sum(d['bad_sessions'] for d in by_project.values())
    total_friction = sum(d['total_friction'] for d in by_project.values())
    total_duration = sum(d['total_duration_min'] for d in by_project.values())
    total_turns = sum(d['total_turns'] for d in by_project.values())
    total_sessions = len(analyses)

    overall_stats = {
        'total_sessions': total_sessions,
        'interactive_sessions': total_interactive,
        'bad_sessions': total_bad,
        'bad_rate': round(total_bad / total_interactive, 2) if total_interactive > 0 else 0,
        'avg_friction': round(total_friction / total_sessions, 1) if total_sessions > 0 else 0,
        'avg_duration_min': round(total_duration / total_sessions, 1) if total_sessions > 0 else 0,
        'avg_turns': round(total_turns / total_sessions, 1) if total_sessions > 0 else 0
    }

    # Time-series: daily stats
    by_day = defaultdict(lambda: {'total': 0, 'interactive': 0, 'bad': 0, 'friction': 0})
    for analysis in analyses:
        started = analysis.get('session_metadata', {}).get('started_at', '')
        if started:
            try:
                dt = datetime.fromisoformat(started.replace('Z', '+00:00'))
                day = dt.strftime('%Y-%m-%d')
                by_day[day]['total'] += 1
                if analysis.get('session_metadata', {}).get('turn_count', 0) > 1:
                    by_day[day]['interactive'] += 1
                if analysis.get('quality') == 'BAD':
                    by_day[day]['bad'] += 1
                by_day[day]['friction'] += analysis.get('friction_summary', {}).get('peak', 0)
            except:
                pass

    daily_stats = []
    for day in sorted(by_day.keys()):
        d = by_day[day]
        daily_stats.append({
            'date': day,
            'total': d['total'],
            'interactive': d['interactive'],
            'bad': d['bad'],
            'bad_rate': round(d['bad'] / d['interactive'], 2) if d['interactive'] > 0 else 0,
            'avg_friction': round(d['friction'] / d['total'], 1) if d['total'] > 0 else 0
        })

    # Best and worst sessions (interactive only)
    interactive_analyses = [a for a in analyses if a.get('session_metadata', {}).get('turn_count', 0) > 1]

    worst_session = None
    best_session = None

    if interactive_analyses:
        # Worst: highest friction
        worst_session = max(interactive_analyses, key=lambda x: x.get('friction_summary', {}).get('peak', 0))

        # Best: lowest friction among OK sessions, or lowest overall if no OK
        ok_sessions = [a for a in interactive_analyses if a.get('quality') == 'OK']
        if ok_sessions:
            best_session = min(ok_sessions, key=lambda x: x.get('friction_summary', {}).get('peak', 0))
        else:
            best_session = min(interactive_analyses, key=lambda x: x.get('friction_summary', {}).get('peak', 0))

    return {
        'analyzed_at': datetime.now(timezone.utc).isoformat(),
        'sessions_analyzed': len(analyses),
        'config_used': config,
        'aggregate_by_source': aggregate_by_source_dict,
        'by_project': project_stats,
        'overall': overall_stats,
        'daily_stats': daily_stats,
        'best_session': {
            'session_id': best_session.get('session_id'),
            'quality': best_session.get('quality'),
            'peak_friction': best_session.get('friction_summary', {}).get('peak', 0),
            'turns': best_session.get('session_metadata', {}).get('turn_count', 0),
            'duration_min': best_session.get('session_metadata', {}).get('duration_min', 0)
        } if best_session else None,
        'worst_session': {
            'session_id': worst_session.get('session_id'),
            'quality': worst_session.get('quality'),
            'peak_friction': worst_session.get('friction_summary', {}).get('peak', 0),
            'turns': worst_session.get('session_metadata', {}).get('turn_count', 0),
            'duration_min': worst_session.get('session_metadata', {}).get('duration_min', 0)
        } if worst_session else None,
        'correlations': {
            'high_friction_sessions': high_friction_count,
            'intervention_sessions': intervention_count,
            'intervention_predictability': round(intervention_pred, 2)
        },
        'common_sequences': common_sequences,
        'verdict': {
            'status': status,
            'reasons': reasons,
            'recommended_actions': actions
        }
    }

def format_duration(minutes):
    """Format duration in human-readable form."""
    if minutes < 60:
        return f'{minutes}m'
    hours = minutes // 60
    mins = minutes % 60
    return f'{hours}h{mins}m' if mins else f'{hours}h'

def print_box(title, lines, width=60):
    """Print a bordered box with title and content."""
    print(f'┌{"─" * (width - 2)}┐')
    print(f'│ {title.upper():<{width - 4}} │')
    print(f'├{"─" * (width - 2)}┤')
    for line in lines:
        # Handle line that may be too long
        if len(line) > width - 4:
            line = line[:width - 7] + '...'
        print(f'│ {line:<{width - 4}} │')
    print(f'└{"─" * (width - 2)}┘')

def print_table(headers, rows, col_widths=None):
    """Print a formatted table."""
    if not col_widths:
        col_widths = [max(len(str(row[i])) for row in [headers] + rows) + 2
                      for i in range(len(headers))]

    # Header
    header_line = '│'.join(f' {h:<{w-2}} ' for h, w in zip(headers, col_widths))
    separator = '┼'.join('─' * w for w in col_widths)
    print(f'┌{"┬".join("─" * w for w in col_widths)}┐')
    print(f'│{header_line}│')
    print(f'├{separator}┤')

    # Rows
    for row in rows:
        row_line = '│'.join(f' {str(v):<{w-2}} ' for v, w in zip(row, col_widths))
        print(f'│{row_line}│')

    print(f'└{"┴".join("─" * w for w in col_widths)}┘')


def generate_detailed_report(output_dir, analyses, summary, config, signal_counts, multi_project):
    """Generate detailed markdown report with all tables."""
    report = []

    report.append('# Friction Analysis - Detailed Report\n\n')
    report.append(f'**Generated:** {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}\n\n')
    report.append(f'**Sessions Analyzed:** {len(analyses)}\n')
    report.append(f'**Interactive Sessions:** {summary["overall"]["interactive_sessions"]} (multi-turn conversations)\n')
    report.append(f'**BAD Sessions:** {summary["overall"]["bad_sessions"]} ({summary["overall"]["bad_rate"]*100:.0f}% of interactive)\n\n')

    # Add glossary
    report.append('## Glossary\n\n')
    report.append('**Interactive Session:** A conversation with >1 turn (multi-turn dialogue). Single-turn sessions are filtered from BAD rate calculation.\n\n')
    report.append('**BAD Session:** User gave up via `/stash`, `/exit`, or silent abandonment (high friction with no resolution).\n\n')
    report.append('**Friction:** Cumulative weight of negative signals. Higher friction = more user frustration.\n\n')
    report.append('**Peak Friction:** Maximum friction reached during a session.\n\n')
    report.append('---\n\n')

    # Add executive summary
    report.append('## Executive Summary\n\n')
    bad_rate = summary["overall"]["bad_rate"]
    overall = summary["overall"]

    if bad_rate > 0.5:
        report.append(f'⚠️  **CRITICAL**: {bad_rate*100:.0f}% of interactive sessions end in failure. ')
    elif bad_rate > 0.3:
        report.append(f'🟡 **WARNING**: {bad_rate*100:.0f}% of interactive sessions end in failure. ')
    else:
        report.append(f'✅ **HEALTHY**: {bad_rate*100:.0f}% of interactive sessions end in failure. ')

    report.append(f'Average session: {overall["avg_turns"]:.1f} turns, {overall["avg_friction"]:.1f} friction, {overall["avg_duration_min"]:.0f} min.\n\n')

    # Top issues
    top_signals = signal_counts.most_common(3)
    report.append('**Top Issues:**\n')
    for sig, count in top_signals:
        weight = config['weights'].get(sig, 0)
        total = count * weight
        report.append(f'- **{sig}** ({count} occurrences, {total:.0f} total friction)\n')
    report.append('\n')

    report.append('---\n\n')

    # Weight system explanation
    report.append('## Friction Weight System\n\n')
    report.append('Each signal has a weight representing its severity. Friction accumulates as signals occur.\n\n')
    report.append('| Weight | Severity | Meaning |\n')
    report.append('|--------|----------|----------|\n')
    report.append('| +10 | CRITICAL | User gave up (intervention, abandonment) |\n')
    report.append('| +8 | SEVERE | LLM false claims or no progress (false_success, no_resolution) |\n')
    report.append('| +7 | HIGH | User frustration (interrupt_cascade) |\n')
    report.append('| +6 | MEDIUM | Stuck patterns (tool_loop, rapid_exit) |\n')
    report.append('| +4-5 | LOW-MEDIUM | User signals (request_interrupted, user_curse) |\n')
    report.append('| +1 | MINOR | Technical issues (exit_error, repeated_question) |\n')
    report.append('| +0.5 | NOISE | Context signals (compaction, long_silence, user_negation) |\n\n')

    report.append('---\n\n')

    # Signal breakdown
    report.append('## Signal Breakdown\n\n')
    report.append('| Signal | Count | Weight | Total Friction | What It Means |\n')
    report.append('|--------|-------|--------|----------------|---------------|\n')

    signal_meanings = {
        'exit_error': 'Command failed (exit code != 0)',
        'compaction': 'Context overflow, conversation summarized',
        'repeated_question': 'User asked same question twice',
        'request_interrupted': 'User hit Ctrl+C or ESC',
        'long_silence': 'User paused >10 min',
        'user_negation': '"no", "didn\'t work", "still broken"',
        'false_success': 'LLM claimed success after error',
        'user_intervention': 'User gave up (/stash, /exit)',
        'interrupt_cascade': '2+ interrupts within 60s',
        'session_abandoned': 'High friction, no resolution',
        'no_resolution': 'Errors without subsequent success',
        'exit_success': 'Command succeeded (exit code 0)',
        'tool_loop': 'Same tool called 3+ times',
        'rapid_exit': '<3 turns, ends with error/interrupt',
        'user_curse': 'User frustration (profanity)'
    }

    for sig_type, count in signal_counts.most_common():
        weight = config['weights'].get(sig_type, 0)
        total = count * weight
        meaning = signal_meanings.get(sig_type, 'Unknown signal')
        report.append(f'| {sig_type} | {count} | {weight:+.1f} | {total:.1f} | {meaning} |\n')
    report.append('\n')

    # Pattern analysis
    report.append('## Pattern Analysis\n\n')

    # Analyze common failure patterns
    false_success_count = signal_counts.get('false_success', 0)
    exit_error_count = signal_counts.get('exit_error', 0)
    interrupt_count = signal_counts.get('request_interrupted', 0)
    intervention_count = signal_counts.get('user_intervention', 0)

    report.append('### Common Failure Patterns\n\n')

    if false_success_count > 0:
        report.append(f'**False Success Loop** ({false_success_count} occurrences): LLM claims task is complete after command fails. ')
        report.append('This indicates the LLM is not checking exit codes properly.\n\n')

    if exit_error_count > 50:
        report.append(f'**High Error Rate** ({exit_error_count} errors): Many commands are failing. ')
        report.append('This suggests either environment issues or LLM choosing wrong approaches.\n\n')

    if interrupt_count > 20:
        report.append(f'**User Interruptions** ({interrupt_count} interrupts): Users frequently canceling operations. ')
        report.append('Commands may be too slow, stuck, or heading in wrong direction.\n\n')

    if intervention_count > 0:
        intervention_rate = intervention_count / summary["overall"]["interactive_sessions"]
        report.append(f'**Abandonment Rate** ({intervention_rate*100:.0f}%): {intervention_count}/{summary["overall"]["interactive_sessions"]} interactive sessions ended with user giving up. ')
        if intervention_rate > 0.3:
            report.append('This is CRITICAL - users are frequently giving up.\n\n')
        else:
            report.append('This is acceptable for complex tasks.\n\n')

    # Why different friction levels
    report.append('### Friction Level Breakdown\n\n')
    low_friction = [a for a in analyses if 0 < a['friction_summary']['peak'] < 15]
    medium_friction = [a for a in analyses if 15 <= a['friction_summary']['peak'] < 50]
    high_friction = [a for a in analyses if a['friction_summary']['peak'] >= 50]

    report.append(f'**Low Friction (0-15):** {len(low_friction)} sessions - Normal operation, minor errors quickly resolved\n\n')
    report.append(f'**Medium Friction (15-50):** {len(medium_friction)} sessions - Some struggles, multiple retries, but eventually successful\n\n')
    report.append(f'**High Friction (50+):** {len(high_friction)} sessions - Severe issues, user frustration, likely gave up\n\n')

    report.append('---\n\n')

    # High-friction sessions
    report.append('## Top Friction Sessions\n\n')
    high_friction = sorted(analyses, key=lambda x: x['friction_summary']['peak'], reverse=True)[:20]
    high_friction = [a for a in high_friction if a['friction_summary']['peak'] > 0]

    if multi_project:
        report.append('| Project | Session | Quality | Peak | Turns | Duration | Top Signals |\n')
        report.append('|---------|---------|---------|------|-------|----------|-------------|\n')
    else:
        report.append('| Session | Quality | Peak | Turns | Duration | Top Signals |\n')
        report.append('|---------|---------|------|-------|----------|-------------|\n')

    for a in high_friction:
        full_sid = a['session_id']
        project = full_sid.split('/')[0] if '/' in full_sid else '?'
        sid = full_sid.split('/')[-1] if '/' in full_sid else full_sid
        peak = a['friction_summary']['peak']
        turns = a['session_metadata'].get('turn_count', 0)
        dur = a['session_metadata'].get('duration_min', 0)
        dur_str = format_duration(dur) if dur else '-'
        quality = a.get('quality', '?')

        # Top signals
        top_sigs = []
        for source, data in a['by_source'].items():
            for sig_type, sig_data in data['signals'].items():
                if sig_data['count'] > 0:
                    short_name = sig_type.replace('user_', '').replace('exit_', '')
                    top_sigs.append(f"{short_name}:{sig_data['count']}")
        sigs_str = ', '.join(top_sigs[:3]) if top_sigs else '-'

        if multi_project:
            report.append(f'| {project} | {sid} | {quality} | {peak} | {turns} | {dur_str} | {sigs_str} |\n')
        else:
            report.append(f'| {sid} | {quality} | {peak} | {turns} | {dur_str} | {sigs_str} |\n')
    report.append('\n')

    # Session quality breakdown
    report.append('## Session Quality Breakdown\n\n')
    quality_counts = Counter(a.get('quality', 'UNKNOWN') for a in analyses)
    quality_order = ['BAD', 'FRICTION', 'ROUGH', 'OK', 'ONE-SHOT']
    quality_desc = {
        'BAD': 'user gave up (/stash)',
        'FRICTION': 'curse or false_success',
        'ROUGH': 'high friction but completed',
        'OK': 'no significant friction',
        'ONE-SHOT': 'single turn (filtered)'
    }

    report.append('| Quality | Count | Description |\n')
    report.append('|---------|-------|-------------|\n')
    for q in quality_order:
        count = quality_counts.get(q, 0)
        desc = quality_desc.get(q, '')
        if count > 0:
            report.append(f'| {q} | {count} | {desc} |\n')
    report.append('\n')

    # Per-project stats
    if 'by_project' in summary and summary['by_project']:
        report.append('## Per-Project Statistics\n\n')
        report.append('| Project | Interactive | BAD | BAD % | Avg Friction | Avg Turns | Avg Duration |\n')
        report.append('|---------|-------------|-----|-------|--------------|-----------|-------------|\n')
        for proj, stats in sorted(summary['by_project'].items()):
            bad_rate_pct = f"{stats['bad_rate']*100:.0f}%" if stats['interactive_sessions'] > 0 else '-'
            dur = stats.get('avg_duration_min', 0)
            dur_str = format_duration(int(dur)) if dur else '-'
            report.append(f'| {proj} | {stats["interactive_sessions"]} | {stats["bad_sessions"]} | {bad_rate_pct} | {stats["avg_friction"]:.1f} | {stats["avg_turns"]:.1f} | {dur_str} |\n')
        report.append('\n')

    # Recommendations
    report.append('## Recommendations\n\n')

    recommendations = []

    if false_success_count > 10:
        recommendations.append('**High Priority:** Add CLAUDE.md rule to verify exit codes before claiming success')

    if interrupt_count > 20:
        recommendations.append('**High Priority:** Commands timing out or stuck - review for heavy operations that need optimization')

    if signal_counts.get('tool_loop', 0) > 3:
        recommendations.append('**Medium Priority:** Add CLAUDE.md rule to detect and break out of tool loops')

    if intervention_count / summary["overall"]["interactive_sessions"] > 0.4:
        recommendations.append('**Critical:** >40% abandonment rate - major UX issues, review antigens for patterns')

    if signal_counts.get('repeated_question', 0) > 20:
        recommendations.append('**Medium Priority:** Many repeated questions - LLM not understanding user intent or context issues')

    if recommendations:
        for i, rec in enumerate(recommendations, 1):
            report.append(f'{i}. {rec}\n\n')
    else:
        report.append('No critical issues detected. Continue monitoring.\n\n')

    report.append('---\n\n')

    # Daily trend
    if 'daily_stats' in summary and summary['daily_stats']:
        report.append('## Daily Trend (Last 14 Days)\n\n')
        report.append('| Date | Interactive | BAD | Rate | Trend |\n')
        report.append('|------|-------------|-----|------|-------|\n')
        for day in summary['daily_stats'][-14:]:
            bad_rate = day['bad_rate'] if day['interactive'] > 0 else 0
            bad_rate_pct = f"{bad_rate*100:.0f}%" if day['interactive'] > 0 else '-'
            bar_len = int(bad_rate * 10)
            bar = '█' * bar_len + '░' * (10 - bar_len)
            report.append(f'| {day["date"]} | {day["interactive"]} | {day["bad"]} | {bad_rate_pct} | {bar} |\n')
        report.append('\n')

    # Write report
    with open(output_dir / 'report.md', 'w') as f:
        f.write(''.join(report))

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    input_path = Path(sys.argv[1])
    config = load_config()

    # Find sessions - check for multi-project directory first
    if input_path.is_file():
        session_files = [input_path]
    else:
        # Try direct session files first
        session_files = [f for f in input_path.glob('*.jsonl')
                        if 'sessions-index' not in f.name]

        # If no direct session files, check if this is a parent directory with project subdirs
        if not session_files:
            project_dirs = [d for d in input_path.iterdir()
                          if d.is_dir() and not d.name.startswith('.')]

            # Check if subdirectories have session files
            for proj_dir in project_dirs:
                proj_sessions = list(proj_dir.glob('*.jsonl'))
                if proj_sessions:
                    # Found sessions in subdirectory - collect all from all projects
                    session_files = []
                    for pd in project_dirs:
                        session_files.extend([f for f in pd.glob('*.jsonl')
                                            if 'sessions-index' not in f.name])
                    break

    if not session_files:
        print(f'No sessions found in {input_path}')
        return 1

    # Create output dir
    output_dir = Path('.aurora/friction')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Process each session, collect into consolidated structures
    analyses = []
    all_signals = []
    errors = []

    # Detect if analyzing multiple projects
    project_parents = set(sf.parent.name for sf in session_files)
    multi_project = len(project_parents) > 1

    if multi_project:
        print(f'Found sessions from {len(project_parents)} projects\n')

    for session_file in session_files:
        try:
            signals, metadata = extract_signals(session_file)
            session_name = derive_session_name(session_file, metadata)

            # Tag signals with session name
            for sig in signals:
                sig['session'] = session_name
                all_signals.append(sig)

            analysis = analyze_session(session_name, signals, metadata, config)
            analyses.append(analysis)

        except Exception as e:
            errors.append((session_file.stem[:12], str(e)[:40]))

    # Write consolidated raw signals
    with open(output_dir / 'friction_raw.jsonl', 'w') as f:
        for sig in all_signals:
            f.write(json.dumps(sig) + '\n')

    # Write consolidated analysis
    with open(output_dir / 'friction_analysis.json', 'w') as f:
        json.dump(analyses, f, indent=2)

    if not analyses:
        print('\nNo sessions could be analyzed')
        return 1

    # Aggregate
    summary = aggregate_sessions(analyses, config)

    with open(output_dir / 'friction_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)

    # === CONCISE TERMINAL OUTPUT ===

    print()
    print('=' * 60)
    print('FRICTION ANALYSIS')
    print('=' * 60)
    print()

    agg = summary['aggregate_by_source']
    corr = summary['correlations']
    overall = summary['overall']

    # Summary line
    interactive = overall['interactive_sessions']
    bad_count = overall['bad_sessions']
    bad_rate = overall['bad_rate']

    projects_count = len(summary.get('by_project', {}))
    print(f"Analyzed: {len(analyses)} sessions ({interactive} interactive*) from {projects_count} project{'s' if projects_count != 1 else ''}")
    print(f"  *interactive = multi-turn conversations (>1 turn)")

    # BAD rate with emoji
    emoji = '🔴' if bad_rate > 0.5 else '🟡' if bad_rate > 0.3 else '✅'
    print(f"BAD Rate: {bad_rate*100:.0f}% ({bad_count}/{interactive} interactive) {emoji}")
    print()

    # Top signals (condensed - top 5)
    signal_counts = Counter()
    for source_data in agg.values():
        for sig_type, count in source_data['top_signals'].items():
            signal_counts[sig_type] += count

    if signal_counts:
        print('Top Signals:')
        for sig_type, count in signal_counts.most_common(5):
            weight = config['weights'].get(sig_type, 0)
            total_friction = count * weight
            print(f'  {sig_type:20s} {count:3d}   ({total_friction:+.0f} friction)')
        print()

    # Per-project stats with median
    if 'by_project' in summary and summary['by_project']:
        print('Per-Project:')
        for proj, stats in sorted(summary['by_project'].items()):
            bad_rate = stats['bad_rate']
            emoji = '🔴' if bad_rate > 0.5 else '🟡' if bad_rate > 0.3 else '✅'
            bad_pct = f"{bad_rate*100:.0f}%" if stats['interactive_sessions'] > 0 else '-'

            # Calculate median friction for this project
            proj_sessions = [a for a in analyses if a['session_id'].startswith(f"{proj}/")]
            interactive_sessions = [a for a in proj_sessions if a['session_metadata'].get('turn_count', 0) > 1]
            if interactive_sessions:
                frictions = sorted([a['friction_summary']['peak'] for a in interactive_sessions])
                median = frictions[len(frictions)//2]
                print(f'  {proj:12s} {bad_pct:>4s} BAD ({stats["bad_sessions"]}/{stats["interactive_sessions"]})  median: {median:.1f}  {emoji}')
            else:
                print(f'  {proj:12s} {bad_pct:>4s} BAD ({stats["bad_sessions"]}/{stats["interactive_sessions"]})  {emoji}')
        print()

    # Best and worst sessions
    if summary.get('best_session') and summary.get('worst_session'):
        ws = summary['worst_session']
        bs = summary['best_session']
        print('Session Extremes:')

        ws_id = ws['session_id'] if multi_project else ws['session_id'].split('/')[-1]
        print(f'  WORST: {ws_id}  peak={ws["peak_friction"]:.0f}  turns={ws["turns"]}')

        bs_id = bs['session_id'] if multi_project else bs['session_id'].split('/')[-1]
        print(f'  BEST:  {bs_id}  peak={bs["peak_friction"]:.0f}  turns={bs["turns"]}')
        print()

    # Last 2 weeks trend
    if 'daily_stats' in summary and summary['daily_stats']:
        print('Last 2 Weeks:')
        for day in summary['daily_stats'][-14:]:
            if day['interactive'] == 0:
                continue
            bad_rate = day['bad_rate']
            bar_len = int(bad_rate * 10)
            bar = '█' * bar_len + '░' * (10 - bar_len)
            print(f'  {day["date"]}  {day["interactive"]:2d} sessions  {day["bad"]:2d} BAD  {bar}  {bad_rate*100:.0f}%')
        print()

    # Verdict
    verdict = summary['verdict']
    status_emoji = {'USEFUL': '✓', 'INCONCLUSIVE': '?', 'BLOAT': '✗'}
    status = verdict['status']
    print(f"Verdict: {status_emoji.get(status, '?')} {status}")

    predictability = corr.get('intervention_predictability', 0)
    snr = summary.get('signal_noise_ratio', 0)
    print(f'  Intervention predictability: {predictability:.0%}')
    if 'signal_noise_ratio' in summary:
        print(f'  Signal/noise ratio: {snr:.1f}')
    print()

    # Generate detailed report
    generate_detailed_report(output_dir, analyses, summary, config, signal_counts, multi_project)

    # Output files
    print('Outputs:')
    print(f'  📊 .aurora/friction/report.md (detailed analysis)')
    print(f'  📋 .aurora/friction/antigen_review.md (failure patterns)')
    print(f'  📁 .aurora/friction/*.json (raw data: {len(all_signals)} signals, {len(analyses)} sessions)')
    print()

    print('Next: Review .aurora/friction/report.md')
    print('=' * 60)

    if errors:
        print(f'\n⚠  {len(errors)} sessions failed to parse')

    return 0 if status == 'USEFUL' else 1

if __name__ == '__main__':
    sys.exit(main())
