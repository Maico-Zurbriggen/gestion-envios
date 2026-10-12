from typing import Any, Optional, Protocol
from uuid import UUID


class IRepositorioRecepciones(Protocol):
    """Protocolo de acceso a datos de la recepción de paquetes en terminal (HU06).

    Se mantiene separado de `IRepositorioEntregas` (HU12/HU13) porque son los
    dos extremos opuestos del ciclo logístico: este registra el ingreso del
    paquete a la red y aquel su salida definitiva.
    """

    async def buscar_paquete_por_codigo(self, codigo: str) -> Optional[Any]:
        """Busca un paquete por su `numero_paquete` (el valor del código de barras)
        o por su `id` (UUID), con el envío y las sucursales ya cargados."""
        ...

    async def registrar_recepcion_paquete(
        self,
        paquete_id: UUID,
        nuevo_estado: str,
        sucursal_id: int,
        historial_estado: Any,
    ) -> Any:
        """Actualiza estado y ubicación del paquete y persiste la fila de historial
        en una sola transacción."""
        ...
