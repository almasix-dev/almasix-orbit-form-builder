"""SQL migration helpers for form builder tables."""

from __future__ import annotations

CREATE_FORM_DEFINITIONS = """
CREATE TABLE IF NOT EXISTS orbit_form_definitions (
    id VARCHAR(64) PRIMARY KEY,
    slug VARCHAR(191) NOT NULL,
    title VARCHAR(255) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'draft',
    definition JSON NOT NULL,
    settings JSON NOT NULL,
    tenant_id VARCHAR(191) NOT NULL DEFAULT '',
    created_at TIMESTAMP NULL,
    updated_at TIMESTAMP NULL,
    UNIQUE (slug, tenant_id)
);
"""

CREATE_FORM_SUBMISSIONS = """
CREATE TABLE IF NOT EXISTS orbit_form_submissions (
    id VARCHAR(64) PRIMARY KEY,
    form_id VARCHAR(64) NOT NULL,
    payload JSON NOT NULL,
    meta JSON NOT NULL,
    tenant_id VARCHAR(191) NOT NULL DEFAULT '',
    created_at TIMESTAMP NULL
);
"""


def migration_statements() -> list[str]:
    return [CREATE_FORM_DEFINITIONS, CREATE_FORM_SUBMISSIONS]
