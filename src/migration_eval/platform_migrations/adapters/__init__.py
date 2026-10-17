"""Provider factory. The real adapter is a disabled port."""

from migration_eval.platform_migrations.adapters.ports import ProviderDisabled, build_provider

__all__ = ["ProviderDisabled", "build_provider"]
