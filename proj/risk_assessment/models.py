from django.db import models


class DatasetRecord(models.Model):
    dataset_name = models.CharField(max_length=255, db_index=True)
    row_index = models.IntegerField()
    data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "dataset_records"  
        ordering = ["dataset_name", "row_index"]

    def __str__(self):
        return f"{self.dataset_name} - Row {self.row_index}"
