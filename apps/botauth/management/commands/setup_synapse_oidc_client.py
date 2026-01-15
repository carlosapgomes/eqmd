"""
Management command to register Synapse as an OIDC client.

This command is idempotent and can be run multiple times safely.
It will create or update the OIDC client configuration for Matrix Synapse.
"""

import os
import secrets
from django.core.management.base import BaseCommand
from django.db import transaction
from oidc_provider.models import Client


class Command(BaseCommand):
    help = 'Register Matrix Synapse as an OIDC client (idempotent)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--client-id',
            default='matrix_synapse_client',
            help='OIDC client ID for Synapse (default: matrix_synapse_client)'
        )
        parser.add_argument(
            '--matrix-fqdn',
            default=os.getenv('MATRIX_FQDN', 'matrix.yourhospital.com'),
            help='Matrix server FQDN for redirect URI'
        )
        parser.add_argument(
            '--force-new-secret',
            action='store_true',
            help='Generate new client secret even if client exists'
        )

    def handle(self, *args, **options):
        client_id = options['client_id']
        matrix_fqdn = options['matrix_fqdn']
        force_new_secret = options['force_new_secret']
        
        # Construct redirect URI for Synapse OIDC callback
        redirect_uri = f"https://{matrix_fqdn}/_synapse/client/oidc/callback"
        
        self.stdout.write(f"Setting up OIDC client for Matrix Synapse...")
        self.stdout.write(f"Client ID: {client_id}")
        self.stdout.write(f"Matrix FQDN: {matrix_fqdn}")
        self.stdout.write(f"Redirect URI: {redirect_uri}")
        
        with transaction.atomic():
            # Check if client already exists
            client, created = Client.objects.get_or_create(
                client_id=client_id,
                defaults={
                    'name': 'Matrix Synapse OIDC',
                    'client_type': 'confidential',
                    'jwt_alg': 'HS256',
                    'require_consent': False,  # Skip consent screen for SSO
                    'reuse_consent': True,
                }
            )
            
            # Generate new client secret if needed
            if created or force_new_secret:
                client.client_secret = secrets.token_urlsafe(32)
                client.save()
                secret_status = "generated new"
            else:
                secret_status = "using existing"
            
            # Update/set redirect URIs (idempotent)
            current_uris = client.redirect_uris
            if redirect_uri not in current_uris:
                if current_uris:
                    client.redirect_uris = f"{current_uris} {redirect_uri}"
                else:
                    client.redirect_uris = redirect_uri
                client.save()
                uri_status = "added new redirect URI"
            else:
                uri_status = "redirect URI already configured"
            
            # Set allowed scopes for Synapse SSO
            client.scopes = ['openid', 'profile', 'email']
            client.save()
        
        # Output results
        if created:
            self.stdout.write(
                self.style.SUCCESS(f"✓ Created new OIDC client '{client_id}'")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"✓ Found existing OIDC client '{client_id}'")
            )
        
        self.stdout.write(f"  - Client secret: {secret_status}")
        self.stdout.write(f"  - Redirect URI: {uri_status}")
        self.stdout.write(f"  - Allowed scopes: {client.scopes}")
        
        # Show configuration details
        self.stdout.write(self.style.WARNING("\nSynapse Configuration:"))
        self.stdout.write("Add these settings to your Synapse homeserver.yaml:")
        self.stdout.write("")
        self.stdout.write("oidc_providers:")
        self.stdout.write("  - idp_id: equipemed")
        self.stdout.write("    idp_name: \"EquipeMed\"")
        self.stdout.write("    discover: true")
        self.stdout.write(f"    issuer: \"{os.getenv('OIDC_ISSUER', 'https://yourhospital.com/o')}\"")
        self.stdout.write(f"    client_id: \"{client.client_id}\"")
        self.stdout.write(f"    client_secret: \"{client.client_secret}\"")
        self.stdout.write("    scopes: [\"openid\", \"profile\", \"email\"]")
        self.stdout.write("    allow_existing_users: true")
        self.stdout.write("    user_mapping_provider:")
        self.stdout.write("      config:")
        self.stdout.write("        localpart_template: \"u_{{ user.sub }}\"")
        self.stdout.write("        display_name_template: \"{{ user.name | default(user.preferred_username) }}\"")
        self.stdout.write("        email_template: \"{{ user.email }}\"")
        self.stdout.write("")
        
        # Environment variable suggestions  
        self.stdout.write(self.style.WARNING("Environment Variables:"))
        self.stdout.write("Add to your .env file:")
        self.stdout.write(f"SYNAPSE_OIDC_CLIENT_SECRET={client.client_secret}")
        self.stdout.write("")
        
        self.stdout.write(
            self.style.SUCCESS("✓ Synapse OIDC client setup complete!")
        )