from app.infrastructure.auth.hasher import HasherContrasenas


def test_generar_y_verificar_hash():
    """Verifica que el hasher BCrypt genere hashes válidos y los compruebe correctamente."""
    password = "MiPasswordSecreta123!"
    hash_generado = HasherContrasenas.generar_hash(password)

    assert hash_generado != password
    assert hash_generado.startswith("$2b$12$") or hash_generado.startswith("$2b$")

    assert HasherContrasenas.verificar_password(password, hash_generado) is True
    assert HasherContrasenas.verificar_password("OtraPasswordIncorrecta!", hash_generado) is False


def test_verificar_password_invalida_no_lanza_excepcion():
    """Comprueba que hashes corruptos no rompan el flujo y devuelvan False."""
    assert HasherContrasenas.verificar_password("clave", "hash_invalido_corrupto") is False

