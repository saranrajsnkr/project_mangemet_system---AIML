import csv
from django.contrib import admin, messages
from .models import Company, Student , Announcement , SiteSetting , UserReport , InternshipApplication , StudentReport , Attendance , downloadable_files , dept_member , batch , Guide, GuideRequest
from django.http import HttpResponse
from django.shortcuts import render, redirect
from .admin_forms import CsvImportForm  # Make sure you have this form
from django.db.models import F
from django.utils.safestring import mark_safe
import csv
from django import forms
from django.urls import path


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'skill_required', 'vacancy', 'location', 'active')
    actions = ["export_as_csv"]

    def export_as_csv(self, request, queryset):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="company_data.csv"'
        writer = csv.writer(response)

        # CSV Header
        writer.writerow([
            'UID',
            'Name',
            'CGPA',
            'Fees',
            'Duration',
            'Domain',
            'Description',
            'Skill Required',
            'Location',
            'Username',
            'password',
        ])

        # CSV Rows
        for company in queryset:
            writer.writerow([
                company.uid,
                company.name,
                company.cgpa if company.cgpa else '',
                company.fees if company.fees else '',
                company.duration if company.duration else '',
                company.domain if company.domain else '',
                company.description if company.description else '',
                company.skill_required if company.skill_required else '',
                company.location if company.location else '',
                company.username if company.username else '',
                company.password if company.password else '',
            ])

        return response

    export_as_csv.short_description = "Export Selected Companies to CSV"




@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('name', 'roll_number', 'department', 'applied_company', 'house','approval_letter_got','undertaking_letter_got','bonafide_letter_got',)
    search_fields = ('name', 'roll_number',)
    list_filter = ('applied_company', 'house')
    actions = ["export_as_csv"]
    change_list_template = "admin/internship/student/changelist.html"

    def export_as_csv(self, request, queryset):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="student_data.csv"'
        writer = csv.writer(response)

        # CSV Header
        writer.writerow(['Name', 'Roll Number', 'Mobile Number', 'Department', 'Applied Company', 'Fee'])

        # CSV Rows
        for student in queryset:
            writer.writerow([
                student.name,
                student.roll_number,
                student.mobile_number,
                student.department,
                student.applied_company.name if student.applied_company else '',
                student.fee if student.fee else '',
            ])

        return response

    export_as_csv.short_description = "Export Selected Students to CSV"

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('upload-csv/', self.upload_csv),
        ]
        return custom_urls + urls

    def upload_csv(self, request):
        if request.method == "POST":
            csv_file = request.FILES.get("csv_upload")
            if not csv_file or not csv_file.name.endswith('.csv'):
                messages.error(request, "Please upload a valid CSV file.")
                return redirect("..")

            try:
                try:
                    decoded_file = csv_file.read().decode('utf-8').splitlines()
                except UnicodeDecodeError:
                    csv_file.seek(0)  # Reset file pointer
                    decoded_file = csv_file.read().decode('latin-1').splitlines()

                reader = csv.DictReader(decoded_file)

                for row in reader:
                    try:
                        # Normalize fields
                        roll = row['Roll Number'].strip().lower()
                        company_name = row['Applied Company'].strip()

                        # Get or create company
                        company, created = Company.objects.get_or_create(
                            name__iexact=company_name,
                            defaults={
                                'name': company_name,
                                'vacancy': 1,  # First entry for new company
                                'fees': row.get('Fee', '').strip() or '0',
                                'location': row.get('Location', 'Not Provided'),
                                'domain': row.get('Domain', 'Unknown'),
                                'active': False,
                                'description': "Auto-created from CSV upload"
                            }
                        )

                        if not created:
                            # If company already exists → increase vacancy before adding
                            company.vacancy = F('vacancy') + 1
                            company.save()
                            company.refresh_from_db()

                        # Duplicate check
                        if Student.objects.filter(roll_number=roll, applied_company=company).exists():
                            self.message_user(request, f"Duplicate: {roll} already applied to {company.name}. Skipping.", level=messages.WARNING)
                            continue

                        # Create student
                        Student.objects.create(
                            name=row['Name'].strip(),
                            roll_number=roll,
                            mobile_number=row.get('Mobile Number', '').strip(),
                            department=row.get('Department', '').strip(),
                            applied_company=company,
                            fee=row.get('Fee', '').strip()
                        )

                    except Exception as e:
                        self.message_user(request, f"Error importing row: {row} → {e}", level=messages.ERROR)

                messages.success(request, "CSV file has been processed successfully.")
                return redirect("..")

            except Exception as e:
                messages.error(request, f"Error processing file: {e}")
                return redirect("..")

        # GET request – show upload form
        form = CsvImportForm()
        payload = {"form": form}
        return render(request, "admin/csv_upload.html", payload)


@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
    list_display = [ 'SiteSettings','maintenance_mode', 'active_approval_letter', 'active_undertaking_letter', 'active_bonafide_letter' ,'max_students_per_internship']

    def has_add_permission(self, request):
        # Only allow adding if no announcement exists
        return not SiteSetting.objects.exists()

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ['message1','is_message1_active','message2','is_message2_active']
    


    def has_add_permission(self, request):
        # Only allow adding if no announcement exists
        return not Announcement.objects.exists()

from django.contrib import admin
from .models import UserReport

@admin.register(UserReport)
class UserReportAdmin(admin.ModelAdmin):
    list_display = ('name', 'roll_number', 'email', 'submitted_at')
    search_fields = ('name', 'roll_number', 'email')
    list_filter = ('submitted_at',)

    # 🚫 Disable Add
    def has_add_permission(self, request):
        return False

    # 🚫 Disable Edit
    def has_change_permission(self, request, obj=None):
        return False

    # # 🚫 Disable Delete
    # def has_delete_permission(self, request, obj=None):
    #     return False
  



@admin.register(InternshipApplication)
class InternshipApplicationAdmin(admin.ModelAdmin):
    list_display = ("student_name", "vtu_number", "industry_name", "application_approved", "submitted_at")
    list_filter = ("application_approved",)
    search_fields = ("student_name", "vtu_number", "industry_name")

    # --- HR fields (separate names to avoid duplicates) ---
    def hr2(self, obj=None): return mark_safe("<hr style='border: 1px solid #ddd; margin: 20px 0;'>")
    def hr3(self, obj=None): return mark_safe("<hr style='border: 1px solid #ddd; margin: 20px 0;'>")
    def hr4(self, obj=None): return mark_safe("<hr style='border: 1px solid #ddd; margin: 20px 0;'>")
    def hr5(self, obj=None): return mark_safe("<hr style='border: 1px solid #ddd; margin: 20px 0;'>")
    def hr6(self, obj=None): return mark_safe("<hr style='border: 1px solid #ddd; margin: 20px 0;'>")
    def hr7(self, obj=None): return mark_safe("<hr style='border: 1px solid #ddd; margin: 20px 0;'>")
    def hr8(self, obj=None): return mark_safe("<hr style='border: 1px solid #ddd; margin: 20px 0;'>")
    def hr9(self, obj=None): return mark_safe("<hr style='border: 1px solid #ddd; margin: 20px 0;'>")

    hr2.short_description = hr3.short_description = hr4.short_description = ""
    hr5.short_description = hr6.short_description = hr7.short_description = ""
    hr8.short_description = hr9.short_description = ""

    fieldsets = (
        ('Student Details', {
            'fields': ('student_name', 'vtu_number', 'department', 'email', 'contact_number', 'submitted_at')
        }),
        ('Industry Details', {
            'fields': (
                'industry_name', 'industry_location', 'domain_of_work',
                'industry_category', 'industry_website', 'industry_email', 'industry_phone_number',
                'referal_person_name', 'referal_person_designation', 'referal_person_email', 'referal_person_phone_number'
            )
        }),
        ('Stipend & Fees', {
            'fields': ('stipend_provided', 'stipend_amount', 'fees_required', 'fees_amount')
        }),
        ('Additional Students', {
            'fields': (
                'student_2', 'vtu_number_2', 'contact_number_stu_2', 'department_stu_2',
                'hr2',
                'student_3', 'vtu_number_3', 'contact_number_stu_3', 'department_stu_3',
                'hr3',
                'student_4', 'vtu_number_4', 'contact_number_stu_4', 'department_stu_4',
                'hr4',
                'student_5', 'vtu_number_5', 'contact_number_stu_5', 'department_stu_5',
                'hr5',
                'student_6', 'vtu_number_6', 'contact_number_stu_6', 'department_stu_6',
                'hr6',
                'student_7', 'vtu_number_7', 'contact_number_stu_7', 'department_stu_7',
                'hr7',
                'student_8', 'vtu_number_8', 'contact_number_stu_8', 'department_stu_8',
                'hr8',
                'student_9', 'vtu_number_9', 'contact_number_stu_9', 'department_stu_9',
                'hr9',
                'student_10', 'vtu_number_10', 'contact_number_stu_10', 'department_stu_10',
            )
        }),
        ('Approval Status', {
            'fields': ('application_approved', 'approval_message'),
        }),
    )

    readonly_fields = ("hr2", "hr3", "hr4", "hr5", "hr6", "hr7", "hr8", "hr9")

    def get_readonly_fields(self, request, obj=None):
        base = ["hr2", "hr3", "hr4", "hr5", "hr6", "hr7", "hr8", "hr9"]
        if obj:
            all_fields = [field.name for field in obj._meta.fields]
            return base + [f for f in all_fields if f not in ("application_approved", "approval_message")]
        return base




@admin.register(StudentReport)
class StudentReportAdmin(admin.ModelAdmin):
    list_display = ('roll_number', 'report_status')
    list_filter = ('report_status',)
    search_fields = ('roll_number',)



@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("student", "company", "date", "status")
    search_fields = ("student__name", "company__name")
    list_filter = ("date", "status", "company")
    actions = ["export_as_csv"]

    def export_as_csv(self, request, queryset):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="attendance_data.csv"'
        writer = csv.writer(response)

        # CSV Header
        writer.writerow([
            "Student Name",
            "VTU Number",
            "Company",
            "Date",
            "Status"
        ])

        # CSV Rows
        for attendance in queryset:
            writer.writerow([
                attendance.student.name if attendance.student else "",
                attendance.vtu_number if attendance.vtu_number else "",
                attendance.company.name if attendance.company else "",
                attendance.date,
                attendance.status,
            ])

        return response

    export_as_csv.short_description = "Export Selected Attendance Records to CSV"



@admin.register(downloadable_files)
class downloadable_filesAdmin(admin.ModelAdmin):
    list_display = ('file_name', 'file_link')
    

#=================== Department Members Admin ===================
from django.contrib import admin, messages
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.urls import path
from .models import dept_member, batch
from django import forms
import csv


# --- CSV Upload Form ---
class CsvImportForm(forms.Form):
    csv_upload = forms.FileField()


@admin.register(dept_member)
class dept_memberAdmin(admin.ModelAdmin):
    list_display = ('name', 'vtu_number', 'role', 'designation', 'email', 'mobile_number')
    search_fields = ('name', 'vtu_number', 'email')
    list_filter = ('role', 'designation')
    actions = ["export_as_csv"]
    change_list_template = "admin/internship/student/changelist.html"

    # ---------- EXPORT CSV ----------
    def export_as_csv(self, request, queryset):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="dept_member_data.csv"'
        writer = csv.writer(response)

        writer.writerow(['Name', 'VTU Number', 'Role', 'Designation', 'Email', 'Mobile Number'])
        for member in queryset:
            writer.writerow([
                member.name,
                member.vtu_number or '',
                member.role or '',
                member.designation or '',
                member.email,
                member.mobile_number or '',
            ])

        return response

    export_as_csv.short_description = "Export Selected Department Members to CSV"

    # ---------- ADD CUSTOM URL ----------
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('upload-csv/', self.upload_csv),
        ]
        return custom_urls + urls

    # ---------- IMPORT CSV ----------
    def upload_csv(self, request):
        if request.method == "POST":
            csv_file = request.FILES.get("csv_upload")
            if not csv_file or not csv_file.name.endswith('.csv'):
                messages.error(request, "Please upload a valid CSV file.")
                return redirect("..")

            try:
                decoded_file = csv_file.read().decode('utf-8').splitlines()
                reader = csv.DictReader(decoded_file)
                for row in reader:
                    vtu = row.get('VTU Number', '').strip()
                    email = row.get('Email', '').strip()

                    if vtu and dept_member.objects.filter(vtu_number__iexact=vtu).exists():
                        self.message_user(request, f"Duplicate VTU: {vtu}. Skipping.", level=messages.WARNING)
                        continue
                    elif email and dept_member.objects.filter(email__iexact=email).exists():
                        self.message_user(request, f"Duplicate Email: {email}. Skipping.", level=messages.WARNING)
                        continue

                    dept_member.objects.create(
                        name=row.get('Name', '').strip(),
                        vtu_number=vtu or None,
                        role=row.get('Role', '').strip(),
                        designation=row.get('Designation', '').strip(),
                        email=email,
                        mobile_number=row.get('Mobile Number', '').strip(),
                    )

                messages.success(request, "CSV file processed successfully.")
                return redirect("..")

            except Exception as e:
                messages.error(request, f"Error processing file: {e}")
                return redirect("..")

        form = CsvImportForm()
        return render(request, "admin/csv_upload.html", {"form": form})


@admin.register(batch)
class batchAdmin(admin.ModelAdmin):
    list_display = ('batch_number', 'project_title', 'project_oneliner')
    search_fields = ('batch_number',)


admin.site.register(Guide)
admin.site.register(GuideRequest)