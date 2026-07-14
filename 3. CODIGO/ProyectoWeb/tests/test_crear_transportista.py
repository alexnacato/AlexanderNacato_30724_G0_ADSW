# tests/test_crear_transportista.py
"""
REQ005 - Crear Transportista
Descripción:
  Como Coordinador necesito: Registrar un nuevo transportista con la información requerida.
  Así podré: Permitir acceso al sistema para los transportistas.

Funciones bajo prueba:
  - crear_transportista (POST /api/transportistas/)

Patrón: AAA (Arrange – Act – Assert)
"""
from unittest.mock import Mock, patch

# pyrefly: ignore [missing-import]
import pytest
# pyrefly: ignore [missing-import]
from fastapi import HTTPException

from routers.transportistas import crear_transportista
from models.models import Usuario


class TestCrearTransportista:
    """Pruebas unitarias para REQ005: Registrar un nuevo transportista."""

    @patch("core.security.hash_password", return_value="hashed_123")
    @patch("routers.transportistas._build_out", return_value={"id": 1, "nombres": "Juan Pérez"})
    @patch("routers.transportistas.registrar_auditoria")
    def test_crear_transportista_exitoso(self, mock_auditoria, mock_build_out, mock_hash):
        """El coordinador registra correctamente un nuevo transportista con todos los datos."""
        # ── Arrange ──────────────────────────────────────────────
        db = Mock()
        # db.query().filter().first() == None simula que NO existen duplicados (ni correo ni cédula)
        db.query.return_value.filter.return_value.first.return_value = None
        
        current_user = Mock(id=100, rol="COORDINADOR")
        request = Mock()
        request.client.host = "127.0.0.1"

        # ── Act ──────────────────────────────────────────────────
        resultado = crear_transportista(
            cedula="1234567890",
            nombres="Juan Pérez",
            correo="juan@correo.com",
            password="clave_segura",
            placa_vehiculo="ABC-1234",
            tipo_vehiculo="Camión",
            capacidad_ton=5.5,
            direccion="Quito",
            telefono="0999999999",
            db=db,
            current_user=current_user,
            request=request,
        )

        # ── Assert ───────────────────────────────────────────────
        assert resultado == {"id": 1, "nombres": "Juan Pérez"}
        
        # Validar inserciones en base de datos (se añade Usuario y luego Transportista)
        assert db.add.call_count == 2
        assert db.flush.called
        assert db.commit.called
        assert db.refresh.called
        
        # Validar que se registró en auditoría el acceso/creación
        mock_auditoria.assert_called_once()

    def test_crear_transportista_correo_existente(self):
        """El sistema impide registrar a alguien si su correo ya está en uso."""
        # ── Arrange ──────────────────────────────────────────────
        db = Mock()
        # Simular que el correo ya existe en BD
        db.query.return_value.filter.return_value.first.return_value = Usuario(id=1)
        
        current_user = Mock(id=100, rol="COORDINADOR")

        # ── Act & Assert ─────────────────────────────────────────
        with pytest.raises(HTTPException) as exc_info:
            crear_transportista(
                cedula="1234567890",
                nombres="Juan Pérez",
                correo="existente@correo.com",
                password="clave",
                placa_vehiculo=None,
                tipo_vehiculo=None,
                capacidad_ton=None,
                direccion=None,
                telefono=None,
                db=db,
                current_user=current_user,
            )
            
        assert exc_info.value.status_code == 400
        assert "correo ya está registrado" in exc_info.value.detail.lower()

    def test_crear_transportista_cedula_existente(self):
        """El sistema impide registrar a alguien si su cédula ya está en uso."""
        # ── Arrange ──────────────────────────────────────────────
        db = Mock()
        
        # La función primero valida correo, luego cédula.
        # Simulamos que el correo NO existe (None), pero la cédula SÍ (objeto).
        db.query.return_value.filter.return_value.first.side_effect = [None, Usuario(id=1)]
        
        current_user = Mock(id=100, rol="COORDINADOR")

        # ── Act & Assert ─────────────────────────────────────────
        with pytest.raises(HTTPException) as exc_info:
            crear_transportista(
                cedula="0999999999",
                nombres="Juan Pérez",
                correo="nuevo@correo.com",
                password="clave",
                placa_vehiculo=None,
                tipo_vehiculo=None,
                capacidad_ton=None,
                direccion=None,
                telefono=None,
                db=db,
                current_user=current_user,
            )
            
        assert exc_info.value.status_code == 400
        assert "cédula ya está registrada" in exc_info.value.detail.lower()
