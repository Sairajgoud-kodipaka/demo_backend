# Generated manually to make tenant field optional

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0002_tenant_google_maps_url'),
        ('clients', '0005_alter_client_summary_notes'),
    ]

    operations = [
        migrations.AlterField(
            model_name='client',
            name='tenant',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='clients', to='tenants.tenant'),
        ),
    ] 