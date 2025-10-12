# from django.db.models.signals import post_save, post_delete
# from django.dispatch import receiver
# from .models import InternshipApplication, Company, Student
# from django.utils.text import slugify
# from django.conf import settings
# import gspread
# from google.oauth2.service_account import Credentials
# from gspread.exceptions import GSpreadException
# import time

# # Google Sheets setup
# SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# def get_google_sheet():
#     """
#     Return the Google Sheet object if credentials are available.
#     Otherwise, return None to safely skip Google Sheets operations.
#     """
#     if not getattr(settings, "GOOGLE_CONFIG", None):
#         return None

#     try:
#         creds = Credentials.from_service_account_info(settings.GOOGLE_CONFIG, scopes=SCOPES)
#         client = gspread.authorize(creds)
#         return client.open_by_key(settings.GOOGLE_SHEET_ID).sheet1
#     except Exception as e:
#         print(f"⚠️ Failed to initialize Google Sheet: {e}")
#         return None


# # ---- Handle Internship Applications ----
# @receiver(post_save, sender=InternshipApplication)
# def handle_approved_application(sender, instance, created, **kwargs):
#     if instance.application_approved != "APPROVED":
#         return

#     base_name = instance.industry_name.strip()
#     normalized_name = base_name
#     counter = 1

#     # Ensure unique company name
#     while Company.objects.filter(name=normalized_name).exists():
#         normalized_name = f"{base_name} ({counter})"
#         counter += 1

#     # Try to find an existing company by name
#     company = Company.objects.filter(
#         name__iexact=base_name,
#     ).first()

#     if company:
#         company.vacancy += 1
#         company.save()
#     else:
#         company = Company.objects.create(
#             name=normalized_name,
#             fees=instance.fees_amount or '0',
#             location=instance.industry_location,
#             domain=instance.domain_of_work,
#             vacancy=1,
#             active=False,
#             description="Auto-created from external application",
#         )

#     # ---------- Handle Multiple Students ----------
#     student_fields = [
#         {
#             "name": instance.student_name,
#             "vtu": instance.vtu_number,
#             "contact": instance.contact_number,
#             "dept": instance.department,
#         },
#         # student_2 → student_10
#         *[
#             {
#                 "name": getattr(instance, f"student_{i}"),
#                 "vtu": getattr(instance, f"vtu_number_{i}"),
#                 "contact": getattr(instance, f"contact_number_stu_{i}"),
#                 "dept": getattr(instance, f"department_stu_{i}"),
#             }
#             for i in range(2, 11)
#         ],
#     ]

#     for stu in student_fields:
#         if stu["vtu"]:  # Only create if VTU is present
#             student, created = Student.objects.get_or_create(
#                 roll_number=stu["vtu"].lower(),
#                 defaults={
#                     'name': stu["name"],
#                     'mobile_number': stu["contact"],
#                     'department': stu["dept"],
#                     'applied_company': company,
#                     'fee': instance.fees_amount or '0',
#                     'house': "External",
#                 }
#             )
#             if not created and not student.applied_company:
#                 student.applied_company = company
#                 student.save()



# # ---- Sync Student Save to Google Sheets ----
# @receiver(post_save, sender=Student)
# def track_save(sender, instance, created, **kwargs):
#     sheet = get_google_sheet()
#     if not sheet:
#         print(f"⚠️ Skipping Google Sheet update for student {instance.name}: No credentials available.")
#         return

#     row_data = [
#         instance.id,
#         instance.name,
#         instance.roll_number,
#         instance.mobile_number or "",
#         f"vtu{instance.roll_number}@veltech.edu.in",  # 👈 new email field
#         instance.department or "",
#         instance.applied_company.name if instance.applied_company else "",
#         instance.applied_company.id if instance.applied_company else "",
#         instance.fee or "",
#         "TRUE",
#         instance.house or "",
#     ]

#     try:
#         cells = sheet.findall(str(instance.id))
#         if cells:
#             cell = cells[0]
#             cell_list = []
#             for col, value in enumerate(row_data, start=1):
#                 cell_obj = sheet.cell(cell.row, col)
#                 cell_obj.value = value
#                 cell_list.append(cell_obj)
#             sheet.update_cells(cell_list, value_input_option='USER_ENTERED')
#             print(f"♻️ Updated student {instance.name} in sheet.")
#         else:
#             raise ValueError("Not found")
#     except (GSpreadException, ValueError):
#         sheet.append_row(row_data, value_input_option='USER_ENTERED')
#         print(f"➕ Added new student {instance.name} to sheet.")
#     except Exception as e:
#         print(f"⚠️ Error updating sheet for student {instance.name}: {e}")
#     finally:
#         time.sleep(2)


# # ---- Sync Student Delete to Google Sheets ----
# @receiver(post_delete, sender=Student)
# def track_delete(sender, instance, **kwargs):
#     sheet = get_google_sheet()
#     if not sheet:
#         print(f"⚠️ Skipping Google Sheet deletion for student {instance.name}: No credentials available.")
#         return

#     try:
#         cell = sheet.find(str(instance.id))
#         if cell:
#             sheet.delete_rows(cell.row)
#             print(f"🗑️ Deleted student {instance.name} (ID={instance.id}) from sheet.")
#     except Exception as e:
#         print(f"⚠️ Error deleting from sheet for student {instance.name}: {e}")
#     finally:
#         time.sleep(2)
