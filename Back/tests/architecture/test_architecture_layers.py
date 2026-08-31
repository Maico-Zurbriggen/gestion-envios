import ast
import os
from pathlib import Path


def test_domain_no_importa_capas_externas():
    """Verifica la regla estricta de Clean Architecture: Domain no importa nada de api, application o infrastructure."""
    domain_path = Path("app/domain")
    capas_prohibidas = ["app.api", "app.application", "app.infrastructure", "fastapi", "sqlalchemy"]

    for root, _, files in os.walk(domain_path):
        for file in files:
            if file.endswith(".py"):
                file_path = Path(root) / file
                with open(file_path, "r", encoding="utf-8") as f:
                    tree = ast.parse(f.read(), filename=str(file_path))

                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            for prohibida in capas_prohibidas:
                                assert not alias.name.startswith(prohibida), (
                                    f"Violación de arquitectura en {file_path}: domain importa {alias.name}"
                                )
                    elif isinstance(node, ast.ImportFrom):
                        module_name = node.module or ""
                        for prohibida in capas_prohibidas:
                            assert not module_name.startswith(prohibida), (
                                f"Violación de arquitectura en {file_path}: domain importa de {module_name}"
                            )


def test_application_no_importa_api():
    """Verifica que Application no dependa de la capa de presentación (API)."""
    app_path = Path("app/application")
    capas_prohibidas = ["app.api", "fastapi"]

    for root, _, files in os.walk(app_path):
        for file in files:
            if file.endswith(".py"):
                file_path = Path(root) / file
                with open(file_path, "r", encoding="utf-8") as f:
                    tree = ast.parse(f.read(), filename=str(file_path))

                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            for prohibida in capas_prohibidas:
                                assert not alias.name.startswith(prohibida), (
                                    f"Violación de arquitectura en {file_path}: application importa {alias.name}"
                                )
                    elif isinstance(node, ast.ImportFrom):
                        module_name = node.module or ""
                        for prohibida in capas_prohibidas:
                            assert not module_name.startswith(prohibida), (
                                f"Violación de arquitectura en {file_path}: application importa de {module_name}"
                            )

