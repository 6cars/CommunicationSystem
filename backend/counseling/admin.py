from django.contrib import admin

from counseling.models import CounselingSession, Experience, Message, RecallSupportLog

admin.site.register(CounselingSession)
admin.site.register(Message)
admin.site.register(Experience)
admin.site.register(RecallSupportLog)
