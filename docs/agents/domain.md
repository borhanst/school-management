# Domain docs

This repo uses a single-context layout.

## Source of truth

- `CONTEXT.md` at repo root for domain language and definitions
- `docs/adr/` for architecture decisions

## Consumer rules

When proposing architecture changes:

1. Read `CONTEXT.md` first and use its domain vocabulary.
2. Read relevant ADRs in `docs/adr/` before suggesting changes.
3. If a proposal contradicts an ADR, call it out only when friction is severe enough to reopen the decision.
