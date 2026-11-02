"""Read-only audit of clinical identity integrity (D4).

Reports three gap kinds without modifying any database row:

1. active users without ``profession_type`` (superusers and
   ``User Managers`` members excluded);
2. profession groups whose permission set drifted from the
   ``setup_groups`` specification;
3. non-exempt users in no profession group (any activation state).

Repair stays a human/admin action: no silent permission mutation in a
clinical system.
"""

from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db.models import Q

from apps.core.management.commands.setup_groups import Command as SetupGroupsCommand

USER_MANAGERS_GROUP_NAME = "User Managers"

# Group name -> permission getter on the setup_groups command. Reusing the
# command getters keeps the audit's expected set identical to the set that
# setup_groups assigns; the audit only reads.
PROFESSION_GROUPS = (
    ("Medical Doctors", "_get_doctor_permissions"),
    ("Residents", "_get_resident_permissions"),
    ("Nurses", "_get_nurse_permissions"),
    ("Physiotherapists", "_get_physiotherapist_permissions"),
    ("Students", "_get_student_permissions"),
)


class Command(BaseCommand):
    help = "Audit clinical identity gaps read-only (modifies nothing)."

    def handle(self, *args, **options):
        user_model = get_user_model()
        exempt_user_ids = self._exempt_user_ids(user_model)

        null_profession_users = list(
            self._null_profession_users(user_model, exempt_user_ids)
        )
        ungrouped_users = list(
            self._ungrouped_users(user_model, exempt_user_ids)
        )
        group_drift = self._group_drift()

        self._write_report(null_profession_users, group_drift, ungrouped_users)

    def _exempt_user_ids(self, user_model):
        return user_model.objects.filter(
            Q(is_superuser=True) | Q(groups__name=USER_MANAGERS_GROUP_NAME)
        ).values_list("pk", flat=True)

    def _null_profession_users(self, user_model, exempt_user_ids):
        return (
            user_model.objects.filter(is_active=True, profession_type__isnull=True)
            .exclude(pk__in=exempt_user_ids)
            .order_by("username")
        )

    def _ungrouped_users(self, user_model, exempt_user_ids):
        profession_group_names = [name for name, _getter in PROFESSION_GROUPS]
        grouped_user_ids = user_model.objects.filter(
            groups__name__in=profession_group_names
        ).values_list("pk", flat=True)
        return (
            user_model.objects.exclude(pk__in=exempt_user_ids)
            .exclude(pk__in=grouped_user_ids)
            .order_by("username")
        )

    def _group_drift(self):
        setup_command = SetupGroupsCommand(stdout=StringIO(), stderr=StringIO())
        drift = []
        for group_name, permission_getter_name in PROFESSION_GROUPS:
            expected = set(getattr(setup_command, permission_getter_name)())
            try:
                group = Group.objects.get(name=group_name)
            except Group.DoesNotExist:
                detail = (
                    "group does not exist "
                    f"(expected {len(expected)} permissions)"
                )
                drift.append((group_name, detail))
                continue
            actual = {
                f"{permission.content_type.app_label}.{permission.codename}"
                for permission in group.permissions.select_related("content_type")
            }
            missing = sorted(expected - actual)
            if missing:
                drift.append((group_name, f"missing {', '.join(missing)}"))
        return drift

    def _write_report(self, null_profession_users, group_drift, ungrouped_users):
        self.stdout.write("Clinical identity audit (read-only)")
        self.stdout.write("===================================")
        self.stdout.write("")
        self.stdout.write(
            f"1) Active users without profession_type "
            f"({len(null_profession_users)})"
        )
        for user in null_profession_users:
            self.stdout.write(
                f"   - {user.username} (id={user.pk}, email={user.email or '-'})"
            )
        self.stdout.write("")
        self.stdout.write(
            f"2) Profession groups missing expected permissions "
            f"({len(group_drift)})"
        )
        for group_name, detail in group_drift:
            self.stdout.write(f"   - {group_name}: {detail}")
        self.stdout.write("")
        self.stdout.write(
            f"3) Non-exempt users in no profession group "
            f"({len(ungrouped_users)})"
        )
        for user in ungrouped_users:
            profession = (
                user.get_profession_type_display()
                if user.profession_type is not None
                else "none"
            )
            self.stdout.write(f"   - {user.username} (profession: {profession})")
        self.stdout.write("")
        self.stdout.write("No database rows were modified.")
