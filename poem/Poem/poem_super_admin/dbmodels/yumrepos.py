from django.db import models


class YumRepo(models.Model):
    name = models.TextField(unique=True)
    description = models.TextField()

    class Meta:
        app_label = 'poem_super_admin'
