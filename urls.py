from django.urls import path, include

urlpatterns = [
    # Risk Assessment APIs
    path('api/', include('risk_assessment.urls')),

    # Privacy APIs
    path('api/privacy/', include('proj.privacy_urls')),
]

