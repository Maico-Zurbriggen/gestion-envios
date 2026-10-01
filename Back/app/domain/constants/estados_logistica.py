"""Constantes de dominio para las tablas de logística/seguimiento planificadas
en Back/docs/01-arquitectura/plan-base-de-datos-completo.md (HU05-HU13).

Ningún servicio las usa todavía (esas historias no están implementadas), pero
ya se definen acá para que el esquema de base de datos (CHECK constraints en
infrastructure/db/models.py) tenga una única fuente de verdad para los
valores válidos, en vez de repetir los strings sueltos en cada lugar."""

from enum import StrEnum


class EstadoPaqueteEnum(StrEnum):
    """Máquina de estados de un paquete. Ver diagrama en el plan de base de
    datos. Hoy (HU03/HU04) un paquete solo llega a PENDIENTE."""

    PENDIENTE = "PENDIENTE"
    EN_SUCURSAL_ORIGEN = "EN_SUCURSAL_ORIGEN"
    EN_TRANSITO = "EN_TRANSITO"
    EN_SUCURSAL_DESTINO = "EN_SUCURSAL_DESTINO"
    LISTO_PARA_RETIRO = "LISTO_PARA_RETIRO"
    EN_SUCURSAL = "EN_SUCURSAL"
    EN_REPARTO = "EN_REPARTO"
    ENTREGADO = "ENTREGADO"
    ENTREGA_FALLIDA = "ENTREGA_FALLIDA"
    RETIRADO = "RETIRADO"
    ENTREGADO_EN_SUCURSAL = "ENTREGADO_EN_SUCURSAL"


class TipoRetiroEnum(StrEnum):
    """HU13: Modalidad de retiro en sucursal."""

    TITULAR = "TITULAR"
    TERCERO_AUTORIZADO = "TERCERO_AUTORIZADO"


class TipoDocumentoEnum(StrEnum):
    """Tipos de documento válidos para verificación de identidad."""

    DNI = "DNI"
    PASAPORTE = "PASAPORTE"
    LC = "LC"
    LE = "LE"
    OTRO = "OTRO"


class TipoDistanciaEnum(StrEnum):
    """HU10 Escenario 4: corta distancia = misma ciudad; larga distancia =
    entre ciudades, dejando paquetes en sucursales."""

    CORTA = "CORTA"
    LARGA = "LARGA"


class CanalNotificacionEnum(StrEnum):
    """HU05: canales por los que se envía el token de seguimiento."""

    EMAIL = "EMAIL"
    WHATSAPP = "WHATSAPP"


class DestinatarioNotificacionEnum(StrEnum):
    REMITENTE = "REMITENTE"
    DESTINATARIO = "DESTINATARIO"


class EstadoNotificacionEnum(StrEnum):
    PENDIENTE = "PENDIENTE"
    ENVIADO = "ENVIADO"
    FALLIDO = "FALLIDO"


class TipoReclamoEnum(StrEnum):
    """HU07."""

    DEMORA = "DEMORA"
    DANIO = "DANIO"
    EXTRAVIO = "EXTRAVIO"
    OTRO = "OTRO"


class EstadoReclamoEnum(StrEnum):
    ABIERTO = "ABIERTO"
    EN_REVISION = "EN_REVISION"
    RESUELTO = "RESUELTO"
    RECHAZADO = "RECHAZADO"


class EstadoRecorridoEnum(StrEnum):
    """HU10."""

    GENERADO = "GENERADO"
    EN_EDICION = "EN_EDICION"
    EN_CURSO = "EN_CURSO"
    FINALIZADO = "FINALIZADO"


class EstadoRecorridoPaqueteEnum(StrEnum):
    PENDIENTE = "PENDIENTE"
    ENTREGADO = "ENTREGADO"
    FALLIDO = "FALLIDO"


class TipoEventoEntregaEnum(StrEnum):
    """HU12 (entrega a domicilio) y HU13 (retiro en sucursal), unificadas en
    la tabla eventos_entrega."""

    ENTREGA_DOMICILIO = "ENTREGA_DOMICILIO"
    RETIRO_SUCURSAL = "RETIRO_SUCURSAL"


class ResultadoEventoEntregaEnum(StrEnum):
    EXITOSO = "EXITOSO"
    FALLIDO = "FALLIDO"