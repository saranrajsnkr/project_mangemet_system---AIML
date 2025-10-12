import uuid
from django.db import models
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from cloudinary.models import CloudinaryField
from django.contrib.auth.models import User
import uuid
from django.db import models
from django.utils.text import slugify


# models.py
class SiteSetting(models.Model):
    SiteSettings = models.CharField(max_length=100, default="Site Settings", editable=False)
    maintenance_mode = models.BooleanField(default=False)
    active_approval_letter = models.BooleanField("Allow Approval Letter Uploads", default=True)
    active_undertaking_letter = models.BooleanField("Allow Undertaking Letter Uploads", default=True)
    active_bonafide_letter = models.BooleanField("Allow Bonafide Letter Uploads", default=True)
    max_students_per_internship = models.PositiveIntegerField("Max Students per Internship", default=10)

    def __str__(self):
        return "Site Settings"

    class Meta:
        verbose_name = "Site Setting"
        verbose_name_plural = "Site Settings"


MESSAGE_COLOR_CHOICES = [
    ('green', 'Green'),
    ('orange', 'Orange'),
    ('red', 'Red'),
]

class Announcement(models.Model):
    message1 = models.TextField("Message 1", max_length=500, blank=True, null=True)
    is_message1_active = models.BooleanField("Show Message 1", default=False)
    message1_color = models.CharField("Message 1 Color", max_length=10, choices=MESSAGE_COLOR_CHOICES, default='green')


    message2 = models.TextField("Message 2", max_length=500, blank=True, null=True)
    is_message2_active = models.BooleanField("Show Message 2", default=False)
    message2_color = models.CharField("Message 2 Color", max_length=10, choices=MESSAGE_COLOR_CHOICES, default='orange')


    def __str__(self):
        return "Announcements"

    class Meta:
        verbose_name = "Announcement"
        verbose_name_plural = "Announcements"


class downloadable_files(models.Model):
    file_name = models.CharField(max_length=100, blank=True, null=True)
    file_link = models.URLField(max_length=200, blank=True, null=True)
    
    def __str__(self):
        return self.file_name

import uuid
from django.db import models

# ==================== Dept Of AIML ====================
class dept_member(models.Model):
    ROLE_CHOICES = [
        ('HOD', 'Head of Department'),
        ('Student', 'Student'),
        ('Faculty', 'Faculty'),
    ]
    YEAR_CHOICES = [(str(year), str(year)) for year in range(1, 5)]  # 1 to 4

    uid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=100)
    year = models.CharField(max_length=1, choices=YEAR_CHOICES, blank=True, null=True)
    vtu_number = models.CharField(max_length=20, blank=True, null=True, unique=True)
    role = models.CharField(max_length=100, choices=ROLE_CHOICES, blank=True, null=True)
    mobile_number = models.CharField(max_length=15, blank=True, null=True)
    designation = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(max_length=100, unique=True)

    def __str__(self):
        return f"{self.name} ({self.vtu_number or 'No VTU'})"


class batch(models.Model):
    batch_number = models.CharField(max_length=20, blank=True, null=True)
    Student1_name = models.CharField(max_length=100, blank=True, null=True)
    Student1_vtu = models.CharField(max_length=20, blank=True, null=True)
    Student2_name = models.CharField(max_length=100, blank=True, null=True)
    Student2_vtu = models.CharField(max_length=20, blank=True, null=True)
    Student3_name = models.CharField(max_length=100, blank=True, null=True)
    Student3_vtu = models.CharField(max_length=20, blank=True, null=True)
    Student4_name = models.CharField(max_length=100, blank=True, null=True)
    Student4_vtu = models.CharField(max_length=20, blank=True, null=True)
    Student5_name = models.CharField(max_length=100, blank=True, null=True)
    Student5_vtu = models.CharField(max_length=20, blank=True, null=True)
    project_title = models.CharField(max_length=200, blank=True, null=True)
    project_oneliner = models.CharField(max_length=300, blank=True, null=True)
    project_abstract = models.TextField(max_length=2000, blank=True, null=True)
    guide_assigned = models.ForeignKey('Guide', on_delete=models.SET_NULL, null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.batch_number:
            last_batch = batch.objects.order_by('-id').first()
            next_num = 1 if not last_batch else int(last_batch.batch_number.split(' ')[-1]) + 1
            self.batch_number = f"Batch {next_num}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.batch_number


class Guide(models.Model):
    faculty = models.OneToOneField(dept_member, on_delete=models.CASCADE, limit_choices_to={'role': 'Faculty'})
    total_slots = models.IntegerField(default=3)
    used_slots = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.faculty.name} (Slots: {self.used_slots}/{self.total_slots})"

    @property
    def available_slots(self):
        return self.total_slots - self.used_slots


class GuideRequest(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Accepted', 'Accepted'),
        ('Declined', 'Declined'),
    ]
    batch = models.ForeignKey(batch, on_delete=models.CASCADE)
    guide = models.ForeignKey(Guide, on_delete=models.CASCADE)
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Pending')
    requested_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.batch.batch_number} → {self.guide.faculty.name} ({self.status})"