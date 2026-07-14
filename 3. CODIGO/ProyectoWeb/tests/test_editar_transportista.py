# tests/test_editar_transportista.py
"""
REQ009 - Editar Transportista
Descripción:
  Como Coordinador necesito: Actualizar la información del vehículo del transportista.
  Así podré: Tener información actualizada dentro del sistema.

Funciones bajo prueba:
  - editar_transportista (PUT /api/transportistas/{transportista_id})

Patrón: AAA (Arrange – Act – Assert)
"""
from unittest.mock import Mock, patch

# pyrefly: ignore [missing-import]
import pytest
# pyrefly: ignore [missing-import]
from fastapi import HTTPException

from routers.transportistas import editar_transportista
from schemas.transportista_schemas import TransportistaUpdate
from models.models import Transportista, Usuario


class TestEditarTransportista:
    """Pruebas unitarias para REQ009: Editar transportista."""

    @patch("routers.transportistas.registrar_auditoria")
    @patch("routers.transportistas._build_out", return_value={"id": 1})
    def test_editar_transportista_vehiculo_exitoso(self, mock_build_out, mock_auditoria):
        """Se actualiza exitosamente la información del vehículo (placa, tipo, capacidad)."""
        # ── Arrange ──────────────────────────────────────────────
        t = Mock(spec=Transportista)
        t.placa_vehiculo = "ANTIGUA"
        t.tipo_vehiculo = "Antiguo"
        t.capacidad_ton = 1.0
        
        # El transportista tiene un usuario asociado
        t.usuario = Mock(spec=Usuario, id=10, nombres="Juan", correo="juan@correo.com")
        
        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = t
        
        current_user = Mock(id=100, rol="COORDINADOR")
        request = Mock()
        request.client.host = "127.0.0.1"

        # Solo enviamos actualización del vehículo
        body = TransportistaUpdate(
            placa_vehiculo="NUEVA-123",
            tipo_vehiculo="Camión Pesado",
            capacidad_ton=10.5,
            nombres=None,
            correo=None,
        )

        # ── Act ──────────────────────────────────────────────────
        resultado = editar_transportista(
            transportista_id=1,
            body=body,
            db=db,
            current_user=current_user,
            request=request,
        )

        # ── Assert ───────────────────────────────────────────────
        assert t.placa_vehiculo == "NUEVA-123"
        assert t.tipo_vehiculo == "Camión Pesado"
        assert t.capacidad_ton == 10.5
        
        db.commit.assert_called_once()
        mock_auditoria.assert_called_once()
        assert resultado == {"id": 1}

    @patch("routers.transportistas.registrar_auditoria")
    @patch("routers.transportistas._build_out", return_value={"id": 1})
    def test_editar_transportista_nombres_correo_exitoso(self, mock_build_out, mock_auditoria):
        """Se pueden actualizar también los datos del usuario (nombres y correo) si están libres."""
        # ── Arrange ──────────────────────────────────────────────
        t = Mock(spec=Transportista)
        t.usuario = Mock(spec=Usuario, id=10, nombres="Juan Viejo", correo="viejo@correo.com")
        
        db = Mock()
        # Primer query() busca al transportista
        # Segundo query() busca si el correo existe. Retornamos None (está libre)
        db.query.return_value.filter.return_value.first.side_effect = [t, None]
        
        current_user = Mock(id=100, rol="COORDINADOR")

        body = TransportistaUpdate(
            nombres="Juan Nuevo",
            correo="nuevo@correo.com",
            # Sin enviar datos del vehículo
            placa_vehiculo=None,
        )

        # ── Act ──────────────────────────────────────────────────
        editar_transportista(
            transportista_id=1,
            body=body,
            db=db,
            current_user=current_user,
        )

        # ── Assert ───────────────────────────────────────────────
        assert t.usuario.nombres == "Juan Nuevo"
        assert t.usuario.correo == "nuevo@correo.com"
        db.commit.assert_called_once()

    def test_editar_transportista_correo_duplicado(self):
        """No permite cambiar el correo si este ya pertenece a OTRO usuario."""
        # ── Arrange ──────────────────────────────────────────────
        t = Mock(spec=Transportista)
        t.usuario = Mock(spec=Usuario, id=10, nombres="Juan", correo="juan@correo.com")
        
        db = Mock()
        # Segundo query() encuentra a OTRO usuario con ese mismo correo
        otro_usuario = Mock(spec=Usuario, id=99)
        db.query.return_value.filter.return_value.first.side_effect = [t, otro_usuario]
        
        current_user = Mock(id=100, rol="COORDINADOR")

        body = TransportistaUpdate(correo="ocupado@correo.com")

        # ── Act & Assert ─────────────────────────────────────────
        with pytest.raises(HTTPException) as exc_info:
            editar_transportista(
                transportista_id=1,
                body=body,
                db=db,
                current_user=current_user,
            )
            
        assert exc_info.value.status_code == 400
        assert "ya se encuentra registrado" in exc_info.value.detail.lower()

    def test_editar_transportista_no_encontrado(self):
        """Retorna HTTP 404 si el transportista a editar no existe."""
        # ── Arrange ──────────────────────────────────────────────
        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = None
        
        current_user = Mock(id=100, rol="COORDINADOR")
        body = TransportistaUpdate(placa_vehiculo="NUEVA-123")

        # ── Act & Assert ─────────────────────────────────────────
        with pytest.raises(HTTPException) as exc_info:
            editar_transportista(
                transportista_id=999,
                body=body,
                db=db,
                current_user=current_user,
            )
            
        assert exc_info.value.status_code == 404
        assert "no encontrado" in exc_info.value.detail.lower()
