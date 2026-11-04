import uuid
from typing import Any

from app.application.interfaces.repositorio_envios import IRepositorioEnvios
from app.application.interfaces.repositorio_reclamos import IRepositorioReclamos
from app.application.interfaces.servicio_reclamos import IServicioReclamos
from app.contracts.reclamos import (
    ActualizarEstadoReclamoRequest,
    CrearReclamoRequest,
    CrearReclamoResponse,
    InicioReclamoData,
    InicioReclamoResponse,
    ListarReclamosAdminResponse,
    PaqueteReclamableData,
    ReclamoAdminData,
    ReclamoAdminResponse,
    ReclamoPublicoData,
    TipoReclamoData,
)
from app.core.exceptions import (
    DuplicateEntryException,
    NotFoundException,
    ValidationException,
)
from app.domain.constants.estados_logistica import EstadoReclamoEnum
from app.domain.rules.codigos_rules import normalizar_token_seguimiento
from app.domain.rules.recepcion_rules import normalizar_codigo_escaneado
from app.domain.rules.reclamo_rules import (
    DESCRIPCIONES_TIPO_RECLAMO,
    ESTADOS_RECLAMO_ACTIVOS,
    ESTADOS_RECLAMO_CERRADOS,
    MAX_RECLAMOS_ACTIVOS_POR_ENVIO,
    es_estado_reclamo_valido,
    es_reclamo_duplicado,
    es_tipo_reclamo_valido,
    evaluar_habilitacion_reclamo,
    normalizar_tipo_reclamo,
    validar_contacto_reclamo,
    validar_transicion_reclamo,
)
from app.infrastructure.db.models import ReclamoModel

MENSAJE_TOKEN_INEXISTENTE = "No se encontró un envío asociado a ese código de seguimiento."


class ServicioReclamos(IServicioReclamos):
    """Servicio de aplicación de los reclamos iniciados desde la vista pública (HU07).

    Cubre el Escenario 1 de HU07: quien accedió a un envío con un token válido
    selecciona la opción de reclamar y el sistema habilita el inicio del
    reclamo **para ese envío**. Suma la gestión interna del reclamo, que es lo
    que le da sentido al "para" de la historia (poder gestionar el
    inconveniente).
    """

    def __init__(
        self,
        repositorio_reclamos: IRepositorioReclamos,
        repositorio_envios: IRepositorioEnvios,
    ):
        self.repo_reclamos = repositorio_reclamos
        self.repo_envios = repositorio_envios

    # --- Vista pública ---

    async def obtener_inicio_reclamo(self, token: str) -> InicioReclamoResponse:
        """Devuelve lo necesario para habilitar el formulario de reclamo.

        Tipos de reclamo, paquetes del envío que se pueden señalar como
        afectados y los reclamos ya iniciados con su estado, para que quien
        consulta no repita un reclamo que ya está en curso.
        """
        envio = await self._obtener_envio(token)
        reclamos = await self.repo_reclamos.listar_por_envio(envio.id)
        activos = [r for r in reclamos if r.estado in ESTADOS_RECLAMO_ACTIVOS]
        habilitado, motivo = evaluar_habilitacion_reclamo(len(activos))

        return InicioReclamoResponse(
            data=InicioReclamoData(
                token_seguimiento=envio.token_seguimiento,
                puede_iniciar=habilitado,
                motivo_no_habilitado=motivo,
                max_reclamos_activos=MAX_RECLAMOS_ACTIVOS_POR_ENVIO,
                tipos_reclamo=[
                    TipoReclamoData(codigo=codigo, descripcion=descripcion)
                    for codigo, descripcion in DESCRIPCIONES_TIPO_RECLAMO.items()
                ],
                paquetes=[
                    PaqueteReclamableData(
                        numero_paquete=p.numero_paquete,
                        descripcion=p.descripcion,
                        estado=p.estado,
                    )
                    for p in envio.paquetes
                ],
                reclamos=[self._mapear_publico(r) for r in reclamos],
            )
        )

    async def crear_reclamo(self, token: str, datos: CrearReclamoRequest) -> CrearReclamoResponse:
        envio = await self._obtener_envio(token)

        # 1. Al menos un medio de contacto válido (el reclamo no tiene sesión).
        errores_contacto = validar_contacto_reclamo(datos.contacto_email, datos.contacto_telefono)
        if errores_contacto:
            raise ValidationException(
                message="Los datos de contacto del reclamo no son válidos.",
                errors=errores_contacto,
            )

        # 2. Si se indicó un paquete, tiene que pertenecer a este envío.
        paquete_id = None
        if datos.numero_paquete:
            numero = normalizar_codigo_escaneado(datos.numero_paquete)
            paquete = next((p for p in envio.paquetes if p.numero_paquete == numero), None)
            if not paquete:
                raise ValidationException(
                    message="El paquete indicado no pertenece a este envío.",
                    errors=[{
                        "field": "numero_paquete",
                        "message": f"El envío {envio.token_seguimiento} no contiene el paquete '{numero}'.",
                    }],
                )
            paquete_id = paquete.id

        # 3. Tope de reclamos activos y anti-duplicado.
        reclamos = await self.repo_reclamos.listar_por_envio(envio.id)
        activos = [r for r in reclamos if r.estado in ESTADOS_RECLAMO_ACTIVOS]

        habilitado, motivo = evaluar_habilitacion_reclamo(len(activos))
        if not habilitado:
            raise ValidationException(
                message="No se puede iniciar un nuevo reclamo para este envío.",
                errors=[{"field": "token", "message": motivo or "Reclamo no habilitado."}],
            )

        if es_reclamo_duplicado(datos.tipo, paquete_id, [(r.tipo, r.paquete_id) for r in activos]):
            raise DuplicateEntryException(
                message="Ya hay un reclamo en curso con el mismo motivo para este envío o paquete.",
                errors=[{
                    "field": "tipo",
                    "message": "Consultá el estado del reclamo existente en lugar de iniciar uno nuevo.",
                }],
            )

        reclamo = ReclamoModel(
            id=uuid.uuid4(),
            envio_id=envio.id,
            paquete_id=paquete_id,
            tipo=datos.tipo,
            descripcion=datos.descripcion,
            contacto_nombre=datos.contacto_nombre,
            contacto_email=str(datos.contacto_email).lower() if datos.contacto_email else None,
            contacto_telefono=datos.contacto_telefono,
            estado=EstadoReclamoEnum.ABIERTO.value,
        )
        creado = await self.repo_reclamos.crear(reclamo)

        return CrearReclamoResponse(data=self._mapear_publico(creado))

    # --- Gestión interna ---

    async def listar_reclamos(
        self,
        estado: str | None = None,
        tipo: str | None = None,
        token_seguimiento: str | None = None,
        sucursal_id: int | None = None,
    ) -> ListarReclamosAdminResponse:
        errores = []
        estado_filtro = estado.strip().upper() if estado and estado.strip() else None
        tipo_filtro = normalizar_tipo_reclamo(tipo) if tipo and tipo.strip() else None

        if estado_filtro and not es_estado_reclamo_valido(estado_filtro):
            errores.append({"field": "estado", "message": f"Estado de reclamo inválido: '{estado}'."})
        if tipo_filtro and not es_tipo_reclamo_valido(tipo_filtro):
            errores.append({"field": "tipo", "message": f"Tipo de reclamo inválido: '{tipo}'."})
        if errores:
            raise ValidationException(message="Los filtros indicados no son válidos.", errors=errores)

        token_filtro = normalizar_token_seguimiento(token_seguimiento) or None
        reclamos = await self.repo_reclamos.listar(
            estado=estado_filtro,
            tipo=tipo_filtro,
            token_seguimiento=token_filtro,
            sucursal_id=sucursal_id,
        )
        return ListarReclamosAdminResponse(
            total=len(reclamos),
            data=[self._mapear_admin(r) for r in reclamos],
        )

    async def obtener_reclamo(self, id: uuid.UUID) -> ReclamoAdminResponse:
        reclamo = await self._obtener_reclamo(id)
        return ReclamoAdminResponse(data=self._mapear_admin(reclamo))

    async def actualizar_estado(
        self,
        id: uuid.UUID,
        datos: ActualizarEstadoReclamoRequest,
        usuario_gestion: Any,
    ) -> ReclamoAdminResponse:
        reclamo = await self._obtener_reclamo(id)

        errores = validar_transicion_reclamo(reclamo.estado, datos.estado, datos.resolucion)
        if errores:
            raise ValidationException(
                message="No se puede aplicar el cambio de estado solicitado.",
                errors=errores,
            )

        reclamo.estado = datos.estado
        if datos.resolucion and datos.resolucion.strip():
            reclamo.resolucion = datos.resolucion.strip()
        # Queda registrado quién tomó o cerró el reclamo por última vez.
        reclamo.usuario_resolucion_id = usuario_gestion.id

        actualizado = await self.repo_reclamos.actualizar(reclamo)
        mensaje = (
            "Reclamo cerrado correctamente."
            if actualizado.estado in ESTADOS_RECLAMO_CERRADOS
            else "Reclamo actualizado correctamente."
        )
        return ReclamoAdminResponse(message=mensaje, data=self._mapear_admin(actualizado))

    # --- Auxiliares ---

    async def _obtener_envio(self, token: str) -> Any:
        envio = await self.repo_envios.obtener_por_token(normalizar_token_seguimiento(token))
        if not envio:
            raise NotFoundException(MENSAJE_TOKEN_INEXISTENTE)
        return envio

    async def _obtener_reclamo(self, id: uuid.UUID) -> ReclamoModel:
        reclamo = await self.repo_reclamos.obtener_por_id(id)
        if not reclamo:
            raise NotFoundException(f"No existe un reclamo con id {id}.")
        return reclamo

    def _mapear_publico(self, reclamo: ReclamoModel) -> ReclamoPublicoData:
        return ReclamoPublicoData(
            id=reclamo.id,
            numero_paquete=reclamo.paquete.numero_paquete if reclamo.paquete else None,
            tipo=reclamo.tipo,
            estado=reclamo.estado,
            descripcion=reclamo.descripcion,
            resolucion=reclamo.resolucion,
            fecha_creacion=reclamo.created_at,
            ultima_actualizacion=reclamo.updated_at,
        )

    def _mapear_admin(self, reclamo: ReclamoModel) -> ReclamoAdminData:
        envio = reclamo.envio
        usuario = reclamo.usuario_resolucion
        return ReclamoAdminData(
            id=reclamo.id,
            envio_id=reclamo.envio_id,
            token_seguimiento=envio.token_seguimiento,
            remitente_nombre=envio.remitente_nombre,
            destinatario_nombre=envio.destinatario_nombre,
            numero_paquete=reclamo.paquete.numero_paquete if reclamo.paquete else None,
            tipo=reclamo.tipo,
            descripcion=reclamo.descripcion,
            contacto_nombre=reclamo.contacto_nombre,
            contacto_email=reclamo.contacto_email,
            contacto_telefono=reclamo.contacto_telefono,
            estado=reclamo.estado,
            resolucion=reclamo.resolucion,
            usuario_resolucion_id=reclamo.usuario_resolucion_id,
            usuario_resolucion_nombre=usuario.nombre if usuario else None,
            created_at=reclamo.created_at,
            updated_at=reclamo.updated_at,
        )
