"""Role-specific dashboard response shapes."""
from rest_framework import serializers

from apps.jobs.serializers import RecommendedJobSerializer


class CandidateDashboardSerializer(serializers.Serializer):
    profile_completion = serializers.IntegerField()
    application_count = serializers.IntegerField()
    application_status_counts = serializers.DictField(child=serializers.IntegerField())
    recommended_jobs = RecommendedJobSerializer(many=True)


class EmployerDashboardSerializer(serializers.Serializer):
    company_status = serializers.CharField(allow_null=True)
    jobs_total = serializers.IntegerField()
    jobs_active = serializers.IntegerField()
    jobs_draft = serializers.IntegerField()
    new_applications = serializers.IntegerField()
    total_applications = serializers.IntegerField()


class AdminDashboardSerializer(serializers.Serializer):
    users_total = serializers.IntegerField()
    users_active = serializers.IntegerField()
    pending_companies = serializers.IntegerField()
    active_jobs = serializers.IntegerField()
    applications = serializers.IntegerField()
    pending_skills = serializers.IntegerField()
