# Tribunais do escritório e por onde a plataforma chega em cada um

## O ponto que muda tudo

**e-SAJ, eproc, PJe, Projudi e SEEU são sistemas, não fontes de dados.**
Não existe "integrar o e-SAJ" e depois "integrar o eproc" para saber das
publicações: quem publica é o tribunal, e a publicação de todos eles sai
num lugar só — o **Diário de Justiça Eletrônico Nacional (DJEN)**.

Isso já está funcionando. Na primeira varredura pela OAB voltaram, na
mesma consulta, TRF4 (eproc), TJSP (e-SAJ), TRT14 (PJe) e TJRO (PJe).

## Os dois canais

| Canal | O que traz | Como busca | Custo |
|---|---|---|---|
| **DJEN / Comunica CNJ** | o que foi **publicado**: intimações, sentenças, despachos, pautas | por OAB e por número | grátis |
| **DataJud CNJ** | **metadados e movimentos**: classe, assunto, órgão, cada movimento com data | por número, por tribunal | grátis |

O DJEN abastece a esteira e os prazos. O DataJud confirma se o processo
ainda anda — pelo **código do movimento** da Tabela Processual Unificada
do CNJ, que é igual em qualquer tribunal e qualquer sistema. Ler o
código é mais confiável que caçar a palavra "arquivado" num texto de
sentença, que muda de juízo para juízo.

## Os onze tribunais configurados

| Tribunal | Sistema | Publicações | Movimentos |
|---|---|---|---|
| TJ Rondônia | PJe | DJEN | DataJud `tjro` |
| TJ Santa Catarina | eproc | DJEN | DataJud `tjsc` |
| TJ Rio Grande do Sul | eproc | DJEN | DataJud `tjrs` |
| TJ Paraná | Projudi e PJe | DJEN | DataJud `tjpr` |
| TJ Mato Grosso | PJe | DJEN | DataJud `tjmt` |
| TJ Bahia | PJe e Projudi | DJEN | DataJud `tjba` |
| TJ São Paulo | e-SAJ | DJEN | DataJud `tjsp` |
| TRT 12ª (SC) | PJe | DJEN | DataJud `trt12` |
| TRT 14ª (RO/AC) | PJe | DJEN | DataJud `trt14` |
| TRF 1ª Região | PJe | DJEN | DataJud `trf1` |
| TRF 4ª Região | eproc | DJEN | DataJud `trf4` |

Primeiro e segundo grau vêm juntos: o DJEN não separa, e o DataJud traz
o campo `grau` em cada processo.

O tribunal é descoberto pelo **próprio número CNJ** (segmento da Justiça
e código do tribunal, Resolução 65/2008), não pelo que veio escrito na
publicação. Conferido nos números reais do acervo.

## O que os canais NÃO cobrem — e o que fazer

**SEEU (execução penal).** Fora do DataJud e com pouca publicação no
DJEN. Esses processos precisam ser cadastrados pelo número, à mão, e
acompanhados no portal. A plataforma guarda o prazo e avisa; ela não
descobre o movimento sozinha.

**Intimação feita só no portal do tribunal**, sem sair no Diário — o PJe
chama de "intimação eletrônica". Só aparece entrando no sistema com o
certificado digital do advogado. Nenhuma API pública entrega isso.

**Processos em segredo de justiça**, que não aparecem em nenhuma das
duas bases.

Para esses três casos há dois caminhos, e os dois custam: um
monitoramento pago (Escavador, Judit — a partir de ~R$ 100/mês) que
acessa os portais com o certificado, ou conferência manual periódica.

## Onde isso vive no código

- `backend/app/core/tribunais.py` — o cadastro e a leitura do número CNJ
- `backend/app/integracoes/comunica_cnj.py` — DJEN
- `backend/app/integracoes/datajud.py` — DataJud, inclusive `por_numero`
- `GET /api/v1/tribunais` — a lista com os canais de cada um
- `GET /api/v1/tribunais/cobertura` — testa o DataJud tribunal a tribunal
- `GET /api/v1/processos/datajud?numero=...` — movimentos de um processo
