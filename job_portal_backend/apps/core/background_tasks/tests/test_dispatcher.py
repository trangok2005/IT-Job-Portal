from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from apps.core.background_tasks.dispatcher import (
    InvalidTaskPayloadError,
    UnknownTaskError,
    dispatch_task,
)


class BackgroundTaskDispatcherTests(SimpleTestCase):
    def test_calls_registered_task_with_keyword_payload(self):
        task = Mock(return_value="result")
        with patch.dict(
            "apps.core.background_tasks.dispatcher.TASK_REGISTRY",
            {"example": task},
            clear=True,
        ):
            result = dispatch_task("example", {"value": 7})

        self.assertEqual(result, "result")
        task.assert_called_once_with(value=7)

    def test_rejects_unknown_task(self):
        with self.assertRaises(UnknownTaskError):
            dispatch_task("unknown", {})

    def test_rejects_non_object_payload(self):
        with patch.dict(
            "apps.core.background_tasks.dispatcher.TASK_REGISTRY",
            {"example": Mock()},
            clear=True,
        ):
            with self.assertRaises(InvalidTaskPayloadError):
                dispatch_task("example", [])

    def test_rejects_missing_or_extra_parameters_before_execution(self):
        task = Mock()

        def registered_task(required_value):
            task(required_value=required_value)

        with patch.dict(
            "apps.core.background_tasks.dispatcher.TASK_REGISTRY",
            {"example": registered_task},
            clear=True,
        ):
            for payload in ({}, {"required_value": 1, "extra": 2}):
                with self.subTest(payload=payload):
                    with self.assertRaises(InvalidTaskPayloadError):
                        dispatch_task("example", payload)

        task.assert_not_called()
