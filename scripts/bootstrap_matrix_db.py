#!/usr/bin/env python
"""
Matrix Database Bootstrap Script

Creates PostgreSQL database and user for Matrix Synapse.
Works with both development and production environments.
Safe to run multiple times (idempotent).

Usage:
    python scripts/bootstrap_matrix_db.py [--dry-run] [--verbose]
    
    # Using uv in project context:
    uv run python scripts/bootstrap_matrix_db.py

Environment Variables Required:
    POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
    MATRIX_DATABASE_PASSWORD

Example:
    # Development (using docker-compose postgres)
    POSTGRES_HOST=localhost POSTGRES_PORT=5432 POSTGRES_USER=eqmd_user \
    POSTGRES_PASSWORD=eqmd_dev_password_123 POSTGRES_DB=eqmd_dev \
    MATRIX_DATABASE_PASSWORD=secure_matrix_password \
    python scripts/bootstrap_matrix_db.py
"""

import os
import sys
import argparse
import logging
from typing import Optional

try:
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
except ImportError:
    print("ERROR: psycopg2 not installed. Run: uv add psycopg2-binary")
    sys.exit(1)


def setup_logging(verbose: bool = False):
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(levelname)s: %(message)s'
    )


def get_env_or_exit(var_name: str) -> str:
    """Get environment variable or exit with error."""
    value = os.environ.get(var_name)
    if not value:
        logging.error(f"Environment variable {var_name} is required")
        sys.exit(1)
    return value


def connect_to_postgres(host: str, port: str, user: str, password: str, database: str) -> psycopg2.extensions.connection:
    """Connect to PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        logging.debug(f"Connected to PostgreSQL at {host}:{port}")
        return conn
    except psycopg2.Error as e:
        logging.error(f"Failed to connect to PostgreSQL: {e}")
        sys.exit(1)


def database_exists(cursor, db_name: str) -> bool:
    """Check if database exists."""
    cursor.execute(
        "SELECT 1 FROM pg_database WHERE datname = %s",
        (db_name,)
    )
    return cursor.fetchone() is not None


def user_exists(cursor, username: str) -> bool:
    """Check if user exists."""
    cursor.execute(
        "SELECT 1 FROM pg_user WHERE usename = %s",
        (username,)
    )
    return cursor.fetchone() is not None


def create_matrix_database(cursor, dry_run: bool = False):
    """Create matrix_db database if it doesn't exist."""
    db_name = "matrix_db"
    
    if database_exists(cursor, db_name):
        logging.info(f"Database '{db_name}' already exists")
        return
    
    sql = f'CREATE DATABASE "{db_name}" WITH ENCODING "UTF8" LC_COLLATE "C" LC_CTYPE "C" TEMPLATE template0'
    
    if dry_run:
        logging.info(f"[DRY RUN] Would create database: {sql}")
        return
    
    logging.info(f"Creating database '{db_name}'...")
    cursor.execute(sql)
    logging.info(f"Database '{db_name}' created successfully")


def create_matrix_user(cursor, matrix_password: str, dry_run: bool = False):
    """Create matrix_user with appropriate permissions."""
    username = "matrix_user"
    
    if user_exists(cursor, username):
        logging.info(f"User '{username}' already exists")
        # Update password in case it changed
        if not dry_run:
            cursor.execute(f'ALTER USER "{username}" PASSWORD %s', (matrix_password,))
            logging.info(f"Updated password for user '{username}'")
        else:
            logging.info(f"[DRY RUN] Would update password for user '{username}'")
        return
    
    if dry_run:
        logging.info(f"[DRY RUN] Would create user '{username}' with password")
        return
    
    logging.info(f"Creating user '{username}'...")
    cursor.execute(f'CREATE USER "{username}" PASSWORD %s', (matrix_password,))
    logging.info(f"User '{username}' created successfully")


def grant_permissions(cursor, dry_run: bool = False):
    """Grant necessary permissions to matrix_user on matrix_db."""
    username = "matrix_user"
    db_name = "matrix_db"
    
    grants = [
        f'GRANT ALL PRIVILEGES ON DATABASE "{db_name}" TO "{username}"',
    ]
    
    for sql in grants:
        if dry_run:
            logging.info(f"[DRY RUN] Would execute: {sql}")
        else:
            logging.info(f"Granting permissions: {sql}")
            cursor.execute(sql)
    
    if not dry_run:
        logging.info(f"Database permissions granted to '{username}' on '{db_name}'")


def grant_schema_permissions(cursor, matrix_password: str, dry_run: bool = False):
    """Grant schema-level permissions by connecting directly to matrix_db."""
    username = "matrix_user"
    db_name = "matrix_db"
    
    if dry_run:
        logging.info(f"[DRY RUN] Would grant schema permissions to '{username}' on '{db_name}'")
        return
    
    # Connect to the matrix_db database to grant schema permissions
    try:
        postgres_host = get_env_or_exit("POSTGRES_HOST")
        postgres_port = get_env_or_exit("POSTGRES_PORT")
        
        # Connect directly to matrix_db as the superuser
        postgres_user = get_env_or_exit("POSTGRES_USER")
        postgres_password = get_env_or_exit("POSTGRES_PASSWORD")
        
        matrix_conn = psycopg2.connect(
            host=postgres_host,
            port=postgres_port,
            user=postgres_user,
            password=postgres_password,
            database=db_name
        )
        matrix_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        matrix_cursor = matrix_conn.cursor()
        
        # Grant schema permissions
        schema_grants = [
            f'GRANT CREATE ON SCHEMA public TO "{username}"',
            f'GRANT USAGE ON SCHEMA public TO "{username}"',
            f'GRANT ALL ON ALL TABLES IN SCHEMA public TO "{username}"',
            f'GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO "{username}"',
            f'GRANT ALL ON ALL FUNCTIONS IN SCHEMA public TO "{username}"',
            # Grant permissions on future objects
            f'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO "{username}"',
            f'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO "{username}"',
            f'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT EXECUTE ON FUNCTIONS TO "{username}"',
        ]
        
        for sql in schema_grants:
            logging.info(f"Granting schema permissions: {sql}")
            matrix_cursor.execute(sql)
        
        matrix_cursor.close()
        matrix_conn.close()
        
        logging.info(f"Schema permissions granted to '{username}' on '{db_name}'")
        
    except psycopg2.Error as e:
        logging.error(f"Failed to grant schema permissions: {e}")
        raise


def test_matrix_connection(host: str, port: str, matrix_password: str, dry_run: bool = False):
    """Test connection as matrix_user to matrix_db."""
    if dry_run:
        logging.info("[DRY RUN] Would test connection as matrix_user")
        return
    
    try:
        test_conn = psycopg2.connect(
            host=host,
            port=port,
            user="matrix_user",
            password=matrix_password,
            database="matrix_db"
        )
        test_conn.close()
        logging.info("✓ Matrix database connection test successful")
    except psycopg2.Error as e:
        logging.error(f"✗ Matrix database connection test failed: {e}")
        return False
    
    return True


def main():
    parser = argparse.ArgumentParser(description="Bootstrap Matrix PostgreSQL database")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    args = parser.parse_args()

    setup_logging(args.verbose)
    
    # Get required environment variables
    postgres_host = get_env_or_exit("POSTGRES_HOST")
    postgres_port = get_env_or_exit("POSTGRES_PORT")
    postgres_user = get_env_or_exit("POSTGRES_USER")
    postgres_password = get_env_or_exit("POSTGRES_PASSWORD")
    postgres_db = get_env_or_exit("POSTGRES_DB")
    matrix_password = get_env_or_exit("MATRIX_DATABASE_PASSWORD")
    
    logging.info("Matrix Database Bootstrap")
    logging.info("=" * 25)
    logging.info(f"PostgreSQL Host: {postgres_host}:{postgres_port}")
    logging.info(f"Admin Database: {postgres_db}")
    logging.info(f"Admin User: {postgres_user}")
    if args.dry_run:
        logging.info("Mode: DRY RUN (no changes will be made)")
    
    # Connect to PostgreSQL as admin user
    conn = connect_to_postgres(
        postgres_host, postgres_port, postgres_user, postgres_password, postgres_db
    )
    
    try:
        cursor = conn.cursor()
        
        # Create database and user
        create_matrix_database(cursor, args.dry_run)
        create_matrix_user(cursor, matrix_password, args.dry_run)
        grant_permissions(cursor, args.dry_run)
        
        # Grant schema-level permissions
        grant_schema_permissions(cursor, matrix_password, args.dry_run)
        
        # Test the connection
        test_matrix_connection(postgres_host, postgres_port, matrix_password, args.dry_run)
        
        logging.info("✓ Matrix database bootstrap completed successfully")
        
    except psycopg2.Error as e:
        logging.error(f"Database operation failed: {e}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()