from django.contrib import admin
from .models import UploadedFile, SimilarItem, Activity
# Register your models here.
@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    list_display = ('item_name', 'user', 'uploaded_at', 'status', 'progress')

@admin.register(SimilarItem)
class SimilarItemAdmin(admin.ModelAdmin):
    list_display = ('item_name', 'similar_item_name', 'image_url', 'created_at')
    list_filter = ('item_name', 'created_at')
    search_fields = ('item_name', 'similar_item_name')
    
@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('activity_type', 'title', 'timestamp')
    list_filter = ('activity_type', 'timestamp')
