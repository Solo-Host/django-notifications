# Copilot Instructions for django-notifications

## Quick Start

This is a reusable Django package for persistent user notifications, admin
dispatches, and a small authenticated API surface. Use `uv` for dependency
management and `tox` as the canonical local validation entry point. This
repository currently targets Python 3.13 only.

```bash
uv sync --extra dev
```

`uv.lock` is committed. Update it when dependency metadata changes, and keep CI
compatible with `uv sync --frozen --extra dev`.

## Build, Test, and Lint Commands

### Setup and Packaging
```bash
uv sync --extra dev
uv run python -m build
```

### Tox Entry Points
```bash
uv run tox
uv run tox -e py313
uv run tox -e lint
uv run tox -e mypy
uv run tox -e security
uv run tox -e py313 -- tests/test_api.py
```

### Direct Commands
```bash
uv run pytest
uv run ruff check django_notifications tests
uv run mypy django_notifications tests
uv run bandit -q -r django_notifications -x django_notifications/migrations
uv run pip-audit
```

`tox` is the canonical entry point for local and CI checks. The configured
environments are `py313`, `lint`, `mypy`, and `security`, with optional `ruff`,
`bandit`, and `pip-audit` aliases for focused runs.

## High-Level Architecture

### Core Components

**Models and admin** (`django_notifications/models.py`, `django_notifications/admin.py`)
- `UserNotification` stores persistent per-user notification rows
- `NotificationDispatch` stores operator-created bulk dispatch requests and
  audit metadata for fan-out delivery
- Django admin lets staff inspect notifications and queue new dispatches

**Services and tasks** (`django_notifications/services.py`, `django_notifications/tasks.py`)
- The service layer creates per-user notifications, resolves host-provided
  settings overrides, queues dispatches, and cleans up expired rows
- Celery tasks perform queued bulk delivery and periodic cleanup

**API surface** (`django_notifications/serializers.py`, `django_notifications/views.py`, `django_notifications/urls.py`)
- Authenticated DRF endpoints expose list, unread count, mark-read,
  mark-all-read, delete, and client-config actions
- Host projects mount `django_notifications.urls` under their preferred API
  prefix

**Configuration** (`django_notifications/conf.py`)
- Static Django settings and an optional dotted-path provider hook feed the
  package settings used for polling cadence, retention, and cleanup timing

## Key Conventions

### Code Style
- Use `from __future__ import annotations` when forward references are needed
- Ruff is the linting tool; line length is 99 characters
- Migration files are exempt from the normal line-length and import-order rules

### Django Patterns
- Keep host-specific notification factories outside this package
- Keep the settings-provider contract indirect so host apps can source config
  from their own registry/service layer
- Treat bulk dispatches as auditable records instead of writing raw
  `UserNotification` rows by hand in admin-only code

### Versioning and Release Flow
- `pyproject.toml` is the source of truth for the package version
- `django_notifications/__init__.py` and the editable `uv.lock` package entry
  must stay aligned with `pyproject.toml`
- Normal feature work should not bump the version manually
- Releases go through `.github/workflows/release.yml`, which creates a release
  bump PR, updates `pyproject.toml`, `django_notifications/__init__.py`, and
  the committed `uv.lock` metadata, then creates the tag and GitHub Release
  after merge
- The release flow is GitHub-only for now; do not add PyPI publishing steps

## Git Workflow

### Using Worktrees
- Create branch worktrees under the shared `../../worktrees/` directory (full
  path: `/home/bjorn/workspace/web_projects/worktrees/`).
- Do not work directly on `main`; create a branch worktree first:
  ```bash
  git worktree add ../../worktrees/django-notifications-my-change -b my-change main
  cd ../../worktrees/django-notifications-my-change
  ```
- Commit and push from that worktree branch as usual.

## Important Notes

- Tests use `tests.settings`
- `django_notifications/__init__.py` and `uv.lock` should stay in sync with
  packaging metadata changes
- Keep workflow path filters aligned with this repo's package path

