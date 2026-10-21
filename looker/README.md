# Looker Studio (gratuito) sobre os dados do painel

O site publica, a cada atualização, os dados em formato longo em
`https://dudaroeira.github.io/painel-imobiliario/data/` (um CSV por tema + `index.json`).
O Looker Studio não lê URLs diretamente; a ponte gratuita é uma planilha Google que se
atualiza sozinha com o script deste diretório.

## 1. Criar a planilha-ponte (uma vez, ~5 minutos)

1. Em [sheets.new](https://sheets.new) crie uma planilha chamada **Painel Imobiliário — dados**.
2. Menu **Extensões → Apps Script**. Apague o conteúdo e cole o arquivo [`apps-script.gs`](apps-script.gs). Salve (ícone de disquete).
3. Clique em **Executar** com a função `atualizarTudo` selecionada. Na primeira vez o Google pede autorização
   (acesso à planilha e a URLs externas) — aceite. Em ~1 minuto as abas `credito_uf`, `funding`, `oferta_cbic`,
   `oferta_amostras`, `precos`, `imoveis`, `macro_custos` e `_meta` aparecem preenchidas.
4. No Apps Script, ícone de **relógio (Gatilhos) → Adicionar gatilho**: função `atualizarTudo`, origem
   *Acionador de tempo*, *Timer diário*, entre 7h e 8h. A planilha passa a se atualizar todo dia depois do site.

## 2. Conectar o Looker Studio

1. Em [lookerstudio.google.com](https://lookerstudio.google.com) → **Criar → Fonte de dados → Planilhas Google** → escolha a planilha e a aba (comece por `credito_uf`).
2. Confira os tipos: `date` = Data (AAAA-MM-DD), `value` = Número, os demais = Texto. Clique em **Conectar**.
3. Repita para as outras abas que quiser (uma fonte de dados por aba). Elas podem ser combinadas num mesmo relatório.

## 3. Montar as visões (sugestão de partida)

Dimensões úteis em todas as abas: `series_id` (o que medir), `region` (UF / região / capital), `date`.

| Visão | Fonte | Como montar |
|---|---|---|
| Crédito por UF | `credito_uf` | Mapa geográfico (dimensão `region`, tipo *Subregião* do Brasil) + filtro `series_id` = `credito_contratacao_contratado_pf_sfh`; métrica `value` SUM; intervalo de data = últimos 12 meses |
| Comparação de UFs no tempo | `credito_uf` | Série temporal, quebra por `region`, controle de filtro para `region` e `series_id` |
| Taxa × LTV × inadimplência | `credito_uf` | Tabela dinâmica com `series_id` nas colunas e `region` nas linhas, data = último mês |
| Oferta por região e segmento | `oferta_cbic` | Colunas empilhadas: dimensão `date`, quebra `region`, filtro `series_id` (`lancamentos`, `vendas`, `oferta`, `lancamentos_mcmv`, `lancamentos_map`…) |
| Preços por capital | `precos` | Série temporal, filtro `series_id = igmi_r`, quebra `region` |

Dicas: use **Controles → Lista suspensa** para `series_id` e `region` no topo do relatório (viram filtros globais);
em métricas de fluxo (crédito contratado) use SUM com agregação por mês ou trimestre; em taxas, LTV, índices e
estoques use AVG ou "último valor" (ordenar por data e limitar a 1).

## Limites

- Planilhas Google: 10 milhões de células; hoje os dados somam ~1,2 milhão (a maior aba, `credito_uf`, tem ~100 mil linhas).
- O script do Google tem cota de 20 mil chamadas de URL por dia; usamos 8.
- Se um dia a planilha ficar lenta, o mesmo CSV pode ir para o BigQuery (nível gratuito: 10 GB e 1 TB de consultas/mês).
