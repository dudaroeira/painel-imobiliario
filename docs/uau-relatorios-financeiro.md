# UAU – Módulo Financeiro: mapa de relatórios e telas para o painel financeiro

Levantamento feito em 31/10/2026 no UAU 10.6.736 (base `C:\UAU`, empresa licenciada APEX Engenharia), navegando o módulo Financeiro pela tela.

## 1. Como os dados saem do UAU

Há dois tipos de fonte no módulo:

| Tipo | Onde fica | Saída | Serve para painel? |
|---|---|---|---|
| **Telas em grade** | menu Financeiro | botão **Imp. > Arquivo XLS** (tabela HTML com extensão .xls, cp1252) ou .txt | **Sim**: dado linha a linha, com todas as colunas, filtrável por várias empresas/obras/contas |
| **Relatórios impressos** | menu Relatórios > Gerais | PDF/impressora, 1 obra ou 1 conta por vez | Não como fonte; servem de referência de layout e de conferência |

Conclusão prática: o painel deve ser alimentado pelas **grades**, não pelos relatórios em PDF.

## 2. Telas em grade (fontes do painel)

| Tela (menu Financeiro) | O que entrega | Filtros | Uso no painel | Já extraído |
|---|---|---|---|---|
| **Contas a Pagar** | Parcelas em aberto: empresa, obra, fornecedor, doc. fiscal, emissão, vencimento, prorrogação, valor, categoria, status NF (81 colunas) | Obras (várias), período de vencimento | A pagar em aberto, vencidos, aging, por obra/fornecedor/categoria | Sim, 28/10 |
| **Contas Pagas** | Mesma estrutura, títulos baixados | Obras, período de pagamento | Desembolso realizado por mês, por obra e categoria; comparação com planejado | Não |
| **Conciliação Bancária > Resumo** | Por conta: saldo anterior, entradas, saídas, saldo atual | Várias contas, período | Posição de caixa por empresa/conta | Sim, 28/10 |
| **Conciliação Bancária > Extrato** | Lançamentos bancários: data, histórico, documento, tipo, valor | Várias contas, período | Movimento diário, entradas × saídas | Sim, 90 dias |
| **Conciliação Bancária > Saldos** | Saldo teórico diário por conta; cartões conciliado / não conciliado / real (1 conta por vez) | Várias contas, data | Histórico de saldo; pendências de conciliação | Sim (diário) |
| **Fluxo de caixa** (sintético/analítico) | Por conta: saldo conciliado inicial, lançamentos, saldo inicial fluxo, total despesa, total receita, saldo final; abas de detalhe (a pagar incorrido, compromissado, contratado, tributo, planejado, receitas a receber, a depositar...) | Várias contas, período, Configuração (marcar tipos de despesa/receita) | **Projeção de caixa** para 30/60/90 dias; saldo projetado por empresa | Não (testado 01/11 a 31/12/2026, funciona) |
| **Visualizador de Fluxo** | Visão gráfica/consolidada do fluxo | período | Conferência | Não verificado |
| **Análise de Resultado** | DRE gerencial por estrutura, intervalo (diário a anual), período de comparação, botão Exportar | Estrutura, obras, conta, gestão | DRE/resultado por obra | **Não há estrutura cadastrada**: precisa configurar em "Estrutura" antes de usar |
| **Caixa de Obra** | Caixa físico/pequenas despesas por obra | obra, período | Secundário | Não |
| **Gestão de Receita/Despesa** | Categorias e classificação | — | Tabela de categorias para o painel | Não |

## 3. Relatórios impressos (menu Relatórios > Gerais)

| Relatório | Filtros | Conteúdo | Relevância |
|---|---|---|---|
| **Fluxo de Caixa Geral** | Obras, período, banco/conta, saldo teórico/real, visão analítica/sintética; despesas (projetada, a pagar, pago, contr. financeiros, transferências) e receitas (projetada, a receber, a depositar, depósitos) | Fluxo projetado × realizado | Alta: é o relatório oficial de caixa; a grade "Fluxo de caixa" traz os mesmos dados exportáveis |
| **Balancete Financeiro** | Obras, período, analítico/sintético, saldo dos bancos, receitas por data de recebimento/depósito/compensação, despesas por pagamento/compensação | Receitas, despesas e saldo bancário por obra | Alta: resumo mensal por obra |
| **Desembolso por CAP** | Obra, CAP, índice, itens (a pagar, pago, controle financeiro), mês de planejamento | Planejado (PL) × a pagar × pago por centro de custo | Alta: orçado × realizado |
| **Contas a Pagar** | Obra, período de pagamento | Lista de títulos | Média (grade cobre) |
| **Contas Pagas** | Obra, período | Lista de pagos | Média (grade cobre) |
| **Posição de Bancos** / **Posição de Bancos Conciliados** | Banco, conta, período | Saldo e movimento de 1 conta | Baixa (grade Resumo cobre todas as contas) |
| **Extrato Bancário** / **Extrato Bancário Conciliado** | Banco, conta, período | Extrato de 1 conta | Baixa (grade Extrato cobre) |
| **Ficha Financeira do Fornecedor** | Fornecedor, período | Histórico por fornecedor | Média: detalhe sob demanda |
| **Itens Comprados** | Obra, período | Itens por processo | Baixa para financeiro; útil em Suprimentos |
| **Aplicações Financeiras** | Conta, período | Rendimento de aplicações | Baixa |
| **Controle de Cheques** | Período | Cheques emitidos | Baixa |

## 4. Proposta de painel financeiro

Páginas e fontes, em ordem de prioridade:

1. **Caixa hoje**: saldo por empresa e conta real (Conciliação > Resumo), entradas × saídas dos últimos 90 dias (Extrato), evolução do saldo (Saldos diário). Já alimentável com os arquivos de 28/10.
2. **Contas a pagar**: total em aberto, vencido, aging, a vencer 30/60/90, por empresa, obra, fornecedor e categoria (Contas a Pagar). Já alimentável.
3. **Projeção de caixa 30/60/90**: saldo inicial + receitas a receber − despesas a pagar/compromissadas, por empresa e conta (grade Fluxo de caixa, com todas as configurações marcadas). Próxima extração.
4. **Desembolso realizado**: pagos por mês, obra e categoria, comparado com o planejado (Contas Pagas + Desembolso por CAP). Próxima extração.
5. **Resultado por obra (DRE)**: depende de cadastrar uma estrutura em Análise de Resultado; até lá, derivar de Contas Pagas + receitas da grade Fluxo de caixa.

Rotina de atualização sugerida: exportar Contas a Pagar, Contas Pagas (mês corrente), Resumo e Extrato (mês corrente) e Fluxo de caixa (próximos 90 dias) uma vez por semana, para `dados/uau/` com nome datado; o script de conversão já trata o formato HTML do UAU.

## 5. Alertas encontrados

- A conta "Banco 0" da APEX aparece no Fluxo de caixa com lançamentos na casa de centenas de bilhões: é lixo de cadastro e deve ser excluída de qualquer soma.
- As contas de tipo "Controle" e do banco 999 "BANCO CONTROLE" não são caixa; filtrar.
- JR6 (empresa 52) tem só saídas lançadas na conciliação nos últimos 90 dias: faltam créditos do extrato.
- A base confiável começa em 01/01/2018; o anterior é legado.

## 6. Critérios oficiais para gerar relatórios (passados pelo usuário em 31/10/2026)

1. **Empresas**: de 1 a 45, exceto as pessoas físicas 4, 34, 35, 36, 37 e 38.
2. **Data de corte**: as conciliações começam em 01/07/2017 (implantação do UAU).
3. **Tipo de movimento**: só "Processos de pagamento"; "Transações financeiras" são transferências de estoque e ficam fora (na grade Contas a Pagar, usar o rádio "Processos").
4. **Bancos**: desconsiderar -1 (Banco interno) e 999 (Banco controle).
5. **Fornecedor**: desconsiderar COMPANHIA IMOBILIARIA DE BRASILIA TERRACAP, código 2813.

Relatórios padrão:
- **Curva ABC** (contas a pagar acumulado por fornecedor): Utilitários > Visualizador de resultados > Relatórios > Financeiro > nº 296; data inicial/final, empresas da regra 1, status do processo 0,1.
- **Contas a Pagar** (impresso): Relatórios > Gerais > Contas a pagar; empresas da regra 1 com todas as obras; período; Imprimir.

## 7. Visualizador de resultados (Utilitários) – catálogo de consultas prontas

A pasta Relatórios > UAU! > Financeiro tem **117 estruturas** (consultas SQL prontas que abrem em grade exportável). Catálogo completo em `dados/uau/visualizador_estruturas_financeiro_2026-10-31.csv`.

**Bloqueio atual:** o usuário EDUARDO só tem permissão na estrutura 695 (Administração de Obra). As demais, inclusive a 296 (Curva ABC), retornam "Você não tem permissão para visualizar a estrutura". A liberação é feita no módulo Segurança pelo administrador do UAU.

Estruturas que vale liberar, por prioridade para o painel:

| Nº | Nome | Por quê |
|---|---|---|
| 296 | Curva ABC dos Fornecedores | Contas a pagar acumulado por fornecedor (relatório padrão da empresa) |
| 636 | Saldo atual das contas bancárias | Saldo de todas as contas numa consulta só |
| 969 | Posição Financeira | Saldo conciliado, aplicações, pagas, a pagar e a receber por empresa/banco/conta |
| 956 | Receitas e Despesas | Projetado, a receber, depositado, a pagar e pago por empresa e obra |
| 286 | Desembolso Mensal por Obra | Gasto a pagar e pago por mês e obra |
| 623 / 1117 | Fluxo de caixa mensal resumido / por empresa, banco e conta | Série mensal para gráficos |
| 488 / 970 | Fluxo de caixa resumido / Fluxo de Caixa | Saldo anterior, a pagar e a receber no dia |
| 149 / 784 / 947 | Contas a Pagar e Pagas (por obra / com CAP / por mês) | Base de desembolso realizado |
| 885 | Curva ABC dos Insumos | Gasto por empresa e insumo |
| 628 | Relatório de desempenho financeiro | Movimento por categoria com grupos configuráveis |
| 909 | Resumo financeiro | Saldo, cheques não compensados, emissão, a pagar |
| 364 / 423 | Resumo Financeiro das Obras / Gerencial de Obras | Projetado × a pagar × pago e receitas por obra |
| 1145-1148 | Movimentação Financeira Geral | A pagar/receber, pagos/recebidos, conciliados |
| 104 / 1178 | Ficha Financeira do Fornecedor | Detalhe por fornecedor, com contratos |

### 7.1 Onde liberar as estruturas (módulo Segurança)

- Abrir: no Financeiro, menu **Módulos > Segurança** (abre o processo `Security.exe`, login próprio).
- No Segurança, menu **Utilitários > Visualizador de Resultados** abre o mesmo catálogo; a pasta **Controle de permissão** (topo da árvore) lista todas as estruturas com a coluna Permissão.
- A concessão por usuário fica em **Segurança > Usuários** (botão Usuário): selecionar o login, aba **Permissões**, botão **Programas** da barra secundária. É lá que se marca o programa/estrutura para o usuário.
- Alternativa por grupo: **Segurança > Grupos de Usuários**, grupo 01 DIRETORIA (EDUARDO e FABRICIO), para liberar para toda a diretoria de uma vez.
- Claude não executa a concessão: alteração de permissão é feita pelo usuário com a senha master.

## 8. Teste das consultas do Visualizador como base única (01/11/2026)

| Consulta | Resultado do teste | Serve como fonte semanal? |
|---|---|---|
| **589 Movimentação Financeira Geral, modo 0** (a pagar + a receber, por data de vencimento) | 37 colunas, nível de item do processo (empresa, obra, item/CAP, fornecedor, CNPJ, NF, vencimento, banco/conta, produto). Período 2015–2035: 1.065 linhas a pagar (contém os 484 processos da grade + 76 extras, R$ 963 mil, a investigar) e **2.231 parcelas a receber, R$ 16,7 mi**, com cliente, produto e vencimento. Exige uma conta no parâmetro Banco/Conta, mas o filtro é ignorado neste modo. | **Sim**: substitui a grade Contas a Pagar e acrescenta contas a receber. |
| 589 modos 1 e 2 (pagos/recebidos) e **1148** | Trazem pagos só da conta escolhida; o seletor aceita **uma conta por vez** (79 contas reais). | Não para o histórico de pagos. |
| 969 Posição Financeira | Mesmo seletor de uma conta. | Não testada a fundo; o Resumo da Conciliação cobre em 1 minuto. |

Conjunto mínimo recomendado (3 extrações): **589 modo 0** (a pagar + a receber), **Contas Pagas** (CSV, histórico de pagos), **Conciliação > Resumo** (saldos). Fluxo de caixa e Extrato saem.

Como executar a 589: Utilitários > Visualizador de resultados > Relatórios > UAU! > Financeiro > Buscar > abrir 589 > Parâmetros: Banco/Conta = filtrar uma conta qualquer na lupa (ignorada no modo 0); datas 01/01/2015 a 31/12/2035 (a data final só aceita na segunda digitação); Empresas/Obras = Selecionar todas as obras; Relatório = 0 (o campo é numérico: 0, 1 ou 2; "%" é recusado); OK > aba Registros > clicar numa linha > Imp. > Arquivo XLS.

## 9. Relatórios do zero: Gerador de Relatórios e Consultas Gerais (01/11/2026)

O UAU permite criar consultas SQL próprias sobre o banco, sem acesso externo ao SQL Server:

- **Utilitários > Gerador de Relatórios**: editor de SQL livre com parâmetros (`<DataInicio>` etc.), campos de detalhe, agrupamentos e grade de registros; os relatórios ficam salvos (ex.: 1001 "Parcelas a receber", 1003 "Faturamento mensal", criados pela própria empresa em 2016) e podem receber permissão por usuário.
- **Geral > Consultas Gerais**: catálogo das consultas SQL que alimentam cada estrutura do Visualizador, com botão **Inserir**. A pasta UAU!/Financeiro tem 801 consultas; a cláusula SQL completa foi exportada para `dados/uau/arquivo/consultas_gerais_financeiro_2026-11-01.csv` e as da 589 (código 843) e 1148 (código 1622) para `sql_consulta_843.sql` e `sql_consulta_1622.sql`.

Achado decisivo: o SQL da 589/1148 trata o parâmetro de contas com `fn_SplitForTable(<BancoConta>, ',')`, ou seja, **aceita lista de contas** no formato `banco|conta,banco|conta`. Só a tela de parâmetros do Visualizador limita a uma conta. Uma cópia dessa consulta no Gerador de Relatórios, com a lista de contas fixa (ou sem esse filtro), devolve a pagar, a receber, pagos e recebidos de todas as contas numa execução só. As fontes são as views `VwDesembolsoAPagar` e `Parc_Proc`/`Dados_Proc` (a pagar) e equivalentes para receber e pagos.

Próximo passo possível: criar no Gerador um relatório "Base painel" a partir do SQL 843, com os critérios oficiais embutidos (empresas 1-45 sem PF, sem bancos -1/999, sem TERRACAP), que substituiria as três extrações por uma. Criar/salvar relatório é alteração de cadastro no ERP: fazer só com autorização do usuário.

### 9.1 Consulta "Base painel" gravada (01/11/2026)
Geral > Consultas Gerais > pasta **Personalizado**, **código 29**, descrição "Base painel financeiro - a pagar, a receber, pagos, recebidos (derivado da 843)". SQL em `financeiro/sql_base_painel.sql`. Parâmetros: DataInicio, DataTermino, Relatorio (0 a pagar+a receber por vencimento; 1 pagos+recebidos; 2 conciliados; 3 tudo). Teste em outubro/2026 com relatório 3 executou sem erro. Gravada pelo usuário (meu controle de tela não grava cadastros no ERP).

### 9.2 Limites encontrados (01/11/2026)
- **Gerador de Relatórios**: os campos Consulta SQL e descrição não aceitam digitação nem colagem, nem para o usuário EDUARDO. Provável falta de permissão de inclusão/alteração no programa "Gerador de Relatórios" (módulo Segurança > Permissões > Programas). Sem isso não se cria a estrutura que faz a consulta aparecer no Visualizador.
- **Consultas Gerais > Testar**: executa a consulta 29 (período 2017-2035, relatório 3 funcionou), mas a janela "Dados da consulta" não tem exportação; o botão Imp. age sobre a grade de cadastro, não sobre os dados.
- Enquanto a estrutura não existir, a rotina continua com 3 extrações (589 modo 0, Contas Pagas CSV, Conciliação Resumo).
- Verificado em 01/11/2026: EDUARDO tem nível 126 (máximo) no programa GERELATORIO (Gerador de Relatórios), GECONSGER (Consulta geral) e GEVISUALRESULT (Visualizador). Logo o bloqueio do editor do Gerador **não é permissão**. Duplo clique, F4 e colar não abrem edição; o campo parece ser preenchido por outro mecanismo (provável: estrutura criada a partir de consulta geral por tela que não localizei). Pendência para o suporte Globaltec: "como criar uma estrutura no Visualizador de resultados a partir da consulta geral personalizada 29".
- Lista de programas liberados ao usuário: `dados/uau/arquivo/permissoes_eduardo_programas_2026-11-01.xls`.

### 9.3 Estrutura 13 "Base painel financeiro" criada (01/11/2026)
Caminho que funcionou (confirmado na Central de Ajuda da Globaltec): Geral > Consultas Gerais lado a lado com Utilitários > Gerador de Relatórios > arrastar a consulta 29 para a caixa "Consulta SQL" (o arraste só funciona com o mouse real; por controle remoto não dispara) > preencher parâmetros > Executar > Salvar estrutura na pasta raiz **Relatórios** (as pastas UAU! são reservadas) > **Criação do lay-out** > arrastar um campo para Detail > Salvar lay-out. Depois: Visualizador > Vínculos > Permissão de Usuário > incluir EDUARDO > Gravar. Parâmetros padrão salvos: 01/07/2017 a 31/12/2035, relatório 3.
Resultado: a aba Registros carrega o período inteiro (demora ~5 min, UAU fica "não respondendo"), mas o relatório impresso dá "ActiveReports Error 5000" e o Imp. > Arquivo XLS falha com "insufficient memory" (erro 32765 cmdOpt_Click). Solução: extrair por períodos menores (por ano ou por modo 0/1).
