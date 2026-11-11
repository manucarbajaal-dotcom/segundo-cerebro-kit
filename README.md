# Segundo Cerebro Kit

Local-first, plain-Markdown continuity for humans and coding agents.

Keep decisions, verified work and next steps outside the chat. Resume a task with
a bounded context bundle, and find broken wiki links before they become missing
knowledge. One Python file, standard library only, no accounts or API keys.

**Status:** initial public release, 0.1.0. This is a reusable implementation of
patterns developed in a private working second brain. It does not contain that
vault or its history. No external adoption or download claims are made.

[Documentación en español](README.es.md) · [Protocol](PROTOCOL.md) · [Contributing](CONTRIBUTING.md)

See [the architecture](ARCHITECTURE.md) for how one source of truth, evidence-aware
handoffs and private/public separation work together across agent sessions.

## Quick start

Requires Python 3.10 or later. Clone or download this repository, then:

```sh
python brainkit.py --root examples index --pending
python brainkit.py --root examples context --topic documentation --max-chars 4000
python brainkit.py --root examples check
python -m unittest -v
```

To start your own vault, create an empty folder and run:

```sh
mkdir my-vault
python brainkit.py --root my-vault note "Document the parser" --author pedro --topic documentation
```

The `note` command creates a unique file in `notes/`. Fill its sections with
actual evidence. Create `wiki/` for durable knowledge and use Obsidian-style
links such as `[[architecture]]` or `[[wiki/architecture#Storage|storage]]`.

## Commands

| Command | What it does |
| --- | --- |
| `note TITLE --author NAME --topic TOPIC` | Creates a unique handoff without overwriting another session |
| `index --topic WORDS --pending --json` | Searches note text and paths, ignoring case and accents |
| `context --topic WORDS --limit 8 --max-chars 12000` | Prints complete pending notes within a character budget |
| `check --json` | Reports missing sections, invalid closure states and broken or ambiguous wikilinks |
| `release --allowlist FILE --output ZIP` | Exports approved files, scans common secret indicators, and includes a SHA-256 manifest |

Pass `--root PATH` **before** the command. `index` and `check` support JSON.
Exit codes: 0 for success, 1 for check findings, 2 for invalid arguments or I/O errors.
Dates in generated notes include the local timezone offset.

## Why this exists

Chat history is a poor task ledger. Separate sessions can lose context, confuse a
proposal with a decision, or mark work done without recording where it landed.
This kit gives a small, inspectable workflow:

1. A session writes a handoff with decisions, verification, limits and sources.
2. Another session reads matching pending notes before acting.
3. Durable findings move to the wiki; the handoff records that destination in `Resolution`.
4. The linter catches closures without a resolution and broken knowledge links.

The files work with any editor. Humans can paste context into any coding agent;
the kit has no dependency on an AI provider or proprietary integration.

## Share tools without sharing your memory

The same vault can contain reusable tools and private records. The release command
requires an explicit JSON file list: unlisted files and Git history are never included.
It rejects path escapes and symlinks, restricts file types, and blocks common API
keys, private keys, email addresses and private Windows user paths. Errors identify
the file and indicator without echoing a suspected secret.

```sh
python brainkit.py --root . release --allowlist public-files.json --output ../second-brain-public.zip
```

The archive includes a `RELEASE-MANIFEST.json` with byte sizes and SHA-256 hashes.
Identical inputs produce identical archive bytes. Existing archives are never
overwritten. Review the allowlist and file contents before sharing: scanning is
heuristic and cannot recognize every secret, customer record, or proprietary text.

## Boundaries

The tool reads local Markdown and prints it to stdout. It does not upload, run
note content, manage credentials, operate browsers, commit files or merge
concurrent edits. `note` creates handoffs; `release` creates an archive outside the
source folder. Other commands are read-only. Review output before sending it to a
third party. Hidden directories and symlink files are excluded from indexing.

The linter handles wiki targets, aliases and file-level heading suffixes. It
does not validate heading existence, standard Markdown links, embeds, or links
inside inline/fenced code. Ambiguous basenames are reported rather than guessed.
The context budget counts characters, not model tokens; notes too large for the
remaining budget are omitted whole and the output states how many were included.
Root-level `notes/*.md` is the supported handoff layout.

## License

MIT. Maintained by Pedro Carbajal. See [LICENSE](LICENSE).
