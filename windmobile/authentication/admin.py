from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User


class CustomUserAdmin(UserAdmin):
    list_display = list(UserAdmin.list_display) + ['last_login', 'date_joined']
    ordering = ('-date_joined',)


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
