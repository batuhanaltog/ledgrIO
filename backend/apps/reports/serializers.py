from rest_framework import serializers
from .models import Report


class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = [
            "id", "report_type", "format", "status", "parameters",
            "file_path", "error_message", "requested_at", "completed_at",
        ]
        read_only_fields = ["id", "status", "file_path", "error_message", "requested_at", "completed_at"]


class GenerateReportSerializer(serializers.Serializer):
    report_type = serializers.ChoiceField(choices=Report.ReportType.choices)
    format = serializers.ChoiceField(choices=Report.Format.choices)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    portfolio_id = serializers.UUIDField(required=False)
