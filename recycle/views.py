import os
import json
import shutil
import calendar
import datetime
from datetime import datetime
from django.http import FileResponse, HttpResponse
from django.utils import timezone
from django.http import JsonResponse
from django.views import View
from django.db.models import Sum, Count
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, get_object_or_404
from django.views.generic import TemplateView, FormView, DetailView, View
from .forms import FileUploadForm
from .models import UploadedFile, SimilarItem, Activity
from .utils import generate_recycle_instructions, generate_similar_items, information_extractor, generate_recycling_report, generate_recycling_instructions_pdf, home_view_details


class CalendarView(View):
    def get(self, request, year, month):
        today = datetime.now() 
        # Adjust year/month for comparison
        today_day = today.day if year == today.year and month == today.month else None
        # Get calendar data for the requested month
        cal = calendar.monthcalendar(year, month)
        month_name = datetime(year, month, 1).strftime('%B')
        calendar_days = []
        for week in cal:
            for i, cal_day in enumerate(week):
                if cal_day == 0:
                    calendar_days.append({
                        'day': '',
                        'class': 'other-month',
                        'has_event': False
                    })
                else:
                    is_today = (cal_day == today_day)
                    has_event = cal_day in []  # This logic would be for scheduling collection i.e create an event on the calendar
                    calendar_days.append({
                        'day': cal_day,
                        'class': 'today' if is_today else '',
                        'has_event': has_event
                    })
        return JsonResponse({
            'month_name': f"{month_name} {year}",
            'days': calendar_days
        })
        
class HomeView(LoginRequiredMixin, TemplateView):
    template_name = "recycle/home.html"
    login_url = 'accounts:login'  # Redirect unauthenticated users to login page
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['user_details'] = {
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'phone_number': user.phone_number,
        }
        recycled_items = UploadedFile.objects.filter(user=user, status="completed")
        details = home_view_details(recycled_items=recycled_items)
        if user.is_superuser:
            recent_activities = Activity.objects.all().order_by('-timestamp') # Superuser should see all the activities performed by all users
        else:
            recent_activities = Activity.objects.filter(user=user).order_by('-timestamp')[:4]  # Limit to 4 recent activities

        # Pass data to template
        context['total_cost_saved'] = round(details['total_cost_saved'], 2)
        context['total_weight'] = round(details['total_weight'], 2)
        context['total_carbon_offset'] = round(details['total_carbon_offset'], 2)
        context['recycled_items_count'] = recycled_items.count()
        context['waste_breakdown'] = {
            'labels': json.dumps(details['labels']),  # JSON-encoded for JavaScript and pie chart
            'weights': json.dumps(details['weights']),
        }
        context['calendar_data'] = {
            'month_name': f"{details['month_name']} {details['year']}",
            'weekdays': details['weekdays'],
            'days': details['calendar_days'],
            'current_year': details['year'],
            'current_month': details['month']
        }
        context['recent_activities'] = recent_activities
        return context
    

class UploadView(LoginRequiredMixin, FormView):
    template_name = "recycle/upload.html"
    form_class = FileUploadForm
    login_url = 'accounts:login'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['recent_uploads'] = UploadedFile.objects.filter(
            user=self.request.user
        ).order_by('-uploaded_at')
        context['user_details'] = {
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'phone_number': user.phone_number,
        }
        return context

    def form_valid(self, form):
        # Save the uploaded file
        upload = UploadedFile(
            user=self.request.user,
            file=form.cleaned_data['file'],
            filename=form.cleaned_data['file'].name,
            file_type=form.cleaned_data['file'].name.split('.')[-1].lower(),
            status='processing',
            progress=0
        )
        upload.save()
        # Log the activity
        Activity.objects.create(
            user=self.request.user,
            activity_type='upload',
            title='Waste Data Uploaded',
            timestamp=timezone.now(),
            meta=self.request.user.username
        )    
        result = generate_recycle_instructions(upload.file.path)
        if result != 'None':
            data = information_extractor(result)
            upload.status = 'completed'
            upload.progress = 100
            upload.item_name = data['item_name']
            upload.recycling_instructions = data['recycling_instruction']
            upload.item_description = data['item_description']
            upload.item_composition = data['item_composition']
            upload.item_weight = data['item_weight']
            upload.cost_saved = data['cost_saved']
            upload.recycling_center_name = data['recycling_center_name']
            upload.recycling_location = data['recycling_location']
            
            # Generate and save similar items if not already saved
            # Check if similar items already exist for this item_name
            if upload.item_name and not SimilarItem.objects.filter(item_name=upload.item_name).exists():
                similar_items = generate_similar_items(upload.item_composition, "google/gemma-3-27b-it:free")
                if similar_items and len(similar_items) == 4:
                    for item_name in similar_items:
                        #image_url = fetch_image_url(item_name)
                        SimilarItem.objects.create(
                            item_name=upload.item_name,
                            similar_item_name=item_name,
                            #image_url=image_url # Find a way to search online for each image of similiar items. Check out serper dev
                        )
            else:
                print('i was not run because i already have similiar items')
            Activity.objects.create(
                user=self.request.user,
                activity_type='report',
                title='Report Generated',
                timestamp=timezone.now(),
                meta=self.request.user.username
            )     
        else:
            upload.status = 'completed'
            upload.progress = 100
            upload.item_name = None
            upload.recycling_instructions = None
            upload.item_description = None
            upload.item_composition = None
            upload.item_weight = None
            upload.cost_saved = None
            upload.recycling_center_name = None
            upload.recycling_location = None
        upload.save()
        return redirect('recycle:results', pk=upload.id)
    
class ViewUploadView(LoginRequiredMixin, DetailView):
    # This is not complete
    # Find a way to view already uploaded images without needing a new html template
    model = UploadedFile
    template_name = "recycle/view_upload.html"
    context_object_name = 'upload'
    login_url = 'accounts:login'

    def get_queryset(self):
        return UploadedFile.objects.filter(user=self.request.user)

class DownloadUploadView(LoginRequiredMixin, View):
    login_url = 'accounts:login'

    def get(self, request, pk):
        upload = get_object_or_404(UploadedFile, pk=pk, user=request.user)
        return FileResponse(upload.file, as_attachment=True, filename=upload.filename)

class DeleteUploadView(LoginRequiredMixin, View):
    login_url = 'accounts:login'

    def post(self, request, pk):
        upload = get_object_or_404(UploadedFile, pk=pk, user=request.user)
        upload.delete()
        return redirect('recycle:upload')

    
class ResultsView(LoginRequiredMixin, DetailView):
    template_name = "recycle/result.html"
    login_url = 'accounts:login'
    model = UploadedFile
    context_object_name = 'upload' 

    def get_queryset(self):
        return UploadedFile.objects.filter(user=self.request.user)
    def get_object(self, queryset=None):
        if queryset is None:
            queryset = self.get_queryset()
        return get_object_or_404(queryset, pk=self.kwargs['pk'])
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        upload = self.get_object()
        context['similar_items'] = SimilarItem.objects.filter(item_name=upload.item_name)
        return context
    




class ExportReportView(LoginRequiredMixin, View):
    login_url = 'accounts:login'

    def get(self, request, *args, **kwargs):
        # Generate the report PDF buffer
        buffer = generate_recycling_report(request.user)

        # Return the PDF as a downloadable response
        response = FileResponse(
            buffer,
            as_attachment=True,
            filename=f'recycling_report_{datetime.now().strftime("%Y%m%d_%H%M")}.pdf'
        )
        return response
    
class DownloadInstructionsView(LoginRequiredMixin, View):
    login_url = 'accounts:login'
    def get(self, request, *args, **kwargs):
        upload = get_object_or_404(UploadedFile, pk=self.kwargs['pk'], user=request.user)
        buffer = generate_recycling_instructions_pdf(upload)
        response = FileResponse(
            buffer,
            as_attachment=True,
            filename=f'recycling_instructions_{upload.item_name or "item"}_{datetime.now().strftime("%Y%m%d_%H%M")}.pdf'
        )
        return response
    