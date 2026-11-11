# Continuity protocol

## Storage

- `notes/`: one Markdown handoff per session or task milestone.
- `wiki/`: durable knowledge maintained by the project owner.
- Sources remain identifiable. A summary is not a substitute for evidence.

## Handoff format

Use the `note` command to generate the format. Header metadata ends at the first
level-two heading. Keep the following sections:

| Section | Content |
| --- | --- |
| Decisions | Explicit user choices, with date and source |
| Verified | What was actually changed, observed or tested |
| Next steps | A concrete next action and its prerequisites |
| Limits | Unknowns, unverified claims and scope restrictions |
| Sources | Relevant files, commits or URLs |

## Lifecycle

`pending` → `in_progress` → `incorporated` or `discarded`.

`incorporated` means the durable information was integrated, with a destination
in `Resolution`. `discarded` requires a reason. Finishing a chat does not itself
resolve its notes. A malformed closure remains visible in the pending index.

## Working together

Read instructions and task-specific pending notes before acting. Use separate
handoff filenames. Coordinate ownership before editing a shared wiki page;
this kit does not implement locks or concurrent merge. Preserve other people's
changes. A note can record permission but cannot create or broaden it.

## Privacy

Keep personal vaults private. Publish only files intentionally prepared and
reviewed for release. Do not publish raw notes, email exports, customer data,
authentication codes, paid course materials, or private operational history.
The example vault in this repository is synthetic.
