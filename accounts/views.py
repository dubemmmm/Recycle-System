from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from django.views.generic import TemplateView
from .forms import SignupForm
from django.urls import reverse
import logging
logger = logging.getLogger(__name__)

# Create your views here.

def signup(request): # Change this to a class based view (CBV)
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            logger.debug(f"Signup successful for {user.email}, redirecting to accounts:login")
            return redirect('accounts:login') 
    else:
        form = SignupForm()
    return render(request, 'accounts/signup.html', {'form': form})

class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True 
    
    def form_valid(self, form):
        logger.debug(f"Login attempt for {form.cleaned_data['username']}")
        response = super().form_valid(form)
        logger.debug(f"Login successful for {self.request.user.email}, redirecting to {self.get_success_url()}")
        return response

    def form_invalid(self, form):
        logger.debug(f"Login failed: {form.errors}")
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse('recycle:home')
    

class CustomLogoutView(LogoutView):
    next_page = 'landing'  
    
