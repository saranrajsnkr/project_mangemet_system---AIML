# from allauth.account.adapter import DefaultAccountAdapter
# from django.shortcuts import redirect

# class CustomAccountAdapter(DefaultAccountAdapter):
#     def get_login_redirect_url(self, request):
#         return '/'

#     def get_login_url(self, request):
#         return '/login/'   # redirect to your site_login.html




from allauth.account.adapter import DefaultAccountAdapter
from django.contrib import messages
from django.core.exceptions import ValidationError


# class CustomAccountAdapter(DefaultAccountAdapter):
#     def is_open_for_signup(self, request):
#         return True

#     def clean_email(self, email):
#         """Restrict signup to only @veltech.edu.in emails"""
#         email = super().clean_email(email)
#         if not email.endswith("@veltech.edu.in"):
#             # Store the message so your template can catch it
#             request = self.request
#             if request:
#                 messages.add_message(
#                     request,
#                     messages.ERROR,
#                     "Please use your @veltech.edu.in email to sign up.",
#                     extra_tags='domain_error'
#                 )
#             # Prevent user creation
#             raise ValidationError("Only @veltech.edu.in emails are allowed.")
#         return email

#     def get_login_redirect_url(self, request):
#         return '/'

#     def get_login_url(self, request):
#         return '/login/'





# class CustomAccountAdapter(DefaultAccountAdapter):
#     def is_open_for_signup(self, request):
#         # Always allow signups (we will restrict by email later)
#         return True

#     def clean_email(self, email):
#         """Ensure only @veltech.edu.in emails can register via Google"""
#         email = super().clean_email(email)
#         if not email.endswith("@veltech.edu.in"):
#             raise ValidationError("Only @veltech.edu.in emails are allowed.")
#         return email

#     def get_login_redirect_url(self, request):
#         return '/'

#     def get_login_url(self, request):
#         return '/login/'




class CustomAccountAdapter(DefaultAccountAdapter):
    def clean_email(self, email):
        email = super().clean_email(email)
        if not email.endswith("@veltech.edu.in"):
            request = getattr(self, 'request', None)
            if request and not hasattr(request, '_email_domain_error_shown'):
                messages.add_message(
                    request,
                    messages.ERROR,
                    "Please use your @veltech.edu.in email to sign up.",
                    extra_tags='domain_error'
                )
                # Mark that we already showed this message once
                request._email_domain_error_shown = True

            raise ValidationError("Please use your @veltech.edu.in email to sign up.")
        return email