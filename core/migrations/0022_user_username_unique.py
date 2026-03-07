# Generated manually to switch authentication to username safely.

from django.db import migrations, models


def make_usernames_unique(apps, schema_editor):
    User = apps.get_model('core', 'User')
    used = set()

    for user in User.objects.all().order_by('id'):
        current = (user.username or '').strip()

        if not current:
            current = f'user{user.id}'

        candidate = current
        suffix = 1
        while candidate in used or User.objects.exclude(pk=user.pk).filter(username=candidate).exists():
            candidate = f'{current}_{suffix}'
            suffix += 1

        if candidate != user.username:
            user.username = candidate
            user.save(update_fields=['username'])

        used.add(candidate)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0021_company_product_custom_fields_config_and_more'),
    ]

    operations = [
        migrations.RunPython(make_usernames_unique, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='user',
            name='username',
            field=models.CharField(max_length=150, unique=True, verbose_name='Usuario'),
        ),
    ]
