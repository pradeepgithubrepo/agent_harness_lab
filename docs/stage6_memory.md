# Stage 6 memory module

The memory module is not a workflow-state store. Durable orchestration remains
the authority for checkpoints, retries, timers, approvals, and recovery state.
Only a controlled projection may enter short-lived working memory.

Required ignored `.env` variables are listed in `.env.example`; secret values
must only be set locally. Run:

```bash
python scripts/test_memory_connections.py
python scripts/demonstrate_memory_lifecycle.py
```

Azure AI Search must use the dedicated `idx-agent-semantic-memory` index. Its
minimum fields are `id` (key), `scope_id` (filterable), `subject`, `fact`,
`supporting_details` (searchable), `status` (filterable), and
`security_scope` (filterable). Do not alter unrelated indexes.

Cosmos containers use partition key `/scope_id`: `episodes` has TTL enabled
for episodic retention, while `semantic_facts` is authoritative and uses
status/supersession rather than age-based eviction.
