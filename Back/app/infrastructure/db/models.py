import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    func,
    types,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.domain.constants.estados_logistica import (
    CanalNotificacionEnum,
    DestinatarioNotificacionEnum,
    EstadoNotificacionEnum,
    EstadoReclamoEnum,
    EstadoRecorridoEnum,
    EstadoRecorridoPaqueteEnum,
    ResultadoEventoEntregaEnum,
    TipoDistanciaEnum,
    TipoEventoEntregaEnum,
    TipoReclamoEnum,
)


def _lista_sql(enum_cls) -> str:
    """Arma un `IN (...)` de SQL a partir de un StrEnum, para no repetir los
    valores válidos como strings sueltos en cada CheckConstraint."""
    valores = ", ".join(f"'{miembro.value}'" for miembro in enum_cls)
    return f"({valores})"


class Base(DeclarativeBase):
    pass


class RolModel(Base):
    """Catálogo fijo de 4 roles (SUPERADMIN, ADMINISTRATIVO, VENDEDOR,
    REPARTIDOR), sembrado una única vez al iniciar la app. No tiene
    endpoint de alta/edición: los IDs están fijados en
    `domain/constants/roles.py:RolIdEnum`."""

    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    usuarios: Mapped[list["UsuarioModel"]] = relationship(
        "UsuarioModel",
        back_populates="rol",
        cascade="all, delete-orphan",
    )


class UsuarioModel(Base):
    """Empleado o Superadministrador del sistema (HU01/HU02). `dni` y
    `email` son únicos (base de la validación de duplicados de HU01
    Escenario 4). `requiere_cambio_password` nace en True para todo alta
    por `POST /admin/empleados`, y en False para el Superadmin sembrado."""

    __tablename__ = "usuarios"

    id: Mapped[uuid.UUID] = mapped_column(
        types.Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    dni: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)
    telefono: Mapped[str] = mapped_column(String(30), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="Activo")
    requiere_cambio_password: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    rol_id: Mapped[int] = mapped_column(Integer, ForeignKey("roles.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    rol: Mapped["RolModel"] = relationship("RolModel", back_populates="usuarios", lazy="joined")
    repartidor: Mapped[Optional["RepartidorModel"]] = relationship(
        "RepartidorModel",
        back_populates="usuario",
        uselist=False,
        cascade="all, delete-orphan",
    )


class SucursalModel(Base):
    """Catálogo público de sucursales para retiro (soporte de HU03/HU09).
    Se siembra al iniciar la app; no tiene endpoint de alta."""

    __tablename__ = "sucursales"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    provincia: Mapped[str] = mapped_column(String(100), nullable=False)
    ciudad: Mapped[str] = mapped_column(String(100), nullable=False)
    direccion: Mapped[str] = mapped_column(String(255), nullable=False)
    latitud: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitud: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    envios: Mapped[list["EnvioModel"]] = relationship(
        "EnvioModel",
        back_populates="sucursal_destino",
    )
    paquetes_ubicados_aqui: Mapped[list["PaqueteModel"]] = relationship(
        "PaqueteModel",
        back_populates="sucursal_actual",
        foreign_keys="[PaqueteModel.sucursal_actual_id]",
    )
    repartidores: Mapped[list["RepartidorModel"]] = relationship(
        "RepartidorModel", back_populates="sucursal_base"
    )
    recorridos: Mapped[list["RecorridoModel"]] = relationship(
        "RecorridoModel", back_populates="sucursal_origen"
    )


class EnvioModel(Base):
    """Registro público de un envío (HU03). `token_seguimiento` vive acá,
    no en `PaqueteModel`: un mismo token siempre corresponde a todos los
    paquetes de un mismo envío (HU04 Escenario 2)."""

    __tablename__ = "envios"

    id: Mapped[uuid.UUID] = mapped_column(
        types.Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Remitente
    remitente_nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    remitente_documento: Mapped[str] = mapped_column(String(20), nullable=False)
    remitente_telefono: Mapped[str] = mapped_column(String(30), nullable=False)
    remitente_email: Mapped[str] = mapped_column(String(150), nullable=False)

    # Destinatario
    destinatario_nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    destinatario_telefono: Mapped[str] = mapped_column(String(30), nullable=False)
    destinatario_email: Mapped[str] = mapped_column(String(150), nullable=False)

    # Entrega: "domicilio" o "sucursal" — exactamente uno de los dos bloques de campos aplica
    tipo_entrega: Mapped[str] = mapped_column(String(20), nullable=False)

    provincia_destino: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ciudad_destino: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    direccion_destino: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    latitud_destino: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitud_destino: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    sucursal_destino_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("sucursales.id"), nullable=True
    )

    terminos_aceptados: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    token_seguimiento: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        nullable=False,
    )

    sucursal_destino: Mapped[Optional["SucursalModel"]] = relationship(
        "SucursalModel", back_populates="envios", lazy="joined"
    )
    paquetes: Mapped[list["PaqueteModel"]] = relationship(
        "PaqueteModel",
        back_populates="envio",
        cascade="all, delete-orphan",
    )
    notificaciones: Mapped[list["NotificacionEnvioModel"]] = relationship(
        "NotificacionEnvioModel", back_populates="envio", cascade="all, delete-orphan"
    )
    reclamos: Mapped[list["ReclamoModel"]] = relationship(
        "ReclamoModel", back_populates="envio", cascade="all, delete-orphan"
    )


class PaqueteModel(Base):
    """Un paquete dentro de un envío (HU03). `numero_paquete` es el valor
    pensado para el código de barras de la planilla imprimible. `estado`
    solo toma el valor "Pendiente" en esta etapa del proyecto; las
    transiciones (en tránsito, entregado, etc.) llegan con HU06/HU10-HU13."""

    __tablename__ = "paquetes"

    id: Mapped[uuid.UUID] = mapped_column(
        types.Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    envio_id: Mapped[uuid.UUID] = mapped_column(
        types.Uuid(as_uuid=True), ForeignKey("envios.id"), nullable=False
    )

    numero_paquete: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)

    descripcion: Mapped[str] = mapped_column(String(255), nullable=False)
    peso_kg: Mapped[float] = mapped_column(Float, nullable=False)
    largo_cm: Mapped[float] = mapped_column(Float, nullable=False)
    ancho_cm: Mapped[float] = mapped_column(Float, nullable=False)
    alto_cm: Mapped[float] = mapped_column(Float, nullable=False)
    observaciones: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    estado: Mapped[str] = mapped_column(String(30), nullable=False, default="Pendiente")

    sucursal_actual_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("sucursales.id"), nullable=True
    )
    """Dónde está físicamente el paquete ahora mismo. `None` hasta que HU06
    lo escanea por primera vez en una terminal. Se actualiza junto con cada
    fila nueva de `historial_estados_paquete`, no reemplaza ese historial:
    esto es solo para que la consulta pública de HU04 no necesite un JOIN."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    envio: Mapped["EnvioModel"] = relationship("EnvioModel", back_populates="paquetes", lazy="joined")
    sucursal_actual: Mapped[Optional["SucursalModel"]] = relationship(
        "SucursalModel",
        back_populates="paquetes_ubicados_aqui",
        foreign_keys=[sucursal_actual_id],
    )
    historial_estados: Mapped[list["HistorialEstadoPaqueteModel"]] = relationship(
        "HistorialEstadoPaqueteModel", back_populates="paquete", cascade="all, delete-orphan"
    )
    reclamos: Mapped[list["ReclamoModel"]] = relationship("ReclamoModel", back_populates="paquete")
    recorrido_asignaciones: Mapped[list["RecorridoPaqueteModel"]] = relationship(
        "RecorridoPaqueteModel", back_populates="paquete"
    )
    alertas: Mapped[list["AlertaRecorridoModel"]] = relationship(
        "AlertaRecorridoModel", back_populates="paquete", cascade="all, delete-orphan"
    )
    eventos_entrega: Mapped[list["EventoEntregaModel"]] = relationship(
        "EventoEntregaModel", back_populates="paquete", cascade="all, delete-orphan"
    )


class RepartidorModel(Base):
    """Extensión 1 a 1 de `UsuarioModel` para el rol REPARTIDOR (soporte de
    HU10/HU11/HU12). Separada de `usuarios` para no llenar esa tabla de
    columnas que no aplican a los demás roles."""

    __tablename__ = "repartidores"
    __table_args__ = (
        CheckConstraint(
            f"tipo_reparto IN {_lista_sql(TipoDistanciaEnum)}",
            name="ck_repartidores_tipo_reparto",
        ),
    )

    usuario_id: Mapped[uuid.UUID] = mapped_column(
        types.Uuid(as_uuid=True), ForeignKey("usuarios.id"), primary_key=True
    )
    sucursal_base_id: Mapped[int] = mapped_column(Integer, ForeignKey("sucursales.id"), nullable=False)
    tipo_reparto: Mapped[str] = mapped_column(String(10), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False
    )

    usuario: Mapped["UsuarioModel"] = relationship("UsuarioModel", back_populates="repartidor")
    sucursal_base: Mapped["SucursalModel"] = relationship("SucursalModel", back_populates="repartidores")
    recorridos: Mapped[list["RecorridoModel"]] = relationship("RecorridoModel", back_populates="repartidor")
    posicion_actual: Mapped[Optional["PosicionActualRepartidorModel"]] = relationship(
        "PosicionActualRepartidorModel", back_populates="repartidor", uselist=False, cascade="all, delete-orphan"
    )


class HistorialEstadoPaqueteModel(Base):
    """Auditoría append-only de cada cambio de estado de un paquete (soporta
    HU04 Escenarios 5/6, HU06, HU10-HU13). `paquetes.estado` (y
    `sucursal_actual_id`) se actualizan junto con cada fila nueva acá — esta
    tabla es para trazabilidad y reportes, no reemplaza esos campos
    denormalizados en la lectura pública de HU04."""

    __tablename__ = "historial_estados_paquete"
    __table_args__ = (
        Index("idx_historial_estados_paquete_id", "paquete_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    paquete_id: Mapped[uuid.UUID] = mapped_column(types.Uuid(as_uuid=True), ForeignKey("paquetes.id"), nullable=False)
    estado_anterior: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    estado_nuevo: Mapped[str] = mapped_column(String(30), nullable=False)
    usuario_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        types.Uuid(as_uuid=True), ForeignKey("usuarios.id"), nullable=True
    )
    """`None` cuando el cambio lo genera el sistema (ej. proximidad automática
    de HU11 Escenario 3); con valor cuando lo genera una persona."""
    sucursal_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("sucursales.id"), nullable=True)
    latitud: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitud: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    observacion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False)

    paquete: Mapped["PaqueteModel"] = relationship("PaqueteModel", back_populates="historial_estados")
    usuario: Mapped[Optional["UsuarioModel"]] = relationship("UsuarioModel")
    sucursal: Mapped[Optional["SucursalModel"]] = relationship("SucursalModel")


class NotificacionEnvioModel(Base):
    """Registro de cada intento de envío del token de seguimiento por email o
    WhatsApp (HU05). Un envío exitoso de HU03 genera hasta 4 filas acá
    (email+WhatsApp × remitente+destinatario), para poder reintentar solo el
    canal que falló y auditar si el token realmente llegó."""

    __tablename__ = "notificaciones_envio"
    __table_args__ = (
        CheckConstraint(f"canal IN {_lista_sql(CanalNotificacionEnum)}", name="ck_notificaciones_envio_canal"),
        CheckConstraint(
            f"destinatario_tipo IN {_lista_sql(DestinatarioNotificacionEnum)}",
            name="ck_notificaciones_envio_destinatario_tipo",
        ),
        CheckConstraint(f"estado IN {_lista_sql(EstadoNotificacionEnum)}", name="ck_notificaciones_envio_estado"),
    )

    id: Mapped[uuid.UUID] = mapped_column(types.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    envio_id: Mapped[uuid.UUID] = mapped_column(
        types.Uuid(as_uuid=True), ForeignKey("envios.id"), nullable=False, index=True
    )
    canal: Mapped[str] = mapped_column(String(10), nullable=False)
    destinatario_tipo: Mapped[str] = mapped_column(String(15), nullable=False)
    destino: Mapped[str] = mapped_column(String(150), nullable=False)
    estado: Mapped[str] = mapped_column(String(15), nullable=False, default=EstadoNotificacionEnum.PENDIENTE.value)
    proveedor_mensaje_id: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    """ID que devuelve el proveedor externo (ej. Twilio, SendGrid/SES), para
    poder rastrear un envío puntual sin acoplar el esquema a un proveedor."""
    error_detalle: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False
    )

    envio: Mapped["EnvioModel"] = relationship("EnvioModel", back_populates="notificaciones")


class ReclamoModel(Base):
    """Reclamo iniciado desde la vista pública de seguimiento (HU07), sin
    autenticación — por eso los datos de contacto se cargan en el reclamo
    mismo en vez de exigir sesión."""

    __tablename__ = "reclamos"
    __table_args__ = (
        CheckConstraint(f"tipo IN {_lista_sql(TipoReclamoEnum)}", name="ck_reclamos_tipo"),
        CheckConstraint(f"estado IN {_lista_sql(EstadoReclamoEnum)}", name="ck_reclamos_estado"),
    )

    id: Mapped[uuid.UUID] = mapped_column(types.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    envio_id: Mapped[uuid.UUID] = mapped_column(
        types.Uuid(as_uuid=True), ForeignKey("envios.id"), nullable=False, index=True
    )
    paquete_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        types.Uuid(as_uuid=True), ForeignKey("paquetes.id"), nullable=True
    )
    """Opcional: el reclamo se inicia desde la vista de un envío, pero puede
    referirse a un paquete puntual si el envío tiene varios."""
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    contacto_nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    contacto_email: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    contacto_telefono: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    estado: Mapped[str] = mapped_column(String(15), nullable=False, default=EstadoReclamoEnum.ABIERTO.value)
    resolucion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    usuario_resolucion_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        types.Uuid(as_uuid=True), ForeignKey("usuarios.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False
    )

    envio: Mapped["EnvioModel"] = relationship("EnvioModel", back_populates="reclamos")
    paquete: Mapped[Optional["PaqueteModel"]] = relationship("PaqueteModel", back_populates="reclamos")
    usuario_resolucion: Mapped[Optional["UsuarioModel"]] = relationship("UsuarioModel")


class PreguntaFrecuenteModel(Base):
    """Contenido editable de la sección de preguntas frecuentes (HU08). Vive
    en base (no hardcodeado en el frontend) para que se pueda mantener sin
    un nuevo despliegue."""

    __tablename__ = "preguntas_frecuentes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    categoria: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    pregunta: Mapped[str] = mapped_column(String(255), nullable=False)
    respuesta: Mapped[str] = mapped_column(Text, nullable=False)
    orden: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    publicada: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False
    )


class RecorridoModel(Base):
    """Recorrido de reparto asignado a un repartidor (HU10). `tipo_distancia`
    decide si el recorrido es dentro de una ciudad (CORTA, entrega a
    domicilio) o entre ciudades (LARGA, deja paquetes en sucursales) —
    HU10 Escenario 4."""

    __tablename__ = "recorridos"
    __table_args__ = (
        CheckConstraint(f"tipo_distancia IN {_lista_sql(TipoDistanciaEnum)}", name="ck_recorridos_tipo_distancia"),
        CheckConstraint(f"estado IN {_lista_sql(EstadoRecorridoEnum)}", name="ck_recorridos_estado"),
    )

    id: Mapped[uuid.UUID] = mapped_column(types.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repartidor_id: Mapped[uuid.UUID] = mapped_column(
        types.Uuid(as_uuid=True), ForeignKey("repartidores.usuario_id"), nullable=False
    )
    sucursal_origen_id: Mapped[int] = mapped_column(Integer, ForeignKey("sucursales.id"), nullable=False)
    tipo_distancia: Mapped[str] = mapped_column(String(10), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    estado: Mapped[str] = mapped_column(String(15), nullable=False, default=EstadoRecorridoEnum.GENERADO.value)
    generado_automaticamente: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False
    )

    repartidor: Mapped["RepartidorModel"] = relationship("RepartidorModel", back_populates="recorridos")
    sucursal_origen: Mapped["SucursalModel"] = relationship("SucursalModel", back_populates="recorridos")
    paquetes: Mapped[list["RecorridoPaqueteModel"]] = relationship(
        "RecorridoPaqueteModel", back_populates="recorrido", cascade="all, delete-orphan"
    )
    alertas_generadas: Mapped[list["AlertaRecorridoModel"]] = relationship(
        "AlertaRecorridoModel", back_populates="recorrido"
    )
    posiciones_actuales: Mapped[list["PosicionActualRepartidorModel"]] = relationship(
        "PosicionActualRepartidorModel", back_populates="recorrido"
    )


class RecorridoPaqueteModel(Base):
    """Posición de un paquete dentro de un recorrido (HU10). No hay una
    tabla separada de "paradas": cada fila acá ya es la parada de ese
    paquete en la ruta (`orden`); para el mapa alcanza con hacer join contra
    el envío/sucursal de cada paquete para obtener sus coordenadas."""

    __tablename__ = "recorrido_paquetes"
    __table_args__ = (
        UniqueConstraint("recorrido_id", "paquete_id", name="uq_recorrido_paquetes_recorrido_paquete"),
        UniqueConstraint("recorrido_id", "orden", name="uq_recorrido_paquetes_recorrido_orden"),
        CheckConstraint(
            f"estado_en_recorrido IN {_lista_sql(EstadoRecorridoPaqueteEnum)}",
            name="ck_recorrido_paquetes_estado",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(types.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recorrido_id: Mapped[uuid.UUID] = mapped_column(types.Uuid(as_uuid=True), ForeignKey("recorridos.id"), nullable=False)
    paquete_id: Mapped[uuid.UUID] = mapped_column(types.Uuid(as_uuid=True), ForeignKey("paquetes.id"), nullable=False)
    orden: Mapped[int] = mapped_column(Integer, nullable=False)
    estado_en_recorrido: Mapped[str] = mapped_column(
        String(15), nullable=False, default=EstadoRecorridoPaqueteEnum.PENDIENTE.value
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False
    )

    recorrido: Mapped["RecorridoModel"] = relationship("RecorridoModel", back_populates="paquetes")
    paquete: Mapped["PaqueteModel"] = relationship("PaqueteModel", back_populates="recorrido_asignaciones")


class AlertaRecorridoModel(Base):
    """Alerta de domicilio/paquete sin recorrido asignado (HU10 Escenario 3).
    Se inserta una fila por cada paquete que queda sin ninguna
    `RecorridoPaqueteModel` al finalizar la generación/edición del día."""

    __tablename__ = "alertas_recorrido"

    id: Mapped[uuid.UUID] = mapped_column(types.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paquete_id: Mapped[uuid.UUID] = mapped_column(types.Uuid(as_uuid=True), ForeignKey("paquetes.id"), nullable=False)
    recorrido_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        types.Uuid(as_uuid=True), ForeignKey("recorridos.id"), nullable=True
    )
    """Recorrido durante cuya generación/edición se detectó la alerta, si
    aplica (puede ser None si se detecta fuera de ese flujo)."""
    motivo: Mapped[str] = mapped_column(String(40), nullable=False, default="SIN_RECORRIDO_ASIGNADO")
    resuelta: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False)
    resuelta_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    paquete: Mapped["PaqueteModel"] = relationship("PaqueteModel", back_populates="alertas")
    recorrido: Mapped[Optional["RecorridoModel"]] = relationship("RecorridoModel", back_populates="alertas_generadas")


class PosicionActualRepartidorModel(Base):
    """Última ubicación conocida de un repartidor (HU11). Guarda solo la
    posición más reciente (UPSERT en cada ping), no un historial de todos
    los pings: ninguna HU pide ver el recorrido pasado del repartidor, solo
    su ubicación actual en el mapa — un historial completo sería una tabla
    de altísimo volumen sin caso de uso que lo consuma. La proximidad de
    10km al destino (HU11 Escenario 3) se calcula en la aplicación
    comparando esta posición contra las coordenadas de la sucursal destino
    en cada ping, no en SQL."""

    __tablename__ = "posicion_actual_repartidor"

    repartidor_id: Mapped[uuid.UUID] = mapped_column(
        types.Uuid(as_uuid=True), ForeignKey("repartidores.usuario_id"), primary_key=True
    )
    recorrido_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        types.Uuid(as_uuid=True), ForeignKey("recorridos.id"), nullable=True
    )
    latitud: Mapped[float] = mapped_column(Float, nullable=False)
    longitud: Mapped[float] = mapped_column(Float, nullable=False)
    actualizado_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False
    )

    repartidor: Mapped["RepartidorModel"] = relationship("RepartidorModel", back_populates="posicion_actual")
    recorrido: Mapped[Optional["RecorridoModel"]] = relationship("RecorridoModel", back_populates="posiciones_actuales")


class EventoEntregaModel(Base):
    """Entrega a domicilio (HU12) y retiro en sucursal (HU13), unificadas:
    en el fondo son el mismo evento de negocio ("el paquete deja la red de
    la empresa"), con datos casi idénticos (quién lo recibe, cuándo, quién
    lo registra). Un paquete puede tener varias filas: cada intento fallido
    de HU12 Escenario 3 es una fila nueva, y la entrega exitosa final (o el
    retiro) es la última.

    `firma_imagen` guarda el archivo directamente en la base (no en un
    storage externo como S3): por ahora el proyecto no terceriza nada, y una
    firma es una imagen chica — si el volumen lo justifica en el futuro,
    migrar a un storage externo es un cambio de aplicación, no de esquema
    (esta columna se reemplazaría por una URL sin tocar el resto de la
    tabla)."""

    __tablename__ = "eventos_entrega"
    __table_args__ = (
        CheckConstraint(f"tipo_evento IN {_lista_sql(TipoEventoEntregaEnum)}", name="ck_eventos_entrega_tipo"),
        CheckConstraint(f"resultado IN {_lista_sql(ResultadoEventoEntregaEnum)}", name="ck_eventos_entrega_resultado"),
        Index("idx_eventos_entrega_paquete", "paquete_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(types.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paquete_id: Mapped[uuid.UUID] = mapped_column(types.Uuid(as_uuid=True), ForeignKey("paquetes.id"), nullable=False)
    tipo_evento: Mapped[str] = mapped_column(String(20), nullable=False)
    resultado: Mapped[str] = mapped_column(String(10), nullable=False)
    receptor_nombre: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    receptor_documento: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    es_autorizado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    """HU13 Escenario 2: True cuando retira una persona distinta al
    destinatario, presentando la Autorización de Retiro física."""
    documento_destinatario_verificado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    firma_imagen: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    firma_content_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    motivo_fallo: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    usuario_registro_id: Mapped[uuid.UUID] = mapped_column(
        types.Uuid(as_uuid=True), ForeignKey("usuarios.id"), nullable=False
    )
    sucursal_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("sucursales.id"), nullable=True)
    latitud: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitud: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False)

    paquete: Mapped["PaqueteModel"] = relationship("PaqueteModel", back_populates="eventos_entrega")
    usuario_registro: Mapped["UsuarioModel"] = relationship("UsuarioModel")
    sucursal: Mapped[Optional["SucursalModel"]] = relationship("SucursalModel")

