# Stage 11 — Write permission gate

⚠️ Summarise **every** file that will be written or edited — spec(s), registry, project map, code/tests already
changed in a remediating run, studies — with the diff stat and the intended **staged-file count**.

Ask for **W1** (or **C1** when tags and push are approved in the same reply — it must list the tags and the push).
Approval covers the writes **and the local finalization commit**. Tag creation (G1) and push (P1) stay separately
gated unless C1 was shown.

Record the reply with `manifest approve <repo> W1 --statement-file … --reply-file …` (stored verbatim with a UTC
time; file arguments keep Arabic text safe from shell quoting). Then prepare the finalization plan
(`stages/12-finalize.md`) and show its dry-run diff in the same message.

Ripple patches: list every other spec that will be patched, with its new version and tag.
