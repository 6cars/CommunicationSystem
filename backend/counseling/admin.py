from django.contrib import admin

from counseling.models import CounselingSession, Message

admin.site.register(CounselingSession)
admin.site.register(Message)
