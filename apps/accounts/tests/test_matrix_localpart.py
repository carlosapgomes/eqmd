from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.accounts.tests.factories import UserFactory


class UserProfileMatrixLocalpartTests(TestCase):
    def test_matrix_localpart_accepts_valid_value(self):
        profile = UserFactory().profile
        profile.matrix_localpart = "joao.silva"
        profile.full_clean()
        profile.save()
        self.assertEqual(profile.matrix_localpart, "joao.silva")

    def test_matrix_localpart_rejects_invalid_value(self):
        profile = UserFactory().profile
        profile.matrix_localpart = "Joao Silva"
        with self.assertRaises(ValidationError):
            profile.full_clean()

    def test_matrix_localpart_unique(self):
        user1 = UserFactory()
        user1.profile.matrix_localpart = "joao"
        user1.profile.full_clean()
        user1.profile.save()

        user2 = UserFactory()
        user2.profile.matrix_localpart = "joao"
        with self.assertRaises(ValidationError):
            user2.profile.full_clean()

    def test_matrix_localpart_empty_normalizes_to_none(self):
        profile = UserFactory().profile
        profile.matrix_localpart = ""
        profile.full_clean()
        profile.save()
        self.assertIsNone(profile.matrix_localpart)
