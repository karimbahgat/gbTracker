# Generated by Django 3.2.11 on 2022-05-19 20:24

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('changeManager', '0006_auto_20220507_2142'),
    ]

    operations = [
        migrations.AlterField(
            model_name='boundaryreference',
            name='parent',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='children', to='changeManager.boundaryreference'),
        ),
        migrations.AlterField(
            model_name='boundaryreference',
            name='source',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='boundary_refs', to='changeManager.boundarysource'),
        ),
    ]