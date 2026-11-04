# Tarefa agendada: atualização semanal do painel financeiro

Para criar no app do Claude (Code): abra **Tarefas agendadas**, crie uma tarefa nova com os dados abaixo e cole o texto do prompt.

- **Nome:** Atualizar painel financeiro (UAU)
- **Quando:** toda segunda-feira às 8h (cron `0 8 * * 1`)
- **Pasta de trabalho:** `D:\Claude\painel-imobiliario`

A tarefa só roda com o app aberto; se ele estiver fechado no horário, roda quando for aberto. Ela abre o UAU e espera o seu login, faz as exportações, atualiza a base e o painel e termina com o comando de publicação no site para você rodar.

## Prompt

```text
Atualização semanal do painel financeiro da APEX Engenharia a partir do ERP UAU (Globaltec). Responda ao usuário em português.

Projeto: D:\Claude\painel-imobiliario (branch de trabalho looker-redesign). Leia primeiro, por inteiro:
- docs/rotina-atualizacao-uau.md (a rotina oficial, com os parâmetros de cada exportação)
- a memória do projeto em C:\Users\eduardo.aroeira\.claude\projects\D--Claude-painel-imobiliario\memory\ (MEMORY.md e os arquivos citados)

Regras de segurança, sem exceção:
- Nunca digite senha. O login no UAU é sempre do usuário: abra o UAU (Start-Process "C:\UAU\Financ.exe" pelo PowerShell), peça para ele logar e espere ele responder "logado".
- Só extraia dados. Nunca grave, altere ou exclua nada no UAU. Na tela Fechamento de Caixa/Conta, nunca clique no botão "Fechamento" da barra; use só Buscar e Imp.
- A pasta dados/ fica fora do git e nunca é publicada em claro.
- Não commite nem envie dashboard/financeiro.html. Esse passo é do usuário.

Passos:
1. Crie a pasta dados/uau/brutos/AAAA-MM-DD com a data de hoje.
2. Abra o UAU e peça o login. Depois exporte, conforme a rotina, para essa pasta: base13_modo0_apagar_areceber.xls (estrutura 13, relatório 0, 01/07/2017 a 31/12/2035), base13_modo1_semana.xls (estrutura 13, relatório 1, de hoje menos 15 dias até hoje), bancos_saldos.xls (Conciliação > Resumo, todas as contas, mês corrente) e fechamentos_caixa.xls (Financeiro > Fechamento de Caixa/Conta, empresa "Vários", 01/01 do ano anterior até hoje pelo calendário).
   Dicas de controle de tela no UAU: request_access com "Financ.exe" (processo em execução); Utilitários > Visualizador de resultados > pasta raiz Relatórios > Buscar > selecionar a estrutura 13 e abrir pelo botão "Relatório" da barra lateral; o campo de data final recusa a primeira digitação (feche o aviso e digite de novo); na grade Registros o clique simples não seleciona linha, use mouse_move + left_mouse_down/left_mouse_up; no "Salvar como" digite só o nome do arquivo, em pedaços de até 10 caracteres; se o screenshot vier todo escuro, capture a tela pelo PowerShell (System.Drawing CopyFromScreen); se o UAU travar por mais de 15 minutos, encerre o processo e peça novo login.
3. Rode no projeto: python -m financeiro.atualizar e depois python -m financeiro.publicar.
4. Confira: abra dados/uau/painel/painel_financeiro.html num servidor local (configuração "financeiro" do .claude/launch.json), verifique que não há erros de console, que a data de referência é a de hoje e que o aviso "Caixa fechado e contas conciliadas até ..." aparece. Compare com a semana anterior os totais do Resumo da base (a pagar, a receber, saldo bancário) e aponte variações grandes.
5. Se mudou algum código ou documento, commite em looker-redesign e envie. Não toque em dashboard/financeiro.html.
6. Termine dizendo ao usuário o que mudou (data de referência, data de conciliação, totais principais) e passe a ele, num bloco bash, o comando para publicar no site:
cd /d D:\Claude\painel-imobiliario && git add dashboard/financeiro.html && git commit -m "Site: painel financeiro (base de DD/MM/AAAA)" && git push origin looker-redesign && git checkout main && git pull origin main && git merge --no-ff looker-redesign -m "Site: painel financeiro (base de DD/MM/AAAA)" && git push origin main && git checkout looker-redesign
(substitua DD/MM/AAAA pela data da base). Depois que ele publicar, acompanhe o deploy do GitHub Pages e confirme que https://dudaroeira.github.io/painel-imobiliario/financeiro.html foi atualizado.

Se algo bloquear (UAU fora do ar, login não feito, exportação com erro), pare, diga exatamente o que falta e não tente contornar as regras acima.
```
