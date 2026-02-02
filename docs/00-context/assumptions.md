# Assumptions and Constraints

## Technical Assumptions

### Environment
- Python 3.10+ installed
- Git available for repository indexing
- At least one AI CLI tool installed (claude, cursor, aider, etc.)

### Performance
- Local SQLite sufficient for 10K+ code chunks
- BM25 + ACT-R retrieval adequate without ML features
- Background loading prevents startup delays

### Dependencies
- ML features (sentence-transformers) optional, not required
- Anthropic API key optional (only for LLM features)

## Architectural Decisions

### Why ACT-R Memory?
- Models human memory decay and strengthening
- Prioritizes frequently accessed code
- No ML infrastructure required for basic operation

### Why SOAR Pipeline?
- Systematic goal decomposition
- Clear phase boundaries for debugging
- Extensible for new reasoning patterns

### Why CLI-Agnostic?
- Users have tool preferences
- Tools evolve rapidly
- Single interface to multiple backends

## Known Limitations

1. **No IDE Integration** - CLI-only currently
2. **Single Machine** - No cloud sync
3. **Text-Based** - No image/diagram support
4. **English Only** - No i18n

## Open Questions

- Should we support remote/cloud memory sync?
- How to handle very large monorepos (100K+ files)?
- Should SOAR phases be configurable per-project?

## Risks

| Risk | Mitigation |
|------|------------|
| ML dependencies too large | Keep optional, CPU-only default |
| CLI tool APIs change | Abstraction layer in spawner |
| Performance degrades at scale | Lazy loading, incremental indexing |
