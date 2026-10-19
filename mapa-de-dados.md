# Painel de Inteligência do Mercado Imobiliário Brasileiro — Mapa de Dados

*Versão 0.1 — 19/10/2026. Levantamento das fontes públicas disponíveis na internet, com foco em quais podem ser automatizadas.*

---

## 1. Blocos estratégicos do painel

| # | Bloco | Pergunta que responde | Indicadores-chave |
|---|-------|----------------------|-------------------|
| 1 | **Oferta primária** (incorporação) | Quanto está sendo lançado e vendido? Há excesso de estoque? | Lançamentos (unid. e VGV), vendas, VSO, oferta final/estoque, distratos, entregas, meses de estoque |
| 2 | **Crédito imobiliário** | Quanto crédito está fluindo, para quem e a que custo? | Contratações (R$ e unidades) por fonte (SBPE/SFH, FGTS, livre/SFI, home equity), taxa média, LTV, prazo, indexador (TR/IPCA/pré), inadimplência, saldo da carteira |
| 3 | **Funding** | De onde vem o dinheiro e ele está crescendo? | Saldo e captação líquida da poupança (SBPE), direcionamento obrigatório, estoque de LCI, LIG, CRI, FGTS (orçamento e arrecadação) |
| 4 | **Habitação social** | Qual o peso do programa público? | Minha Casa Minha Vida: contratações por faixa, UF, subsídios, orçamento FGTS/OGU |
| 5 | **Preços** | Imóveis estão subindo ou caindo, em termos reais? | FipeZap (oferta, venda e locação), IGMI-R (transação, base avaliações bancárias), IVG-R/MVG-R (BCB), rental yield, preço/renda |
| 6 | **Custos & atividade da construção** | O lado da produção está aquecido? Margens apertando? | INCC, SINAPI, CUB/m², PIB da construção, emprego formal (CAGED), sondagem/confiança (CNI/FGV), consumo de cimento |
| 7 | **Macro condicionantes** | O ambiente ajuda ou atrapalha? | Selic, IPCA, TR, renda/desemprego, confiança do consumidor, câmbio |
| 8 | **Mercado secundário / transações** | Quantas transações efetivas ocorrem? | Registros de imóveis (ONR), ITBI municipal, avaliações bancárias (nº de imóveis, tipo, área, dormitórios — BCB) |
| 9 | **Demanda estrutural** | Qual o tamanho da necessidade? | Déficit habitacional (FJP/CBIC), demografia (IBGE), formação de domicílios |

---

## 2. Fontes por bloco

Legenda de acesso: 🟢 API/JSON (automatizável direto) · 🟡 Excel/CSV com URL fixa (automatizável com parser) · 🟠 PDF/HTML (scraping ou coleta manual) · 🔴 restrito/pago.

### Bloco 2+3+5+8 — Banco Central: "Informações do Mercado Imobiliário" 🟢 ★ espinha dorsal do painel

- **Endpoint:** `https://olinda.bcb.gov.br/olinda/servico/MercadoImobiliario/versao/v1/odata/mercadoimobiliario` (OData, JSON/CSV, sem autenticação).
- **Estrutura:** um único recurso com colunas `Data`, `Info`, `Valor`. Testado em 19/10/2026: **1.948 séries mensais** no mês de jun/2026, dados desde 2014, último mês disponível jul/2026. Quase todas com recorte por **UF + Brasil** (sufixo `_br`, `_sp`, `_rj`...).
- **Famílias de séries (prefixo `Info`):**

| Família | O que mede | Dimensões |
|---------|-----------|-----------|
| `credito_contratacao_contratado_{pf,pj}_{sfh,fgts,livre,home_equity,comercial}` | **Valor contratado no mês** (R$) | PF/PJ × fonte × UF |
| `credito_contratacao_taxa_...` | Taxa média das novas contratações | idem |
| `credito_contratacao_ltv_...` | LTV médio das contratações | idem |
| `credito_contratacao_indexador_{pf,pj}_{tr,ipca,prefixado,cdi,outros}` | Contratações por indexador | → **forma de financiamento** |
| `credito_estoque_carteira_credito_...` | Saldo da carteira | PF/PJ × fonte × UF |
| `credito_estoque_inadimplencia_...` / `ativo_problematico_...` | Inadimplência e ativos problemáticos (%) | idem |
| `credito_estoque_indexador_...` | Carteira por indexador | idem |
| `credito_estoque_parcela_...` | Parcela média | idem |
| `fontes_sbpe_saldo`, `fontes_lci_br`, `fontes_lig_*`, `fontes_cri_*` (*) | **Funding**: saldo da poupança SBPE, estoque de LCI/LIG/CRI | Brasil |
| `direcionamento_{aplicacao,aquisicao,construcao,reforma_ampliacao}_{residencial,comercial,imobiliario}` | Exigibilidade/direcionamento de poupança | Brasil |
| `imoveis_valor_avaliacao`, `imoveis_valor_compra`, `imoveis_area_*`, `imoveis_dormitorio_*`, `imoveis_tipo_{apartamento,casa}`, `imoveis_garantia_{alienacao_fiduciaria,hipoteca}`, `imoveis_implantacao_*` | **Perfil dos imóveis financiados** (avaliações bancárias) | UF |
| `indices_ivg_r`, `indices_mvg_r`, `indices_selic`, `indices_pib`, `indices_imobiliario_pib` | Índice de Valores de Garantia (preço de transação), mediana, macro | Brasil |

(*) `fontes_lci_br` confirmado na amostra; demais `fontes_*` listadas na metodologia do BCB, a confirmar na carga completa.

- **Exemplo de consulta (contratações PF SFH, Brasil, 2026):**
  `...?$filter=Info eq 'credito_contratacao_contratado_pf_sfh_br' and Data ge '2026-01-01'&$format=json`
  Retornou jan/26 R$ 7,49 bi → jul/26 R$ 12,22 bi.
- **Metodologia:** https://www.bcb.gov.br/content/estatisticas/mercadoimobiliario_docs/Metodologia.pdf
- **Lacuna:** não traz *número de unidades* financiadas (só R$) — complementar com ABECIP.

### Bloco 7 — Banco Central SGS (séries macro) 🟢

- **Endpoint:** `https://api.bcb.gov.br/dados/serie/bcdata.sgs.{código}/dados?formato=json&dataInicial=dd/mm/aaaa` (testado, sem autenticação).
- Séries úteis: Selic meta (432), Selic diária (11/1178), IPCA (433), TR (226), INCC-DI/FGV (192), poupança — captação líquida e saldo (dados abertos BCB: buscar "poupança"), concessões/saldo/inadimplência de crédito imobiliário direcionado PF (datasets 20704, 27738 etc. — confirmar códigos no portal https://dadosabertos.bcb.gov.br).
- Também Focus (expectativas Selic/IPCA) via API Olinda `Expectativas`.

### Bloco 2+5 — ABECIP 🟡

| Dado | URL | Formato |
|------|-----|---------|
| Financiamento SBPE mensal: R$ e **unidades**, construção × aquisição | https://www.abecip.org.br/credito-imobiliario/indicadores/financiamento → `download?file=unidades-site81.xlsx` (ref. ago/2026) | XLSX (nome do arquivo muda a cada mês → scraping leve da página) |
| Caderneta de poupança (captação, resgate, saldo SBPE) | https://www.abecip.org.br/credito-imobiliario/indicadores/caderneta-de-poupanca | XLSX |
| CGI (home equity) | https://www.abecip.org.br/credito-imobiliario/indicadores/cgi | XLSX |
| **IGMI-R** (índice de preços de transação, jan/2014–ago/2026, Brasil + capitais) | https://www.abecip.org.br/igmi-r-abecip/serie-historica | XLSX |
| Informativos mensais / coletivas (projeções anuais) | https://www.abecip.org.br/imprensa/informativos-mensais | PDF |

Dado de contexto 1S/2026 (Abecip): R$ 180,9 bi financiados (+23% a/a); SBPE R$ 93,7 bi (+29%); jul/26 recorde histórico SBPE (R$ 20,96 bi, 57,9 mil imóveis); projeção 2026 revista para +25% (R$ 410 bi).

### Bloco 1 — Oferta primária (lançamentos, vendas, estoque, distratos)

| Fonte | Cobertura | Dados | Periodicidade | Acesso |
|-------|-----------|-------|---------------|--------|
| **Abrainc-Fipe — Indicadores** | Nacional (20 incorporadoras associadas, viés grandes empresas/MCMV) | Lançamentos, vendas, entregas, oferta final, **distratos**, por segmento (MCMV × médio/alto padrão), VGV | Mensal (≈ D+45) | 🟠 PDF em `https://cdn.abrainc.org.br/files/{ano}/{mês}/Release_Indicadores_{AAAAMM}.pdf` (padrão previsível; dados extraíveis das tabelas) |
| **Secovi-SP — PMI** | Cidade de São Paulo (maior mercado) | Lançamentos, vendas, VSO mensal e 12m, oferta (estoque 36m), VGV deflacionado INCC | Mensal | 🟠 Release/PDF + planilhas no site do Secovi-SP |
| **CBIC Hub de Dados — Indicadores Imobiliários** | Consolida pesquisas regionais (Sinduscons/Ademis: SP, RJ, BH, POA, Curitiba, Fortaleza, Recife, Belém, Goiânia, DF…) | Lançamentos, vendas, oferta, VSO por cidade | Mensal/trimestral | 🟡 https://cbic.org.br/hubdedados/mercado — XLSX, **cadastro gratuito** exigido para boa parte |
| **Brain Inteligência Estratégica** | Censos em várias praças (com Sinduscons) | Lançamentos, vendas, preço, estoque | Trimestral | 🟠 PDFs públicos parciais; detalhado 🔴 pago |
| Ademi-RJ, Sinduscon-MG, Sinduscon-RS, Ademi-PE etc. | Praças individuais | idem | Mensal/trim. | 🟠 PDFs |
| Incorporadoras listadas (prévias operacionais B3) | ~20 companhias (Cyrela, MRV, Direcional, Tenda, EZTec…) | Lançamentos, vendas líquidas, VSO, estoque, distratos, landbank | Trimestral (prévia ≈ D+15) | 🟠 PDF nas RIs / CVM (RAD) — ótimo *proxy* antecedente |

### Bloco 4 — Minha Casa Minha Vida / FGTS

| Fonte | Dados | Acesso |
|-------|-------|--------|
| BCB Olinda `credito_contratacao_contratado_pf_fgts_{uf}` | R$ contratados com recursos FGTS por UF/mês | 🟢 já coberto |
| Ministério das Cidades — painéis e portarias | Unidades contratadas por faixa/UF, metas (1 mi/ano em 2026-27), orçamento FGTS 2026 R$ 144,5 bi | 🟠 painéis Power BI / PDF; dados abertos em dados.gov.br a verificar |
| FGTS — Conselho Curador / Caixa | Orçamento operacional, arrecadação líquida, aplicações em habitação | 🟠 PDF/relatórios |
| Caixa — dados abertos habitação | Contratações por município (historicamente obtido via LAI) | 🟠/🔴 irregular |

### Bloco 5 — Preços

| Fonte | O que é | Cobertura | Acesso |
|-------|---------|-----------|--------|
| **FipeZap** (Fipe/OLX) | Preço de **oferta** (anúncios) venda e locação, residencial e comercial; nº-índice, var. mensal, R$/m², rental yield, por nº dormitórios | 56 cidades (22 capitais) + Índice Brasil; desde 2008 | 🟡 https://downloads.fipe.org.br/indices/fipezap/fipezap-serieshistoricas.xlsx (URL fixa, mensal) |
| **IGMI-R ABECIP/FGV** | Preço de **transação** (avaliações bancárias) | Brasil + 10 capitais, jan/2014– | 🟡 XLSX (ver ABECIP) |
| **IVG-R / MVG-R (BCB)** | Índice/mediana de valores de garantia (avaliações) | Brasil | 🟢 Olinda `indices_ivg_r`, `indices_mvg_r` |
| Índice QuintoAndar / Imovelweb / DataZAP | Aluguel e venda, oferta | Capitais | 🟠 releases |

### Bloco 6 — Custos & atividade

| Fonte | Dados | Acesso |
|-------|-------|--------|
| **IBGE SIDRA** (API `https://apisidra.ibge.gov.br/values/t/{tabela}/...`) | SINAPI (custo m² por UF), PIB construção (Contas Nacionais trimestrais), PNAD Contínua (ocupados na construção), PAIC (empresas) | 🟢 API pública sem auth |
| **FGV IBRE** | INCC-M / INCC-DI, Sondagem da Construção, confiança do consumidor | 🟢 INCC via SGS (192, 7458…); sondagens 🟠 PDF/portal IBRE |
| **CBIC / Sinduscon** — CUB/m² | Custo unitário básico por UF | 🟡 cub.org.br + Hub CBIC |
| **CAGED (MTE)** | Emprego formal na construção, por UF | 🟡 Painel PDET / microdados |
| **SNIC** | Consumo aparente de cimento (mensal, por UF) | 🟠 PDF/release |
| **CNI** | Sondagem Indústria da Construção (NUCI, confiança) | 🟠 PDF/portal |

### Bloco 8 — Transações

| Fonte | Dados | Acesso |
|-------|-------|--------|
| **ONR — Estatísticas** (https://onr.org.br/estatisticas) | Atos registrais eletrônicos por UF, volumes, séries históricas (portal lançado 2025) | 🟠 painéis; verificar se há API/CSV |
| Prefeituras — ITBI (SP: dados abertos da PMSP) | Transações e valores por bairro/mês | 🟡 CSV (SP), demais 🟠 |

### Bloco 9 — Demanda estrutural

| Fonte | Dados | Acesso |
|-------|-------|--------|
| **Fundação João Pinheiro / CBIC** | Déficit habitacional (componentes, UF) | 🟡 Hub CBIC `/deficit` + PDF FJP |
| IBGE Censo 2022 / Projeções | Domicílios, população, faixas etárias | 🟢 SIDRA |

---

## 3. Priorização para o MVP

**Tier 1 — automatizável hoje via API (base do painel):**
1. BCB Olinda Mercado Imobiliário — crédito (R$, taxa, LTV, indexador, inadimplência, carteira) por fonte e UF; funding (SBPE, LCI); perfil dos imóveis; IVG-R.
2. BCB SGS — Selic, IPCA, TR, INCC, poupança.
3. IBGE SIDRA — SINAPI, PIB construção, PNAD construção.

**Tier 2 — Excel com URL estável (parser simples):**
4. FipeZap (séries históricas completas).
5. ABECIP — financiamento SBPE em **unidades**, poupança, IGMI-R.
6. CBIC Hub de Dados (com cadastro) — indicadores imobiliários regionais, déficit, CUB.

**Tier 3 — PDF/scraping (maior esforço, mas é onde estão lançamentos/vendas/estoque):**
7. Abrainc-Fipe releases (URL previsível, extração de tabela do PDF).
8. Secovi-SP PMI.
9. Prévias operacionais das incorporadoras listadas.
10. Ministério das Cidades (MCMV), ONR, SNIC.

**Observação importante sobre o Bloco 1:** não existe fonte pública nacional, aberta e automatizável de lançamentos/vendas/estoque. O que existe são (a) amostras associativas (Abrainc = grandes incorporadoras; Secovi = SP) e (b) pesquisas regionais fragmentadas. O painel deve deixar explícito a cobertura de cada série e, idealmente, triangular Abrainc + Secovi + prévias das listadas.

---

## 4. Arquitetura proposta (rascunho)

```
[Coletores agendados]  →  [Camada de dados]  →  [Painel]
 - bcb_olinda.py             parquet/SQLite        HTML estático (Plotly/ECharts)
 - bcb_sgs.py                tabela longa:         ou Streamlit/Observable
 - sidra.py                  fonte | serie | uf |  páginas por bloco (1-9)
 - fipezap.py (xlsx)         data | valor | unid.  + "painel executivo" com
 - abecip.py (xlsx)          + catálogo de séries    ~12 KPIs e semáforos
 - abrainc_pdf.py            (metadados, cobertura,
 - secovi.py                  defasagem, fonte)
```

- Periodicidade: coleta mensal (dia 5 e dia 20 para pegar divulgações defasadas).
- Cada série carrega metadados: fonte, URL, cobertura geográfica, data de referência, data de coleta, nota metodológica (oferta × transação, amostra × censo).
- Deflator padrão: IPCA (séries financeiras) e INCC (VGV/oferta, como faz o Secovi).

---

## 5. Decisões em aberto

1. **Recorte geográfico do MVP:** Brasil + UFs (o que o BCB permite) ou já incluir cidades (SP via Secovi; capitais via FipeZap/IGMI-R)?
2. **Público do painel:** uso interno/analítico (Streamlit, Python) ou publicação (HTML estático / artifact)?
3. **Profundidade do Bloco 1:** aceitar o esforço de extrair PDFs da Abrainc/Secovi no MVP, ou começar só com Tier 1+2 e adicionar depois?
4. **Cadastro no Hub CBIC:** vale fazer (gratuito) para liberar as pesquisas regionais consolidadas.
