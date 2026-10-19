# Painel Imobiliário Brasil

Consolida, em um único painel estático, dados públicos de inteligência de mercado do setor
imobiliário brasileiro: crédito, funding, lançamentos/vendas/estoque, preços, custos e macro.

## Como usar

```bash
pip install -r requirements.txt
python -m painel.collect          # baixa todas as fontes para data/series/*.csv (+ data/catalog.csv)
python -m painel.build            # gera dashboard/index.html
```

Abra `dashboard/index.html` no navegador — não precisa de servidor. Para atualizar só uma fonte:
`python -m painel.collect secovi abecip`. `--no-refresh` reaproveita os arquivos baixados em `data/raw/`.

## Fontes e coletores

| Coletor | Fonte | O que traz | Acesso |
|---|---|---|---|
| `bcb_olinda` | BCB — Informações do Mercado Imobiliário | Crédito contratado, taxa, LTV, indexador, carteira, inadimplência (PF/PJ × fonte × UF); funding (SBPE, LCI, CRI, LIG); perfil dos imóveis financiados; IVG-R | API OData, ano a ano |
| `bcb_sgs` | BCB — SGS | Selic, IPCA, INCC-DI, IGP-M, TR, poupança, desemprego, IBC-Br | API JSON |
| `sidra` | IBGE — SIDRA | SINAPI (custo m² por UF), PIB da construção e total | API JSON |
| `abecip` | ABECIP | Unidades e R$ financiados com SBPE (construção × aquisição); IGMI-R (preço de transação, Brasil + 10 capitais) | XLSX (link raspado da página) |
| `cbic` | CBIC/CII + Brain | Indicadores Imobiliários Nacionais: lançamentos, vendas e oferta final por região, trimestral, ~220 cidades | PDF público das coletivas (tabelas por região) |
| `abrainc` | Abrainc-Fipe | Lançamentos, vendas, entregas, distratos, oferta, VGV por segmento (MCMV × MAP) | XLSX série histórica (link raspado) |
| `secovi` | Secovi-SP — PMI | Lançamentos, vendas, oferta, VSO, VGV/VGL/VGO — cidade de São Paulo | PDF mensal (quadro-resumo da pág. 4) |

Preços usam só índices de **transação** (IGMI-R, IVG-R/MVG-R). O coletor `fipezap.py` (preço de oferta em
anúncios) continua no pacote, mas fora do painel por decisão de confiabilidade.

Detalhes do levantamento de fontes e das decisões em [mapa-de-dados.md](mapa-de-dados.md).

## Estrutura

```
painel/
  collectors/      um módulo por fonte; cada um devolve a tabela longa padrão
  store.py         esquema longo (source, series_id, name, block, region, unit, freq, date, value) e catálogo
  http.py          GET com cache em data/raw e User-Agent de navegador
  collect.py       orquestra os coletores
  build.py         seleciona as séries do painel e injeta o JSON em template.html
  template.html    o painel (HTML + SVG puro, sem dependências externas; tema claro/escuro)
data/
  raw/             downloads brutos (cache)
  series/          <fonte>.csv + <fonte>.meta.json
  catalog.csv      catálogo de todas as séries coletadas
dashboard/index.html
```

## Site com atualização diária (GitHub Pages)

O workflow em `.github/workflows/update.yml` roda todo dia às 06:00 (Brasília), coleta todas as fontes,
gera o painel e publica em GitHub Pages. Se uma fonte falhar, o painel mantém o último dado bom dela
(os CSVs ficam em cache entre execuções). Para ativar num repositório novo:

1. Crie o repositório no GitHub e envie este código (`git push`).
2. Em **Settings → Pages → Build and deployment → Source**, escolha **GitHub Actions**.
3. Em **Actions**, abra "Atualizar painel" e clique em **Run workflow** para a primeira publicação.

O site fica em `https://<usuário>.github.io/<repositório>/`. A maioria das fontes é mensal; a execução
diária só garante que cada divulgação apareça no dia seguinte.

## Próximos passos sugeridos

- Minha Casa Minha Vida em unidades (Ministério das Cidades) e orçamento FGTS.
- Funding de mercado atualizado (B3: estoque de LCI/LIG; ANBIMA: CRI) — as séries do BCB param em fev/2025.
- Pesquisas regionais de lançamentos/vendas (CBIC Hub de Dados — exige cadastro gratuito).
- Prévias operacionais das incorporadoras listadas (proxy antecedente trimestral).
- Agendar a coleta (Task Scheduler / cron) nos dias 5 e 20 de cada mês.
