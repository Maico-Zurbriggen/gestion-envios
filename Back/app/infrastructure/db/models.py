import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, func, types
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


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

