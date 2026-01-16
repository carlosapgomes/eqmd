import json
import os
import secrets
import urllib.error
import urllib.parse
import urllib.request

from dataclasses import dataclass
from django.utils import timezone

from apps.botauth.models import MatrixUserBinding
from apps.botauth.services import MatrixBindingService


class MatrixApiError(RuntimeError):
    pass


class MatrixProvisioningError(RuntimeError):
    pass


@dataclass
class MatrixConfig:
    matrix_fqdn: str
    admin_base_url: str
    client_base_url: str
    admin_token: str
    oidc_provider_id: str
    bot_user_id: str
    bot_access_token: str
    global_room_name: str

    @classmethod
    def from_env(cls):
        matrix_fqdn = os.getenv("MATRIX_FQDN", "matrix.local")
        admin_base_url = os.getenv("MATRIX_ADMIN_INTERNAL_URL", "http://matrix-synapse:8008")
        client_base_url = os.getenv("MATRIX_CLIENT_INTERNAL_URL", "http://matrix-synapse:8008")
        admin_token = os.getenv("SYNAPSE_ADMIN_TOKEN", "")
        oidc_provider_id = os.getenv("SYNAPSE_OIDC_PROVIDER_ID", "equipemed")
        bot_user_id = os.getenv("MATRIX_BOT_USER_ID", f"@rzero_bot:{matrix_fqdn}")
        bot_access_token = os.getenv("MATRIX_BOT_ACCESS_TOKEN", "")
        global_room_name = os.getenv("MATRIX_GLOBAL_ROOM_NAME", "EquipeMed - Todos")
        return cls(
            matrix_fqdn=matrix_fqdn,
            admin_base_url=admin_base_url,
            client_base_url=client_base_url,
            admin_token=admin_token,
            oidc_provider_id=oidc_provider_id,
            bot_user_id=bot_user_id,
            bot_access_token=bot_access_token,
            global_room_name=global_room_name,
        )


class MatrixHttpClient:
    def __init__(self, base_url, token=None, timeout=15):
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._timeout = timeout

    def request(self, method, path, payload=None, token=None):
        url = f"{self._base_url}{path}"
        headers = {}
        auth_token = token or self._token
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8")
            raise MatrixApiError(
                f"{method} {url} failed: {exc.code} {error_body}"
            ) from exc
        if not body:
            return {}
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {"raw": body}


class SynapseAdminClient:
    def __init__(self, config: MatrixConfig):
        self._client = MatrixHttpClient(config.admin_base_url, config.admin_token)

    def get_user(self, user_id):
        encoded = urllib.parse.quote(user_id, safe="")
        return self._client.request("GET", f"/_synapse/admin/v2/users/{encoded}")

    def ensure_user(self, user_id, display_name=None, admin=False, deactivated=False, external_ids=None):
        encoded = urllib.parse.quote(user_id, safe="")
        payload = {
            "admin": admin,
            "deactivated": deactivated,
            "password": secrets.token_urlsafe(32),
        }
        if display_name:
            payload["displayname"] = display_name
        if external_ids:
            payload["external_ids"] = external_ids
        return self._client.request("PUT", f"/_synapse/admin/v2/users/{encoded}", payload)

    def deactivate_user(self, user_id, erase=False):
        encoded = urllib.parse.quote(user_id, safe="")
        payload = {"erase": erase}
        return self._client.request(
            "POST", f"/_synapse/admin/v1/deactivate/{encoded}", payload
        )

    def reactivate_user(self, user_id, display_name=None, external_ids=None):
        return self.ensure_user(
            user_id,
            display_name=display_name,
            deactivated=False,
            external_ids=external_ids,
        )

    def create_login_token(self, user_id):
        encoded = urllib.parse.quote(user_id, safe="")
        return self._client.request("POST", f"/_synapse/admin/v2/users/{encoded}/login")


class MatrixClient:
    def __init__(self, config: MatrixConfig):
        self._client = MatrixHttpClient(config.client_base_url, config.bot_access_token)

    def create_room(self, payload):
        return self._client.request("POST", "/_matrix/client/v3/createRoom", payload)

    def invite_user(self, room_id, user_id):
        encoded = urllib.parse.quote(room_id, safe="")
        payload = {"user_id": user_id}
        return self._client.request(
            "POST", f"/_matrix/client/v3/rooms/{encoded}/invite", payload
        )

    def kick_user(self, room_id, user_id, reason=None):
        encoded = urllib.parse.quote(room_id, safe="")
        payload = {"user_id": user_id}
        if reason:
            payload["reason"] = reason
        return self._client.request(
            "POST", f"/_matrix/client/v3/rooms/{encoded}/kick", payload
        )


def build_external_ids(user, oidc_provider_id):
    try:
        profile = user.profile
    except Exception:
        return None
    if not getattr(profile, "public_id", None):
        return None
    if not oidc_provider_id:
        return None
    return [
        {
            "auth_provider": oidc_provider_id,
            "external_id": str(profile.public_id),
        }
    ]


def build_matrix_user_id(user, matrix_fqdn):
    localpart = None
    try:
        localpart = user.profile.matrix_localpart
    except Exception:
        localpart = None

    if not localpart:
        public_id = None
        try:
            public_id = user.profile.public_id
        except Exception:
            public_id = None

        if public_id:
            localpart = f"u_{public_id}"
        else:
            localpart = f"u_{user.pk}"

    return f"@{localpart}:{matrix_fqdn}"


class MatrixProvisioningService:
    @classmethod
    def provision_user(cls, user, config, performed_by=None):
        if not config.admin_token:
            raise MatrixProvisioningError("SYNAPSE_ADMIN_TOKEN is required")

        try:
            profile = user.profile
        except Exception:
            from apps.accounts.models import UserProfile

            profile, _ = UserProfile.objects.get_or_create(user=user)

        if not profile.matrix_localpart:
            raise MatrixProvisioningError("Matrix localpart is required before provisioning")

        matrix_user_id = build_matrix_user_id(user, config.matrix_fqdn)
        display_name = display_name_for_user(user)
        external_ids = build_external_ids(user, config.oidc_provider_id)
        if not external_ids:
            raise MatrixProvisioningError("SYNAPSE_OIDC_PROVIDER_ID is required")

        admin_client = SynapseAdminClient(config)
        admin_client.ensure_user(
            matrix_user_id,
            display_name=display_name,
            external_ids=external_ids,
        )

        binding = MatrixUserBinding.objects.filter(user=user).first()
        if binding and binding.matrix_id != matrix_user_id:
            raise MatrixProvisioningError(
                f"User already has a different Matrix binding: {binding.matrix_id}"
            )
        if not binding:
            try:
                binding, _ = MatrixBindingService.create_binding(user, matrix_user_id)
            except ValueError as exc:
                raise MatrixProvisioningError(str(exc)) from exc
        if not binding.verified:
            MatrixBindingService.verify_binding(binding)

        profile.matrix_provisioned_at = timezone.now()
        if performed_by:
            profile.matrix_provisioned_by = performed_by
        profile.save(update_fields=["matrix_provisioned_at", "matrix_provisioned_by"])

        return matrix_user_id


def display_name_for_user(user):
    full_name = user.get_full_name()
    if full_name.strip():
        return full_name
    return user.email or user.username
