"""Motor de Validação de Suitability de Carteira (CVM 30).

Decisões de projeto:
  * Aritmética exata com ``Decimal``: elimina erros de ponto flutuante
    (ex.: 3.0 * 1.1 == 3.3000000000000003) nas fronteiras de decisão.
  * A decisão usa o valor EXATO; o arredondamento é só para exibição.
  * Validação estrita das entradas, com erro claro (``ValidacaoEntradaError``).
  * ``validar_suitability_seguro`` nunca levanta exceção e é "fail-closed":
    qualquer falha resulta em status "Erro", jamais em "Aprovado".
  * Nenhuma entrada é modificada.

Faixas de decisão (score = ``score_max_risco`` do cliente):
  * risco projetado <= score x FATOR_ALERTA ................. Aprovado
  * score x FATOR_ALERTA < risco <= score x FATOR_REJEICAO ... Alerta
  * risco projetado > score x FATOR_REJEICAO ................. Rejeitado
O FATOR_ALERTA (1,1) vem do enunciado. O FATOR_REJEICAO (1,3) é uma PREMISSA:
o enunciado não define onde começa o desenquadramento severo; qualquer valor
entre ~1,11 e 1,4 reproduz os exemplos de saída do enunciado (2,78 = Alerta e
3,5 = Rejeitado para score 2,5).
"""
from __future__ import annotations

from collections.abc import Mapping
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation, localcontext
from typing import Any, Dict, Iterable, Optional, Tuple

FATOR_ALERTA = Decimal("1.1")  # Regra Genial Hipotética: alerta se risco > score x 1,1
FATOR_REJEICAO = Decimal("1.3")  # Premissa: acima de score x 1,3 o desenquadramento é severo
LIMITE_MAXIMO = Decimal(10) ** 18  # teto de sanidade para valores de entrada
_DUAS_CASAS = Decimal("0.01")
_PRECISAO = 60


class ValidacaoEntradaError(ValueError):
    """Entrada inválida (tipo, ausência de campo, valor fora do domínio)."""


# --------------------------------------------------------------------------
# Conversão e validação
# --------------------------------------------------------------------------
def _para_decimal(valor: Any, campo: str) -> Decimal:
    """Converte int/float/Decimal/str numérica em Decimal finito e limitado."""
    if isinstance(valor, bool):
        raise ValidacaoEntradaError(f"'{campo}' deve ser numérico, não booleano.")
    try:
        if isinstance(valor, Decimal):
            numero = valor
        elif isinstance(valor, int):
            numero = Decimal(valor)
        elif isinstance(valor, float):
            numero = Decimal(repr(valor))  # repr evita o ruído binário do float
        elif isinstance(valor, str):
            numero = Decimal(valor.strip())
        else:
            raise ValidacaoEntradaError(
                f"'{campo}' deve ser numérico (recebido: {type(valor).__name__})."
            )
    except InvalidOperation:
        raise ValidacaoEntradaError(f"'{campo}' não é um número válido: {valor!r}.") from None

    if not numero.is_finite():
        raise ValidacaoEntradaError(f"'{campo}' deve ser um número finito (NaN/Infinito não são aceitos).")
    if abs(numero) > LIMITE_MAXIMO:
        raise ValidacaoEntradaError(f"'{campo}' excede o limite permitido ({LIMITE_MAXIMO}).")
    return numero


def _exigir_dict(valor: Any, nome: str) -> Mapping:
    if not isinstance(valor, Mapping):
        raise ValidacaoEntradaError(f"'{nome}' deve ser um dicionário (recebido: {type(valor).__name__}).")
    return valor


def _exigir_chave(dados: Mapping, chave: str, nome: str) -> Any:
    if chave not in dados or dados[chave] is None:
        raise ValidacaoEntradaError(f"Campo obrigatório ausente em {nome}: '{chave}'.")
    return dados[chave]


def _validar_perfil(perfil_cliente: Any) -> Decimal:
    perfil = _exigir_dict(perfil_cliente, "perfil_cliente")
    score = _para_decimal(_exigir_chave(perfil, "score_max_risco", "perfil_cliente"), "score_max_risco")
    if score <= 0:
        raise ValidacaoEntradaError("'score_max_risco' deve ser maior que zero.")
    return score


def _validar_carteira(carteira: Any) -> Tuple[Tuple[Decimal, Decimal], ...]:
    if isinstance(carteira, (str, bytes, Mapping)) or not isinstance(carteira, Iterable):
        raise ValidacaoEntradaError("'carteira_atual' deve ser uma lista de ativos.")
    itens = []
    for i, ativo in enumerate(carteira):
        nome = f"carteira_atual[{i}]"
        ativo = _exigir_dict(ativo, nome)
        risco = _para_decimal(_exigir_chave(ativo, "risco", nome), f"{nome}.risco")
        valor = _para_decimal(_exigir_chave(ativo, "valor_investido", nome), f"{nome}.valor_investido")
        if risco < 0:
            raise ValidacaoEntradaError(f"'{nome}.risco' não pode ser negativo.")
        if valor < 0:
            raise ValidacaoEntradaError(f"'{nome}.valor_investido' não pode ser negativo.")
        itens.append((risco, valor))
    return tuple(itens)


def _validar_ordem(nova_ordem: Any) -> Tuple[Decimal, Decimal]:
    ordem = _exigir_dict(nova_ordem, "nova_ordem")
    risco = _para_decimal(_exigir_chave(ordem, "risco", "nova_ordem"), "nova_ordem.risco")
    valor = _para_decimal(_exigir_chave(ordem, "valor_ordem", "nova_ordem"), "nova_ordem.valor_ordem")
    if risco < 0:
        raise ValidacaoEntradaError("'nova_ordem.risco' não pode ser negativo.")
    if valor <= 0:
        raise ValidacaoEntradaError("'nova_ordem.valor_ordem' deve ser maior que zero.")
    return risco, valor


# --------------------------------------------------------------------------
# Cálculo
# --------------------------------------------------------------------------
def _media_ponderada(itens: Iterable[Tuple[Decimal, Decimal]]) -> Tuple[Decimal, Decimal]:
    with localcontext() as ctx:
        ctx.prec = _PRECISAO
        soma_ponderada = Decimal(0)
        total = Decimal(0)
        for risco, valor in itens:
            soma_ponderada += risco * valor
            total += valor
        if total <= 0:
            raise ValidacaoEntradaError("O valor total da carteira deve ser maior que zero.")
        return soma_ponderada / total, total


def calcular_risco_carteira(
    carteira: Any, nova_ordem: Optional[Mapping] = None
) -> Tuple[Decimal, Decimal]:
    """Média ponderada do risco da carteira (atual ou projetada).

    Retorna ``(risco_ponderado, valor_total_investido)`` como ``Decimal``.
    Se ``nova_ordem`` for informada, ela é somada à carteira (risco projetado).
    """
    itens = list(_validar_carteira(carteira))
    if nova_ordem is not None:
        itens.append(_validar_ordem(nova_ordem))
    return _media_ponderada(itens)


def _arredondar(valor: Decimal) -> float:
    with localcontext() as ctx:
        ctx.prec = _PRECISAO
        return float(valor.quantize(_DUAS_CASAS, rounding=ROUND_HALF_UP))


def _fmt(valor: Decimal) -> str:
    with localcontext() as ctx:
        ctx.prec = _PRECISAO
        return f"{valor.quantize(_DUAS_CASAS, rounding=ROUND_HALF_UP):.2f}"


# --------------------------------------------------------------------------
# API pública
# --------------------------------------------------------------------------
def _validar_fatores(fator_alerta: Any, fator_rejeicao: Any) -> Tuple[Decimal, Decimal]:
    """Resolve os fatores (padrão ou informados) e garante 1 <= alerta < rejeição."""
    alerta = _para_decimal(FATOR_ALERTA if fator_alerta is None else fator_alerta, "fator_alerta")
    rejeicao = _para_decimal(FATOR_REJEICAO if fator_rejeicao is None else fator_rejeicao, "fator_rejeicao")
    if alerta < 1:
        raise ValidacaoEntradaError("'fator_alerta' deve ser maior ou igual a 1.")
    if rejeicao <= alerta:
        raise ValidacaoEntradaError("'fator_rejeicao' deve ser maior que 'fator_alerta'.")
    return alerta, rejeicao


def validar_suitability(
    perfil_cliente: Any,
    carteira_atual: Any,
    nova_ordem: Any,
    fator_alerta: Any = None,
    fator_rejeicao: Any = None,
) -> Dict[str, Any]:
    """Valida a nova ordem de compra contra o perfil e a carteira do cliente.

    ``fator_alerta`` e ``fator_rejeicao`` são opcionais (padrão: 1,1 e 1,3).
    Levanta ``ValidacaoEntradaError`` se a entrada for inválida.
    """
    score_max = _validar_perfil(perfil_cliente)
    f_alerta, f_rejeicao = _validar_fatores(fator_alerta, fator_rejeicao)
    itens = list(_validar_carteira(carteira_atual))
    itens.append(_validar_ordem(nova_ordem))

    risco_projetado, _ = _media_ponderada(itens)
    with localcontext() as ctx:
        ctx.prec = _PRECISAO
        limite_alerta = score_max * f_alerta
        limite_rejeicao = score_max * f_rejeicao

    # A decisão usa o valor EXATO (sem arredondar).
    if risco_projetado <= limite_alerta:
        status = "Aprovado"
        mensagem = "Ordem executada. Carteira em conformidade."
    elif risco_projetado <= limite_rejeicao:
        status = "Alerta"
        mensagem = (
            f"Atenção: O risco da carteira ultrapassará o limite de {_fmt(limite_alerta)}. "
            f"É necessário termo de ciência."
        )
    else:
        status = "Rejeitado"
        mensagem = "Risco excessivo. A operação viola a política de Suitability."

    return {
        "status": status,
        "risco_projetado": _arredondar(risco_projetado),
        "mensagem": mensagem,
    }


def validar_suitability_seguro(
    perfil_cliente: Any,
    carteira_atual: Any,
    nova_ordem: Any,
    fator_alerta: Any = None,
    fator_rejeicao: Any = None,
) -> Dict[str, Any]:
    """Versão que NUNCA levanta exceção e é fail-closed.

    Qualquer problema (entrada inválida ou erro inesperado) retorna
    ``status == "Erro"``; a ordem nunca é aprovada em caso de falha.
    """
    try:
        return validar_suitability(
            perfil_cliente, carteira_atual, nova_ordem, fator_alerta, fator_rejeicao
        )
    except ValidacaoEntradaError as exc:
        return {"status": "Erro", "risco_projetado": None,
                "mensagem": f"Entrada inválida: {exc}"}
    except Exception:  # noqa: BLE001 - fail-closed deliberado
        return {"status": "Erro", "risco_projetado": None,
                "mensagem": "Erro interno ao validar suitability. Ordem não autorizada."}
