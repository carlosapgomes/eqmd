"""
Management command to register Synapse as an OIDC client.

This command is idempotent and can be run multiple times safely.
It will create or update the OIDC client configuration for Matrix Synapse.
"""

import os
import secrets
from django.core.management.base import BaseCommand
from django.db import transaction
from oidc_provider.models import Client, ResponseType


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
                    'jwt_alg': 'RS256',
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

            # Ensure RS256 signing for Synapse so JWKS is used for validation
            if getattr(client, "jwt_alg", None) != "RS256":
                client.jwt_alg = "RS256"
                client.save(update_fields=["jwt_alg"])
            
            # Update/set redirect URIs (idempotent, list or string field)
            redirect_field = "_redirect_uris" if hasattr(client, "_redirect_uris") else "redirect_uris"
            current_uris = getattr(client, redirect_field)
            is_list_field = isinstance(current_uris, (list, tuple))
            normalized_uris = []
            was_char_list = False
            if is_list_field:
                if current_uris and all(isinstance(item, str) and len(item) == 1 for item in current_uris):
                    # Stored as list of characters; reconstruct
                    normalized_uris = ["".join(current_uris)]
                    was_char_list = True
                else:
                    normalized_uris = [uri for uri in current_uris if uri]
            elif isinstance(current_uris, str):
                normalized_uris = [uri for uri in current_uris.split() if uri]

            needs_update = was_char_list
            if redirect_uri not in normalized_uris:
                normalized_uris.append(redirect_uri)
                needs_update = True

            if needs_update:
                if is_list_field:
                    setattr(client, redirect_field, normalized_uris)
                else:
                    setattr(client, redirect_field, " ".join(normalized_uris))
                client.save()
                uri_status = "added new redirect URI"
            else:
                uri_status = "redirect URI already configured"

            # Set allowed scopes for Synapse SSO
            scope_value = "openid profile email"
            if hasattr(client, "_scope"):
                client._scope = scope_value
            elif hasattr(client, "scope"):
                client.scope = scope_value
            client.save()

            # Ensure response type includes authorization code
            try:
                code_response, _ = ResponseType.objects.get_or_create(
                    value="code",
                    defaults={"description": "Authorization code"},
                )
                client.response_types.add(code_response)
            except Exception:
                pass
        
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
        scope_display = getattr(client, "_scope", None) or getattr(client, "scope", None) or scope_value
        self.stdout.write(f"  - Allowed scopes: {scope_display}")
        
        # Show configuration details
        provider_id = os.getenv("SYNAPSE_OIDC_PROVIDER_ID", "equipemed")
        self.stdout.write(self.style.WARNING("\nSynapse Configuration:"))
        self.stdout.write("Add these settings to your Synapse homeserver.yaml:")
        self.stdout.write("")
        self.stdout.write("oidc_providers:")
        self.stdout.write(f"  - idp_id: {provider_id}")
        self.stdout.write("    idp_name: \"EquipeMed\"")
        self.stdout.write("    discover: true")
        self.stdout.write(f"    issuer: \"{os.getenv('OIDC_ISSUER', 'https://yourhospital.com/o')}\"")
        self.stdout.write(f"    client_id: \"{client.client_id}\"")
        self.stdout.write(f"    client_secret: \"{client.client_secret}\"")
        self.stdout.write("    scopes: [\"openid\", \"profile\", \"email\"]")
        self.stdout.write("    allow_existing_users: true")
        self.stdout.write("    allow_new_users: false")
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
        self.stdout.write(f"SYNAPSE_OIDC_PROVIDER_ID={provider_id}")
        self.stdout.write("")
        
        self.stdout.write(
            self.style.SUCCESS("✓ Synapse OIDC client setup complete!")
        )
