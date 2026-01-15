#!/usr/bin/env python3
"""Benchmark different embedding models for performance vs. quality trade-offs.

Tests various sentence-transformer models to find optimal balance between
speed and semantic quality for code embeddings.

Usage:
    python benchmark_embedding_models.py
"""

import time
from pathlib import Path

import numpy as np


def benchmark_model(model_name: str, texts: list[str], batch_size: int = 32) -> dict:
    """Benchmark a single embedding model.

    Args:
        model_name: Hugging Face model identifier
        texts: List of texts to embed
        batch_size: Batch size for embedding

    Returns:
        Dictionary with timing and model info
    """
    try:
        from sentence_transformers import SentenceTransformer

        print(f"\nBenchmarking: {model_name}")

        # Load model
        load_start = time.perf_counter()
        model = SentenceTransformer(model_name)
        load_time = time.perf_counter() - load_start

        # Warm-up
        _ = model.encode(texts[:10], batch_size=batch_size, show_progress_bar=False)

        # Benchmark encoding
        encode_start = time.perf_counter()
        embeddings = model.encode(texts, batch_size=batch_size, show_progress_bar=False)
        encode_time = time.perf_counter() - encode_start

        # Calculate metrics
        num_texts = len(texts)
        throughput = num_texts / encode_time
        avg_per_text = (encode_time / num_texts) * 1000  # ms

        return {
            "model_name": model_name,
            "load_time_s": load_time,
            "encode_time_s": encode_time,
            "throughput_texts_per_sec": throughput,
            "avg_ms_per_text": avg_per_text,
            "embedding_dim": embeddings.shape[1],
            "num_texts": num_texts,
            "status": "success",
        }

    except Exception as e:
        return {
            "model_name": model_name,
            "status": "error",
            "error": str(e),
        }


def main():
    """Main benchmark runner."""
    # Sample code texts (realistic examples)
    texts = [
        "def calculate_total(items: list) -> float:\n    return sum(item.price for item in items)",
        "class UserRepository:\n    def find_by_email(self, email: str) -> User:\n        return self.db.query(User).filter_by(email=email).first()",
        "async def fetch_data(url: str) -> dict:\n    async with aiohttp.ClientSession() as session:\n        async with session.get(url) as response:\n            return await response.json()",
        "def authenticate_user(username: str, password: str) -> bool:\n    user = get_user(username)\n    return user and verify_password(password, user.password_hash)",
        "class TokenManager:\n    def create_token(self, user_id: int) -> str:\n        payload = {'user_id': user_id, 'exp': datetime.utcnow() + timedelta(hours=1)}\n        return jwt.encode(payload, self.secret_key)",
    ] * 20  # Repeat to get 100 texts

    # Models to benchmark (ordered by expected speed)
    models = [
        # Fastest (lightweight)
        "paraphrase-MiniLM-L3-v2",  # 128 dim, very fast
        "all-MiniLM-L12-v2",  # 384 dim, fast
        # Default
        "all-MiniLM-L6-v2",  # 384 dim, balanced
        # Higher quality (slower)
        "all-mpnet-base-v2",  # 768 dim, slower but better
        "paraphrase-mpnet-base-v2",  # 768 dim, high quality
    ]

    print("=" * 80)
    print("EMBEDDING MODEL BENCHMARK")
    print("=" * 80)
    print(f"\nTest dataset: {len(texts)} code snippets")
    print(f"Batch size: 32")

    results = []
    for model_name in models:
        result = benchmark_model(model_name, texts, batch_size=32)
        results.append(result)

        if result["status"] == "success":
            print(f"  Load time:    {result['load_time_s']:.2f}s")
            print(f"  Encode time:  {result['encode_time_s']:.2f}s")
            print(f"  Throughput:   {result['throughput_texts_per_sec']:.1f} texts/s")
            print(f"  Avg per text: {result['avg_ms_per_text']:.1f}ms")
            print(f"  Embedding:    {result['embedding_dim']} dimensions")
        else:
            print(f"  ERROR: {result['error']}")

    # Summary table
    print("\n" + "=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80)

    print(f"\n{'Model':<35} {'Dims':<6} {'Throughput':<12} {'Avg/Text':<10} {'vs Default':<10}")
    print("-" * 80)

    default_throughput = None
    for r in results:
        if r["status"] == "success":
            if "MiniLM-L6-v2" in r["model_name"]:
                default_throughput = r["throughput_texts_per_sec"]
            speedup = (
                f"{r['throughput_texts_per_sec'] / default_throughput:.1f}x"
                if default_throughput
                else "N/A"
            )
            print(
                f"{r['model_name']:<35} {r['embedding_dim']:<6} {r['throughput_texts_per_sec']:>8.1f}/s   {r['avg_ms_per_text']:>6.1f}ms   {speedup:<10}"
            )
        else:
            print(f"{r['model_name']:<35} ERROR")

    # Recommendations
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)

    fastest = max(
        [r for r in results if r["status"] == "success"],
        key=lambda x: x["throughput_texts_per_sec"],
    )
    print(f"\nFastest model: {fastest['model_name']}")
    print(f"  Throughput: {fastest['throughput_texts_per_sec']:.1f} texts/s")
    print(f"  Trade-off: Lower dimensionality ({fastest['embedding_dim']} dims)")

    print("\nFor production use:")
    print("  • Development/iteration: paraphrase-MiniLM-L3-v2 (fastest)")
    print("  • Default/balanced: all-MiniLM-L6-v2 (current)")
    print("  • High-quality search: all-mpnet-base-v2 (slower but better)")

    print("\nEstimated indexing time for 1000 chunks:")
    for r in results:
        if r["status"] == "success":
            est_time = (1000 * r["avg_ms_per_text"]) / 1000
            print(f"  {r['model_name']:<35} {est_time:>6.1f}s")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
