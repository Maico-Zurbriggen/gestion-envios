"""Constantes de dominio para las tablas de logística/seguimiento planificadas
en Back/docs/01-arquitectura/plan-base-de-datos-completo.md (HU05-HU13).

Se definen acá para que el esquema de base de datos (CHECK constraints en
infrastructure/db/models.py), las reglas de dominio y los servicios tengan una
única fuente de verdad para los valores válidos, en vez de repetir los strings
sueltos en cada lugar. Las que ya se usan en código son las de HU05
(notificaciones), HU06 (recepción en terminal), HU07 (reclamos), HU09
(opciones de retiro), HU10 (recorridos) y HU13 (retiro en sucursal); el resto
quedan reservadas para HU11-HU12."""

from enum import StrEnum


class EstadoPaqueteEnum(StrEnum):
    """Máquina de estados de un paquete. Ver diagrama en el plan de base de
    datos. Transiciones implementadas hoy: PENDIENTE (HU03) ->
    EN_SUCURSAL_ORIGEN (HU06) -> EN_TRANSITO | EN_REPARTO (inicio de un
    recorrido de HU10) y -> ENTREGADO_EN_SUCURSAL (HU13)."""

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
    EN_DEVOLUCION = "EN_DEVOLUCION"
    """No se retiró a tiempo: espera viajar de vuelta a la sucursal de origen."""
    DEVUELTO = "DEVUELTO"
    """El remitente retiró el paquete devuelto."""
    VENCIDO = "VENCIDO"
    """Pre-registro que nunca se entregó en una sucursal dentro del plazo."""


class TipoRetiroEnum(StrEnum):
    """HU13: Modalidad de retiro en sucursal."""

    TITULAR = "TITULAR"
    TERCERO_AUTORIZADO = "TERCERO_AUTORIZADO"


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


class MotivoAlertaRecorridoEnum(StrEnum):
    """HU10 Escenario 3: por qué un paquete quedó fuera de todo recorrido.

    `alertas_recorrido.motivo` no tiene CHECK constraint (nació con un único
    valor por defecto), así que sumar un motivo nuevo no requiere migración.
    """

    SIN_RECORRIDO_ASIGNADO = "SIN_RECORRIDO_ASIGNADO"
    SIN_REPARTIDOR_DISPONIBLE = "SIN_REPARTIDOR_DISPONIBLE"
    SIN_UBICACION_DESTINO = "SIN_UBICACION_DESTINO"
    SIN_SUCURSAL_DESTINO = "SIN_SUCURSAL_DESTINO"
    FALTANTE_EN_DESCARGA = "FALTANTE_EN_DESCARGA"
    FALTANTE_EN_CARGA = "FALTANTE_EN_CARGA"
    """Estaba en el recorrido pero no se cargó en el vehículo: se quitó del recorrido."""
    """Tenía que bajar en la sucursal de destino y no apareció en el control de descarga."""


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


class TipoAvisoEnum(StrEnum):
    """Hitos del envío que se avisan al cliente por email y WhatsApp."""

    NUEVO_ENVIO = "NUEVO_ENVIO"
    ADMITIDO = "ADMITIDO"
    EN_REPARTO = "EN_REPARTO"
    LISTO_PARA_RETIRO = "LISTO_PARA_RETIRO"
    ENTREGADO = "ENTREGADO"
    VISITA_FALLIDA = "VISITA_FALLIDA"
    DEVOLUCION = "DEVOLUCION"
    VENCIDO = "VENCIDO"


class TipoControlEnum(StrEnum):
    """Escaneo de un recorrido al cargar el vehículo (origen) o al descargarlo (destino)."""

    CARGA = "CARGA"
    DESCARGA = "DESCARGA"
