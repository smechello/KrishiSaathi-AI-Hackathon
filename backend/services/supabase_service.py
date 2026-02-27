"""Database service router — picks RDS or Supabase based on ``Config.DB_BACKEND``.

Every file in the codebase does:

    from backend.services.supabase_service import SupabaseManager

This module transparently routes that import to the correct backend:

  - ``DB_BACKEND="rds"``      → ``rds_service.SupabaseManager``     (AWS RDS PostgreSQL + bcrypt + JWT)
  - ``DB_BACKEND="supabase"`` → ``supabase_service_legacy.SupabaseManager`` (original Supabase GoTrue)

**Zero changes needed in any consumer file.**
"""

from __future__ import annotations

import os

# Determine backend at module load time
_backend = os.getenv("DB_BACKEND", "rds").lower()

if _backend == "supabase":
    from backend.services.supabase_service_legacy import SupabaseManager  # noqa: F401
else:
    from backend.services.rds_service import SupabaseManager  # noqa: F401

__all__ = ["SupabaseManager"]
