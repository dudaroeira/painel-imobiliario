# Looker Studio (gratuito) sobre os dados do painel

A cadeia é toda automática e sem custo:

1. **Site** (GitHub Actions, todo dia às 06h de Brasília) coleta as fontes e publica CSVs enxutos em
   `https://dudaroeira.github.io/painel-imobiliario/data/sheets/` (`series_id, region, date_key, value`)
   mais o dicionário `series.csv` (nome, bloco, unidade e frequência de cada série).
2. **Planilha-ponte** no Google Drive: cada aba tem só a fórmula
   `=IMPORTDATA("…/data/sheets/<aba>.csv"; ","; "en_US")` na célula A1. O Google Sheets reexecuta a
   importação sozinho (cerca de uma vez por hora), sem script nem gatilho.
3. **Looker Studio** lê as abas da planilha; o cache dele renova a cada 12 horas (ajustável em
   *Recurso → Gerenciar fontes de dados → Atualização dos dados*).

Planilha atual: [Painel Imobiliário — dados (Looker)](https://docs.google.com/spreadsheets/d/1P6lHKtxmYiZdbf2EelqBSYiFiytCzgs4-iScZYJHNu0/edit)
(pasta *Painel Imobiliário — dados para Looker* no Drive).

## Recriar a planilha (se precisar)

```bash
python looker/make_sheet.py
```

Gera `looker/painel_sheets.xlsx`. Envie ao Google Drive, abra com o Google Planilhas e clique em
**Permitir acesso** no aviso da primeira aba (autoriza as URLs externas para todas as abas).

Por que o terceiro argumento `"en_US"`: os CSVs usam ponto decimal. Sem ele, uma planilha em pt-BR lê
`9.13` como data (9 de janeiro) e o valor vira um número de série como 46031.

## Conectar o Looker Studio

Link que cria um relatório já ligado à aba `credito_contratado` (clique em **Salvar e compartilhar**):

<https://datastudio.google.com/reporting/create?c.mode=edit&r.reportName=Painel%20Imobili%C3%A1rio%20%E2%80%94%20BI&ds.connector=googleSheets&ds.datasourceName=credito_contratado&ds.spreadsheetId=1P6lHKtxmYiZdbf2EelqBSYiFiytCzgs4-iScZYJHNu0&ds.worksheetId=590064066&ds.hasHeader=true&ds.refreshFields=true>

Para outras abas: no relatório, **Adicionar dados → Planilhas Google →** a planilha **→** a aba.

Na fonte de dados, ajuste os tipos:

| Campo | Tipo |
|---|---|
| `date_key` | Data e hora → *Data (AAAAMMDD)* |
| `value` | Número (agregação SUM para fluxos em R$; AVG para taxas, LTV, índices e saldos) |
| `region` | Texto; para mapa use *Geo → Subdivisão do país (1º nível)* nas abas com UF |
| `series_id` | Texto |

Para ver nomes legíveis, faça uma **mesclagem** (Recurso → Gerenciar mesclagens) entre a aba de dados e a
aba `series`, chave `series_id`, trazendo `name` e `unit`.

## Visões sugeridas

| Visão | Aba | Como montar |
|---|---|---|
| Crédito por UF | `credito_contratado` | Mapa geográfico (`region`), filtro `series_id = credito_contratacao_contratado_pf_sfh`, SUM de `value`, últimos 12 meses |
| Comparação de UFs no tempo | `credito_contratado` | Série temporal por `date_key`, quebra por `region`, controles de lista para `region` e `series_id` |
| Taxa e LTV por UF | `credito_taxa_ltv` | Tabela dinâmica: `region` nas linhas, `series_id` nas colunas, AVG de `value`, último mês |
| Inadimplência | `credito_inadimplencia` | Série temporal, AVG, filtro de `region` |
| Oferta por região e segmento | `oferta_cbic` | Colunas empilhadas: `date_key`, quebra `region`, filtro `series_id` (`lancamentos`, `vendas`, `oferta`, `*_mcmv`, `*_map`) |
| Preços por capital | `precos` | Série temporal, filtro `series_id = igmi_r`, quebra `region` |

## Limites

- IMPORTDATA recusa arquivos grandes; por isso os CSVs de crédito são divididos por família e ficam até ~1,5 MB.
- O Google Sheets aceita 10 milhões de células; a planilha usa ~0,6 milhão.
- Se um dia ficar lento, os CSVs completos (`/data/*.csv`) podem ir para o BigQuery (nível gratuito).
