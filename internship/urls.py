from django.urls import path
from . import views
from .views import performance_view


urlpatterns = [
    path('',views.home, name='home'),
    # path('sitelogin/', views.sitelogin, name='sitelogin'),
    # path('logout/', views.logout_view, name='logout'),

    path("server-stats/", performance_view, name="performance"),

    # path("student/upload/documents/", views.upload_student_documents, name="upload_documents"),
    path("downloadable-files/", views.downloadable_files_view, name="downloadable_files"),
    path("batch/create/", views.create_batch, name="create_batch"),
    
    path("api/students/", views.get_students_same_year, name="get_students_same_year"),
    path('guides/', views.guide_list, name='guide_list'),
    path('request-guide/<int:guide_id>/', views.request_guide, name='request_guide'),
    path('guide/dashboard/', views.guide_dashboard, name='guide_dashboard'),
    path('guide/request/<int:req_id>/<str:action>/', views.handle_request, name='handle_request'),
    
]


