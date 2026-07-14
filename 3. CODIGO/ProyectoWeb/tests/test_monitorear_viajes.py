# tests/test_monitorear_viajes.py
"""
REQ004 - Monitorear Viajes
Descripción:
  Como Coordinador necesito: Controlar y supervisar los viajes de transporte detectando 
  imprevistos para poder tomar acciones.
  Así podré: Notificar mediante el sistema a los transportistas para que realicen 
  protocolos para cada tipo de eventualidad.

Funciones bajo prueba:
  - modificar_ruta         (PATCH /api/monitoreo/viajes/{viaje_id}/ruta) -> Usa Observer para notificar.
  - ver_log_notificaciones (GET /api/monitoreo/notificaciones-log)       -> Verifica log de notificaciones.

Patrón: AAA (Arrange – Act – Assert)
"""
from unittest.mock import Mock, patch

# pyrefly: ignore [missing-import]
import pytest
# pyrefly: ignore [missing-import]
from fastapi import HTTPException

from routers.monitoreo import modificar_ruta, ver_log_notificaciones
from schemas.viaje_schemas import ModificarRutaRequest
from models.models import EstadoViajeEnum


def _mock_viaje(viaje_id=1, codigo="VJ-2026-TEST", estado=EstadoViajeEnum.EN_EJECUCION):
    """Crea un mock de viaje para los tests de monitoreo e imprevistos."""
    v = Mock()
    v.id = viaje_id
    v.codigo = codigo
    v.estado = estado
    return v


# ══════════════════════════════════════════════════════════════════════════════
# TESTS — Controlar imprevistos y notificar transportista
# ══════════════════════════════════════════════════════════════════════════════


class TestModificarRuta:
    """Pruebas para controlar imprevistos y notificar al transportista (REQ004)."""

    @patch("patterns.adapter.city_gps_adapter.CityToGPSAdapter.get_coordinates")
    @patch("patterns.observer.trip_observer.TripSubject.notify_all")
    @patch("routers.monitoreo._viaje_monitoreo")
    def test_modificar_ruta_exitoso_notifica_transportista(self, mock_viaje_out, mock_notify, mock_get_coords):
        """El coordinador detecta un imprevisto, desvía la ruta y notifica al transportista."""
        # ── Arrange ──────────────────────────────────────────────
        viaje = _mock_viaje(estado=EstadoViajeEnum.EN_EJECUCION)
        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = viaje
        
        current_user = Mock(id=100, rol="COORDINADOR")
        
        body = ModificarRutaRequest(
            nueva_ruta_json="GUAYAQUIL_SUR",
            motivo="Vía cerrada por deslave (imprevisto)"
        )
        mock_get_coords.return_value = {"lat": -2.2, "lng": -79.9}
        mock_viaje_out.return_value = {"id": 1, "estado": "EN_EJECUCION"}
        
        # ── Act ──────────────────────────────────────────────────
        resultado = modificar_ruta(
            viaje_id=1, body=body, db=db, current_user=current_user
        )
            
        # ── Assert ───────────────────────────────────────────────
        # Se modifican los datos del viaje
        assert viaje.ruta_json == "GUAYAQUIL_SUR"
        assert viaje.destino == "GUAYAQUIL_SUR"
        assert viaje.latitud_destino == -2.2
        assert viaje.longitud_destino == -79.9
        
        # 1. Verifica que la notificación del protocolo de eventualidad se disparó
        mock_notify.assert_called_once()
        args, kwargs = mock_notify.call_args
        assert kwargs["event_type"] == "MODIFICAR_RUTA"
        assert "Desvío registrado" in kwargs["extra_info"]
        assert "Vía cerrada por deslave" in kwargs["extra_info"]

        # 2. Verifica la respuesta
        assert resultado == {"id": 1, "estado": "EN_EJECUCION"}

    def test_modificar_ruta_viaje_no_encontrado(self):
        """Intento de notificar un desvío en un viaje inexistente retorna 404."""
        # ── Arrange ──────────────────────────────────────────────
        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = None
        current_user = Mock(id=100, rol="COORDINADOR")
        body = ModificarRutaRequest(nueva_ruta_json="X", motivo="Y")
        
        # ── Act & Assert ─────────────────────────────────────────
        with pytest.raises(HTTPException) as exc_info:
            modificar_ruta(viaje_id=99, body=body, db=db, current_user=current_user)
            
        assert exc_info.value.status_code == 404
        assert "no encontrado" in exc_info.value.detail.lower()

    def test_modificar_ruta_viaje_no_ejecucion(self):
        """No se puede registrar un imprevisto en un viaje que no está activo."""
        # ── Arrange ──────────────────────────────────────────────
        viaje = _mock_viaje(estado=EstadoViajeEnum.COMPLETADO)
        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = viaje
        current_user = Mock(id=100, rol="COORDINADOR")
        body = ModificarRutaRequest(nueva_ruta_json="X", motivo="Y")
        
        # ── Act & Assert ─────────────────────────────────────────
        with pytest.raises(HTTPException) as exc_info:
            modificar_ruta(viaje_id=1, body=body, db=db, current_user=current_user)
            
        assert exc_info.value.status_code == 409
        assert "ejecución" in exc_info.value.detail.lower()

    def test_modificar_ruta_vacia(self):
        """El sistema requiere una ruta válida para redirigir al transportista."""
        # ── Arrange ──────────────────────────────────────────────
        viaje = _mock_viaje(estado=EstadoViajeEnum.EN_EJECUCION)
        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = viaje
        current_user = Mock(id=100, rol="COORDINADOR")
        body = ModificarRutaRequest(nueva_ruta_json="", motivo="Y")
        
        # ── Act & Assert ─────────────────────────────────────────
        with pytest.raises(HTTPException) as exc_info:
            modificar_ruta(viaje_id=1, body=body, db=db, current_user=current_user)
            
        assert exc_info.value.status_code == 400
        assert "vacía" in exc_info.value.detail.lower()


# ══════════════════════════════════════════════════════════════════════════════
# TESTS — Log de notificaciones enviadas
# ══════════════════════════════════════════════════════════════════════════════


class TestNotificacionesLog:
    """Pruebas para comprobar que el sistema mantiene un historial de notificaciones enviadas."""

    def test_ver_log_notificaciones(self):
        """Se obtienen las notificaciones Push/SMS enviadas a los transportistas."""
        # ── Arrange ──────────────────────────────────────────────
        current_user = Mock(id=100, rol="COORDINADOR")
        mock_logs = [
            "[10:00:00] Notificación Push/SMS enviada a Transportista. Evento: MODIFICAR_RUTA.",
            "[11:00:00] Notificación Push/SMS enviada a Transportista. Evento: ALERTA."
        ]
        
        # ── Act ──────────────────────────────────────────────────
        with patch("routers.monitoreo.global_notification_observer.envios", mock_logs):
            resultado = ver_log_notificaciones(current_user=current_user)
            
        # ── Assert ───────────────────────────────────────────────
        assert isinstance(resultado, list)
        assert len(resultado) == 2
        assert resultado == mock_logs
