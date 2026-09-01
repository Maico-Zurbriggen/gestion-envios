
PESO_MAX_KG = 25
DIMENSION_MAX_CM = 150
SUMA_DIMENSIONES_MAX_CM = 250


def validar_paquete(
    peso_kg: float,
    largo_cm: float,
    ancho_cm: float,
    alto_cm: float,
) -> list[dict[str, str]]:
    """Valida peso y dimensiones de un paquete según las restricciones de HU03 (Escenario 2).

    No lanza excepciones (capa de dominio pura) — retorna una lista de errores
    con forma {"field": ..., "message": ...}, vacía si no hay violaciones.
    """
    errores: list[dict[str, str]] = []

    if peso_kg <= 0:
        errores.append({"field": "peso_kg", "message": "El peso debe ser mayor a 0 kg."})
    elif peso_kg > PESO_MAX_KG:
        errores.append({"field": "peso_kg", "message": f"El peso no puede superar los {PESO_MAX_KG} kg."})

    dimensiones = {"largo_cm": largo_cm, "ancho_cm": ancho_cm, "alto_cm": alto_cm}
    for campo, valor in dimensiones.items():
        if valor <= 0:
            errores.append({"field": campo, "message": "La dimensión debe ser mayor a 0 cm."})
        elif valor > DIMENSION_MAX_CM:
            errores.append({"field": campo, "message": f"Ninguna dimensión puede superar los {DIMENSION_MAX_CM} cm."})

    suma_dimensiones = largo_cm + ancho_cm + alto_cm
    if suma_dimensiones > SUMA_DIMENSIONES_MAX_CM:
        errores.append(
            {
                "field": "dimensiones",
                "message": f"La suma de largo + ancho + alto no puede superar los {SUMA_DIMENSIONES_MAX_CM} cm.",
            }
        )

    return errores
