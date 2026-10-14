# CI/CD — Explained Simply

## What CI and CD actually mean

**CI (Continuous Integration)** — every time someone pushes code or opens
a PR, a robot automatically checks it: does it follow style rules? Do the
tests pass? Does it build? You find out in minutes, not after it breaks
something in production.

**CD (Continuous Delivery)** — once CI says the code on `main` is good,
another robot automatically packages it (here: Docker images) and
publishes it somewhere people can pull it from.

In this project: **`ci.yml`** is the checker. **`cd.yml`** is the
publisher. They're two separate files on purpose — CD only ever runs on
code that CI has already approved.

```mermaid
flowchart LR
    A["You push code"] --> B["CI runs checks"]
    B -->|"fails"| C["Fix it, push again"]
    B -->|"passes, on main"| D["CD publishes Docker images"]

    classDef action fill:#0071CE,color:#fff,stroke:#004C91
    classDef bad fill:#C62828,color:#fff,stroke:#8f1d1d
    classDef good fill:#1B8A5A,color:#fff,stroke:#11603e
    class A,B action
    class C bad
    class D good
```

---

## What CI does here — 7 jobs

```mermaid
flowchart TD
    LINT["1. Lint<br/>style + SQL formatting"]
    LINT --> UNIT["2. Unit tests"]
    LINT --> SMOKE["3. Smoke tests"]
    LINT --> DASH["4. Dashboard smoke"]
    LINT --> DAG["5. Airflow DAG check"]
    LINT --> BUILD["6. Docker build check"]
    UNIT --> INT["7. Integration test"]
    SMOKE --> INT
    DASH --> INT
    DAG --> INT
    BUILD --> INT

    classDef gate fill:#0071CE,color:#fff,stroke:#004C91
    classDef check fill:#017CEE,color:#fff,stroke:#015da8
    classDef live fill:#1B8A5A,color:#fff,stroke:#11603e
    class LINT gate
    class UNIT,SMOKE,DASH,DAG,BUILD check
    class INT live
```

| Job | What it checks, in plain terms |
|---|---|
| **lint** | Is the code and SQL formatted consistently? Runs first — no point running slow tests on messy code. |
| **unit-tests** | Do the small, isolated pieces of Python code (`src/utils/`, `extract.py` logic) work correctly? |
| **smoke-tests** | Do all modules import, the repo layout hold, and CLIs answer? No live services needed. |
| **dashboard-smoke** | Does the dashboard import with only its own pinned deps (no `databricks` connector)? |
| **dag-integrity** | Does the Airflow pipeline definition actually load without errors or circular dependencies? |
| **docker-build** | Do both Docker images actually build? This job never pushes anything — it just proves the `Dockerfile`s aren't broken. |
| **integration** | The real test: spin up a throwaway Postgres, load fake sample data, and run the **entire** bronze → silver → gold pipeline exactly like it would run for real. |

### Integration — the important one

This job rebuilds the whole medallion pipeline against a temporary
database, using fake data instead of real MongoDB:

```mermaid
flowchart LR
    A["Load fake bronze data"] --> B["Check bronze data"]
    B --> C["Build silver layer"]
    C --> D["Check silver data"]
    D --> E["Build gold layer"]
    E --> F["Check gold data"]

    classDef bronze fill:#B5651D,color:#fff,stroke:#7a4413
    classDef silver fill:#6B7B8C,color:#fff,stroke:#4a565f
    classDef gold fill:#D4A017,color:#1A1F2B,stroke:#8a6d1f
    classDef check fill:#0071CE,color:#fff,stroke:#004C91
    class A bronze
    class B,D,F check
    class C silver
    class E gold
```

Each arrow is a **gate**: if a check fails, everything after it stops.
This mirrors exactly what `run_pipeline.ps1` and the real Airflow DAG do
— CI is just running the same logic somewhere disposable, so a bug is
caught before it ever touches real data.

---

## What CD does here

```mermaid
flowchart LR
    A["CI passes on main"] --> B["Build 2 Docker images"]
    B --> C["Push to GitHub's<br/>container registry (GHCR)"]

    classDef good fill:#1B8A5A,color:#fff,stroke:#11603e
    classDef action fill:#0071CE,color:#fff,stroke:#004C91
    class A good
    class B,C action
```

Two images get built and published:

- `walmart-pipeline` — the standalone image
- `walmart-airflow` — the image the Airflow stack runs on

Both get tagged with the commit's short SHA and `latest`. There's no
live server this deploys to — "CD" here just means *make a fresh,
pullable image available*, not *push to a website*. If this project
ever gets a real always-on host, that's where a deploy step would be
added to `cd.yml`.

**Why CD waits for CI, instead of running on every push directly:**
if `cd.yml` triggered on `push` the same way `ci.yml` does, it could
publish a broken image the moment code lands on `main`, before anyone
knows it's broken. Instead, `cd.yml` triggers on `ci.yml` finishing —
and only publishes if that run succeeded.

---

## The short version

| | Runs when | Job |
|---|---|---|
| **CI** | Every PR, every push to `main` | Catch problems early |
| **CD** | Only after CI passes on `main` | Publish trusted, working images |

If you remember one thing: **CI protects `main`, CD only ships what CI
already approved.**
