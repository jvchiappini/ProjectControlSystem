---
id: DB-XXXX
titulo: "(database doc title)"
categoria: database
estado: draft  # draft | published | outdated | deprecated
creado: YYYY-MM-DD
actualizado: YYYY-MM-DD
autor: agente
tags: []
---

# (Database doc title)

## Overview

Description of the database component being documented.

## Schema

### Table: `table_name`

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| id | UUID | NO | gen_random_uuid() | Primary key |
| | | | | |

#### Indexes
- `idx_name` on `column`

#### Constraints
- Foreign key: `column` references `other_table(id)`

### Views

### Functions / Stored procedures

## Migrations

| Migration | Description | Status |
|---|---|---|
| | | |

## Relationships

```mermaid
erDiagram
    ENTITY {
        type field
    }
```

## Related

- `architecture/<domain>.md`
