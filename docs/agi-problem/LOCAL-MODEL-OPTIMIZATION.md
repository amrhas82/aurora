# Local Model Optimization: Running Small Models Fast Without Learning

**Date**: December 10, 2025
**Question**: "Is there a way to compact local small models to fit and work fast on local machines without taking too long to respond? Does it make sense to use QLoRA even though no learning? Or what is the equivalent?"

**Direct Answer**: **Yes, multiple techniques exist. QLoRA for inference only (without learning) still makes sense, but there are better alternatives for pure inference.**

---

## The Situation

You want:
- ✅ Small model that fits in memory
- ✅ Fast inference (low latency)
- ✅ Works on local machine (CPU/laptop GPU)
- ❌ Not doing fine-tuning (so QLoRA learning isn't needed)

**Question**: Is QLoRA worth it if you're not training?

---

## Answer: It Depends

### If You're ONLY Doing Inference (No Training)

**Better alternatives than QLoRA**:
1. **Quantization-only** (simplest, fastest)
2. **Pruning** (removes weights)
3. **Distillation** (smaller student model)
4. **Mobile optimizations** (TensorRT, CoreML)

**QLoRA is designed for fine-tuning**, so using it for inference-only is suboptimal.

### If You Might Fine-tune Later

**Then QLoRA makes sense**:
- Quantize to int8 immediately
- Add LoRA adapters (even if unused)
- Can fine-tune whenever needed
- Zero switching cost

---

## Quick Comparison: Inference-Only Options

```
┌──────────────────────────────────────────────────────────────┐
│ Local Model Optimization (Inference Only)                    │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│ TECHNIQUE          SIZE    SPEED   ACCURACY  SETUP  COST    │
│ ─────────────────────────────────────────────────────────── │
│                                                              │
│ Quantization int8  75% ↓  +10%    99%       Easy   FREE    │
│ Quantization int4  50% ↓  +30%    97%       Easy   FREE    │
│ Pruning            30% ↓  +20%    96%       Med    FREE    │
│ Distillation       40% ↓  +40%    94%       Hard   $$$     │
│ QLoRA (no training)75% ↓  +10%    99%       Med    FREE    │
│ Flash Attention    100%   +20%    100%      Easy   FREE    │
│ KV-Cache optimize  100%   +30%    100%      Easy   FREE    │
│                                                              │
└──────────────────────────────────────────────────────────────┘

↓ = Size reduction
+ = Speed improvement
```

---

## 1. Quantization (Best for Inference-Only)

### What It Is
Convert model weights from float32 → int8 or int4

### How It Works
```
Original: 4 bytes per weight (float32)
int8:     1 byte per weight (4x smaller, 1% accuracy loss)
int4:     0.5 bytes per weight (8x smaller, 3% accuracy loss)
```

### Implementations

#### Option A: GGML/GGUF (Best for CPU)
```
Model: Llama 2 7B
Original: 14GB
GGML int8: 3.5GB ← Fits on laptop
GGML int4: 1.7GB ← Fits on phone!
Speed: CPU inference (slow but works)

Tools: llama.cpp, gpt4all, ollama
```

#### Option B: GPTQ (Better for GPU)
```
Model: Llama 2 7B
Original: 14GB
GPTQ int4: 3.5GB
Speed: Fast on GPU, runs on 8GB VRAM cards
Accuracy: 97-98% (better than standard quantization)

Tools: AutoGPTQ, ExLlamaV2
```

#### Option C: AWQ (Balanced)
```
Model: Llama 2 7B
Original: 14GB
AWQ int4: 3.5GB
Speed: Similar to GPTQ
Accuracy: 98-99% (higher than GPTQ)
Efficiency: Good on both CPU and GPU

Tools: AutoAWQ
```

### Speed Comparison
```
Llama 2 7B Inference Speed (generate 100 tokens):

Device: MacBook Pro (M2, 16GB RAM)
  ├─ Float32 (full): Can't fit
  ├─ Int8 GGML: 2 sec (slow but works!)
  └─ Int4 GGML: 1.5 sec (better)

Device: RTX 3090 (24GB VRAM)
  ├─ Float32: 0.3 sec
  ├─ GPTQ int4: 0.35 sec (same speed, 4x smaller!)
  └─ Int8: 0.32 sec

Device: RTX 4090 (24GB VRAM)
  ├─ Float32: 0.2 sec
  ├─ GPTQ int4: 0.2 sec (identical speed!)
  └─ Int8: 0.19 sec
```

---

## 2. Pruning (Remove Unneeded Weights)

### What It Is
Identify and remove weights below a threshold → smaller model

### How It Works
```
Step 1: Identify low-magnitude weights
  ├─ These contribute minimally to output
  └─ Example: 30% of weights below 0.01

Step 2: Set to zero
  ├─ Sparse matrix (many zeros)
  └─ Can compress sparse storage

Step 3: Compress
  ├─ Store only non-zero weights
  ├─ Use sparse tensor format
  └─ Result: 30-50% size reduction

Step 4: Fine-tune (optional)
  ├─ Model adapts to pruning
  ├─ Recover 1-2% accuracy loss
  └─ Or skip if no time
```

### Implementation
```
Original: GPT2 (1.5B params) = 6GB
Pruning at 50% sparsity: 3GB
Accuracy: 97% (3% loss, recoverable)

Tools:
  - PyTorch: torch.nn.utils.prune
  - TensorFlow: TensorFlow Model Optimization Toolkit
  - Huggingface: torch_pruning library
```

### When to Use
- Want maximum size reduction (30-50%)
- Have GPU for pruning (optional, slow on CPU)
- Slight accuracy loss acceptable
- Not doing fine-tuning

---

## 3. Distillation (Best Accuracy)

### What It Is
Train small "student" model to mimic large "teacher" model

### How It Works
```
Teacher (Large):  GPT2 (1.5B params)
Student (Small):  Tiny-GPT2 (300M params)
                  ↑ 5x smaller

Temperature scaling: Teacher outputs softened
Student learns:
  ├─ Final predictions
  ├─ Relationships between classes
  ├─ "Dark knowledge" patterns
  └─ Result: 95-98% of teacher quality

Speed: 5x faster than teacher
Size: 5x smaller (200MB)
```

### Implementation Time
```
Training time: 2-7 days on GPU
Best for: Pre-trained once, reuse many times
Cost: High setup, zero inference cost
```

### Example: Distill Llama 2 7B → 1B
```
Teacher:  Llama 2 7B (14GB)
Student:  Custom 1B model (2GB)
Accuracy: 92-94% of teacher (vs 85% naive smaller model)
Speed:    3x faster than teacher
Cost:     1 week training + 100GB tokens
```

---

## 4. Flash Attention (Speed Without Size)

### What It Is
Optimize attention computation (the slow part of transformers)

### How It Works
```
Standard Attention:
  1. Load Q, K, V into memory
  2. Compute attention scores
  3. Load to main memory
  4. Result: Multiple memory transfers (slow!)

Flash Attention:
  1. Block-wise computation
  2. Stay in fast cache as long as possible
  3. Minimal memory transfers
  4. Result: 2-4x speedup, same accuracy!
```

### Implementation
```
Installation:
  pip install flash-attn

Usage: Auto-enabled in many libraries
  - Huggingface transformers
  - LM Studio
  - Ollama (optional)

Benefit: No accuracy loss, 20-30% speed improvement
Catch: Only works on certain GPUs (A100, RTX 40xx, etc.)
```

---

## 5. KV-Cache Optimization (Inference Speed)

### What It Is
Cache Key and Value matrices from previous tokens

### How It Works
```
Generation (token-by-token):

Without KV-Cache:
  Token 1: Compute Q,K,V for all 1 tokens
  Token 2: Recompute Q,K,V for all 2 tokens ← Redundant!
  Token 3: Recompute Q,K,V for all 3 tokens ← Redundant!

  Cost: O(n²) computation

With KV-Cache:
  Token 1: Compute Q,K,V for 1 token, save K,V
  Token 2: Reuse saved K,V, compute only for new token
  Token 3: Reuse saved K,V, compute only for new token

  Cost: O(n) computation (linear!)
```

### Speed Improvement
```
Llama 2 7B (100 token generation):

Without KV-Cache: 2 seconds
With KV-Cache:    0.5 seconds ← 4x faster!

Memory trade-off: +200MB for cache (acceptable)
```

### Implementation
```
Good news: Most inference engines have this by default
  - ollama: enabled
  - llama.cpp: enabled
  - huggingface transformers: enabled
  - vLLM: enabled

Just use! No configuration needed.
```

---

## 6. QLoRA for Inference-Only (Not Recommended Alone)

### The Honest Truth

**Using QLoRA for inference without fine-tuning is like buying a sports car but only driving in the parking lot.**

#### What you get with QLoRA:
```
Quantization (int8): 4x smaller
LoRA adapters (unused): Extra files, no benefit

Result: Same as int8 quantization + complexity
```

#### What you should use instead:
```
Just use int8 quantization directly
  ├─ Same size (75% reduction)
  ├─ Same speed (10% faster)
  ├─ Same accuracy (99%)
  └─ Simpler setup (1 tool vs 2)
```

#### When QLoRA makes sense:
```
If you MIGHT fine-tune later:
  ├─ Pre-quantize to int8
  ├─ Add LoRA adapters
  ├─ Deploy as-is (inference-only)
  └─ When you fine-tune, they're ready

Cost: Minimal (just add LoRA files)
Benefit: Ready to train whenever
```

---

## Decision Tree: What to Use?

```
┌─ Do you need fine-tuning support? ─┐
│                                    │
├─ YES → Use QLoRA                  │
│   ├─ Inference: int8 quantization │
│   ├─ Later: Add fine-tuning       │
│   └─ Cost/setup: Medium           │
│                                    │
├─ NO → Use pure inference methods:  │
│  │                                 │
│  ├─ Want smallest size?            │
│  │  └─ Use int4 quantization       │
│  │     (50% reduction, 3% loss)    │
│  │                                 │
│  ├─ Want fastest speed?            │
│  │  └─ Use Flash Attention         │
│  │     (20% faster, free)          │
│  │                                 │
│  ├─ Want best accuracy?            │
│  │  └─ Use distillation            │
│  │     (5x smaller, 95% accuracy)  │
│  │                                 │
│  └─ Want balanced?                 │
│     └─ Use int8 + Flash Attn       │
│        (75% smaller, 10% faster,   │
│        99% accuracy)               │
│                                    │
└────────────────────────────────────┘
```

---

## Concrete Examples

### Example 1: Run Llama 2 7B on MacBook Pro (16GB)

**Goal**: Fast inference on local machine

**Solution**: GGML int4 quantization
```
Model: Llama 2 7B
Original size: 14GB
Quantized: 3.5GB ← Fits in memory!
Speed: 1-2 tokens/sec (acceptable for local)
Setup: 10 minutes

Tool: llama.cpp
  brew install llama.cpp
  llama-cpp-python install

Download: GGMLv3 int4 from huggingface
Usage: Load and inference

Cost: FREE
Accuracy: 97% of original
```

### Example 2: Run Multiple Models on 8GB GPU

**Goal**: Quick switching between models

**Solution**: GPTQ int4 quantization
```
Model options:
  1. Mistral 7B: 3.5GB (GPTQ int4)
  2. Neural-chat 7B: 3.5GB (GPTQ int4)
  3. Orca 7B: 3.5GB (GPTQ int4)

Total: ~10.5GB (fits with batching)
Speed: 0.3-0.5 tokens/sec on RTX 3060
Setup: 30 minutes (download 3 models)

Tool: ExLlamaV2 or vLLM
Cost: FREE
Accuracy: 98% of original
```

### Example 3: Deploy on Phone

**Goal**: Run AI locally on mobile

**Solution**: Distillation to 1B model
```
Large Teacher: Llama 2 7B
Small Student: Custom 1B model
Setup: 1 week training (expensive!)
Result:
  Size: 2GB quantized → 500MB int4
  Speed: 100-200 ms per token (mobile acceptable)
  Accuracy: 92% of teacher
Cost: High upfront, zero inference
```

---

## Speed Comparison: Local Inference

```
Device: MacBook Pro M2 (16GB)
Task: Generate 100 tokens

Model               Format    Size    Speed
────────────────────────────────────────────
Llama 2 7B         float32   Can't fit
Llama 2 7B         int8      3.5GB   2.0 sec
Llama 2 7B         int4      1.7GB   1.5 sec
Mistral 7B         int4      3.5GB   1.8 sec
Orca 7B            int4      3.5GB   2.1 sec
Phi 2.7B           int4      0.7GB   0.3 sec ← Fastest
Tiny Llama 1B      int4      0.3GB   0.2 sec ← Smallest

────────────────────────────────────────────
Device: RTX 3090 (24GB)
Llama 2 7B         float32   14GB    0.3 sec
Llama 2 7B         int8      3.5GB   0.32 sec
Llama 2 7B         int4      1.7GB   0.35 sec (almost same!)
```

---

## Best Practices for Local Inference

### 1. Choose Right Model Size
```
GPU Memory Available:
  ├─ <4GB:   Use 1B-3B models (int4)
  ├─ 4-8GB:  Use 3B-7B models (int4)
  ├─ 8-24GB: Use 7B-13B models (int8 or int4)
  └─ >24GB:  Use 13B+ models (int8 or float16)
```

### 2. Quantization Priority
```
1. int4 quantization (best size/speed trade-off)
2. int8 quantization (best accuracy preservation)
3. Both + Flash Attention (maximum performance)
```

### 3. Inference Engines
```
For CPU (MacBook, CPU-only):
  ├─ llama.cpp ← Best for performance
  ├─ gpt4all ← Easy UI
  └─ ollama ← Simple setup

For GPU (NVIDIA):
  ├─ vLLM ← Fast, feature-rich
  ├─ ExLlamaV2 ← Very fast
  └─ LocalLLM ← Easy UI

For mobile:
  ├─ NCNN ← Android
  ├─ CoreML ← iOS
  └─ TensorFlowLite ← Both
```

### 4. Temperature & Sampling
```
For speed: Use lower temperature (0.1-0.3)
  └─ Less variation → Faster convergence

For creativity: Use higher temperature (0.7-1.0)
  └─ More variation → Slower (more exploration)

Greedy sampling: Fastest
  └─ Always pick highest probability token
```

---

## Should You Use QLoRA Without Learning?

### Quick Answer: **No, unless you might train later**

### Detailed Answer:

**Don't use QLoRA if**:
- Pure inference-only
- Want simplest setup
- Don't plan to fine-tune

**Use QLoRA if**:
- Might fine-tune in future
- Want to be future-proof
- Setup complexity not an issue

---

## Summary Table

| Technique | Size ↓ | Speed ↑ | Accuracy | Setup | Cost | Learning |
|-----------|---------|---------|----------|-------|------|----------|
| **int8 Quant** | 75% | 10% | 99% | Easy | FREE | No |
| **int4 Quant** | 50% | 30% | 97% | Easy | FREE | No |
| **Pruning** | 40% | 20% | 96% | Medium | FREE | Optional |
| **Distillation** | 80% | 400% | 94% | Hard | $$$ | Yes |
| **Flash Attn** | 0% | 30% | 100% | Easy | FREE | No |
| **KV-Cache** | 0% | 300% | 100% | Auto | FREE | No |
| **QLoRA** | 75% | 10% | 99% | Medium | FREE | Yes |

---

## Final Recommendation for AURORA

For local deployment in Phase 1:
```
Recommendation: int4 quantization
  ├─ Use GGML/GPTQ int4
  ├─ Size: ~1.7-3.5GB per model
  ├─ Speed: 1-2 tokens/sec (good for local)
  ├─ Accuracy: 97-98% (acceptable)
  ├─ Cost: FREE
  └─ Future: Can add QLoRA adapters for Phase 4 learning

Alternative: QLoRA for Phase 4 readiness
  ├─ Deploy with int8 + LoRA now
  ├─ Same size/speed as int8
  ├─ Ready to fine-tune in Phase 4
  ├─ Cost: Minimal complexity increase
  └─ Benefit: Future-proof for learning
```

---

**Status**: Local model optimization strategies clarified
**Referenced in**: AURORA WS3 Deployment section
**File**: This document (LOCAL-MODEL-OPTIMIZATION.md)
