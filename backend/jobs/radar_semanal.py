"""Execução standalone do Radar Jurimétrico (DataJud/CNJ).

Use quando preferir disparar por cron do HOST em vez do scheduler embutido:
    # crontab -e  (rodar segunda 06:00)
    0 6 * * 1 cd /opt/fsc-legal-os/backend && docker compose exec -T api \
        python -m jobs.radar_semanal >> /var/log/fsc-radar.log 2>&1
"""
import json
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from app.agentes import radar  # noqa: E402

if __name__ == "__main__":
    resultado = radar.radar_semanal()
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
