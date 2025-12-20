# LLM Learning Techniques - Comprehensive Quick Reference Guide

**Status**: Complete Reference Guide
**Date**: December 9, 2025
**Purpose**: Clarify LLM learning paradigms, techniques, and their use cases

---

## Executive Summary

Large Language Models learn through various training paradigms, each suited for different objectives:

- **Foundational Learning** (pre-training): RL, SFT, Supervised/Unsupervised
- **Optimization Techniques**: Fine-tuning, Transfer Learning, In-Context Learning
- **Reinforcement Learning Variants**: TAO, Replay, RLHF, DPO
- **Evaluation/Improvement**: Preference-based learning, Adversarial training

This guide provides quick reference for understanding what each technique does, when to use it, and how they relate.

---

## Part 1: Core Learning Paradigms

### 1.1 Reinforcement Learning (RL)

**What It Is**: Agent learns by interacting with environment, receiving rewards/penalties, optimizing cumulative reward.

**Core Concept**:
```
Agent → Action → Environment → Reward/Penalty → Update Policy
   ↑_________________________________________|
```

**Key Components**:
- **State (s)**: Current situation
- **Action (a)**: Agent's choice
- **Reward (r)**: Feedback signal
- **Policy (π)**: Mapping from state → action
- **Value Function (V)**: Expected cumulative reward from state

**Common RL Algorithms**:
- **Q-Learning**: Learn value of state-action pairs
- **Policy Gradient**: Directly optimize policy parameters
- **Actor-Critic**: Combine value function (critic) + policy (actor)

**Use Cases**:
- Game playing (AlphaGo, Chess)
- Robotics control
- Resource optimization
- LLM alignment with human preferences (RLHF)

**Strengths**:
- Handles complex, sequential decision-making
- Can explore and discover novel solutions
- Naturally handles delayed rewards

**Weaknesses**:
- Requires extensive interaction/simulation (expensive)
- Can be unstable during training
- Hard to control exploration vs. exploitation
- Data inefficient (needs many trials)

**Example in LLMs**:
```
State: "Incomplete sentence: The capital of France is..."
Action: Generate token (e.g., "Paris", "Lyon")
Reward: Human feedback (correct=+1, incorrect=-1)
Update: Increase probability of "Paris", decrease "Lyon"
```

---

### 1.2 Supervised Fine-Tuning (SFT)

**What It Is**: Train model to predict outputs given inputs using labeled examples (input-output pairs).

**Core Concept**:
```
Input → Model → Predicted Output
                      ↓
                Compare with Ground Truth
                      ↓
                Update Weights (Gradient Descent)
```

**Key Components**:
- **Training Data**: Input-output pairs with correct labels
- **Loss Function**: Measures prediction error (e.g., Cross-Entropy)
- **Gradient Descent**: Optimization algorithm to minimize loss
- **Epochs**: Number of passes through data

**Common SFT Approaches**:
- **Causal Language Modeling**: Predict next token given previous tokens
- **Sequence-to-Sequence**: Map input sequence to output sequence
- **Classification**: Map input to class labels

**Use Cases**:
- Teaching LLM to follow specific formats
- Instruction following
- Code generation (code-specific fine-tuning)
- Domain adaptation (medical, legal, scientific domains)
- Multi-turn conversation training

**Strengths**:
- Simple, well-understood training procedure
- Fast convergence with good labeled data
- Predictable results
- Easy to implement and debug

**Weaknesses**:
- Requires high-quality labeled data (expensive)
- Doesn't learn to handle uncertainty or preferences
- Can overfit on small datasets
- Doesn't capture human value judgments well

**Example in LLMs**:
```
Input: "Write a Python function to check if a number is prime"
Ground Truth: "def is_prime(n): ..."
Loss: Cross-entropy between predicted and ground truth tokens
Update: Increase probability of correct tokens, decrease incorrect
```

---

### 1.3 Supervised vs. Unsupervised Learning

**Supervised Learning (Labeled Data)**

**What It Is**: Learn from data with explicit labels/targets.

**Characteristics**:
- Requires human annotation
- Loss function directly compares prediction to ground truth
- Training objective is clear and measurable

**Use Cases for LLMs**:
- SFT on instruction-response pairs
- Named Entity Recognition (NER)
- Question-answering with correct answers
- Machine translation (source-target pairs)

**Examples**:
- (Question, Answer) pairs
- (Code comment, Code) pairs
- (English sentence, French translation)

**Strengths**:
- Clear learning signal
- Measurable progress
- Predictable results

**Weaknesses**:
- Expensive labeling
- Limited to labeled examples
- Can't learn from unlabeled data

---

**Unsupervised Learning (Unlabeled Data)**

**What It Is**: Learn patterns from data WITHOUT explicit labels.

**Characteristics**:
- No human annotation needed
- Model discovers hidden structure
- Objective is implicit (compression, reconstruction, clustering)

**Common Unsupervised Objectives**:
- **Language Modeling**: Predict next token (standard pre-training)
- **Masked Language Modeling**: Predict masked tokens in context
- **Contrastive Learning**: Make similar items closer, dissimilar items farther
- **Clustering**: Group similar items
- **Dimensionality Reduction**: Compress high-dimensional data

**Use Cases for LLMs**:
- Pre-training on raw internet text
- Learning general language patterns
- Discovering conceptual relationships
- Zero-shot generalization

**Examples**:
- GPT pre-training: "The quick brown fox [PREDICT: jumps]"
- BERT: "[MASK] quick brown fox" → predict masked token
- Contrastive: Make "dog" close to "puppy", far from "cat"

**Strengths**:
- No labeling cost
- Unlimited data available
- Learns general, transferable patterns
- Foundation for downstream tasks

**Weaknesses**:
- Learning signal is indirect
- Slower convergence
- Can learn spurious patterns
- Harder to measure progress

---

## Part 2: The Learning Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│                    LLM Learning Techniques                  │
└─────────────────────────────────────────────────────────────┘
                              │
                ┌─────────────┼─────────────┐
                │             │             │
           ┌────▼────┐   ┌────▼────┐   ┌───▼────┐
           │ Pre-     │   │ Fine-   │   │ Online/│
           │ training │   │ tuning  │   │ Deploy │
           └────┬────┘   └────┬────┘   └───┬────┘
                │             │             │
        ┌───────┼───────┐     │             │
        │               │     │             │
    ┌───▼──┐       ┌───▼──┐  │             │
    │RL    │       │SFT   │  │             │
    │(GPT) │       │(PPO) │  │             │
    └──────┘       └──────┘  │             │
                              │             │
                        ┌─────▼─────┐      │
                        │RL from LLM│      │
                        │ Feedback  │      │
                        │ (RLHF)    │      │
                        └───────────┘      │
                                           │
                                   ┌───────▼────────┐
                                   │ In-Context     │
                                   │ Learning (ICL) │
                                   │ Few-Shot       │
                                   └────────────────┘
```

---

## Part 3: Fine-Tuning Techniques

### 3.1 Full Fine-Tuning

**What It Is**: Update ALL model parameters on task-specific data.

```
Pre-trained Model (All params frozen)
        ↓
    Add Task-Specific Layer
        ↓
    Unfreeze ALL parameters
        ↓
    Train on Task Data (Update all weights)
        ↓
    Task-Specific Model
```

**Characteristics**:
- Modifies every weight in the model
- Requires full model copy per task
- Most flexible, best accuracy
- Most computationally expensive

**Use Cases**:
- Domain adaptation (legal, medical, code)
- Large datasets with new distribution
- Task-specific optimization where accuracy matters most

**Computational Cost**: High (full gradient computation + memory)

**Example**:
```
Start: GPT-3 (175B parameters)
Data: Medical notes + clinical outcomes (100k examples)
Result: Medical-GPT with all 175B parameters optimized
Storage: Need separate copy (175B params × 2 bytes = ~350GB)
```

---

### 3.2 Parameter-Efficient Fine-Tuning (PEFT)

**What It Is**: Fine-tune only a SMALL fraction of parameters, freeze the rest.

**Hierarchy**:

```
┌─ PEFT (Parameter-Efficient Fine-Tuning) ─┐
│                                           │
├─ 3.2.1 LoRA (Low-Rank Adaptation)        │
├─ 3.2.2 QLoRA (Quantized LoRA)            │
├─ 3.2.3 Adapters                          │
├─ 3.2.4 Prefix Tuning                     │
├─ 3.2.5 Prompt Tuning                     │
└─ 3.2.6 BitFit                            │
```

#### 3.2.1 LoRA (Low-Rank Adaptation)

**What It Is**: Instead of updating weight matrix W directly, learn two small matrices A and B such that update ≈ A × B.

**Formula**:
```
Standard: W_new = W + ΔW  (update is large)
LoRA:     W_new = W + A × B  (A and B are small)

Example: W is 1000×1000 (1M params)
         A is 1000×8 (8k params)
         B is 8×1000 (8k params)

Update params: 16k instead of 1M (1.6% of original)
```

**Characteristics**:
- Updates only ~1-2% of parameters
- Minimal memory overhead
- Fast training
- Can create task-specific adapters
- Doesn't modify model for inference

**Use Cases**:
- Multi-task fine-tuning (different LoRA for each task)
- Domain adaptation with limited budget
- Mobile/edge deployment (add LoRA to base model)
- Quick iteration on multiple variations

**Strengths**:
- 10-100x memory savings
- 3-10x faster training
- Can combine multiple LoRAs
- Base model unchanged (no catastrophic forgetting)

**Weaknesses**:
- Slightly lower accuracy than full fine-tuning
- Adds inference latency (small)
- Rank selection is hyperparameter

**Comparison to Full Fine-Tuning**:
```
Full Fine-Tuning:    GPT-2 (1.5B params) → requires 6GB VRAM
LoRA:                GPT-2 (rank=8) → requires 1GB VRAM
Accuracy trade-off:  Full wins by ~2-3%, but LoRA often sufficient
```

---

#### 3.2.2 QLoRA (Quantized LoRA)

**What It Is**: LoRA + Quantization = extreme parameter efficiency.

**How It Works**:
```
Original Model (fp32): 4 bytes per parameter
        ↓
Quantized to int8: 1 byte per parameter (75% reduction)
        ↓
Add LoRA adapters: Minimal overhead
        ↓
Fine-tune: Update only LoRA, frozen quantized model
        ↓
Result: Train 7B model on consumer GPU (24GB VRAM)
```

**Use Cases**:
- Fine-tune very large models on limited hardware
- Local fine-tuning without cloud
- Cost-effective domain adaptation

**Strengths**:
- Can fine-tune 70B+ models on single GPU
- Extremely low memory
- Preserves most accuracy

**Weaknesses**:
- Training is slower (quantization overhead)
- More complex to implement

---

#### 3.2.3 Adapters

**What It Is**: Small trainable modules inserted into model layers.

**Architecture**:
```
Original Layer Output
        ↓
    [Adapter Module]  ← Small bottleneck (trainable)
        ↓
    Feed to Next Layer
```

**Characteristics**:
- Smaller than LoRA (~100x parameter reduction)
- Inserted at specific layers
- Each task has its own adapter

**Use Cases**:
- Multitask learning
- Language-specific adaptation
- Continual learning scenarios

**Strengths**:
- Very parameter-efficient
- Modular
- Can compose adapters

**Weaknesses**:
- More architectural changes needed
- Slightly more complex than LoRA

---

#### 3.2.4 Prefix Tuning

**What It Is**: Only train a learnable PREFIX added to model inputs.

**How It Works**:
```
Task 1: [Learnable Prefix 1] + Input → Model → Output
Task 2: [Learnable Prefix 2] + Input → Model → Output
                               (same frozen model)
```

**Characteristics**:
- Learn only prefix (task-specific virtual tokens)
- Model parameters frozen
- Different prefix per task

**Use Cases**:
- Multi-task learning
- Few-shot adaptation
- Prompt optimization

**Strengths**:
- Minimal parameters (prefix only)
- Fast training
- Clear task separation

**Weaknesses**:
- Can't change deeper model behavior
- Limited to prompt-level changes

---

#### 3.2.5 Prompt Tuning

**What It Is**: Learn soft prompts (continuous vectors) instead of discrete tokens.

**How It Works**:
```
Traditional prompt: "Classify as [positive/negative]: "
                    (discrete tokens)

Soft prompt:        [Learnable Vector 1, Vector 2, Vector 3, ...]
                    (continuous embeddings)

Result: Concatenate soft prompt + input → Model → Output
```

**Use Cases**:
- Few-shot learning
- Fast domain adaptation
- Prompt optimization

**Strengths**:
- Very parameter-efficient
- Learns better prompts automatically
- No architecture changes

**Weaknesses**:
- Very limited parameter budget
- Less expressive than LoRA

---

#### 3.2.6 BitFit

**What It Is**: Only train the bias parameters (not weight matrices).

**Concept**:
```
Weight Matrix W: [Frozen]
Bias Vector b:   [Trainable]

Update only: h = W·x + b
                      ↑ train this, freeze W
```

**Characteristics**:
- Minimal parameter overhead (~0.1% of model)
- Simplest PEFT method
- Task-specific fine-tuning with almost no cost

**Use Cases**:
- Ultra-low-resource scenarios
- Proof-of-concept adaptation

**Strengths**:
- Minimal memory
- Conceptually simple

**Weaknesses**:
- Very limited expressiveness
- Accuracy drop can be significant

---

### 3.3 Fine-Tuning Comparison Table

| Technique | Parameters | Memory | Speed | Accuracy | Best For |
|-----------|-----------|--------|-------|----------|----------|
| **Full Fine-Tuning** | 100% | High | Slow | Highest | Max accuracy, large data |
| **LoRA** | ~1-2% | Low-Med | Fast | 97-99% | Multi-task, quick iteration |
| **QLoRA** | ~1-2% + quantization | Very Low | Med | 96-98% | Limited hardware, large models |
| **Adapters** | ~0.5% | Very Low | Fast | 96-98% | Multi-task composition |
| **Prefix Tuning** | ~0.1-1% | Very Low | Fast | 95-97% | Few-shot, multitask |
| **Prompt Tuning** | ~0.01% | Minimal | Fastest | 90-95% | Extreme efficiency |
| **BitFit** | ~0.1% | Minimal | Fastest | 85-92% | Ultra-light adaptation |

---

## Part 4: Reinforcement Learning from Human Feedback (RLHF) and Variants

### 4.1 RLHF (Reinforcement Learning from Human Feedback)

**What It Is**: Train model to optimize for human preferences using RL signals derived from human annotations.

**Three-Stage Pipeline**:

```
┌─────────────────────────────────────────────────────┐
│ Stage 1: Supervised Fine-Tuning (SFT)              │
│ ────────────────────────────────────────────────   │
│ Input: Instruction → Output: Expert Response       │
│ Model learns basic task competency                 │
│                                                   │
│                    ↓                               │
│                                                   │
│ Stage 2: Reward Model Training                    │
│ ────────────────────────────────────────────────   │
│ Input: Two LLM outputs                            │
│ Label: Which is better? (A > B or B > A)          │
│ Model learns to predict human preference          │
│                                                   │
│                    ↓                               │
│                                                   │
│ Stage 3: RL Fine-Tuning (PPO)                     │
│ ────────────────────────────────────────────────   │
│ Policy: LLM generates response                    │
│ Reward: Reward model scores response              │
│ Loss: Maximize expected reward - KL penalty       │
│ Update: Policy gradient (PPO algorithm)           │
└─────────────────────────────────────────────────────┘
```

**Stage 1: SFT Phase**

```
Input: "Explain gravity to a 5-year-old"
Expert Output: "Gravity is a force that pulls things down..."
Loss: Cross-entropy between predicted and expert tokens
Train: Standard supervised learning
```

**Stage 2: Reward Model Training**

```
Prompt: "Explain gravity to a 5-year-old"

Response A: "Gravity is when things fall"
Response B: "Gravity is a force pulling objects toward Earth's center"

Human Annotation: B is better (score_B > score_A)
Reward Model learns: P(B is better than A) = f(A, B, prompt)

Loss: Binary cross-entropy on pairwise comparisons
```

**Stage 3: RL Fine-Tuning**

```
Prompt: "Explain gravity"
LLM generates: Response X
Reward Model scores: r(X) = 0.7 (good!)

Policy Gradient Update:
- Increase probability of tokens that led to high-reward response
- Decrease probability of tokens that led to low-reward response
- Add KL penalty: Don't drift too far from SFT model

Loss = -r(X) + β·KL(LLM || SFT_model)
       ↑reward  ↑keep close to original
```

**Key Components**:
- **Reward Model**: Learns human preference signal
- **Reference Model**: SFT model to prevent drift
- **PPO (Proximal Policy Optimization)**: RL algorithm
- **KL Penalty**: Regularization to prevent collapse

**Use Cases**:
- Aligning LLM with human values
- Improving response quality
- Instruction following
- Safety/harmlessness training

**Strengths**:
- Learns from human preferences directly
- Improves response quality significantly
- Can train for multiple objectives (helpful, harmless, honest)

**Weaknesses**:
- Requires extensive human annotations (expensive)
- Training is unstable (RL is hard)
- Needs reward model (proxy for human judgment)
- Can reward gaming (model exploits reward model)

**Typical Numbers**:
- Stage 1 (SFT): 10k-50k examples
- Stage 2 (Reward Model): 50k-500k pairwise comparisons
- Stage 3 (RL): 10k-100k prompts for RL training
- Total cost: $1M-$10M for frontier models

---

### 4.2 DPO (Direct Preference Optimization)

**What It Is**: Train LLM to optimize human preferences DIRECTLY without separate reward model.

**Key Innovation**: Skip the reward model! Learn preferences end-to-end.

**Comparison to RLHF**:

```
RLHF:
  SFT Model → Reward Model (learns preferences)
           → RL Fine-tuning (optimize with RL)
           → Result

DPO:
  SFT Model + Preference Data → Direct Optimization
           → Result

Time: DPO is ~8x faster
Cost: DPO is cheaper (no reward model training)
```

**How DPO Works**:

```
Input: Prompt
Outputs: Good response (y_w), Bad response (y_l)

Loss = -log(sigmoid(β · (log π(y_w|x) - log π(y_l|x))))

Where:
- π(y_w|x) = probability model assigns to good response
- π(y_l|x) = probability model assigns to bad response
- β = scaling factor
- sigmoid makes it classification-like

Interpretation: Maximize probability of good response relative to bad
```

**Training**:
```
For each example (prompt, good_response, bad_response):
  1. Forward pass: Compute log probabilities
  2. Loss: Make good response MORE likely than bad
  3. Gradient: Update model to increase gap
  4. Repeat
```

**Use Cases**:
- Fast preference alignment
- Limited annotation budget
- Domain-specific preference learning
- Iterative improvement

**Strengths**:
- No separate reward model needed
- Simpler pipeline (1 stage instead of 3)
- Faster training (~8x)
- More stable than RLHF
- Better generalization (learns relative preferences, not absolute scores)

**Weaknesses**:
- Still requires preference annotations
- Newer technique (less battle-tested)
- Requires good SFT base model

**Typical Numbers**:
- Training data: 10k-100k preference pairs
- Training time: Hours to days (vs. weeks for RLHF)
- Cost: 10-20% of RLHF cost

---

### 4.3 IPO (Iterative Preference Optimization)

**What It Is**: DPO variant that iteratively refines preferences.

**How It Differs from DPO**:
```
DPO: Single pass optimization on static preference data

IPO:
  Iteration 1: Train on preferences
           ↓
  Iteration 2: Generate new examples with trained model
           ↓
  Iteration 3: Annotate new examples
           ↓
  Iteration 4: Train on expanded dataset
           ↓
  Repeat until convergence
```

**Use Cases**:
- Continuous improvement
- Bootstrapping from initial model
- Limited initial annotation budget

---

### 4.4 Comparison: RLHF vs. DPO vs. IPO

| Aspect | RLHF | DPO | IPO |
|--------|------|-----|-----|
| **Stages** | 3 (SFT → RM → RL) | 1 (Direct) | Multi-pass |
| **Reward Model** | Required | Not needed | Not needed |
| **Training Time** | 4-8 weeks | 2-4 days | 1-2 weeks |
| **Cost** | Very high | Medium | Medium |
| **Stability** | Unstable (RL) | Stable | Stable |
| **Accuracy** | Highest | High | High |
| **Exploration** | Good | Limited | Good (iterative) |
| **Used by** | OpenAI (RLHF for ChatGPT) | Anthropic (DPO for Claude) | Research |

---

## Part 5: Advanced Techniques

### 5.1 TAO (Test-Time Augmentation Optimization)

**What It Is**: Improve model performance at TEST-TIME by generating multiple outputs and selecting best.

**How It Works**:

```
Input: "What is the capital of France?"

Generate 5 responses:
  1. "Paris" → Score: 0.95
  2. "The capital of France is Paris" → Score: 0.92
  3. "Paris is the capital" → Score: 0.88
  4. "London" → Score: 0.05
  5. "I'm not sure" → Score: 0.10

Select: Response 1 (highest score)
Output: "Paris"
```

**Key Idea**: Don't just take first output; generate multiple and pick best.

**Scoring Methods**:
- **Likelihood**: Probability model assigns to response
- **Length-normalized**: Adjust for response length bias
- **Semantic similarity**: How similar to query
- **Reward model**: Use separate evaluator
- **Voting**: Multiple models vote

**Use Cases**:
- Improving accuracy without retraining
- Uncertainty estimation (variance in outputs)
- Ensemble-like behavior from single model
- Cost-effective improvement

**Strengths**:
- No retraining needed
- Can improve accuracy by 5-15%
- Reveals model uncertainty

**Weaknesses**:
- 5-10x slower inference (generate N outputs)
- Doesn't help with fundamental model limitations
- Scoring function must be good

**Example with LLMs**:
```
Prompt: "Write a Python function to reverse a list"

Temperature=0.7 (diverse samples):
  Sample 1: "def reverse(lst): return lst[::-1]"
  Sample 2: "def reverse(lst): return list(reversed(lst))"
  Sample 3: "def reverse(lst): result=[]; ...[loop]"

Scoring: Check syntax, simplicity, performance
Select: Sample 1 (cleanest)
```

---

### 5.2 Replay / Experience Replay

**What It Is**: Store past experiences and retrain on them to improve stability and sample efficiency.

**Concept**:
```
Experience Buffer:
  ┌─────────────────────────────────┐
  │ (state, action, reward, next_s) │ ← Sample t
  │ (state, action, reward, next_s) │ ← Sample t-1
  │ (state, action, reward, next_s) │ ← Sample t-2
  │ ...                             │
  └─────────────────────────────────┘
           ↓
    Sample random batch
           ↓
    Train on this batch
           ↓
    Update policy/value function
```

**Why It Helps**:
1. **Breaks correlation**: Consecutive experiences are correlated; random sampling decorrelates
2. **Stability**: Reduces variance in gradient estimates
3. **Efficiency**: Reuse data multiple times
4. **Data:** Sample from past, don't need fresh interaction

**Types of Replay**:

#### 5.2.1 Standard Experience Replay
```
Buffer: Store (s, a, r, s') for every step
Sample: Random batch of size B
Train: Update on batch
Forget: Remove old experiences when buffer full
```

**Use**: DQN, Actor-Critic algorithms

#### 5.2.2 Prioritized Experience Replay
```
Buffer: Store experiences + TD-error (how wrong we were)
Sample: Bias toward high TD-error experiences (more informative)
Train: Update on batch
Weight: Correct for sampling bias with importance weights

Result: Learn faster from surprising/wrong predictions
```

#### 5.2.3 Hindsight Experience Replay (HER)
```
Original Experience:
  Goal: Reach position (10, 10)
  Outcome: Reached (5, 5)
  Reward: -1 (failed)

Relabel:
  Goal: Reach position (5, 5)
  Outcome: Reached (5, 5)
  Reward: +1 (succeeded!)

Benefit: Learn from failures by treating outcome as goal
```

**Use Cases**:
- Goal-reaching tasks (robotics)
- Sparse reward environments
- Sample-efficient learning

**Use Cases in LLMs**:
- Store successful generations
- Retrain on important examples
- Improve sample efficiency

**Strengths**:
- Increases sample efficiency (reuse data)
- Stabilizes training
- Reduces variance

**Weaknesses**:
- Requires buffer storage (memory)
- Off-policy (learning from old data, policy changed)
- Needs importance sampling correction

---

### 5.3 RAFT (Reward Augmented Fine-Tuning)

**What It Is**: Combine SFT with reward feedback for faster training.

**How It Works**:
```
Standard SFT:
  Loss = -log P(y_true | x)
  Only learns from ground truth examples

RAFT:
  Loss = -log P(y | x) where y ∈ {high-reward outputs}
  Learn from multiple good outputs (not just ground truth)

Benefit: More training signal, faster convergence
```

**Process**:
```
Step 1: SFT model generates outputs
Step 2: Score outputs with reward model
Step 3: Keep high-reward outputs (y_aug)
Step 4: Supervised train on {x, y_aug}
Step 5: Repeat

Result: SFT + RL signal without full RL training
```

**Use Cases**:
- Fast preference alignment
- When reward model is good but imperfect
- Combining labeled data + reward signals

**Strengths**:
- Simpler than full RL
- Faster than RLHF
- Combines labeled + reward data

**Weaknesses**:
- Requires good reward model
- Still requires some RL-like components
- Reward model errors propagate

---

### 5.4 Constitutional AI (CAI)

**What It Is**: Train LLM to follow a set of principles/constitution without extensive human feedback.

**Process**:
```
Step 1: Provide Constitution (set of principles)
  Example:
    1. "Be helpful"
    2. "Be honest"
    3. "Be harmless"
    4. "Avoid harmful content"

Step 2: Generate Critique
  LLM generates response → LLM critiques it against constitution

  Prompt: "Evaluate if this response violates the constitution"
  Output: "Yes, it's biased" or "No, it follows constitution"

Step 3: Revise
  LLM generates revised response based on critique

Step 4: Supervised Fine-tune
  Train on (prompt, revised_response) pairs

Step 5: Optional: RLHF
  Use revised responses to train reward model
  Then RLHF as usual
```

**Advantages**:
- Reduces human annotation (LLM self-critiques)
- Principles are transparent
- Can update constitution without retraining

**Use Cases**:
- Safety alignment
- Value alignment
- Bias reduction

**Example**:
```
Constitution:
  1. "Avoid stereotypes"
  2. "Be factual"
  3. "Be respectful"

Query: "Why are programmers lazy?"

Initial Response: "Programmers are lazy because they automate everything"

LLM Critique: "This violates principle 1 (stereotype)"

Revised Response: "Many programmers are motivated by efficiency; they
                   automate repetitive tasks to focus on complex problems"

Train: SFT on revised response
```

---

## Part 6: Training Paradigm Comparison

```
┌──────────────────────────────────────────────────────────────────┐
│                     LLM Learning Methods                          │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  STAGE              METHOD              COST      DIFFICULTY     │
│  ──────────────────────────────────────────────────────────────   │
│                                                                  │
│  Pre-training       Unsupervised RL      Very High   Very Hard    │
│                     (Next-token pred)                             │
│                                                                  │
│  ─────────────────────────────────────────────────────────────   │
│                                                                  │
│  Supervised         SFT                  Medium      Easy         │
│                     Full Fine-tuning                              │
│                                                                  │
│  ─────────────────────────────────────────────────────────────   │
│                                                                  │
│  Parameter-         LoRA                 Low         Easy         │
│  Efficient          QLoRA                Low         Easy         │
│                     Adapters             Low         Medium       │
│                     Prefix Tuning        Very Low    Medium       │
│                                                                  │
│  ─────────────────────────────────────────────────────────────   │
│                                                                  │
│  Preference         RLHF                 Very High   Very Hard    │
│  Learning           DPO                  High        Medium       │
│                     IPO                  High        Medium       │
│                     Constitutional AI    Medium      Medium       │
│                                                                  │
│  ─────────────────────────────────────────────────────────────   │
│                                                                  │
│  Test-time          TAO                  Low*        Easy         │
│                     Ensemble voting      Low*        Easy         │
│                                                                  │
│  * Additional inference cost, not training cost                  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Part 7: When to Use Each Technique

### Decision Tree

```
┌─ Do you have labeled data? ─┐
│                              │
├─ YES → SFT (Supervised)      │
│        ├─ Large dataset (>100k)?     → Full Fine-tuning
│        ├─ Medium dataset (10k-100k)? → LoRA or QLoRA
│        └─ Small dataset (<10k)?      → Prompt Tuning or BitFit
│
├─ NO → Unsupervised Learning
│       ├─ Pre-train from scratch?     → Language Modeling (RL)
│       └─ Improve existing model?     → TAO or few-shot learning
│
└─ Do you have human preference data? ─┐
                                       │
                            ├─ YES → DPO or RLHF?
                            │        ├─ Fast iteration? → DPO
                            │        └─ Max accuracy?   → RLHF
                            │
                            └─ NO → Constitutional AI (self-critique)
```

### Quick Reference Table

| Goal | Best Method | Cost | Time | Data Needed |
|------|-------------|------|------|-------------|
| **Adapt to new domain** | LoRA | Low | Days | 10k-50k examples |
| **Max accuracy** | Full Fine-tuning | High | Weeks | 100k+ examples |
| **Limited budget** | QLoRA | Very Low | Days | 10k-50k examples |
| **Align with preferences** | DPO | Medium | Days | 10k pairwise prefs |
| **Safety/values** | Constitutional AI | Medium | Days | Constitution + examples |
| **Improve test-time** | TAO | Very Low* | Minutes | None (inference only) |
| **Multi-task** | Adapters/LoRA | Low | Days | 5k-20k per task |
| **Few-shot learning** | Prompt Tuning | Very Low | Hours | 100-1k examples |
| **Uncertainty** | TAO ensemble | Low* | Seconds | None (inference) |

*Test-time methods have high inference cost but zero training cost

---

## Part 8: Real-World Examples

### Example 1: Fine-tune GPT-2 for Code Generation

**Goal**: Improve GPT-2 on Python code tasks

**Data Available**: 20k code examples with solutions

**Solution**:
```
1. Base Model: GPT-2 pre-trained
2. Method: LoRA (not enough data for full fine-tuning)
3. Training:
   - LoRA rank: 8
   - Learning rate: 1e-4
   - Epochs: 3
   - Batch size: 32
4. Cost: ~4 GPU hours
5. Result: 92% accuracy on test code (vs 45% baseline)

Files needed:
  - train_lora.py (LoRA training script)
  - config.yaml (hyperparameters)
  - data/train.jsonl (20k examples)
```

---

### Example 2: Align Claude for Safety

**Goal**: Ensure Claude follows safety principles

**Data Available**: 100k preference judgments (which response is safer)

**Solution**:
```
1. Base Model: Claude (SFT model)
2. Method: DPO (faster than RLHF)
3. Training:
   - Preference data: 100k pairs
   - Training epochs: 5
   - Learning rate: 5e-6
   - Batch size: 8
4. Cost: ~2-4 days on 8 A100 GPUs
5. Result: 98% preference match with constitution

Alternative (Constitutional AI):
  - Constitution: 10 safety principles
  - Self-critique on 50k examples
  - SFT on revised responses
  - Cost: 1-2 days (faster, less human annotation)
```

---

### Example 3: Deploy Medical Chat on Edge Device

**Goal**: Run medical LLM on iPad (4GB RAM)

**Solution**:
```
1. Base Model: Llama-2 7B
2. Method: QLoRA (extreme efficiency)
   - Quantize to int8: 7B params → 7GB
   - LoRA rank: 8 → +56MB
   - Total: ~7.1GB (compresses to ~3.5GB with quantization)
3. Medical Data: 10k medical Q&A pairs
4. Training: 1 day on RTX 3080
5. Deployment:
   - Run quantized base model + LoRA
   - Fits in 4GB iPad memory
   - Inference: ~500ms per response

Cost benefit:
  - Full model would need $50M GPU setup
  - QLoRA approach: $200 GPU + 1 day training
  - 250x cost reduction
```

---

### Example 4: Continuous Learning System

**Goal**: Model improves from user feedback in production

**Solution**:
```
Method: DPO with Replay

1. Start: Pre-trained Claude
2. Deploy: Users interact, provide feedback (good/bad)
3. Replay Buffer: Store (prompt, good_response, bad_response)
4. Weekly Update:
   - Sample 10k preference pairs from buffer
   - Train DPO for 1 day
   - Deploy new version
   - Evaluate on validation set
5. Result: 1-2% accuracy improvement per month

Alternative (RAFT):
  1. Store user interactions
  2. Score with learned reward model
  3. SFT on high-reward outputs weekly
  4. Simpler, faster than DPO
```

---

## Part 9: Terminology Quick Reference

| Term | What | When Use |
|------|------|----------|
| **Epoch** | One pass through entire dataset | Training metric |
| **Batch** | Subset of data processed together | Training efficiency |
| **Learning Rate** | Step size for weight updates | Hyperparameter |
| **Gradient Descent** | Algorithm that minimizes loss | Optimization |
| **Backpropagation** | Compute gradients through network | Implementation |
| **Loss Function** | Measures prediction error | Training objective |
| **Overfitting** | Model memorizes training data | Problem to avoid |
| **Regularization** | Penalize complex models | Prevent overfitting |
| **Transfer Learning** | Use pre-trained model as base | Most NLP tasks |
| **Domain Adaptation** | Adjust model for new domain | Fine-tuning use case |
| **Few-shot Learning** | Learn from few examples | Prompt tuning |
| **Zero-shot Learning** | Generalize to unseen tasks | Pre-trained models |
| **Evaluation Metric** | Measure model performance | Progress tracking |
| **Validation Set** | Data for hyperparameter tuning | Model selection |
| **Test Set** | Final held-out evaluation | Report results |

---

## Part 10: Common Pitfalls and Solutions

| Pitfall | Symptom | Solution |
|---------|---------|----------|
| **Overfitting** | High train acc, low test acc | Reduce data, add regularization, early stopping |
| **Underfitting** | Low train & test accuracy | Larger model, more data, longer training |
| **Poor hyperparameters** | Unstable training curves | Grid search, learning rate warmup, gradient clipping |
| **Data quality** | Model learns incorrect patterns | Clean data, check labels, remove outliers |
| **Distribution shift** | Good on train, bad on test | Use validation set, test on real distribution |
| **Catastrophic forgetting** | Fine-tuning destroys pre-training | Use LoRA, lower learning rate, small batch size |
| **Mode collapse (RL)** | Generates same response repeatedly | Entropy bonus, KL penalty, diverse rewards |
| **Reward gaming (RLHF)** | Model exploits reward model | Robust reward model, constitution constraints |
| **Slow convergence** | Training takes forever | Higher learning rate, batch size, better init |
| **Memory issues** | Out of memory during training | Smaller batch, LoRA/QLoRA, gradient checkpointing |

---

## Part 11: Additional Advanced Techniques

### 11.1 Knowledge Distillation (KD)

**What It Is**: Train a small "student" model to mimic a large "teacher" model.

**How It Works**:
```
Teacher Model (Large, Slow)
         ↓
    Soft Targets (probability distributions)
         ↓
Student Model (Small, Fast)
         ↓
    Train to match teacher's outputs
```

**Key Idea**: Instead of learning from hard targets (one-hot labels), student learns from soft targets (probability distribution from teacher).

**Formula**:
```
Loss = α · CrossEntropy(student, hard_labels)
     + (1-α) · KL_Divergence(student_probs, teacher_probs)

Temperature T softens probabilities:
  p_soft = softmax(logits / T)
  Higher T → softer, more information-rich targets
```

**Use Cases**:
- Deploy large models on edge devices
- Reduce inference latency
- Compress models without losing much accuracy

**Example**:
```
Teacher: GPT-3 (175B parameters, 10s inference)
Student: GPT-2 (1.5B parameters, 100ms inference)

Teacher accuracy: 92% on benchmark
Student (naive): 45% on benchmark
Student (distilled): 87% on benchmark

Trade-off: 5% accuracy loss, 100x speedup
```

**Strengths**:
- Model compression
- Fast inference
- Maintained performance

**Weaknesses**:
- Requires teacher model
- Can only match teacher (can't exceed)

---

### 11.2 In-Context Learning (ICL) / Few-Shot Learning

**What It Is**: Model learns to solve tasks from examples in the prompt itself (no training).

**How It Works**:
```
Prompt Structure:
  Example 1: Input → Output
  Example 2: Input → Output
  Example 3: Input → Output
  New Task: Input → [Model generates output]

No training updates; model uses context to understand task
```

**Key Insight**: Transformer attention mechanisms can "learn" task patterns from examples.

**Types**:
- **Zero-Shot**: No examples, direct instruction
- **Few-Shot**: 1-5 examples
- **One-Shot**: Single example
- **Chain-of-Thought**: Examples with reasoning steps

**Example**:
```
Zero-shot:
  "Translate to French: Hello" → "Bonjour"

Few-shot:
  "Translate to French:
   - Hello → Bonjour
   - Goodbye → Au revoir
   - Thank you → Merci
   New: Please → ?"
  → "S'il vous plaît"

Chain-of-thought:
  "Q: 5 + 3 × 2 = ?
   A: First, multiply: 3 × 2 = 6. Then add: 5 + 6 = 11.

   Q: 7 + 4 × 2 = ?
   A: [Model follows same reasoning pattern]"
```

**Strengths**:
- Zero training cost
- Immediate adaptation
- No fine-tuning needed
- Task agnostic

**Weaknesses**:
- Limited by context window
- Accuracy lower than fine-tuned models
- Examples matter a lot (prompt engineering)

**Why It Works** (Mechanistic Understanding):
- Transformers contain "meta-learners" that recognize task patterns
- Attention reads examples, maps patterns to test input
- This happens naturally during forward pass

---

### 11.3 Prompt Engineering & Optimization

**What It Is**: Carefully design prompts to elicit better model responses without training.

**Techniques**:

#### 11.3.1 Chain-of-Thought (CoT)
```
Without CoT:
  Q: "What is 3 × 4 + 2?"
  A: "14" (model guesses)

With CoT:
  Q: "What is 3 × 4 + 2? Think step by step."
  A: "3 × 4 = 12. 12 + 2 = 14. Answer: 14"

Result: ~50% improvement on math reasoning
```

#### 11.3.2 Self-Consistency
```
Generate multiple reasoning paths (temperature > 0)
Take majority vote on final answer

Path 1: ... → Answer A
Path 2: ... → Answer A
Path 3: ... → Answer B
Path 4: ... → Answer A

Final: A (3/4 votes)
```

#### 11.3.3 Tree-of-Thought (ToT)
```
Explore multiple reasoning branches
Evaluate each branch
Prune low-scoring branches
Continue high-scoring branches

Like search tree for problem-solving
```

#### 11.3.4 Role-Based Prompting
```
"You are an expert Python programmer..."
"You are a medical doctor with 20 years experience..."
"You are a creative writer..."

Same model behaves differently based on role
```

#### 11.3.5 Structured Prompts
```
Input:
  Context: [background]
  Task: [specific instruction]
  Examples: [format examples]
  Output Format: [specify JSON/XML/etc]

Better structure → more consistent outputs
```

**Use Cases**:
- Improve accuracy without training
- Task-specific adaptation
- Reduce hallucinations
- Structured outputs

---

### 11.4 Mixture of Experts (MoE)

**What It Is**: Model with many "expert" sub-networks; router selects relevant experts per input.

**Architecture**:
```
Input
  ↓
Router Network
  ↓
┌─────────┬─────────┬─────────┬─────────┐
│Expert 1 │Expert 2 │Expert 3 │Expert 4 │
│(Math)   │(Code)   │(Text)   │(Logic)  │
└─────────┴─────────┴─────────┴─────────┘
  ↓         ↓         ↓         ↓
Weighted Combination (router chooses which experts)
  ↓
Output
```

**Key Idea**:
- Typically only 2-3 experts active per input (sparse)
- Different experts specialize in different domains
- Router learns to route inputs to appropriate experts

**Use Cases**:
- Scaling to very large models (more experts = more capacity, but sparse activation)
- Multi-domain models
- Conditional computation (save compute)

**Example**:
```
Input: "def fibonacci(n):"  (code)
Router: Route to Code Expert (90% weight), Logic Expert (10%)
Unused: Math Expert, Text Expert (0% weight, no computation)
Result: Generate code efficiently
```

**Strengths**:
- Scale to 100B+ parameters with sparse activation
- Multi-domain specialization
- Compute efficient

**Weaknesses**:
- Load balancing (some experts overused)
- Training instability
- Routing decisions not interpretable

---

### 11.5 Federated Learning

**What It Is**: Train model on decentralized data without collecting data to central server.

**How It Works**:
```
Device 1: Local Model → Train on local data → Gradient
Device 2: Local Model → Train on local data → Gradient
Device 3: Local Model → Train on local data → Gradient
           ↓
      Aggregate Gradients (Server)
           ↓
      Update Global Model
           ↓
      Send to devices
      ↓ (repeat)
```

**Key Concept**:
- Data stays on device
- Only gradients/updates sent to server
- Privacy-preserving

**Use Cases**:
- Mobile device learning
- Healthcare (data privacy)
- Keyboard predictions (Gboard)
- Corporate networks

**Strengths**:
- Privacy-preserving
- Decentralized
- Works with sensitive data

**Weaknesses**:
- Communication overhead
- Slower convergence
- Complex implementation

---

### 11.6 Continual Learning / Lifelong Learning

**What It Is**: Learn new tasks sequentially without forgetting previous tasks.

**Problem (Catastrophic Forgetting)**:
```
Train on Task 1: Accuracy = 95%
Train on Task 2: Task 1 accuracy drops to 30% (forgot!)
```

**Solutions**:

#### 11.6.1 Experience Replay
```
Task 1: Store examples in memory buffer
Task 2: Train on Task 2 + randomly sampled Task 1 examples
Result: Remember both tasks
```

#### 11.6.2 Elastic Weight Consolidation (EWC)
```
Task 1: Identify important weights (Fisher Information Matrix)
Task 2: When training on Task 2, penalize changes to important weights

Loss = Task2_Loss + λ · F · (w - w1)²
                           ↑ importance
```

#### 11.6.3 Dynamic Architectures
```
Task 1: Learn parameters p1
Task 2: Grow new parameters p2 (keep p1 frozen)
Task 3: Grow new parameters p3

Each task uses dedicated subset of parameters
```

**Use Cases**:
- Lifelong learning agents
- Multi-task systems
- Reducing data storage

---

### 11.7 Meta-Learning (Learning to Learn)

**What It Is**: Learn an algorithm that can quickly adapt to new tasks.

**Concept**:
```
Standard Learning:
  Task 1 → Train → Model 1
  Task 2 → Train → Model 2
  Task 3 → Train → Model 3

Meta-Learning:
  Task 1, 2, 3 → Meta-train → Meta-model

  New Task 4 → Few steps → Adapted Model 4
               (very fast)
```

**Common Approaches**:

#### 11.7.1 MAML (Model-Agnostic Meta-Learning)
```
Meta-train: For each task:
  1. Take gradient step on task
  2. Take gradient step on that gradient
  (Optimize for fast adaptation)

Meta-test: New task:
  1. One or few gradient steps → Good performance
```

**Result**: Model learns initializations and hyperparameters that adapt quickly.

#### 11.7.2 Prototypical Networks
```
Learn embedding space where:
- Examples of same class cluster together
- Examples of different classes are far apart

New task: Compare new example to class prototypes (centroids)
```

**Use Cases**:
- Few-shot learning
- Rapid task adaptation
- Cross-domain learning

---

### 11.8 Adversarial Training

**What It Is**: Train model to be robust against adversarial examples (inputs designed to fool the model).

**How It Works**:
```
Step 1: Generate adversarial example
  x_adv = x + ε · sign(∇_x Loss(model(x), y))
  (perturb input in direction that maximizes loss)

Step 2: Train on adversarial example
  Update model to correctly classify x_adv

Step 3: Repeat
```

**Use Cases**:
- Robustness
- Safety (security)
- Out-of-distribution generalization

**Example**:
```
Clean input: image of dog → Correctly classified
Adversarial: add tiny noise → Model outputs "cat"

Adversarial training: Learn to classify both correctly
```

**Strengths**:
- More robust models
- Better generalization

**Weaknesses**:
- Slower training
- Accuracy-robustness trade-off

---

### 11.9 Self-Supervised Learning

**What It Is**: Learn representations without labeled data by creating self-generated labels.

**Methods**:

#### 11.9.1 Contrastive Learning
```
Goal: Embeddings of similar items close, dissimilar items far

Loss = -log(exp(sim(x, x+) / τ) / Σ exp(sim(x, x-) / τ))
         ↑positive pair    ↑negative pairs

Example:
  x = image of dog
  x+ = augmented image of same dog (similar)
  x- = images of cats (dissimilar)

  Learn: embeddings where x and x+ are close
```

**Use Cases**:
- Pre-training without labels
- Few-shot learning
- Representation learning

#### 11.9.2 Masked Language Modeling (MLM)
```
Input: "The [MASK] is blue"
Predict: "The [sky] is blue"

Learn: Fill in masked tokens using context
(BERT uses this)
```

#### 11.9.3 Next Sentence Prediction
```
Given: Sentence A, Sentence B
Predict: IsNext? (A and B consecutive or random)

Learn: Sentence relationships and coherence
```

**Strengths**:
- No labeling cost
- Learns rich representations
- Transfer to downstream tasks

---

### 11.10 Curriculum Learning

**What It Is**: Train on easy examples first, gradually increase difficulty.

**Concept**:
```
Stage 1: Easy examples
  "1 + 1 = ?"
  "2 + 2 = ?"

Stage 2: Medium examples
  "5 + 8 = ?"
  "12 + 17 = ?"

Stage 3: Hard examples
  "345 + 782 = ?"
  "1000 + 9999 = ?"

Result: Faster convergence, better final performance
```

**Intuition**: Humans learn this way (kindergarten → university)

**Use Cases**:
- Machine translation
- Question answering
- Complex reasoning tasks

**Strengths**:
- Faster training
- Better generalization
- Avoids early local minima

---

### 11.11 Contrastive Learning & Similarity Learning

**Beyond standard contrastive learning; specialized variants**:

#### 11.11.1 SimCLR (Simple Contrastive Learning of Representations)
```
Augment image → Two views of same image
Learn: Views are similar
       Different images are dissimilar

Result: Good image representations from unlabeled data
```

#### 11.11.2 MoCo (Momentum Contrast)
```
Maintain momentum encoder (slowly updated copy)
Use momentum encoder's representations as negative pairs
More stable contrastive learning
```

---

### 11.12 Distillation Variants

#### 11.12.1 Dark Knowledge
```
Teacher model has "dark knowledge":
  - Similarities between classes in soft targets
  - Which classes are related (learned implicitly)

Student learns these relationships, not just classifications
```

#### 11.12.2 FitNet (Feature-based Distillation)
```
Match not just outputs, but intermediate layer features
Student learns feature representations matching teacher
More expressive distillation
```

#### 11.12.3 Attention Transfer
```
Teacher: Attention maps at each layer
Student: Learn to produce similar attention maps

Benefit: Transfer attention patterns, not just outputs
```

---

### 11.13 Data Augmentation

**What It Is**: Create synthetic training examples to improve robustness and prevent overfitting.

**Methods**:

#### 11.13.1 Traditional Augmentation (Text)
```
Original: "The movie was great"

Back-translation: EN→FR→EN = "The film was great"
Paraphrase: "I loved the movie"
Token replacement: "The film was excellent"
Generative: "This film was excellent"
```

#### 11.13.2 Mixup / CutMix (Images)
```
Blend two examples:
  x_mixed = λ · x1 + (1-λ) · x2
  y_mixed = λ · y1 + (1-λ) · y2

Train on mixed examples
Smoothes decision boundaries
```

#### 11.13.3 Generative Augmentation
```
Train generative model (VAE, GAN) on limited data
Generate synthetic examples
Train classifier on synthetic + real data
```

**Use Cases**:
- Small datasets
- Robustness
- Domain generalization

---

### 11.14 Transfer Learning

**What It Is**: Use knowledge from pre-trained model on new task.

**Levels of Transfer**:

#### 11.14.1 Feature Extraction (Frozen Weights)
```
Pre-trained Model (frozen)
        ↓
    Feature Extractor
        ↓
    Task-Specific Classifier (train only this)
        ↓
    Output

Cost: Very low, fast training
```

#### 11.14.2 Fine-Tuning (Unfreeze Top Layers)
```
Pre-trained Model
        ↓
    Frozen Layers (preserve pre-training)
        ↓
    Unfrozen Top Layers (train on task)
        ↓
    Output

Cost: Medium, balanced
```

#### 11.14.3 Domain Adaptation
```
Source Domain: ImageNet (pre-trained)
Target Domain: Medical images
Method: Fine-tune on target domain with small learning rate
```

**Use Cases**:
- When target task has limited data
- Cross-domain learning
- Cost-effective training

---

### 11.15 Noise Contrastive Estimation (NCE)

**What It Is**: Approximate softmax with simpler binary classification.

**Problem**: Softmax over vocabulary is expensive (|V| = 50k-100k)

**Solution**: Approximate with binary classification
```
Instead of: P(y | x) = exp(w_y · x) / Σ_i exp(w_i · x)

Use: P(y=correct) = sigmoid(w_y · x)
     vs
     P(y=wrong) = sigmoid(-w_wrong · x)

Train as binary classification on correct vs. sampled negatives
Result: ~100x speedup
```

**Use Cases**:
- Language modeling with large vocabulary
- Efficient training

---

### 11.16 Layer Normalization & Batch Normalization as Learning Techniques

**Batch Normalization (BN)**:
```
Normalize activations per batch
Reduce internal covariate shift
Allows higher learning rates
Acts as regularization
```

**Layer Normalization (LN)**:
```
Normalize per sample/layer (not per batch)
More stable than BN
Better for Transformers
```

**Use Cases**:
- Stabilize training
- Faster convergence
- Better generalization

---

### 11.17 Gradient Accumulation & Mixed Precision

**Gradient Accumulation**:
```
Standard:
  Batch size = 32, update every step

Gradient Accumulation:
  Effective batch size = 32 × 8 = 256
  Compute gradients on 32, accumulate 8 steps

Benefit: Train with large batch sizes on limited memory
```

**Mixed Precision**:
```
Float32: Store weights in float32 (full precision)
Float16: Compute forward/backward in float16 (half precision)

Benefit: 2x speedup, half memory, same accuracy
```

---

### 11.18 Optimization & Scheduler Techniques

**Optimizers** (update rules):

#### 11.18.1 SGD (Stochastic Gradient Descent)
```
w = w - lr · ∇Loss
Simple, slow convergence
```

#### 11.18.2 Momentum
```
v = β · v + ∇Loss
w = w - lr · v
Accelerates in consistent direction
```

#### 11.18.3 Adam (Adaptive Moment Estimation)
```
m = β1 · m + (1-β1) · ∇Loss
v = β2 · v + (1-β2) · (∇Loss)²
w = w - lr · m / (√v + ε)

Combines momentum + adaptive learning rates per parameter
Most common for LLMs
```

#### 11.18.4 AdamW (Adam Weight Decay)
```
Decoupled weight decay from gradient update
Better generalization than L2 regularization
Standard for modern LLMs
```

**Learning Rate Schedulers**:

#### 11.18.5 Linear Warmup + Cosine Decay
```
Learning Rate
      │
      │    ╱─────────────╲
      │   ╱               ╲
      │  ╱                 ╲
      │ ╱                   ╲___
      └─────────────────────────→ Step

Warmup: Gradually increase LR (0 → peak)
Decay: Cosine decrease (peak → 0)

Benefit: Stable training + fine-tuning at end
```

---

### 11.19 Regularization Techniques

#### 11.19.1 Dropout
```
During training: Randomly disable units (probability p)
During inference: Use all units

Effect: Prevents co-adaptation, reduces overfitting
```

#### 11.19.2 L1/L2 Regularization
```
L1: Loss += λ · Σ|w|  (sparse weights)
L2: Loss += λ · Σ w²  (small weights)
```

#### 11.19.3 Weight Decay
```
w = w · (1 - decay_rate)
Penalizes large weights
Similar to L2 but decoupled
```

#### 11.19.4 Label Smoothing
```
Hard labels: [1, 0, 0]
Soft labels: [0.9, 0.05, 0.05]

Effect: Prevents overconfidence
```

---

### 11.20 Inference-Time Optimization

#### 11.20.1 Quantization at Inference
```
Store weights in lower precision:
  float32 (4 bytes) → int8 (1 byte) = 4x smaller

Inference: 4x faster, 4x less memory
Training: Full precision maintained
```

#### 11.20.2 Pruning
```
Remove weights below threshold
Reduce model size without retraining
Or prune then fine-tune
```

#### 11.20.3 Speculative Decoding
```
Draft Model: Quickly generate N tokens
Verification: Check if main model agrees
Accept: If yes, continue from draft
Reject: Regenerate with main model

Benefit: 2-3x speedup with same quality
```

#### 11.20.4 Caching & KV-Cache
```
Attention mechanism:
  Compute Q, K, V for each token

Optimization:
  Cache K, V from previous tokens
  Only compute for new token

Benefit: ~2x speedup in generation
```

---

## Part 12: Future Trends

### Emerging Techniques

1. **Mixture of Experts (MoE) Fine-tuning**
   - Different adapters for different tasks
   - Route to relevant expert for each input
   - Sparse activation (efficient)

2. **Federated Learning**
   - Train on decentralized data
   - Privacy-preserving
   - Combine gradients from multiple sources

3. **Continual Learning**
   - Learn new tasks without forgetting old ones
   - Memory replay + regularization
   - Lifelong adaptation

4. **Reinforcement Learning from Environment**
   - Learn from real-world interaction (robotics)
   - Not just human feedback
   - Closes sim-to-real gap

5. **Multi-Modal Learning**
   - Combine text, image, audio, video
   - Joint fine-tuning
   - Unified representations

6. **Knowledge Distillation**
   - Compress large model to small model
   - Student learns from teacher
   - Deployment efficiency

---

## Part 13: Complete Summary Tree

```
LLM Learning Techniques (Comprehensive)
│
├── FOUNDATIONAL LEARNING (Pre-training)
│   ├── Unsupervised Learning
│   │   ├── Language Modeling (next token prediction)
│   │   ├── Masked Language Modeling (MLM) - BERT
│   │   ├── Next Sentence Prediction
│   │   └── Causal Language Modeling
│   │
│   └── Self-Supervised Learning
│       ├── Contrastive Learning
│       │   ├── SimCLR
│       │   ├── MoCo (Momentum Contrast)
│       │   └── General contrastive loss
│       ├── Noise Contrastive Estimation (NCE)
│       └── Autoregressive Modeling
│
├── SUPERVISED FINE-TUNING (Task Adaptation)
│   ├── Full Fine-tuning
│   │   └── Update all parameters
│   │
│   └── Parameter-Efficient Fine-tuning (PEFT)
│       ├── LoRA (Low-Rank Adaptation) - 1-2% params
│       ├── QLoRA (Quantized LoRA) - LoRA + quantization
│       ├── Adapters - 0.5% params, inserted modules
│       ├── Prefix Tuning - Learnable prefix only
│       ├── Prompt Tuning - Soft prompts (embeddings)
│       └── BitFit - Bias parameters only
│
├── PREFERENCE & ALIGNMENT LEARNING
│   ├── Reinforcement Learning from Human Feedback (RLHF)
│   │   └── 3-stage: SFT → Reward Model → RL (PPO)
│   │
│   ├── Direct Preference Optimization (DPO)
│   │   └── Learn preferences directly (no separate RM)
│   │
│   ├── Iterative Preference Optimization (IPO)
│   │   └── Multi-pass DPO with refinement
│   │
│   ├── Reward-Augmented Fine-Tuning (RAFT)
│   │   └── Combine SFT + reward signals
│   │
│   └── Constitutional AI
│       └── Self-critique against principles
│
├── REINFORCEMENT LEARNING (Reward Optimization)
│   ├── Policy-Based Methods
│   │   ├── Policy Gradient
│   │   ├── Proximal Policy Optimization (PPO)
│   │   ├── Trust Region Policy Optimization (TRPO)
│   │   └── Actor-Critic Methods
│   │
│   ├── Value-Based Methods
│   │   ├── Q-Learning
│   │   ├── Deep Q-Network (DQN)
│   │   └── Temporal Difference Learning
│   │
│   └── Experience Replay (Improve Stability)
│       ├── Standard Experience Replay
│       ├── Prioritized Experience Replay
│       └── Hindsight Experience Replay (HER)
│
├── PROMPT-BASED LEARNING (No Training)
│   ├── In-Context Learning (ICL)
│   │   ├── Zero-shot prompting
│   │   ├── Few-shot prompting (1-5 examples)
│   │   └── One-shot prompting
│   │
│   └── Prompt Engineering & Optimization
│       ├── Chain-of-Thought (CoT)
│       ├── Self-Consistency
│       ├── Tree-of-Thought (ToT)
│       ├── Role-Based Prompting
│       └── Structured Prompting
│
├── TEST-TIME & INFERENCE OPTIMIZATION
│   ├── Generation-Time Methods
│   │   ├── Test-Time Augmentation (TAO)
│   │   ├── Self-Critique & Revision
│   │   └── Ensemble Voting
│   │
│   ├── Inference Acceleration
│   │   ├── Quantization (int8, int4)
│   │   ├── Speculative Decoding
│   │   ├── KV-Cache Optimization
│   │   └── Pruning
│   │
│   └── Distillation (Knowledge Transfer)
│       ├── Knowledge Distillation (KD)
│       ├── Dark Knowledge
│       ├── FitNet (Feature-based)
│       └── Attention Transfer
│
├── ADVANCED TRAINING TECHNIQUES
│   ├── Data & Augmentation
│   │   ├── Data Augmentation (back-translation, paraphrase)
│   │   ├── Mixup / CutMix
│   │   ├── Generative Augmentation
│   │   └── Curriculum Learning (easy→hard)
│   │
│   ├── Multi-Task Learning
│   │   ├── Mixture of Experts (MoE)
│   │   │   └── Sparse routing to expert sub-networks
│   │   ├── Hard Parameter Sharing
│   │   ├── Soft Parameter Sharing
│   │   └── Multi-task routing
│   │
│   ├── Continual / Lifelong Learning
│   │   ├── Experience Replay (memory buffer)
│   │   ├── Elastic Weight Consolidation (EWC)
│   │   └── Dynamic Architectures
│   │
│   ├── Meta-Learning (Learning to Learn)
│   │   ├── MAML (Model-Agnostic Meta-Learning)
│   │   ├── Prototypical Networks
│   │   └── Matching Networks
│   │
│   └── Robustness Training
│       ├── Adversarial Training
│       └── Domain Randomization
│
├── REPRESENTATION LEARNING
│   ├── Similarity Learning
│   │   ├── Metric Learning
│   │   ├── Siamese Networks
│   │   └── Triplet Loss
│   │
│   └── Transfer Learning
│       ├── Feature Extraction (frozen weights)
│       ├── Fine-tuning (unfreeze top layers)
│       └── Domain Adaptation
│
├── DISTRIBUTED & PRIVACY LEARNING
│   ├── Federated Learning
│   │   └── Decentralized training on edge devices
│   │
│   └── Differential Privacy
│       └── Privacy-preserving gradient updates
│
├── TRAINING INFRASTRUCTURE
│   ├── Optimization Algorithms
│   │   ├── SGD (Stochastic Gradient Descent)
│   │   ├── Momentum
│   │   ├── Adam (Adaptive Moment Estimation)
│   │   └── AdamW (Adam + Weight Decay)
│   │
│   ├── Learning Rate Scheduling
│   │   ├── Linear Warmup + Cosine Decay
│   │   ├── Constant learning rate
│   │   ├── Step decay
│   │   └── Exponential decay
│   │
│   ├── Regularization
│   │   ├── Dropout
│   │   ├── L1/L2 Regularization
│   │   ├── Weight Decay
│   │   └── Label Smoothing
│   │
│   ├── Normalization
│   │   ├── Batch Normalization (BN)
│   │   ├── Layer Normalization (LN)
│   │   ├── Group Normalization
│   │   └── Instance Normalization
│   │
│   └── Training Efficiency
│       ├── Gradient Accumulation
│       ├── Mixed Precision Training
│       ├── Gradient Checkpointing
│       └── Flash Attention
│
└── EMERGING & FUTURE TECHNIQUES
    ├── Reinforcement Learning from Environment
    │   └── Real-world interaction (robotics, games)
    │
    ├── Multi-Modal Learning
    │   └── Joint text, image, audio, video training
    │
    ├── Retrieval-Augmented Generation (RAG)
    │   └── Combine with external knowledge
    │
    └── Neurosymbolic Learning
        └── Combine neural + symbolic reasoning
```

---

## Part 14: Comprehensive Technique Inventory

### By Stage of Learning Pipeline

**Pre-training Stage**:
- Language Modeling (unsupervised RL)
- Masked Language Modeling
- Contrastive Learning
- Self-Supervised Learning methods

**Fine-tuning Stage**:
- Supervised Fine-Tuning (SFT)
- Parameter-Efficient Fine-Tuning (PEFT): LoRA, QLoRA, Adapters, etc.
- Multi-task learning with MoE
- Curriculum learning
- Transfer learning

**Alignment Stage**:
- RLHF
- DPO
- Constitutional AI
- Adversarial training for robustness

**Deployment Stage**:
- Knowledge Distillation
- Quantization
- Pruning
- Speculative Decoding
- Prompt optimization

**Continuous Learning Stage**:
- Continual learning
- Federated learning
- Online learning

---

## Part 15: Technique Selection Matrix

```
Goal                          → Best Techniques
─────────────────────────────────────────────────────
Maximize accuracy             → Full Fine-tuning, RLHF, Ensemble
Fast training                 → LoRA, DPO, Prompt Tuning
Limited hardware              → QLoRA, BitFit, Knowledge Distillation
Multi-task                    → MoE, Adapters, LoRA per task
No training budget            → In-Context Learning, Prompt Engineering
Privacy-preserving            → Federated Learning, Differential Privacy
Robustness                    → Adversarial Training, Data Augmentation
Few-shot learning             → Meta-Learning (MAML), Prototypical Networks
Lifelong learning             → Continual Learning, Experience Replay, EWC
Edge deployment               → Knowledge Distillation, Quantization, Pruning
Learning speed                → Curriculum Learning, Meta-Learning
Generalization                → Transfer Learning, Domain Adaptation
User preferences              → DPO, Constitutional AI, RAFT
Real-world interaction        → RL from environment
Semantic understanding        → Contrastive Learning, Masked LM
```

---

## Quick Decision Guide

**I want to...**

- **Adapt pre-trained model to new domain** → Use **LoRA** (best balance)
- **Maximize accuracy regardless of cost** → Use **Full Fine-tuning**
- **Train on limited hardware** → Use **QLoRA**
- **Align with human preferences** → Use **DPO** (fast) or **RLHF** (accurate)
- **Ensure safety/values** → Use **Constitutional AI**
- **Improve without retraining** → Use **TAO**
- **Multi-task learning** → Use **Adapters** or **LoRA per task**
- **Few-shot learning** → Use **Prompt Tuning**
- **Continuous improvement** → Use **DPO with Replay**

---

## References & Further Learning

**Key Papers**:
- RLHF: "Learning to Summarize from Human Feedback" (OpenAI, 2022)
- DPO: "Direct Preference Optimization" (Anthropic, 2023)
- LoRA: "LoRA: Low-Rank Adaptation" (Microsoft, 2021)
- QLoRA: "QLoRA: Efficient Fine-tuning" (UW, 2023)
- Constitutional AI: "Constitutional AI" (Anthropic, 2022)
- PPO: "Proximal Policy Optimization Algorithms" (OpenAI, 2017)

**Implementations**:
- HuggingFace Transformers (LoRA, full fine-tuning)
- TRL (RLHF, DPO implementations)
- Axolotl (LoRA/QLoRA training)
- Stanford Alpaca (instruction fine-tuning)

---

---

## Part 16: Additional Niche & Specialized Techniques

### 16.1 Retrieval-Augmented Generation (RAG)

**What It Is**: Combine LLM with external knowledge retrieval to ground outputs.

**How It Works**:
```
Query: "What is the capital of France?"
       ↓
   Retrieve: Search knowledge base/internet
       ↓
   Get: [Document 1, Document 2, ...]
       ↓
   Prompt: "Context: [Doc1, Doc2...] Question: capital of France?"
       ↓
   LLM: Generates answer based on context
       ↓
   Output: "Paris" (grounded in retrieved context)
```

**Use Cases**:
- Reduce hallucinations (ground in facts)
- Domain-specific QA
- Current events (LLM knowledge is outdated)
- Long-form knowledge (facts LLM doesn't memorize)

**Strengths**:
- Factually accurate
- Up-to-date information
- Explainable (shows sources)

**Weaknesses**:
- Slower (retrieval latency)
- Quality depends on retrieval
- May retrieve wrong documents

---

### 16.2 Chain-of-Thought (CoT) Distillation

**What It Is**: Distill reasoning chains from teacher model to student.

**How It Works**:
```
Teacher Model:
  Input: "5 + 3 × 2 = ?"
  Output: "First multiply: 3 × 2 = 6. Then add: 5 + 6 = 11. Answer: 11"

Student Learns: Both answer AND reasoning process
Result: Student can reason even on new problems
```

**vs Standard Distillation**:
```
Standard KD: Only learn final answer → Student can't reason
CoT KD:      Learn reasoning steps → Student can reason
```

---

### 16.3 Instruction Tuning

**What It Is**: Fine-tune on diverse instruction-response pairs.

**Format**:
```
Instruction: "Translate to French: Hello"
Response: "Bonjour"

Instruction: "Write a poem about cats"
Response: "Whiskers and paws..."

Instruction: "Solve 5+3"
Response: "5 + 3 = 8"

Result: Model learns to follow diverse instructions
```

**Characteristics**:
- Not task-specific (diverse instructions)
- Teaches general instruction-following
- Foundation for chat models

---

### 16.4 Mixture of Losses

**What It Is**: Combine multiple loss functions to optimize multiple objectives.

**Example**:
```
Loss = 0.5 * CrossEntropy(prediction, label)
     + 0.3 * KL_Divergence(model, teacher)
     + 0.2 * L2_Regularization(weights)

Optimize for accuracy + knowledge distillation + regularization
```

---

### 16.5 Noisy Labels Learning

**What It Is**: Learn effectively even when training labels are incorrect.

**Why It's Needed**:
- Real-world data has annotation errors
- Crowdsourced labels are noisy
- Cost to clean labels is high

**Techniques**:
- **Label Smoothing**: Convert hard [1,0,0] to soft [0.9, 0.05, 0.05]
- **Robust Loss**: Use loss functions less sensitive to outliers
- **Sample Reweighting**: Downweight examples with uncertain labels
- **Noise Modeling**: Learn noise distribution explicitly

---

### 16.6 Curriculum Learning with Hard Example Mining

**Extension of Standard Curriculum**:
```
Standard Curriculum: Easy → Medium → Hard

Advanced Curriculum:
  Easy examples (confidence > 0.9) → Standard training
  Medium examples (0.5 < confidence < 0.9) → Focused learning
  Hard examples (confidence < 0.5) → Hard example mining

Hard example mining: Deliberately choose examples model struggles with
```

---

### 16.7 Mutual Information Maximization

**What It Is**: Maximize information shared between representations.

**Formula**:
```
I(X; Y) = Σ P(x,y) log(P(x,y) / (P(x)P(y)))

Goal: Make representations X and Y as similar as possible
Application: Positive pairs should maximize mutual information
```

---

### 16.8 Metric Learning & Similarity-Based Training

**What It Is**: Learn distance metrics between examples.

**Methods**:

#### 16.8.1 Triplet Loss
```
Loss = max(0, sim(anchor, negative) - sim(anchor, positive) + margin)

Goal: positive closer to anchor than negative
```

#### 16.8.2 Contrastive Loss
```
Loss = ||embedding1 - embedding2||²  (if similar)
     OR max(0, margin - ||embedding1 - embedding2||)  (if dissimilar)
```

---

### 16.9 Active Learning

**What It Is**: Model selects which examples to label (not random sampling).

**Process**:
```
1. Train on labeled data
2. Predict on unlabeled data
3. Select examples where model is most uncertain
4. Human labels these uncertain examples
5. Add to labeled data
6. Repeat

Result: Label efficiently, focusing on informative examples
```

**Query Strategies**:
- **Uncertainty Sampling**: Label examples with lowest confidence
- **Query by Committee**: Multiple models vote; label if disagreed
- **Expected Model Change**: Label examples that most change model

---

### 16.10 Multi-Task Learning with Task Gating

**What It Is**: Learn multiple tasks with learned gating mechanisms.

**Architecture**:
```
Shared Encoder
       ↓
  [Gating Mechanism] ← Learns importance of shared vs task-specific
       ↓
  ┌─────┬─────┬─────┐
  │ T1  │ T2  │ T3  │
  │Head │Head │Head │
  └─────┴─────┴─────┘
```

**Benefit**: Dynamically balance task-specific vs shared learning

---

### 16.11 Focal Loss

**What It Is**: Weight hard examples more in loss function.

**Formula**:
```
Standard CrossEntropy: CE = -log(p_t)
Focal Loss:            FL = -α(1-p_t)^γ · log(p_t)
                           ↑                ↑
                        class weight    focus on hard examples

γ = 2 is common
When p_t is high (easy): (1-p_t)^2 ≈ 0 (downweight)
When p_t is low (hard): (1-p_t)^2 ≈ 1 (upweight)
```

**Use Cases**:
- Class imbalance
- Hard negative mining
- Focus on difficult examples

---

### 16.12 Bootstrapping & Self-Training

**What It Is**: Use model's own predictions as pseudo-labels.

**Process**:
```
Phase 1:
  Train on labeled data

Phase 2:
  Predict on unlabeled data

Phase 3:
  For high-confidence predictions, treat as labeled

Phase 4:
  Retrain on labeled + pseudo-labeled data

Result: Self-improve from unlabeled data
```

**Variants**:
- **Co-Training**: Two models label for each other
- **Self-Ensembling**: Ensemble of different model versions
- **Temporal Ensembling**: Average predictions over time

---

### 16.13 Sentence-Piece Tokenization with Learned Vocabularies

**Not a training technique, but relevant for learning**:
```
Standard: Use fixed vocabulary (50k words)
Learned: Learn which n-grams to include in vocabulary

Benefit: Better compression, handles rare words, domain-specific vocab
```

---

### 16.14 Entropy Regularization

**What It Is**: Penalize overly confident predictions.

**Formula**:
```
Loss = CrossEntropy + λ · Entropy(predictions)

Entropy(p) = -Σ p_i · log(p_i)

High entropy → Model is uncertain → Less penalized
Low entropy → Model is very confident → More penalized
```

**Benefit**: Prevent overconfidence, better calibration

---

### 16.15 Margin-Based Losses

**What It Is**: Enforce a margin between correct and incorrect predictions.

**Examples**:
- **Hinge Loss**: max(0, 1 - y·f(x))
- **Margin Loss**: max(0, margin - (score_correct - score_wrong))

**Benefit**: More robust than softmax, better generalization

---

### 16.16 Graph Neural Networks (GNNs) for Learning

**What It Is**: Use graph structure in data for training.

**Applications**:
- Knowledge graphs (entities and relations)
- Code graphs (function calls, imports)
- Social networks

**Methods**:
- Graph Convolutional Networks (GCN)
- Graph Attention Networks (GAT)
- Message Passing Neural Networks

---

### 16.17 Physics-Informed Neural Networks (PINNs)

**What It Is**: Incorporate physical constraints into training.

**How It Works**:
```
Standard Loss: ||predictions - ground_truth||²

PINN Loss: Standard Loss + λ · ||physical_constraints_violated||²

Benefit: Model must satisfy physical laws even if data doesn't explicitly show it
```

---

### 16.18 Prototypical Learning

**What It Is**: Learn class prototypes (cluster centers) for few-shot learning.

**Process**:
```
Phase 1: Learn embedding space
Phase 2: Compute class prototypes = mean embedding per class
Phase 3: For new example, find nearest prototype
```

---

### 16.19 Siamese Networks

**What It Is**: Two identical networks that learn to compare examples.

**Architecture**:
```
Input A → Shared Encoder → Embedding A
                             ↓
                        Similarity Function
                             ↓
Input B → Shared Encoder → Embedding B

Loss: Compare embeddings (should be similar/dissimilar based on label)
```

---

### 16.20 Temporal Dropout

**What It Is**: Dropout applied consistently across time steps (RNNs).

**Why It Helps**:
- Standard dropout: Random dropout at each step (inconsistent)
- Temporal dropout: Same dropout mask across all steps (consistent)
- Better for RNNs where consistency matters

---

### 16.21 Scheduled Sampling

**What It Is**: During training, gradually transition from teacher forcing to sampling.

**How It Works**:
```
Early training: Use ground truth tokens (teacher forcing)
Mid training:   Sometimes use ground truth, sometimes model's output
Late training:  Use model's own output (like inference)

Benefit: Model learns to recover from its own errors
```

---

### 16.22 Lookahead Optimizer

**What It Is**: Keep a "slow weights" copy that averages recent "fast weights".

**How It Works**:
```
Fast update: w_fast = w_fast - lr · ∇Loss (normal SGD)
Slow update: w_slow = w_slow + α · (w_fast - w_slow)

During inference: Use w_slow (more stable)
```

**Benefit**: Smoother convergence, more stable training

---

### 16.23 Layer-wise Coordinate Descent (LCC)

**What It Is**: Update layers one at a time (instead of all together).

**Why It Helps**:
- More stable training
- Better conditioning
- Faster convergence in some cases

---

### 16.24 Variational Autoencoder (VAE) Fine-tuning

**What It Is**: Train VAE to learn latent representations, then fine-tune decoder.

**How It Works**:
```
Phase 1: Train VAE
  Encoder: x → latent z
  Decoder: z → x

Phase 2: Fine-tune decoder for task
  z (from encoder) → Task-specific Decoder → Prediction
```

**Benefit**: Structured latent space for generation

---

### 16.25 Softmax Temperature Scaling

**What It Is**: Adjust prediction confidence by dividing logits by temperature.

**Formula**:
```
Standard: p = softmax(logits)
Temperature: p = softmax(logits / T)

T > 1: Softer probabilities (less confident)
T < 1: Sharper probabilities (more confident)
T = 1: No change
```

**Use Cases**:
- Knowledge distillation (high T for teacher)
- Ensemble diversity (high T for ensemble members)
- Calibration (tune T on validation set)

---

## Part 17: Complete Technique Reference by Use Case

### Use Case: "Improve accuracy on classification task with labeled data"
```
1. Start with: Supervised Fine-Tuning (SFT)
2. Add complexity: Curriculum Learning (easy → hard examples)
3. Robustness: Data Augmentation
4. Better convergence: Adjust learning rate schedule
5. Final push: Ensemble multiple models
6. Extreme accuracy: RLHF if you have preference labels
```

### Use Case: "Deploy model on edge device"
```
1. Distill: Knowledge Distillation (teacher → student)
2. Quantize: INT8 or INT4 quantization
3. Prune: Remove low-weight connections
4. Cache: KV-cache optimization
5. Speed: Speculative decoding
Result: 100x smaller, 10x faster, 95% accuracy
```

### Use Case: "Learn from limited labeled data"
```
1. Transfer Learning: Start from pre-trained model
2. Few-shot: In-Context Learning or Meta-Learning (MAML)
3. Augmentation: Data Augmentation
4. Self-training: Bootstrap with pseudo-labels
5. Regularization: Prevent overfitting
Result: Good performance with 10-100 examples
```

### Use Case: "Handle noisy real-world labels"
```
1. Label Smoothing: Reduce label confidence
2. Robust Loss: Use Focal Loss
3. Sample Reweighting: Downweight uncertain examples
4. Noise Modeling: Explicitly model noise
5. Clean Subset: Manually verify and label high-uncertainty examples
Result: 5-10% accuracy improvement despite noise
```

### Use Case: "Continuous learning from user feedback"
```
1. Start: Pre-trained model
2. Collect: User interactions + feedback
3. Learn: DPO or RAFT on feedback
4. Weekly: Retrain on accumulated feedback
5. Evaluate: A/B test new version
6. Deploy: If better than baseline
Result: 1-2% accuracy improvement per month
```

---

**Status**: Comprehensive reference covering 100+ LLM learning techniques
**Last Updated**: December 9, 2025
**Total Sections**: 17 major sections + 100+ techniques
**Purpose**: Ultimate quick reference guide for all LLM learning methods

