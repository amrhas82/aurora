#!/usr/bin/env python3
"""Performance benchmarks for complexity assessor.

Tests single prompt latency, long prompt latency, and throughput.
Requirements:
- Single prompt: <1ms target (~0.5ms expected)
- Long prompt (500+ chars): <5ms target (~2.5ms expected)
- Throughput: >1000/sec target (~2000/sec expected)
"""

import time
from statistics import mean, median, stdev

from aurora_soar.phases.assess import ComplexityAssessor


def benchmark_single_prompt():
    """Benchmark single short prompt latency."""
    assessor = ComplexityAssessor()
    prompt = "explain how the caching works"

    # Warmup
    for _ in range(10):
        assessor.assess(prompt)

    # Measure
    times = []
    for _ in range(1000):
        start = time.perf_counter()
        assessor.assess(prompt)
        end = time.perf_counter()
        times.append((end - start) * 1000)  # Convert to ms

    return {
        "mean": mean(times),
        "median": median(times),
        "min": min(times),
        "max": max(times),
        "stdev": stdev(times),
        "p95": sorted(times)[int(len(times) * 0.95)],
        "p99": sorted(times)[int(len(times) * 0.99)],
    }


def benchmark_long_prompt():
    """Benchmark long prompt (500+ chars) latency."""
    assessor = ComplexityAssessor()
    prompt = (
        """
    Implement a comprehensive user authentication system with the following requirements:
    1. Support for multiple authentication methods (OAuth, SAML, local credentials)
    2. Multi-factor authentication with SMS and TOTP support
    3. Session management with Redis-backed storage
    4. Rate limiting and brute force protection
    5. Audit logging for all authentication events
    6. Integration with existing user management API
    7. Support for both web and mobile clients
    8. Comprehensive unit and integration tests
    9. Documentation including API specs and deployment guide
    10. Performance optimization for high-concurrency scenarios
    """
        * 2
    )  # Double it to ensure 500+ chars

    assert len(prompt) > 500, f"Prompt length: {len(prompt)}"

    # Warmup
    for _ in range(10):
        assessor.assess(prompt)

    # Measure
    times = []
    for _ in range(500):
        start = time.perf_counter()
        assessor.assess(prompt)
        end = time.perf_counter()
        times.append((end - start) * 1000)  # Convert to ms

    return {
        "mean": mean(times),
        "median": median(times),
        "min": min(times),
        "max": max(times),
        "stdev": stdev(times),
        "p95": sorted(times)[int(len(times) * 0.95)],
        "p99": sorted(times)[int(len(times) * 0.99)],
        "prompt_length": len(prompt),
    }


def benchmark_throughput():
    """Benchmark throughput (prompts per second)."""
    assessor = ComplexityAssessor()
    prompts = [
        "what is python",
        "explain how the caching works",
        "implement user authentication with oauth",
        "fix the validation bug",
        "design a caching system for the api",
    ]

    # Warmup
    for _ in range(100):
        for prompt in prompts:
            assessor.assess(prompt)

    # Measure throughput over 2 seconds
    count = 0
    start = time.perf_counter()
    duration = 2.0  # seconds

    while (time.perf_counter() - start) < duration:
        for prompt in prompts:
            assessor.assess(prompt)
            count += 1

    elapsed = time.perf_counter() - start
    throughput = count / elapsed

    return {
        "total_prompts": count,
        "elapsed_seconds": elapsed,
        "prompts_per_second": throughput,
    }


def main():
    print("=" * 70)
    print("COMPLEXITY ASSESSOR PERFORMANCE BENCHMARKS")
    print("=" * 70)

    print("\n[1/3] Single Prompt Latency (target: <1ms)...")
    single_stats = benchmark_single_prompt()
    print(f"  Mean:   {single_stats['mean']:.3f} ms")
    print(f"  Median: {single_stats['median']:.3f} ms")
    print(f"  Min:    {single_stats['min']:.3f} ms")
    print(f"  Max:    {single_stats['max']:.3f} ms")
    print(f"  StdDev: {single_stats['stdev']:.3f} ms")
    print(f"  P95:    {single_stats['p95']:.3f} ms")
    print(f"  P99:    {single_stats['p99']:.3f} ms")

    if single_stats["p95"] < 1.0:
        print(f"  ✓ PASS: P95 latency {single_stats['p95']:.3f}ms < 1ms target")
    else:
        print(f"  ✗ FAIL: P95 latency {single_stats['p95']:.3f}ms > 1ms target")

    print(f"\n[2/3] Long Prompt Latency (target: <5ms, {single_stats['mean']:.1f}x longer)...")
    long_stats = benchmark_long_prompt()
    print(f"  Prompt length: {long_stats['prompt_length']} chars")
    print(f"  Mean:   {long_stats['mean']:.3f} ms")
    print(f"  Median: {long_stats['median']:.3f} ms")
    print(f"  Min:    {long_stats['min']:.3f} ms")
    print(f"  Max:    {long_stats['max']:.3f} ms")
    print(f"  StdDev: {long_stats['stdev']:.3f} ms")
    print(f"  P95:    {long_stats['p95']:.3f} ms")
    print(f"  P99:    {long_stats['p99']:.3f} ms")

    if long_stats["p95"] < 5.0:
        print(f"  ✓ PASS: P95 latency {long_stats['p95']:.3f}ms < 5ms target")
    else:
        print(f"  ✗ FAIL: P95 latency {long_stats['p95']:.3f}ms > 5ms target")

    print("\n[3/3] Throughput (target: >1000 prompts/sec)...")
    throughput_stats = benchmark_throughput()
    print(f"  Total prompts:  {throughput_stats['total_prompts']}")
    print(f"  Elapsed time:   {throughput_stats['elapsed_seconds']:.2f} seconds")
    print(f"  Throughput:     {throughput_stats['prompts_per_second']:.0f} prompts/sec")

    if throughput_stats["prompts_per_second"] > 1000:
        print(
            f"  ✓ PASS: Throughput {throughput_stats['prompts_per_second']:.0f} > 1000/sec target",
        )
    else:
        print(
            f"  ✗ FAIL: Throughput {throughput_stats['prompts_per_second']:.0f} < 1000/sec target",
        )

    print("\n" + "=" * 70)

    # Overall pass/fail
    all_pass = (
        single_stats["p95"] < 1.0
        and long_stats["p95"] < 5.0
        and throughput_stats["prompts_per_second"] > 1000
    )

    if all_pass:
        print("✓ ALL PERFORMANCE TARGETS MET")
        return 0
    print("✗ SOME PERFORMANCE TARGETS NOT MET")
    return 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
