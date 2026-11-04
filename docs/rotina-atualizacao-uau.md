# Rotina semanal de atualização da base financeira (UAU)

Frequência: uma vez por semana. Tempo estimado: 5 minutos no UAU (a maior parte esperando) e menos de 1 minuto de processamento.

Fonte principal: a estrutura **13 "Base painel financeiro"** do Visualizador de resultados, criada em 01/11/2026 sobre a consulta geral personalizada 29. O SQL da consulta fica em `financeiro/sql_base_painel.sql` como modelo, sem a lista de contas bancárias (o repositório é público); a lista está em `dados/uau/contas_consulta29.txt` e `python -m financeiro.montar_sql` gera `dados/uau/sql_base_painel_completo.sql`, que é o texto a colar no UAU. Ela traz, com os critérios oficiais já embutidos, contas a pagar, a receber, pagas, recebidas, transferências e controles financeiros, por empresa, obra, item e fornecedor.

## 1. Criar a pasta da semana

Crie `dados/uau/brutos/AAAA-MM-DD/` com a data do dia. Todos os arquivos abaixo vão para ela, **com estes nomes exatos**.

## 2. Exportar do UAU (módulo Financeiro)

Abra **Utilitários > Visualizador de resultados**, pasta **Relatórios** (a raiz, não UAU!), **Buscar**, duplo clique na estrutura **13**. Depois **Parâmetros**:

| Arquivo | Parâmetros da estrutura 13 | Como exportar |
|---|---|---|
| `base13_modo0_apagar_areceber.xls` | Data inicial `01/07/2017`, data final `31/12/2035`, Relatório `0` · OK | Aba **Registros** · clicar numa linha · **Imp.** > **Arquivo XLS** |
| `base13_modo1_semana.xls` | Data inicial = **hoje menos 15 dias**, data final = **hoje**, Relatório `1` · OK | Idem |
| `fechamentos_caixa.xls` | Tela **Financeiro > Fechamento de Caixa/Conta** · Empresa "Vários" (todas) · período pelo **calendário** ao lado (os campos não aceitam digitação): 01/01 do ano anterior até hoje · Fiscal, Banco/Conta e Diário (Caixa) marcados · Buscar | Clicar numa linha · **Imp.** > **Arquivo XLS**. Só consulta: **não** clicar em "Fechamento" na barra |
| `bancos_saldos.xls` | Tela **Concil.** > aba **Resumo** · Banco "Vários", Conta "Várias" (lupa > marcar todas) · mês corrente (dia 1 até hoje) · Buscar | Clicar numa linha · **Imp.** > **Arquivo XLS** |

Dicas:
- O campo de data final costuma recusar a primeira digitação ("não é uma data válida"); confirme o aviso e digite de novo.
- Ao clicar OK, o UAU mostra o relatório impresso; com muitos registros aparece "ActiveReports Error 5000". Ignore: os dados estão na aba **Registros**.
- Enquanto monta a grade ou grava o arquivo, o UAU fica "não respondendo" por alguns minutos. Aguarde; não feche.
- **Não** execute o relatório 3 (tudo) para o período completo: a exportação estoura a memória do UAU.
- **Carga incremental.** O modo 1 (pagos, recebidos, transferências, controles) é acumulado em `dados/uau/historico/movimento_e13.pkl`. Cada arquivo exportado traz o período que cobre; ao incorporá-lo, o script apaga do histórico as linhas desse período e grava as novas. Por isso basta exportar os últimos 15 dias: a sobreposição corrige lançamentos atrasados sem duplicar nada. O nome do arquivo pode ser qualquer `base13_modo1_*.xls`.
- **Carga inicial do histórico**: feita em 01/11/2026, modo 1 ano a ano de 2017 a 2025 (`dados/uau/historico/base13_modo1_<ano>.xls`). Em 02/11/2026 a consulta 29 ganhou três contas Caixa encerradas (lista em `dados/uau/contas_consulta29.txt`) e 2017 a 2020 foram reexportados. Não precisa repetir. O diálogo "Salvar como" do UAU não aceita caminho completo digitado: salve na pasta da semana e mova o arquivo depois.
- Com o histórico completo, o processamento leva cerca de 1,5 minuto.
- Para corrigir um ano inteiro depois, basta exportar o ano de novo com o mesmo nome e rodar o script: as linhas do período são substituídas. As cargas feitas ficam listadas em `dados/uau/historico/movimento_e13_cargas.json`.

## 3. Montar a base e o painel

```bash
python -m financeiro.atualizar
```

Gera `dados/uau/base/base_financeira_AAAA-MM-DD.xlsx`, a cópia `base_financeira_atual.xlsx` e o painel `dados/uau/painel/painel_financeiro.html`. Dependências (uma vez): `pip install pandas openpyxl lxml xlsxwriter`.

Para ver o painel, dê dois cliques no arquivo HTML: abre no navegador, sem servidor e sem internet.

### Data de conciliação no painel

O caixa é fechado no UAU cerca de 15 dias depois do fim de cada mês, quando as contas já estão conciliadas. O painel mostra, no topo, até que data os valores são definitivos ("Caixa fechado e contas conciliadas até ..."), lida do `fechamentos_caixa.xls` mais recente (`financeiro/conciliacao.py`). Com todas as empresas selecionadas vale a data mais antiga entre elas; ao filtrar uma empresa, vale a dela. A empresa 31 (empresa de teste) fica fora do cálculo. Em 04/11/2026 todas as empresas do escopo estavam fechadas até 30/09/2026.

### Versão no site, com senha

O painel vai para o site público (GitHub Pages) **cifrado**: `python -m financeiro.publicar` lê o HTML do painel, cifra tudo com AES-256-GCM (chave derivada da senha) e grava `dashboard/financeiro.html`, uma página que pede a senha e decifra o painel no navegador. O repositório e o site só recebem o texto cifrado. A senha fica em `dados/uau/painel/senha_site.txt` (fora do git); para trocá-la, apague o arquivo, rode o `publicar` de novo e avise quem usa.

O site mostra só o histórico a partir de **01/01/2025** (`DESDE` em `financeiro/publicar.py`); contas a pagar, a receber e saldos atuais aparecem inteiros. O painel local continua com todo o histórico desde 07/2017.

Toda semana, depois do `atualizar`:

```bash
python -m financeiro.publicar
```

Depois commite `dashboard/financeiro.html` e envie para `main`; o workflow do Pages publica em https://dudaroeira.github.io/painel-imobiliario/financeiro.html (link "Financeiro · acesso restrito" no menu do site). Atenção: a página cifrada é pública na internet; a proteção é só a senha, então ela precisa ser forte e não deve ser compartilhada por canais abertos.

Há também uma cópia privada no claude.ai (https://claude.ai/artifact/Fxf4xeGJniaD4xxEWKwEUD), que só abre para o dono e para quem ele compartilhar; peça ao Claude para republicá-la quando quiser.

## 4. Conferir

Abra a aba **Resumo** da base e a aba **Exclusoes**. Compare o total a pagar, o total a receber e o saldo bancário com a semana anterior. Variações grandes sem motivo indicam exportação incompleta.

## Abas da base

Resumo · A pagar · A receber · Pagas · Recebidas · Saldos · Movimento (todo o movimento bancário do modo 1) · Saldo projetado diario · Fluxo projetado (vazio se `fluxo_sintetico.xls` não for exportado) · Conferencia · Exclusoes · Criterios.

A aba **Conferencia** aplica as regras de consistência entre lançamentos (`financeiro/consistencia.py`, de 2018 em diante): toda transferência entre contas da mesma empresa precisa de entrada no mesmo dia e valor na mesma empresa (regra 1); todo aporte, mútuo ou repasse "X P/ Y" precisa de entrada no mesmo dia e valor em outra empresa (regra 2). A aba lista os lançamentos sem par; o Resumo traz o percentual fechado de cada regra. Saídas de transferência entre contas que só encontram par em outra empresa (histórico genérico) contam como fechadas e aparecem na aba com a marca "Fechada via outra empresa". Referência em 02/11/2026: regra 1 fecha 93% e regra 2 fecha 85% das saídas desde 2018; o que sobra concentra-se em 2018 a 2021. Para a regra 2 funcionar, a consulta 29 precisa estar na versão 3 (02/11/2026), que monta o lado crédito das transferências com a empresa de destino (EmpresaCred_Tb); antes disso o recebimento entre empresas não aparecia na base.

A aba Movimento traz a coluna **Tipo de movimento**, deduzida do histórico do lançamento (campo HistLanc do UAU) para transferências e controles financeiros: aporte de capital, mútuo entre empresas, distribuição de lucros, aplicação financeira, rendimento, empréstimo bancário, tarifa bancária, taxa de administração, caução, estorno e devolução, impostos, juros, receitas diversas, transferência entre empresas ("X P/ Y") e transferência entre contas. Pagamentos e recebimentos recebem o tipo pela origem. As regras estão em `financeiro/estrutura13.py` (`_REGRAS_TIPO`); o que não casa fica como "Outros controles". O painel mostra o resumo por tipo na aba Caixa.

## Critérios aplicados

1. Empresas 1 a 45, exceto pessoas físicas 4, 34, 35, 36, 37 e 38 (já no SQL da consulta 29).
2. Movimento a partir de 01/07/2017.
3. Só processos de pagamento.
4. Bancos -1 e 999 fora dos pagos e do movimento; nos saldos também o banco 0 e contas do tipo Controle.
5. Fornecedor TERRACAP (2813) fora.

## Como o saldo projetado é calculado

Saldo real de hoje (Resumo da Conciliação) menos as contas a pagar acumuladas por vencimento, com as vencidas no primeiro dia. A segunda série soma as contas a receber **ainda a vencer**; as vencidas são inadimplência e ficam fora.

## Se a estrutura 13 não estiver disponível

O script aceita a rotina antiga (contas_a_pagar.xls, contas_pagas.csv, bancos_extrato.xls, fluxo_sintetico.xls) se o arquivo do modo 0 não existir na pasta. Os caminhos dessas telas estão em `docs/uau-relatorios-financeiro.md`.

## Segurança

`dados/` está no `.gitignore`: nada do ERP vai para o GitHub nem para o painel público do repositório.
