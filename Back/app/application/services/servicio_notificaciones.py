import uuid
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

from app.application.interfaces.proveedores_mensajeria import IEmailProvider, IWhatsAppProvider
from app.application.interfaces.repositorio_notificaciones import IRepositorioNotificaciones
from app.application.interfaces.servicio_notificaciones import IServicioNotificaciones
from app.contracts.notificaciones import (
    DatosNotificacionEnvio,
    NotificacionesEnvioData,
    NotificacionesEnvioResponse,
    NotificacionItemData,
)
from app.core.config import settings
from app.core.exceptions import NotFoundException
from app.core.logging import logger
from app.domain.constants.estados_logistica import (
    CanalNotificacionEnum,
    DestinatarioNotificacionEnum,
    EstadoNotificacionEnum,
    EstadoPaqueteEnum,
    TipoAvisoEnum,
)
from app.domain.rules.circuito_rules import texto_visita
from app.domain.rules.codigos_rules import normalizar_token_seguimiento
from app.domain.rules.notificacion_rules import (
    MensajeEmail,
    MensajeWhatsApp,
    armar_email_hito,
    armar_email_nuevo_envio,
    armar_email_visita_fallida,
    armar_enlace_seguimiento,
    armar_whatsapp_hito,
    armar_whatsapp_nuevo_envio,
    armar_whatsapp_visita_fallida,
)
from app.domain.rules.plantillas_correo import (
    ADMITIDO,
    CAMPOS_CONFIGURACION,
    CAMPOS_PLANTILLA,
    DEVOLUCION,
    DEVOLUCION_LISTA,
    EN_REPARTO,
    ENTREGADO,
    LISTO_PARA_RETIRO,
    NUEVO_ENVIO_DESTINATARIO,
    NUEVO_ENVIO_REMITENTE,
    VENCIDO,
    VISITA_FALLIDA,
)
from app.domain.rules.telefono_rules import normalizar_telefono_whatsapp
from app.infrastructure.repositories.repositorio_notificaciones import RepositorioNotificaciones
from app.infrastructure.repositories.repositorio_plantillas_correo import RepositorioPlantillasCorreo

MAX_ERROR_DETALLE = 1000
NOMBRE_CANAL = {CanalNotificacionEnum.EMAIL.value: "email", CanalNotificacionEnum.WHATSAPP.value: "WhatsApp"}


def _fecha_local(momento: datetime) -> str:
    """Fecha y hora de Argentina (UTC-3) para mostrar en los correos."""
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=UTC)
    return momento.astimezone(timezone(timedelta(hours=-3))).strftime("%d/%m/%Y %H:%M")


def _fecha_corta(momento: datetime | None) -> str:
    if momento is None:
        return ""
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=UTC)
    return momento.astimezone(timezone(timedelta(hours=-3))).strftime("%d/%m/%Y")


REMITENTE = DestinatarioNotificacionEnum.REMITENTE.value
DESTINATARIO = DestinatarioNotificacionEnum.DESTINATARIO.value

HITOS = {
    TipoAvisoEnum.ADMITIDO.value: (REMITENTE,),
    TipoAvisoEnum.EN_REPARTO.value: (DESTINATARIO,),
    TipoAvisoEnum.LISTO_PARA_RETIRO.value: (DESTINATARIO,),
    TipoAvisoEnum.ENTREGADO.value: (REMITENTE, DESTINATARIO),
    TipoAvisoEnum.DEVOLUCION.value: (REMITENTE,),
    TipoAvisoEnum.VENCIDO.value: (REMITENTE,),
}
"""A quién se avisa cada hito. En una devolución, el que retira es el remitente."""

VENTANA_AVISO_HITO = timedelta(hours=12)
"""Un hito se avisa una vez por envío, canal y destinatario dentro de esta ventana.
Los bultos que se escanean juntos generan un solo aviso; una nueva salida a
reparto al día siguiente vuelve a avisar."""


def _paquetes_en_el_mismo_estado(paquete: Any) -> str:
    """Los bultos del envío que están igual que este paquete (el aviso es por envío)."""
    hermanos = [
        p.numero_paquete for p in (getattr(paquete.envio, "paquetes", None) or [])
        if p.estado == paquete.estado and p.sucursal_actual_id == paquete.sucursal_actual_id
    ]
    if paquete.numero_paquete not in hermanos:
        hermanos.insert(0, paquete.numero_paquete)
    if len(hermanos) == 1:
        return hermanos[0]
    return ", ".join(hermanos[:-1]) + f" y {hermanos[-1]}"


def _destino_whatsapp(telefono: str | None) -> str:
    """Se audita el número al que realmente se envía; si no es válido, el original para poder corregirlo."""
    numero = normalizar_telefono_whatsapp(telefono, settings.WHATSAPP_CODIGO_PAIS)
    return f"+{numero}" if numero else (telefono or "")


class ServicioNotificaciones(IServicioNotificaciones):
    """Notificaciones por email y WhatsApp (HU05 y aviso de visita de HU12).

    Cada canal y destinatario es una fila auditada en `notificaciones_envio`.
    Un fallo de un canal no afecta a los demás ni al alta del envío. Un intento
    ya enviado nunca se repite: reintentar solo despacha lo pendiente o fallido,
    y la reserva atómica del repositorio impide dos despachos simultáneos.
    """

    def __init__(
        self,
        email_provider: IEmailProvider,
        session_factory: Callable[[], Any] | None = None,
        repo_notificaciones: IRepositorioNotificaciones | None = None,
        whatsapp_provider: IWhatsAppProvider | None = None,
    ):
        self.email_provider = email_provider
        self.whatsapp_provider = whatsapp_provider
        self.session_factory = session_factory
        self.repo_notificaciones = repo_notificaciones

    @asynccontextmanager
    async def _repositorio(self) -> AsyncIterator[IRepositorioNotificaciones | None]:
        """Las tareas en segundo plano abren su propia sesión: la del request ya se cerró."""
        if self.session_factory:
            async with self.session_factory() as session:
                yield RepositorioNotificaciones(session)
        else:
            yield self.repo_notificaciones

    async def _textos_correo(self) -> tuple[dict[str, dict[str, str]], dict[str, str]]:
        """Plantillas editadas y datos de la empresa. Ante cualquier problema se
        usan los textos de fábrica: un aviso nunca deja de salir por esto."""
        if not self.session_factory:
            return {}, {}
        try:
            async with self.session_factory() as session:
                repo = RepositorioPlantillasCorreo(session)
                plantillas = {
                    clave: {campo: getattr(fila, campo) for campo in CAMPOS_PLANTILLA}
                    for clave, fila in (await repo.obtener_plantillas()).items()
                }
                fila = await repo.obtener_configuracion()
                configuracion = {campo: getattr(fila, campo) or "" for campo in CAMPOS_CONFIGURACION} if fila else {}
                return plantillas, configuracion
        except Exception:
            logger.exception("No se pudieron leer las plantillas de correo; se usan las de fábrica.")
            return {}, {}

    def _canal_habilitado(self, canal: str) -> bool:
        return canal == CanalNotificacionEnum.EMAIL.value or self.whatsapp_provider is not None

    # --- Aviso de visita fallida (HU12) ---

    async def notificar_visita_fallida(self, evento_id: uuid.UUID) -> None:
        """Despacha los avisos ya persistidos, sin deshacer la visita si falla un canal.

        Una repetición permite recuperar un aviso pendiente/fallido. La reserva
        atómica del repositorio impide dos despachos simultáneos del mismo aviso.
        """
        try:
            async with self._repositorio() as repo:
                if repo is None:
                    logger.warning("[ServicioNotificaciones] Sin repositorio para el aviso de visita %s.", evento_id)
                    return
                plantillas, configuracion = await self._textos_correo()
                for aviso in await repo.obtener_avisos_visita(evento_id):
                    if not self._canal_habilitado(aviso.canal) or not await repo.tomar_notificacion(aviso.id):
                        continue
                    evento, envio = aviso.evento_entrega, aviso.envio
                    enlace = armar_enlace_seguimiento(settings.FRONTEND_BASE_URL, envio.token_seguimiento)
                    numero = evento.paquete.numero_paquete
                    proximo_paso = await self._proximo_paso_visita(repo, evento.paquete)
                    contenido: MensajeEmail | MensajeWhatsApp
                    if aviso.canal == CanalNotificacionEnum.EMAIL.value:
                        contenido = armar_email_visita_fallida(
                            nombre=envio.destinatario_nombre,
                            numero_paquete=numero,
                            fecha_hora=_fecha_local(evento.created_at),
                            enlace=enlace,
                            token=envio.token_seguimiento,
                            proximo_paso=proximo_paso,
                            plantilla=plantillas.get(VISITA_FALLIDA),
                            configuracion=configuracion,
                        )
                    else:
                        contenido = armar_whatsapp_visita_fallida(
                            nombre=envio.destinatario_nombre, numero_paquete=numero, enlace=enlace
                        )
                    await self._enviar_y_finalizar(repo, aviso, contenido, "el aviso de visita")
        except Exception:
            logger.exception("No se pudo procesar el aviso de visita %s; la visita permanece registrada.", evento_id)

    async def _proximo_paso_visita(self, repo: IRepositorioNotificaciones, paquete: Any) -> str:
        maximo = settings.MAX_VISITAS_DOMICILIO
        if paquete.estado == EstadoPaqueteEnum.LISTO_PARA_RETIRO.value:
            sucursal = paquete.sucursal_actual
            lugar = f"{sucursal.nombre} ({sucursal.direccion})" if sucursal else "la sucursal"
            return (
                f"Ya hicimos las {maximo} visitas previstas: el paquete te espera en {lugar} "
                f"hasta el {_fecha_corta(paquete.retiro_hasta)}. Retiralo con tu DNI."
            )
        visitas = await repo.contar_visitas_fallidas(paquete.id)
        return (
            f"Vamos a intentarlo de nuevo en el próximo reparto (fue la {texto_visita(visitas, maximo)}). "
            "Si en la siguiente visita tampoco hay nadie, el paquete te va a esperar en la sucursal."
        )

    # --- Hitos del envío ---

    async def notificar_hito(self, paquete_id: uuid.UUID, tipo: str) -> None:
        """Avisa un hito del envío por email y WhatsApp.

        Se avisa por envío, no por bulto: si el mismo hito ya se avisó en las
        últimas horas (`VENTANA_AVISO_HITO`), no se repite.
        """
        try:
            async with self._repositorio() as repo:
                if repo is None:
                    return
                paquete = await repo.obtener_paquete_aviso(paquete_id)
                if paquete is None or tipo not in HITOS:
                    return
                envio = paquete.envio
                destinatarios = (REMITENTE,) if paquete.en_devolucion else HITOS[tipo]
                plantillas, configuracion = await self._textos_correo()
                valores = await self._valores_hito(repo, paquete, tipo)
                clave = self._clave_hito(tipo, paquete)
                desde = datetime.now(UTC) - VENTANA_AVISO_HITO
                existentes: dict[tuple[str, str], Any] = {}
                for previo in await repo.avisos_recientes_de_envio(envio.id, tipo, desde):
                    existentes.setdefault((previo.canal, previo.destinatario_tipo), previo)
                canales = [c.value for c in CanalNotificacionEnum if self._canal_habilitado(c.value)]
                for quien in destinatarios:
                    nombre = envio.remitente_nombre if quien == REMITENTE else envio.destinatario_nombre
                    email = envio.remitente_email if quien == REMITENTE else envio.destinatario_email
                    telefono = envio.remitente_telefono if quien == REMITENTE else envio.destinatario_telefono
                    for canal in canales:
                        aviso = existentes.get((canal, quien))
                        if aviso is not None and aviso.estado == EstadoNotificacionEnum.ENVIADO.value:
                            continue
                        if aviso is None:
                            destino = email if canal == CanalNotificacionEnum.EMAIL.value else _destino_whatsapp(telefono)
                            aviso = await repo.registrar_intento(
                                envio.id, canal, quien, destino or "", tipo_aviso=tipo, paquete_id=paquete.id
                            )
                        if not await repo.tomar_notificacion(aviso.id):
                            continue
                        datos = {**valores, "nombre": nombre}
                        contenido: MensajeEmail | MensajeWhatsApp
                        if canal == CanalNotificacionEnum.EMAIL.value:
                            contenido = armar_email_hito(
                                clave=clave, valores=datos, plantilla=plantillas.get(clave), configuracion=configuracion
                            )
                        else:
                            contenido = armar_whatsapp_hito(nombre=nombre, novedad=self._novedad(tipo, datos, paquete), enlace=datos["enlace"])
                        await self._enviar_y_finalizar(repo, aviso, contenido, "el aviso del envío")
        except Exception:
            logger.exception("No se pudo procesar el aviso %s del paquete %s.", tipo, paquete_id)

    @staticmethod
    def _clave_hito(tipo: str, paquete: Any) -> str:
        if tipo == TipoAvisoEnum.LISTO_PARA_RETIRO.value and paquete.en_devolucion:
            return DEVOLUCION_LISTA
        return {
            TipoAvisoEnum.ADMITIDO.value: ADMITIDO,
            TipoAvisoEnum.EN_REPARTO.value: EN_REPARTO,
            TipoAvisoEnum.LISTO_PARA_RETIRO.value: LISTO_PARA_RETIRO,
            TipoAvisoEnum.ENTREGADO.value: ENTREGADO,
            TipoAvisoEnum.DEVOLUCION.value: DEVOLUCION,
            TipoAvisoEnum.VENCIDO.value: VENCIDO,
        }[tipo]

    async def _valores_hito(self, repo: IRepositorioNotificaciones, paquete: Any, tipo: str) -> dict[str, str]:
        envio = paquete.envio
        sucursal = paquete.sucursal_actual
        if tipo == TipoAvisoEnum.DEVOLUCION.value and paquete.sucursal_origen_id:
            sucursal = await repo.obtener_sucursal(paquete.sucursal_origen_id) or sucursal
        valores = {
            "token": envio.token_seguimiento,
            "enlace": armar_enlace_seguimiento(settings.FRONTEND_BASE_URL, envio.token_seguimiento),
            "paquete": _paquetes_en_el_mismo_estado(paquete),
            "sucursal": sucursal.nombre if sucursal else "la sucursal",
            "direccion_sucursal": f"{sucursal.direccion}, {sucursal.ciudad}" if sucursal else "",
            "retiro_hasta": _fecha_corta(paquete.retiro_hasta),
            "plazo": f"{settings.VENCIMIENTO_PRE_REGISTRO_DIAS} días",
            "motivo": "tu paquete ya llegó a la sucursal que elegiste.",
        }
        if tipo == TipoAvisoEnum.EN_REPARTO.value:
            visitas = await repo.contar_visitas_fallidas(paquete.id)
            valores["visita"] = texto_visita(visitas + 1, settings.MAX_VISITAS_DOMICILIO)
        if tipo == TipoAvisoEnum.ENTREGADO.value:
            entrega = await repo.ultima_entrega(paquete.id)
            valores["fecha"] = _fecha_local(entrega.created_at) if entrega else ""
            valores["recibio"] = (entrega.receptor_nombre if entrega and entrega.receptor_nombre else "la persona indicada")
        return valores

    @staticmethod
    def _novedad(tipo: str, valores: dict[str, str], paquete: Any) -> str:
        """Una línea por hito para WhatsApp (sin saltos: Meta los rechaza en los parámetros)."""
        p = valores["paquete"]
        if tipo == TipoAvisoEnum.ADMITIDO.value:
            return f"recibimos tu paquete {p} en {valores['sucursal']}. Ya está en camino."
        if tipo == TipoAvisoEnum.EN_REPARTO.value:
            return f"tu paquete {p} sale hoy a reparto ({valores['visita']}). Tené a mano tu DNI."
        if tipo == TipoAvisoEnum.LISTO_PARA_RETIRO.value:
            quien = "el paquete devuelto" if paquete.en_devolucion else "tu paquete"
            return f"{quien} {p} te espera en {valores['sucursal']} hasta el {valores['retiro_hasta']}. Retiralo con tu DNI."
        if tipo == TipoAvisoEnum.ENTREGADO.value:
            return f"entregamos el paquete {p}. Lo recibió {valores.get('recibio', '')}."
        if tipo == TipoAvisoEnum.DEVOLUCION.value:
            return f"el paquete {p} no se retiró a tiempo y vuelve a {valores['sucursal']}. Te avisamos cuando puedas retirarlo."
        return f"venció el registro del envío {valores['token']} porque el paquete no llegó a una sucursal."

    # --- Token de seguimiento (HU05) ---

    async def notificar_nuevo_envio(self, datos: DatosNotificacionEnvio) -> list[Any]:
        """Comparte el token por email y WhatsApp con remitente y destinatario, auditando cada intento."""
        logger.info(f"[ServicioNotificaciones] Notificaciones del envío {datos.envio_id} ({datos.token_seguimiento})")
        enlace = armar_enlace_seguimiento(settings.FRONTEND_BASE_URL, datos.token_seguimiento)
        partes = [
            (DestinatarioNotificacionEnum.REMITENTE.value, datos.remitente_nombre, datos.remitente_email,
             datos.remitente_telefono),
            (DestinatarioNotificacionEnum.DESTINATARIO.value, datos.destinatario_nombre, datos.destinatario_email,
             datos.destinatario_telefono),
        ]
        canales = [c.value for c in CanalNotificacionEnum if self._canal_habilitado(c.value)]

        try:
            async with self._repositorio() as repo:
                if repo is None:
                    logger.warning("[ServicioNotificaciones] Sin repositorio ni session_factory para auditar.")
                    return []
                plantillas, configuracion = await self._textos_correo()
                existentes = {
                    (n.canal, n.destinatario_tipo): n
                    for n in await repo.obtener_por_envio_id(datos.envio_id)
                    if n.evento_entrega_id is None and n.tipo_aviso in (None, TipoAvisoEnum.NUEVO_ENVIO.value)
                }
                for tipo, nombre, email, telefono in partes:
                    for canal in canales:
                        notificacion = existentes.get((canal, tipo))
                        if notificacion is not None and notificacion.estado == EstadoNotificacionEnum.ENVIADO.value:
                            continue
                        if notificacion is None:
                            destino = email if canal == CanalNotificacionEnum.EMAIL.value else _destino_whatsapp(telefono)
                            notificacion = await repo.registrar_intento(datos.envio_id, canal, tipo, destino or "")
                        if not await repo.tomar_notificacion(notificacion.id):
                            continue
                        contenido: MensajeEmail | MensajeWhatsApp
                        if canal == CanalNotificacionEnum.EMAIL.value:
                            es_remitente = tipo == DestinatarioNotificacionEnum.REMITENTE.value
                            contenido = armar_email_nuevo_envio(
                                es_remitente=es_remitente,
                                nombre=nombre,
                                remitente_nombre=datos.remitente_nombre,
                                destinatario_nombre=datos.destinatario_nombre,
                                token=datos.token_seguimiento,
                                numeros_paquetes=datos.numeros_paquetes,
                                enlace=enlace,
                                plazo=f"{settings.VENCIMIENTO_PRE_REGISTRO_DIAS} días",
                                plantilla=plantillas.get(NUEVO_ENVIO_REMITENTE if es_remitente else NUEVO_ENVIO_DESTINATARIO),
                                configuracion=configuracion,
                            )
                        else:
                            contenido = armar_whatsapp_nuevo_envio(
                                nombre=nombre, token=datos.token_seguimiento, enlace=enlace
                            )
                        await self._enviar_y_finalizar(repo, notificacion, contenido, "el token de seguimiento")
                return await repo.obtener_por_envio_id(datos.envio_id)
        except Exception:
            logger.exception("No se pudieron procesar las notificaciones del envío %s.", datos.envio_id)
            return []

    async def _enviar_y_finalizar(
        self,
        repo: IRepositorioNotificaciones,
        notificacion: Any,
        contenido: MensajeEmail | MensajeWhatsApp,
        descripcion: str,
    ) -> None:
        """Despacha por el canal de la fila reservada y registra el resultado, aun si el proveedor falla."""
        canal = notificacion.canal
        exito, mensaje_id, error = False, None, None
        try:
            if canal == CanalNotificacionEnum.EMAIL.value and isinstance(contenido, MensajeEmail):
                if not notificacion.destino:
                    error = "El destinatario no tiene un email registrado."
                else:
                    exito, mensaje_id, error = await self.email_provider.enviar_email(
                        destinatario=notificacion.destino,
                        asunto=contenido.asunto,
                        cuerpo_texto=contenido.texto,
                        cuerpo_html=contenido.html,
                    )
            elif self.whatsapp_provider is not None and isinstance(contenido, MensajeWhatsApp):
                numero = normalizar_telefono_whatsapp(notificacion.destino, settings.WHATSAPP_CODIGO_PAIS)
                if numero is None:
                    error = "El teléfono registrado no es un número válido para WhatsApp."
                else:
                    exito, mensaje_id, error = await self.whatsapp_provider.enviar_whatsapp(numero, contenido)
        except Exception:
            # No persistir excepciones del proveedor: pueden contener credenciales o URLs firmadas.
            exito, mensaje_id = False, None
            error = f"Falló el proveedor de {NOMBRE_CANAL.get(canal, canal)} al enviar {descripcion}."
            logger.warning("Falló el proveedor de %s para la notificación %s.", canal, notificacion.id)

        if not exito and not error:
            error = f"No se pudo enviar {descripcion} por {NOMBRE_CANAL.get(canal, canal)}."
        await repo.finalizar_notificacion(
            notificacion.id,
            EstadoNotificacionEnum.ENVIADO.value if exito else EstadoNotificacionEnum.FALLIDO.value,
            mensaje_id if exito else None,
            None if exito else (error or "")[:MAX_ERROR_DETALLE],
        )

    # --- Consulta y reintento para el personal ---

    async def _obtener_envio(self, repo: IRepositorioNotificaciones, token: str) -> Any:
        envio = await repo.obtener_envio_por_token(normalizar_token_seguimiento(token))
        if envio is None:
            raise NotFoundException(message="No existe un envío con ese código de seguimiento.")
        return envio

    async def listar_por_token(self, token: str, mensaje: str | None = None) -> NotificacionesEnvioResponse:
        async with self._repositorio() as repo:
            if repo is None:
                raise NotFoundException(message="No existe un envío con ese código de seguimiento.")
            envio = await self._obtener_envio(repo, token)
            filas = await repo.obtener_por_envio_id(envio.id)
            items = [
                NotificacionItemData(
                    id=fila.id,
                    motivo=fila.tipo_aviso or ("VISITA_FALLIDA" if fila.evento_entrega_id else "NUEVO_ENVIO"),
                    canal=fila.canal,
                    destinatario_tipo=fila.destinatario_tipo,
                    destino=fila.destino,
                    estado=fila.estado,
                    error_detalle=fila.error_detalle,
                    created_at=fila.created_at,
                    updated_at=fila.updated_at,
                )
                for fila in filas
            ]
            return NotificacionesEnvioResponse(
                message=mensaje,
                data=NotificacionesEnvioData(token_seguimiento=envio.token_seguimiento, notificaciones=items),
            )

    async def reintentar_por_token(self, token: str) -> NotificacionesEnvioResponse:
        """Vuelve a despachar solo los intentos pendientes o fallidos del envío."""
        async with self._repositorio() as repo:
            if repo is None:
                raise NotFoundException(message="No existe un envío con ese código de seguimiento.")
            envio = await self._obtener_envio(repo, token)
            datos = DatosNotificacionEnvio(
                envio_id=envio.id,
                token_seguimiento=envio.token_seguimiento,
                remitente_nombre=envio.remitente_nombre,
                remitente_email=envio.remitente_email,
                remitente_telefono=envio.remitente_telefono,
                destinatario_nombre=envio.destinatario_nombre,
                destinatario_email=envio.destinatario_email,
                destinatario_telefono=envio.destinatario_telefono,
                numeros_paquetes=[p.numero_paquete for p in envio.paquetes],
            )
            filas = await repo.obtener_por_envio_id(envio.id)
            eventos_pendientes = {
                fila.evento_entrega_id
                for fila in filas
                if fila.evento_entrega_id and fila.estado != EstadoNotificacionEnum.ENVIADO.value
            }
            hitos_pendientes = {
                (fila.paquete_id, fila.tipo_aviso)
                for fila in filas
                if fila.tipo_aviso in HITOS and fila.paquete_id and fila.estado != EstadoNotificacionEnum.ENVIADO.value
            }
        await self.notificar_nuevo_envio(datos)
        for evento_id in eventos_pendientes:
            await self.notificar_visita_fallida(evento_id)
        for paquete_id, tipo in hitos_pendientes:
            await self.notificar_hito(paquete_id, tipo)
        return await self.listar_por_token(token, mensaje="Se reintentaron las notificaciones pendientes o fallidas.")
