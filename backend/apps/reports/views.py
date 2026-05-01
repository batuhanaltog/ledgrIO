import os
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.viewsets import ReadOnlyModelViewSet
from django.http import FileResponse, Http404
from drf_spectacular.utils import extend_schema_view, extend_schema

from .models import Report
from .serializers import ReportSerializer, GenerateReportSerializer


@extend_schema_view(
    list=extend_schema(tags=["Reports"]),
    retrieve=extend_schema(tags=["Reports"]),
)
class ReportViewSet(ReadOnlyModelViewSet):
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Report.objects.filter(user=self.request.user)

    @extend_schema(tags=["Reports"])
    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        report = self.get_object()
        if report.status != Report.Status.COMPLETE or not report.file_path:
            return Response({"detail": "Report not ready."}, status=status.HTTP_400_BAD_REQUEST)
        if not os.path.exists(report.file_path):
            raise Http404
        return FileResponse(open(report.file_path, "rb"), as_attachment=True, filename=os.path.basename(report.file_path))


@extend_schema(tags=["Reports"])
class GenerateReportView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = GenerateReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        report = Report.objects.create(
            user=request.user,
            report_type=data["report_type"],
            format=data["format"],
            parameters={
                "date_from": str(data.get("date_from", "2000-01-01")),
                "date_to": str(data.get("date_to", "2099-12-31")),
                "portfolio_id": str(data["portfolio_id"]) if data.get("portfolio_id") else None,
            },
        )

        from celery_app.tasks.report_tasks import generate_report_task
        generate_report_task.delay(str(report.id))

        return Response(ReportSerializer(report).data, status=status.HTTP_201_CREATED)
