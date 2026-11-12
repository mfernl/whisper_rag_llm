# CLAUDE.md — whisper_rag_llm

> Claude Code carga este archivo al empezar cada sesión. Explica **cómo trabajamos** y **por dónde seguir**.
> Última actualización: 2026-11-12.

---

## 1. Cómo tiene que trabajar Claude en este proyecto

### Mentoría (reglas heredadas de `instrucciones.txt`)
- Responder **en español**, paso a paso.
- **No dar la solución completa.** Dar pistas, preguntas guía, esqueletos con huecos (`TODO`) y criterios para comprobar el resultado. Si Marco pide "hazme X", darle un esqueleto con pistas.
- Diagnosticar a partir del código y la salida que pegue Marco, y señalarle dónde tiene que mirar.
- Las APIs de LangChain, LangGraph y RAGAS cambian rápido: **consultar la documentación actual** antes de guiarle en esas fases.
- Entorno: Windows, **cmd.exe**, venv en `.venv`, Python 3.10.11. El Dockerfile usa `python:3.11-slim-bookworm`.

### Citar siempre las fuentes (petición explícita de Marco)
- Toda afirmación sobre **cómo funciona SDD** (o cualquier técnica o herramienta) tiene que llevar la **fuente con enlace**.
- Cada propuesta sobre **cómo debería trabajar Marco** tiene que explicar el **porqué** y de dónde sale.
- Cuando una recomendación sea **criterio propio de Claude** y no venga de una fuente, hay que decirlo así, con el razonamiento.
- Las referencias base están en la sección 5.

---

## 2. Estado actual (2026-11-12)

**El desarrollo está EN PAUSA.** Antes de seguir, Marco quiere pasar el proyecto a un flujo **SDD (Spec-Driven Development)**. El plan está en la sección 3.

- Contexto detallado de las sesiones anteriores en `instrucciones.txt` (ignorado por git y **desactualizado**: dice que la Fase 2 no ha empezado). En `razonamiento.md` se explica por qué se mantiene SQLAlchemy, y `chuleta_comandos_rag_llm.md` es la chuleta de comandos.
- **Fase 1 (modelo de datos y tests): cerrada.** Modelos `RealTimeSession`, `BatchTranscription` y `TranscriptionEmbeddings`, con el `CheckConstraint` `check_one_source`. Hay 5 tests en `tests/test_db.py` contra SQLite en memoria.
- **Fase 2 (Postgres + pgvector + Alembic): casi cerrada.** Último commit: `75c39fe`. Ya hay servicio `db` en compose con volumen y healthcheck, `pg_uri` lee el `.env`, la columna es `Vector(384)` y existe la migración `alembic/versions/e6edc15da35a_esquema_inicial.py`. En `main.py` están comentados `create_all` y `CREATE EXTENSION`.
  Pendientes (con preguntas guía, sin dar la solución):
  1. ¿Está aplicada la migración? Comprobarlo con `alembic current`, y con `\dt` y `\dx` en psql.
  2. Con una BD vacía (después de `down -v`), ¿quién crea la extensión `vector`? ¿La crea la migración?
  3. ¿Siguen pasando los tests en SQLite ahora que hay una columna `Vector`? ¿Habría que ejecutarlos contra Postgres?
  4. Sin commitear: el cambio de `.gitignore`, `chuleta_comandos_rag_llm.md`, `razonamiento.md` y `requirements_copia.txt` (¿se commitea o se borra?).
- **Fases que quedan** (objetivo completo en `instrucciones.txt`): 3 ingesta (chunking por ventanas de tiempo + sentence-transformers), 4 endpoint `/ask` con citas, 5 agente LangGraph (herramientas `buscar_en_transcripcion` y `consultar_metadatos`), 6 evaluación RAGAS, 7 worker y compose multiservicio, 8 README/CI.

---

## 3. Plan: pasar a SDD y después reanudar

### 3.1 Qué es SDD (resumen con fuentes)
- La **especificación es la fuente de verdad**. El código, los tests y la documentación salen de ella, y cualquier cambio empieza por modificar la spec. [Allstacks], [Allegro]
- Hay tres niveles: *spec-first* (la spec se escribe antes de programar), *spec-anchored* (la spec se mantiene viva después) y *spec-as-source* (solo se edita la spec; todavía no es práctico). [Böckeler], [InfoWorld]
- El flujo de referencia es parecido en las dos herramientas principales. **GitHub Spec Kit**: constitution → specify → clarify → plan → tasks → analyze → implement [Augment], [CodeMySpec-SK], [Bitovi]. **Kiro**: `requirements.md` (criterios en notación EARS) → `design.md` → `tasks.md` [Kiro], [CodeMySpec-Kiro].

### 3.2 Buenas prácticas que adoptamos y por qué

| Práctica | Por qué | Fuente |
|---|---|---|
| Separar el **qué** (spec) del **cómo** (plan y tareas) | La spec es estable y el plan se puede tirar. Mezclarlos genera confusión y complica el trabajo incremental | [Allegro] |
| Tener una **constitución** con los principios comunes | Así no se repiten los estándares en cada spec y se mantienen coherentes | [Allegro], [Augment], [Bitovi] |
| Una **spec por funcionalidad o fase**, no un documento monolítico | Cabe mejor en el contexto del agente y es más fácil de mantener | [Allegro], [Osmani] |
| **Criterios de aceptación verificables** en notación EARS (CUANDO/SI … EL SISTEMA DEBERÁ …) | Quitan ambigüedad y se pueden convertir directamente en tests | [Kiro], [CodeMySpec-Kiro] |
| **Tareas pequeñas**, enlazadas a un criterio y que quepan en una sesión | Las tareas grandes y difusas no salen bien con un contexto limitado | [Allegro], [Kilo], [CodeMySpec-Kiro] |
| **Tests como bucle de feedback** (test primero) | Le dan al agente, y a Marco, un objetivo concreto que comprobar | [Allegro] |
| **Iterar** la spec, sin quedarse corto ni pasarse | Una spec vaga deja demasiado a la interpretación y una sobredetallada acaba siendo código en prosa | [Allegro], [Osmani], [Intent] |
| **Mantener la spec al día** (spec-anchored) | Si la spec se desvía del código, deja de servir | [Intent], [Allegro] |
| **Ajustar el rigor al riesgo**: nada de spec para cambios triviales | En tareas triviales SDD da más trabajo del que ahorra | [Allegro] |
| **Revisión humana**, y si se puede, una sesión nueva sin contexto previo | Una sesión limpia detecta lo que se le escapó a la original. La responsabilidad final es de la persona | [Allegro] |

### 3.3 Decisiones de adaptación (criterio propio de Claude, con su razonamiento)
- **SDD a mano, sin instalar Spec Kit ni Kiro.** En Spec Kit es el agente quien genera las specs [Augment], [Bitovi], y eso choca con la regla de mentoría de no dar soluciones. Escribirlas a mano obliga a Marco a pensar los requisitos, que es justo lo que quiere aprender. *Se puede replantear si quiere probar la herramienta.*
- **Nivel spec-anchored.** Spec-as-source todavía no es práctico [Böckeler], [InfoWorld], y spec-first a secas deja que la spec se quede obsoleta [Intent].
- **Reparto de papeles.** Marco escribe la spec, el plan y las tareas. Claude hace de *clarify* y *analyze* (preguntas sobre ambigüedades y comprobación de coherencia entre spec y plan), que son pasos de Spec Kit [Augment], y da pistas al implementar.
- **Las specs de las Fases 1 y 2 serán retroactivas y breves.** Ya están hechas; documentarlas sirve para tener trazabilidad (criterio → test), no para volver a diseñarlas.

### 3.4 Pasos de la migración (en orden)
- [x] 0. Crear este `CLAUDE.md`.
- [ ] 1. Crear `specs/constitution.md` (lo escribe Marco con preguntas guía de Claude): stack, convenciones, puertas de calidad (tests en verde, migración revisada, etc.) y reglas de commits.
- [ ] 2. Crear `specs/000-vision.md`: objetivo, alcance y lo que queda fuera (fine-tuning, diarización). Sacarlo de `instrucciones.txt`.
- [ ] 3. Crear `specs/001-modelo-datos/spec.md`, retroactiva. Ejemplo de criterio EARS: *"SI se intenta guardar un embedding con `session_id` y `batch_id` a la vez, o sin ninguno, ENTONCES el sistema DEBERÁ rechazarlo"* → `test_embedding_two_transcriptions` y `test_embedding_no_transcriptions`.
- [ ] 4. Crear `specs/002-postgres-pgvector/spec.md` y `tasks.md`, con los pendientes de la sección 2 como tareas.
- [ ] 5. Mover `razonamiento.md` a `docs/decisiones/` (formato ADR) y decidir qué hacer con `instrucciones.txt` (pasar a `specs/` lo que siga vigente).
- [ ] 6. Cerrar la Fase 2 siguiendo su `tasks.md`.
- [ ] 7. **Reanudar el desarrollo**: Fase 3 (ingesta) con el flujo completo: `spec.md` → clarify → `plan.md` → analyze → `tasks.md` → implementar (test primero, un commit por tarea) → actualizar la spec.

Estructura objetivo:
```
CLAUDE.md
specs/constitution.md
specs/000-vision.md
specs/NNN-nombre/{spec.md, plan.md, tasks.md}
docs/decisiones/
```

**Al empezar la próxima sesión:** recordarle a Marco en qué punto de la sección 3.4 está y proponerle seguir con el primer paso sin marcar. Al terminar cada paso, actualizar la casilla y la fecha de este archivo.

---

## 4. Comandos útiles
Ver `chuleta_comandos_rag_llm.md`. Tests: `python -m pytest -v tests\test_db.py` (en cmd, con el `.venv` activado).

---

## 5. Referencias
- [Böckeler] B. Böckeler, *Understanding Spec-Driven-Development: Kiro, spec-kit, and Tessl*, martinfowler.com (oct. 2025): https://www.martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html
- [Allegro] K. Piechna, *Spec-driven development best practices*, Allegro Tech Blog (jun. 2026): https://blog.allegro.tech/2026/06/spec-driven-development-best-practices.html
- [Osmani] A. Osmani, *How to write a good spec for AI agents*: https://addyosmani.com/blog/good-spec/
- [Intent] *Best Practices for Spec-Driven Development*, intent-driven.dev: https://intent-driven.dev/knowledge/best-practices/
- [Allstacks] *Spec-driven development*, Allstacks: https://www.allstacks.com/blog/spec-driven-development
- [Kilo] *Spec-Driven Development pattern*, Kilo: https://path.kilo.ai/introduction/patterns/spec-driven-development/
- [Kiro] *Specs — concepts*, documentación oficial de Kiro: https://kiro.dev/docs/specs/concepts
- [CodeMySpec-Kiro] *Kiro Specs Explained: EARS, Spec Mode, and the Trade-offs*: https://codemyspec.com/blog/kiro-specs-explained
- [CodeMySpec-SK] *GitHub Spec Kit: How It Works and When to Use It (2026)*: https://codemyspec.com/blog/github-spec-kit-guide
- [Augment] *GitHub Spec Kit practical guide (SDD workflow)*: https://www.augmentcode.com/guides/github-spec-kit-practical-guide-sdd-workflow
- [Bitovi] *Spec Kit — Analysis*, Bitovi wiki: https://wiki.at.bitovi.com/wiki/spaces/AIEnabledDevelopment/pages/1799847940/Spec+Kit+-+Analysis
- [InfoWorld] M. Heller, *Four cutting-edge tools for spec-driven development*: https://infoworld.com/article/4171332/four-cutting-edge-tools-for-spec-driven-development.html
- Repositorio oficial de Spec Kit (comprobar los nombres actuales de los comandos antes de citarlos): https://github.com/github/spec-kit
