from django.urls import path
from . import views

app_name = 'pdfgenerator'

urlpatterns = [
    path('prescription/', views.PrescriptionPDFView.as_view(), name='prescription_pdf'),
    path('discharge-report/', views.DischargeReportPDFView.as_view(), name='discharge_report_pdf'),
    path('exam-request/', views.ExamRequestPDFView.as_view(), name='exam_request_pdf'),
]