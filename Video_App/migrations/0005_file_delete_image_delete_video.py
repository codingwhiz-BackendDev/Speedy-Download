# Generated by Django 4.1.4 on 2099-02-16 18:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Video_App', '0004_image_remove_video_image'),
    ]

    operations = [
        migrations.CreateModel(
            name='File',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('caption', models.CharField(max_length=50)),
                ('file', models.FileField(null=True, upload_to='videos')),
            ],
        ),
        migrations.DeleteModel(
            name='Image',
        ),
        migrations.DeleteModel(
            name='Video',
        ),
    ]
