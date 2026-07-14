---
id: SK-0004
nombre: decision-record
tipo: skill
estado: activa
disparador: "se tomo una decision de diseno con alternativas descartadas, o que sera dificil de revertir"
ubicacion: skills/decision-record.md
creado_por: usuario
version: 1
---

# Skill: decision-record

Cuándo se dispara: se eligió un enfoque técnico entre varios posibles
(librería, patrón, estructura de datos, protocolo, etc), especialmente
si es costoso de revertir o si alguien podría razonablemente preguntar
"¿por qué se hizo así y no de otra forma?".

No crear un ADR para decisiones triviales o fácilmente reversibles
(nombre de una variable, orden de dos pasos independientes). La señal
es: si en 3 meses alguien preguntará "¿por qué?", amerita ADR.

## Procedimiento

1. Determinar el próximo ID: revisar el último `D-XXXX` en
   `decisions/`. No hay comando `pctl` dedicado todavía — si esto se
   vuelve frecuente, proponer automatizarlo vía
   `skill-authoring.md`.
2. Crear `decisions/D-XXXX.md` con frontmatter:
   ```
   id, titulo, fecha, estado (aceptada de entrada salvo que se
   discuta primero), reemplaza, version_schema
   ```
3. Cuerpo con exactamente estas tres secciones:
   - `## Contexto` — qué problema forzó la decisión, en pocas líneas.
   - `## Decisión` — qué se eligió, en una afirmación clara.
   - `## Consecuencias` — qué se gana, qué se pierde, qué queda
     pendiente de revisar más adelante.
4. Enlazar el ADR desde el `.md` de arquitectura del dominio afectado,
   en la sección "Decisiones relevantes" — solo el ID y el título, no
   dupliques el contenido ahí.
5. Si esta decisión reemplaza una anterior: marcar la nueva con
   `reemplaza: [D-000X]` y cambiar el `estado` de la vieja a
   `reemplazada` (editar su frontmatter).

## Qué NO hacer

- No incluir código de ejemplo de las alternativas evaluadas — describir
  el trade-off en prosa.
- No crear un ADR por cada commit; agrupar decisiones relacionadas de
  la misma sesión en un solo documento si tiene sentido.
