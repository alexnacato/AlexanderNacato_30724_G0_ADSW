# tests/test_login.py
from unittest.mock import Mock, patch
import pytest
from fastapi import HTTPException
from routers.auth import login

class TestLogin:
    """Pruebas unitarias para RF-1: Iniciar Sesión (login) con control de roles."""

    # Usamos parametrización para generar 5 pruebas dinámicas (una por cada rol requerido)
    @pytest.mark.parametrize("rol_usuario", ["CLIENTE", "COORDINADOR", "TRANSPORTISTA", "SECRETARIA", "GERENTE"])
    def test_login_exitoso_roles(self, rol_usuario):
        body = Mock(username="usuario@correo.com", password="clave123")
        request = Mock()
        request.client.host = "127.0.0.1"

        user_mock = Mock(
            id=1,
            rol=rol_usuario,
            nombres="Jonathan",
            activo=True,
            hashed_password="hash_falso",
        )

        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = user_mock

        with patch("routers.auth.verify_password", return_value=True), \
             patch("routers.auth.create_access_token", return_value="token_falso"), \
             patch("routers.auth.registrar_auditoria"):

            resultado = login(body, request, db)

            assert resultado.access_token == "token_falso"
            assert resultado.rol == rol_usuario
            assert resultado.nombres == "Jonathan"
            assert resultado.id == 1

    def test_login_usuario_no_existe(self):
        body = Mock(username="noexiste@correo.com", password="clave123")
        request = Mock()
        request.client.host = "127.0.0.1"

        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            login(body, request, db)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Correo y/o contraseña incorrectos"

    def test_login_password_incorrecta(self):
        body = Mock(username="usuario@correo.com", password="claveMala")
        request = Mock()
        request.client.host = "127.0.0.1"

        user_mock = Mock(id=1, rol="GERENTE", activo=True, hashed_password="hash_falso")

        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = user_mock

        with patch("routers.auth.verify_password", return_value=False):
            with pytest.raises(HTTPException) as exc_info:
                login(body, request, db)

            assert exc_info.value.status_code == 401
            assert exc_info.value.detail == "Correo y/o contraseña incorrectos"

    def test_login_cuenta_inactiva(self):
        body = Mock(username="usuario@correo.com", password="clave123")
        request = Mock()
        request.client.host = "127.0.0.1"

        user_mock = Mock(id=1, rol="TRANSPORTISTA", activo=False, hashed_password="hash_falso")

        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = user_mock

        with patch("routers.auth.verify_password", return_value=True):
            with pytest.raises(HTTPException) as exc_info:
                login(body, request, db)

            assert exc_info.value.status_code == 403
            assert "inactiva" in exc_info.value.detail.lower()