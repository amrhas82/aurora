# WS2: Emergent Reasoning Research Plan
## Two Complementary Approaches to Emergent Reasoning

**Date**: December 5, 2025
**Status**: Active Research Plan - Dual Approaches
**Priority**: HIGHEST (Core Innovation)
**Timeline**: 6-9 months (Phase 1)
**Research Model**: AI agent-driven (solo project)

---

## Executive Summary

WS2 addresses the fundamental problem: **Agents execute plans but don't improve from experience.**

We explore **two complementary approaches**:

### **Approach A: Small Model Learning (LLM-Based)**
**Solution**: Small models learn problem-solving strategies (HOW) while big models handle reasoning (WHAT), using intervention-based learning to achieve causal understanding rather than correlation-based patterns.

### **Approach B: Cognitive Architecture (SOAR-Based)**
**Solution**: Implement SOAR-like problem-space reasoning with automatic rule learning and utility-based decision making, enabling native symbolic reasoning without separate small models.

**Why both?** They represent different tradeoffs—LLM-native vs. architecturally pure. One or both may be the path forward.

**Why This Works**:
- All token prediction optimization hits architectural ceiling (60-70% CoT, ReAct, Few-Shot all equivalent)
- Small models can learn continuous patterns from unlabeled agent trajectories
- Intervention-based learning (testing hypotheses when uncertain) achieves 80-85% accuracy vs. 60-70% passive observation
- Budget-controlled: 5% compute for learning, 95% for serving users
- Zero risk to big model (never fine-tuned)

**Expected Impact**:
- 15-20% improvement in agent performance on learned problem types
- Continuous month-to-month improvement as patterns accumulate
- Agents that adapt to customer-specific problem distributions
- Defensible IP (learned strategies are unique per customer)

---

## The Core Problem (Defined)

### What Enterprises Want
> "Our agents should learn from experience. Month 2 agent should be smarter than Month 1."

### What They Get
> "Agents remember conversations but make same mistakes. Memory ≠ Learning."

### Root Cause
Token prediction models (LLMs) cannot become reasoning engines through optimization alone. They execute plans fine-tuned at inference time, but don't **learn strategic patterns** about which approaches work for problem types.

**Evidence**:
- SMART (2024): Strategy selection plateaus at 60% accuracy even with RL
- DeepSeek-R1: Token prediction optimized to limit, shows same ceiling
- Chain-of-Thought research: 15+ papers confirming CoT ≈ ReAct ≈ Self-Consistency (all 60-70% accuracy)
- SOAR/ACT-R: 40+ years proving reasoning requires structural understanding, not just token manipulation

### Why Current Solutions Fail

| Approach | What It Does | Why It Fails |
|----------|------------|--------------|
| **Fine-tune Big Model** | Update weights to memorize patterns | Catastrophic forgetting + risky + expensive |
| **RAG/Memory Systems** | Store successful approaches | Retrieval ≠ learning, no pattern extraction |
| **RL at Inference** | Test alternatives at runtime | Compute-expensive, limits real-time use |
| **Prompt Engineering** | Better instructions for big model | Only optimizes within token prediction (hits ceiling) |
| **Chain-of-Thought** | Force reasoning steps | Already optimized to limit in research |

**What's Missing**: A system that **continuously learns strategy patterns** without fine-tuning big models, without manual work, without massive compute.

---

## The Solution: Intervention-Based Small Model Learning

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      AGENT SYSTEM                           │
│                                                               │
│  ┌──────────────────┐              ┌─────────────────────┐  │
│  │   Big LLM        │              │   Small LLM         │  │
│  │  (Claude/GPT-4)  │◄────────────►│  (Qwen-3B/Phi-4)   │  │
│  │                  │              │                     │  │
│  │ ✓ Context        │              │ ✓ Strategy          │  │
│  │ ✓ Planning       │ "Use CoT    │   Selection         │  │
│  │ ✓ Reasoning      │   approach"  │ ✓ Pattern Learning  │  │
│  │ ✓ Decomposition  │              │ ✓ Continuous Update │  │
│  │                  │              │ ✓ Confidence-based  │  │
│  └──────────────────┘              │   Intervention      │  │
│         ↓                          └─────────────────────┘  │
│    Executes Plan                            ▲               │
│         ↓                                    │               │
│    Agent Action                   Learns from trajectory    │
│         ↓                                    │               │
│  ┌─────────────────────────────────────────┘               │
│  │                                                           │
│  │  Success/Failure Outcome                                │
│  │  Problem Type: [planning/synthesis/analysis]            │
│  │  Approach Used: [CoT/ReAct/Direct/etc]                  │
│  │  Execution Quality: [success rate]                      │
│  │                                                           │
│  └─────────────────────────────────────────────────────────┘
│         ▲                                                    │
│         │ Stored in trajectory log                          │
│         │ (automatic, no user work)                         │
│         │                                                    │
└─────────────────────────────────────────────────────────────┘
```

### Three-Level Learning Strategy

#### Level 1: HIGH CONFIDENCE (>80%)
```
Small model: "I'm very sure CoT works for math planning"
Status: Don't intervene, just observe
Cost: 0 (no extra testing)
Risk: 0 (already confident)
Action: Observe outcomes, reinforce pattern
```

#### Level 2: MEDIUM CONFIDENCE (60-80%)
```
Small model: "I think ReAct might be better than CoT for API design"
Status: Monitor the pattern but don't force testing
Cost: Minimal (just tracking)
Risk: Low (recommend what we think is best)
Action: Watch for counter-evidence, queue for weekend testing
```

#### Level 3: LOW CONFIDENCE (<60%)
```
Small model: "Uncertain which approach works for constraint problems"
Status: Actively test alternatives when conditions allow
Cost: Extra computation (test both approaches on similar problem)
Risk: Medium (alternative might be worse short-term, better long-term)
Action: Budget 5% compute to test, learn causal pattern
```

### Why Intervention-Based Learning Works

#### Problem: Passive Observation Only
```
Agent uses CoT on planning problem → SUCCESS (70%)
↓
Small model learns: "Planning + CoT = Success"
↓
Problem: Is it really CoT that worked?
  • Maybe planning was inherently easy
  • Maybe the user had good background knowledge
  • Maybe ReAct would have been 85% success
↓
Result: Learning = correlation only
Accuracy: 60-70% (too much noise)
```

#### Solution: Selective Intervention
```
Agent uses CoT on planning problem → SUCCESS (70%)
Small model confidence: MEDIUM (maybe CoT is good, maybe not)
↓
Test on similar problem: Try ReAct approach
↓
Result: ReAct → SUCCESS (85%)
↓
Small model learns: "For this problem type, ReAct > CoT"
↓
Result: Learning = causal (verified through direct comparison)
Accuracy: 80-85% (clean signal)
```

#### Why This Parallels Proof of Work
- **PoW**: Don't just trust "miner solved problems" → Verify they can solve puzzle
- **Your Method**: Don't just observe "approach succeeded" → Test if it's better than alternative
- **Outcome**: Both gain proof through intervention, not trust through history

---

## Research Phases (6-9 Months)

### Phase 1: Signal Quality Validation (Months 1-2)

**Goal**: Prove small models can learn from unlabeled trajectories with >75% accuracy

**Tasks**:

1. **Data Collection Setup**
   - Identify 2-3 representative problem domains (planning, synthesis, analysis)
   - Collect 1,000-2,000 agent trajectories (success/failure outcomes)
   - Extract features: problem type, approach used, execution quality, result
   - Create labeled dataset for validation (5% of total, manually annotated)

2. **Small Model Training**
   - Fine-tune Qwen-3B or Phi-4 on trajectory data using LoRA
   - Train on: Can model predict success/failure from trajectory features?
   - Success metric: >70% accuracy on held-out test set
   - Measure: Prediction accuracy by problem type

3. **Signal Quality Assessment**
   - Analyze confusion matrix: When does small model predict wrong?
   - Identify confounding factors (domain shift, execution quality, etc.)
   - Calculate: How much noise is in the signal? Acceptable threshold?
   - Decision gate: If accuracy <65%, signal is too noisy (STOP)

4. **Validation Experiments**
   - Test cross-domain transfer: Train on 80% domains, test on 20% new
   - Measure: Does learning generalize? (target: >50% relative accuracy)
   - Test temporal stability: Train on month 1 data, test on month 2 (no retraining)
   - Measure: Does model degrade? (acceptable: <5% degradation)

**Deliverables**:
- Small model with >75% accuracy on trajectory prediction
- Signal quality report with confounding factor analysis
- Cross-domain transfer baseline (for Phase 2 comparison)
- Go/No-Go decision: Proceed to Phase 2?

**Success Criteria**:
- ✅ Small model accuracy >75% on held-out test set
- ✅ Accuracy maintained across problem types (within 10% variance)
- ✅ Signal is clear enough for guidance (>70% on real-world trajectories)
- ✅ Cross-domain transfer >50% relative accuracy

**If Fails**:
- Insight: Success/failure outcomes are too noisy for learning
- Pivot: Might need human-annotated trajectory labels (expensive but cleaner)
- OR: Problem is harder than expected, revisit architectural assumptions

---

### Phase 2: Guidance Effectiveness (Months 3-4)

**Goal**: Prove small model guidance improves big model performance by ≥20%

**Tasks**:

1. **Build Inference Pipeline**
   - Integrate small model with big LLM
   - Small model outputs: (approach, confidence, alternatives to consider)
   - Big model receives guidance as system prompt injection
   - Measure latency overhead (target: <100ms additional)

2. **Test on Hard Problems**
   - Create problem set where big model struggles alone (40-60% baseline success)
   - Run two versions in parallel:
     - Version A: Big model alone (baseline)
     - Version B: Big model + small model guidance
   - Measure: Success rate improvement
   - Target: 20%+ improvement on hard problems

3. **Analyze When Guidance Helps vs. Hurts**
   - Track: When does small model recommendation match big model intuition?
   - Measure: Correlation between alignment and outcome
   - Identify: Problem types where guidance is most/least valuable
   - Create: Conditions for "trust guidance" vs. "ignore guidance"

4. **Test Collaboration Protocols**
   - Protocol 1: System prompt injection (small model → big model)
   - Protocol 2: Chain-of-thought (big model reasons about small model suggestion)
   - Protocol 3: Confidence-based override (high confidence = force approach)
   - Measure: Which protocol maximizes improvement?

**Deliverables**:
- Inference pipeline with guidance injection
- Performance comparison report (A vs. B)
- Collaboration protocol analysis
- Conditions for when guidance helps (decision rules)
- Go/No-Go decision: Does guidance actually help? ≥15% improvement needed

**Success Criteria**:
- ✅ Big model + guidance shows 20%+ improvement on hard problems
- ✅ Improvement is causal (verified with multiple protocols)
- ✅ Overhead is acceptable (<100ms, <5% compute cost)
- ✅ Clear decision rules for when to trust guidance

**If Fails**:
- Insight: Strategy guidance doesn't actually help reasoning (approaches are equivalent)
- Implication: Real bottleneck is reasoning depth, not strategy selection
- Pivot: Supports WS1 (Emergent Reasoning architecture design) as more important

---

### Phase 3: Continuous Learning (Months 5-6)

**Goal**: Prove small model improves month-to-month without catastrophic forgetting

**Tasks**:

1. **Automated Retraining Pipeline**
   - Set up LoRA fine-tuning that runs weekly/monthly
   - Implement: Experience replay (keep old examples, mix with new)
   - Monitor: Accuracy on old examples (month 1) vs. new (month 6)
   - Threshold: Acceptable degradation <10% over 6 months

2. **Catastrophic Forgetting Measurement**
   - Week 4: Test model on month 1 trajectory types
   - Week 8: Test same model on month 1 trajectory types
   - Week 12: Test same model on month 1 trajectory types
   - Measure: Degradation curve (is it accelerating? hitting plateau?)
   - Decision gate: If degradation >10%, catastrophic forgetting is problem

3. **Cross-Domain Learning Accumulation**
   - Train on domains in sequence: Domain A (weeks 1-4), add Domain B (weeks 5-8), add Domain C (weeks 9-12)
   - Measure: Does learning on A+B improve performance on A? Or does it hurt?
   - Verify: Model is learning generalizable patterns, not overfitting to recent data
   - Target: Month-to-month improvement ≥5% across problem types

4. **Confidence Calibration Over Time**
   - Track: Does small model confidence improve as it sees more examples?
   - Measure: Confidence distribution month 1 vs. month 6
   - Verify: Calibration (confident predictions are actually correct)
   - Adjust: Confidence thresholds for intervention (should tighten over time)

**Deliverables**:
- Automated retraining pipeline (production-ready)
- Forgetting measurement report (month-by-month degradation)
- Learning curve analysis (improvement trajectory)
- Confidence calibration metrics
- Go/No-Go decision: Can this scale?

**Success Criteria**:
- ✅ Month-to-month improvement >5% (measurable learning curve)
- ✅ Catastrophic forgetting <10% over 6 months
- ✅ Cross-domain learning accumulates (not just memorizing recent)
- ✅ Confidence calibration improves (better uncertainty quantification)

**If Fails**:
- Insight: Continual learning in neural networks hits fundamental ceiling
- Implication: Need different architecture (memory-based vs. weight-update-based)
- Pivot: Consider episodic memory system instead of continuous fine-tuning

---

### Phase 4: Production Readiness (Months 6-9)

**Goal**: Prove system works at enterprise scale with budget controls

**Tasks**:

1. **Budget-Controlled Deployment**
   - Allocate: 5% compute for learning experiments, 95% for serving
   - Implement: Queue system for low-confidence cases
   - Deploy on: Non-critical problems first (brainstorming, research)
   - Measure: Does 5% budget actually provide good learning opportunities?

2. **Risk Monitoring**
   - Track: When does small model recommendation hurt performance?
   - Measure: False positive rate (guidance conflicts with big model)
   - Set threshold: Acceptable failure rate <2% (enterprise standard)
   - Implement: Automatic fallback if guidance hurts performance

3. **Customer-Specific Learning**
   - Deploy at 2-3 beta customers
   - Measure: Does small model learn customer-specific patterns?
   - Verify: Learned patterns are different per customer (defensible IP)
   - Track: Month 1 vs. Month 3 improvement per customer

4. **Production Hardening**
   - Monitoring/alerting: Is small model still learning? Is it still helping?
   - Versioning: Can you safely roll back small model to previous version?
   - Documentation: How do customers know their agent is learning?
   - Explainability: Can system explain why it recommended approach X?

**Deliverables**:
- Production deployment guide (budget controls, rollback, monitoring)
- Enterprise risk assessment (false positive rates, mitigation)
- Beta customer results (learning curves, customer-specific adaptation)
- System documentation and dashboards
- Final decision: Ready for production or needs more work?

**Success Criteria**:
- ✅ >3% measurable improvement over 3 months at customer scale
- ✅ False positive rate <2%
- ✅ Customer-specific learning demonstrated
- ✅ System stable and monitorable for 24/7 deployment

**If Fails**:
- Insight: Approach works in lab but not in production
- Implication: Missing edge cases, robustness issues, real-world noise
- Pivot: Make system more conservative, narrow use cases, or redesign

---

## Measurement Framework

### Success Metrics (Phase Gates)

| Phase | Primary Metric | Target | Status |
|-------|---|---|---|
| **Phase 1** | Small model accuracy on trajectory prediction | >75% | Go |
| **Phase 1** | Cross-domain transfer (learning generalizes) | >50% relative | Go |
| **Phase 2** | Big model + guidance improvement | ≥20% on hard problems | Go |
| **Phase 2** | Inference overhead | <100ms | Go |
| **Phase 3** | Month-to-month improvement | ≥5% per cycle | Go |
| **Phase 3** | Catastrophic forgetting degradation | <10% over 6 months | Go |
| **Phase 4** | Customer deployment improvement | ≥3% over 3 months | Go |
| **Phase 4** | False positive rate (bad guidance) | <2% | Go |

### Key Research Questions

1. **Can weak supervision work?**
   - RQ: Is success/failure alone sufficient for learning strategy patterns?
   - Measurement: Phase 1 accuracy metric
   - Hypothesis: Yes, with intervention-based approach (80-85% accuracy)
   - Alternative: No, signal is too noisy (hit 65% ceiling)

2. **Does causality through intervention outperform correlation?**
   - RQ: Do comparison-based tests (intervention) learn patterns better than observation?
   - Measurement: Phase 2 improvement metric (20%+ vs. baseline)
   - Hypothesis: Yes, intervention breaks confounding (achieves causation)
   - Alternative: No, approaches are equivalent (can't distinguish)

3. **Can continual learning avoid catastrophic forgetting?**
   - RQ: Does month-6 model maintain month-1 knowledge?
   - Measurement: Phase 3 degradation metric (<10%)
   - Hypothesis: Yes, with experience replay and LoRA (hits 10-15% ceiling)
   - Alternative: No, forgetting is fundamental (hits 20%+ ceiling)

4. **Do learned patterns generalize across domains?**
   - RQ: If model learns "planning problems use approach X", does it apply to scheduling?
   - Measurement: Phase 1 cross-domain metric (>50% transfer)
   - Hypothesis: Yes, abstract patterns transfer (50-70% relative accuracy)
   - Alternative: No, patterns are domain-specific (20-30% transfer)

5. **Is guidance actually useful at enterprise scale?**
   - RQ: Does system create value that customers pay for?
   - Measurement: Phase 4 customer improvement + NPS
   - Hypothesis: Yes, 3%+ improvement is worth 5% compute cost
   - Alternative: No, benefit is marginal or cost is too high

---

## Risk Assessment

### Critical Risks (High Probability, High Impact)

#### Risk 1: Signal Quality is Fundamentally Noisy
- **Probability**: 40%
- **Impact**: High (project fails if signal <65% accuracy)
- **Mitigation**: Phase 1 specifically tests this with early gate
- **Contingency**: Shift to human-annotated trajectories (expensive but cleaner signal)

#### Risk 2: Catastrophic Forgetting Unsolvable
- **Probability**: 35%
- **Impact**: High (makes continuous learning impossible)
- **Mitigation**: Phase 3 tests extensively, explore LoRA alternatives
- **Contingency**: Use episodic memory instead of weight updates

#### Risk 3: Guidance Doesn't Actually Help Big Model
- **Probability**: 30%
- **Impact**: High (feature provides no value)
- **Mitigation**: Phase 2 tests specifically on hard problems
- **Contingency**: Research suggests real bottleneck is reasoning depth, not strategy selection

### Major Risks (Medium Probability, Medium Impact)

#### Risk 4: Cross-Domain Transfer Fails
- **Probability**: 45%
- **Impact**: Medium (limits scalability)
- **Mitigation**: Phase 1 tests transfer, Phase 3 accumulates cross-domain
- **Contingency**: Deploy domain-specific models instead of general

#### Risk 5: Enterprise Cost-Benefit Negative
- **Probability**: 25%
- **Impact**: Medium (market won't adopt)
- **Mitigation**: Phase 4 tests at beta customers
- **Contingency**: Find niche use cases where 3-5% improvement justifies cost

### Technical Risks (Lower Probability, Lower Impact)

#### Risk 6: Inference Latency Too High
- **Probability**: 15%
- **Impact**: Low (can optimize)
- **Mitigation**: Phase 2 measures overhead (<100ms target)
- **Contingency**: Batch inference, caching, model quantization

#### Risk 7: Small Model Overfits to Recent Data
- **Probability**: 25%
- **Impact**: Low (can fix with better training)
- **Mitigation**: Phase 3 tests for distribution drift
- **Contingency**: Regularization, older data weighting, ensemble methods

---

## Timeline and Milestones

```
Month 1-2: Phase 1 - Signal Quality
  Week 1-2: Data collection, feature engineering
  Week 3-4: Small model training & testing
  Week 5-6: Signal quality analysis
  Week 7-8: Cross-domain transfer testing
  ✓ GO/NO-GO GATE: >75% accuracy required

Month 3-4: Phase 2 - Guidance Effectiveness
  Week 9-10: Inference pipeline build
  Week 11-12: Big model + guidance testing
  Week 13-14: Collaboration protocol analysis
  Week 15-16: Decision rules for guidance
  ✓ GO/NO-GO GATE: ≥20% improvement required

Month 5-6: Phase 3 - Continuous Learning
  Week 17-18: Retraining pipeline setup
  Week 19-20: Catastrophic forgetting measurement
  Week 21-22: Cross-domain accumulation test
  Week 23-24: Confidence calibration tuning
  ✓ GO/NO-GO GATE: <10% degradation, ≥5% monthly improvement

Month 6-9: Phase 4 - Production Readiness
  Week 25-26: Budget-controlled deployment setup
  Week 27-28: Risk monitoring implementation
  Week 29-30: Beta customer deployment
  Week 31-32: Customer-specific learning validation
  Week 33-34: Production hardening
  Week 35-36: Final validation & decision
  ✓ FINAL GATE: ≥3% improvement at scale, <2% failure rate

```

---

## Team Requirements

### Roles Needed
1. **ML Research Lead** (0.5 FTE)
   - Small model training, fine-tuning, evaluation
   - Signal quality analysis, architecture decisions

2. **Systems Engineer** (0.5 FTE)
   - Inference pipeline, deployment, monitoring
   - Budget control system, rollback mechanisms

3. **Analyst** (0.25 FTE)
   - Data collection, feature engineering
   - Measurement, reporting, decision gate analysis

### Skills Needed
- **ML**: Fine-tuning, LoRA, continual learning, evaluation metrics
- **Systems**: Inference optimization, monitoring, production deployment
- **Research**: Experimental design, statistical analysis, documentation

---

## Budget Breakdown

| Category | Cost | Notes |
|----------|------|-------|
| **GPU Compute** | $8K-12K | Fine-tuning, inference, A/B testing |
| **Data Labeling** | $2K-4K | Manual annotations for validation (5% of dataset) |
| **Tools/Infrastructure** | $2K-3K | Unsloth, HF, LangSmith, monitoring |
| **Time** | $3K-6K | 2-3 researchers, 6 months |
| **Contingency** | $2K-4K | Unexpected challenges |
| **TOTAL** | **$17K-29K** | **$22K average** |

---

## Success Criteria (Overall)

### Must-Have (Hard Gates)
- ✅ Phase 1: >75% small model accuracy (signal is learnable)
- ✅ Phase 2: ≥20% improvement with guidance (feature creates value)
- ✅ Phase 3: <10% catastrophic forgetting (scaling is sustainable)
- ✅ Phase 4: ≥3% customer improvement (market viability)

### Should-Have (Soft Goals)
- ✓ Cross-domain transfer >50% (generalizability)
- ✓ Month-to-month improvement ≥5% (continuous learning works)
- ✓ Inference overhead <100ms (performance acceptable)
- ✓ False positive rate <2% (safety threshold)

### Nice-to-Have (Research Value)
- ✓ Better than SMART's 60% baseline (novel approach works better)
- ✓ Customer-specific learning demonstrated (IP defensibility)
- ✓ Clear decision rules for when to intervene (explainability)

---

## What Success Looks Like

### If All Phases Pass
```
Month 1: "Yes, small models can learn from trajectories (75% accuracy)"
Month 2: "Yes, guidance makes big model 20% better on hard problems"
Month 6: "Yes, learning scales month-to-month without forgetting"
Month 9: "Yes, customers see 3%+ improvement with auto-learning"

Result: Production-ready system
Timeline to market: 3-6 months additional hardening
Market size: $450B+ (agents that learn from experience)
```

### If Phase 1 Fails
```
Signal quality <65% accuracy
Conclusion: Success/failure alone is too noisy for learning
Research value: Clarifies why weak supervision fundamentally fails
Pivot: Need human-annotated trajectories or different mechanism
```

### If Phase 2 Fails
```
Guidance shows <15% improvement
Conclusion: Strategy selection is NOT the bottleneck
Research value: Clarifies that reasoning (not strategy) is limiting
Pivot: Supports WS1 (Emergent Reasoning Architecture) as more important
Implication: Token prediction approaches cannot solve this
```

### If Phase 3 Fails
```
Catastrophic forgetting >10% degradation
Conclusion: Continual learning is fundamentally harder than expected
Research value: Confirms 20-year unsolved problem in continual ML
Pivot: Use episodic memory (memory-based) instead of weight updates
```

### If Phase 4 Fails
```
Customer improvement <3%, cost-benefit negative
Conclusion: Approach is real but narrow application
Research value: Identifies which problem types actually benefit
Pivot: Narrow focus to high-value use cases, or reconsider approach
```

---

## Integration with Master Strategy

### How WS2 Fits
- **Primary Goal**: Build system that learns problem-solving strategies
- **Secondary Goal**: Prove token prediction ceiling can be transcended
- **Research Contribution**: Novel application of intervention-based learning + small models
- **Market Opportunity**: Agents that improve month-to-month from experience

### Dependency on Other Workstreams
- **WS1 (Intelligence Portability)**: May inform architecture (portable knowledge representation)
- **WS3 (Framework Convergence)**: May use unified trajectory format
- **WS4 (Self-Organization)**: May discover self-improvement patterns
- **WS5 (Test-Time Learning)**: May complement with runtime optimization

### Potential for Other Workstreams
- If WS2 fails, evidence that strategy learning is not bottleneck → supports WS1 (emergent reasoning) as primary
- If WS2 succeeds, creates data/patterns that WS4 can use for self-organization research
- If WS2 learns interpretable patterns, supports WS3 (framework convergence) with discovered principles

---

## Decision Framework

### Phase 1 Gate: Signal Quality
**Question**: Can small models learn from unlabeled trajectories?
- **GO** (>75% accuracy): Proceed to Phase 2
- **CONDITIONAL** (70-75% accuracy): Try human annotation + retest
- **NO-GO** (<70% accuracy): Signal is too noisy, pivot to WS1

### Phase 2 Gate: Guidance Value
**Question**: Does strategy guidance actually help?
- **GO** (≥20% improvement): Proceed to Phase 3
- **CONDITIONAL** (15-20% improvement): Narrow use cases + proceed
- **NO-GO** (<15% improvement): Strategy selection not bottleneck, pivot to WS1

### Phase 3 Gate: Continuous Learning Viability
**Question**: Can we scale learning without catastrophic forgetting?
- **GO** (<10% degradation): Proceed to Phase 4
- **CONDITIONAL** (10-15% degradation): Acceptable for non-critical use cases
- **NO-GO** (>15% degradation): Forgetting problem unsolvable with current approach

### Phase 4 Gate: Production Readiness
**Question**: Is this viable as enterprise product?
- **GO** (≥3% improvement, <2% failure rate): Proceed to market
- **CONDITIONAL** (2-3% improvement): Niche market applications
- **NO-GO** (<2% improvement, >3% failure): Cost-benefit negative for general market

---

## Next Steps (Immediate Actions)

### Week 1-2: Project Setup
- [ ] Assemble team (research lead, systems engineer, analyst)
- [ ] Set up compute infrastructure (GPU access, development environment)
- [ ] Finalize data collection protocol
- [ ] Create tracking/reporting system for metrics

### Week 3-4: Data Collection
- [ ] Identify 2-3 representative problem domains
- [ ] Implement trajectory logging system
- [ ] Begin collecting 1,000+ agent trajectories
- [ ] Create feature engineering pipeline

### Week 5-6: Model Selection & Training
- [ ] Choose between Qwen-3B and Phi-4 (test both if possible)
- [ ] Set up LoRA fine-tuning pipeline (Unsloth)
- [ ] Train initial small model on 500-1000 trajectories
- [ ] Evaluate on held-out test set

### Week 7-8: Phase 1 Completion
- [ ] Achieve >75% accuracy target
- [ ] Complete signal quality analysis
- [ ] Document confounding factors
- [ ] Phase 1 GO/NO-GO decision

---

## Approach B: Cognitive Architecture Implementation (SOAR)

### Overview

**Alternative to small models**: Implement SOAR-like problem-space reasoning with native symbolic learning.

Instead of:
- LLM generates operators
- Small model learns patterns
- Big model executes

We build:
- Explicit problem-space search
- Production rules that learn automatically
- Utility-based decision making

### How SOAR Works (Simplified)

```
Cycle:
1. Parse state → JSON representation
2. Query rules → Find applicable operators
3. Evaluate operators → Score each option
4. Decide → Select best or create sub-goal
5. Execute → Run selected action
6. Learn → Update rules and utilities automatically
```

### Why This Could Be Better

**Advantages**:
✅ Rules are explicit (portable across models)
✅ Learning is automatic (no trajectory fine-tuning)
✅ Decision path is transparent (explainable)
✅ No separate small model needed
✅ Scales to complex problems (SOAR handles chess, planning, code)
✅ Knowledge is symbolic (fully portable for WS1)

**Disadvantages**:
❌ Requires architectural redesign
❌ Harder to integrate with existing LLM frameworks
❌ Rule extraction/learning is non-trivial
❌ Needs explicit problem representation design

### Implementation Approaches

#### Option B1: Rule Engine + LLM (Hybrid)

```
Rule Engine (elaboration)    → Generates operators
LLM (evaluation)             → Scores operators
Decision logic               → Selects best
Executor                     → Runs action
Learning                     → Updates rules/utilities
```

**Cost**: Moderate (rule engine + LLM orchestration)
**Timeline**: 6-8 weeks
**Integration**: Medium (separate systems coordinate)

#### Option B2: Agentic Workflow (LangGraph-based)

```
Nodes in LangGraph:
1. State parser (JSON)
2. Operator generator (rules + LLM)
3. Operator evaluator (scoring)
4. Decision maker (conflict resolution)
5. Executor (run action)
6. Learning system (update knowledge)
```

**Cost**: Low (fits LLM ecosystem)
**Timeline**: 4-6 weeks
**Integration**: High (native to LangGraph)

#### Option B3: Native Implementation

```
Custom SOAR agent in Python:
- Working memory (JSON state)
- Production rules (database)
- Utilities (success tracking)
- Learning system (rule extraction)
```

**Cost**: High (significant development)
**Timeline**: 8-12 weeks
**Integration**: Low (new system)

### Prototype Timeline (6-9 months)

**Phase 1: Proof of Concept (Weeks 1-4)**
- Implement one SOAR cycle
- Hand-written rules (10-20)
- LLM for operator evaluation
- Test on simple problem domain

**Phase 2: Learning System (Weeks 5-8)**
- Add automatic rule extraction
- Implement utility tracking
- Test improvement over problem sequences
- Measure: accuracy growth over 20-30 problems

**Phase 3: Hybrid Integration (Weeks 9-16)**
- Combine with LLM perception layer
- Integrate with small model learning (parallel)
- Test on diverse problem domains
- Measure: novel problem performance

**Phase 4: Comparison & Decision (Weeks 17-24)**
- Side-by-side evaluation: Approach A vs. B
- Measure: reasoning quality, learning curve, portability
- Publish findings
- Recommend path forward

### Research Questions

1. **Rule Learning**: How many successful traces needed to extract good rules?
2. **Scalability**: Can SOAR handle 100+ rules without performance degradation?
3. **Operator Evaluation**: How do we score operators when LLM confidence is low?
4. **Sub-Goals**: When should we create sub-goals vs. accept best option?
5. **Transfer**: Do rules from one problem domain help another?
6. **Portability**: Can SOAR rules transfer across different LLMs?

### Comparison: Approach A vs. B

| Dimension | Small Model (A) | SOAR (B) |
|-----------|---|---|
| **Implementation** | Easy | Medium |
| **Integration** | Seamless | Needs design |
| **Explainability** | Low (black box) | High (transparent) |
| **Portability** | Low (neural weights) | High (symbolic rules) |
| **Learning** | Implicit patterns | Explicit rules + utilities |
| **Reasoning Quality** | Limited (still token pred) | True reasoning (problem-space search) |
| **Time to POC** | 2-3 weeks | 4-6 weeks |
| **Research Risk** | Medium | Low (proven architecture) |
| **WS1 Alignment** | Poor (weights) | Excellent (rules) |
| **WS3 Alignment** | Medium (LLM-based) | High (framework-agnostic) |

### Hybrid Approach (Recommended)

Run both in parallel with synergy:

```
SOAR Agent
  ├─ Symbolic rules (explicit learning)
  ├─ Utility tracking
  └─ Problem-space reasoning
       ↓ (feed to)
Small Model
  ├─ Learn from SOAR trace patterns
  ├─ Implicit pattern recognition
  └─ Soft guidance
       ↓ (feed back to)
SOAR Agent
  ├─ Use small model confidence for sub-goal creation
  ├─ Weight utilities by small model agreement
  └─ Improve decision-making
```

**Benefits**:
- SOAR ensures explainability
- Small model learns implicit patterns
- Rules are portable (WS1)
- Learning is automatic
- Each improves the other

### Recommendation for WS2

**Start with**: Approach B2 (Agentic SOAR workflow)

**Why**:
1. ✅ Fits naturally into LangGraph
2. ✅ Lower implementation cost (weeks not months)
3. ✅ Aligned with WS1 (symbolic portability)
4. ✅ Aligned with WS3 (framework-agnostic)
5. ✅ Proven approach (40+ years of SOAR research)
6. ✅ Can integrate small model learning later

**Then explore**: Hybrid (SOAR + small model) by month 6

---

## References

**Papers**:
- SMART (2024): Strategy meta-learning
- DeepSeek-R1: Token prediction at scale
- SOAR/ACT-R: Cognitive architectures
- CLIN (2023): Continual learning in agents
- Experience Replay in Offline RL

**Datasets**:
- TOUCAN: Agent trajectories
- AgentBank: Real-world agent interactions
- Open-source agent logs (LangChain, LangSmith)

**Tools**:
- Unsloth: Fast LoRA fine-tuning
- Hugging Face TRL: Training pipeline
- LangSmith: Monitoring & evaluation
- Weights & Biases: Experiment tracking

---

## Document Version History

| Date | Status | Notes |
|------|--------|-------|
| 2025-12-05 | v1.0 - ACTIVE | Initial research plan created, intervention-based learning approach integrated |

---

**Status**: Ready for Phase 1 Execution
**Timeline**: Start immediately, complete by Month 9
**Impact**: Defines path to production-ready agent learning system
