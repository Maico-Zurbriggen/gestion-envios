# Despliegue en el VPS

La app está publicada en **https://envios.179-236-253-243.sslip.io**, en el VPS de Hostinger `srv2042235.hstgr.cloud` (Ubuntu 24.04). La base es Neon.

En ese VPS también corre la app **soderia**. Gestión de envíos está aislada y **no se toca nada de soderia**: ni su sitio de Nginx, ni su certificado, ni su servicio, ni su PostgreSQL.

## Cómo está armado

| Pieza | Dónde |
|---|---|
| Código | `/opt/gestion-envios/back` (con su `.venv` y su `.env`) y `/opt/gestion-envios/front/dist` |
| Usuario del sistema | `gestionenvios` |
| API | Servicio `gestion-envios-api` en `127.0.0.1:8010`, con un solo proceso para que la revisión de plazos no se duplique. Copia: [`deploy/vps/gestion-envios-api.service`](../../../deploy/vps/gestion-envios-api.service) |
| Nginx | Archivo propio `zz-gestion-envios`, que carga después de soderia para que soderia siga siendo la respuesta por IP. Copia: [`deploy/vps/nginx-gestion-envios.conf`](../../../deploy/vps/nginx-gestion-envios.conf) |
| HTTPS | Certificado `gestion-envios` de Let's Encrypt, que se renueva solo y recarga Nginx |
| Dirección | `sslip.io` traduce el nombre a la IP del VPS, sin registrar nada. Si después usan un dominio propio, hay que cambiar `server_name`, sacar otro certificado y actualizar `FRONTEND_BASE_URL` |

El `.env` del servidor es una copia del de desarrollo con `ENVIRONMENT=production`, `DEBUG=false` y `FRONTEND_BASE_URL` con la dirección pública. No va al repositorio.

## Publicar una versión nueva

Desde la raíz del repositorio, con la clave SSH del despliegue en `~/.ssh/gestion_envios_vps`:

```bash
bash deploy/vps/actualizar.sh
```

Publica el último commit de la rama actual: compila el frontend, sube los dos paquetes, instala dependencias y reinicia solo `gestion-envios-api`. Al arrancar, la API aplica en Neon las migraciones pendientes.

## Consultar el estado

```bash
ssh -i ~/.ssh/gestion_envios_vps root@179.236.253.243
systemctl status gestion-envios-api
journalctl -u gestion-envios-api -n 100 --no-pager
```

## Cuidados

- Antes de recargar Nginx, verificar con `nginx -t`.
- Es la misma base que se usa en desarrollo: todo lo que se haga en una se ve en la otra, y los avisos por email y WhatsApp son reales.
- El VPS vence el 7 de noviembre de 2026: renovarlo para que no se caigan esta app ni soderia.
