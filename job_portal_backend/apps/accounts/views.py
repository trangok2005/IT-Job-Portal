"""Các view gọn cho đăng ký, OAuth và quản trị tài khoản."""
from rest_framework import status
from rest_framework.generics import CreateAPIView, ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView
from drf_spectacular.utils import extend_schema

from apps.accounts import selectors, serializers, services
from common import permissions as common_permissions


class RegisterView(CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = serializers.RegisterSerializer

    @extend_schema(responses={201: serializers.UserSerializer})

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = services.create_registered_user(serializer.validated_data)
        return Response(
            serializers.UserSerializer(user).data, status=status.HTTP_201_CREATED
        )


class MeView(RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = serializers.UserSerializer

    def get_object(self):
        return self.request.user


class GoogleAuthView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=serializers.GoogleAuthSerializer,
        responses=serializers.GoogleAuthResponseSerializer,
    )
    def post(self, request):
        """Xác minh danh tính Google, tạo user khi cần và trả về JWT."""
        serializer = serializers.GoogleAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        claims = services.verify_google_token(serializer.validated_data["id_token"])
        user = services.login_or_register_google(
            claims,
            serializer.validated_data["role"],
            serializer.validated_data.get("company_name", ""),
        )
        tokens = services.issue_token_pair(user)
        return Response({**tokens, "user": serializers.UserSerializer(user).data})


class ActiveUserTokenRefreshView(TokenRefreshView):
    serializer_class = serializers.ActiveUserTokenRefreshSerializer


class AdminUserListView(ListAPIView):
    permission_classes = [IsAuthenticated, common_permissions.IsAdmin]
    serializer_class = serializers.UserSerializer

    @extend_schema(parameters=[serializers.AdminUserListQuerySerializer])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        # A missing BooleanField in a QueryDict is interpreted like an unchecked
        # HTML checkbox (False). A plain dict preserves "filter not supplied".
        query = serializers.AdminUserListQuerySerializer(
            data=self.request.query_params.dict()
        )
        query.is_valid(raise_exception=True)
        return selectors.get_users(**query.validated_data)


class AdminUserLockView(APIView):
    permission_classes = [IsAuthenticated, common_permissions.IsAdmin]
    locked = True

    @extend_schema(request=None, responses=serializers.UserSerializer)
    def post(self, request, user_id):
        """Áp dụng trạng thái khóa được yêu cầu qua service tài khoản."""
        target = selectors.get_manageable_user(user_id)
        if target is None:
            from rest_framework.exceptions import NotFound

            raise NotFound("Không tìm thấy tài khoản.")
        user = services.set_user_lock(request.user, target, self.locked)
        return Response(serializers.UserSerializer(user).data)


class AdminUserUnlockView(AdminUserLockView):
    locked = False
