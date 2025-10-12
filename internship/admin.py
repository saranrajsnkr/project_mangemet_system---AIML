import csv
from django.contrib import admin, messages
from .models import  Announcement , SiteSetting , downloadable_files , dept_member , batch , Guide, GuideRequest
from django.http import HttpResponse
from django.shortcuts import render, redirect
from .admin_forms import CsvImportForm  # Make sure you have this form
from django.db.models import F
from django.utils.safestring import mark_safe
import csv
from django import forms
from django.urls import path

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