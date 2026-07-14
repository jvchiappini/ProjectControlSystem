---
id: SK-0009
nombre: domain-scoping
tipo: skill
estado: activa
disparador: "before creating or editing architecture documentation, or when creating a new task"
ubicacion: skills/domain-scoping.md
creado_por: usuario
version: 1
---

# Skill: domain-scoping

Trigger: every time the agent is about to write in
`architecture/<domain>.md` or create a task, and needs to decide which
domain it belongs to.

## Procedure

1. Look at `architecture/_index.md` — if the user's request clearly
   mentions an already existing domain, use that one, do not create a
   new one with a slightly different name (e.g., do not create
   "product" if "productos" already exists).
2. If the request is ambiguous between two existing domains (e.g.,
   "fix the checkout" could be `pagos` or `productos`), ask the user
   which one applies before touching any file. Do not document both
   "just in case".
3. If the request clearly introduces a new domain not in the index,
   confirm it with the user in one line before creating it formally
   (avoid typos or inconsistent granularity, e.g., creating `cart`
   when the project already has `pagos` and the cart should live
   inside it).
4. Once the domain is decided, ALL documentation work for that task
   goes only there. Do not touch other domain `.md` files even if the
   code crosses boundaries — if the crossing is real and relevant,
   mention it in "Componentes clave" of the main domain as a
   reference, without expanding the other domain.

## Domain granularity

Neither too large ("backend" as a single giant domain) nor too small
(one domain per file). Good signal: a domain groups what a new
developer would need to understand together to touch that part of the
system without reading the entire project.

## What NOT to do

- Do not create a new domain for each task — reusing existing ones is
  the norm, creating a new one is the exception.
- Do not rename an existing domain without telling the user — it breaks
  references in tasks and ADRs already created.
