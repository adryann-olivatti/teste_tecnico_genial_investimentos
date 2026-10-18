import json

from suitability import validar_suitability_seguro


def main():
    perfil_cliente = {"perfil": "Moderado", "score_max_risco": 2.5}

    carteira_atual = [
        {"ativo": "CDB XPTO", "risco": 1.2, "valor_investido": 50000.0},
        {"ativo": "Ação ABC", "risco": 4.0, "valor_investido": 10000.0},
    ]

    cenarios = [
        ("Aprovado", {"ativo": "FII YYY", "risco": 1.5, "valor_ordem": 20000.0}),
        ("Alerta (Desenquadramento Leve)", {"ativo": "Ação High Risk", "risco": 4.5, "valor_ordem": 30000.0}),
        ("Rejeitado (Desenquadramento Severo)", {"ativo": "Crypto XYZ", "risco": 5.0, "valor_ordem": 80000.0}),
    ]

    for i, (titulo, ordem) in enumerate(cenarios, start=1):
        print(f"\n--- Testando Ordem {i}: {titulo} ---")
        resultado = validar_suitability_seguro(perfil_cliente, carteira_atual, ordem)
        print(json.dumps(resultado, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
