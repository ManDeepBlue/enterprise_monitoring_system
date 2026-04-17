"""
Alembic Environment Configuration
---------------------------------
This script is used by Alembic to configure the migration environment.
It handles both 'offline' (SQL generation) and 'online' (direct DB update) 
migration modes.
"""

import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Import the SQLAlchemy Base and models to ensure they are registered 
# on the metadata for 'autogenerate' support.
from app.db.session import Base
from app.db import models  # noqa

# Alembic Config object, which provides access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set the target metadata for autogenerate support
target_metadata = Base.metadata

def get_url():
    """
    Retrieves the database connection URL from environment variables.
    This ensures migrations use the same DB as the application.
    """
    return os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/monitoring")

def run_migrations_offline():
    """
    Run migrations in 'offline' mode.
    This configures the context with just a URL and not an Engine, 
    though an Engine is acceptable here as well. By skipping the Engine 
    creation we don't even need a DBAPI to be installed.
    Calls to context.execute() here emit the given string to the script output.
    """
    url = get_url()
    context.configure(
        url=url, 
        target_metadata=target_metadata, 
        literal_binds=True, 
        dialect_opts={"paramstyle": "named"}
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """
    Run migrations in 'online' mode.
    In this scenario we need to create an Engine and associate a connection 
    with the context.
    """
    # Get the configuration section from the alembic.ini file
    configuration = config.get_section(config.config_ini_section)
    # Inject the actual database URL from environment
    configuration["sqlalchemy.url"] = get_url()
    
    # Create the engine from configuration
    connectable = engine_from_config(
        configuration, 
        prefix="sqlalchemy.", 
        poolclass=pool.NullPool
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

# Determine if we should run in offline or online mode
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
