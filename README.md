# Teste Técnico — Genial Investimentos

Resolução do case técnico do Programa de Estágio de Férias (Tecnologia, Jan/2027).

- **Case I:** Motor de Validação de Suitability de Carteira (CVM 30), com código, testes e o relatório em [`case-report.md`](case-report.md).
- **Case II:** respostas sobre infraestrutura, monitoramento, disponibilidade e governança de TI, em [`case-ii-respostas.md`](case-ii-respostas.md).

## Estrutura do projeto

```
.
├── suitability.py          # motor de validação (lógica principal)
├── main.py                 # exemplo de execução com 3 cenários
├── test_suitability.py     # testes automatizados
├── case-report.md          # relatório do Case I
├── case-ii-respostas.md    # respostas do Case II
└── README.md
```

## Requisitos

- **Python 3.8 ou superior** (testado com 3.12).
- Nenhuma biblioteca externa. Só é usada a biblioteca padrão do Python, então não há nada para instalar.

Para conferir a versão:

```bash
python --version
```

> Em alguns sistemas (Linux e macOS) o comando é `python3` em vez de `python`. Em todos os comandos deste README, pode trocar `python` por `python3`. Exemplo: `python3 main.py` e `python3 -m unittest -v`.

## Como rodar

Abra o terminal na pasta do projeto e execute:

```bash
python main.py
```

ou, dependendo do seu sistema:

```bash
python3 main.py
```

Esse comando executa **só o teste do `main.py`**: três ordens de exemplo (Aprovado, Alerta e Rejeitado) com a carteira do enunciado, com o resultado impresso em JSON. **Ele não executa os 25 testes automatizados.** Para esses, veja a seção "Como rodar os testes".

A saída esperada é:

```json
{
  "status": "Aprovado",
  "risco_projetado": 1.63,
  "mensagem": "Ordem executada. Carteira em conformidade."
}
```

```json
{
  "status": "Alerta",
  "risco_projetado": 2.61,
  "mensagem": "Atenção: O risco da carteira ultrapassará o limite de 2.75. É necessário termo de ciência."
}
```

```json
{
  "status": "Rejeitado",
  "risco_projetado": 3.57,
  "mensagem": "Risco excessivo. A operação viola a política de Suitability."
}
```

## Como usar o motor no seu código

```python
from suitability import validar_suitability

perfil = {"perfil": "Moderado", "score_max_risco": 2.5}

carteira = [
    {"ativo": "CDB XPTO", "risco": 1.2, "valor_investido": 50000},
    {"ativo": "Ação ABC", "risco": 4.0, "valor_investido": 10000},
]

ordem = {"ativo": "FII YYY", "risco": 3.5, "valor_ordem": 5000}

print(validar_suitability(perfil, carteira, ordem))
```

### Como o resultado é decidido

O risco da carteira é uma **média ponderada** pelo valor investido. O risco projetado inclui a nova ordem.

| Risco projetado | Status |
|---|---|
| até o `score_max_risco` | `Aprovado` |
| acima do `score_max_risco` e até `score_max_risco × 1,1` | `Alerta` |
| acima de `score_max_risco × 1,1` | `Rejeitado` |

A decisão usa o valor exato. O `risco_projetado` mostrado na saída é arredondado para 2 casas.

### Funções disponíveis

| Função | O que faz |
|---|---|
| `validar_suitability(perfil, carteira, ordem)` | Retorna o JSON com a decisão. Se a entrada for inválida, levanta `ValidacaoEntradaError`. |
| `validar_suitability_seguro(perfil, carteira, ordem)` | Igual à anterior, mas nunca levanta erro. Se algo der errado, retorna `status: "Erro"` e a ordem **não é aprovada**. |
| `calcular_risco_carteira(carteira, nova_ordem=None)` | Retorna o risco ponderado e o valor total. Sem `nova_ordem`, é o risco atual. |

## Como rodar os testes

Há duas formas de testar o projeto:

| O que você quer | Comando | O que executa |
|---|---|---|
| Ver só o teste do `main.py` (rápido) | `python3 main.py` | Apenas os 3 cenários de exemplo |
| Rodar os testes automatizados | `python3 -m unittest -v` | Os 25 testes do `test_suitability.py` |

Para rodar os 25 testes, na pasta do projeto:

```bash
python -m unittest -v
```

ou:

```bash
python3 -m unittest -v
```

O `-v` mostra cada teste e se passou. O resultado esperado termina com:

```
Ran 25 tests in 0.3s

OK
```

### Outras formas de rodar

Só um grupo de testes:

```bash
python -m unittest test_suitability.TestDecisao -v
```

Só um teste:

```bash
python -m unittest test_suitability.TestDecisao.test_alerta -v
```

Com `pytest` (opcional, precisa instalar com `pip install pytest`):

```bash
pytest -v
```

### O que os testes cobrem

- **Cálculo:** risco atual, risco projetado e carteira vazia.
- **Decisão:** os três status, o exemplo do enunciado e os limites exatos (2,5 e 2,75).
- **Entradas inválidas:** campos ausentes, valores negativos ou zero, `NaN`, texto no lugar de número e tipos errados.
- **Robustez:** as entradas não são alteradas, e um teste com 5.000 entradas aleatórias confirma que o motor nunca quebra fora do esperado.

## Problemas comuns

| Erro | Causa e solução |
|---|---|
| `python: command not found` | Use `python3`, ou instale o Python em [python.org](https://www.python.org/downloads/). |
| `ModuleNotFoundError: No module named 'suitability'` | Você não está na pasta do projeto. Use `cd` para entrar nela antes de rodar. |
| `No module named pytest` | O `pytest` é opcional. Use `python -m unittest -v`. |
