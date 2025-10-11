from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView
from internship.views import account_dashboard
from django.shortcuts import redirect


def redirect_to_dashboard(request):
    return redirect('account_dashboard')


urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', TemplateView.as_view(template_name="internship/site_login.html"), name="custom_login"),
    path('dashboard/', account_dashboard, name='account_dashboard'),
    path('accounts/email/', redirect_to_dashboard, name='account_email_override'),
    path('accounts/email/', redirect_to_dashboard),
    path('accounts/password/change/', redirect_to_dashboard),
    path('accounts/3rdparty/signup/', redirect_to_dashboard),
    path('accounts/3rdparty/', redirect_to_dashboard),
    # path('accounts/google/login/callback/', redirect_to_dashboard),
    path('accounts/password/set/', redirect_to_dashboard),
    path('accounts/social/connections/', redirect_to_dashboard),
    path("accounts/", include("allauth.urls")),  # allauth routes
    path('', include('internship.urls')),  # Routes to app-level urls.py

]
handler404 = "internship.views.handler404"
handler500 = "internship.views.handler500"
handler403 = "internship.views.handler403"
handler400 = "internship.views.handler400"
