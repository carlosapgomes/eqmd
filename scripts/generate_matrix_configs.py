#!/usr/bin/env python
"""
Matrix Configuration Template Generator

Processes .template files and generates actual configuration files by substituting
environment variables. Used for Matrix Synapse and Element Web configurations.

Usage:
    python scripts/generate_matrix_configs.py [--check] [--verbose]
    
    # Using uv in project context:
    uv run python scripts/generate_matrix_configs.py

Environment Variables Required:
    MATRIX_FQDN, CHAT_FQDN, EQMD_DOMAIN, MATRIX_PUBLIC_BASEURL, OIDC_ISSUER,
    MATRIX_DATABASE_PASSWORD, HOSPITAL_EMAIL, SYNAPSE_OIDC_CLIENT_SECRET

Environment Variables Optional:
    MATRIX_ADMIN_USERS, MATRIX_BOT_USER_ID

Examples:
    # Generate all configs
    python scripts/generate_matrix_configs.py
    
    # Check if configs are up to date
    python scripts/generate_matrix_configs.py --check
    
    # Verbose output
    python scripts/generate_matrix_configs.py --verbose
"""

import os
import sys
import argparse
import logging
from typing import Dict, List, Tuple
from string import Template
from pathlib import Path


def load_env_file(env_path: str = '.env') -> Dict[str, str]:
    """Load environment variables from .env file."""
    env_vars = {}
    env_file = Path(env_path)
    
    if not env_file.exists():
        logging.warning(f"Environment file {env_path} not found")
        return env_vars
    
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            
            # Parse KEY=VALUE format
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Remove quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                
                env_vars[key] = value
                
                # Also set in os.environ for consistency
                os.environ[key] = value
    
    logging.debug(f"Loaded {len(env_vars)} variables from {env_path}")
    return env_vars


def setup_logging(verbose: bool = False):
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(levelname)s: %(message)s'
    )


def get_env_or_exit(var_name: str, default: str = None) -> str:
    """Get environment variable or exit with error."""
    value = os.environ.get(var_name, default)
    if not value:
        logging.error(f"Environment variable {var_name} is required")
        sys.exit(1)
    return value


def get_template_vars() -> Dict[str, str]:
    """Get all required template variables from environment."""
    matrix_fqdn = get_env_or_exit('MATRIX_FQDN')
    bot_user_id = os.environ.get('MATRIX_BOT_USER_ID') or f"@rzero_bot:{matrix_fqdn}"
    return {
        'MATRIX_FQDN': matrix_fqdn,
        'CHAT_FQDN': get_env_or_exit('CHAT_FQDN'),
        'EQMD_DOMAIN': get_env_or_exit('EQMD_DOMAIN'),
        'MATRIX_PUBLIC_BASEURL': get_env_or_exit('MATRIX_PUBLIC_BASEURL'),
        'OIDC_ISSUER': get_env_or_exit('OIDC_ISSUER'),
        'MATRIX_DATABASE_PASSWORD': get_env_or_exit('MATRIX_DATABASE_PASSWORD'),
        'SYNAPSE_OIDC_CLIENT_SECRET': get_env_or_exit('SYNAPSE_OIDC_CLIENT_SECRET'),
        'MATRIX_ADMIN_USERS': os.environ.get('MATRIX_ADMIN_USERS', ''),
        'MATRIX_BOT_USER_ID': bot_user_id,
        'HOSPITAL_EMAIL': get_env_or_exit('HOSPITAL_EMAIL', 'admin@localhost'),
        'MATRIX_SYNAPSE_PORT': get_env_or_exit('MATRIX_SYNAPSE_PORT', '8008'),
        'MATRIX_ELEMENT_PORT': get_env_or_exit('MATRIX_ELEMENT_PORT', '8080'),
    }


def find_template_files() -> List[Tuple[Path, Path]]:
    """Find all .template files and their target paths."""
    template_files = []
    
    # Define template mappings
    templates = [
        ('matrix/homeserver.yaml.template', 'matrix/homeserver.yaml'),
        ('element/config.json.template', 'element/config.json'),
        ('nginx/matrix.conf.template', 'nginx/matrix.conf'),
        ('nginx/element.conf.template', 'nginx/element.conf'),
    ]
    
    for template_path, target_path in templates:
        template_file = Path(template_path)
        target_file = Path(target_path)
        
        if template_file.exists():
            template_files.append((template_file, target_file))
            logging.debug(f"Found template: {template_file} -> {target_file}")
        else:
            logging.warning(f"Template file not found: {template_file}")
    
    return template_files


def process_template(template_path: Path, target_path: Path, variables: Dict[str, str], dry_run: bool = False) -> bool:
    """Process a single template file."""
    try:
        # Read template content
        with open(template_path, 'r') as f:
            template_content = f.read()
        
        # For nginx configs, use simple string replacement to avoid conflicts with nginx variables
        if str(template_path).startswith('nginx/'):
            rendered_content = template_content
            for key, value in variables.items():
                rendered_content = rendered_content.replace('${' + key + '}', value)
        else:
            # Use Template for other configs
            template = Template(template_content)
            rendered_content = template.substitute(variables)
        
        # Check if target exists and is different
        target_exists = target_path.exists()
        needs_update = True
        
        if target_exists:
            with open(target_path, 'r') as f:
                existing_content = f.read()
            needs_update = existing_content != rendered_content
        
        if not needs_update:
            logging.info(f"✓ {target_path} is up to date")
            return True
        
        if dry_run:
            status = "would be updated" if target_exists else "would be created"
            logging.info(f"[DRY RUN] {target_path} {status}")
            return True
        
        # Create target directory if needed
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write rendered content
        with open(target_path, 'w') as f:
            f.write(rendered_content)
        
        status = "updated" if target_exists else "created"
        logging.info(f"✓ {target_path} {status}")
        return True
        
    except Exception as e:
        logging.error(f"✗ Failed to process {template_path}: {e}")
        return False


def create_required_directories():
    """Create required directories for Matrix and Element."""
    directories = [
        'matrix/logs',
        'element',
        'nginx',
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        logging.debug(f"Created directory: {directory}")


def main():
    parser = argparse.ArgumentParser(description="Generate Matrix configuration files from templates")
    parser.add_argument("--check", action="store_true", help="Check if configs are up to date (dry run)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--env-file", default='.env', help="Path to .env file (default: .env)")
    args = parser.parse_args()

    setup_logging(args.verbose)
    
    logging.info("Matrix Configuration Generator")
    logging.info("=" * 30)
    
    # Load environment file
    env_vars = load_env_file(args.env_file)
    if not env_vars:
        logging.error("No environment variables loaded. Check your .env file.")
        return 1
    
    # Get template variables
    try:
        variables = get_template_vars()
        logging.debug(f"Template variables: {list(variables.keys())}")
    except SystemExit:
        return 1
    
    # Create required directories
    create_required_directories()
    
    # Find template files
    template_files = find_template_files()
    if not template_files:
        logging.warning("No template files found")
        return 0
    
    # Process templates
    success_count = 0
    for template_path, target_path in template_files:
        if process_template(template_path, target_path, variables, dry_run=args.check):
            success_count += 1
    
    # Summary
    total_count = len(template_files)
    if success_count == total_count:
        logging.info(f"✓ Successfully processed {success_count}/{total_count} templates")
        return 0
    else:
        logging.error(f"✗ Processed {success_count}/{total_count} templates")
        return 1


if __name__ == "__main__":
    sys.exit(main())
