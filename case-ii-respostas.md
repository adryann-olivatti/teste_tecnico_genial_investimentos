# Case II — Infraestrutura, Monitoramento, Disponibilidade e Governança de TI

## Cenário 1: Crescimento de demanda (10 mil → 100 mil carteiras por dia)

**Ideia principal:** antes de comprar ou mudar qualquer coisa, eu descobriria qual parte do sistema vai ficar "apertada" primeiro. Para isso, olharia estes pontos:

- **Servidores da aplicação (CPU e memória):** o cálculo do motor é simples, mas é preciso medir quanto cada servidor aguenta. Como o motor não guarda informação entre uma validação e outra, é fácil colocar mais servidores trabalhando juntos quando o volume crescer.
- **Banco de dados:** é onde o motor lê as carteiras e grava os registros de cada decisão. Com 10 vezes mais carteiras, ele passa a ter 10 vezes mais leituras e gravações. Eu conferiria se as consultas são rápidas (índices), se o número de conexões simultâneas é suficiente e se o banco aguenta o ritmo de gravação.
- **Fila de processamento:** em vez de processar tudo de uma vez, os pedidos entram numa fila e os servidores vão pegando um a um. Isso evita que um pico derrube o sistema.
- **Serviços externos:** se o motor consulta preços ou riscos dos ativos em outro sistema, ele pode ter limite de consultas por minuto.
- **Armazenamento:** os registros de auditoria (que precisam ser guardados por lei) também vão crescer 10 vezes, então é preciso ter espaço e orçamento para isso.
- **Teste de carga:** simular as 100 mil carteiras antes de elas chegarem, para ver onde o sistema falha primeiro.

**Justificativa:** 100 mil carteiras por dia dá pouco mais de 1 por segundo na média, o que parece fácil. O problema são os picos: se a maior parte chegar na mesma hora (por exemplo, depois do fechamento do mercado), o volume por segundo é muito maior. Por isso o sistema deve ser preparado para o pior horário, e não para a média do dia.

---

## Cenário 2: Servidor indisponível

**Como preparar o sistema para continuar funcionando:**

- **Mais de um servidor:** em vez de um único servidor, manter vários rodando ao mesmo tempo, de preferência em locais físicos diferentes. Se um cai (por exemplo, por falta de energia), os outros continuam atendendo.
- **Balanceador de carga:** ele distribui os pedidos entre os servidores e testa se cada um está saudável. Se um para de responder, o balanceador para de enviar pedidos para ele sozinho, sem ninguém precisar intervir.
- **Fila de pedidos:** se todos os servidores caírem, os pedidos ficam guardados na fila e são processados quando o serviço voltar. Assim nenhuma validação se perde.
- **Banco de dados com cópia (réplica) e backup:** se o banco principal falhar, a cópia assume. O backup protege contra perda de dados.
- **Plano de recuperação:** definir antes quanto tempo o sistema pode ficar fora do ar e quanto de dados se aceita perder, e deixar escrito o passo a passo para voltar ao normal.
- **Regra de segurança:** se não for possível validar uma ordem, ela **não é aprovada**. Ela fica pendente ou é recusada por enquanto.

**Justificativa:** o motor roda antes de toda compra, então se ele para, o cliente não consegue investir. Ter mais de um servidor mantém o serviço de pé. E não aprovar sem validar é importante porque aprovar uma ordem sem checar o perfil do cliente descumpriria a regra da CVM.

---

## Cenário 3: Lentidão (de 500 ms para 8 segundos)

**O que eu verificaria, nesta ordem:**

1. **O que mudou recentemente?** Uma atualização do sistema, uma configuração nova ou um aumento de pedidos. Se a lentidão começou logo depois de uma atualização, voltar para a versão anterior é a solução mais rápida.
2. **Painéis de monitoramento:** ver o tempo de resposta em cada etapa (aplicação, banco, serviços externos), para saber onde o tempo está sendo gasto.
3. **Banco de dados:** é uma das causas mais comuns. Procurar consultas lentas, pedidos travados esperando uns pelos outros, conexões esgotadas e tabelas de registros que cresceram demais.
4. **Servidor da aplicação:** ver se o uso de processador ou de memória está no limite.
5. **Serviços externos:** se o motor depende de outro sistema e ele está lento, o motor fica lento junto. Tentativas repetidas depois de uma falha podem piorar o problema.
6. **Rede:** atrasos na comunicação entre os componentes.
7. **Fila:** se há muitos pedidos acumulados esperando para serem processados.

**Enquanto investigo:** adicionar mais servidores, reiniciar o componente com problema ou voltar a versão anterior, para reduzir o impacto para o cliente.

**Justificativa:** uma lentidão tão grande quase sempre tem uma causa única. Começar pelo que mudou e medir cada etapa evita ficar tentando consertar tudo ao mesmo tempo.

---

## Cenário 4: Monitoramento (nenhuma carteira validada há 30 minutos)

**O problema:** o sistema responde, então um monitoramento simples ("o servidor está ligado?") diz que está tudo bem. Mas na prática ele não está fazendo o trabalho dele. Por isso é preciso monitorar o **resultado**, e não só se o sistema está no ar.

**Como detectar:**

- **Contar as validações por minuto:** criar um alerta que dispara se esse número ficar em zero (ou muito baixo) por alguns minutos. É preciso considerar o horário normal de uso, para não alertar de madrugada à toa.
- **Comparar o que entra com o que sai:** se chegam pedidos mas nenhum é concluído, algo está travado no meio do caminho.
- **Olhar a fila:** verificar se há pedidos parados há muito tempo sem serem processados.
- **Teste automático:** a cada poucos minutos, o próprio sistema envia uma carteira de teste e confere se a validação funciona do começo ao fim.
- **Verificação de saúde completa:** em vez de só responder "estou ligado", o sistema deve checar se consegue falar com o banco de dados e com os outros serviços de que precisa.
- **Alerta para a equipe:** o aviso deve chegar rápido a quem está de plantão (e-mail ou chat) e dizer o que está acontecendo e o que fazer.

**Justificativa:** um sistema pode estar "vivo" e mesmo assim não funcionar. Acompanhar se o trabalho está sendo concluído pega problemas silenciosos que um teste simples de "está ligado?" não pega.

---

## Cenário 5: Mudança em produção

**Como eu planejaria, em etapas:**

1. **Documentar a mudança:** escrever o que vai mudar, por que, quando, quem vai fazer e qual é o passo a passo. Assim, qualquer pessoa entende e pode revisar.
2. **Avaliar os riscos:** pensar no que pode dar errado, qual a chance disso acontecer e qual seria o impacto. Por exemplo: o motor parar de validar ordens, ou validar errado.
3. **Testar antes:** fazer a mudança primeiro em um ambiente de teste parecido com o real. Testar também como voltar atrás, para ter certeza de que o plano de volta funciona.
4. **Pedir aprovação:** a mudança precisa ser aprovada por quem responde por ela. Se mexer no motor de suitability, o Compliance também deve aprovar.
5. **Avisar os envolvidos:** comunicar antes (o que vai acontecer e quando), durante (como está indo) e depois (se deu certo). A mudança deve ser feita em horário de pouco uso, fora do horário de negociação do mercado.
6. **Plano de contingência:** antes de começar, fazer um backup. Definir com antecedência em que situação se volta atrás (por exemplo, se os erros passarem de certo nível), quem toma essa decisão e como fazer.
7. **Conferir depois:** verificar se tudo funciona, acompanhar o sistema de perto por um tempo, fechar o registro da mudança e anotar o que foi aprendido.

**Justificativa:** o motor protege a Genial perante a CVM, então uma mudança mal feita pode parar as validações ou gerar decisões erradas. Planejar, testar e ter um plano de volta reduz o risco e deixa tudo registrado, o que ajuda em uma eventual auditoria.
