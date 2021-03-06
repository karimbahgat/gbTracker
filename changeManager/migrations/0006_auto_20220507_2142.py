# Generated by Django 3.2.11 on 2022-05-07 19:42

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('changeManager', '0005_auto_20220314_1521'),
    ]

    operations = [
        migrations.CreateModel(
            name='CodeType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('description', models.CharField(max_length=255)),
            ],
        ),
        migrations.AddField(
            model_name='boundaryreference',
            name='level',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name='BoundaryCode',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=100)),
                ('code_type', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='+', to='changeManager.codetype')),
            ],
        ),
        migrations.AddField(
            model_name='boundaryreference',
            name='codes',
            field=models.ManyToManyField(related_name='boundary_refs', to='changeManager.BoundaryCode'),
        ),
    ]
