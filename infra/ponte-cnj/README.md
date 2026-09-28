# Ponte CNJ — saída de rede no Brasil

O Comunica CNJ recusa requisição de IP fora do Brasil (bloqueio
geográfico no CloudFront, HTTP 403). O servidor principal da plataforma
está nos Estados Unidos. Esta ponte é uma máquina pequena em **São
Paulo** que apenas repassa a consulta ao Diário — nada é guardado nela.

Com a ponte no ar, a varredura volta a rodar sozinha de madrugada, sem
depender de alguém abrir a tela.

## 1. A máquina (Oracle Cloud — Always Free)

- Região de origem: **Brasil Leste (São Paulo)**.
  ⚠️ A região de origem **não pode ser trocada depois**, e os recursos
  gratuitos só existem nela. Escolher errado significa refazer a conta.
- Instância: `VM.Standard.E2.1.Micro` (AMD, Always Free) ou
  `VM.Standard.A1.Flex` (ARM, 1 OCPU / 6 GB — também Always Free).
- Imagem: Ubuntu 22.04 ou 24.04.
- Guardar a chave SSH que o console oferece no momento da criação: ela
  não é mostrada de novo.

Liberar as portas 80 e 443:
- no console: *Networking → VCN → Security Lists → Ingress Rules*,
  origem `0.0.0.0/0`, TCP, portas 80 e 443;
- na máquina, o Ubuntu da Oracle vem com iptables fechado:

```bash
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save
```

## 2. Confirmar que dali o CNJ responde

Antes de qualquer instalação — é o teste que decide tudo:

```bash
curl -s -o /dev/null -w '%{http_code}\n' \
  'https://comunicaapi.pje.jus.br/api/v1/comunicacao?numeroOab=10849&ufOab=RO&itensPorPagina=1&pagina=1'
```

`200` = o caminho está aberto. `403` = a máquina não está sendo vista
como brasileira; nada adiante funcionará e é hora de parar e rever.

## 3. Instalar

```bash
sudo apt update && sudo apt install -y docker.io docker-compose-v2 git
sudo git clone https://github.com/advfabioscunha-design/fsc-legal-os.git /opt/fsc
cd /opt/fsc/infra/ponte-cnj
printf 'PONTE_TOKEN=%s\n' "$(openssl rand -hex 24)" | sudo tee .env
sudo cat .env          # guardar este token: ele vai no .env do backend
sudo docker compose up -d --build
```

## 4. DNS

Criar um registro **A** para `br.fscadvocaciadigital.com.br` apontando
para o IP público da instância. O Caddy emite o certificado sozinho na
primeira visita. Sem HTTPS, o token viajaria em texto claro.

## 5. Ligar no backend

No `.env` do servidor principal:

```
COMUNICA_PONTE_URL=https://br.fscadvocaciadigital.com.br/comunicacao
COMUNICA_PONTE_TOKEN=<o token gerado acima>
```

e `docker compose up -d --build api worker`.

Conferir:

```bash
curl -s localhost:8000/api/v1/processos/diagnostico-cnj
```

## Manutenção

- A Oracle recupera instâncias Always Free **ociosas** (aviso por
  e-mail antes). Esta ponte recebe uma consulta por dia, o que pode
  contar como ociosa: se o aviso chegar, basta responder pelo console
  ou manter a instância em uso. Vale não ignorar o e-mail.
- A ponte não guarda nada: reinstalá-la do zero custa dez minutos e não
  perde dado nenhum.
