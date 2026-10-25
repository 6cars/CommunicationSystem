from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('counseling', '0004_experience_db_and_dialogue_logs'),
    ]

    operations = [
        migrations.AddField(
            model_name='counselingsession',
            name='log_mode',
            field=models.CharField(choices=[('full', 'ログを取る'), ('anonymous', 'ログを取らない（匿名）')], default='full', max_length=16),
        ),
    ]
