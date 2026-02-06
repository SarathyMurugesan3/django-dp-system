from django.urls import path
from . import views

urlpatterns = [
    path('assess-table/', views.assess_table_risk, name='assess_table_risk'),
    path('list-tables/', views.list_tables, name='list_tables'),
    path('assess-query/', views.assess_query_risk, name='assess_query_risk'),
    path('assess-dataset/', views.assess_dataset_risk, name='assess_dataset_risk'),
]
