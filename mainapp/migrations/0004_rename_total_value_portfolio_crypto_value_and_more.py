# Generated by Django 5.0.6 on 2024-05-25 17:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mainapp', '0003_alter_referal_referrer_alter_portfolio_user_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='portfolio',
            old_name='total_value',
            new_name='crypto_value',
        ),
        migrations.RemoveField(
            model_name='profile',
            name='cash_balance',
        ),
        migrations.AddField(
            model_name='portfolio',
            name='cash_balance',
            field=models.DecimalField(decimal_places=2, default=100000.0, max_digits=15),
        ),
    ]
