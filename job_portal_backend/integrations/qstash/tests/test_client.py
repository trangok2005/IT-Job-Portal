from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from integrations.qstash.client import (
    QStashConfigurationError,
    get_qstash_client,
    get_qstash_receiver,
)


class QStashClientTests(SimpleTestCase):
    def tearDown(self):
        get_qstash_client.cache_clear()
        get_qstash_receiver.cache_clear()

    @override_settings(
        QSTASH_DEV=True,
        QSTASH_URL="http://127.0.0.1:8080",
        QSTASH_TOKEN="",
        QSTASH_CURRENT_SIGNING_KEY="",
        QSTASH_NEXT_SIGNING_KEY="",
    )
    @patch("qstash.Receiver")
    @patch("qstash.QStash")
    def test_dev_mode_uses_local_url_and_default_credentials(
        self, qstash_class, receiver_class
    ):
        first_client = get_qstash_client()
        second_client = get_qstash_client()
        first_receiver = get_qstash_receiver()
        second_receiver = get_qstash_receiver()

        self.assertIs(first_client, second_client)
        self.assertIs(first_receiver, second_receiver)
        qstash_class.assert_called_once()
        self.assertTrue(qstash_class.call_args.args[0])
        self.assertEqual(
            qstash_class.call_args.kwargs["base_url"], "http://127.0.0.1:8080"
        )
        receiver_class.assert_called_once()
        self.assertTrue(receiver_class.call_args.kwargs["current_signing_key"])
        self.assertTrue(receiver_class.call_args.kwargs["next_signing_key"])

    @override_settings(
        QSTASH_DEV=False,
        QSTASH_TOKEN="cloud-token",
        QSTASH_CURRENT_SIGNING_KEY="current-key",
        QSTASH_NEXT_SIGNING_KEY="next-key",
    )
    @patch("qstash.Receiver")
    @patch("qstash.QStash")
    def test_cloud_mode_uses_configured_credentials(
        self, qstash_class, receiver_class
    ):
        get_qstash_client()
        get_qstash_receiver()

        qstash_class.assert_called_once_with("cloud-token", base_url=None)
        receiver_class.assert_called_once_with(
            current_signing_key="current-key",
            next_signing_key="next-key",
        )

    @override_settings(QSTASH_DEV=False, QSTASH_TOKEN="")
    def test_cloud_mode_requires_token(self):
        with self.assertRaisesMessage(QStashConfigurationError, "QSTASH_TOKEN"):
            get_qstash_client()

    @override_settings(
        QSTASH_DEV=False,
        QSTASH_CURRENT_SIGNING_KEY="",
        QSTASH_NEXT_SIGNING_KEY="next-key",
    )
    def test_cloud_mode_requires_current_signing_key(self):
        with self.assertRaisesMessage(
            QStashConfigurationError, "QSTASH_CURRENT_SIGNING_KEY"
        ):
            get_qstash_receiver()

    @override_settings(
        QSTASH_DEV=False,
        QSTASH_CURRENT_SIGNING_KEY="current-key",
        QSTASH_NEXT_SIGNING_KEY="",
    )
    def test_cloud_mode_requires_next_signing_key(self):
        with self.assertRaisesMessage(
            QStashConfigurationError, "QSTASH_NEXT_SIGNING_KEY"
        ):
            get_qstash_receiver()
