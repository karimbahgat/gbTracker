# Generated by Django 3.2.11 on 2022-05-22 11:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('changeManager', '0007_auto_20220519_2224'),
    ]

    operations = [
        migrations.AddField(
            model_name='boundarysource',
            name='valid_from',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='boundarysource',
            name='valid_to',
            field=models.DateField(blank=True, null=True),
        ),
    ]