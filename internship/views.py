from django.shortcuts import render, redirect, get_object_or_404
from .models import  Announcement , downloadable_files , SiteSetting
from django.contrib import messages
from django.db import transaction, IntegrityError
from django.db.models import F
from django.http import JsonResponse
import psutil
import os
from django.core.mail import send_mail
import random
from django.conf import settings
import gspread
from google.oauth2.service_account import Credentials
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, get_object_or_404, redirect
import re
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
import cloudinary.uploader
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
import datetime
from django.db.models import Q
import json
from django.http import JsonResponse, HttpResponseBadRequest

# Setup Google credentials
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(settings.GOOGLE_CONFIG, scopes=SCOPES)
client = gspread.authorize(creds)
sheet = client.open_by_key(settings.GOOGLE_SHEET_ID).sheet1


def home(request):
    if request.user.is_authenticated:
        username = request.user.username
        name = request.user.first_name
        email = request.user.email
        rollno = email.split("@")[0]

        if rollno.startswith("vtu") and rollno[3:].isdigit():
            Vtu_number = rollno[3:]   # only the numbers
        else:
            Vtu_number = None

        announcement = Announcement.objects.first()

        # check admin
        is_admin = request.user.is_superuser or request.user.is_staff

        return render(
            request,
            "internship/home.html",
            {
                "rollno": rollno,
                "announcement": announcement,
                "name": name,
                "email": email,
                "username": username,
                "Vtu_number": Vtu_number,
                "path": request.path,
                "is_admin": is_admin,   # pass to template
            },
        )

# def sitelogin(request):
#     return render(request, 'internship/site_login.html')

@login_required
def account_dashboard(request):
    if request.user.is_authenticated:
        username = request.user.username
        name = request.user.first_name
        email = request.user.email
        rollno = email.split("@")[0]

        if rollno.startswith("vtu") and rollno[3:].isdigit():
            Vtu_number = rollno[3:]   # only the numbers
        else:
            Vtu_number = None


        # check admin
        is_admin = request.user.is_superuser or request.user.is_staff
        
        # Check Student model
        

        site_settings = SiteSetting.objects.first()

        return render(
            request,
            "internship/dashboard.html",
            {
                "rollno": rollno,
                "name": name,
                "email": email,
                "username": username,
                "Vtu_number": Vtu_number,
                "path": request.path,
                "is_admin": is_admin,   # pass to template
                "site_setting": site_settings,
            },
        )




def performance_view(request):
    pid = os.getpid()
    process = psutil.Process(pid)

    cpu = process.cpu_percent(interval=0.5)
    memory = process.memory_info().rss / 1024 ** 2  # in MB

    return JsonResponse({
        "cpu_usage_percent": f"{cpu:.2f}",
        "memory_usage_mb": f"{memory:.2f}"
    })




def csrf_failure(request, reason=""):
    path = request.path

    if path.startswith("/company/login/") or path.startswith("/company/attendance/"):
        # Company-specific CSRF failure page
        return render(request, "internship/csrf_failure.html", status=403)

    # Default/common CSRF failure page
    return render(request, "internship/common_csrf_failure.html", status=403)


def handler404(request, exception):
    return render(request, "errors/404.html", status=404)

def handler500(request):
    return render(request, "errors/500.html", status=500)

def handler403(request, exception=None):
    return render(request, "errors/403.html", status=403)

def handler400(request, exception):
    return render(request, "errors/400.html", status=400)





MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB in bytes (2097152)

def extract_roll_from_email(email):
    match = re.search(r"\d+", email)
    return match.group() if match else None

def downloadable_files_view(request):
    files = downloadable_files.objects.all()
    return render(request, 'internship/downloadable_files.html', {'files': files})


@login_required
def create_batch(request):
    user_email = request.user.email
    # Get VTU number from email (ex: vtu24875@veltech.edu.in)
    match = re.search(r'vtu(\d+)', user_email, re.IGNORECASE)
    vtu_num = f"VTU{match.group(1)}" if match else None

    try:
        current_student = dept_member.objects.get(email=user_email)
    except dept_member.DoesNotExist:
        return HttpResponseBadRequest("You are not registered in AIML Department.")

    if request.method == "POST":
        data = request.POST
        members_json = data.get("members_json", "[]")
        members_list = json.loads(members_json)

        if len(members_list) + 1 > 5:
            return HttpResponseBadRequest("Maximum 5 members allowed (including you).")

        # Collect student data
        students = dept_member.objects.filter(vtu_number__in=members_list)
        if students.filter(year=current_student.year).count() != len(members_list):
            return HttpResponseBadRequest("All members must be from the same year.")

        # Save Batch
        batch = batch.objects.create(
            Student1_name=current_student.name,
            Student1_vtu=current_student.vtu_number,
            project_title=data.get("project_title"),
            project_oneliner=data.get("project_oneliner"),
            project_abstract=data.get("project_abstract"),
        )

        # Fill additional student slots dynamically
        for i, member in enumerate(students, start=2):
            setattr(batch, f"Student{i}_name", member.name)
            setattr(batch, f"Student{i}_vtu", member.vtu_number)
        batch.save()

        return redirect("batch_success")  # You can replace with your success page

    return render(request, "internship/create_batch.html", {"student": current_student})


@login_required
def get_students_same_year(request):
    """Return same-year students (except current user)"""
    try:
        student = dept_member.objects.get(email=request.user.email)
    except dept_member.DoesNotExist:
        return JsonResponse({"students": []})

    same_year_students = dept_member.objects.filter(
        year=student.year, role="Student"
    ).exclude(email=request.user.email)

    data = [
        {"name": s.name, "vtu": s.vtu_number, "email": s.email}
        for s in same_year_students
    ]
    return JsonResponse({"students": data})


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import batch, Guide, GuideRequest, dept_member

@login_required
def guide_list(request):
    guides = Guide.objects.all()
    return render(request, 'student/guide_list.html', {'guides': guides})

@login_required
def request_guide(request, guide_id):
    student_email = request.user.email
    try:
        student = dept_member.objects.get(email=student_email)
    except dept_member.DoesNotExist:
        messages.error(request, "You are not registered in AIML department.")
        return redirect('guide_list')

    student_vtu = student.vtu_number
    batch_instance = batch.objects.filter(
        Student1_vtu=student_vtu
    ).first() or batch.objects.filter(
        Student2_vtu=student_vtu
    ).first() or batch.objects.filter(
        Student3_vtu=student_vtu
    ).first() or batch.objects.filter(
        Student4_vtu=student_vtu
    ).first() or batch.objects.filter(
        Student5_vtu=student_vtu
    ).first()

    if not batch_instance:
        messages.error(request, "You are not assigned to any batch.")
        return redirect('guide_list')

    # Check if any pending/accepted request exists for this batch
    if GuideRequest.objects.filter(batch=batch_instance, status__in=['Pending', 'Accepted']).exists():
        messages.error(request, "Your batch already has a pending or accepted guide request.")
        return redirect('guide_list')

    guide = get_object_or_404(Guide, id=guide_id)

    if guide.available_slots <= 0:
        messages.error(request, "This guide has no available slots.")
        return redirect('guide_list')

    GuideRequest.objects.create(batch=batch_instance, guide=guide, requested_by=request.user)
    messages.success(request, f"Request sent to {guide.faculty.name}. Awaiting approval.")
    return redirect('guide_list')


@login_required
def guide_dashboard(request):
    # Identify the logged-in guide
    try:
        guide_faculty = dept_member.objects.get(email=request.user.email, role='Faculty')
        guide = Guide.objects.get(faculty=guide_faculty)
    except (dept_member.DoesNotExist, Guide.DoesNotExist):
        messages.error(request, "You are not registered as a guide.")
        return redirect('custom_login')

    requests = GuideRequest.objects.filter(guide=guide, status='Pending')
    return render(request, 'guide/dashboard.html', {'requests': requests})


@login_required
def handle_request(request, req_id, action):
    guide_req = get_object_or_404(GuideRequest, id=req_id)
    guide = guide_req.guide

    if action == "accept":
        if guide.available_slots <= 0:
            messages.error(request, "No available slots left.")
            return redirect('guide_dashboard')

        guide_req.status = "Accepted"
        guide_req.save()
        guide.used_slots += 1
        guide.save()
        batch_instance = guide_req.batch
        batch_instance.guide_assigned = guide
        batch_instance.save()
        messages.success(request, f"You accepted {batch_instance.batch_number}.")
    elif action == "decline":
        guide_req.status = "Declined"
        guide_req.save()
        guide.total_slots += 1
        guide.save()
        messages.warning(request, f"You declined {guide_req.batch.batch_number}.")
    return redirect('guide_dashboard')
