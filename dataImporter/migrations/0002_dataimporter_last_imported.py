# Generated by Django 3.2.11 on 2022-05-08 21:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dataImporter', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='dataimporter',
            name='last_imported',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
