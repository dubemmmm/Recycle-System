from django.contrib.auth import logout
from django.conf import settings
from datetime import datetime, timedelta
import time


# This is to ensure the authenticated user is logged out after a certain amount of time
class AutoLogoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            return self.get_response(request)

        last_activity = request.session.get('last_activity')

        if last_activity:
            last_activity_time = datetime.fromtimestamp(float(last_activity))
            inactivity_duration = datetime.now() - last_activity_time
            max_inactivity = timedelta(seconds=settings.SESSION_EXPIRE_SECONDS)

            if inactivity_duration > max_inactivity:
                logout(request)
                request.session.flush()

        request.session['last_activity'] = str(time.time())

        return self.get_response(request)