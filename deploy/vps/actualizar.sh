#!/usr/bin/env bash
# Publica en el VPS el último commit de la rama actual. Se corre desde la raíz del repositorio (Git Bash o Linux):
#
#   bash deploy/vps/actualizar.sh
#
# Compila el frontend, sube el backend y el frontend, instala dependencias y reinicia solo el servicio
# gestion-envios-api. No toca nada más del servidor: el .env y el entorno de Python del servidor se conservan.
set -euo pipefail

SERVIDOR="${SERVIDOR:-root@179.236.253.243}"
CLAVE="${CLAVE:-$HOME/.ssh/gestion_envios_vps}"
DOMINIO="${DOMINIO:-gestionenvios.duckdns.org}"
DESTINO=/opt/gestion-envios
SSH=(ssh -i "$CLAVE" -o BatchMode=yes "$SERVIDOR")

if [ -n "$(git status --porcelain)" ]; then
  echo "Hay cambios sin commitear: se publica el último commit, no el directorio de trabajo." >&2
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "1/4 Empaquetando el backend ($(git rev-parse --short HEAD))"
git archive --format=tar.gz -o "$TMP/back.tar.gz" HEAD:Back

echo "2/4 Compilando el frontend para https://$DOMINIO"
(cd front && VITE_API_URL="https://$DOMINIO/api/v1" npm run build >/dev/null)
tar --force-local -czf "$TMP/front-dist.tar.gz" -C front/dist .

echo "3/4 Subiendo"
scp -i "$CLAVE" -o BatchMode=yes "$TMP/back.tar.gz" "$TMP/front-dist.tar.gz" "$SERVIDOR:/tmp/"

echo "4/4 Instalando y reiniciando gestion-envios-api"
"${SSH[@]}" "set -e
tar -xzf /tmp/back.tar.gz -C $DESTINO/back
rm -rf $DESTINO/front/dist.nuevo && mkdir -p $DESTINO/front/dist.nuevo
tar -xzf /tmp/front-dist.tar.gz -C $DESTINO/front/dist.nuevo
rm -rf $DESTINO/front/dist && mv $DESTINO/front/dist.nuevo $DESTINO/front/dist
rm /tmp/back.tar.gz /tmp/front-dist.tar.gz
chown -R gestionenvios:gestionenvios $DESTINO
find $DESTINO/front/dist -type d -exec chmod 755 {} + ; find $DESTINO/front/dist -type f -exec chmod 644 {} +
$DESTINO/back/.venv/bin/pip install --quiet -r $DESTINO/back/requirements.txt
systemctl restart gestion-envios-api
for i in \$(seq 1 60); do curl -s -o /dev/null http://127.0.0.1:8010/health && break; sleep 1; done
echo \"Servicio: \$(systemctl is-active gestion-envios-api) | Web: \$(curl -s -o /dev/null -w %{http_code} https://$DOMINIO/)\""
echo "Listo: https://$DOMINIO"
