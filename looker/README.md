# Looker Studio (gratuito) sobre os dados do painel

Relatório: [Painel Imobiliário — BI](https://lookerstudio.google.com/reporting/983431e2-c597-41cb-8b1b-69c86977cff8)
(também embutido na aba **BI (Looker)** do site).

A cadeia é toda automática e sem custo:

1. **Site** (GitHub Actions, todo dia às 06h de Brasília) coleta as fontes e publica CSVs enxutos em
   `https://dudaroeira.github.io/painel-imobiliario/data/sheets/`, com colunas em português:
   `serie, regiao, tema, mes, valor`. Há ainda `indicadores.csv` (os números da página de abertura, já com os
   textos prontos de cada cartão: `*_txt` e `*_nota`) e `series.csv` (dicionário das séries).
2. **Planilha-ponte** no Google Drive
   ([Painel Imobiliário — dados (Looker)](https://docs.google.com/spreadsheets/d/1P6lHKtxmYiZdbf2EelqBSYiFiytCzgs4-iScZYJHNu0/edit)),
   com o script [`apps-script.gs`](apps-script.gs) (Extensões > Apps Script, projeto "Ponte do painel para o
   Looker"). Todo dia entre 8h e 9h ele baixa os 11 CSVs, empilha tudo na aba **tudo** (com `mes` como data de
   verdade) e copia `indicadores.csv` para a aba **indicadores**. A célula G1 da aba `tudo` mostra a hora da
   última carga.
3. **Looker Studio** lê as abas `tudo` e `indicadores`. O cache renova a cada 12 horas; para forçar, use
   *Atualizar dados* no menu de três pontos do relatório.

## Como o relatório está organizado

- **Visão geral**: os principais indicadores, cada um com o último valor, a variação e a referência.
- **Uma página por tema**, todas com o mesmo modelo: período, série e região no topo; um indicador do período
  com minigráfico; a evolução mensal da região escolhida; e o ranking das regiões (sem o total Brasil).
  Cada página filtra a aba `tudo` pelo código do tema (filtros "Tema …" em *Recurso > Gerenciar filtros*).

| Tema (código) | Página | Série padrão | Indicador |
|---|---|---|---|
| `cred` | Crédito contratado | PF · SFH/SBPE | soma |
| `idx` | Crédito por indexador | IPCA | soma |
| `taxa` | Taxa de juros e LTV | Taxa · SFH/SBPE | média |
| `cart` | Carteira de crédito | Saldo · SFH/SBPE | média |
| `inad` | Inadimplência | SFH/SBPE | média |
| `fund` | Funding | Saldo da poupança SBPE | média |
| `cbic` | Oferta CBIC | Lançamentos residenciais (CBIC · ~220 cidades) | soma |
| `amos` | Abrainc e Secovi-SP | Vendas — total (Abrainc) | soma |
| `prec` | Preços de imóveis | IGMI-R (jan/2014 = 100) | média |
| `imov` | Perfil dos imóveis | Valor de avaliação (R$) | média |
| `macro` | Custos e macro | SINAPI · custo por m² (R$) | média |

Fluxos (crédito contratado, lançamentos, vendas) somam no período; taxas, saldos e índices mostram a média.
O filtro de região vale só para o indicador e o gráfico mensal (estão agrupados com ele). O ranking ignora esse
filtro e exclui o total Brasil, para não misturar o país com as regiões.

Os rótulos das séries não levam vírgula: o Looker lê a seleção padrão dos controles como lista separada por
vírgulas.

## Recriar a planilha (se precisar)

1. Crie uma planilha vazia no Google Drive.
2. Em *Extensões > Apps Script*, cole o conteúdo de [`apps-script.gs`](apps-script.gs) e salve.
3. Escolha a função `instalar` e clique em *Executar*. Na primeira vez o Google pede autorização ("O Google não
   verificou este app" > *Avançado* > *Permitir*): o script só lê os CSVs do site e escreve nesta planilha.
4. `instalar` faz a primeira carga e agenda a atualização diária. Depois, reconecte as fontes do Looker às abas
   `tudo` e `indicadores` da nova planilha.

## Limites

- O Google Sheets aceita 10 milhões de células; a aba `tudo` usa cerca de 700 mil (140 mil linhas × 5 colunas).
- Cada execução do Apps Script pode durar até 6 minutos; a carga completa leva menos de um.
- O IMPORTDATA foi abandonado: com 11 arquivos grandes ele esbarrava na cota do Google ("pode levar mais tempo
  devido a uma grande quantidade de solicitações").
