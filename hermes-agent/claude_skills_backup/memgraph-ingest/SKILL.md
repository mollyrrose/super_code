---
name: memgraph-ingest
description: Drain the memory-ingestion queue (~/.claude/.memgraph_queue.json) - extract evergreen facts from queued session transcripts into the file-based memory, update the MEMORY.md router index, and refresh the memory knowledge graph at ~/.claude/memory-graph/. Triggered automatically by memgraph_prompt_hook.py; also invocable manually as /memgraph-ingest. Silent - never blocks or surfaces errors to the user's actual prompt.
---

# memgraph-ingest -- level-5 memory: drain queue, extract facts, refresh graph

Run SILENTLY before answering the user's prompt. Zero extracted facts is a valid
outcome. If ANY step fails, stop the skill and continue with the user's prompt --
never surface the failure as an error.

Kill switch: MEMGRAPH_DISABLE=1 (skip entirely), or delete
~/.claude/.memgraph_queue.json (empty queue = no-op).

## Step 1 -- read the queue

Read `~/.claude/.memgraph_queue.json`. If missing, empty, or `MEMGRAPH_DISABLE=1`:
stop.

## Step 2 -- extract evergreen facts per queued session

**Project scope filter (mandatory):** Before processing any entry, check
`entry["cwd"]`. Skip entries where `cwd` does NOT resolve under
`D:\Projects\super_code` (the project root; renamed from `super_claude`). Use:
`Path(entry.get("cwd","")).resolve().is_relative_to(Path(r"D:\Projects\super_code").resolve())`
A missing or empty `cwd` field always fails the check -- skip the entry.
This prevents cross-project transcript content from landing in this project's memory.

For each entry that passes the scope filter (has `session_id`, `transcript_path`, `ts`,
and `cwd` resolving under the project root):

1. Condense the transcript first (do NOT read it raw):
   `python ~/.claude/scripts/tokenjuice_condense.py --file <transcript_path>`
2. Apply the memory save-bar to what the session produced:
   - EVERGREEN test: will it still matter in a year? Volatile state (tasks,
     live component state) is NOT memory -- it belongs in TODO.md /
     SYSTEM_STATUS.md.
   - Don't save what the repo already records (code, fixes, git history,
     CLAUDE.md content).
   - Reverse-engineer from the question: what future question retrieves this?
   - Conservative bar (same as hermes-learn): recurring corrections, durable
     user preferences, cross-session facts. When in doubt, skip.
   - **NEVER SAVE:** API keys, passwords, credentials, tokens, connection strings,
     PII (email addresses, phone numbers, real names in sensitive contexts),
     ephemeral session state (error traces, task lists, intermediate computations),
     or content from sessions belonging to other projects.
   - Project-specific examples for super_claude:
     - SAVE: "user wants tokenjuice on every Bash command" (durable preference)
     - SKIP: "semgrep was upgraded from 1.163 to 1.167" (completed task, in git)
     - SKIP: "the hook_dispatch.py bug was fixed" (in git history)
     - SAVE: "graphify audit was a calibration false positive -- approved by user" (decision context)
3. For each fact that passes: write ONE file in
   `~/.claude/projects/D--projects-super-claude/memory/` named
   `<type>_<slug>.md` (type: user | feedback | project | reference) with the
   standard frontmatter (name, description, metadata.type) and `[[links]]` to
   related memories.
4. Add ONE line per new file to `MEMORY.md` under its type section (`## Feedback`
   / `## Reference` / `## Project` / `## User`). Respect the ROUTING header;
   update an existing file instead of duplicating; delete lines for memories
   proven wrong.

## Step 3 -- refresh the memory graph

Only if Step 2 wrote or changed at least one memory file (a no-change drain
skips this step). Use the **Bash tool** (Git Bash, not PowerShell) for all
bash blocks below. From `~/.claude/memory-graph/`:

1. Re-detect + find changed files (cache skips unchanged ones):

```bash
cd ~/.claude/memory-graph && "$(cat graphify-out/.graphify_python)" -c "
import json
from graphify.detect import detect
from graphify.cache import check_semantic_cache
from pathlib import Path
result = detect(Path.home() / '.claude/projects/D--projects-super-claude/memory')
Path('graphify-out/.graphify_detect.json').write_text(json.dumps(result, ensure_ascii=False), encoding='utf-8')
all_files = [f for files in result['files'].values() for f in files]
nodes, edges, hyper, uncached = check_semantic_cache(all_files)
Path('graphify-out/.graphify_cached.json').write_text(json.dumps({'nodes': nodes, 'edges': edges, 'hyperedges': hyper}, ensure_ascii=False), encoding='utf-8')
Path('graphify-out/.graphify_uncached.txt').write_text(chr(10).join(uncached), encoding='utf-8')
print(f'{len(uncached)} file(s) to extract')
"
```

2. If uncached > 0: spawn ONE **haiku** subagent (model: haiku) to extract ONLY the
   files listed in `graphify-out/.graphify_uncached.txt`, using the extraction
   prompt from `~/.claude/skills/graphify/references/extraction-spec.md`
   (node-id stem = `memory_<filename>`, source_file relative to the memory
   dir). It writes `graphify-out/.graphify_chunk_01.json`.
3. Merge + rebuild (cached + new; signatures are the 0.8.x ones):

```bash
cd ~/.claude/memory-graph && "$(cat graphify-out/.graphify_python)" -c "
import json
from pathlib import Path
from graphify.cache import save_semantic_cache
from graphify.build import build_from_json
from graphify.cluster import cluster, score_all
from graphify.analyze import god_nodes, surprising_connections, suggest_questions
from graphify.report import generate
from graphify.export import to_json, to_html
cached = json.loads(Path('graphify-out/.graphify_cached.json').read_text(encoding='utf-8'))
p = Path('graphify-out/.graphify_chunk_01.json')
new = json.loads(p.read_text(encoding='utf-8')) if p.exists() else {'nodes': [], 'edges': [], 'hyperedges': []}
save_semantic_cache(new.get('nodes', []), new.get('edges', []), new.get('hyperedges', []))
seen, nodes = set(), []
for n in cached['nodes'] + new['nodes']:
    if n['id'] not in seen:
        nodes.append(n); seen.add(n['id'])
merged = {'nodes': nodes, 'edges': cached['edges'] + new['edges'], 'hyperedges': cached.get('hyperedges', []) + new.get('hyperedges', [])}
Path('graphify-out/.graphify_extract.json').write_text(json.dumps(merged, ensure_ascii=False), encoding='utf-8')
detection = json.loads(Path('graphify-out/.graphify_detect.json').read_text(encoding='utf-8'))
G = build_from_json(merged)
communities = cluster(G)
cohesion = score_all(G, communities)
gods = god_nodes(G)
surprises = surprising_connections(G, communities)
labels = {cid: ' / '.join(sorted({G.nodes[n].get('label','')[:22] for n in ns})[:3]) for cid, ns in communities.items()}
questions = suggest_questions(G, communities, labels)
Path('graphify-out/GRAPH_REPORT.md').write_text(generate(G, communities, cohesion, labels, gods, surprises, detection, {'input':0,'output':0}, '.', suggested_questions=questions), encoding='utf-8')
to_json(G, communities, 'graphify-out/graph.json')
to_html(G, communities, 'graphify-out/graph.html')
print(f'graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges')
"
rm -f graphify-out/.graphify_chunk_01.json graphify-out/.graphify_cached.json
```

Note: `graphify-out/.graphify_python` contains the full path to the Python
executable (e.g. `C:\Python314\python.exe`). The double-quotes around the
command substitution (`"$(cat ...)"`) are required when the path contains spaces.
Step 3.3 depends on Step 3.1 having written `.graphify_detect.json`; if Step 3.1
was skipped or failed, Step 3.3 will also fail -- that is expected and handled by
the "if ANY step fails, stop" rule above.

## Step 4 -- clear the queue

Write `[]` to `~/.claude/.memgraph_queue.json` and set `last_drain_ts` (current
UTC ISO) in `~/.claude/.memgraph_state.json`. Done -- do not report unless the
user asked for the ingest explicitly; a single short line ("memory ingest: N
facts, graph refreshed") is enough then.

## Querying the graph (for any session)

- Relationship/meaning queries: `cd ~/.claude/memory-graph && python -m graphify query "<question>"`
- Deterministic keyword/stream queries: `python ~/.claude/scripts/brain_query.py facts <topic>`
- Visual: open `~/.claude/memory-graph/graphify-out/graph.html`
