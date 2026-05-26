import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0002_saldo'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Movimentacao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('tipo', models.CharField(
                    choices=[('entrada', 'Entrada'), ('saida', 'Saída')],
                    default='saida',
                    max_length=10,
                )),
                ('titulo', models.CharField(max_length=120)),
                ('categoria', models.CharField(
                    blank=True,
                    choices=[
                        ('moradia', 'Moradia'),
                        ('alimentacao', 'Alimentacao'),
                        ('transporte', 'Transporte'),
                        ('lazer', 'Lazer'),
                        ('saude', 'Saude'),
                        ('educacao', 'Educacao'),
                        ('outros', 'Outros'),
                    ],
                    default='',
                    max_length=20,
                )),
                ('valor', models.DecimalField(decimal_places=2, max_digits=10)),
                ('data', models.DateField()),
                ('observacao', models.TextField(blank=True)),
                ('usuario', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='movimentacoes',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Movimentacao',
                'verbose_name_plural': 'Movimentacoes',
                'ordering': ['-data', '-created_at'],
            },
        ),
        migrations.DeleteModel(
            name='Gasto',
        ),
    ]
