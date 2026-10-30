# Proveniência e privacidade dos dados

## Origem

Todo conteúdo operacional do FormFlow foi criado especificamente para esta demonstração:

- layout do formulário e identidade FormFlow;
- empresa fictícia “Distribuidora Aurora Demo”;
- oito nomes de produtos fictícios;
- coordenadas, marcadores e campos;
- valores numéricos e degradações visuais;
- amostras `clean`, `noisy` e `review`;
- fixture de Ground Truth usada somente em testes.

As amostras são reproduzíveis pelo script `scripts/generate_samples.py`. O caminho de execução da
aplicação não lê a fixture de Ground Truth e o OCR apresentado ao visitante é executado pelo
Tesseract local.

## Tratamento de uploads

- bytes enviados ficam apenas na memória da sessão Streamlit;
- nenhuma imagem é gravada em arquivo, banco ou storage;
- nenhum dado é enviado a OpenAI, Google ou outro processador externo;
- não há analytics, cookies próprios, credenciais ou identificadores de usuário;
- reiniciar o fluxo remove imagem, revisão e resultado do estado da sessão.

## Exportações

CSV, XLSX e JSON são produzidos em memória a partir de um `ValidatedDocument`. O JSON contém hash
da imagem, valores estruturados, confiança, origens e eventos, mas nunca inclui bytes da imagem ou
caminhos locais.

## Fontes e licenças

O projeto incorpora a fonte Inter distribuída pelo repositório oficial Google Fonts sob SIL Open
Font License. A licença acompanha o arquivo em `assets/fonts/OFL.txt`.

## Declaração clean-room

Este é um projeto independente de portfólio. Nenhum formulário, dado, screenshot, regra de negócio,
código, prompt ou artefato de cliente foi utilizado na implementação ou nos assets públicos.
