from django.urls import path, include
from django.http import HttpResponse
from django.conf import settings
import os

def serve_react_app(request):
    try:
        with open(os.path.join(settings.BASE_DIR, 'frontend', 'dist', 'index.html'), 'r', encoding='utf-8') as f:
            return HttpResponse(f.read())
    except FileNotFoundError:
        return HttpResponse("Frontend build not found. Run npm run build in frontend directory.", status=500)

urlpatterns = [
    # React App Root
    path('', serve_react_app, name='index'),

    # Risk Assessment APIs
    path('api/', include('risk_assessment.urls')),

    # Privacy APIs
    path('api/privacy/', include('proj.privacy_urls')),
]

