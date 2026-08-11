"""Alembic env — URL lấy từ Settings (không hard-code trong alembic.ini)."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import get_settings
from app.core.database import Base

# Import models để metadata đăng ký với Alembic
from app.modules.config import models as config_models  # noqa: F401, E402
from app.modules.core import models as core_models  # noqa: F401, E402
from app.modules.policy import models as policy_models  # noqa: F401, E402
from app.modules.calendar import models as calendar_models  # noqa: F401, E402
from app.modules.mdm import models as mdm_models  # noqa: F401, E402
from app.modules.integration import models as integration_models  # noqa: F401, E402

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
