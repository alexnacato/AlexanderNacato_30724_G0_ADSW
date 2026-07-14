# tests/test_eliminar_transportista.py
"""
REQ010 - Eliminar Transportista
Descripción:
  Como Coordinador necesito: Eliminar transportistas del sistema.
  Así podré: Que las cuentas de transportistas eliminados no tengan acceso al sistema.

Funciones bajo prueba:
  - desactivar_transportista (DELETE /api/transportistas/{transportista_id})
  - eliminar_permanentemente (DELETE /api/transportistas/{transportista_id}/permanente)

Patrón: AAA (Arrange – Act – Assert)
"""
from unittest.mock import Mock, patch

# pyrefly: ignore [missing-import]
import pytest
# pyrefly: ignore [missing-import]
from fastapi import HTTPException

from routers.transportistas import desactivar_transportista, eliminar_permanentemente
from schemas.transportista_schemas import EliminarTransportistaRequest
from models.models import Transportista, Usuario


class TestEliminarTransportista:
    """Pruebas unitarias para REQ010: Eliminar transportistas del sistema."""

    @patch("routers.transportistas.registrar_auditoria")
    def test_desactivar_transportista_exitoso(self, mock_auditoria):
        """El coordinador desactiva una cuenta correctamente."""
        # ── Arrange ──────────────────────────────────────────────
        t = Mock(spec=Transportista)
        t.usuario = Mock(spec=Usuario, id=10, activo=True)
        
        db = Mock()
        # db.query() 1: Busca transportista -> lo encuentra
        # db.query() 2: Busca viajes activos -> no encuentra (None)
        db.query.return_value.filter.return_value.first.side_effect = [t, None]
        
        current_user = Mock(id=100, rol="COORDINADOR")
        request = Mock()
        request.client.host = "127.0.0.1"

        body = EliminarTransportistaRequest(
            razon="Terminación de contrato",
            observaciones="Solicitado por gerencia."
        )

        # ── Act ──────────────────────────────────────────────────
        resultado = desactivar_transportista(
            transportista_id=1,
            body=body,
            db=db,
            current_user=current_user,
            request=request,
        )

        # ── Assert ───────────────────────────────────────────────
        assert "desactivado correctamente" in resultado["mensaje"].lower()
        
        # Validar que la cuenta de usuario se marcó como inactiva (sin acceso al sistema)
        assert t.usuario.activo is False
        db.commit.assert_called_once()
        mock_auditoria.assert_called_once()

    def test_desactivar_transportista_con_viajes_activos(self):
        """No se puede desactivar a un transportista si tiene viajes en ejecución."""
        # ── Arrange ──────────────────────────────────────────────
        t = Mock(spec=Transportista)
        t.usuario = Mock(spec=Usuario, id=10, activo=True)
        
        db = Mock()
        # db.query() 1: Busca transportista -> lo encuentra
        # db.query() 2: Busca viajes activos -> SÍ ENCUENTRA UNO (simulado como True/Mock)
        db.query.return_value.filter.return_value.first.side_effect = [t, Mock()]
        
        current_user = Mock(id=100, rol="COORDINADOR")
        body = EliminarTransportistaRequest(razon="Baja voluntaria")

        # ── Act & Assert ─────────────────────────────────────────
        with pytest.raises(HTTPException) as exc_info:
            desactivar_transportista(
                transportista_id=1,
                body=body,
                db=db,
                current_user=current_user,
            )
            
        assert exc_info.value.status_code == 409
        assert "viajes en ejecución" in exc_info.value.detail.lower()
        # Confirmar que no se guardó el cambio de inactividad
        db.commit.assert_not_called()

    def test_desactivar_transportista_no_encontrado(self):
        """Retorna HTTP 404 si el transportista no existe."""
        # ── Arrange ──────────────────────────────────────────────
        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = None
        
        current_user = Mock(id=100, rol="COORDINADOR")
        body = EliminarTransportistaRequest(razon="Error de tipeo")

        # ── Act & Assert ─────────────────────────────────────────
        with pytest.raises(HTTPException) as exc_info:
            desactivar_transportista(
                transportista_id=999,
                body=body,
                db=db,
                current_user=current_user,
            )
            
        assert exc_info.value.status_code == 404
        assert "no encontrado" in exc_info.value.detail.lower()

    @patch("routers.transportistas.registrar_auditoria")
    def test_eliminar_permanentemente_exitoso(self, mock_auditoria):
        """La eliminación permanente borra físicamente al usuario de la base de datos."""
        # ── Arrange ──────────────────────────────────────────────
        t = Mock(spec=Transportista)
        t.usuario = Mock(spec=Usuario, id=10)
        
        db = Mock()
        # db.query() 1: Busca transportista -> lo encuentra
        # db.query() 2: Busca viajes activos -> no encuentra (None)
        db.query.return_value.filter.return_value.first.side_effect = [t, None]
        
        current_user = Mock(id=100, rol="COORDINADOR")
        request = Mock()
        request.client.host = "127.0.0.1"

        # ── Act ──────────────────────────────────────────────────
        resultado = eliminar_permanentemente(
            transportista_id=1,
            db=db,
            current_user=current_user,
            request=request,
        )

        # ── Assert ───────────────────────────────────────────────
        assert "eliminado permanentemente" in resultado["mensaje"].lower()
        
        # Validar la eliminación en cascada
        db.delete.assert_any_call(t)
        db.delete.assert_any_call(t.usuario)
        db.commit.assert_called_once()
        mock_auditoria.assert_called_once()
