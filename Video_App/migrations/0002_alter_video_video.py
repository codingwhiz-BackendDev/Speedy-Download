# Generated by Django 4.1.4 on 2023-02-25 03:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Video_App', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='video',
            name='video',
            field=models.FileField(null=True, upload_to='videos'),
        ),
    ]