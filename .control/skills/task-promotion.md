---
id: SK-0002
nombre: task-promotion
tipo: skill
estado: activa
disparador: "a task changes state (work starts, blocked, completed, deprioritized)"
ubicacion: skills/task-promotion.md
creado_por: usuario
version: 1
---

# Skill: task-promotion

Trigger: any state change of an existing task.

## Procedure

1. Never change the `estado` field by editing the frontmatter by hand.
   Always use `pctl task-move <id> <new_state>`.
2. Before moving to `in_progress`: confirm the task has context and
   reasonable acceptance criteria (if not, apply `task-intake.md`
   first).
3. Before moving to `blocked`: have the concrete reason ready,
   `pctl task-move <id> blocked --motivo "..."` — the command fails
   without a reason, so there is no way to block without explaining
   why.
4. Before moving to `done`: verify all "Criterios de aceptación"
   checkboxes in the body are checked. If legitimately completed with
   something pending (reduced scope, conscious decision), use
   `--force "reason"` — never falsely check boxes just to pass
   validation.
5. After any move, run `pctl reindex` (normally automatic within
   `task-move`, but confirm if anything was edited manually in the
   same turn).
6. Log the event in the active session:
   `pctl session-log <sid> "T-XXXX: <old_state> -> <new_state>"`.

## Reopening completed tasks

Moving from `done` to `in_progress` is valid (bug found later,
requirements changed). `pctl` automatically annotates date and reason
if `--motivo` is passed. Always provide a reason in this case even if
the command does not require it — it helps anyone reading the history
later.
