from django.test import SimpleTestCase, override_settings

from integrations.storage import create_private_file_url


class PrivateR2StorageTests(SimpleTestCase):
    @override_settings(PRIVATE_FILE_URL_TTL_SECONDS=120)
    def test_signed_storage_receives_configured_expiry(self):
        class Storage:
            querystring_auth = True

            def __init__(self):
                self.expire = None

            def url(self, name, *, expire):
                self.expire = expire
                return f"https://r2.example/{name}?signed=true"

        storage = Storage()
        file_field = type(
            "FileField",
            (),
            {"storage": storage, "name": "resumes/cv.pdf"},
        )()

        result = create_private_file_url(file_field)

        self.assertEqual(storage.expire, 120)
        self.assertEqual(result["url"], "https://r2.example/resumes/cv.pdf?signed=true")
