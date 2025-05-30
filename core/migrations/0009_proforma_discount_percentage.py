# Generated by Django 5.1.7 on 2025-03-19 00:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_remove_user_empresa_remove_user_logo_user_company'),
    ]

    operations = [
        migrations.AddField(
            model_name='proforma',
            name='discount_percentage',
            field=models.DecimalField(decimal_places=2, default=0.0, help_text='Descuento en porcentaje (ej. 10.00 para 10%)', max_digits=5),
        ),
    ]
