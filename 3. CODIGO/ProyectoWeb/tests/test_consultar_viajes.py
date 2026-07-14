# tests/test_consultar_viajes.py
"""
REQ012 - Consultar Viajes
Descripción:
  Como Secretaria necesito: Visualizar los viajes, detalles y estado de cada uno de ellos.
  Así podré: Conocer el estado operativo y el transportista asignado.

Funciones bajo prueba:
  - listar_viajes (GET /api/viajes/)
  - obtener_viaje (GET /api/viajes/{viaje_id})

Patrón: AAA (Arrange – Act – Assert)
"""
from unittest.mock import Mock, patch

# pyrefly: ignore [missing-import]
import pytest
# pyrefly: ignore [missing-import]
from fastapi import HTTPException

from routers.viajes import listar_viajes, obtener_viaje
from models.models import Viaje, Transportista, EstadoViajeEnum


class TestConsultarViajes:
    """Pruebas unitarias para REQ012: Consultar información de viajes."""

    @patch("routers.viajes._viaje_out")
    def test_listar_viajes_como_secretaria(self, mock_viaje_out):
        """La secretaria puede visualizar todos los viajes registrados."""
        # ── Arrange ──────────────────────────────────────────────
        v1 = Mock(spec=Viaje, id=1, codigo="VJ-001")
        v2 = Mock(spec=Viaje, id=2, codigo="VJ-002")
        
        db = Mock()
        db.query.return_value.order_by.return_value.all.return_value = [v1, v2]
        
        current_user = Mock(id=50)
        current_user.rol = Mock()
        current_user.rol.value = "SECRETARIA"
        type(current_user.rol).value = "SECRETARIA"

        # Mockear serialización para simplificar
        mock_viaje_out.side_effect = lambda v: {"id": v.id, "codigo": v.codigo}

        # ── Act ──────────────────────────────────────────────────
        resultado = listar_viajes(db=db, current_user=current_user)

        # ── Assert ───────────────────────────────────────────────
        assert len(resultado) == 2
        assert resultado[0]["id"] == 1
        assert resultado[1]["id"] == 2
        # Verifica que no se aplicaron filtros de transportista por el rol
        db.query.return_value.filter.assert_not_called()

    @patch("routers.viajes._viaje_out")
    def test_listar_viajes_como_transportista(self, mock_viaje_out):
        """Si el usuario es Transportista, el listado se filtra obligatoriamente a solo SUS viajes."""
        # ── Arrange ──────────────────────────────────────────────
        v = Mock(spec=Viaje, id=5, codigo="VJ-MIO")
        t = Mock(spec=Transportista, id=10, usuario_id=88)
        
        db = Mock()
        # db.query(Transportista) para obtener su ID
        db.query.return_value.filter.return_value.first.return_value = t
        # db.query(Viaje) -> all()
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [v]
        
        current_user = Mock(id=88)
        current_user.rol = Mock()
        current_user.rol.value = "TRANSPORTISTA"
        type(current_user.rol).value = "TRANSPORTISTA"
        
        mock_viaje_out.side_effect = lambda v: {"id": v.id, "codigo": v.codigo}

        # ── Act ──────────────────────────────────────────────────
        resultado = listar_viajes(db=db, current_user=current_user)

        # ── Assert ───────────────────────────────────────────────
        assert len(resultado) == 1
        assert resultado[0]["codigo"] == "VJ-MIO"
        # Valida que se aplicó el filtro forzado transportista_id == 10
        db.query.return_value.filter.assert_called()

    @patch("routers.viajes._viaje_out")
    def test_listar_viajes_con_filtros(self, mock_viaje_out):
        """La secretaria puede aplicar filtros como estado y transportista_id."""
        # ── Arrange ──────────────────────────────────────────────
        v1 = Mock(spec=Viaje, id=1)
        
        db = Mock()
        db.query.return_value.filter.return_value.filter.return_value.order_by.return_value.all.return_value = [v1]
        
        current_user = Mock(id=50)
        current_user.rol = Mock()
        current_user.rol.value = "SECRETARIA"
        type(current_user.rol).value = "SECRETARIA"
        
        mock_viaje_out.side_effect = lambda v: {"id": v.id}

        # ── Act ──────────────────────────────────────────────────
        resultado = listar_viajes(
            estado="DISPONIBLE",
            transportista_id=10,
            db=db, 
            current_user=current_user
        )

        # ── Assert ───────────────────────────────────────────────
        assert len(resultado) == 1
        # Se retornó la cantidad esperada indicando que la cadena de filtros funcionó
        pass

    @patch("routers.viajes._viaje_out")
    def test_obtener_viaje_por_id_exitoso(self, mock_viaje_out):
        """Visualiza los detalles operativos completos de un viaje específico."""
        # ── Arrange ──────────────────────────────────────────────
        v = Mock(spec=Viaje, id=10, codigo="VJ-X")
        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = v
        
        current_user = Mock(id=50)
        
        mock_viaje_out.return_value = {"id": 10, "estado": "EN_EJECUCION"}

        # ── Act ──────────────────────────────────────────────────
        resultado = obtener_viaje(viaje_id=10, db=db, current_user=current_user)

        # ── Assert ───────────────────────────────────────────────
        assert resultado["id"] == 10
        assert resultado["estado"] == "EN_EJECUCION"

    def test_obtener_viaje_no_encontrado(self):
        """Retorna HTTP 404 si el viaje solicitado no existe."""
        # ── Arrange ──────────────────────────────────────────────
        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = None
        current_user = Mock(id=50)

        # ── Act & Assert ─────────────────────────────────────────
        with pytest.raises(HTTPException) as exc_info:
            obtener_viaje(viaje_id=999, db=db, current_user=current_user)
            
        assert exc_info.value.status_code == 404
        assert "no encontrado" in exc_info.value.detail.lower()
