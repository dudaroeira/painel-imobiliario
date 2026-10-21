/**
 * Painel Imobiliário → Google Sheets (ponte para o Looker Studio)
 *
 * Baixa os CSVs publicados pelo painel (dashboard/data/) e grava cada um numa aba
 * desta planilha. Rode `atualizarTudo` uma vez à mão e depois agende um gatilho
 * diário (Gatilhos → Adicionar → atualizarTudo → Acionador de tempo → Diário, 07:00).
 *
 * Formato das abas (todas iguais, "formato longo"):
 *   source | series_id | name | region | unit | freq | date | value
 * No Looker Studio, `date` é a dimensão de data, `value` a métrica e
 * series_id / name / region são os filtros e as quebras.
 */
const BASE = 'https://dudaroeira.github.io/painel-imobiliario/data/';
const ARQUIVOS = ['credito_uf', 'funding', 'oferta_cbic', 'oferta_amostras', 'precos', 'imoveis', 'macro_custos'];

function atualizarTudo() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const indice = JSON.parse(UrlFetchApp.fetch(BASE + 'index.json', { muteHttpExceptions: true }).getContentText());
  for (const nome of ARQUIVOS) {
    const csv = UrlFetchApp.fetch(BASE + nome + '.csv', { muteHttpExceptions: true }).getContentText('UTF-8');
    const linhas = Utilities.parseCsv(csv);
    // value como número e date como data, para o Looker reconhecer os tipos
    const iDate = linhas[0].indexOf('date'), iVal = linhas[0].indexOf('value');
    for (let r = 1; r < linhas.length; r++) {
      linhas[r][iVal] = Number(linhas[r][iVal]);
      linhas[r][iDate] = new Date(linhas[r][iDate] + 'T00:00:00');
    }
    let aba = ss.getSheetByName(nome) || ss.insertSheet(nome);
    aba.clearContents();
    aba.getRange(1, 1, linhas.length, linhas[0].length).setValues(linhas);
    aba.getRange(2, iDate + 1, linhas.length - 1, 1).setNumberFormat('yyyy-mm-dd');
    aba.setFrozenRows(1);
  }
  let meta = ss.getSheetByName('_meta') || ss.insertSheet('_meta');
  meta.clearContents();
  meta.getRange(1, 1, 2, 2).setValues([['painel gerado em', indice.built_at], ['planilha atualizada em', new Date()]]);
}
