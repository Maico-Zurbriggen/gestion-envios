import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.domain.constants.roles import RolEnum, RolIdEnum
from app.domain.rules.paquete_rules import DIMENSION_MAX_CM, PESO_MAX_KG, SUMA_DIMENSIONES_MAX_CM
from app.infrastructure.auth.hasher import HasherContrasenas
from app.infrastructure.db.models import PreguntaFrecuenteModel, RolModel, SucursalModel, UsuarioModel
from app.infrastructure.db.session import AsyncSessionLocal

ROLES_BASE = [
    {"id": RolIdEnum.SUPERADMIN.value, "nombre": RolEnum.SUPERADMIN.value, "descripcion": "Administrador general del sistema"},
    {"id": RolIdEnum.ADMINISTRATIVO.value, "nombre": RolEnum.ADMINISTRATIVO.value, "descripcion": "Usuario administrativo operativo"},
    {"id": RolIdEnum.VENDEDOR.value, "nombre": RolEnum.VENDEDOR.value, "descripcion": "Personal de terminal / venta"},
    {"id": RolIdEnum.REPARTIDOR.value, "nombre": RolEnum.REPARTIDOR.value, "descripcion": "Personal de reparto"},
]

SUCURSALES_BASE = [
    {"nombre": "Sucursal Córdoba Centro", "provincia": "Córdoba", "ciudad": "Córdoba", "direccion": "Av. Colón 1234", "latitud": -31.4167, "longitud": -64.1833},
    {"nombre": "Sucursal Rosario Sur", "provincia": "Santa Fe", "ciudad": "Rosario", "direccion": "Bv. Oroño 2456", "latitud": -32.9587, "longitud": -60.6931},
    {"nombre": "Sucursal Mendoza Capital", "provincia": "Mendoza", "ciudad": "Mendoza", "direccion": "San Martín 890", "latitud": -32.8908, "longitud": -68.8272},
    {"nombre": "Sucursal Buenos Aires Palermo", "provincia": "Buenos Aires", "ciudad": "CABA", "direccion": "Av. Santa Fe 3450", "latitud": -34.5875, "longitud": -58.4205},
    {"nombre": "Sucursal Salta Norte", "provincia": "Salta", "ciudad": "Salta", "direccion": "Av. Sarmiento 555", "latitud": -24.7859, "longitud": -65.4117},
    {"nombre": "Sucursal Mar del Plata", "provincia": "Buenos Aires", "ciudad": "Mar del Plata", "direccion": "Av. Colón 3020", "latitud": -38.0055, "longitud": -57.5426},
]

VENCIMIENTO = settings.VENCIMIENTO_PRE_REGISTRO_DIAS
PLAZO_RETIRO = settings.PLAZO_RETIRO_DIAS_HABILES
MAX_VISITAS = settings.MAX_VISITAS_DOMICILIO

PREGUNTAS_FRECUENTES_BASE = [
    # --- Envíos (HU03 / HU06) ---
    {
        "categoria": "Envíos",
        "orden": 10,
        "pregunta": "¿Cómo registro un envío?",
        "respuesta": (
            "Desde la opción \"Registrar envío\", sin necesidad de crear una cuenta. Completás los datos de "
            "quien envía y de quien recibe, cargás uno o más paquetes, elegís si se entrega a domicilio o se "
            "retira en una sucursal y aceptás los términos y condiciones. Al confirmar obtenés el código de "
            "seguimiento y un comprobante con un código de barras por paquete. No necesitás imprimir etiquetas: "
            "las imprime la sucursal cuando recibe el paquete."
        ),
    },
    {
        "categoria": "Envíos",
        "orden": 20,
        "pregunta": "¿Cuánto puede pesar y medir un paquete?",
        "respuesta": (
            f"Cada paquete puede pesar hasta {PESO_MAX_KG} kg. Ninguna de sus medidas (largo, ancho o alto) "
            f"puede superar los {DIMENSION_MAX_CM} cm y la suma de las tres no puede superar los "
            f"{SUMA_DIMENSIONES_MAX_CM} cm. Si un paquete excede alguno de estos límites, el sistema no permite "
            "registrarlo."
        ),
    },
    {
        "categoria": "Envíos",
        "orden": 30,
        "pregunta": "¿Qué no puedo enviar?",
        "respuesta": (
            "No se aceptan materiales peligrosos, inflamables o explosivos, armas, dinero en efectivo, "
            "sustancias ilegales, animales vivos ni alimentos perecederos. El detalle completo de restricciones "
            "y contenidos prohibidos está en los términos y condiciones que se aceptan al registrar el envío."
        ),
    },
    {
        "categoria": "Envíos",
        "orden": 40,
        "pregunta": "Ya registré el envío, ¿qué hago con el paquete?",
        "respuesta": (
            f"Llevalo a cualquier sucursal dentro de los {VENCIMIENTO} días con el código de seguimiento o el "
            "comprobante (impreso o en el celular). Ahí lo pesan, le pegan la etiqueta y te avisamos por correo y "
            f"WhatsApp que ya está en camino. Si pasan los {VENCIMIENTO} días sin llevarlo, el registro vence y "
            "tenés que registrar el envío de nuevo."
        ),
    },
    # --- Seguimiento (HU04 / HU05) ---
    {
        "categoria": "Seguimiento",
        "orden": 50,
        "pregunta": "¿Cómo consulto el estado de mi envío?",
        "respuesta": (
            "Ingresá el código de seguimiento (empieza con ENV-) en la sección \"Seguimiento\". No hace falta "
            "iniciar sesión: quien envía y quien recibe usan el mismo código y ven la misma información."
        ),
    },
    {
        "categoria": "Seguimiento",
        "orden": 60,
        "pregunta": "¿Dónde recibo el código de seguimiento?",
        "respuesta": (
            "Se muestra al terminar el registro y además se envía por correo electrónico tanto a quien envía "
            "como a quien recibe el paquete."
        ),
    },
    {
        "categoria": "Seguimiento",
        "orden": 70,
        "pregunta": "Mi envío tiene varios paquetes, ¿necesito un código por cada uno?",
        "respuesta": (
            "No. Un mismo código de seguimiento muestra todos los paquetes del envío, cada uno con su propio "
            "estado."
        ),
    },
    # --- Retiro en sucursal (HU09 / HU13) ---
    {
        "categoria": "Retiro en sucursal",
        "orden": 80,
        "pregunta": "¿Cómo sé si ya puedo retirar mi paquete?",
        "respuesta": (
            "Te avisamos por correo y WhatsApp cuando llega a la sucursal y queda listo. También podés verlo "
            "con el código de seguimiento: ahí figura la sucursal, la dirección y hasta qué día podés retirarlo. "
            f"Tenés {PLAZO_RETIRO} días hábiles; si no se retira en ese plazo, el paquete vuelve a quien lo envió."
        ),
    },
    {
        "categoria": "Retiro en sucursal",
        "orden": 90,
        "pregunta": "¿Qué necesito para retirar un paquete en sucursal?",
        "respuesta": (
            "Si lo retirás vos, tenés que ser mayor de 16 años y presentar tu documento de identidad original. "
            "Si lo retira otra persona, tiene que presentar su propio documento, una copia del documento del "
            "destinatario y la autorización de retiro firmada por el destinatario."
        ),
    },
    # --- Entregas a domicilio (HU10 / HU12) ---
    {
        "categoria": "Entregas a domicilio",
        "orden": 100,
        "pregunta": "¿Quién puede recibir un paquete en el domicilio?",
        "respuesta": (
            "Cualquier persona mayor de 16 años que se encuentre en el domicilio. Quien recibe firma la entrega "
            "y queda registrada la fecha y la hora."
        ),
    },
    {
        "categoria": "Entregas a domicilio",
        "orden": 110,
        "pregunta": "¿Qué pasa si no hay nadie cuando llega el repartidor?",
        "respuesta": (
            "El repartidor intenta comunicarse con el teléfono del destinatario. Si no logra concretar la "
            "entrega, la visita queda registrada en el seguimiento, se avisa por correo y WhatsApp y el paquete "
            f"sale en el próximo recorrido. Se hacen hasta {MAX_VISITAS} visitas: después queda para retirar en "
            "la sucursal, con el mismo plazo que cualquier retiro."
        ),
    },
    # --- Reclamos (HU07) ---
    {
        "categoria": "Reclamos",
        "orden": 120,
        "pregunta": "¿Cómo inicio un reclamo?",
        "respuesta": (
            "Consultá tu envío con el código de seguimiento y elegí la opción para iniciar un reclamo. Indicá "
            "el motivo (demora, daño, extravío u otro), el paquete afectado si corresponde, una descripción y "
            "un correo o teléfono de contacto."
        ),
    },
    {
        "categoria": "Reclamos",
        "orden": 130,
        "pregunta": "¿Cómo sé en qué estado está mi reclamo?",
        "respuesta": (
            "En la misma vista del envío, con el código de seguimiento, se listan los reclamos iniciados y su "
            "estado: abierto, en revisión, resuelto o rechazado, junto con la respuesta cuando se cierra."
        ),
    },
]
"""Contenido inicial de la sección de preguntas frecuentes (HU08). Los límites
de peso y medidas se toman de `paquete_rules` para que la respuesta no quede
desactualizada si cambian las reglas de HU03."""

RESPUESTAS_ANTERIORES: dict[str, str] = {
    "¿Cómo registro un envío?": (
        "Desde la opción \"Registrar envío\", sin necesidad de crear una cuenta. Completás los datos de "
        "quien envía y de quien recibe, cargás uno o más paquetes, elegís si se entrega a domicilio o se "
        "retira en una sucursal y aceptás los términos y condiciones. Al confirmar obtenés el código de "
        "seguimiento y una planilla imprimible con un código de barras por paquete."
    ),
    "Ya registré el envío, ¿qué hago con el paquete?": (
        "Imprimí la planilla, pegala en el paquete y llevalo a una sucursal. El personal escanea el código "
        "de barras de la planilla, identifica tu envío sin volver a cargar los datos y lo deja listo para "
        "despacharlo."
    ),
    "¿Cómo sé si ya puedo retirar mi paquete?": (
        "Con el código de seguimiento podés consultar las opciones de retiro: ahí se indica la sucursal "
        "asignada y si cada paquete ya está disponible para retirar. Esperá a que figure como disponible "
        "antes de acercarte."
    ),
    "¿Qué pasa si no hay nadie cuando llega el repartidor?": (
        "El repartidor intenta comunicarse con el teléfono del destinatario. Si no logra concretar la "
        "entrega, la visita queda registrada en el seguimiento, se avisa por correo y WhatsApp y el paquete "
        "se incluye en un nuevo recorrido."
    ),
}
"""Textos sembrados antes del circuito con admisión en sucursal y plazos. Si una
base todavía tiene alguno sin editar, se reemplaza por la versión actual."""


async def sembrar_roles(db: AsyncSession) -> None:
    """Inserta los roles predeterminados si no existen."""
    for rol_data in ROLES_BASE:
        stmt = select(RolModel).where(RolModel.id == rol_data["id"])
        result = await db.execute(stmt)
        existente = result.scalar_one_or_none()
        if not existente:
            rol = RolModel(
                id=rol_data["id"],
                nombre=rol_data["nombre"],
                descripcion=rol_data["descripcion"],
            )
            db.add(rol)
            logger.info(f"Sembrando rol: {rol_data['nombre']}")
    await db.commit()


async def sembrar_superadmin(db: AsyncSession) -> None:
    """Inserta el usuario Superadministrador inicial desde variables de entorno."""
    password_plana = settings.SUPERADMIN_SEED_PASSWORD
    if not password_plana:
        logger.warning("No se definió SUPERADMIN_SEED_PASSWORD. Omitiendo seed de Superadmin.")
        return

    dni = settings.SUPERADMIN_SEED_DNI
    email = settings.SUPERADMIN_SEED_EMAIL

    stmt = select(UsuarioModel).where((UsuarioModel.dni == dni) | (UsuarioModel.email == email))
    result = await db.execute(stmt)
    existente = result.scalar_one_or_none()

    if not existente:
        password_hash = HasherContrasenas.generar_hash(password_plana)
        superadmin = UsuarioModel(
            nombre=settings.SUPERADMIN_SEED_NOMBRE,
            dni=dni,
            email=email,
            telefono=settings.SUPERADMIN_SEED_TELEFONO,
            password_hash=password_hash,
            estado="Activo",
            requiere_cambio_password=False,
            rol_id=RolIdEnum.SUPERADMIN.value,
        )
        db.add(superadmin)
        await db.commit()
        logger.info(f"Superadministrador sembrado exitosamente: {email} (DNI: {dni})")
    else:
        logger.info(f"Superadministrador ya existente ({email} / {dni}).")


async def sembrar_sucursales(db: AsyncSession) -> None:
    """Inserta las sucursales predeterminadas si no existen (matching por nombre)."""
    for datos in SUCURSALES_BASE:
        stmt = select(SucursalModel).where(SucursalModel.nombre == datos["nombre"])
        result = await db.execute(stmt)
        if not result.scalar_one_or_none():
            db.add(SucursalModel(**datos))
            logger.info(f"Sembrando sucursal: {datos['nombre']}")
    await db.commit()


async def sembrar_preguntas_frecuentes(db: AsyncSession) -> None:
    """Carga el contenido inicial de preguntas frecuentes solo si la tabla está vacía.

    A diferencia de las sucursales (matching por nombre), acá no se compara
    pregunta por pregunta: el contenido es editable desde la administración, y
    re-sembrar por texto volvería a crear en cada arranque una pregunta que un
    administrador borró o reescribió a propósito.
    """
    existente = await db.execute(select(PreguntaFrecuenteModel.id).limit(1))
    if existente.scalar_one_or_none() is not None:
        await _actualizar_respuestas_sin_editar(db)
        return

    for datos in PREGUNTAS_FRECUENTES_BASE:
        db.add(PreguntaFrecuenteModel(publicada=True, **datos))
    await db.commit()
    logger.info(f"Sembradas {len(PREGUNTAS_FRECUENTES_BASE)} preguntas frecuentes iniciales.")


async def _actualizar_respuestas_sin_editar(db: AsyncSession) -> None:
    """Pone al día las respuestas que siguen exactamente como se sembraron.

    Solo toca una pregunta si su respuesta es idéntica al texto anterior: lo
    que un administrador reescribió o borró queda como está.
    """
    actuales = {datos["pregunta"]: datos["respuesta"] for datos in PREGUNTAS_FRECUENTES_BASE}
    filas = await db.execute(
        select(PreguntaFrecuenteModel).where(PreguntaFrecuenteModel.pregunta.in_(RESPUESTAS_ANTERIORES))
    )
    cambiadas = 0
    for pregunta in filas.scalars():
        if pregunta.respuesta == RESPUESTAS_ANTERIORES[pregunta.pregunta]:
            pregunta.respuesta = actuales[pregunta.pregunta]
            cambiadas += 1
    if cambiadas:
        await db.commit()
        logger.info(f"Se actualizaron {cambiadas} respuestas frecuentes al circuito actual.")


async def ejecutar_semillas(db: AsyncSession) -> None:
    """Datos base idempotentes: no duplica nada si ya existen."""
    await sembrar_roles(db)
    await sembrar_superadmin(db)
    await sembrar_sucursales(db)
    await sembrar_preguntas_frecuentes(db)


async def ejecutar_siembra() -> None:
    """Actualiza el esquema con Alembic y siembra los datos iniciales.

    No se usa `create_all`: contra Neon creaba tablas sin registrar la versión
    de Alembic y nunca agregaba columnas nuevas (ver `actualizar_base.py`).
    """
    if settings.DB_ACTUALIZAR_ESQUEMA_AL_INICIAR:
        from app.infrastructure.db.actualizar_base import actualizar_esquema_al_iniciar

        logger.info("Verificando el esquema de la base de datos...")
        await asyncio.to_thread(actualizar_esquema_al_iniciar)
    async with AsyncSessionLocal() as db:
        await ejecutar_semillas(db)
    logger.info("Siembra completada con éxito.")


if __name__ == "__main__":
    asyncio.run(ejecutar_siembra())

