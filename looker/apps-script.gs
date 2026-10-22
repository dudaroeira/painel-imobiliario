/**
 * Ponte site -> planilha -> Looker Studio, sem IMPORTDATA (que esbarra na cota do Google com arquivos grandes).
 *
 * Instalação (uma vez): Extensões > Apps Script, cole este arquivo, salve, rode `instalar` e autorize.
 * `instalar` faz a primeira carga e agenda `atualizarTudo` para todo dia entre 8h e 9h (depois do site, às 6h).
 */
const BASE = 'https://dudaroeira.github.io/painel-imobiliario/data/sheets/';
const ABAS = ['credito_contratado', 'credito_taxa_ltv', 'credito_indexador', 'credito_carteira',
  'credito_inadimplencia', 'funding', 'oferta_cbic', 'oferta_amostras', 'precos', 'imoveis', 'macro_custos'];

function instalar() {
  ScriptApp.getProjectTriggers()
    .filter(t => t.getHandlerFunction() === 'atualizarTudo')
    .forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('atualizarTudo').timeBased().everyDays(1).atHour(8).create();
  atualizarTudo();
}

function baixar(nome) {
  const resp = UrlFetchApp.fetch(BASE + nome + '.csv?t=' + Date.now(), { muteHttpExceptions: true });
  if (resp.getResponseCode() !== 200) throw new Error(nome + ': HTTP ' + resp.getResponseCode());
  return Utilities.parseCsv(resp.getContentText('UTF-8'));
}

function atualizarTudo() {
  const ss = SpreadsheetApp.getActive();
  // aba "tudo": todas as séries empilhadas (serie, regiao, tema, mes, valor)
  const linhas = [['serie', 'regiao', 'tema', 'mes', 'valor']];
  ABAS.forEach(nome => {
    baixar(nome).slice(1).forEach(r => {
      if (!r[0]) return;
      const p = r[3].split('-');
      linhas.push([r[0], r[1], r[2], new Date(+p[0], +p[1] - 1, +p[2], 12), Number(r[4])]);
    });
  });
  escrever(ss, 'tudo', linhas, { 4: 'yyyy-mm-dd' });
  // aba "indicadores": uma linha com os números da página de abertura
  const ind = baixar('indicadores');
  const valores = ind[1].map(v => (v !== '' && !isNaN(v) ? Number(v) : v));
  escrever(ss, 'indicadores', [ind[0], valores], {});
  ss.getSheetByName('tudo').getRange('G1').setValue('Atualizado em ' + new Date().toLocaleString('pt-BR'));
}

function escrever(ss, nome, linhas, formatos) {
  const aba = ss.getSheetByName(nome) || ss.insertSheet(nome);
  aba.clear();
  const n = linhas.length, m = linhas[0].length;
  if (aba.getMaxRows() < n) aba.insertRowsAfter(aba.getMaxRows(), n - aba.getMaxRows());
  aba.getRange(1, 1, n, m).setValues(linhas);
  Object.keys(formatos).forEach(col => aba.getRange(2, +col, n - 1, 1).setNumberFormat(formatos[col]));
}
