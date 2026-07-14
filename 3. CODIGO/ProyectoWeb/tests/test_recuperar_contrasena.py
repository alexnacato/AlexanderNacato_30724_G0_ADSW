# tests/test_recuperar_contrasena.py
"""
REQ008 - Recuperar Contraseña
Descripción:
  Como Usuario necesito: Módulo para recuperar contraseñas.
  Así podré: Los usuarios tendrán acceso nuevamente al sistema.

Funciones bajo prueba:
  - solicitar_recuperacion (POST /api/auth/recuperar-password)

Patrón: AAA (Arrange – Act – Assert)
"""
from unittest.mock import Mock, patch

# pyrefly: ignore [missing-import]
import pytest
# pyrefly: ignore [missing-import]
from fastapi import HTTPException

from routers.auth import solicitar_recuperacion
from schemas.auth_schemas import RecuperarPasswordRequest
from models.models import Usuario


class TestRecuperarContrasena:
    """Pruebas unitarias para REQ008: Recuperación de contraseñas."""

    @patch("routers.auth.enviar_nueva_contrasena")
    @patch("routers.auth.hash_password")
    @patch("routers.auth.generar_contrasena")
    def test_solicitar_recuperacion_exitoso(self, mock_generar, mock_hash, mock_enviar):
        """Si el correo existe y el usuario está activo, se genera y envía una nueva clave."""
        # ── Arrange ──────────────────────────────────────────────
        mock_generar.return_value = "NuevaClave123"
        mock_hash.return_value = "hashed_NuevaClave123"
        
        user = Mock(spec=Usuario)
        user.correo = "test@correo.com"
        user.activo = True
        
        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = user
        
        body = RecuperarPasswordRequest(correo="test@correo.com")

        # ── Act ──────────────────────────────────────────────────
        resultado = solicitar_recuperacion(body=body, db=db)

        # ── Assert ───────────────────────────────────────────────
        assert "recibirás tu nueva contraseña" in resultado["mensaje"].lower()
        
        # Validar generación y guardado
        mock_generar.assert_called_once()
        mock_hash.assert_called_once_with("NuevaClave123")
        assert user.hashed_password == "hashed_NuevaClave123"
        assert user.token_reset is None
        assert user.token_reset_exp is None
        db.commit.assert_called_once()
        
        # Validar envío de correo
        mock_enviar.assert_called_once_with("test@correo.com", "NuevaClave123")

    @patch("routers.auth.enviar_nueva_contrasena")
    @patch("routers.auth.generar_contrasena")
    def test_solicitar_recuperacion_correo_inexistente(self, mock_generar, mock_enviar):
        """Para evitar filtración de correos registrados, siempre retorna el mismo mensaje exitoso, pero no hace nada si el correo no existe."""
        # ── Arrange ──────────────────────────────────────────────
        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = None
        
        body = RecuperarPasswordRequest(correo="inexistente@correo.com")

        # ── Act ──────────────────────────────────────────────────
        resultado = solicitar_recuperacion(body=body, db=db)

        # ── Assert ───────────────────────────────────────────────
        assert "recibirás tu nueva contraseña" in resultado["mensaje"].lower()
        
        # Validar que NO se ejecutó la lógica interna
        mock_generar.assert_not_called()
        mock_enviar.assert_not_called()
        db.commit.assert_not_called()

    @patch("routers.auth.enviar_nueva_contrasena")
    @patch("routers.auth.generar_contrasena")
    def test_solicitar_recuperacion_usuario_inactivo(self, mock_generar, mock_enviar):
        """Si el usuario existe pero está inactivo, tampoco se le genera clave ni se revela su inactividad."""
        # ── Arrange ──────────────────────────────────────────────
        user = Mock(spec=Usuario)
        user.correo = "test@correo.com"
        user.activo = False  # Inactivo
        
        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = user
        
        body = RecuperarPasswordRequest(correo="test@correo.com")

        # ── Act ──────────────────────────────────────────────────
        resultado = solicitar_recuperacion(body=body, db=db)

        # ── Assert ───────────────────────────────────────────────
        assert "recibirás tu nueva contraseña" in resultado["mensaje"].lower()
        
        # Validar que NO se ejecutó la lógica interna
        mock_generar.assert_not_called()
        mock_enviar.assert_not_called()
        db.commit.assert_not_called()

    @patch("routers.auth.enviar_nueva_contrasena")
    @patch("routers.auth.generar_contrasena")
    def test_solicitar_recuperacion_falla_envio_correo(self, mock_generar, mock_enviar):
        """Si el servidor SMTP falla, se retorna un HTTP 500 para notificar al usuario."""
        # ── Arrange ──────────────────────────────────────────────
        mock_generar.return_value = "NuevaClave123"
        mock_enviar.side_effect = Exception("Fallo en SMTP")
        
        user = Mock(spec=Usuario)
        user.correo = "test@correo.com"
        user.activo = True
        
        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = user
        
        body = RecuperarPasswordRequest(correo="test@correo.com")

        # ── Act & Assert ─────────────────────────────────────────
        with pytest.raises(HTTPException) as exc_info:
            solicitar_recuperacion(body=body, db=db)
            
        assert exc_info.value.status_code == 500
        assert "error al enviar el correo" in exc_info.value.detail.lower()
