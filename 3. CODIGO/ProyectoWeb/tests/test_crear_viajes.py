# tests/test_crear_viajes.py
"""
REQ011 - Crear Viajes
Descripción:
  Como Secretaria necesito: Registrar nuevos viajes.
  Así podré: Crear cargas laborales para asignarles a los transportistas.

Funciones bajo prueba:
  - crear_viaje (POST /api/viajes/)

Patrón: AAA (Arrange – Act – Assert)
"""
from unittest.mock import Mock, patch

# pyrefly: ignore [missing-import]
import pytest
# pyrefly: ignore [missing-import]
from fastapi import HTTPException

from routers.viajes import crear_viaje
from schemas.viaje_schemas import ViajeCreate
from models.models import Viaje, EstadoViajeEnum


class TestCrearViajes:
    """Pruebas unitarias para REQ011: Crear Viajes."""

    @patch("routers.viajes.registrar_auditoria")
    @patch("routers.viajes._generar_codigo", return_value="VJ-TEST-001")
    @patch("routers.viajes.CityToGPSAdapter.get_coordinates")
    @patch("routers.viajes._viaje_out", return_value={"id": 1, "codigo": "VJ-TEST-001"})
    def test_crear_viaje_exitoso(self, mock_viaje_out, mock_adapter, mock_codigo, mock_auditoria):
        """La secretaria crea un viaje con datos correctos y se guarda en la base de datos."""
        # ── Arrange ──────────────────────────────────────────────
        db = Mock()
        current_user = Mock(id=50, rol="SECRETARIA")
        request = Mock()
        request.client.host = "127.0.0.1"

        # Simular adaptador de coordenadas
        mock_adapter.side_effect = [
            {"lat": -0.2, "lng": -78.5}, # Origen (QUITO)
            {"lat": -2.2, "lng": -79.9}  # Destino (GUAYAQUIL)
        ]

        body = ViajeCreate(
            tipo_mercancia="Electrónicos",
            peso_total_kg=5000,
            dimensiones="10x5x3",
            numero_contenedor="MSCU1234567",
            peso_contenedor_kg=2000,
            origen="QUITO",
            destino="GUAYAQUIL",
            punto_recepcion="Bodega Central",
            destinatario_nombre="Empresa XYZ",
            destinatario_tel="0999999999",
            destinatario_correo="empresa@correo.com",
            observaciones="Carga frágil"
        )

        # ── Act ──────────────────────────────────────────────────
        resultado = crear_viaje(
            body=body,
            db=db,
            current_user=current_user,
            request=request,
        )

        # ── Assert ───────────────────────────────────────────────
        assert resultado == {"id": 1, "codigo": "VJ-TEST-001"}
        
        # Validar persistencia en BD
        db.add.assert_called_once()
        viaje_guardado = db.add.call_args[0][0]
        assert isinstance(viaje_guardado, Viaje)
        assert viaje_guardado.codigo == "VJ-TEST-001"
        assert viaje_guardado.origen == "QUITO"
        assert viaje_guardado.destino == "GUAYAQUIL"
        assert viaje_guardado.estado == EstadoViajeEnum.DISPONIBLE
        
        # Las coordenadas iniciales (actual) deben ser iguales a las del origen
        assert viaje_guardado.latitud_actual == -0.2
        assert viaje_guardado.longitud_actual == -78.5
        
        db.commit.assert_called_once()
        mock_auditoria.assert_called_once()

    def test_crear_viaje_contenedor_invalido(self):
        """Si el número de contenedor no cumple con el formato internacional (4 letras + 7 dígitos), falla."""
        # ── Arrange ──────────────────────────────────────────────
        db = Mock()
        current_user = Mock(id=50, rol="SECRETARIA")
        
        body = ViajeCreate(
            tipo_mercancia="Carga General",
            peso_total_kg=1000,
            numero_contenedor="MAL123", # Formato incorrecto
            origen="QUITO",
            destino="CUENCA",
            punto_recepcion="Bodega",
            destinatario_nombre="Destinatario"
        )

        # ── Act & Assert ─────────────────────────────────────────
        with pytest.raises(HTTPException) as exc_info:
            crear_viaje(
                body=body,
                db=db,
                current_user=current_user,
            )
            
        assert exc_info.value.status_code == 400
        assert "formato de contenedor inválido" in exc_info.value.detail.lower()

    def test_crear_viaje_origen_destino_iguales(self):
        """El sistema impide crear viajes donde el origen sea idéntico al destino."""
        # ── Arrange ──────────────────────────────────────────────
        db = Mock()
        current_user = Mock(id=50, rol="SECRETARIA")
        
        body = ViajeCreate(
            tipo_mercancia="Carga",
            peso_total_kg=1000,
            origen="  Quito  ", # Mismo origen
            destino="QUITO",   # Mismo destino
            punto_recepcion="Bodega",
            destinatario_nombre="Destinatario"
        )

        # ── Act & Assert ─────────────────────────────────────────
        with pytest.raises(HTTPException) as exc_info:
            crear_viaje(
                body=body,
                db=db,
                current_user=current_user,
            )
            
        assert exc_info.value.status_code == 400
        assert "origen y destino no pueden ser iguales" in exc_info.value.detail.lower()
