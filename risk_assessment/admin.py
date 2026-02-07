from django.contrib import admin
from .models import DatasetRecord

@admin.register(DatasetRecord)
class DatasetRecordAdmin(admin.ModelAdmin):
    list_display = ("dataset_name", "row_index", "created_at")
    search_fields = ("dataset_name",)


















# from django.contrib import admin
# from .models import DemographicRecord


# @admin.register(DemographicRecord)
# class DemographicRecordAdmin(admin.ModelAdmin):
#     list_display = [
#         'record_id', 'age', 'gender', 'state', 'district', 
#         'monthly_income', 'occupation', 'education'
#     ]

#     list_filter = [
#         'gender', 'state', 'area_type', 'education',
#         'marital_status', 'disability', 'chronic_illness'
#     ]

#     search_fields = [
#         'record_id', 'state', 'district', 'occupation'
#     ]

#     ordering = ['record_id']
#     list_per_page = 50
    
#     fieldsets = (
#         ('Basic Information', {
#             'fields': ('record_id', 'age', 'gender')
#         }),
#         ('Location', {
#             'fields': ('state', 'district', 'area_type')
#         }),
#         ('Education & Employment', {
#             'fields': (
#                 'education', 'occupation', 'industry', 
#                 'employment_type', 'monthly_income'
#             )
#         }),
#         ('Household & Personal', {
#             'fields': (
#                 'household_size', 'marital_status', 'land_owned_acres'
#             )
#         }),
#         ('Health & Migration', {
#             'fields': (
#                 'disability', 'chronic_illness', 'migration_status'
#             )
#         }),
#         ('Timestamps', {
#             'fields': ('created_at', 'updated_at'),
#             'classes': ('collapse',)
#         }),
#     )
    
#     readonly_fields = ['created_at', 'updated_at']
