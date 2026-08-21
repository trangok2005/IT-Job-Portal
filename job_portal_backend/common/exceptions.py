from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        detail = response.data.get("detail", response.data)
        response.data = {"success": False, "errors": detail}
    return response