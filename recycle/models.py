from django.db import models
from accounts.models import UserManager, CustomUser
from django.utils import timezone

# Create your models here.
class UploadedFile(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    file = models.FileField(upload_to='recycling_uploads/')
    filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=50)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed')
    ])
    progress = models.IntegerField(default=0)
    item_name = models.CharField(blank=True, null=True, max_length=100,)
    recycling_instructions = models.TextField(blank=True, null=True)
    item_description = models.CharField(blank=True, null=True, max_length=100,)
    item_composition = models.CharField(blank=True, null=True, max_length=100,)
    item_weight = models.FloatField(blank=True, null=True)  # In kg
    cost_saved = models.FloatField(blank=True, null=True)  # In currency (e.g., USD)
    recycling_center_name = models.CharField(blank=True, null=True, max_length=100,)
    recycling_location = models.CharField(blank=True, null=True, max_length=100,)
    
    def __str__(self):
        return self.filename

class SimilarItem(models.Model):
    item_name = models.CharField(max_length=255, blank=True, null=True, db_index=True)  # Key for grouping similar items
    similar_item_name = models.CharField(max_length=255)
    image_url = models.URLField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.similar_item_name

    class Meta:
        unique_together = ('item_name', 'similar_item_name')  # Prevent duplicates
        indexes = [
            models.Index(fields=['item_name']),
        ]
        
class Activity(models.Model):
    ACTIVITY_TYPES = (
        ('upload', 'Waste Data Uploaded'),
        ('report', 'Report Generated'),
        ('schedule', 'Collection Scheduled'),
        ('member', 'Team Member Added'),
    )

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    title = models.CharField(max_length=100)
    timestamp = models.DateTimeField(default=timezone.now)
    meta = models.CharField(max_length=100, blank=True, null=True)  # Additional info (e.g., user name)

    def __str__(self):
        return f"{self.get_activity_type_display()} - {self.timestamp}"

    class Meta:
        ordering = ['-timestamp']  # Latest activities first