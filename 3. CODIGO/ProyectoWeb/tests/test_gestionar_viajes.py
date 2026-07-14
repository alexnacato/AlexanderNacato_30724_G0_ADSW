# tests/test_gestionar_viajes.py
"""
REQ003 - Gestionar Viajes
  Como Secretaria/Transportista necesito: Tener un mapa para visualizar cada viaje.
  Así podré: Ver la ejecución y ubicación de cada viaje en tiempo real.

Funciones bajo prueba:
  - obtener_ubicacion         (GET /api/monitoreo/ubicacion/{viaje_id})  → GPS Strategy
  - viajes_en_ejecucion       (GET /api/monitoreo/viajes-en-ejecucion)  → listado mapa
  - listar_viajes             (GET /api/viajes/)                        → consultar viajes
  - obtener_viaje             (GET /api/viajes/{viaje_id})              → detalle + coords

Patrón: AAA (Arrange – Act – Assert)
"""
from unittest.mock import Mock, patch, MagicMock

# pyrefly: ignore [missing-import]
import pytest
# pyrefly: ignore [missing-import]
from fastapi import HTTPException

from routers.monitoreo import obtener_ubicacion, viajes_en_ejecucion
from routers.viajes import listar_viajes, obtener_viaje


# ── Helpers para construir mocks de Viaje ─────────────────────────────────────

def _mock_viaje(
    viaje_id=1, codigo="VJ-20260101-ABCD", estado="EN_EJECUCION",
    origen="QUITO", destino="GUAYAQUIL",
    lat_origen=-0.1807, lng_origen=-78.4678,
    lat_destino=-2.1708, lng_destino=-79.9224,
    lat_actual=-1.2500, lng_actual=-79.2000,
    transportista_nombres="Carlos Pérez", placa="ABC-1234",
    horas_retraso=0, ruta_json=None, fecha_salida=None,
    fecha_llegada_est=None, fecha_llegada_real=None,
    transportista_id=10, causa_retraso=None, causa_cancelacion=None,
    observaciones=None,
):
    """Crea un mock de Viaje con coordenadas GPS para visualización en mapa."""
    v = Mock()
    v.id = viaje_id
    v.codigo = codigo
    v.origen = origen
    v.destino = destino
    v.ruta_json = ruta_json
    v.fecha_salida = fecha_salida
    v.fecha_llegada_est = fecha_llegada_est
    v.fecha_llegada_real = fecha_llegada_real
    v.horas_retraso = horas_retraso
    v.causa_retraso = causa_retraso
    v.causa_cancelacion = causa_cancelacion
    v.observaciones = observaciones
    v.transportista_id = transportista_id
    v.creado_en = "2026-01-01T00:00:00"
    v.actualizado_en = "2026-01-01T00:00:00"

    # Coordenadas GPS (esenciales para el mapa)
    v.latitud_origen = lat_origen
    v.longitud_origen = lng_origen
    v.latitud_destino = lat_destino
    v.longitud_destino = lng_destino
    v.latitud_actual = lat_actual
    v.longitud_actual = lng_actual

    # Mercancía
    v.tipo_mercancia = "Electrónicos"
    v.peso_total_kg = 5000
    v.dimensiones = "10x5x3"
    v.numero_contenedor = "MSCU1234567"
    v.peso_contenedor_kg = 2000
    v.punto_recepcion = "Bodega Central"
    v.destinatario_nombre = "Empresa XYZ"
    v.destinatario_tel = "0991234567"
    v.destinatario_correo = "dest@correo.com"

    # Estado como Enum-like
    v.estado = Mock()
    v.estado.value = estado
    v.estado.__eq__ = lambda self, other: self.value == (other.value if hasattr(other, 'value') else other)
    v.estado.__ne__ = lambda self, other: not self.__eq__(other)
    v.estado.__str__ = lambda self: self.value

    # Transportista asociado
    if transportista_nombres:
        usuario_mock = Mock()
        usuario_mock.nombres = transportista_nombres
        transportista_mock = Mock()
        transportista_mock.usuario = usuario_mock
        transportista_mock.placa_vehiculo = placa
        v.transportista = transportista_mock
    else:
        v.transportista = None

    return v


# ══════════════════════════════════════════════════════════════════════════════
# TESTS — Ubicación GPS en Tiempo Real (Patrón Strategy)
# ══════════════════════════════════════════════════════════════════════════════


class TestObtenerUbicacion:
    """Pruebas para obtener_ubicacion (GET /api/monitoreo/ubicacion/{viaje_id}).
    Verifica la obtención de coordenadas GPS para el mapa en tiempo real."""

    @patch("routers.monitoreo.GPSTrackerContext")
    @patch("routers.monitoreo.SimulatedInterpolationStrategy")
    def test_ubicacion_strategy_simulada(self, mock_strategy_cls, mock_context_cls):
        """La estrategia simulada retorna coordenadas interpoladas para el mapa."""
        # ── Arrange ──────────────────────────────────────────────
        viaje = _mock_viaje(viaje_id=1, estado="EN_EJECUCION")

        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = viaje

        mock_tracker = Mock()
        mock_tracker.execute.return_value = {
            "lat": -1.0500, "lng": -79.1000, "tipo_gps": "Simulado (En Movimiento: 45%)"
        }
        mock_context_cls.return_value = mock_tracker

        current_user = Mock(id=50, rol="SECRETARIA")

        # ── Act ──────────────────────────────────────────────────
        resultado = obtener_ubicacion(
            viaje_id=1, strategy_type="simulado", db=db, current_user=current_user,
        )

        # ── Assert ───────────────────────────────────────────────
        assert resultado["viaje_id"] == 1
        assert resultado["codigo"] == "VJ-20260101-ABCD"
        assert resultado["lat"] == -1.0500
        assert resultado["lng"] == -79.1000
        assert "Simulado" in resultado["tipo_gps"]

    @patch("routers.monitoreo.GPSTrackerContext")
    @patch("routers.monitoreo.RealGPSTrackingStrategy")
    def test_ubicacion_strategy_real(self, mock_strategy_cls, mock_context_cls):
        """La estrategia real retorna las coordenadas almacenadas en BD."""
        # ── Arrange ──────────────────────────────────────────────
        viaje = _mock_viaje(
            viaje_id=2, codigo="VJ-20260101-REAL",
            lat_actual=-0.9500, lng_actual=-78.8000,
        )

        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = viaje

        mock_tracker = Mock()
        mock_tracker.execute.return_value = {
            "lat": -0.9500, "lng": -78.8000, "tipo_gps": "GPS Real (Telemetría Activa)"
        }
        mock_context_cls.return_value = mock_tracker

        current_user = Mock(id=50, rol="COORDINADOR")

        # ── Act ──────────────────────────────────────────────────
        resultado = obtener_ubicacion(
            viaje_id=2, strategy_type="real", db=db, current_user=current_user,
        )

        # ── Assert ───────────────────────────────────────────────
        assert resultado["viaje_id"] == 2
        assert resultado["lat"] == -0.9500
        assert resultado["lng"] == -78.8000
        assert "Real" in resultado["tipo_gps"]

    def test_ubicacion_viaje_no_encontrado(self):
        """Se lanza HTTP 404 si el viaje no existe."""
        # ── Arrange ──────────────────────────────────────────────
        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = None

        current_user = Mock(id=50, rol="SECRETARIA")

        # ── Act & Assert ─────────────────────────────────────────
        with pytest.raises(HTTPException) as exc_info:
            obtener_ubicacion(
                viaje_id=999, strategy_type="simulado", db=db, current_user=current_user,
            )

        assert exc_info.value.status_code == 404
        assert "no encontrado" in exc_info.value.detail.lower()


# ══════════════════════════════════════════════════════════════════════════════
# TESTS — Viajes en Ejecución (Vista de Mapa con Decorator)
# ══════════════════════════════════════════════════════════════════════════════


class TestViajesEnEjecucion:
    """Pruebas para viajes_en_ejecucion (GET /api/monitoreo/viajes-en-ejecucion).
    Verifica el listado de viajes activos para monitoreo en mapa."""

    def test_viajes_en_ejecucion_con_datos(self):
        """Retorna viajes activos con coordenadas GPS y datos de decoración visual."""
        # ── Arrange ──────────────────────────────────────────────
        v1 = _mock_viaje(viaje_id=1, codigo="VJ-001", estado="EN_EJECUCION")
        v2 = _mock_viaje(
            viaje_id=2, codigo="VJ-002", estado="TRANSPORTISTA_ASIGNADO",
            transportista_nombres="María López", placa="XYZ-5678",
        )

        db = Mock()
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [v1, v2]

        current_user = Mock(id=100, rol="COORDINADOR")

        # ── Act ──────────────────────────────────────────────────
        resultado = viajes_en_ejecucion(db=db, current_user=current_user)

        # ── Assert ───────────────────────────────────────────────
        assert isinstance(resultado, list)
        assert len(resultado) == 2

        # Verificar coordenadas GPS del primer viaje (esenciales para el mapa)
        v1_data = resultado[0]
        assert v1_data["latitud_origen"] == -0.1807
        assert v1_data["longitud_origen"] == -78.4678
        assert v1_data["latitud_destino"] == -2.1708
        assert v1_data["longitud_destino"] == -79.9224
        assert v1_data["latitud_actual"] == -1.2500
        assert v1_data["longitud_actual"] == -79.2000

        # Verificar datos de monitoreo
        assert v1_data["codigo"] == "VJ-001"
        assert v1_data["origen"] == "QUITO"
        assert v1_data["destino"] == "GUAYAQUIL"
        assert v1_data["transportista_nombres"] == "Carlos Pérez"
        assert v1_data["placa_vehiculo"] == "ABC-1234"

        # Verificar que el Decorator Visual añadió los campos de decoración
        assert "decoracion_alerta" in v1_data
        assert "decoracion_color" in v1_data
        assert "decoracion_mensaje" in v1_data
        assert "decoracion_clima" in v1_data

    def test_viajes_en_ejecucion_sin_viajes_activos(self):
        """Retorna lista vacía cuando no hay viajes en ejecución."""
        # ── Arrange ──────────────────────────────────────────────
        db = Mock()
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

        current_user = Mock(id=100, rol="COORDINADOR")

        # ── Act ──────────────────────────────────────────────────
        resultado = viajes_en_ejecucion(db=db, current_user=current_user)

        # ── Assert ───────────────────────────────────────────────
        assert isinstance(resultado, list)
        assert len(resultado) == 0

    def test_viaje_con_retraso_muestra_alerta_alto_riesgo(self):
        """Un viaje con más de 2h de retraso es decorado como ALTO RIESGO."""
        # ── Arrange ──────────────────────────────────────────────
        v = _mock_viaje(viaje_id=5, codigo="VJ-RIESGO", horas_retraso=3.5)

        db = Mock()
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [v]

        current_user = Mock(id=100, rol="COORDINADOR")

        # ── Act ──────────────────────────────────────────────────
        resultado = viajes_en_ejecucion(db=db, current_user=current_user)

        # ── Assert ───────────────────────────────────────────────
        assert resultado[0]["decoracion_alerta"] == "ALTO RIESGO"
        assert resultado[0]["decoracion_color"] == "red"

    def test_viaje_sin_retraso_muestra_operacion_normal(self):
        """Un viaje sin retraso es decorado como OPERACIÓN NORMAL."""
        # ── Arrange ──────────────────────────────────────────────
        v = _mock_viaje(viaje_id=6, codigo="VJ-NORMAL", horas_retraso=0)

        db = Mock()
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [v]

        current_user = Mock(id=100, rol="COORDINADOR")

        # ── Act ──────────────────────────────────────────────────
        resultado = viajes_en_ejecucion(db=db, current_user=current_user)

        # ── Assert ───────────────────────────────────────────────
        assert resultado[0]["decoracion_alerta"] == "OPERACIÓN NORMAL"
        assert resultado[0]["decoracion_color"] == "green"


# ══════════════════════════════════════════════════════════════════════════════
# TESTS — Consultar Viaje Individual con Coordenadas para Mapa
# ══════════════════════════════════════════════════════════════════════════════


class TestObtenerViaje:
    """Pruebas para obtener_viaje (GET /api/viajes/{viaje_id}).
    Verifica que el detalle del viaje incluye coordenadas GPS para el mapa."""

    def test_obtener_viaje_con_coordenadas_gps(self):
        """El viaje retornado contiene todas las coordenadas para renderizar en Leaflet."""
        # ── Arrange ──────────────────────────────────────────────
        v = _mock_viaje(
            viaje_id=10, codigo="VJ-MAPA-001",
            lat_origen=-0.1807, lng_origen=-78.4678,
            lat_destino=-2.1708, lng_destino=-79.9224,
            lat_actual=-1.0000, lng_actual=-79.0000,
        )

        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = v

        current_user = Mock(id=50, rol="SECRETARIA")

        # ── Act ──────────────────────────────────────────────────
        resultado = obtener_viaje(viaje_id=10, db=db, current_user=current_user)

        # ── Assert ───────────────────────────────────────────────
        # Coordenadas de origen (marcador de inicio en mapa)
        assert resultado["latitud_origen"] == -0.1807
        assert resultado["longitud_origen"] == -78.4678

        # Coordenadas de destino (marcador de fin en mapa)
        assert resultado["latitud_destino"] == -2.1708
        assert resultado["longitud_destino"] == -79.9224

        # Coordenadas actuales (posición del vehículo en mapa)
        assert resultado["latitud_actual"] == -1.0000
        assert resultado["longitud_actual"] == -79.0000

        # Datos del viaje para info del mapa
        assert resultado["origen"] == "QUITO"
        assert resultado["destino"] == "GUAYAQUIL"
        assert resultado["transportista_nombres"] == "Carlos Pérez"
        assert resultado["placa_vehiculo"] == "ABC-1234"

    def test_obtener_viaje_no_encontrado(self):
        """Se lanza HTTP 404 si el viaje no existe."""
        # ── Arrange ──────────────────────────────────────────────
        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = None

        current_user = Mock(id=50, rol="SECRETARIA")

        # ── Act & Assert ─────────────────────────────────────────
        with pytest.raises(HTTPException) as exc_info:
            obtener_viaje(viaje_id=999, db=db, current_user=current_user)

        assert exc_info.value.status_code == 404
        assert "no encontrado" in exc_info.value.detail.lower()

    def test_obtener_viaje_sin_transportista(self):
        """Un viaje DISPONIBLE sin transportista aún tiene coordenadas de mapa."""
        # ── Arrange ──────────────────────────────────────────────
        v = _mock_viaje(
            viaje_id=20, codigo="VJ-DISP-001", estado="DISPONIBLE",
            transportista_nombres=None, placa=None, transportista_id=None,
        )

        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = v

        current_user = Mock(id=50, rol="SECRETARIA")

        # ── Act ──────────────────────────────────────────────────
        resultado = obtener_viaje(viaje_id=20, db=db, current_user=current_user)

        # ── Assert ───────────────────────────────────────────────
        # Las coordenadas del mapa deben estar presentes aunque no haya transportista
        assert resultado["latitud_origen"] is not None
        assert resultado["longitud_origen"] is not None
        assert resultado["latitud_destino"] is not None
        assert resultado["longitud_destino"] is not None

        # Sin transportista asignado
        assert resultado["transportista_nombres"] is None
        assert resultado["placa_vehiculo"] is None


# ══════════════════════════════════════════════════════════════════════════════
# TESTS — Listar Viajes (para vista general del mapa)
# ══════════════════════════════════════════════════════════════════════════════


class TestListarViajes:
    """Pruebas para listar_viajes (GET /api/viajes/).
    Verifica el listado de viajes con datos de mapa."""

    def test_listar_viajes_retorna_coordenadas(self):
        """Cada viaje del listado incluye coordenadas GPS para el mapa."""
        # ── Arrange ──────────────────────────────────────────────
        v1 = _mock_viaje(viaje_id=1, codigo="VJ-001")
        v2 = _mock_viaje(viaje_id=2, codigo="VJ-002", origen="CUENCA", destino="LOJA")

        db = Mock()
        # current_user con rol no-TRANSPORTISTA → sin filtro adicional
        current_user = Mock(id=50)
        current_user.rol = Mock()
        current_user.rol.value = "SECRETARIA"
        type(current_user.rol).value = "SECRETARIA"

        db.query.return_value.order_by.return_value.all.return_value = [v1, v2]

        # ── Act ──────────────────────────────────────────────────
        resultado = listar_viajes(db=db, current_user=current_user)

        # ── Assert ───────────────────────────────────────────────
        assert isinstance(resultado, list)
        assert len(resultado) == 2

        # Ambos viajes deben tener coordenadas para el mapa
        for viaje_data in resultado:
            assert "latitud_origen" in viaje_data
            assert "longitud_origen" in viaje_data
            assert "latitud_destino" in viaje_data
            assert "longitud_destino" in viaje_data
            assert "latitud_actual" in viaje_data
            assert "longitud_actual" in viaje_data

    def test_listar_viajes_vacio(self):
        """Retorna lista vacía cuando no hay viajes registrados."""
        # ── Arrange ──────────────────────────────────────────────
        db = Mock()
        current_user = Mock(id=50)
        current_user.rol = Mock()
        current_user.rol.value = "SECRETARIA"
        type(current_user.rol).value = "SECRETARIA"

        db.query.return_value.order_by.return_value.all.return_value = []

        # ── Act ──────────────────────────────────────────────────
        resultado = listar_viajes(db=db, current_user=current_user)

        # ── Assert ───────────────────────────────────────────────
        assert isinstance(resultado, list)
        assert len(resultado) == 0
