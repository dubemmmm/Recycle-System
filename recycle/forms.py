from django import forms
from django.core.validators import FileExtensionValidator

class FileUploadForm(forms.Form):
    file = forms.ImageField(
        label='Upload an Image',
        help_text='Upload an image of an item to get recycling instructions',
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'gif']),
        ],
        widget=forms.FileInput(attrs={'class': 'form-control-file', 'accept': 'image/*'})
    )