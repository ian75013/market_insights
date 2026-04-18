# Market Insights — Index de la documentation

**Projet :** Pipeline ETL + API de données de marché avec LLM intégré.  
**Stack :** FastAPI · PostgreSQL · Airflow · Docker · LiteLLM

---

## Racine du projet

| Fichier | Description |
|---------|-------------|
| [../README.md](../README.md) | Vue d'ensemble, quick start |
| [../README_DOCKER.md](../README_DOCKER.md) | Guide Docker complet |
| [../ARCHITECTURE.md](../ARCHITECTURE.md) | Architecture globale du projet |

---

## Documentation (`doc/`)

### Déploiement & Infrastructure

| Fichier | Description |
|---------|-------------|
| [DEPLOIEMENT_OVH.md](DEPLOIEMENT_OVH.md) | Déploiement sur VPS OVH, configuration Apache/nginx |
| [SCRIPTS_DEPLOIEMENT.md](SCRIPTS_DEPLOIEMENT.md) | Scripts d'automatisation du déploiement |
| [ENV_FILES.md](ENV_FILES.md) | Variables d'environnement, fichiers `.env`, configuration |
| [AGENT_DEPLOYMENT_GUARDRAILS.md](AGENT_DEPLOYMENT_GUARDRAILS.md) | Règles de sécurité pour déploiements automatisés par agents |

### Pipelines & Data

| Fichier | Description |
|---------|-------------|
| [AIRFLOW_ETL.md](AIRFLOW_ETL.md) | Pipeline Airflow ETL, DAGs, scheduling, monitoring |

### Incidents & Post-mortems

| Fichier | Description |
|---------|-------------|
| [REPORT_COLD_START_2026-04-11.md](REPORT_COLD_START_2026-04-11.md) | Rapport de cold start du 11 avril 2026 |

---

## Scripts (`scripts/`)

| Fichier | Description |
|---------|-------------|
| [../scripts/DEPLOYMENT_GUIDE.md](../scripts/DEPLOYMENT_GUIDE.md) | Guide complet d'automatisation du déploiement |

---

## Guardrails (`.guardrails/rules/`)

| Fichier | Description |
|---------|-------------|
| [../.guardrails/rules/01-core-principles.md](../.guardrails/rules/01-core-principles.md) | Principes fondamentaux : sécurité, réversibilité, testabilité |
| [../.guardrails/rules/02-engineering-standards.md](../.guardrails/rules/02-engineering-standards.md) | Standards de code et revue |
| [../.guardrails/rules/03-security-privacy.md](../.guardrails/rules/03-security-privacy.md) | Sécurité et confidentialité |
| [../.guardrails/rules/04-testing-quality-gates.md](../.guardrails/rules/04-testing-quality-gates.md) | Couches de tests requises et blockers de merge |
| [../.guardrails/rules/05-release-change-management.md](../.guardrails/rules/05-release-change-management.md) | Gestion des releases et des changements |
| [../.guardrails/rules/06-observability-operations.md](../.guardrails/rules/06-observability-operations.md) | Observabilité et opérations |
| [../.guardrails/rules/07-documentation-knowledge.md](../.guardrails/rules/07-documentation-knowledge.md) | Exigences de documentation |
