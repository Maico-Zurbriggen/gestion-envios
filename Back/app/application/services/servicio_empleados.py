from uuid import UUID

from app.application.interfaces.repositorio_roles import IRepositorioRoles
from app.application.interfaces.repositorio_usuarios import IRepositorioUsuarios
from app.contracts.empleados import (
    ActualizarEmpleadoRequest,
    CambiarEstadoEmpleadoRequest,
    CrearEmpleadoRequest,
    CrearEmpleadoResponse,
    EmpleadoCreadoData,
    EmpleadoData,
    EmpleadoResponse,
    ListarEmpleadosData,
    ListarEmpleadosResponse,
    PasswordRestablecidaData,
    PasswordRestablecidaResponse,
    ResumenEmpleadosData,
)
from app.core.exceptions import DuplicateEntryException, NotFoundException, ValidationException
from app.domain.rules.empleado_rules import (
    ESTADO_ACTIVO,
    ESTADO_INACTIVO,
    deja_de_ser_superadmin_activo,
    validar_cambios_propios,
)
from app.domain.rules.password_rules import generar_password_temporal
from app.infrastructure.auth.hasher import HasherContrasenas
from app.infrastructure.db.models import UsuarioModel


class ServicioEmpleados:
    """Servicio que implementa la gestión y alta de empleados administrativos (HU01)."""

    def __init__(
        self,
        repositorio_usuarios: IRepositorioUsuarios,
        repositorio_roles: IRepositorioRoles,
        hasher: HasherContrasenas = HasherContrasenas(),
    ):
        self.repo_usuarios = repositorio_usuarios
        self.repo_roles = repositorio_roles
        self.hasher = hasher

    async def crear_empleado(
        self, datos: CrearEmpleadoRequest
    ) -> CrearEmpleadoResponse:
        """Da de alta a un nuevo empleado en el sistema (HU01 - Escenarios 3 y 4)."""
        # 1. Validar existencia del rol
        rol = await self.repo_roles.obtener_por_id(datos.rol_id)
        if not rol:
            raise ValidationException(
                message="El rol seleccionado no es válido.",
                errors=[{"field": "rol_id", "message": f"No existe un rol con ID {datos.rol_id}."}],
            )

        # 2. Validar unicidad de DNI y Email (Escenario 4 de HU01)
        errores_duplicados = []
        usuario_dni = await self.repo_usuarios.obtener_por_dni(datos.dni)
        if usuario_dni:
            errores_duplicados.append({"field": "dni", "message": "El DNI ingresado ya está registrado."})

        # Se busca con la misma normalización con la que se guarda (minúsculas):
        # si no, "Laura@..." pasaba la validación y chocaba con el UNIQUE de la base (500).
        usuario_email = await self.repo_usuarios.obtener_por_email(datos.email.strip().lower())
        if usuario_email:
            errores_duplicados.append({"field": "email", "message": "El Email ingresado ya está registrado."})

        if errores_duplicados:
            raise DuplicateEntryException(
                message="El DNI o Email ya se encuentran registrados.",
                errors=errores_duplicados,
            )

        # 3. Generar contraseña temporal segura (Adenda Sección B)
        password_temporal = generar_password_temporal(longitud=12)
        password_hash = self.hasher.generar_hash(password_temporal)

        # 4. Crear entidad de usuario con estado Activo y requiere_cambio_password = True
        nuevo_usuario = UsuarioModel(
            nombre=datos.nombre.strip(),
            dni=datos.dni.strip(),
            email=datos.email.strip().lower(),
            telefono=datos.telefono.strip(),
            password_hash=password_hash,
            estado="Activo",
            requiere_cambio_password=True,
            rol_id=datos.rol_id,
        )

        usuario_creado = await self.repo_usuarios.crear(nuevo_usuario)

        return CrearEmpleadoResponse(
            status="success",
            message="Empleado creado correctamente.",
            data=EmpleadoCreadoData(
                id=usuario_creado.id,
                nombre=usuario_creado.nombre,
                dni=usuario_creado.dni,
                email=usuario_creado.email,
                telefono=usuario_creado.telefono,
                estado=usuario_creado.estado,
                rol=rol.nombre,
                password_temporal=password_temporal,
            ),
        )

    # --- Gestión de usuarios del personal ------------------------------------

    @staticmethod
    def _a_dato(usuario: UsuarioModel) -> EmpleadoData:
        return EmpleadoData(
            id=usuario.id,
            nombre=usuario.nombre,
            dni=usuario.dni,
            email=usuario.email,
            telefono=usuario.telefono,
            estado=usuario.estado,
            rol=usuario.rol.nombre if usuario.rol else "",
            rol_id=usuario.rol_id,
            requiere_cambio_password=usuario.requiere_cambio_password,
            created_at=usuario.created_at,
            updated_at=usuario.updated_at,
        )

    async def _obtener(self, id: UUID) -> UsuarioModel:
        usuario = await self.repo_usuarios.obtener_por_id(id)
        if not usuario:
            raise NotFoundException("No existe un usuario con ese identificador.")
        return usuario

    async def listar_empleados(
        self, buscar: str | None = None, rol_id: int | None = None, estado: str | None = None
    ) -> ListarEmpleadosResponse:
        """Listado filtrado más un resumen del personal completo (no del filtro),
        así los indicadores no cambian al buscar."""
        filtrados = await self.repo_usuarios.listar(buscar=buscar, rol_id=rol_id, estado=estado)
        todos = await self.repo_usuarios.listar()
        por_rol: dict[str, int] = {}
        for usuario in todos:
            nombre_rol = usuario.rol.nombre if usuario.rol else ""
            por_rol[nombre_rol] = por_rol.get(nombre_rol, 0) + 1
        activos = sum(1 for usuario in todos if usuario.estado == ESTADO_ACTIVO)
        return ListarEmpleadosResponse(data=ListarEmpleadosData(
            empleados=[self._a_dato(u) for u in filtrados],
            total=len(filtrados),
            resumen=ResumenEmpleadosData(total=len(todos), activos=activos, inactivos=len(todos) - activos, por_rol=por_rol),
        ))

    async def obtener_empleado(self, id: UUID) -> EmpleadoResponse:
        return EmpleadoResponse(data=self._a_dato(await self._obtener(id)))

    async def actualizar_empleado(self, actor_id: UUID, id: UUID, datos: ActualizarEmpleadoRequest) -> EmpleadoResponse:
        usuario = await self._obtener(id)
        cambios = datos.model_dump(exclude_unset=True)
        rol_actual = usuario.rol.nombre if usuario.rol else ""
        rol_nuevo = rol_actual
        if cambios.get("rol_id") is not None and cambios["rol_id"] != usuario.rol_id:
            rol = await self.repo_roles.obtener_por_id(cambios["rol_id"])
            if not rol:
                raise ValidationException(
                    message="El rol seleccionado no es válido.",
                    errors=[{"field": "rol_id", "message": f"No existe un rol con ID {cambios['rol_id']}."}],
                )
            rol_nuevo = rol.nombre
        errores = validar_cambios_propios(es_uno_mismo=actor_id == id, cambia_rol=rol_nuevo != rol_actual, cambia_estado=False)
        if errores:
            raise ValidationException(message="No podés modificar tu propio rol.", errors=errores)
        if deja_de_ser_superadmin_activo(
            rol_actual=rol_actual, estado_actual=usuario.estado, rol_nuevo=rol_nuevo, estado_nuevo=usuario.estado
        ):
            await self._exigir_otro_superadmin(id)

        duplicados = []
        if cambios.get("dni") is not None and cambios["dni"] != usuario.dni:
            existente = await self.repo_usuarios.obtener_por_dni(cambios["dni"])
            if existente and existente.id != id:
                duplicados.append({"field": "dni", "message": "El DNI ingresado ya está registrado."})
        if cambios.get("email") is not None:
            cambios["email"] = str(cambios["email"]).strip().lower()
            existente = await self.repo_usuarios.obtener_por_email(cambios["email"])
            if existente and existente.id != id:
                duplicados.append({"field": "email", "message": "El Email ingresado ya está registrado."})
        if duplicados:
            raise DuplicateEntryException(message="El DNI o Email ya se encuentran registrados.", errors=duplicados)

        for campo in ("nombre", "dni", "email", "telefono", "rol_id"):
            valor = cambios.get(campo)
            if valor is not None:
                setattr(usuario, campo, valor.strip() if isinstance(valor, str) else valor)
        actualizado = await self.repo_usuarios.guardar(usuario)
        return EmpleadoResponse(message="Usuario actualizado correctamente.", data=self._a_dato(actualizado))

    async def cambiar_estado(self, actor_id: UUID, id: UUID, datos: CambiarEstadoEmpleadoRequest) -> EmpleadoResponse:
        usuario = await self._obtener(id)
        if datos.estado == usuario.estado:
            return EmpleadoResponse(message="El usuario ya estaba en ese estado.", data=self._a_dato(usuario))
        errores = validar_cambios_propios(es_uno_mismo=actor_id == id, cambia_rol=False, cambia_estado=True)
        if errores:
            raise ValidationException(message="No podés dar de baja tu propio usuario.", errors=errores)
        rol = usuario.rol.nombre if usuario.rol else ""
        if deja_de_ser_superadmin_activo(rol_actual=rol, estado_actual=usuario.estado, rol_nuevo=rol, estado_nuevo=datos.estado):
            await self._exigir_otro_superadmin(id)
        usuario.estado = datos.estado
        actualizado = await self.repo_usuarios.guardar(usuario)
        mensaje = (
            "Usuario dado de baja. Ya no puede ingresar al sistema."
            if datos.estado == ESTADO_INACTIVO
            else "Usuario reactivado."
        )
        return EmpleadoResponse(message=mensaje, data=self._a_dato(actualizado))

    async def restablecer_password(self, actor_id: UUID, id: UUID) -> PasswordRestablecidaResponse:
        usuario = await self._obtener(id)
        if actor_id == id:
            raise ValidationException(
                message="Para cambiar tu propia contraseña usá la opción Cambiar contraseña.",
                errors=[{"field": "id", "message": "No podés blanquear tu propia contraseña."}],
            )
        password_temporal = generar_password_temporal(longitud=12)
        await self.repo_usuarios.restablecer_password(id, self.hasher.generar_hash(password_temporal))
        return PasswordRestablecidaResponse(
            data=PasswordRestablecidaData(id=usuario.id, nombre=usuario.nombre, password_temporal=password_temporal)
        )

    async def _exigir_otro_superadmin(self, id: UUID) -> None:
        if await self.repo_usuarios.contar_superadmins_activos(excluir_id=id) == 0:
            raise ValidationException(
                message="Debe quedar al menos un Superadministrador activo.",
                errors=[{"field": "rol_id", "message": "Es el único Superadministrador activo: asigná otro antes de cambiarlo."}],
            )

