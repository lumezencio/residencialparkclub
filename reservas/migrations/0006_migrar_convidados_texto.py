"""Move os convidados que estavam no campo de texto para registros proprios.

O campo Reserva.convidados guardava um nome por linha, sem CPF. Cada linha vira
um Convidado com o CPF em branco, preservando o historico ja existente.
"""
from django.db import migrations


def texto_para_registros(apps, schema_editor):
    Reserva = apps.get_model("reservas", "Reserva")
    Convidado = apps.get_model("reservas", "Convidado")

    novos = []
    for reserva in Reserva.objects.exclude(convidados="").exclude(convidados=None):
        if Convidado.objects.filter(reserva=reserva).exists():
            continue  # ja migrada
        for linha in reserva.convidados.splitlines():
            nome = linha.strip()[:120]
            if nome:
                novos.append(Convidado(reserva=reserva, nome=nome, cpf=""))
    if novos:
        Convidado.objects.bulk_create(novos)


def desfazer(apps, schema_editor):
    """Os nomes continuam no campo de texto, entao basta apagar os registros."""
    Convidado = apps.get_model("reservas", "Convidado")
    Convidado.objects.filter(cpf="").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("reservas", "0005_convidado"),
    ]

    operations = [
        migrations.RunPython(texto_para_registros, desfazer),
    ]
