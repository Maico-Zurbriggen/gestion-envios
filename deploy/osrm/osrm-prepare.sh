#!/bin/sh
# Prepara el mapa de Argentina (Geofabrik, ~400 MB, lo baja osrm-download) para OSRM (perfil auto, algoritmo MLD).
# Se corre una vez y después cada mes para actualizar calles: tarda unos minutos y usa varios GB de RAM.
set -e
cd /data
PBF=argentina-latest.osm.pbf
# El mapa lo baja el servicio osrm-download (docker compose lo corre antes que este).
[ -s "$PBF" ] || { echo "Falta $PBF: correr  docker compose -f deploy/osrm/docker-compose.yml --profile preparar run --rm osrm-prepare"; exit 1; }
osrm-extract -p /opt/car.lua "$PBF"
osrm-partition argentina-latest.osrm
osrm-customize argentina-latest.osrm
echo "OSRM listo: levantar con  docker compose -f deploy/osrm/docker-compose.yml up -d osrm"
