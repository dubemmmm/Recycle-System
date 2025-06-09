from django.urls import path
from . import views
app_name = 'recycle'


urlpatterns = [
    path('home', views.HomeView.as_view(), name='home'),
    path('upload', views.UploadView.as_view(), name='upload'),
    path('results/<int:pk>/', views.ResultsView.as_view(), name='results'),
    path('view/<int:pk>/', views.ViewUploadView.as_view(), name='view_upload'),
    path('download/<int:pk>/', views.DownloadUploadView.as_view(), name='download_upload'),
    path('delete/<int:pk>/', views.DeleteUploadView.as_view(), name='delete_upload'),
    path('calendar/<int:year>/<int:month>/', views.CalendarView.as_view(), name='calendar'),
    path('export-report/', views.ExportReportView.as_view(), name='export_report'),
    path('download-instructions/<int:pk>/', views.DownloadInstructionsView.as_view(), name='download_instructions'),
]
