from django.db import connection
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import serializers
from drf_spectacular.utils import extend_schema, inline_serializer


class HealthView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        responses=inline_serializer(
            name="HealthResponse",
            fields={
                "success": serializers.BooleanField(),
                "data": inline_serializer(
                    name="HealthData",
                    fields={
                        "status": serializers.CharField(),
                        "database": serializers.CharField(),
                    },
                ),
            },
        )
    )
    def get(self, request):
        db_ok = True
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except Exception:  # noqa: BLE001
            db_ok = False
        return Response(
            {
                "success": True,
                "data": {
                    "status": "ok",
                    "database": "ok" if db_ok else "error",
                },
            }
        )
