from app.application.interfaces.repositorio_roles import IRepositorioRoles
from app.application.interfaces.repositorio_usuarios import IRepositorioUsuarios
from app.contracts.empleados import (
    CrearEmpleadoRequest,
    CrearEmpleadoResponse,
    EmpleadoCreadoData,
)
from app.core.exceptions import DuplicateEntryException, ValidationException
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

        usuario_email = await self.repo_usuarios.obtener_por_email(datos.email)
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

