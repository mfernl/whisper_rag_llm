# Constitución — whisper_rag_llm
Versión: 0.1 · Fecha: 2026-11-14

## 1. Stack fijo
Cambiar cualquiera de estos elementos requiere abrir una decisión (ADR) en `docs/decisiones/`.

| Capa | Tecnología | Versión |
|---|---|---|
| Lenguaje | Python | 3.11 (la del `Dockerfile`) |
| API | FastAPI + Uvicorn | TODO |
| Persistencia | PostgreSQL + pgvector (imagen `pgvector/pgvector:0.8.7-pg18-bookworm`) | pgvector 0.8.7 · PostgreSQL 18 |
| ORM y migraciones | SQLAlchemy + Alembic + psycopg | TODO |
| Transcripción | openai-whisper (modelo `tiny`) + torch (CPU) | TODO |
| Embeddings | sentence-transformers con `all-MiniLM-L6-v2` (dimensión 384 → columna `Vector(384)`) | TODO |
| Autenticación | python-jose + bcrypt | TODO |
| Empaquetado | Docker + Docker Compose | — |

**LLM (Fases 4 y 5):** llamada a una API externa. Proveedor: TODO.

## 2. Restricciones
- Despliegue en Render, tier gratis: 512 MB de RAM. Hay acceso a internet.
- Los embeddings se generan con el modelo cargado en la memoria del servicio en Render.
- Riesgo conocido: no se ha medido si torch + Whisper tiny + MiniLM caben en 512 MB. Queda abierto qué hacer si no caben; se decide cuando se mida.

## 3. Puertas de calidad (Definition of Done)
- Una tarea está terminada cuando sus tests y los de toda la suite están en verde.
  - Un test saltado (`skip`) cuenta como verde solo si lleva motivo (se revisan con `pytest -rs`).
  - Si los tests de integración no se ejecutan por falta de Docker, la suite NO cuenta como verde.
- Cada criterio de aceptación (EARS) tiene al menos un test que lo comprueba.
- Se trabaja en ciclos de TDD (rojo → verde → refactorizar), empezando por los tests de cada criterio EARS. Más allá de esos tests, el desarrollador decide cuándo dejar de iterar.
- Los tests de integración se ejecutan con pytest + testcontainers-python, en local, con Python 3.11 y la imagen `pgvector/pgvector:0.8.7-pg18-bookworm`.
- Cada migración de Alembic se revisa a mano antes de commitearla.
- Una tarea que modifica otra spec solo queda terminada si ambas funcionan después de actualizarse lo necesario.

## 4. Convenciones de trabajo
- Un commit por tarea.
- Mensajes de commit con [Conventional Commits](https://www.conventionalcommits.org/es/v1.0.0/) (`feat:`, `fix:`, `test:`, `docs:`…).
- Idioma: todo en inglés (commits y código). PENDIENTE: ¿también las specs y la documentación, que hoy están en español?
- Ramas: una rama por tarea, a partir de cuando el flujo SDD esté formalizado (pasos 1-5 de `CLAUDE.md` §3.4). Hasta entonces, commits directos en `main`.
- TODO: estructura de `specs/` (propuesta en `CLAUDE.md`: `specs/NNN-nombre/{spec.md, plan.md, tasks.md}`).

## 5. Principios de seguridad y datos
TODO

## 6. Gobernanza
TODO: cómo se cambia esta constitución
