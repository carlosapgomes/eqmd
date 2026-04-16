from django.test import SimpleTestCase

from apps.core.utils.cache import apply_client_side_filters


class CacheFilterUtilsTests(SimpleTestCase):
    def test_apply_client_side_filters_matches_patient_name_without_accents(self):
        ward_data = [
            {
                "ward": {"id": "1", "name": "UTI"},
                "patient_count": 1,
                "patients": [
                    {
                        "patient": {"name": "João da Silva"},
                        "bed": "101",
                        "tags": [],
                    }
                ],
            }
        ]

        filtered = apply_client_side_filters(ward_data, {"q": "joao"})

        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["patient_count"], 1)
        self.assertEqual(filtered[0]["patients"][0]["patient"]["name"], "João da Silva")
