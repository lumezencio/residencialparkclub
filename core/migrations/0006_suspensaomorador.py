# Adicionado em 2026-05-18: tabela de Suspensoes de moradores (Regimento Interno)

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_usuario_instagram_usuario_nome_empresa_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='SuspensaoMorador',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('inicio', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Inicio')),
                ('fim', models.DateTimeField(blank=True, help_text='Deixe em branco para suspensao por tempo indeterminado.', null=True, verbose_name='Fim')),
                ('motivo', models.TextField(verbose_name='Motivo')),
                ('ativa', models.BooleanField(default=True, help_text='Desmarque (ou clique em remover) para encerrar a suspensao. O historico fica preservado.', verbose_name='Ativa')),
                ('criada_em', models.DateTimeField(auto_now_add=True)),
                ('encerrada_em', models.DateTimeField(blank=True, null=True)),
                ('aplicada_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='suspensoes_aplicadas', to=settings.AUTH_USER_MODEL)),
                ('encerrada_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='suspensoes_encerradas', to=settings.AUTH_USER_MODEL)),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='suspensoes', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Suspensao de morador',
                'verbose_name_plural': 'Suspensoes de moradores',
                'ordering': ['-inicio'],
                'indexes': [models.Index(fields=['usuario', 'ativa'], name='core_suspen_usuario_e8c4b2_idx')],
            },
        ),
    ]
