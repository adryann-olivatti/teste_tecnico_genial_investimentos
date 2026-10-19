# Case I — Relatório: Motor de Validação de Suitability (CVM 30)

## Premissas do motor

O risco projetado é comparado ao `score_max_risco` do cliente em três faixas:

| Risco projetado | Status |
|---|---|
| até `score × 1,1` | `Aprovado` |
| acima de `score × 1,1` e até `score × 1,3` | `Alerta` (desenquadramento leve, exige Termo de Ciência) |
| acima de `score × 1,3` | `Rejeitado` (desenquadramento severo) |

O fator **1,1** vem do enunciado (com score 2,5, o alerta dispara acima de 2,75). O enunciado não define o limite do desenquadramento severo, então **1,3 é uma premissa** (qualquer valor entre ~1,11 e 1,4 reproduz os exemplos de saída: 2,78 = Alerta e 3,5 = Rejeitado). Os dois fatores são parâmetros do motor.

## 1. Regulação vs. Negócio

**Situação:** o motor retorna `Alerta` e o cliente insiste em comprar. A CVM permite, mediante **Termo de Ciência**. O `Rejeitado` não tem essa saída: nenhum termo o libera.

### Implicações tecnológicas

| O que prever | Como |
|---|---|
| **Estado da ordem** | O `Alerta` não executa a ordem. Ela fica `AGUARDANDO_CIENCIA` e só segue após o aceite. Estados: `APROVADA`, `AGUARDANDO_CIENCIA`, `CIENCIA_ACEITA`, `EXECUTADA`, `REJEITADA`, `EXPIRADA`. |
| **Registro do Termo de Ciência** | Gravar no banco, ligado à ordem e ao cliente: quem aceitou (login e autenticação, ex.: MFA), data/hora (UTC), IP e dispositivo, versão e *hash* do texto exibido, e o perfil, o risco projetado e o limite mostrados ao cliente. |
| **Aceite explícito** | O cliente deve marcar ou assinar ativamente. Nunca uma opção pré-marcada. |
| **Log de auditoria** | Registrar toda validação (`Aprovado`, `Alerta` e `Rejeitado`): entradas, saída, versão do motor e das regras, data/hora e um `correlation_id`. Assim a decisão pode ser **reproduzida** numa auditoria. |
| **Regras configuráveis e versionadas** | Os fatores de alerta (1,1) e de rejeição (1,3, premissa) são parâmetros do motor. Em produção, devem vir de uma configuração versionada, não de constantes no código. Cada decisão registra qual versão da regra foi usada. |
| **Imutabilidade e guarda** | Termos e logs em armazenamento só de inclusão (sem editar ou apagar), com backup e prazo de guarda conforme a regulação (a confirmar com o Compliance). |
| **Revalidar na execução** | Preços e riscos mudam entre o alerta e a execução. O motor roda de novo na hora de executar. |
| **Validade do termo** | Curta, e válido só para aquela ordem e aquele valor. |
| **Transação segura** | Aceite e mudança de estado numa mesma transação, para evitar ordem duplicada ou executada sem termo. |
| **Segurança e LGPD** | Criptografia, acesso por perfil (só quem precisa) e o mínimo de dados pessoais nos logs. |

### Implicações de Compliance

- **Prova:** o termo e o log comprovam à CVM e à auditoria que o cliente foi informado do risco e decidiu por conta própria.
- **Ordens por assessor:** o assessor não aceita o termo pelo cliente sem prova de autorização. O canal usado (telefone, chat, app) deve ficar registrado.
- **Recorrência:** cliente que aceita termos com frequência, ou assessor com muitos alertas, gera relatório ao Compliance. Pode indicar perfil desatualizado.
- **Indicadores:** número de alertas, aceites e rejeições por período, disponível para fiscalização e auditoria interna.

---

## 2. Desenquadramento Passivo

**Ideia central:** o mesmo motor serve para monitorar a carteira **sem nova ordem**. `calcular_risco_carteira(carteira)` (sem `nova_ordem`) já retorna o risco atual, comparado ao `score_max_risco` com as mesmas faixas (enquadrado até `score × 1,1`, desenquadramento leve até `score × 1,3` e severo acima disso).

### Como funcionaria

1. **Gatilhos:**
   - Rotina diária após o fechamento do mercado, recalculando todas as carteiras.
   - Recálculo por evento, quando o preço ou o score de risco de um ativo muda de forma relevante. Só as carteiras com esse ativo são recalculadas.
2. **Processamento:** uma fila divide as carteiras entre vários processadores. A função não guarda estado, então escala facilmente. Reprocessar não duplica notificações (idempotência).
3. **Estado e histórico:** guardar o último status de cada cliente (`Enquadrado`, `Desenquadrado leve`, `Desenquadrado severo`) e **notificar só quando o status muda**. Uma pequena margem perto do limite evita alertas que ficam liga e desliga.
4. **Consequências:** enquanto desenquadrado, novas compras que aumentem o risco são bloqueadas ou exigem Termo de Ciência. O reenquadramento (vender, rebalancear ou atualizar o perfil) fica registrado com prazo e responsável.
5. **Auditoria:** registrar a detecção, a notificação enviada e a resposta do cliente, como no item 1.

### Canais de comunicação

| Situação | Canal principal | Complementar | Por quê |
|---|---|---|---|
| Desenquadramento leve | **App** (notificação *push*) | **E-mail** | O app é imediato e leva o cliente direto à tela para agir. O e-mail fica como registro formal. |
| Desenquadramento severo | **Assessor** (contato ativo) | App + e-mail | Risco alto exige explicação e orientação personalizada. Contato humano tem mais chance de gerar ação. |
| Sem resposta em X dias | **Assessor** ou central (escalonamento) | — | Evita alerta ignorado e comprova que a Genial agiu com diligência. |

**Conteúdo da mensagem:** risco atual, limite do perfil e as opções (reenquadrar, atualizar o perfil ou manter com ciência), sem pressionar a venda.

**Medir a eficácia:** taxa de leitura e tempo até o reenquadramento, para ajustar canais e prazos.
