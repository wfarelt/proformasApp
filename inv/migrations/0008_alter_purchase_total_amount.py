# Generated by Django 5.1.7 on 2025-04-12 03:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inv', '0007_purchase_purchasedetail'),
    ]

    operations = [
        migrations.AlterField(
            model_name='purchase',
            name='total_amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
    ]
