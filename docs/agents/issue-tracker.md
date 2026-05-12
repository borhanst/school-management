# Issue tracker

This repo tracks issues as local markdown files under `.scratch/`.

## Storage format

- Create one folder per initiative: `.scratch/<initiative>/`
- Create one issue file per slice: `.scratch/<initiative>/<id>-<slug>.md`
- Keep file names stable after creation; update status inside the file

## Required issue fields

Each issue file should include:

- Title
- Type (`AFK` or `HITL`)
- Status
- Labels (include `needs-triage` on creation)
- Blocked by
- What to build
- Acceptance criteria

## Workflow

1. New issues start with label `needs-triage`.
2. Triage updates labels using `docs/agents/triage-labels.md`.
3. Work executes in dependency order (blockers first).
4. Do not modify or close parent planning artifacts when creating slices.
