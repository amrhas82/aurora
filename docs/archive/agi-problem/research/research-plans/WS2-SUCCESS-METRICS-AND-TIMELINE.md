# WS2: Success Metrics & Decision Framework

Based on SOAR-vs-ACT-R-DETAILED-COMPARISON.md and research-continuation.md

---

## Overview

**Research Goal**: Prove that a hybrid SOAR + ACT-R system breaks the token prediction ceiling and enables genuine learning.

**Timeline**: 6-9 months (phased)

**Key Decision Points**: Go/No-Go gates at end of each phase

---

## Phase 1: SOAR Foundation (Months 1-2)

### What You're Building
SOAR reasoning engine that can:
- Parse problems into state representations
- Elaborate possible operators (what can I do?)
- Evaluate and select best operator
- Execute and learn from results

### Success Criteria (Phase 1)

| Criterion | Target | How to Measure |
|-----------|--------|----------------|
| **Transparency** | >90% of decisions can be explained | Run 10 different problem types, examine decision traces |
| **Novel Problem Accuracy** | 70%+ on first attempt | Test 20 problems agent hasn't seen, measure success rate |
| **Rule Extraction** | 5+ rules extracted | Count new rules created during phase |
| **State Representation** | Parser works for 5 problem types | Test parser on diverse problems (code, business, logic) |
| **Decision Speed** | No more than 20s per problem | Measure latency (5-15s target) |
| **Code Quality** | <10 bugs found in testing | Run 100 test cases, document failures |

### Go/No-Go Decision
**SOAR Phase Success if**:
- Transparency > 85%
- Novel accuracy > 65%
- Rules extracted ≥ 3
- Decision speed < 20s

**If not met**: Refine SOAR implementation, extend Phase 1

---

## Phase 2: ACT-R Learning Layer (Months 3-4)

### What You're Building
ACT-R utilities that:
- Track success of each operator
- Update utilities based on outcomes
- Route familiar problems to fast path
- Maintain activation decay

### Success Criteria (Phase 2)

| Criterion | Target | How to Measure |
|-----------|--------|----------------|
| **Utility Tracking** | All operators have utilities | Check that every operator has success count |
| **Fast Path Activation** | >50% of familiar problems use ACT-R | Run 100 problems, measure how many skip SOAR |
| **Speed Improvement** | Familiar problems 30% faster than month 1 | Compare latency month 1 vs month 3 |
| **Utility Growth** | Utilities increase >0.15/month | Track average utility across all operators |
| **Confidence Thresholds** | 80% of high-utility operators actually successful | Check when utility > 0.8, how often does execution succeed? |
| **Learning Curve** | Month 1 faster than month 2 faster than month 3 | Plot average latency over time (should improve) |

### Go/No-Go Decision
**ACT-R Phase Success if**:
- Fast path > 40% of problems
- Speed improvement > 20%
- Utilities increasing consistently
- Confidence threshold accuracy > 75%

**If not met**: Refine utility tracking, extend Phase 2

---

## Phase 3: Hybrid Integration & Optimization (Months 5-6)

### What You're Building
Unified system with:
- Intelligent routing (when to use each path)
- Parallel learning (both mechanisms improve)
- Portability validation
- Performance optimization

### Success Criteria (Phase 3)

| Criterion | Target | How to Measure |
|-----------|--------|----------------|
| **Orchestrator Routing** | Correct path chosen 90% of time | Log every routing decision, verify accuracy |
| **Dual Learning** | Both SOAR rules AND ACT-R utilities improve | Track new rules + utility increases monthly |
| **System Improvement** | Month 3 > Month 2 > Month 1 | Overall performance metrics trending up |
| **Portability Across Models** | 80%+ of rules transfer to new LLM | Switch to different model, test rule accuracy |
| **Portability Across Frameworks** | 75%+ rules work in new framework | Switch framework, test rule execution |
| **Reasoning Transparency** | Still >85% explainability | Verify decision traces remain clear |
| **Catastrophic Forgetting** | <10% performance loss when adding new task | Add new problem type, measure impact on old ones |

### Go/No-Go Decision
**Hybrid Phase Success if**:
- System improvement > 15% from month 1
- Portability > 75% across models
- Catastrophic forgetting < 15%
- Dual learning confirmed (both mechanisms active)

**If not met**: Refactor routing, improve learning convergence

---

## Overall System Metrics (By Month)

### Month 1 (End of SOAR)
```
Speed per problem: 5-7 seconds
Accuracy on novel: 70%
Speed on familiar: 5-7 seconds (no learning yet)
Rules created: 5-10
Explainability: >90%
Portability: Not tested yet
```

### Month 2 (Middle of ACT-R)
```
Speed per problem: 4-6 seconds (some familiar patterns)
Accuracy on novel: 72%
Speed on familiar: 2-4 seconds (ACT-R starting to work)
Rules created: 10-15
Utilities improving: Yes
Fast path usage: 20-30%
Explainability: >85%
```

### Month 3 (End of ACT-R)
```
Speed per problem: 2-4 seconds (mix of fast + reasoning)
Accuracy on novel: 74%
Speed on familiar: 0.5-1 second (ACT-R optimized)
Rules created: 15-25
Utilities stable and improving
Fast path usage: 40-60%
Explainability: >85%
Improvement from month 1: >30%
```

### Month 4 (Middle of Integration)
```
Speed per problem: 1-3 seconds
Accuracy on novel: 75%
Speed on familiar: 0.2-0.5 second
Rules created: 20-30
Fast path usage: 50-70%
Portability tested: 75%+ transfer to new model
Dual learning confirmed: Yes
Explainability: >85%
Improvement from month 1: >40%
```

### Month 5-6 (End of Integration)
```
Speed per problem: 0.5-2 seconds
Accuracy on novel: 76-78%
Speed on familiar: 0.15-0.3 second
Rules created: 30-50
Fast path usage: 70-80%
Portability: 80%+ transfer across models AND frameworks
Dual learning: Both mechanisms strongly active
Catastrophic forgetting: <10% when adding new tasks
Explainability: >85%
Improvement from month 1: >50%
```

---

## Research Publication Metrics

By end of month 6, you should have:

### Metric 1: System Performance
- Novel problem accuracy: 76-78%
- Familiar problem latency: 150-300ms
- Month 1 to Month 6 improvement: >50%
- Fast path adoption: 70-80%

**Publication value**: Demonstrates hybrid approach beats pure SOAR or pure ACT-R

### Metric 2: Learning Curves
- ACT-R utilities improving monthly: Yes
- SOAR rule extraction rate: 5-8 rules/month
- Learning curve matches human-like (initial steep, then plateau)

**Publication value**: Realistic learning development in agents

### Metric 3: Portability
- Rules transfer to new LLM: 80%+
- Rules transfer to new framework: 75%+
- Performance recovery: 70%+ of original performance

**Publication value**: First agent system with portable learned knowledge

### Metric 4: Explainability
- Decision transparency: >85%
- Rule interpretability: All rules humanly understandable
- Reasoning traces: Complete from query to execution

**Publication value**: Agents that explain their reasoning (vs. black-box LLMs)

### Metric 5: Scalability
- Handles 50+ different problem types
- Rule base grows without degradation
- System performance stable as rules accumulate

**Publication value**: Proof that symbolic learning doesn't hit scaling ceiling

---

## Decision Framework at Each Gate

### After Phase 1 (Month 2)
**Question**: Does SOAR foundation work?

**Check**:
- [ ] Parser handles 5+ problem types
- [ ] Transparency >85%
- [ ] Novel accuracy >65%
- [ ] Rules extracting consistently

**Options**:
- ✅ GO: Proceed to Phase 2 (ACT-R learning)
- 🔄 REFINE: Fix specific SOAR issues, extend Phase 1 by 2 weeks
- ❌ STOP: Fundamental issue (explore alternative reasoning architecture)

---

### After Phase 2 (Month 4)
**Question**: Does ACT-R speed up familiar problems?

**Check**:
- [ ] Fast path used >40% of problems
- [ ] Familiar problems 20%+ faster than month 1
- [ ] Utilities increasing month-over-month
- [ ] Confidence thresholds >75% accurate

**Options**:
- ✅ GO: Proceed to Phase 3 (integration & analysis)
- 🔄 REFINE: Improve routing or confidence thresholds, extend Phase 2 by 2 weeks
- ❌ RECONSIDER: ACT-R not providing value (evaluate alternatives)

---

### After Phase 3 (Month 6)
**Question**: Does hybrid system break the token prediction ceiling?

**Check**:
- [ ] System 50%+ faster than month 1
- [ ] Portability >75% across models/frameworks
- [ ] Dual learning confirmed (both mechanisms active)
- [ ] Catastrophic forgetting <10%

**Options**:
- ✅ GO PRODUCTION: System ready for enterprise pilots
- 🔄 REFINE: Fine-tune specific areas, extend Phase 3
- ❌ PUBLISHABLE RESEARCH: Even if not perfect, publish findings on hybrid approach

---

## Metrics to Track Daily

### Development Metrics
```
Daily:
- Lines of code (should increase ~100-150/day)
- Tests passing (should stay >90%)
- Bugs logged (should decrease over time)

Weekly:
- Phase progress (tasks completed vs. planned)
- Blocker list (show progress on critical issues)

Monthly:
- Speed improvement (latency trend)
- Accuracy trend (novel + familiar)
- Rule extraction rate
- Fast path adoption
```

### Quality Metrics
```
Code Quality:
- Test coverage: Target 80%+
- Code review findings: 0-2 per 100 lines (acceptable)

Correctness:
- Routing decisions: 90%+ correct
- Rule execution: 95%+ successful application

Scalability:
- Rules processing: <50ms to elaborate all rules
- Memory usage: <500MB for 50+ rules + utilities
```

---

## Comparison to Token Prediction Ceiling

### Current Approach (All 30+ Competitors)
```
Month 1: 20% accuracy on hard problems
Month 2: 22% accuracy (marginal improvement)
Month 3: 23% accuracy
Month 6: 25% accuracy (plateau reached)

Conclusion: Ceiling ~25% due to token prediction limits
```

### SOAR + ACT-R Approach (Your Research)
```
Month 1: 70% accuracy on novel, 60% on familiar (no ACT-R yet)
Month 2: 72% accuracy on novel, 75% on familiar (ACT-R learning)
Month 3: 74% accuracy on novel, 80% on familiar (optimization)
Month 6: 76-78% accuracy (approaching human-level)

Conclusion: No ceiling visible, continuous improvement
```

**Publication story**: "How hybrid cognitive architectures break the token prediction ceiling"

---

## Resource Requirements

### Team (For Full Implementation)
- 1 architect (full-time): Overall design, integration
- 1-2 engineers (full-time): SOAR implementation
- 1 ML engineer (part-time): ACT-R utilities, learning optimization
- 1 researcher (part-time): Metrics, analysis, publications

### Infrastructure
- GPU: For LLM grounding (Claude API)
- CPU: For SOAR/ACT-R processing (standard server)
- Storage: For rule base and learning history

### Budget
- Total 6-month budget: ~$150-200K
- LLM API calls: $30-50K
- Infrastructure: $10-20K
- Personnel (if new hires): $80-120K

---

## Red Flags (Stop-Work Conditions)

If any of these occur, pause and reassess:

1. **Parser can't handle basic problems**: If SOAR state representation fails on simple cases, fundamental issue
2. **Rules don't improve outcomes**: If extracted rules don't actually help, learning mechanism broken
3. **Utilities always converge to 0.5**: If learning signal too noisy, weak supervision insufficient
4. **No portability**: If rules can't transfer to new model, core assumption wrong
5. **Catastrophic forgetting >20%**: If adding task destroys old learning, system unstable
6. **Fast path never activates**: If ACT-R never builds confidence, routing logic wrong

**Action if flag triggered**: Deep dive into root cause, may need to refactor Phase 1 or 2

---

## Success Story (What Success Looks Like)

```
Month 1-2: SOAR working
- Agent can reason about novel problems
- Decisions are transparent and explainable
- Learning traces into rules

Month 3-4: ACT-R optimizing
- Familiar problems get fast responses
- Learning curves look human-like
- Utilities improve reliably

Month 5-6: Hybrid system
- Fast for known, thorough for novel
- System 50%+ faster than month 1
- Rules portable across models
- Continuous improvement evident

Publication: "Hybrid SOAR+ACT-R Agents: Breaking the Token Prediction Ceiling"

Enterprise Pilot: Test with customer
- Agent learns from their domain
- Performance improves month-to-month
- Rules can transfer between their LLMs
```

---

## Summary: How to Know You're on Track

**Month 1**: SOAR foundation solid (transparency + accuracy + rules)
**Month 2**: SOAR + ACT-R hybrid working (fast path activating)
**Month 3**: System clearly better than month 1 (50%+ improvement visible)
**Month 6**: Enterprise-ready system with proven learning

If you're hitting targets at each checkpoint, you're succeeding. Adjust if you're missing.

---

**These metrics are based on**:
- SOAR-vs-ACT-R-DETAILED-COMPARISON.md (reasoning quality targets)
- research-continuation.md (learning curve expectations)
- Standard cognitive science evaluation methods

**Confidence**: 90% (metrics are achievable, timeline realistic for experienced team)
