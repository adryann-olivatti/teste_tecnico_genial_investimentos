"""Testes do motor de suitability.

Escritos com ``unittest`` (biblioteca padrão): rodam com
``python -m unittest -v`` e também com ``pytest``.
"""
import copy
import math
import random
import unittest
from decimal import Decimal

from suitability import (
    ValidacaoEntradaError,
    calcular_risco_carteira,
    validar_suitability,
    validar_suitability_seguro,
)

PERFIL = {"perfil": "Moderado", "score_max_risco": 2.5}
CARTEIRA = [
    {"ativo": "CDB XPTO", "risco": 1.2, "valor_investido": 50000.0},
    {"ativo": "Ação ABC", "risco": 4.0, "valor_investido": 10000.0},
]


def ordem(risco, valor):
    return {"ativo": "X", "risco": risco, "valor_ordem": valor}


def fronteira(score, risco_proj):
    """Carteira de um único ativo cujo risco projetado é exatamente risco_proj."""
    return validar_suitability(
        {"score_max_risco": score},
        [{"ativo": "A", "risco": risco_proj, "valor_investido": 100}],
        ordem(risco_proj, 100),
    )


class TestCalculo(unittest.TestCase):
    def test_risco_atual(self):
        risco, total = calcular_risco_carteira(CARTEIRA)
        self.assertEqual(round(risco, 4), Decimal("1.6667"))
        self.assertEqual(total, Decimal(60000))

    def test_risco_projetado(self):
        risco, total = calcular_risco_carteira(CARTEIRA, ordem(3.5, 5000))
        self.assertEqual(round(risco, 2), Decimal("1.81"))
        self.assertEqual(total, Decimal(65000))

    def test_carteira_vazia_com_ordem(self):
        r = validar_suitability(PERFIL, [], ordem(2.0, 1000))
        self.assertEqual((r["status"], r["risco_projetado"]), ("Aprovado", 2.0))

    def test_carteira_vazia_sem_ordem_levanta_erro(self):
        with self.assertRaises(ValidacaoEntradaError):
            calcular_risco_carteira([])

    def test_ativo_com_valor_zero_e_aceito(self):
        r = validar_suitability(PERFIL, [{"risco": 9, "valor_investido": 0}], ordem(1, 100))
        self.assertEqual(r["status"], "Aprovado")


class TestDecisao(unittest.TestCase):
    """Faixas (score 2,5): Aprovado <= 2,75 | Alerta <= 3,25 | Rejeitado > 3,25."""

    def test_aprovado(self):
        r = validar_suitability(PERFIL, CARTEIRA, ordem(1.5, 20000))
        self.assertEqual(r["status"], "Aprovado")
        self.assertEqual(r["risco_projetado"], 1.63)
        self.assertEqual(r["mensagem"], "Ordem executada. Carteira em conformidade.")

    def test_exemplo_do_enunciado_fii(self):
        self.assertEqual(validar_suitability(PERFIL, CARTEIRA, ordem(3.5, 5000))["status"], "Aprovado")

    def test_exemplos_de_saida_do_enunciado(self):
        # Aprovado 2.1 | Alerta 2.78 | Rejeitado 3.5 (score 2.5)
        for risco, status in [("2.1", "Aprovado"), ("2.78", "Alerta"), ("3.5", "Rejeitado")]:
            with self.subTest(risco=risco):
                r = fronteira(2.5, risco)
                self.assertEqual(r["status"], status)
                self.assertEqual(r["risco_projetado"], float(risco))

    def test_mensagens_exatas_do_enunciado(self):
        self.assertEqual(
            fronteira(2.5, "2.78")["mensagem"],
            "Atenção: O risco da carteira ultrapassará o limite de 2.75. É necessário termo de ciência.",
        )
        self.assertEqual(
            fronteira(2.5, "3.5")["mensagem"],
            "Risco excessivo. A operação viola a política de Suitability.",
        )

    def test_alerta(self):
        r = validar_suitability(PERFIL, CARTEIRA, ordem(5.0, 40000))
        self.assertEqual(r["status"], "Alerta")
        self.assertEqual(r["risco_projetado"], 3.0)
        self.assertIn("2.75", r["mensagem"])
        self.assertIn("termo de ciência", r["mensagem"])

    def test_rejeitado(self):
        r = validar_suitability(PERFIL, CARTEIRA, ordem(5.0, 80000))
        self.assertEqual(r["status"], "Rejeitado")
        self.assertGreater(r["risco_projetado"], 3.25)

    def test_entre_score_e_limite_de_alerta_ainda_e_aprovado(self):
        # O alerta só dispara ACIMA de score x 1,1 (2,75), não acima do score.
        self.assertEqual(fronteira(2.5, 2.5)["status"], "Aprovado")
        self.assertEqual(fronteira(2.5, "2.6")["status"], "Aprovado")

    def test_fronteira_exatamente_no_limite_de_alerta_e_aprovado(self):
        self.assertEqual(fronteira(2.5, 2.75)["status"], "Aprovado")

    def test_logo_acima_do_limite_de_alerta_e_alerta(self):
        self.assertEqual(fronteira(2.5, "2.7501")["status"], "Alerta")

    def test_fronteira_exatamente_no_limite_de_rejeicao_e_alerta(self):
        self.assertEqual(fronteira(2.5, 3.25)["status"], "Alerta")

    def test_logo_acima_do_limite_de_rejeicao_e_rejeitado(self):
        self.assertEqual(fronteira(2.5, "3.2501")["status"], "Rejeitado")

    def test_decisao_usa_valor_exato_nao_o_arredondado(self):
        r = fronteira(2.5, "3.2504")
        self.assertEqual(r["status"], "Rejeitado")
        self.assertEqual(r["risco_projetado"], 3.25)  # exibição arredondada
        r = fronteira(2.5, "2.7504")
        self.assertEqual(r["status"], "Alerta")
        self.assertEqual(r["risco_projetado"], 2.75)

    def test_sem_ruido_de_float_na_fronteira(self):
        # 3.0 * 1.1 == 3.3000000000000003 em float; com Decimal é exato.
        self.assertEqual(fronteira(3.0, 3.3)["status"], "Aprovado")
        self.assertEqual(fronteira(3.0, "3.3001")["status"], "Alerta")
        self.assertEqual(fronteira(3.0, 3.9)["status"], "Alerta")
        self.assertEqual(fronteira(3.0, "3.9001")["status"], "Rejeitado")

    def test_aceita_int_decimal_e_string(self):
        for score, risco in [(3, 3), (Decimal("2.5"), Decimal("2.5")), ("2.5", "2.5")]:
            self.assertEqual(fronteira(score, risco)["status"], "Aprovado")

    def test_valores_enormes_e_minusculos(self):
        r = validar_suitability(
            {"score_max_risco": 2.5},
            [{"risco": 1, "valor_investido": 10**15}],
            ordem(1, "0.01"),
        )
        self.assertEqual(r["status"], "Aprovado")

    def test_muitos_ativos(self):
        carteira = [{"risco": 1.0, "valor_investido": 1.0}] * 100_000
        self.assertEqual(validar_suitability(PERFIL, carteira, ordem(1.0, 1.0))["status"], "Aprovado")


class TestFatores(unittest.TestCase):
    """O fator de rejeição é uma premissa: deve ser configurável e validado."""

    def test_fatores_personalizados(self):
        def run(risco):
            return validar_suitability(
                {"score_max_risco": 2.5},
                [{"risco": risco, "valor_investido": 100}],
                ordem(risco, 100),
                fator_rejeicao=1.2,
            )
        self.assertEqual(run(3.0)["status"], "Alerta")        # 3.0 = 2.5 x 1.2 (limite)
        self.assertEqual(run("3.0001")["status"], "Rejeitado")

    def test_fatores_invalidos(self):
        for kwargs in [
            {"fator_alerta": 0.9},                          # < 1
            {"fator_rejeicao": 1.05},                       # <= fator_alerta (1,1)
            {"fator_alerta": 1.2, "fator_rejeicao": 1.2},   # iguais
            {"fator_alerta": "abc"}, {"fator_rejeicao": float("nan")}, {"fator_alerta": True},
        ]:
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValidacaoEntradaError):
                    validar_suitability(PERFIL, CARTEIRA, ordem(1.0, 1000), **kwargs)
                r = validar_suitability_seguro(PERFIL, CARTEIRA, ordem(1.0, 1000), **kwargs)
                self.assertEqual(r["status"], "Erro")  # fail-closed


class TestEntradasInvalidas(unittest.TestCase):
    def assertInvalida(self, perfil=PERFIL, carteira=CARTEIRA, nova=ordem(1.0, 1000)):
        with self.assertRaises(ValidacaoEntradaError):
            validar_suitability(perfil, carteira, nova)
        r = validar_suitability_seguro(perfil, carteira, nova)  # fail-closed
        self.assertEqual(r["status"], "Erro")
        self.assertIsNone(r["risco_projetado"])

    def test_ordem_invalida(self):
        casos = [
            None, [], "texto", 5,
            {"ativo": "X", "risco": 1},                     # sem valor_ordem
            {"ativo": "X", "valor_ordem": 1000},            # sem risco
            ordem(1, 0), ordem(1, -5000), ordem(-1, 1000),
            ordem(1, None), ordem(None, 1000),
            ordem(1, True), ordem(False, 1000),
            ordem(1, "abc"), ordem(1, ""), ordem(1, [1]),
            ordem(1, float("nan")), ordem(1, float("inf")), ordem(float("-inf"), 1),
            ordem(1, 10**19),
        ]
        for nova in casos:
            with self.subTest(nova=nova):
                self.assertInvalida(nova=nova)

    def test_perfil_invalido(self):
        casos = [
            None, [], "x", {}, {"perfil": "Moderado"},
            {"score_max_risco": 0}, {"score_max_risco": -2.5},
            {"score_max_risco": None}, {"score_max_risco": "abc"},
            {"score_max_risco": float("nan")}, {"score_max_risco": True},
        ]
        for perfil in casos:
            with self.subTest(perfil=perfil):
                self.assertInvalida(perfil=perfil)

    def test_carteira_invalida(self):
        casos = [
            None, "abc", 123, {"risco": 1, "valor_investido": 1},
            [None], ["x"], [1],
            [{"risco": 1}], [{"valor_investido": 100}],
            [{"risco": -1, "valor_investido": 100}],
            [{"risco": 1, "valor_investido": -100}],
            [{"risco": "a", "valor_investido": 100}],
            [{"risco": float("nan"), "valor_investido": 100}],
        ]
        for carteira in casos:
            with self.subTest(carteira=carteira):
                self.assertInvalida(carteira=carteira)

    def test_erro_inesperado_nao_aprova(self):
        class Quebrado(dict):
            def __getitem__(self, k):
                raise RuntimeError("boom")
        r = validar_suitability_seguro(Quebrado(score_max_risco=2.5), CARTEIRA, ordem(1, 1))
        self.assertEqual(r["status"], "Erro")

    def test_entradas_nao_sao_modificadas(self):
        p, c, o = copy.deepcopy(PERFIL), copy.deepcopy(CARTEIRA), ordem(4.5, 30000)
        p0, c0, o0 = copy.deepcopy(p), copy.deepcopy(c), copy.deepcopy(o)
        validar_suitability(p, c, o)
        self.assertEqual((p, c, o), (p0, c0, o0))

    def test_aceita_tupla_e_gerador_como_carteira(self):
        self.assertEqual(validar_suitability(PERFIL, tuple(CARTEIRA), ordem(1.5, 20000))["status"], "Aprovado")
        self.assertEqual(validar_suitability(PERFIL, (a for a in CARTEIRA), ordem(1.5, 20000))["status"], "Aprovado")


class TestRobustezAleatoria(unittest.TestCase):
    """Fuzz: nunca pode haver exceção fora do contrato, nem Aprovado indevido."""

    def test_fuzz(self):
        rnd = random.Random(42)
        lixo = [None, "", "abc", True, [], {}, float("nan"), float("inf"), -1, 0, 10**30, 1.5, "2.5", Decimal("1")]

        def valor():
            return rnd.choice(lixo) if rnd.random() < 0.3 else round(rnd.uniform(0, 6), 3)

        for _ in range(5000):
            perfil = {"score_max_risco": valor()}
            carteira = [{"risco": valor(), "valor_investido": valor() if rnd.random() < .3 else rnd.uniform(0, 1e6)}
                        for _ in range(rnd.randint(0, 4))]
            nova = ordem(valor(), valor() if rnd.random() < .3 else rnd.uniform(0, 1e6))
            r = validar_suitability_seguro(perfil, carteira, nova)
            self.assertIn(r["status"], {"Aprovado", "Alerta", "Rejeitado", "Erro"})
            if r["status"] != "Erro":
                self.assertTrue(math.isfinite(r["risco_projetado"]))
                self.assertGreaterEqual(r["risco_projetado"], 0)


if __name__ == "__main__":
    unittest.main()
