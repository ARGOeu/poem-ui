# Generated by Django 2.2.12 on 2020-07-16 14:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('poem_super_admin', '0022_metrictags'),
    ]

    operations = [
        migrations.AddField(
            model_name='metrictemplate',
            name='tags',
            field=models.ManyToManyField(to='poem_super_admin.MetricTags'),
        ),
    ]