from django.contrib import admin
from .models import Movement, MovementDetail

# Register your models here.

class MovementDetailInline(admin.TabularInline):
    model = MovementDetail
    extra = 1

class MovementAdmin(admin.ModelAdmin):
    inlines = [MovementDetailInline]

admin.site.register(Movement, MovementAdmin)
admin.site.register(MovementDetail)