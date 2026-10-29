from datetime import date
from typing import Any, Protocol
from uuid import UUID


class IRepositorioRecorridos(Protocol):
    """Protocolo de acceso a datos de los recorridos y sus alertas (HU10).

    Además de las consultas, expone operaciones de unidad de trabajo
    (`agregar`, `eliminar`, `sincronizar`, `confirmar`): generar recorridos
    escribe en tres tablas (`recorridos`, `recorrido_paquetes`,
    `alertas_recorrido`) y tiene que hacerlo en un único commit.
    """

    # --- Paquetes ---

    async def contar_sin_llegar(self) -> dict[int | None, int]:
        """Registrados que todavía no se recibieron, por la sucursal donde los van a llevar."""
        ...

    async def listar_paquetes_listos_en_sucursal(self, sucursal_id: int) -> list[Any]:
        """Paquetes ubicados en la sucursal y en un estado listo para despacho,
        con su envío y la sucursal de destino precargados."""
        ...

    async def buscar_paquetes_por_codigos(self, codigos: list[str]) -> list[Any]:
        """Paquetes por número (`PAQ-...`) o por UUID, con su envío precargado."""
        ...

    async def paquetes_en_recorridos_activos(self, excluir_recorridos: set[UUID] | None = None) -> dict[UUID, UUID]:
        """`{paquete_id: recorrido_id}` de los paquetes pendientes en recorridos
        generados, en edición o en curso (excepto los recorridos excluidos)."""
        ...

    # --- Repartidores ---

    async def listar_repartidores_disponibles(self, sucursal_id: int, tipo_distancia: str) -> list[Any]:
        """Perfiles activos de la sucursal y tipo, con usuario Activo precargado."""
        ...

    async def obtener_repartidor(self, usuario_id: UUID) -> Any | None: ...

    async def repartidores_con_recorrido_activo(
        self,
        fecha: date,
        excluir_recorridos: set[UUID] | None = None,
    ) -> set[UUID]:
        """Repartidores que ya tienen un recorrido activo ese día."""
        ...

    # --- Recorridos ---

    async def listar_recorridos(
        self,
        sucursal_id: int | None = None,
        fecha: date | None = None,
        tipo_distancia: str | None = None,
        estado: str | None = None,
        repartidor_id: UUID | None = None,
        desde: date | None = None,
        hasta: date | None = None,
    ) -> list[Any]: ...

    async def obtener_recorrido(self, id: UUID) -> Any | None:
        """Recorrido con paquetes, envíos, repartidor y sucursal de origen precargados."""
        ...

    async def bloquear_recorrido(self, id: UUID, repartidor_id: UUID) -> None:
        """Serializa las escrituras del repartidor hasta el commit, también en SQLite."""
        ...

    async def obtener_posicion(self, repartidor_id: UUID) -> Any | None: ...

    async def actualizar_estado_paquete(self, paquete_id: UUID, anterior: str, nuevo: str,
                                       sucursal_id: int | None = None) -> None:
        """Actualización condicional: rechaza una transición si el estado cambió concurrentemente."""
        ...

    async def listar_recorridos_editables(self, sucursal_id: int, fecha: date, tipo_distancia: str) -> list[Any]: ...

    async def listar_recorridos_activos_del_envio(self, envio_id: UUID) -> list[Any]:
        """Recorridos afectados al completar la ubicación compartida de un envío."""
        ...

    # --- Alertas ---

    async def listar_alertas_pendientes_en_sucursal(self, sucursal_id: int) -> list[Any]: ...

    async def listar_alertas(self, sucursal_id: int | None = None, incluir_resueltas: bool = False) -> list[Any]: ...

    async def alertas_pendientes_de_paquetes(self, paquete_ids: list[UUID]) -> list[Any]: ...

    async def obtener_alerta(self, id: UUID) -> Any | None: ...

    # --- Unidad de trabajo ---

    async def agregar(self, entidad: Any) -> None: ...

    async def eliminar(self, entidad: Any) -> None: ...

    async def sincronizar(self) -> None:
        """Envía los cambios pendientes a la base sin confirmar la transacción."""
        ...

    async def confirmar(self) -> None:
        """Confirma la transacción."""
        ...

    async def visitas_fallidas_de(self, paquete_ids: list[UUID]) -> dict[UUID, int]:
        """Visitas a domicilio sin éxito de cada paquete."""
        ...

    async def control_de_carga(self, recorrido_id: UUID) -> tuple[str, int] | None:
        """(estado, verificados) del control de carga del recorrido, si existe."""
        ...
