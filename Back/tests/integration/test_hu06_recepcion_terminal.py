"""Tests de integración de HU06 — Recepción de paquetes en terminal por escaneo.

> Yo como vendedor / personal de la terminal deseo escanear el código de barras
> de la planilla del envío al recibir el paquete, para identificar el paquete
> precargado y dejarlo listo en la terminal para su envío.
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.constants.error_codes import ErrorCodes
from app.domain.constants.estados_logistica import EstadoPaqueteEnum
from app.domain.constants.scopes import ScopeEnum
from app.infrastructure.auth.jwt_handler import ManejadorJWT
from app.infrastructure.db.models import (
    EnvioModel,
    HistorialEstadoPaqueteModel,
    PaqueteModel,
)

BASE = "/api/v1/terminal/paquetes"


async def _crear_envio_precargado(
    db: AsyncSession,
    *,
    numero_paquete: str = "PAQ-TERMINAL01",
    token: str = "ENV-TERMINAL01",
    estado: str = "Pendiente",
    tipo_entrega: str = "sucursal",
) -> PaqueteModel:
    """Simula un envío ya precargado por HU03, con su paquete y su planilla."""
    envio = EnvioModel(
        remitente_nombre="Carlos Remitente",
        remitente_documento="30111222",
        remitente_telefono="+543564111222",
        remitente_email="carlos.remitente@test.com",
        destinatario_nombre="Ana Destinataria",
        destinatario_telefono="+543564333444",
        destinatario_email="ana.destinataria@test.com",
        tipo_entrega=tipo_entrega,
        sucursal_destino_id=2 if tipo_entrega == "sucursal" else None,
        provincia_destino="Córdoba" if tipo_entrega == "domicilio" else None,
        ciudad_destino="Córdoba" if tipo_entrega == "domicilio" else None,
        direccion_destino="Av. Siempre Viva 742" if tipo_entrega == "domicilio" else None,
        terminos_aceptados=True,
        token_seguimiento=token,
    )
    db.add(envio)
    await db.commit()
    await db.refresh(envio)

    paquete = PaqueteModel(
        envio_id=envio.id,
        numero_paquete=numero_paquete,
        descripcion="Caja con repuestos",
        peso_kg=4.5,
        largo_cm=40.0,
        ancho_cm=30.0,
        alto_cm=20.0,
        observaciones="Frágil",
        estado=estado,
    )
    db.add(paquete)
    await db.commit()
    await db.refresh(paquete)
    return paquete


# --- Seguridad y autorización ---


@pytest.mark.asyncio
async def test_hu06_seguridad_roles_habilitados_en_terminal(
    client: AsyncClient,
    db_session: AsyncSession,
    vendedor_token: str,
    administrativo_token: str,
    repartidor_token: str,
):
    """HU06: los endpoints de terminal exigen rol VENDEDOR, ADMINISTRATIVO o SUPERADMIN."""
    paquete = await _crear_envio_precargado(
        db_session, numero_paquete="PAQ-SEGURID001", token="ENV-SEGURID001"
    )

    # 1. Sin token -> 401
    resp_sin_auth = await client.get(f"{BASE}/{paquete.numero_paquete}/escanear")
    assert resp_sin_auth.status_code == 401
    assert resp_sin_auth.json()["code"] == ErrorCodes.INVALID_TOKEN

    # 2. Rol no habilitado (REPARTIDOR) -> 403
    resp_repartidor = await client.get(
        f"{BASE}/{paquete.numero_paquete}/escanear",
        headers={"Authorization": f"Bearer {repartidor_token}"},
    )
    assert resp_repartidor.status_code == 403
    assert resp_repartidor.json()["code"] == ErrorCodes.FORBIDDEN_ACCESS

    # 3. Token con scope restringido (primer acceso pendiente) -> 403
    token_reset = ManejadorJWT.emitir_token(
        usuario_id=str(uuid.uuid4()),
        rol="VENDEDOR",
        scope=ScopeEnum.PASSWORD_RESET_ONLY.value,
    )
    resp_reset = await client.get(
        f"{BASE}/{paquete.numero_paquete}/escanear",
        headers={"Authorization": f"Bearer {token_reset}"},
    )
    assert resp_reset.status_code == 403
    assert resp_reset.json()["code"] == ErrorCodes.FORBIDDEN_SCOPE

    # 4. Rol VENDEDOR (el de la historia) -> 200
    resp_vendedor = await client.get(
        f"{BASE}/{paquete.numero_paquete}/escanear",
        headers={"Authorization": f"Bearer {vendedor_token}"},
    )
    assert resp_vendedor.status_code == 200

    # 5. Rol ADMINISTRATIVO (sucursales chicas) -> 200
    resp_admin = await client.get(
        f"{BASE}/{paquete.numero_paquete}/escanear",
        headers={"Authorization": f"Bearer {administrativo_token}"},
    )
    assert resp_admin.status_code == 200


# --- Escenario 1: identificación del paquete precargado ---


@pytest.mark.asyncio
async def test_hu06_escenario_1_escaneo_identifica_el_paquete_precargado(
    client: AsyncClient,
    db_session: AsyncSession,
    vendedor_token: str,
):
    """HU06 Escenario 1: al escanear el código de barras, el sistema identifica
    el paquete registrado y muestra los datos del envío para contrastarlos."""
    paquete = await _crear_envio_precargado(
        db_session, numero_paquete="PAQ-ESCANEO001", token="ENV-ESCANEO001"
    )
    headers = {"Authorization": f"Bearer {vendedor_token}"}

    resp = await client.get(f"{BASE}/{paquete.numero_paquete}/escanear", headers=headers)

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["paquete_id"] == str(paquete.id)
    assert data["numero_paquete"] == "PAQ-ESCANEO001"
    assert data["descripcion"] == "Caja con repuestos"
    assert data["peso_kg"] == 4.5
    assert data["largo_cm"] == 40.0
    assert data["observaciones"] == "Frágil"
    assert data["estado_actual"] == "Pendiente"
    assert data["disponible_para_recepcion"] is True
    assert data["motivo_no_disponible"] is None
    # Todavía no fue recibido en ninguna terminal
    assert data["sucursal_actual"] is None

    envio = data["envio"]
    assert envio["token_seguimiento"] == "ENV-ESCANEO001"
    assert envio["remitente_nombre"] == "Carlos Remitente"
    assert envio["remitente_documento"] == "30111222"
    assert envio["destinatario_nombre"] == "Ana Destinataria"
    assert envio["tipo_entrega"] == "sucursal"
    assert envio["sucursal_destino"]["id"] == 2
    # El destino viene armado y sin duplicar el prefijo "Sucursal"
    assert envio["destino"] == "Sucursal Test Norte - Bv. Test 456, Rosario, Santa Fe"


@pytest.mark.asyncio
async def test_hu06_escaneo_arma_el_destino_a_domicilio(
    client: AsyncClient,
    db_session: AsyncSession,
    vendedor_token: str,
):
    """El destino se muestra como texto legible también para envíos a domicilio."""
    paquete = await _crear_envio_precargado(
        db_session,
        numero_paquete="PAQ-DOMICIL001",
        token="ENV-DOMICIL001",
        tipo_entrega="domicilio",
    )
    headers = {"Authorization": f"Bearer {vendedor_token}"}

    resp = await client.get(f"{BASE}/{paquete.numero_paquete}/escanear", headers=headers)

    assert resp.status_code == 200
    envio = resp.json()["data"]["envio"]
    assert envio["tipo_entrega"] == "domicilio"
    assert envio["sucursal_destino"] is None
    assert envio["destino"] == "Av. Siempre Viva 742, Córdoba, Córdoba"


@pytest.mark.asyncio
async def test_hu06_escaneo_acepta_uuid_y_normaliza_el_codigo_del_lector(
    client: AsyncClient,
    db_session: AsyncSession,
    vendedor_token: str,
):
    """El mismo endpoint resuelve el UUID del paquete y tolera lo que agrega el lector."""
    paquete = await _crear_envio_precargado(
        db_session, numero_paquete="PAQ-NORMALIZ01", token="ENV-NORMALIZ01"
    )
    headers = {"Authorization": f"Bearer {vendedor_token}"}

    # Por UUID
    resp_uuid = await client.get(f"{BASE}/{paquete.id}/escanear", headers=headers)
    assert resp_uuid.status_code == 200
    assert resp_uuid.json()["data"]["numero_paquete"] == "PAQ-NORMALIZ01"

    # En minúsculas (algunos lectores emiten así)
    resp_minuscula = await client.get(
        f"{BASE}/{paquete.numero_paquete.lower()}/escanear", headers=headers
    )
    assert resp_minuscula.status_code == 200
    assert resp_minuscula.json()["data"]["numero_paquete"] == "PAQ-NORMALIZ01"


@pytest.mark.asyncio
async def test_hu06_escaneo_de_codigo_inexistente_devuelve_404(
    client: AsyncClient,
    vendedor_token: str,
):
    """Una planilla que no corresponde a un envío registrado no identifica nada."""
    headers = {"Authorization": f"Bearer {vendedor_token}"}

    resp = await client.get(f"{BASE}/PAQ-NOEXISTE01/escanear", headers=headers)

    assert resp.status_code == 404
    cuerpo = resp.json()
    assert cuerpo["code"] == ErrorCodes.NOT_FOUND
    assert "PAQ-NOEXISTE01" in cuerpo["message"]
    assert "data" not in cuerpo


@pytest.mark.asyncio
async def test_hu06_escaneo_de_codigo_con_formato_invalido_devuelve_400(
    client: AsyncClient,
    vendedor_token: str,
):
    """Un token de seguimiento no es un código de paquete: se rechaza por formato."""
    headers = {"Authorization": f"Bearer {vendedor_token}"}

    resp = await client.get(f"{BASE}/ENV-ZPC5LB48JJ/escanear", headers=headers)

    assert resp.status_code == 400
    cuerpo = resp.json()
    assert cuerpo["code"] == ErrorCodes.VALIDATION_ERROR
    assert cuerpo["errors"][0]["field"] == "codigo"


# --- Escenario 1 (segunda parte): dejarlo registrado como listo para su envío ---


@pytest.mark.asyncio
async def test_hu06_escenario_1_recepcion_deja_el_paquete_listo_en_la_terminal(
    client: AsyncClient,
    db_session: AsyncSession,
    vendedor_token: str,
    vendedor_usuario,
):
    """HU06 Escenario 1: el sistema permite dejar el paquete registrado en la
    terminal como listo para su respectivo envío."""
    paquete = await _crear_envio_precargado(
        db_session, numero_paquete="PAQ-RECEPCION1", token="ENV-RECEPCION1"
    )
    headers = {"Authorization": f"Bearer {vendedor_token}"}

    resp = await client.post(
        f"{BASE}/{paquete.numero_paquete}/recepcionar",
        headers=headers,
        json={"sucursal_id": 1, "observaciones": "Caja en buen estado, sin golpes."},
    )

    assert resp.status_code == 200
    cuerpo = resp.json()
    assert cuerpo["status"] == "success"
    data = cuerpo["data"]
    assert data["numero_paquete"] == "PAQ-RECEPCION1"
    assert data["estado_anterior"] == "Pendiente"
    assert data["estado"] == EstadoPaqueteEnum.EN_SUCURSAL_ORIGEN.value
    assert data["sucursal_id"] == 1
    assert data["sucursal_nombre"] == "Sucursal Test Centro"
    assert data["usuario_receptor_id"] == str(vendedor_usuario.id)
    assert data["usuario_receptor_nombre"] == vendedor_usuario.nombre
    assert data["token_seguimiento"] == "ENV-RECEPCION1"
    assert data["observaciones"] == "Caja en buen estado, sin golpes."
    assert data["fecha_hora_recepcion"] is not None

    # El paquete queda ubicado en la terminal que lo recibió
    await db_session.refresh(paquete)
    assert paquete.estado == EstadoPaqueteEnum.EN_SUCURSAL_ORIGEN.value
    assert paquete.sucursal_actual_id == 1


@pytest.mark.asyncio
async def test_hu06_recepcion_registra_el_cambio_en_el_historial(
    client: AsyncClient,
    db_session: AsyncSession,
    vendedor_token: str,
    vendedor_usuario,
):
    """Cada recepción deja trazabilidad en `historial_estados_paquete`."""
    paquete = await _crear_envio_precargado(
        db_session, numero_paquete="PAQ-HISTORIAL1", token="ENV-HISTORIAL1"
    )
    headers = {"Authorization": f"Bearer {vendedor_token}"}

    resp = await client.post(
        f"{BASE}/{paquete.numero_paquete}/recepcionar",
        headers=headers,
        json={"sucursal_id": 1, "observaciones": "Recibido en mostrador"},
    )
    assert resp.status_code == 200

    filas = (
        await db_session.execute(
            select(HistorialEstadoPaqueteModel).where(
                HistorialEstadoPaqueteModel.paquete_id == paquete.id
            )
        )
    ).scalars().all()

    assert len(filas) == 1
    historial = filas[0]
    assert historial.estado_anterior == "Pendiente"
    assert historial.estado_nuevo == EstadoPaqueteEnum.EN_SUCURSAL_ORIGEN.value
    assert historial.usuario_id == vendedor_usuario.id
    assert historial.sucursal_id == 1
    assert "escaneo del código de barras" in historial.observacion
    assert "Recibido en mostrador" in historial.observacion
    # Las coordenadas de la terminal quedan asentadas en el evento
    assert historial.latitud == -31.4
    assert historial.longitud == -64.18


@pytest.mark.asyncio
async def test_hu06_recepcion_sin_observaciones_es_valida(
    client: AsyncClient,
    db_session: AsyncSession,
    vendedor_token: str,
):
    """Las observaciones del vendedor son opcionales."""
    paquete = await _crear_envio_precargado(
        db_session, numero_paquete="PAQ-SINOBSERV1", token="ENV-SINOBSERV1"
    )
    headers = {"Authorization": f"Bearer {vendedor_token}"}

    resp = await client.post(
        f"{BASE}/{paquete.numero_paquete}/recepcionar",
        headers=headers,
        json={"sucursal_id": 2},
    )

    assert resp.status_code == 200
    assert resp.json()["data"]["observaciones"] is None
    assert resp.json()["data"]["sucursal_id"] == 2


@pytest.mark.asyncio
async def test_hu06_no_permite_recibir_dos_veces_el_mismo_paquete(
    client: AsyncClient,
    db_session: AsyncSession,
    vendedor_token: str,
):
    """Un paquete ya ingresado a la red no puede volver a recibirse en terminal."""
    paquete = await _crear_envio_precargado(
        db_session, numero_paquete="PAQ-DUPLICADO1", token="ENV-DUPLICADO1"
    )
    headers = {"Authorization": f"Bearer {vendedor_token}"}
    cuerpo_peticion = {"sucursal_id": 1}

    primera = await client.post(
        f"{BASE}/{paquete.numero_paquete}/recepcionar", headers=headers, json=cuerpo_peticion
    )
    assert primera.status_code == 200

    segunda = await client.post(
        f"{BASE}/{paquete.numero_paquete}/recepcionar", headers=headers, json=cuerpo_peticion
    )
    assert segunda.status_code == 400
    cuerpo = segunda.json()
    assert cuerpo["code"] == ErrorCodes.VALIDATION_ERROR
    assert cuerpo["errors"][0]["field"] == "estado"
    assert "ya fue recibido" in cuerpo["errors"][0]["message"]


@pytest.mark.asyncio
async def test_hu06_no_permite_recibir_un_paquete_ya_entregado(
    client: AsyncClient,
    db_session: AsyncSession,
    vendedor_token: str,
):
    """Un paquete que ya cerró su ciclo (entregado/retirado) no reingresa."""
    paquete = await _crear_envio_precargado(
        db_session,
        numero_paquete="PAQ-ENTREGADO1",
        token="ENV-ENTREGADO1",
        estado=EstadoPaqueteEnum.ENTREGADO_EN_SUCURSAL.value,
    )
    headers = {"Authorization": f"Bearer {vendedor_token}"}

    resp = await client.post(
        f"{BASE}/{paquete.numero_paquete}/recepcionar", headers=headers, json={"sucursal_id": 1}
    )

    assert resp.status_code == 400
    assert "completó su ciclo" in resp.json()["errors"][0]["message"]


@pytest.mark.asyncio
async def test_hu06_escaneo_de_paquete_ya_recibido_informa_el_motivo(
    client: AsyncClient,
    db_session: AsyncSession,
    vendedor_token: str,
):
    """El escaneo de un paquete ya recibido responde 200 con el motivo, no un error:
    el vendedor necesita ver en pantalla qué pasó con ese paquete."""
    paquete = await _crear_envio_precargado(
        db_session,
        numero_paquete="PAQ-ENTRANSIT1",
        token="ENV-ENTRANSIT1",
        estado=EstadoPaqueteEnum.EN_TRANSITO.value,
    )
    headers = {"Authorization": f"Bearer {vendedor_token}"}

    resp = await client.get(f"{BASE}/{paquete.numero_paquete}/escanear", headers=headers)

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["disponible_para_recepcion"] is False
    assert "EN_TRANSITO" in data["motivo_no_disponible"]


@pytest.mark.asyncio
async def test_hu06_rechaza_una_sucursal_inexistente(
    client: AsyncClient,
    db_session: AsyncSession,
    vendedor_token: str,
):
    """La terminal informada tiene que existir en el catálogo de sucursales."""
    paquete = await _crear_envio_precargado(
        db_session, numero_paquete="PAQ-SUCINVALI1", token="ENV-SUCINVALI1"
    )
    headers = {"Authorization": f"Bearer {vendedor_token}"}

    resp = await client.post(
        f"{BASE}/{paquete.numero_paquete}/recepcionar", headers=headers, json={"sucursal_id": 9999}
    )

    # Una sucursal que no existe tampoco está entre las habilitadas del vendedor.
    assert resp.status_code == 403
    assert resp.json()["code"] == ErrorCodes.FORBIDDEN_ACCESS

    # El paquete no se modificó
    await db_session.refresh(paquete)
    assert paquete.estado == "Pendiente"
    assert paquete.sucursal_actual_id is None


@pytest.mark.asyncio
async def test_hu06_rechaza_un_cuerpo_sin_sucursal(
    client: AsyncClient,
    db_session: AsyncSession,
    vendedor_token: str,
):
    """`sucursal_id` es obligatorio y debe ser positivo (validación de contrato)."""
    paquete = await _crear_envio_precargado(
        db_session, numero_paquete="PAQ-SINSUCURS1", token="ENV-SINSUCURS1"
    )
    headers = {"Authorization": f"Bearer {vendedor_token}"}

    resp_sin_campo = await client.post(
        f"{BASE}/{paquete.numero_paquete}/recepcionar", headers=headers, json={}
    )
    assert resp_sin_campo.status_code == 400
    assert resp_sin_campo.json()["code"] == ErrorCodes.VALIDATION_ERROR

    resp_negativo = await client.post(
        f"{BASE}/{paquete.numero_paquete}/recepcionar", headers=headers, json={"sucursal_id": 0}
    )
    assert resp_negativo.status_code == 400
    assert resp_negativo.json()["code"] == ErrorCodes.VALIDATION_ERROR


# --- Integración con el seguimiento público de HU04 ---


@pytest.mark.asyncio
async def test_hu06_la_recepcion_se_refleja_en_el_seguimiento_publico(
    client: AsyncClient,
    db_session: AsyncSession,
    vendedor_token: str,
):
    """Tras la recepción, la consulta pública de HU04 muestra el nuevo estado."""
    paquete = await _crear_envio_precargado(
        db_session, numero_paquete="PAQ-SEGUIMIEN1", token="ENV-SEGUIMIEN1"
    )
    headers = {"Authorization": f"Bearer {vendedor_token}"}

    antes = await client.get("/api/v1/seguimiento/ENV-SEGUIMIEN1")
    assert antes.status_code == 200
    assert antes.json()["data"]["paquetes"][0]["estado"] == "Pendiente"

    recepcion = await client.post(
        f"{BASE}/{paquete.numero_paquete}/recepcionar", headers=headers, json={"sucursal_id": 1}
    )
    assert recepcion.status_code == 200

    despues = await client.get("/api/v1/seguimiento/ENV-SEGUIMIEN1")
    assert despues.status_code == 200
    assert (
        despues.json()["data"]["paquetes"][0]["estado"]
        == EstadoPaqueteEnum.EN_SUCURSAL_ORIGEN.value
    )


@pytest.mark.asyncio
async def test_hu06_recepcion_en_la_sucursal_de_retiro_queda_lista_para_retirar(
    client: AsyncClient, db_session: AsyncSession, vendedor_token: str, administrativo_token: str
):
    """Si el envío se retira en la misma sucursal que lo recibe, no hay recorrido que esperar:
    queda listo para retirar (HU09) y el mostrador de HU13 puede entregarlo."""
    paquete = await _crear_envio_precargado(db_session, numero_paquete="PAQ-MISMASUC01", token="ENV-MISMASUC1")
    resp = await client.post(
        f"{BASE}/{paquete.numero_paquete}/recepcionar",
        headers={"Authorization": f"Bearer {vendedor_token}"},
        json={"sucursal_id": 2},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["estado"] == EstadoPaqueteEnum.LISTO_PARA_RETIRO.value

    opciones = (await client.get("/api/v1/sucursales/opciones-retiro/ENV-MISMASUC1")).json()["data"]
    assert opciones["paquetes"][0]["disponible_para_retirar"] is True

    validacion = await client.get(
        f"/api/v1/sucursal/paquetes/{paquete.numero_paquete}/validar-retiro",
        headers={"Authorization": f"Bearer {administrativo_token}"},
    )
    assert validacion.json()["data"]["disponible_para_retiro"] is True


@pytest.mark.asyncio
async def test_hu06_recepcion_simultanea_solo_se_registra_una_vez(db_session: AsyncSession, vendedor_usuario):
    """Dos terminales escanean el mismo paquete antes de que la otra confirme: la segunda recibe 409."""
    from app.application.services.servicio_recepcion_terminal import ServicioRecepcionTerminal
    from app.contracts.recepcion_terminal import RecepcionarPaqueteRequest
    from app.core.exceptions import DuplicateEntryException
    from app.infrastructure.repositories.repositorio_recepciones import RepositorioRecepciones
    from app.infrastructure.repositories.repositorio_sucursales import RepositorioSucursales

    paquete = await _crear_envio_precargado(db_session, numero_paquete="PAQ-CARRERA002", token="ENV-CARRERA02")

    class RepoConLecturaVieja(RepositorioRecepciones):
        async def buscar_paquete_por_codigo(self, codigo):
            encontrado = await super().buscar_paquete_por_codigo(codigo)
            self.db.expunge(encontrado)  # copia leída antes de que la otra terminal confirmara
            encontrado.estado = "Pendiente"
            return encontrado

    servicio = ServicioRecepcionTerminal(RepoConLecturaVieja(db_session), RepositorioSucursales(db_session))
    datos = RecepcionarPaqueteRequest(sucursal_id=1)
    await servicio.recepcionar_paquete(paquete.numero_paquete, datos, vendedor_usuario)
    with pytest.raises(DuplicateEntryException):
        await servicio.recepcionar_paquete(paquete.numero_paquete, datos, vendedor_usuario)

    historial = (
        await db_session.execute(
            select(HistorialEstadoPaqueteModel).where(HistorialEstadoPaqueteModel.paquete_id == paquete.id)
        )
    ).scalars().all()
    assert len(historial) == 1
