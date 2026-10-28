"""Monitor de envíos: resumen operativo, listado filtrable y trazabilidad completa
de cada paquete para la administración."""

import csv
import io
import math
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.application.interfaces.repositorio_monitor import IRepositorioMonitor
from app.contracts.monitor import (
    ActividadHoyData,
    AsignacionTrazaData,
    EntregaTrazaData,
    EventoTrazaData,
    ListadoMonitorData,
    ListadoMonitorResponse,
    NotificacionTrazaData,
    PaqueteHermanoData,
    PaqueteMonitorData,
    PersonaData,
    ReclamoTrazaData,
    RecorridoAsignadoData,
    RecorridosHoyData,
    ResumenMonitorData,
    ResumenMonitorResponse,
    SucursalOpcionData,
    TrazaPaqueteData,
    TrazaPaqueteResponse,
)
from app.core.exceptions import NotFoundException, ValidationException
from app.domain.constants.estados_logistica import (
    EstadoRecorridoEnum,
    ResultadoEventoEntregaEnum,
    TipoEventoEntregaEnum,
)
from app.domain.rules.destino_rules import formatear_destino_domicilio, formatear_destino_sucursal
from app.domain.rules.monitor_rules import (
    ESTADOS_RECLAMO_EN_CURSO,
    FILTROS_ESPECIALES,
    GRUPOS_ESTADO,
    ZONA_HORARIA_LOCAL,
    como_utc,
    es_estado_duplicado_de_entrega,
    estados_de_grupo,
    etiqueta_estado,
    filtro_devolucion,
    grupo_de_estado,
    grupo_de_paquete,
    inicio_del_dia_local,
    ocultar_documento,
)

POR_PAGINA_MAX = 100
EXPORTACION_MAX = 5000

TIPOS_RECLAMO = {"DEMORA": "Demora", "DANIO": "Daño", "EXTRAVIO": "Extravío", "OTRO": "Otro"}
ESTADOS_RECLAMO = {"ABIERTO": "abierto", "EN_REVISION": "en revisión", "RESUELTO": "resuelto", "RECHAZADO": "rechazado"}
MOTIVOS_AVISO = {
    "NUEVO_ENVIO": "Código de seguimiento",
    "ADMITIDO": "Paquete recibido",
    "EN_REPARTO": "Sale a reparto",
    "VISITA_FALLIDA": "Aviso de visita fallida",
    "LISTO_PARA_RETIRO": "Listo para retirar",
    "ENTREGADO": "Paquete entregado",
    "DEVOLUCION": "Vuelve al remitente",
    "VENCIDO": "Registro vencido",
}

MOTIVOS_ALERTA = {
    "SIN_RECORRIDO_ASIGNADO": "Quedó fuera de los recorridos generados.",
    "SIN_REPARTIDOR_DISPONIBLE": "No había repartidores disponibles.",
    "SIN_UBICACION_DESTINO": "El domicilio no tiene ubicación en el mapa.",
    "SIN_SUCURSAL_DESTINO": "Falta la sucursal de destino.",
    "FALTANTE_EN_DESCARGA": "Tenía que bajar en la sucursal de destino y no apareció al controlar la descarga.",
    "FALTANTE_EN_CARGA": "Estaba en un recorrido pero no se cargó en el vehículo: se quitó del recorrido.",
}


def _nombre(usuario: Any) -> str | None:
    return getattr(usuario, "nombre", None) if usuario else None


def _destino(envio: Any) -> str:
    if envio.tipo_entrega == "sucursal":
        sucursal = envio.sucursal_destino
        return formatear_destino_sucursal(
            getattr(sucursal, "nombre", None), getattr(sucursal, "direccion", None),
            getattr(sucursal, "ciudad", None), getattr(sucursal, "provincia", None),
        )
    return formatear_destino_domicilio(envio.direccion_destino, envio.ciudad_destino, envio.provincia_destino)


def _recorrido(asignacion: Any) -> RecorridoAsignadoData | None:
    if asignacion is None:
        return None
    recorrido = asignacion.recorrido
    return RecorridoAsignadoData(
        id=recorrido.id,
        fecha=recorrido.fecha,
        estado=recorrido.estado,
        tipo_distancia=recorrido.tipo_distancia,
        repartidor_nombre=_nombre(recorrido.repartidor.usuario) or "Repartidor",
        orden=asignacion.orden,
        estado_en_recorrido=asignacion.estado_en_recorrido,
    )


def _paquete(paquete: Any, operativo: dict[str, Any]) -> PaqueteMonitorData:
    envio = paquete.envio
    return PaqueteMonitorData(
        id=paquete.id,
        numero_paquete=paquete.numero_paquete,
        estado=paquete.estado,
        estado_etiqueta=etiqueta_estado(paquete.estado),
        grupo=grupo_de_paquete(paquete.estado, bool(paquete.en_devolucion)),
        descripcion=paquete.descripcion,
        peso_kg=paquete.peso_kg,
        envio_id=envio.id,
        token_seguimiento=envio.token_seguimiento,
        remitente_nombre=envio.remitente_nombre,
        destinatario_nombre=envio.destinatario_nombre,
        tipo_entrega=envio.tipo_entrega,
        destino=_destino(envio),
        sucursal_actual=getattr(paquete.sucursal_actual, "nombre", None),
        recorrido=_recorrido(operativo.get("asignacion")),
        intentos_fallidos=operativo.get("fallidos", 0),
        reclamos_en_curso=operativo.get("reclamos", 0),
        sin_recorrido=operativo.get("alerta", False),
        faltante_en_descarga=operativo.get("faltante", False),
        en_devolucion=bool(getattr(paquete, "en_devolucion", False)),
        retiro_hasta=getattr(paquete, "retiro_hasta", None),
        created_at=paquete.created_at,
        updated_at=paquete.updated_at,
    )


class ServicioMonitor:
    def __init__(self, repositorio: IRepositorioMonitor):
        self.repo = repositorio

    # --- Resumen ------------------------------------------------------------

    async def resumen(self, ahora: datetime | None = None) -> ResumenMonitorResponse:
        ahora = ahora or datetime.now(UTC)
        por_estado = await self.repo.contar_por_estado()
        por_grupo = {grupo: sum(por_estado.get(e, 0) for e in estados) for grupo, estados in GRUPOS_ESTADO.items()}
        # Una devolución que espera en origen figura como devolución, no como «para retirar».
        en_espera = await self.repo.contar_devoluciones_en_espera()
        por_grupo["DEVOLUCIONES"] += en_espera
        por_grupo["PARA_RETIRAR"] -= en_espera
        especiales = await self.repo.contar_paquetes_especiales()
        actividad = await self.repo.actividad_desde(inicio_del_dia_local(ahora))
        recorridos = await self.repo.recorridos_por_estado(ahora.astimezone(ZONA_HORARIA_LOCAL).date())
        return ResumenMonitorResponse(data=ResumenMonitorData(
            total_paquetes=sum(por_estado.values()),
            total_envios=await self.repo.contar_envios(),
            por_grupo=por_grupo,
            por_estado=por_estado,
            sin_recorrido=especiales["SIN_RECORRIDO"],
            faltantes=especiales["FALTANTES"],
            con_reclamo=especiales["CON_RECLAMO"],
            con_problemas=especiales["CON_PROBLEMAS"],
            reclamos_abiertos=await self.repo.contar_reclamos_en_curso(),
            notificaciones_fallidas=await self.repo.contar_notificaciones_fallidas(),
            hoy=ActividadHoyData(**actividad),
            recorridos_hoy=RecorridosHoyData(
                total=sum(recorridos.values()),
                generados=recorridos.get(EstadoRecorridoEnum.GENERADO.value, 0)
                + recorridos.get(EstadoRecorridoEnum.EN_EDICION.value, 0),
                en_curso=recorridos.get(EstadoRecorridoEnum.EN_CURSO.value, 0),
                finalizados=recorridos.get(EstadoRecorridoEnum.FINALIZADO.value, 0),
                repartidores_en_ruta=await self.repo.contar_repartidores_en_ruta(),
            ),
            sucursales=[SucursalOpcionData(id=s.id, nombre=s.nombre) for s in await self.repo.listar_sucursales()],
            generado_at=ahora,
        ))

    # --- Listado ------------------------------------------------------------

    @staticmethod
    def _filtros(grupo: str | None, tipo_entrega: str | None, desde: datetime | None, hasta: datetime | None) -> dict:
        estados = None
        especial = None
        devolucion = None
        if grupo:
            clave = grupo.strip().upper()
            if clave in FILTROS_ESPECIALES:
                especial = clave
            elif estados_de_grupo(clave):
                estados = estados_de_grupo(clave)
                devolucion = filtro_devolucion(clave)
            elif clave != "TODOS":
                raise ValidationException(
                    message="El filtro de grupo no es válido.",
                    errors=[{"field": "grupo", "message": "Usá un grupo de estados o CON_PROBLEMAS, SIN_RECORRIDO, CON_RECLAMO o FALTANTES."}],
                )
        if tipo_entrega and tipo_entrega not in ("domicilio", "sucursal"):
            raise ValidationException(
                message="El tipo de entrega no es válido.",
                errors=[{"field": "tipo_entrega", "message": "Usá domicilio o sucursal."}],
            )
        if desde and hasta and desde >= hasta:
            raise ValidationException(
                message="El rango de fechas no es válido.",
                errors=[{"field": "hasta", "message": "La fecha final debe ser posterior a la inicial."}],
            )
        return {"estados": estados, "devolucion": devolucion, "especial": especial}

    async def listar(
        self,
        *,
        buscar: str | None = None,
        grupo: str | None = None,
        sucursal_id: int | None = None,
        tipo_entrega: str | None = None,
        desde: datetime | None = None,
        hasta: datetime | None = None,
        orden: str = "movimiento",
        pagina: int = 1,
        por_pagina: int = 25,
    ) -> ListadoMonitorResponse:
        por_pagina = max(1, min(por_pagina, POR_PAGINA_MAX))
        pagina = max(1, pagina)
        filtros = self._filtros(grupo, tipo_entrega, desde, hasta)
        paquetes, total = await self.repo.listar_paquetes(
            buscar=(buscar or "").strip() or None, sucursal_id=sucursal_id, tipo_entrega=tipo_entrega,
            desde=desde, hasta=hasta, orden=orden, offset=(pagina - 1) * por_pagina, limite=por_pagina, **filtros,
        )
        operativos = await self.repo.datos_operativos(paquetes)
        return ListadoMonitorResponse(data=ListadoMonitorData(
            paquetes=[_paquete(p, operativos[p.id]) for p in paquetes],
            total=total,
            pagina=pagina,
            por_pagina=por_pagina,
            paginas=max(1, math.ceil(total / por_pagina)),
        ))

    async def exportar_csv(self, **filtros: Any) -> str:
        """Mismo filtro que el listado, hasta 5000 paquetes, en CSV separado por `;` (Excel en español)."""
        datos = (await self.listar(**filtros, pagina=1, por_pagina=POR_PAGINA_MAX)).data
        filas = list(datos.paquetes)
        pagina = 2
        while len(filas) < min(datos.total, EXPORTACION_MAX) and pagina <= datos.paginas:
            filas += (await self.listar(**filtros, pagina=pagina, por_pagina=POR_PAGINA_MAX)).data.paquetes
            pagina += 1
        salida = io.StringIO()
        escritor = csv.writer(salida, delimiter=";")
        escritor.writerow([
            "Paquete", "Código de seguimiento", "Estado", "Descripción", "Peso (kg)", "Remitente", "Destinatario",
            "Entrega", "Destino", "Ubicación actual", "Recorrido", "Repartidor", "Visitas fallidas",
            "Reclamos en curso", "Sin recorrido", "Registrado", "Último movimiento",
        ])
        for p in filas[:EXPORTACION_MAX]:
            escritor.writerow([
                p.numero_paquete, p.token_seguimiento, p.estado_etiqueta, p.descripcion, f"{p.peso_kg:g}".replace(".", ","),
                p.remitente_nombre, p.destinatario_nombre, "Domicilio" if p.tipo_entrega == "domicilio" else "Sucursal",
                p.destino, p.sucursal_actual or "", p.recorrido.fecha.strftime("%d/%m/%Y") if p.recorrido else "",
                p.recorrido.repartidor_nombre if p.recorrido else "", p.intentos_fallidos, p.reclamos_en_curso,
                "Sí" if p.sin_recorrido else "No", _local(p.created_at), _local(p.updated_at),
            ])
        return "﻿" + salida.getvalue()

    # --- Trazabilidad -------------------------------------------------------

    async def trazabilidad(self, numero_paquete: str) -> TrazaPaqueteResponse:
        paquete = await self.repo.obtener_paquete(numero_paquete)
        if paquete is None:
            raise NotFoundException("No encontramos un paquete con ese número.")
        envio = paquete.envio
        operativo = (await self.repo.datos_operativos([paquete]))[paquete.id]
        historial = await self.repo.historial(paquete.id)
        eventos = await self.repo.eventos_entrega(paquete.id)
        asignaciones = await self.repo.asignaciones(paquete.id)
        alertas = await self.repo.alertas(paquete.id)
        reclamos = [
            r for r in await self.repo.reclamos_del_envio(envio.id) if r.paquete_id in (None, paquete.id)
        ]
        notificaciones = await self.repo.notificaciones_del_envio(envio.id)
        lecturas = await self.repo.lecturas_descarga(paquete.id)
        hermanos = await self.repo.paquetes_del_envio(envio.id)

        entregas = [
            EntregaTrazaData(
                id=evento.id,
                fecha=evento.created_at,
                tipo_evento=evento.tipo_evento,
                resultado=evento.resultado,
                receptor_nombre=evento.receptor_nombre,
                receptor_documento=ocultar_documento(evento.receptor_documento),
                es_autorizado=evento.es_autorizado,
                motivo_fallo=evento.motivo_fallo,
                con_firma=con_firma,
                registrado_por=_nombre(evento.usuario_registro),
                sucursal=getattr(evento.sucursal, "nombre", None),
                latitud=evento.latitud,
                longitud=evento.longitud,
            )
            for evento, con_firma in eventos
        ]
        traza = TrazaPaqueteData(
            paquete=_paquete(paquete, operativo),
            observaciones=paquete.observaciones,
            peso_admision_kg=paquete.peso_admision_kg,
            sucursal_origen=getattr(paquete.sucursal_origen, "nombre", None),
            largo_cm=paquete.largo_cm,
            ancho_cm=paquete.ancho_cm,
            alto_cm=paquete.alto_cm,
            remitente=PersonaData(
                nombre=envio.remitente_nombre, documento=envio.remitente_documento,
                telefono=envio.remitente_telefono, email=envio.remitente_email,
            ),
            destinatario=PersonaData(
                nombre=envio.destinatario_nombre, telefono=envio.destinatario_telefono, email=envio.destinatario_email,
            ),
            sucursal_destino=getattr(envio.sucursal_destino, "nombre", None),
            direccion_destino=_destino(envio),
            latitud_destino=envio.latitud_destino if envio.tipo_entrega == "domicilio" else getattr(envio.sucursal_destino, "latitud", None),
            longitud_destino=envio.longitud_destino if envio.tipo_entrega == "domicilio" else getattr(envio.sucursal_destino, "longitud", None),
            paquetes_del_envio=[
                PaqueteHermanoData(
                    numero_paquete=h.numero_paquete, estado=h.estado,
                    estado_etiqueta=etiqueta_estado(h.estado), grupo=grupo_de_estado(h.estado),
                )
                for h in hermanos
            ],
            asignaciones=[
                AsignacionTrazaData(
                    **_recorrido(a).model_dump(),
                    sucursal_origen=getattr(a.recorrido.sucursal_origen, "nombre", ""),
                    asignado_at=a.created_at,
                )
                for a in asignaciones
            ],
            entregas=entregas,
            reclamos=[
                ReclamoTrazaData(
                    id=r.id, tipo=r.tipo, estado=r.estado, descripcion=r.descripcion, resolucion=r.resolucion,
                    contacto_nombre=r.contacto_nombre, numero_paquete=getattr(r.paquete, "numero_paquete", None),
                    created_at=r.created_at, updated_at=r.updated_at,
                )
                for r in reclamos
            ],
            notificaciones=[
                NotificacionTrazaData(
                    canal=n.canal, destinatario_tipo=n.destinatario_tipo, destino=n.destino, estado=n.estado,
                    motivo=MOTIVOS_AVISO.get(n.tipo_aviso or "", "Aviso de visita fallida" if n.evento_entrega_id else "Código de seguimiento"),
                    created_at=n.created_at, updated_at=n.updated_at,
                )
                for n in notificaciones
            ],
            linea_de_tiempo=self._linea_de_tiempo(envio, historial, entregas, asignaciones, alertas, reclamos, notificaciones, lecturas),
        )
        return TrazaPaqueteResponse(data=traza)

    @staticmethod
    def _linea_de_tiempo(
        envio, historial, entregas, asignaciones, alertas, reclamos, notificaciones, lecturas
    ) -> list[EventoTrazaData]:
        eventos: list[EventoTrazaData] = [
            EventoTrazaData(
                fecha=envio.created_at, tipo="registro", titulo="Envío registrado",
                detalle=f"Código de seguimiento {envio.token_seguimiento}.", actor=envio.remitente_nombre, tono="info",
            )
        ]
        momentos_entrega = [e.fecha for e in entregas]
        for h in historial:
            if es_estado_duplicado_de_entrega(h.estado_nuevo, h.created_at, momentos_entrega):
                continue
            eventos.append(EventoTrazaData(
                fecha=h.created_at, tipo="estado", titulo=etiqueta_estado(h.estado_nuevo),
                detalle=h.observacion or (f"Antes: {etiqueta_estado(h.estado_anterior)}." if h.estado_anterior else None),
                actor=_nombre(h.usuario) or "Sistema", lugar=getattr(h.sucursal, "nombre", None),
                tono="success" if grupo_de_estado(h.estado_nuevo) == "ENTREGADOS" else "brand",
                latitud=h.latitud, longitud=h.longitud,
            ))
        for a in asignaciones:
            recorrido = a.recorrido
            eventos.append(EventoTrazaData(
                fecha=a.created_at, tipo="recorrido",
                titulo=f"Asignado a un recorrido de {'corta' if recorrido.tipo_distancia == 'CORTA' else 'larga'} distancia",
                detalle=f"Parada {a.orden} del recorrido del {recorrido.fecha.strftime('%d/%m/%Y')}.",
                actor=_nombre(recorrido.repartidor.usuario), lugar=getattr(recorrido.sucursal_origen, "nombre", None),
                tono="info",
            ))
        for e in entregas:
            exitoso = e.resultado == ResultadoEventoEntregaEnum.EXITOSO.value
            retiro = e.tipo_evento == TipoEventoEntregaEnum.RETIRO_SUCURSAL.value
            if exitoso:
                titulo = "Retirado en sucursal" if retiro else "Entregado a domicilio"
                detalle = f"Recibió {e.receptor_nombre or 'sin nombre'}" + (" (persona autorizada)" if e.es_autorizado else "") + "."
            else:
                titulo = "Visita fallida"
                detalle = e.motivo_fallo or "No se pudo concretar la entrega."
            eventos.append(EventoTrazaData(
                fecha=e.fecha, tipo="entrega", titulo=titulo, detalle=detalle, actor=e.registrado_por, lugar=e.sucursal,
                tono="success" if exitoso else "danger", latitud=e.latitud, longitud=e.longitud,
                evento_entrega_id=e.id, con_firma=e.con_firma,
            ))
        for lectura in lecturas:
            correcto = lectura.resultado == "CORRECTO"
            eventos.append(EventoTrazaData(
                fecha=lectura.created_at, tipo="descarga",
                titulo="Verificado en la descarga" if correcto else "Leído de más en una descarga",
                detalle=lectura.detalle, actor=_nombre(lectura.usuario),
                lugar=getattr(lectura.control.sucursal, "nombre", None), tono="success" if correcto else "warning",
            ))
        for alerta in alertas:
            faltante = alerta.motivo == "FALTANTE_EN_DESCARGA"
            eventos.append(EventoTrazaData(
                fecha=alerta.created_at, tipo="alerta",
                titulo="Alerta: faltante en la descarga" if faltante else "Alerta: sin recorrido",
                detalle=MOTIVOS_ALERTA.get(alerta.motivo, alerta.motivo), tono="danger" if faltante else "warning",
            ))
            if alerta.resuelta and alerta.resuelta_at:
                eventos.append(EventoTrazaData(
                    fecha=alerta.resuelta_at, tipo="alerta", titulo="Alerta resuelta", tono="success",
                ))
        for r in reclamos:
            eventos.append(EventoTrazaData(
                fecha=r.created_at, tipo="reclamo", titulo=f"Reclamo por {TIPOS_RECLAMO.get(r.tipo, r.tipo).lower()}",
                detalle=r.descripcion, actor=r.contacto_nombre, tono="warning",
            ))
            if r.estado not in ESTADOS_RECLAMO_EN_CURSO or r.estado == "EN_REVISION":
                eventos.append(EventoTrazaData(
                    fecha=r.updated_at, tipo="reclamo", titulo=f"Reclamo {ESTADOS_RECLAMO.get(r.estado, r.estado)}",
                    detalle=r.resolucion, actor=_nombre(r.usuario_resolucion),
                    tono="success" if r.estado == "RESUELTO" else "neutral",
                ))
        for n in notificaciones:
            canal = "Email" if n.canal == "EMAIL" else "WhatsApp"
            quien = "remitente" if n.destinatario_tipo == "REMITENTE" else "destinatario"
            motivo = MOTIVOS_AVISO.get(
                n.tipo_aviso or "", "Aviso de visita fallida" if n.evento_entrega_id else "Código de seguimiento"
            ).lower()
            estado = {"ENVIADO": "enviado", "FALLIDO": "falló", "PENDIENTE": "pendiente"}.get(n.estado, n.estado.lower())
            eventos.append(EventoTrazaData(
                fecha=n.updated_at or n.created_at, tipo="notificacion",
                titulo=f"{canal} al {quien}: {estado}", detalle=f"{motivo.capitalize()} a {n.destino}.",
                tono="danger" if n.estado == "FALLIDO" else "neutral",
            ))
        eventos.sort(key=lambda e: como_utc(e.fecha))
        return eventos

    async def firma(self, evento_id: UUID) -> tuple[bytes, str]:
        firma = await self.repo.obtener_firma(evento_id)
        if firma is None:
            raise NotFoundException("Esa entrega no tiene una firma registrada.")
        return firma


def _local(momento: datetime) -> str:
    return como_utc(momento).astimezone(ZONA_HORARIA_LOCAL).strftime("%d/%m/%Y %H:%M")
