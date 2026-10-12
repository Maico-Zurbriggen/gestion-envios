"""Tests de integración de HU09 — Sucursales disponibles para retiro.

> Yo como usuario que espera un paquete deseo visualizar las sucursales
> disponibles para retiro cuando el envío no es a domicilio, para conocer dónde
> puedo retirar el paquete.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.constants.error_codes import ErrorCodes
from app.domain.constants.estados_logistica import EstadoPaqueteEnum
from app.infrastructure.db.models import EnvioModel, PaqueteModel, SucursalModel

CATALOGO = "/api/v1/sucursales"
OPCIONES = "/api/v1/sucursales/opciones-retiro"


async def _crear_envio(
    db: AsyncSession,
    *,
    token: str,
    tipo_entrega: str = "sucursal",
    sucursal_destino_id: int | None = 1,
    estados_paquetes: list[str] | None = None,
) -> EnvioModel:
    """Crea un envío con uno o más paquetes en los estados indicados."""
    envio = EnvioModel(
        remitente_nombre="Sofía Remitente",
        remitente_documento="30555666",
        remitente_telefono="+543564555666",
        remitente_email="sofia.remitente@test.com",
        destinatario_nombre="Pablo Destinatario",
        destinatario_telefono="+543564777888",
        destinatario_email="pablo.destinatario@test.com",
        tipo_entrega=tipo_entrega,
        sucursal_destino_id=sucursal_destino_id if tipo_entrega == "sucursal" else None,
        provincia_destino="Córdoba" if tipo_entrega == "domicilio" else None,
        ciudad_destino="Córdoba" if tipo_entrega == "domicilio" else None,
        direccion_destino="Av. Vélez Sarsfield 100" if tipo_entrega == "domicilio" else None,
        terminos_aceptados=True,
        token_seguimiento=token,
    )
    db.add(envio)
    await db.commit()
    await db.refresh(envio)

    for indice, estado in enumerate(estados_paquetes or ["Pendiente"], start=1):
        db.add(
            PaqueteModel(
                envio_id=envio.id,
                numero_paquete=f"PAQ-{token[4:]}{indice:02d}"[:30],
                descripcion=f"Bulto {indice}",
                peso_kg=1.5,
                largo_cm=20.0,
                ancho_cm=15.0,
                alto_cm=10.0,
                estado=estado,
            )
        )
    await db.commit()
    await db.refresh(envio)
    return envio


# --- Escenario 1: el envío se gestiona para retiro ---


@pytest.mark.asyncio
async def test_hu09_escenario_1_muestra_las_sucursales_disponibles_para_retiro(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """HU09 Escenario 1: dado un envío para retiro, la consulta pública devuelve
    las sucursales donde se puede retirar el paquete."""
    await _crear_envio(db_session, token="ENV-RETIRO0001", sucursal_destino_id=1)

    resp = await client.get(f"{OPCIONES}/ENV-RETIRO0001")

    assert resp.status_code == 200
    cuerpo = resp.json()
    assert cuerpo["status"] == "success"
    data = cuerpo["data"]
    assert data["token_seguimiento"] == "ENV-RETIRO0001"
    assert data["tipo_entrega"] == "sucursal"
    assert data["aplica_retiro"] is True
    assert data["motivo_no_aplica"] is None

    asignada = data["sucursal_asignada"]
    assert asignada["id"] == 1
    assert asignada["nombre"] == "Sucursal Test Centro"
    assert asignada["direccion"] == "Calle Falsa 123"
    assert asignada["ciudad"] == "Córdoba"
    assert asignada["latitud"] == -31.4
    assert asignada["longitud"] == -64.18
    assert asignada["es_sucursal_asignada"] is True

    # La sucursal asignada siempre encabeza la lista de puntos de retiro
    assert len(data["sucursales_disponibles"]) >= 1
    assert data["sucursales_disponibles"][0]["id"] == 1
    assert data["sucursales_disponibles"][0]["es_sucursal_asignada"] is True


@pytest.mark.asyncio
async def test_hu09_no_requiere_autenticacion(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """La consulta es parte de la experiencia pública: sin iniciar sesión."""
    await _crear_envio(db_session, token="ENV-PUBLICO001")

    resp = await client.get(f"{OPCIONES}/ENV-PUBLICO001")

    assert resp.status_code == 200
    assert resp.json()["data"]["aplica_retiro"] is True


@pytest.mark.asyncio
async def test_hu09_lista_las_otras_sucursales_de_la_misma_ciudad(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Además de la asignada, se ofrecen las otras sucursales de esa ciudad como
    referencia de la red cercana, marcadas como no asignadas."""
    db_session.add(
        SucursalModel(
            id=3,
            nombre="Sucursal Test Córdoba Sur",
            provincia="Córdoba",
            ciudad="Córdoba",
            direccion="Bv. Sur 900",
            latitud=-31.45,
            longitud=-64.2,
        )
    )
    await db_session.commit()
    await _crear_envio(db_session, token="ENV-MISMACIU1", sucursal_destino_id=1)

    resp = await client.get(f"{OPCIONES}/ENV-MISMACIU1")

    assert resp.status_code == 200
    disponibles = resp.json()["data"]["sucursales_disponibles"]
    assert [s["id"] for s in disponibles] == [1, 3]
    assert disponibles[0]["es_sucursal_asignada"] is True
    assert disponibles[1]["es_sucursal_asignada"] is False
    # No se cuela una sucursal de otra ciudad (Rosario, id 2)
    assert 2 not in [s["id"] for s in disponibles]


@pytest.mark.asyncio
async def test_hu09_informa_el_estado_de_cada_paquete_del_envio(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Se informa si cada paquete ya llegó a la sucursal o todavía está en camino."""
    await _crear_envio(
        db_session,
        token="ENV-ESTADOS01",
        estados_paquetes=[
            EstadoPaqueteEnum.LISTO_PARA_RETIRO.value,
            EstadoPaqueteEnum.EN_TRANSITO.value,
        ],
    )

    resp = await client.get(f"{OPCIONES}/ENV-ESTADOS01")

    assert resp.status_code == 200
    paquetes = resp.json()["data"]["paquetes"]
    assert len(paquetes) == 2

    listo = next(p for p in paquetes if p["estado"] == EstadoPaqueteEnum.LISTO_PARA_RETIRO.value)
    assert listo["disponible_para_retirar"] is True

    en_camino = next(p for p in paquetes if p["estado"] == EstadoPaqueteEnum.EN_TRANSITO.value)
    assert en_camino["disponible_para_retirar"] is False


@pytest.mark.asyncio
async def test_hu09_un_paquete_recien_registrado_no_se_anuncia_como_retirable(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Un paquete "Pendiente" todavía no salió de la terminal de origen: la vista
    pública no debe invitar al destinatario a pasar a buscarlo."""
    await _crear_envio(db_session, token="ENV-PENDIENT1", estados_paquetes=["Pendiente"])

    resp = await client.get(f"{OPCIONES}/ENV-PENDIENT1")

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["aplica_retiro"] is True
    assert data["paquetes"][0]["disponible_para_retirar"] is False


@pytest.mark.asyncio
async def test_hu09_informa_los_requisitos_para_retirar(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Los requisitos son los mismos que exige el mostrador en HU13."""
    await _crear_envio(db_session, token="ENV-REQUISIT1")

    resp = await client.get(f"{OPCIONES}/ENV-REQUISIT1")

    assert resp.status_code == 200
    requisitos = resp.json()["data"]["requisitos_retiro"]
    assert "documento de identidad original" in requisitos["titular"]
    assert "16 años" in requisitos["titular"]
    assert "autorización de retiro" in requisitos["tercero_autorizado"]


# --- Condición negativa del escenario: el envío es a domicilio ---


@pytest.mark.asyncio
async def test_hu09_envio_a_domicilio_no_ofrece_sucursales(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """"...y no para entrega a domicilio": si es a domicilio se responde 200 con
    el motivo y sin sucursales, porque el token es válido igual."""
    await _crear_envio(db_session, token="ENV-DOMICILI1", tipo_entrega="domicilio")

    resp = await client.get(f"{OPCIONES}/ENV-DOMICILI1")

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["tipo_entrega"] == "domicilio"
    assert data["aplica_retiro"] is False
    assert "domicilio" in data["motivo_no_aplica"]
    assert data["sucursal_asignada"] is None
    assert data["sucursales_disponibles"] == []
    assert data["paquetes"] == []


@pytest.mark.asyncio
async def test_hu09_token_inexistente_devuelve_404(client: AsyncClient):
    """Un token que no existe no devuelve datos de ningún envío."""
    resp = await client.get(f"{OPCIONES}/ENV-NOEXISTE1")

    assert resp.status_code == 404
    cuerpo = resp.json()
    assert cuerpo["code"] == ErrorCodes.NOT_FOUND
    assert "data" not in cuerpo


@pytest.mark.asyncio
async def test_hu09_no_expone_datos_de_contacto_en_la_vista_publica(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """El endpoint es público: no debe filtrar email, teléfono ni documento,
    igual que la consulta de seguimiento de HU04."""
    await _crear_envio(db_session, token="ENV-PRIVACID1")

    resp = await client.get(f"{OPCIONES}/ENV-PRIVACID1")

    assert resp.status_code == 200
    cuerpo_crudo = resp.text
    assert "pablo.destinatario@test.com" not in cuerpo_crudo
    assert "sofia.remitente@test.com" not in cuerpo_crudo
    assert "+543564777888" not in cuerpo_crudo
    assert "30555666" not in cuerpo_crudo


# --- Catálogo filtrable que alimenta la vista pública ---


@pytest.mark.asyncio
async def test_hu09_catalogo_sin_filtros_devuelve_todas_las_sucursales(client: AsyncClient):
    """Sin filtros el catálogo se comporta igual que antes de HU09 (compatibilidad
    con el selector de retiro en sucursal de HU03)."""
    resp = await client.get(CATALOGO)

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 2
    # Ordenado por nombre
    assert [s["nombre"] for s in data] == ["Sucursal Test Centro", "Sucursal Test Norte"]


@pytest.mark.asyncio
async def test_hu09_catalogo_filtra_por_provincia_y_ciudad(client: AsyncClient):
    """El usuario que espera un paquete puede filtrar las sucursales de su zona."""
    resp_provincia = await client.get(CATALOGO, params={"provincia": "Santa Fe"})
    assert resp_provincia.status_code == 200
    assert [s["nombre"] for s in resp_provincia.json()["data"]] == ["Sucursal Test Norte"]

    resp_ciudad = await client.get(CATALOGO, params={"ciudad": "Córdoba"})
    assert resp_ciudad.status_code == 200
    assert [s["nombre"] for s in resp_ciudad.json()["data"]] == ["Sucursal Test Centro"]

    resp_ambos = await client.get(
        CATALOGO, params={"provincia": "Santa Fe", "ciudad": "Rosario"}
    )
    assert resp_ambos.status_code == 200
    assert len(resp_ambos.json()["data"]) == 1


@pytest.mark.asyncio
async def test_hu09_catalogo_filtra_sin_distinguir_mayusculas(client: AsyncClient):
    """Los filtros no dependen de cómo escriba el usuario la provincia o ciudad."""
    resp = await client.get(CATALOGO, params={"provincia": "  santa fe  ", "ciudad": "ROSARIO"})

    assert resp.status_code == 200
    assert len(resp.json()["data"]) == 1
    assert resp.json()["data"][0]["nombre"] == "Sucursal Test Norte"


@pytest.mark.asyncio
async def test_hu09_catalogo_sin_coincidencias_devuelve_lista_vacia(client: AsyncClient):
    """Una zona sin sucursales devuelve 200 con la lista vacía, no un error."""
    resp = await client.get(CATALOGO, params={"ciudad": "Ushuaia"})

    assert resp.status_code == 200
    assert resp.json()["data"] == []


# --- Integración con HU06: la recepción cambia lo que ve el destinatario ---


@pytest.mark.asyncio
async def test_hu09_refleja_el_avance_del_paquete_tras_llegar_a_la_sucursal(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Cuando el paquete pasa a estar en la sucursal de destino, la vista pública
    de HU09 lo anuncia como retirable."""
    envio = await _crear_envio(db_session, token="ENV-AVANCE001", estados_paquetes=["Pendiente"])

    antes = await client.get(f"{OPCIONES}/ENV-AVANCE001")
    assert antes.json()["data"]["paquetes"][0]["disponible_para_retirar"] is False

    paquete = envio.paquetes[0]
    paquete.estado = EstadoPaqueteEnum.LISTO_PARA_RETIRO.value
    paquete.sucursal_actual_id = 1
    await db_session.commit()

    despues = await client.get(f"{OPCIONES}/ENV-AVANCE001")
    assert despues.json()["data"]["paquetes"][0]["disponible_para_retirar"] is True
