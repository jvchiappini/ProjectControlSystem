# Skill: doc-concise

Trigger: post-edit of any `.md` inside `.control/` (architecture,
flows, decisions, tasks), or when executing `pctl doc-update`.

## Rule

There is no fixed line limit. Validation is based on **reference
density**:

> A section in a `.md` file inside `.control/` should not have more
> than 3 consecutive paragraphs without at least one `file:line`
> reference.

If a section is pure prose without pointing to code, it is a candidate
for pruning.

## Procedure

1. After writing or modifying any `.md` in `.control/`, parse sections.
2. For each section, count paragraphs (separated by double newline).
3. If there are 3+ consecutive paragraphs without any `file:line`,
   flag the section.
4. For each flagged section, suggest pruning: turn prose into
   references, or move the content to a flow if it describes
   cross-domain behavior.
5. Do not prune automatically — only flag and suggest. The final
   decision is the user's.

## Output

List of candidate sections for pruning, with a concrete suggestion of
what to do (convert to reference, move to flow, or delete).

## Example

```
architecture/stock.md — section "Detalle de implementacion":
  4 paragraphs without references.
  Suggestion: replace with references to `src/stock/validator.py:10-45`
  and `src/stock/reserve.py:22-30`.
```
