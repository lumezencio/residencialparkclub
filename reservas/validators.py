"""Validacao e formatacao de CPF dos convidados."""
import re


def limpar_cpf(valor):
    """Deixa so os digitos."""
    return re.sub(r"\D", "", valor or "")


def cpf_valido(valor):
    """Confere os dois digitos verificadores do CPF."""
    cpf = limpar_cpf(valor)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    for tamanho in (9, 10):
        soma = sum(int(cpf[i]) * (tamanho + 1 - i) for i in range(tamanho))
        digito = (soma * 10) % 11
        if digito == 10:
            digito = 0
        if digito != int(cpf[tamanho]):
            return False
    return True


def formatar_cpf(valor):
    """000.000.000-00 (devolve o que veio se nao tiver 11 digitos)."""
    cpf = limpar_cpf(valor)
    if len(cpf) != 11:
        return valor or ""
    return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
