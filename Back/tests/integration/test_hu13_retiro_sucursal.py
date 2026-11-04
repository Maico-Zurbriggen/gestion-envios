import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.constants.error_codes import ErrorCodes
from app.domain.constants.estados_logistica import (
    EstadoPaqueteEnum,
    ResultadoEventoEntregaEnum,
    TipoEventoEntregaEnum,
)
from app.domain.constants.scopes import ScopeEnum
from app.infrastructure.auth.jwt_handler import ManejadorJWT
from app.infrastructure.db.models import (
    EnvioModel,
    EventoEntregaModel,
    HistorialEstadoPaqueteModel,
    PaqueteModel,
    UsuarioModel,
)


async def _crear_paquete_test(
    db: AsyncSession,
    estado: str = EstadoPaqueteEnum.LISTO_PARA_RETIRO.value,
    numero_paquete: str = "PAQ-TEST123456",
) -> PaqueteModel:
    envio = EnvioModel(
        remitente_nombre="Juan Remitente",
        remitente_documento="30111222",
        remitente_telefono="+543564111222",
        remitente_email="remitente@test.com",
        destinatario_nombre="María Destinataria",
        destinatario_telefono="+543564333444",
        destinatario_email="destinataria@test.com",
        tipo_entrega="sucursal",
        sucursal_destino_id=1,
        terminos_aceptados=True,
        token_seguimiento="ENV-TEST123456",
    )
    db.add(envio)
    await db.commit()
    await db.refresh(envio)

    paquete = PaqueteModel(
        envio_id=envio.id,
        numero_paquete=numero_paquete,
        descripcion="Caja con libros",
        peso_kg=2.5,
        largo_cm=20.0,
        ancho_cm=15.0,
        alto_cm=10.0,
        estado=estado,
        sucursal_actual_id=1,
    )
    db.add(paquete)
    await db.commit()
    await db.refresh(paquete)
    return paquete


@pytest.mark.asyncio
async def test_hu13_seguridad_requiere_autenticacion_y_rol_administrativo(
    client: AsyncClient,
    vendedor_token: str,
    administrativo_token: str,
    db_session: AsyncSession,
):
    """HU13: Los endpoints de sucursal requieren rol ADMINISTRATIVO o SUPERADMIN."""
    paquete = await _crear_paquete_test(db_session, numero_paquete="PAQ-SEG001")

    # 1. Sin Token -> 401
    resp_no_auth = await client.get(f"/api/v1/sucursal/paquetes/{paquete.id}/validar-retiro")
    assert resp_no_auth.status_code == 401
    assert resp_no_auth.json()["code"] == ErrorCodes.INVALID_TOKEN

    # 2. Token con Rol No Permitido (VENDEDOR) -> 403
    headers_vendedor = {"Authorization": f"Bearer {vendedor_token}"}
    resp_vendedor = await client.get(
        f"/api/v1/sucursal/paquetes/{paquete.id}/validar-retiro",
        headers=headers_vendedor,
    )
    assert resp_vendedor.status_code == 403
    assert resp_vendedor.json()["code"] == ErrorCodes.FORBIDDEN_ACCESS

    # 3. Token con Scope Restringido (PASSWORD_RESET_ONLY) -> 403
    token_reset = ManejadorJWT.emitir_token(
        usuario_id="00000000-0000-0000-0000-000000000001",
        rol="ADMINISTRATIVO",
        scope=ScopeEnum.PASSWORD_RESET_ONLY.value,
    )
    resp_reset = await client.get(
        f"/api/v1/sucursal/paquetes/{paquete.id}/validar-retiro",
        headers={"Authorization": f"Bearer {token_reset}"},
    )
    assert resp_reset.status_code == 403
    assert resp_reset.json()["code"] == ErrorCodes.FORBIDDEN_SCOPE

    # 4. Token con Rol ADMINISTRATIVO -> 200
    headers_admin = {"Authorization": f"Bearer {administrativo_token}"}
    resp_admin = await client.get(
        f"/api/v1/sucursal/paquetes/{paquete.id}/validar-retiro",
        headers=headers_admin,
    )
    assert resp_admin.status_code == 200


@pytest.mark.asyncio
async def test_hu13_validar_retiro_por_uuid_y_por_numero_paquete(
    client: AsyncClient,
    administrativo_token: str,
    db_session: AsyncSession,
):
    """HU13: Permite buscar y validar el paquete tanto por UUID como por numero_paquete (código de barras)."""
    headers = {"Authorization": f"Bearer {administrativo_token}"}
    paquete = await _crear_paquete_test(
        db_session,
        estado=EstadoPaqueteEnum.LISTO_PARA_RETIRO.value,
        numero_paquete="PAQ-BUSQUEDA1",
    )

    # Búsqueda por UUID
    resp_uuid = await client.get(
        f"/api/v1/sucursal/paquetes/{paquete.id}/validar-retiro",
        headers=headers,
    )
    assert resp_uuid.status_code == 200
    data_uuid = resp_uuid.json()["data"]
    assert data_uuid["paquete_id"] == str(paquete.id)
    assert data_uuid["disponible_para_retiro"] is True
    assert data_uuid["datos_destinatario"]["nombre"] == "María Destinataria"

    # Búsqueda por Código (PAQ-BUSQUEDA1)
    resp_cod = await client.get(
        "/api/v1/sucursal/paquetes/PAQ-BUSQUEDA1/validar-retiro",
        headers=headers,
    )
    assert resp_cod.status_code == 200
    data_cod = resp_cod.json()["data"]
    assert data_cod["paquete_id"] == str(paquete.id)
    assert data_cod["numero_paquete"] == "PAQ-BUSQUEDA1"
    assert data_cod["disponible_para_retiro"] is True

    # Igual que en HU06: lo que emite el lector (minúsculas, espacios) se normaliza
    resp_lector = await client.get(
        "/api/v1/sucursal/paquetes/%20paq-busqueda1%20/validar-retiro",
        headers=headers,
    )
    assert resp_lector.status_code == 200
    assert resp_lector.json()["data"]["paquete_id"] == str(paquete.id)


@pytest.mark.asyncio
async def test_hu13_validar_retiro_paquete_no_encontrado(
    client: AsyncClient,
    administrativo_token: str,
):
    """HU13: Paquete inexistente retorna 404."""
    headers = {"Authorization": f"Bearer {administrativo_token}"}
    resp = await client.get(
        "/api/v1/sucursal/paquetes/PAQ-INEXISTENTE/validar-retiro",
        headers=headers,
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == ErrorCodes.NOT_FOUND


@pytest.mark.asyncio
async def test_hu13_validar_retiro_paquete_no_disponible(
    client: AsyncClient,
    administrativo_token: str,
    db_session: AsyncSession,
):
    """HU13: Paquete en tránsito o ya entregado indica disponible_para_retiro = False."""
    headers = {"Authorization": f"Bearer {administrativo_token}"}
    paquete_transito = await _crear_paquete_test(
        db_session,
        estado=EstadoPaqueteEnum.EN_TRANSITO.value,
        numero_paquete="PAQ-TRANSITO1",
    )

    resp = await client.get(
        f"/api/v1/sucursal/paquetes/{paquete_transito.id}/validar-retiro",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["disponible_para_retiro"] is False
    assert "EN_TRANSITO" in data["motivo_no_disponible"]


@pytest.mark.asyncio
async def test_hu13_escenario_1_retiro_titular_exitoso(
    client: AsyncClient,
    administrativo_token: str,
    administrativo_usuario: UsuarioModel,
    db_session: AsyncSession,
):
    """HU13 - Escenario 1: Retiro presencial por titular mayor de 16 años."""
    headers = {"Authorization": f"Bearer {administrativo_token}"}
    paquete = await _crear_paquete_test(
        db_session,
        estado=EstadoPaqueteEnum.LISTO_PARA_RETIRO.value,
        numero_paquete="PAQ-TITULAR01",
    )

    payload = {
        "tipo_retiro": "TITULAR",
        "documento_presentado": {
            "tipo": "DNI",
            "numero": "40123456",
        },
        "destinatario_mayor_16": True,
        "sucursal_id": 1,
        "receptor_fecha_nacimiento": "1990-05-10",
        "documento_original_verificado": True,
        "observaciones": "Entrega realizada en ventanilla 2",
    }

    resp = await client.post(
        f"/api/v1/sucursal/paquetes/{paquete.id}/registrar-retiro",
        json=payload,
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]

    assert data["paquete_id"] == str(paquete.id)
    assert data["estado"] == EstadoPaqueteEnum.ENTREGADO_EN_SUCURSAL.value
    assert data["tipo_retiro"] == "TITULAR"
    assert data["receptor_nombre"] == "María Destinataria"
    assert data["receptor_documento"] == "40123456"
    assert data["es_autorizado"] is False
    assert data["usuario_administrativo_id"] == str(administrativo_usuario.id)
    assert data["observaciones"] == "Entrega realizada en ventanilla 2"

    # Verificar que el paquete en BD cambió a ENTREGADO_EN_SUCURSAL
    paquete_bd = await db_session.get(PaqueteModel, paquete.id)
    assert paquete_bd.estado == EstadoPaqueteEnum.ENTREGADO_EN_SUCURSAL.value

    # Verificar registro en eventos_entrega
    stmt_evento = select(EventoEntregaModel).where(EventoEntregaModel.paquete_id == paquete.id)
    evento = (await db_session.execute(stmt_evento)).scalar_one()
    assert evento.tipo_evento == TipoEventoEntregaEnum.RETIRO_SUCURSAL.value
    assert evento.resultado == ResultadoEventoEntregaEnum.EXITOSO.value
    assert evento.es_autorizado is False
    assert evento.usuario_registro_id == administrativo_usuario.id

    # Verificar registro en historial_estados_paquete
    stmt_hist = select(HistorialEstadoPaqueteModel).where(HistorialEstadoPaqueteModel.paquete_id == paquete.id)
    hist = (await db_session.execute(stmt_hist)).scalar_one()
    assert hist.estado_nuevo == EstadoPaqueteEnum.ENTREGADO_EN_SUCURSAL.value
    assert hist.usuario_id == administrativo_usuario.id


@pytest.mark.asyncio
async def test_hu13_escenario_1_titular_menor_16_es_rechazado(
    client: AsyncClient,
    administrativo_token: str,
    db_session: AsyncSession,
):
    """HU13 - Escenario 1: Rechazo si el destinatario es menor de 16 años."""
    headers = {"Authorization": f"Bearer {administrativo_token}"}
    paquete = await _crear_paquete_test(
        db_session,
        estado=EstadoPaqueteEnum.LISTO_PARA_RETIRO.value,
        numero_paquete="PAQ-MENOR16",
    )

    payload = {
        "tipo_retiro": "TITULAR",
        "documento_presentado": {
            "tipo": "DNI",
            "numero": "45123456",
        },
        "destinatario_mayor_16": False,
        "sucursal_id": 1,
        "receptor_fecha_nacimiento": "1990-05-10",
        "documento_original_verificado": True,
    }

    resp = await client.post(
        f"/api/v1/sucursal/paquetes/{paquete.id}/registrar-retiro",
        json=payload,
        headers=headers,
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == ErrorCodes.VALIDATION_ERROR
    campos = [e["field"] for e in resp.json()["errors"]]
    assert "destinatario_mayor_16" in campos


@pytest.mark.asyncio
async def test_hu13_escenario_2_retiro_tercero_autorizado_exitoso(
    client: AsyncClient,
    administrativo_token: str,
    administrativo_usuario: UsuarioModel,
    db_session: AsyncSession,
):
    """HU13 - Escenario 2: Retiro por tercero autorizado con todos los recaudos completos."""
    headers = {"Authorization": f"Bearer {administrativo_token}"}
    paquete = await _crear_paquete_test(
        db_session,
        estado=EstadoPaqueteEnum.EN_SUCURSAL.value,
        numero_paquete="PAQ-TERCERO01",
    )

    payload = {
        "tipo_retiro": "TERCERO_AUTORIZADO",
        "documento_presentado": {
            "tipo": "DNI",
            "numero": "38999888",
        },
        "destinatario_mayor_16": True,
        "sucursal_id": 1,
        "receptor_fecha_nacimiento": "1990-05-10",
        "documento_original_verificado": True,
        "tercero_autorizado": {
            "nombre_completo": "Juan Pérez",
            "documento": "38999888",
            "posee_copia_dni_titular": True,
            "posee_nota_autorizacion": True,
        },
        "observaciones": "Presenta nota con firma certificada",
    }

    resp = await client.post(
        f"/api/v1/sucursal/paquetes/{paquete.numero_paquete}/registrar-retiro",
        json=payload,
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]

    assert data["tipo_retiro"] == "TERCERO_AUTORIZADO"
    assert data["receptor_nombre"] == "Juan Pérez"
    assert data["receptor_documento"] == "38999888"
    assert data["es_autorizado"] is True

    # Verificar en BD el evento de entrega
    stmt_evento = select(EventoEntregaModel).where(EventoEntregaModel.paquete_id == paquete.id)
    evento = (await db_session.execute(stmt_evento)).scalar_one()
    assert evento.es_autorizado is True
    assert evento.receptor_nombre == "Juan Pérez"
    assert evento.documento_destinatario_verificado is True


@pytest.mark.asyncio
async def test_hu13_escenario_2_tercero_sin_copia_dni_es_rechazado(
    client: AsyncClient,
    administrativo_token: str,
    db_session: AsyncSession,
):
    """HU13 - Escenario 2: Rechazo si el tercero no presenta copia del documento del titular."""
    headers = {"Authorization": f"Bearer {administrativo_token}"}
    paquete = await _crear_paquete_test(db_session, numero_paquete="PAQ-SINCOPIA")

    payload = {
        "tipo_retiro": "TERCERO_AUTORIZADO",
        "documento_presentado": {"tipo": "DNI", "numero": "38999888"},
        "destinatario_mayor_16": True,
        "sucursal_id": 1,
        "receptor_fecha_nacimiento": "1990-05-10",
        "documento_original_verificado": True,
        "tercero_autorizado": {
            "nombre_completo": "Juan Pérez",
            "documento": "38999888",
            "posee_copia_dni_titular": False,
            "posee_nota_autorizacion": True,
        },
    }

    resp = await client.post(
        f"/api/v1/sucursal/paquetes/{paquete.id}/registrar-retiro",
        json=payload,
        headers=headers,
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == ErrorCodes.VALIDATION_ERROR
    campos = [e["field"] for e in resp.json()["errors"]]
    assert "tercero_autorizado.posee_copia_dni_titular" in campos


@pytest.mark.asyncio
async def test_hu13_escenario_2_tercero_sin_nota_autorizacion_es_rechazado(
    client: AsyncClient,
    administrativo_token: str,
    db_session: AsyncSession,
):
    """HU13 - Escenario 2: Rechazo si el tercero no presenta la nota de autorización firmada."""
    headers = {"Authorization": f"Bearer {administrativo_token}"}
    paquete = await _crear_paquete_test(db_session, numero_paquete="PAQ-SINNOTA")

    payload = {
        "tipo_retiro": "TERCERO_AUTORIZADO",
        "documento_presentado": {"tipo": "DNI", "numero": "38999888"},
        "destinatario_mayor_16": True,
        "sucursal_id": 1,
        "receptor_fecha_nacimiento": "1990-05-10",
        "documento_original_verificado": True,
        "tercero_autorizado": {
            "nombre_completo": "Juan Pérez",
            "documento": "38999888",
            "posee_copia_dni_titular": True,
            "posee_nota_autorizacion": False,
        },
    }

    resp = await client.post(
        f"/api/v1/sucursal/paquetes/{paquete.id}/registrar-retiro",
        json=payload,
        headers=headers,
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == ErrorCodes.VALIDATION_ERROR
    campos = [e["field"] for e in resp.json()["errors"]]
    assert "tercero_autorizado.posee_nota_autorizacion" in campos


@pytest.mark.asyncio
async def test_hu13_reintento_retiro_paquete_ya_entregado(
    client: AsyncClient,
    administrativo_token: str,
    db_session: AsyncSession,
):
    """HU13: No se puede retirar un paquete que ya fue entregado previamente."""
    headers = {"Authorization": f"Bearer {administrativo_token}"}
    paquete_ya_retirado = await _crear_paquete_test(
        db_session,
        estado=EstadoPaqueteEnum.ENTREGADO_EN_SUCURSAL.value,
        numero_paquete="PAQ-YARETIRADO",
    )

    payload = {
        "tipo_retiro": "TITULAR",
        "documento_presentado": {"tipo": "DNI", "numero": "40123456"},
        "destinatario_mayor_16": True,
        "sucursal_id": 1,
        "receptor_fecha_nacimiento": "1990-05-10",
        "documento_original_verificado": True,
    }

    resp = await client.post(
        f"/api/v1/sucursal/paquetes/{paquete_ya_retirado.id}/registrar-retiro",
        json=payload,
        headers=headers,
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == ErrorCodes.VALIDATION_ERROR


def _payload_titular(**cambios) -> dict:
    payload = {
        "tipo_retiro": "TITULAR",
        "documento_presentado": {"tipo": "DNI", "numero": "40123456"},
        "destinatario_mayor_16": True,
        "sucursal_id": 1,
        "receptor_fecha_nacimiento": "1990-05-10",
        "documento_original_verificado": True,
    }
    payload.update(cambios)
    return payload


async def _retirar(client: AsyncClient, token: str, paquete: PaqueteModel, payload: dict):
    return await client.post(
        f"/api/v1/sucursal/paquetes/{paquete.numero_paquete}/registrar-retiro",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("estado", ["Pendiente", EstadoPaqueteEnum.PENDIENTE.value, EstadoPaqueteEnum.EN_SUCURSAL_ORIGEN.value])
async def test_hu13_paquete_que_no_llego_a_la_sucursal_no_se_retira(
    client: AsyncClient, administrativo_token: str, db_session: AsyncSession, estado: str
):
    """El backend (no solo la pantalla) impide retirar un paquete que nunca ingresó a la sucursal."""
    paquete = await _crear_paquete_test(db_session, estado=estado, numero_paquete="PAQ-PENDIENTE1")
    resp = await _retirar(client, administrativo_token, paquete, _payload_titular())
    assert resp.status_code == 400
    assert "estado" in [e["field"] for e in resp.json()["errors"]]
    await db_session.refresh(paquete)
    assert paquete.estado == estado


@pytest.mark.asyncio
async def test_hu13_envio_a_domicilio_no_se_retira_en_sucursal(
    client: AsyncClient, administrativo_token: str, db_session: AsyncSession
):
    """Un envío a domicilio que espera el reparto no se retira en sucursal; solo
    cuando agota las visitas queda «listo para retirar» en la sucursal donde está."""
    paquete = await _crear_paquete_test(
        db_session, numero_paquete="PAQ-DOMICILIO1", estado=EstadoPaqueteEnum.EN_SUCURSAL_DESTINO.value
    )
    envio = await db_session.get(EnvioModel, paquete.envio_id)
    envio.tipo_entrega = "domicilio"
    await db_session.commit()
    resp = await _retirar(client, administrativo_token, paquete, _payload_titular())
    assert resp.status_code == 400
    assert "tipo_entrega" in [e["field"] for e in resp.json()["errors"]]

    paquete.estado = EstadoPaqueteEnum.LISTO_PARA_RETIRO.value
    await db_session.commit()
    resp = await _retirar(client, administrativo_token, paquete, _payload_titular())
    assert resp.status_code == 200, "tras las visitas sin éxito se retira en la sucursal donde quedó"


@pytest.mark.asyncio
async def test_hu13_rechaza_retiro_en_otra_sucursal(
    client: AsyncClient, administrativo_token: str, db_session: AsyncSession
):
    paquete = await _crear_paquete_test(db_session, numero_paquete="PAQ-OTRASUC01")
    resp = await _retirar(client, administrativo_token, paquete, _payload_titular(sucursal_id=2))
    assert resp.status_code == 400
    assert "sucursal_id" in [e["field"] for e in resp.json()["errors"]]

    # Paquete que quedó en otra sucursal que la elegida para el retiro.
    paquete.sucursal_actual_id = 2
    await db_session.commit()
    resp = await _retirar(client, administrativo_token, paquete, _payload_titular())
    assert resp.status_code == 400
    assert "sucursal_actual" in [e["field"] for e in resp.json()["errors"]]

    validacion = await client.get(
        f"/api/v1/sucursal/paquetes/{paquete.numero_paquete}/validar-retiro",
        headers={"Authorization": f"Bearer {administrativo_token}"},
    )
    assert validacion.json()["data"]["disponible_para_retiro"] is False


@pytest.mark.asyncio
async def test_hu13_quien_retira_debe_ser_mayor_de_16_y_mostrar_documento(
    client: AsyncClient, administrativo_token: str, db_session: AsyncSession
):
    from datetime import date

    hoy = date.today()
    cumple_16_hoy = hoy.replace(year=hoy.year - 16) if not (hoy.month == 2 and hoy.day == 29) else date(hoy.year - 16, 3, 1)
    paquete = await _crear_paquete_test(db_session, numero_paquete="PAQ-EDAD00001")
    resp = await _retirar(
        client,
        administrativo_token,
        paquete,
        _payload_titular(receptor_fecha_nacimiento=cumple_16_hoy.isoformat(), documento_original_verificado=False),
    )
    assert resp.status_code == 400
    campos = [e["field"] for e in resp.json()["errors"]]
    assert "receptor_fecha_nacimiento" in campos and "documento_original_verificado" in campos


@pytest.mark.asyncio
async def test_hu13_tercero_con_documento_distinto_al_presentado(
    client: AsyncClient, administrativo_token: str, db_session: AsyncSession
):
    paquete = await _crear_paquete_test(db_session, numero_paquete="PAQ-TERCERO02")
    payload = _payload_titular(
        tipo_retiro="TERCERO_AUTORIZADO",
        documento_presentado={"tipo": "DNI", "numero": "38999888"},
        tercero_autorizado={
            "nombre_completo": "Juan Pérez",
            "documento": "11111111",
            "posee_copia_dni_titular": True,
            "posee_nota_autorizacion": True,
        },
    )
    resp = await _retirar(client, administrativo_token, paquete, payload)
    assert resp.status_code == 400
    assert "tercero_autorizado.documento" in [e["field"] for e in resp.json()["errors"]]


@pytest.mark.asyncio
async def test_hu13_constancia_y_seguimiento_publico_reflejan_el_retiro(
    client: AsyncClient, administrativo_token: str, db_session: AsyncSession
):
    paquete = await _crear_paquete_test(db_session, numero_paquete="PAQ-CONSTANC1")
    resp = await _retirar(client, administrativo_token, paquete, _payload_titular())
    assert resp.status_code == 200, resp.text

    evento = (await db_session.execute(select(EventoEntregaModel))).scalar_one()
    assert evento.receptor_fecha_nacimiento.isoformat() == "1990-05-10"
    assert evento.documento_destinatario_verificado is True
    assert evento.sucursal_id == 1

    publico = (await client.get("/api/v1/seguimiento/ENV-TEST123456")).json()["data"]
    assert publico["tipo_entrega"] == "sucursal"
    ultimo = publico["paquetes"][0]["historial"][-1]
    assert ultimo["estado"] == EstadoPaqueteEnum.ENTREGADO_EN_SUCURSAL.value
    assert ultimo["descripcion"] == "Retirado en sucursal."
    assert "40123456" not in str(publico)


@pytest.mark.asyncio
async def test_hu13_retiro_simultaneo_solo_se_registra_una_vez(
    client: AsyncClient, administrativo_usuario: UsuarioModel, db_session: AsyncSession
):
    """Dos mostradores leen el paquete disponible antes de que el otro confirme: solo uno lo entrega."""
    from datetime import date

    from app.application.services.servicio_retiro_sucursal import ServicioRetiroSucursal
    from app.contracts.sucursal_retiro import RegistrarRetiroRequest
    from app.core.exceptions import DuplicateEntryException
    from app.infrastructure.repositories.repositorio_entregas import RepositorioEntregas

    paquete = await _crear_paquete_test(db_session, numero_paquete="PAQ-CARRERA01")
    repo = RepositorioEntregas(db_session)
    leido_antes = await repo.buscar_paquete_por_id_o_codigo(paquete.numero_paquete)
    instantanea = {"estado": leido_antes.estado}

    class RepoConLecturaVieja(RepositorioEntregas):
        async def buscar_paquete_por_id_o_codigo(self, id_o_codigo):
            encontrado = await super().buscar_paquete_por_id_o_codigo(id_o_codigo)
            self.db.expunge(encontrado)  # copia leída antes de que el otro mostrador confirmara
            encontrado.estado = instantanea["estado"]
            return encontrado

    datos = RegistrarRetiroRequest(**_payload_titular())
    servicio = ServicioRetiroSucursal(RepoConLecturaVieja(db_session))
    await servicio.registrar_retiro(paquete.numero_paquete, datos, administrativo_usuario)
    with pytest.raises(DuplicateEntryException):
        await servicio.registrar_retiro(paquete.numero_paquete, datos, administrativo_usuario)

    eventos = (await db_session.execute(select(EventoEntregaModel))).scalars().all()
    assert len(eventos) == 1 and eventos[0].receptor_fecha_nacimiento == date(1990, 5, 10)
