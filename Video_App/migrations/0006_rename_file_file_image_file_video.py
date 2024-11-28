# Generated by Django 4.1.4 on 2099-02-16 20:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Video_App', '0005_file_delete_image_delete_video'),
    ]

    operations = [
        migrations.RenameField(
            model_name='file',
            old_name='file',
            new_name='image',
        ),
        migrations.AddField(
            model_name='file',
            name='video',
            field=models.FileField(null=True, upload_to='videos'),
        ),
    ]
