# Generated by Django 5.1.7 on 2025-03-12 02:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_producto_latest_price'),
    ]

    operations = [
        migrations.AddField(
            model_name='cliente',
            name='status',
            field=models.BooleanField(default=True),
        ),
    ]
