from django.shortcuts import render, redirect, get_object_or_404
from .models import Company, Student , Announcement , UserReport , InternshipApplication , StudentReport , Attendance , downloadable_files , SiteSetting
from django.contrib import messages
from django.db import transaction, IntegrityError
from django.db.models import F
from django.http import JsonResponse
import psutil
import os
from .forms import UserReportForm , InternshipApplicationForm , StudentReportForm
from django.core.mail import send_mail
import random
from django.conf import settings
import gspread
from google.oauth2.service_account import Credentials
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, get_object_or_404, redirect
from .models import Student
from .forms import StudentDocumentsForm
import re
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
import cloudinary.uploader
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from .models import Student, Company, Attendance
from .forms import CompanyLoginForm
import datetime
from django.db.models import Q



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
        student_result = Student.objects.filter(roll_number=Vtu_number).select_related('applied_company').first()
        
        attendance_records = Attendance.objects.filter(vtu_number=Vtu_number).order_by('-date')

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
                'student_result': student_result,
                'attendance_records': attendance_records,
                "is_admin": is_admin,   # pass to template
                "site_setting": site_settings,
            },
        )


def company_list(request):
    companies_with_vacancy = Company.objects.filter(vacancy__gt=0,active=True)
    announcement = Announcement.objects.first()
    context = {
        'companies': companies_with_vacancy,
        'has_vacancy': companies_with_vacancy.exists(),
        'announcement': announcement,
    }
    return render(request, 'internship/company_list.html', context)


@transaction.atomic
def apply_to_company(request, company_uid):
    company = get_object_or_404(Company.objects.select_for_update(), uid=company_uid)

    # Generate roll number from email (locked)
    roll = str(request.user.email[3:8]).lower().strip()

    if request.method == 'POST':
        name = request.POST.get('name')
        mobile = request.POST.get('mobile_number')
        department = request.POST.get('department')

        # Prevent application if no vacancies
        if company.vacancy <= 0:
            messages.error(request, "Vacancy was filled. Please apply for another company.",extra_tags='user')
            return redirect('home')

        # Prevent duplicate application
        if Student.objects.filter(roll_number=roll, applied_company=company).exists():
            messages.error(request, "You have already applied to this company.",extra_tags='user')
            return redirect('home')
        
        student_qs = Student.objects.filter(roll_number=roll)

        if student_qs.exists():
            student = student_qs.first()

            # Check if student already applied AND the company is NOT the "BLOCKED" company
            if student.applied_company.name == "Blocked":
                messages.error(request, "You have been blacklisted, so you cannot apply to any company.", extra_tags='user')
                return redirect('home')
        
        if Student.objects.filter(roll_number=roll).exists():
            messages.error(request, "You have already enrolled in a company, so you cannot apply again to another company.",extra_tags='user')
            return redirect('home')
        
        # if InternshipApplication.objects.filter(vtu_number=roll).exists():
        #     messages.error(request, "You have already applied with this VTU number.",extra_tags='user')
        #     return redirect('company_list')
        
        Intern_qs= InternshipApplication.objects.filter(vtu_number=roll)
        if Intern_qs.exists():
            intern = Intern_qs.first()
            if intern.application_approved == "APPROVED" or intern.application_approved == "PENDING":
                messages.error(request, "Your external company form is either pending or approved. You can only enroll in other companies if it gets rejected.",extra_tags='user')
                return redirect('home')
            
            
        for i in range(2, 11):  # since student_2 to student_10
            field_name = f"vtu_number_{i}"
            Intern_qs = InternshipApplication.objects.filter(**{field_name: roll})
            if Intern_qs.exists():
                intern = Intern_qs.first()
                if intern.application_approved in ["APPROVED", "PENDING"]:
                    messages.error(
                        request,
                        "Your external company form is either pending or approved. "
                        "You can only enroll in other companies if it gets rejected.",
                        extra_tags='user'
                    )
                    return redirect('home')


        try:
            # Create the student application and assign it to variable
            student = Student.objects.create(
                name=name,
                roll_number=roll,
                mobile_number=mobile,
                department=department,
                applied_company=company,
                house="INTERNAL",
            )

            # Reduce the company's vacancy
            company.vacancy = F('vacancy') - 1
            company.save()
            company.refresh_from_db()

            messages.success(request, "Applied successfully!", extra_tags='user')
            return redirect('home')

        except IntegrityError:
            messages.error(request, "You have already applied or something went wrong. Please check your VTU on the application status page.", extra_tags='user')
            return redirect('home')

    return render(request, 'internship/apply_form.html', {
        'company': company,
        'roll_number': roll,  # Pass it to template (readonly field)
    })

def check_application_status(request):
    internship_result = None
    student_result = None
    roll_number = ''
    searched = False  # Default is False (page just loaded)

    SiteSettings = SiteSetting.objects.first()

    if request.method == 'POST':
        roll_number = str(request.POST.get('roll_number', '')).strip().lower()
        searched = True  # User submitted a search


        # Check InternshipApplication model
        internship_result = InternshipApplication.objects.filter(Q(vtu_number=roll_number) |
                        Q(vtu_number_2=roll_number) |
                        Q(vtu_number_3=roll_number) |
                        Q(vtu_number_4=roll_number) |
                        Q(vtu_number_5=roll_number) |
                        Q(vtu_number_6=roll_number) |
                        Q(vtu_number_7=roll_number) |
                        Q(vtu_number_8=roll_number) |
                        Q(vtu_number_9=roll_number) |
                        Q(vtu_number_10=roll_number)
                    )
        # Check Student model
        student_result = Student.objects.filter(roll_number=roll_number).select_related('applied_company').first()

    return render(request, 'internship/check_status.html', {
        'internship_result': internship_result,
        'student_result': student_result,
        'roll_number': roll_number,
        "searched": searched,
        "site_setting": SiteSettings,

    })


def performance_view(request):
    pid = os.getpid()
    process = psutil.Process(pid)

    cpu = process.cpu_percent(interval=0.5)
    memory = process.memory_info().rss / 1024 ** 2  # in MB

    return JsonResponse({
        "cpu_usage_percent": f"{cpu:.2f}",
        "memory_usage_mb": f"{memory:.2f}"
    })



# === Site Support Report Views ===

# === Helper ===
def generate_otp():
    return str(random.randint(100000, 999999))

# === Step 1: Ask for Email ===
def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        request.session['email'] = email

        # === Bypass OTP if email matches ===
        if email == 'vtu24875@veltech.edu.in':
            request.session['is_logged_in'] = True
            return redirect('submit_report')

        # === Normal OTP flow ===
        otp = generate_otp()
        request.session['otp'] = otp

        send_mail(
            subject='Your OTP Code',
            message=f'Your OTP is {otp}',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
        )
        return redirect('verify_otp')

    return render(request, 'reports/login.html')

# === Step 2: OTP Verification ===
def verify_otp_view(request):
    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        if entered_otp == request.session.get('otp'):
            request.session['is_logged_in'] = True
            return redirect('submit_report')
        else:
            messages.error(request, 'Invalid OTP')
    return render(request, 'reports/verify_otp.html')

# === Step 3: Report Submission ===
def submit_report_view(request):
    # if not request.session.get('is_logged_in'):
    #     return redirect('login')

    email = request.user.email
    initial_data = {
        'email': email,
        'roll_number': email[3:8]  # Extracts "24875"
    }

    if request.method == 'POST':
        form = UserReportForm(request.POST, request.FILES)
        if form.is_valid():
            report = form.save()
            # Email to admin
            try:
                send_mail(
                    subject=f"New Report from {report.name}",
                    message=(
                        f"Name: {report.name}\n"
                        f"Roll No: {report.roll_number}\n"
                        f"Email: {report.email}\n"
                        f"Problem:\n{report.problem}"
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[settings.ADMIN_EMAIL]
                )
                print("Email sent successfully.")
            except Exception as e:
                print("Error sending email:", e)

            messages.success(request, "Report submitted successfully.", extra_tags='user')
            return redirect('home')
    else:
        form = UserReportForm(initial=initial_data)

    return render(request, 'reports/report_form.html', {'form': form})

# === Step 4: Thank You Page ===
def thank_you_view(request):
    request.session.flush()  # clear login session after submit
    return render(request, 'reports/thank_you.html')




# === External Application ===

# # === Helper ===
def cmpapply_otp():
    return str(random.randint(100000, 999999))

# === Step 1: Ask for Email ===
def cmpapply_login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        request.session['cmp_email'] = email

        # Bypass logic
        if email == 'vtu24875@veltech.edu.in':
            request.session['cmp_logged_in'] = True
            return redirect('cmpapply_form')

        # Normal OTP flow
        otp = cmpapply_otp()
        request.session['cmp_otp'] = otp

        send_mail(
            subject='Your Internship OTP Code',
            message=f'Your One Time Password (OTP) for internship application is: {otp}',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
        )
        return redirect('cmpapply_verify_otp')

    return render(request, 'internship/email_login.html')


# === Step 2: OTP Verification ===
def cmpapply_verify_otp(request):
    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        if entered_otp == request.session.get('cmp_otp'):
            request.session['cmp_logged_in'] = True
            return redirect('cmpapply_form')
        else:
            messages.error(request, 'Invalid OTP. Please try again.')
    return render(request, 'internship/verify_otp.html')

# === Step 3: Internship Form Submission ===
def cmpapply_form_view(request):
    # if not request.session.get('cmp_logged_in'):
    #     return redirect('cmpapply_login')

    email = request.user.email
    initial_data = {
        'email': email,
        'vtu_number': email[3:8] if len(email) >= 8 else ''
    }
    
    vtu_number = initial_data['vtu_number']
    student_qs = Student.objects.filter(roll_number=vtu_number)

    if student_qs.exists():
        student = student_qs.first()

        # Check if student already applied AND the company is NOT the "BLOCKED" company
        if student.applied_company.name != "Blocked":
            messages.error(request, "You have already enrolled in a company, so you cannot access the external application form.", extra_tags='user')
            return redirect('home')



    
    # if InternshipApplication.objects.filter(vtu_number=vtu_number).exists():
    #     messages.error(request, "You have already applied with this VTU number.",extra_tags='user')
    #     return redirect('company_list')
    
    Intern_qs= InternshipApplication.objects.filter(vtu_number=vtu_number)
    if Intern_qs.exists():
        intern = Intern_qs.first()
        if intern.application_approved == "APPROVED" or intern.application_approved == "PENDING":
            messages.error(request,"You’ve already submitted an external application, and it’s either approved or still pending. You can only apply again if it gets rejected.",extra_tags='user')
            return redirect('home')
    
    for i in range(2, 11):  # since student_2 to student_10
        field_name = f"vtu_number_{i}"
        Intern_qs = InternshipApplication.objects.filter(**{field_name: vtu_number})
        if Intern_qs.exists():
            intern = Intern_qs.first()
            if intern.application_approved in ["APPROVED", "PENDING"]:
                messages.error(
                    request,
                    "Your external company form is either pending or approved. "
                    "You can only enroll in other companies if it gets rejected.",
                    extra_tags='user'
                )
                return redirect('home')
        

    if request.method == 'POST':
        form = InternshipApplicationForm(request.POST)
        if form.is_valid():
            application = form.save(commit=False)  # don't save yet

            invalid_vtus = []

            for i in range(1, 11):  # student_1 to student_10
                vtu_field = f"vtu_number" if i == 1 else f"vtu_number_{i}"
                vtu_value = getattr(application, vtu_field, None)

                if vtu_value:
                    # Check Student model
                    if Student.objects.filter(roll_number=vtu_value).exists():
                        student = Student.objects.filter(roll_number=vtu_value).first()
                        if student.applied_company and student.applied_company.name != "Blocked":
                            invalid_vtus.append(vtu_value)

                    # Check InternshipApplication model
                    existing_applications = InternshipApplication.objects.filter(
                        Q(vtu_number=vtu_value) |
                        Q(vtu_number_2=vtu_value) |
                        Q(vtu_number_3=vtu_value) |
                        Q(vtu_number_4=vtu_value) |
                        Q(vtu_number_5=vtu_value) |
                        Q(vtu_number_6=vtu_value) |
                        Q(vtu_number_7=vtu_value) |
                        Q(vtu_number_8=vtu_value) |
                        Q(vtu_number_9=vtu_value) |
                        Q(vtu_number_10=vtu_value)
                    )

                    for existing in existing_applications:
                        if existing.application_approved in ["APPROVED", "PENDING"]:
                            invalid_vtus.append(vtu_value)

            # If there are invalid VTUs, warn user without saving
            if invalid_vtus:
                form.add_error(None, f"The following VTU(s) have already applied and cannot be added again: {', '.join(invalid_vtus)}")
                messages.warning(request, f"Please remove or change the following VTU(s): {', '.join(invalid_vtus)}", extra_tags='user')
                return render(request, 'internship/internship_form.html', {'form': form})

            # ✅ If no issues, now save
            application.save()
            messages.success(request, "Application submitted successfully.", extra_tags='user')
            return redirect('home')
    else:
        form = InternshipApplicationForm(initial=initial_data)
    
    max_students = SiteSetting.objects.first().max_students_per_internship

    return render(request, 'internship/internship_form.html', {'form': form, 'max_students': max_students})


# === Step 4: Thank You Page ===
def cmpapply_thank_you(request):
    request.session.flush()
    return render(request, 'internship/thank_you.html')





# === Reporting status of Internship (Optional Unwanted)===

# === Helper ===
def generate_otp():
    return str(random.randint(100000, 999999))

# === Step 1: Student Login with Roll Number ===
def rep_login_view(request):
    if request.method == 'POST':
        roll_number = request.POST.get('roll_number')
        
        # Check if report already submitted
        if StudentReport.objects.filter(roll_number=roll_number).exists():
            messages.error(request, "You have already submitted a report.", extra_tags='user')
            return redirect('company_list')

        try:
            student = Student.objects.get(roll_number=roll_number)
            request.session['student_roll'] = roll_number
            request.session['student_email'] = f"vtu{roll_number}@veltech.edu.in"

            otp = generate_otp()
            request.session['student_otp'] = otp

            send_mail(
                subject='Student OTP Verification',
                message=f'Your OTP is {otp}',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[request.session['student_email']],
            )
            return redirect('rep_verify_otp')
        except Student.DoesNotExist:
            messages.error(request, 'Invalid roll number. Student not found in any company.')

    return render(request, 'report/student_login.html')



# === Step 2: Verify Student OTP ===
def rep_verify_otp_view(request):
    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        if entered_otp == request.session.get('student_otp'):
            request.session['is_student_logged_in'] = True
            return redirect('rep_submit_report')
        else:
            messages.error(request, 'Invalid OTP. Please try again.')

    return render(request, 'report/student_verify_otp.html')


# === Step 3: Submit Report Status ===

def rep_submit_report_view(request):
    roll_number = request.session.get('student_roll', '')
    email = request.session.get('student_email', '')
    
    if not roll_number:
        messages.error(request, "Session expired or not logged in.")
        return redirect('rep_login')

    initial_data = {
        'roll_number': roll_number,
        'email': email,
        'vtu_number': email[3:8] if len(email) >= 8 else ''
    }

    if request.method == 'POST':
        form = StudentReportForm(request.POST)
        if form.is_valid():
            if StudentReport.objects.filter(roll_number=roll_number).exists():
                messages.error(request, "You have already submitted the report.")
            else:
                report = form.save(commit=False)
                report.roll_number = roll_number  # Ensure it's saved with session value
                report.save()
                return redirect('rep_thank_you')
    else:
        form = StudentReportForm(initial=initial_data)

    return render(request, 'report/student_report_form.html', {'form': form})


# === Step 4: Thank You ===
def rep_thank_you_view(request):
    request.session.flush()
    return render(request, 'report/student_thank_you.html')







def login_not_required(view_func):
    """Redirect authenticated users away from guest-only pages"""
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('custom_login')  # change to your logged-in home page
        return view_func(request, *args, **kwargs)
    return _wrapped_view


@login_not_required
def company_login(request):
    """Company Login"""
    if request.method == "POST":
        form = CompanyLoginForm(request.POST)
        if form.is_valid():
            company = form.cleaned_data["company"]
            request.session["company_id"] = str(company.uid)  # Save in session
            return redirect("attendance_page")
        else:
            messages.error(request, "Invalid username or password.")
            return redirect("company_login")
    else:
        form = CompanyLoginForm()
    return render(request, "internship/company_login.html", {"form": form})



@login_not_required
def attendance_page(request):
    company_id = request.session.get("company_id")
    if not company_id:
        return redirect("company_login")

    company = Company.objects.get(uid=company_id)
    students = Student.objects.filter(applied_company=company)

    # Default date = today
    today = datetime.date.today()
    selected_date = request.POST.get("attendance_date") or today
    if isinstance(selected_date, str):
        selected_date = datetime.datetime.strptime(selected_date, "%Y-%m-%d").date()

    if request.method == "POST":
        for student in students:
            status = request.POST.get(f"attendance_{student.id}", "Absent")
            Attendance.objects.update_or_create(
                student=student,
                vtu_number=student.roll_number,
                company=company,
                date=selected_date,
                defaults={"status": status},
            )
        messages.success(request, f"Attendance saved for {selected_date}!", extra_tags='user')
        return redirect("attendance_page")

    # Fetch attendance for that selected date
    attendance_records = Attendance.objects.filter(company=company, date=selected_date)

    return render(request, "internship/attendance_page.html", {
        "company": company,
        "students": students,
        "attendance_records": attendance_records,
        "today": today,
        "selected_date": selected_date,
    })


@login_not_required
def submit_attendance(request):
    request.session.flush()
    return render(request, "internship/submit_attendance.html")


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

@login_required
def upload_student_documents(request):
    # get roll from logged in user email
    email = request.user.email
    roll_number = extract_roll_from_email(email)
    
    SiteSettings = SiteSetting.objects.first()

    student = Student.objects.filter(roll_number=roll_number).first()
    if not student:
        messages.error(request, 'Invalid roll number. Student not found in any company.', extra_tags='user')
        return redirect('home')

    if request.method == "POST":
        approval_file = request.FILES.get("approval_letter")
        undertaking_file = request.FILES.get("undertaking_letter")
        bonafide_file = request.FILES.get("bonafide_letter")

        # ✅ validation function
        def is_valid_pdf(file, label):
            # Size check
            if file.size > MAX_FILE_SIZE:
                messages.error(request, f"{label} must be under 2 MB.", extra_tags='user')
                return False
            # Extension check
            ext = os.path.splitext(file.name)[1].lower()
            if ext != ".pdf":
                messages.error(request, f"{label} must be a PDF file.", extra_tags='user')
                return False
            # MIME type check
            if file.content_type != "application/pdf":
                messages.error(request, f"{label} must be a valid PDF.", extra_tags='user')
                return False
            return True

        if approval_file:
            if not is_valid_pdf(approval_file, "Approval letter"):
                return redirect("upload_documents")
            result = cloudinary.uploader.upload(
                approval_file,
                folder=f"APPROVAL_LETTERS/",
                public_id=f"{student.name}_{roll_number}"
            )
            student.approval_letter = result["secure_url"]
            student.approval_letter_got = True

        if undertaking_file:
            if not is_valid_pdf(undertaking_file, "Undertaking letter"):
                return redirect("upload_documents")
            result = cloudinary.uploader.upload(
                undertaking_file,
                folder=f"UNDERTAKING_LETTERS/",
                public_id=f"{student.name}_{roll_number}"
            )
            student.undertaking_letter = result["secure_url"]
            student.undertaking_letter_got = True

        if bonafide_file:
            if not is_valid_pdf(bonafide_file, "Bonafide letter"):
                return redirect("upload_documents")
            result = cloudinary.uploader.upload(
                bonafide_file,
                folder=f"BONAFIDE_LETTERS/",
                public_id=f"{student.name}_{roll_number}"
            )
            student.bonafide_letter = result["secure_url"]
            student.bonafide_letter_got = True

        student.save()
        messages.success(request, "Documents uploaded successfully!", extra_tags='user')
        return redirect("upload_documents")  # reload page after upload

    return render(request, "student/upload_documents.html", {"student": student, "site_setting": SiteSettings})


def downloadable_files_view(request):
    files = downloadable_files.objects.all()
    return render(request, 'internship/downloadable_files.html', {'files': files})


from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Count, Sum, Case, When, IntegerField, FloatField, F
from django.views.decorators.http import require_http_methods

# import your models
from .models import Student, Attendance, Company  # adjust import as per your structure

# Your DEPARTMENT_CHOICES (you already have this)
DEPARTMENT_CHOICES = [
    ('Artificial Intelligence (AI) and Data Science', 'Artificial Intelligence (AI) and Data Science'),
    ('Artificial Intelligence and Machine Learning', 'Artificial Intelligence and Machine Learning'),
    ('Computer Science & Engineering', 'Computer Science & Engineering'),
    ('Computer Science and Engineering (Artificial Intelligence and Machine Learning)', 'Computer Science and Engineering (Artificial Intelligence and Machine Learning)'),
    ('Computer Science and Engineering (Cyber Security)', 'Computer Science and Engineering (Cyber Security)'),
    ('Computer Science and Engineering (Data Science)', 'Computer Science and Engineering (Data Science)'),
    ('Computer Science and Design', 'Computer Science and Design'),
    ('Information Technology', 'Information Technology'),
]

# ❗ Hardcoded department accounts (username → dict)
DEPT_ACCOUNTS = {
    # username: {password, department}
    "dept_aimlds": {
        "password": "AIDS@123",
        "department": "Artificial Intelligence (AI) and Data Science",
    },
    "dept_aiml": {
        "password": "AIML@123",
        "department": "Artificial Intelligence and Machine Learning",
    },
    "dept_cse": {
        "password": "CSE@123",
        "department": "Computer Science & Engineering",
    },
    "dept_cse_aiml": {
        "password": "CSE-AIML@123",
        "department": "Computer Science and Engineering (Artificial Intelligence and Machine Learning)",
    },
    "dept_cyber": {
        "password": "CYBER@123",
        "department": "Computer Science and Engineering (Cyber Security)",
    },
    "dept_ds": {
        "password": "DS@123",
        "department": "Computer Science and Engineering (Data Science)",
    },
    "dept_csd": {
        "password": "CSD@123",
        "department": "Computer Science and Design",
    },
    "dept_it": {
        "password": "IT@123",
        "department": "Information Technology",
    },
}

def _require_dept_session(request):
    """Return department name if logged in; else None."""
    return request.session.get("dept_department")

@require_http_methods(["GET", "POST"])
def department_login(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()
        acct = DEPT_ACCOUNTS.get(username)

        if acct and acct["password"] == password:
            # Save session
            request.session["dept_username"] = username
            request.session["dept_department"] = acct["department"]
            messages.success(request, f"You are logged in as {acct['department']}.")
            return redirect("department_dashboard")
        else:
            messages.error(request, "Invalid username or password.")
            return render(request, "dept_login.html", {"title": "Department Login"})

    # GET
    return render(request, "dept_login.html", {"title": "Department Login"})

def department_logout(request):
    request.session.pop("dept_username", None)
    request.session.pop("dept_department", None)
    messages.info(request, "You have been logged out.")
    return redirect("department_login")

# views.py
from django.db.models import Count, Sum, Case, When, F, FloatField, IntegerField
from django.shortcuts import render, redirect
from django.contrib import messages

def department_dashboard(request):
    dept_name = _require_dept_session(request)
    if not dept_name:
        messages.warning(request, "Please log in first.")
        return redirect("department_login")

    site_settings = SiteSetting.objects.first()

    students_qs = (
        Student.objects
        .filter(department=dept_name, applied_company__isnull=False)
        .select_related("applied_company")
        .annotate(
            total_classes=Count("attendance"),
            present_classes=Sum(
                Case(
                    When(attendance__status="Present", then=1),
                    default=0,
                    output_field=IntegerField(),
                )
            ),
        )
        .annotate(
            attendance_pct=Case(
                When(total_classes__gt=0, then=(100.0 * F("present_classes") / F("total_classes"))),
                default=0.0,
                output_field=FloatField(),
            )
        )
        .order_by("name", "roll_number")
    )

    context = {
        "title": f"{dept_name} — Internship Dashboard",
        "dept_name": dept_name,
        "students": students_qs,
        "site_setting": site_settings,
    }
    return render(request, "dept_dashboard.html", context)




from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseBadRequest
from .models import dept_member, batch
import json, re


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
