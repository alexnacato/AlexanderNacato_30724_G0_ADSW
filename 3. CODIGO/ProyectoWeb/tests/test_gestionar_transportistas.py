# tests/test_gestionar_transportistas.py
"""
Pruebas unitarias para Gestionar Transportistas:
  Como Coordinador necesito ver un listado detallado de los transportistas.
  Así podré ver información detallada de cada transportista y su estado
  dentro del sistema.

Funciones bajo prueba:
  - listar_transportistas  (GET /api/transportistas/)
  - obtener_transportista  (GET /api/transportistas/{id})

Patrón: AAA (Arrange – Act – Assert)
"""
from unittest.mock import Mock, patch, PropertyMock
# pyrefly: ignore [missing-import]
import pytest 
# pyrefly: ignore [missing-import]
from fastapi import HTTPException

from routers.transportistas import listar_transportistas, obtener_transportista


# ── Helpers para construir mocks reutilizables ────────────────────────────────

def _mock_documento(doc_id=1, tipo="CEDULA", estado="APROBADO"):
    """Crea un mock de Documento con los atributos que usa _build_out."""
    doc = Mock()
    doc.id = doc_id
    doc.tipo = tipo
    doc.nombre_archivo = f"{tipo}_20260101.pdf"
    doc.estado = estado
    doc.fecha_vencimiento = None
    doc.observacion = None
    doc.subido_en = "2026-01-01T00:00:00"
    doc.revisado_en = None
    doc.contenido_pdf = b"%PDF-fake"
    return doc


def _mock_transportista(
    t_id=1, usuario_id=10, cedula="0102030405", nombres="Carlos Pérez",
    correo="carlos@correo.com", telefono="0991234567", direccion="Quito",
    placa="ABC-1234", tipo_vehiculo="Camión", capacidad_ton=5.0,
    activo=True, documentos=None,
):
    """Crea un mock de Transportista con su Usuario asociado."""
    usuario = Mock()
    usuario.cedula = cedula
    usuario.nombres = nombres
    usuario.correo = correo
    usuario.telefono = telefono
    usuario.direccion = direccion
    usuario.activo = activo

    t = Mock()
    t.id = t_id
    t.usuario_id = usuario_id
    t.usuario = usuario
    t.placa_vehiculo = placa
    t.tipo_vehiculo = tipo_vehiculo
    t.capacidad_ton = capacidad_ton
    t.documentos = documentos if documentos is not None else []
    return t


# ══════════════════════════════════════════════════════════════════════════════
# TESTS
# ══════════════════════════════════════════════════════════════════════════════


class TestListarTransportistas:
    """Pruebas para listar_transportistas (GET /api/transportistas/)."""

    def test_listar_transportistas_exitoso_con_datos(self):
        """El coordinador obtiene un listado con transportistas activos."""
        # ── Arrange ──────────────────────────────────────────────
        doc1 = _mock_documento(doc_id=1, tipo="CEDULA", estado="APROBADO")
        doc2 = _mock_documento(doc_id=2, tipo="LICENCIA_E", estado="PENDIENTE")

        t1 = _mock_transportista(
            t_id=1, nombres="Carlos Pérez", placa="ABC-1234",
            documentos=[doc1, doc2],
        )
        t2 = _mock_transportista(
            t_id=2, usuario_id=11, cedula="0506070809",
            nombres="María López", correo="maria@correo.com",
            placa="XYZ-5678", tipo_vehiculo="Furgoneta", capacidad_ton=3.0,
            documentos=[],
        )

        db = Mock()
        query_chain = db.query.return_value.join.return_value
        query_chain.filter.return_value.order_by.return_value.all.return_value = [t1, t2]

        current_user = Mock(id=100, rol="COORDINADOR")

        # ── Act ──────────────────────────────────────────────────
        resultado = listar_transportistas(solo_activos=True, db=db, current_user=current_user)

        # ── Assert ───────────────────────────────────────────────
        assert isinstance(resultado, list)
        assert len(resultado) == 2

        # Verificar datos del primer transportista
        assert resultado[0]["id"] == 1
        assert resultado[0]["nombres"] == "Carlos Pérez"
        assert resultado[0]["placa_vehiculo"] == "ABC-1234"
        assert resultado[0]["activo"] is True
        assert len(resultado[0]["documentos"]) == 2
        assert resultado[0]["estado_documentacion"] == "PENDIENTE"

        # Verificar datos del segundo transportista
        assert resultado[1]["id"] == 2
        assert resultado[1]["nombres"] == "María López"
        assert resultado[1]["placa_vehiculo"] == "XYZ-5678"
        assert resultado[1]["estado_documentacion"] == "SIN_DOCS"

    def test_listar_transportistas_lista_vacia(self):
        """El coordinador consulta y no hay transportistas registrados."""
        # ── Arrange ──────────────────────────────────────────────
        db = Mock()
        query_chain = db.query.return_value.join.return_value
        query_chain.filter.return_value.order_by.return_value.all.return_value = []

        current_user = Mock(id=100, rol="COORDINADOR")

        # ── Act ──────────────────────────────────────────────────
        resultado = listar_transportistas(solo_activos=True, db=db, current_user=current_user)

        # ── Assert ───────────────────────────────────────────────
        assert isinstance(resultado, list)
        assert len(resultado) == 0

    def test_listar_transportistas_incluye_inactivos(self):
        """El coordinador consulta con solo_activos=False y ve todos."""
        # ── Arrange ──────────────────────────────────────────────
        t_activo = _mock_transportista(t_id=1, nombres="Carlos Pérez", activo=True)
        t_inactivo = _mock_transportista(
            t_id=2, usuario_id=11, cedula="9999999999",
            nombres="Pedro Gómez", correo="pedro@correo.com",
            activo=False,
        )

        db = Mock()
        # Cuando solo_activos=False, NO se llama .filter(), va directo a .order_by()
        query_chain = db.query.return_value.join.return_value
        query_chain.order_by.return_value.all.return_value = [t_activo, t_inactivo]

        current_user = Mock(id=100, rol="COORDINADOR")

        # ── Act ──────────────────────────────────────────────────
        resultado = listar_transportistas(solo_activos=False, db=db, current_user=current_user)

        # ── Assert ───────────────────────────────────────────────
        assert len(resultado) == 2
        assert resultado[0]["activo"] is True
        assert resultado[1]["activo"] is False
        assert resultado[1]["nombres"] == "Pedro Gómez"

    def test_listar_transportistas_detalle_completo(self):
        """Verifica que cada transportista contiene TODOS los campos esperados."""
        # ── Arrange ──────────────────────────────────────────────
        doc = _mock_documento(doc_id=10, tipo="SOAT", estado="APROBADO")
        t = _mock_transportista(
            t_id=5, usuario_id=20, cedula="1234567890",
            nombres="Ana Torres", correo="ana@correo.com",
            telefono="0987654321", direccion="Guayaquil",
            placa="GYE-0001", tipo_vehiculo="Tráiler",
            capacidad_ton=20.0, documentos=[doc],
        )

        db = Mock()
        query_chain = db.query.return_value.join.return_value
        query_chain.filter.return_value.order_by.return_value.all.return_value = [t]

        current_user = Mock(id=100, rol="COORDINADOR")

        # ── Act ──────────────────────────────────────────────────
        resultado = listar_transportistas(solo_activos=True, db=db, current_user=current_user)

        # ── Assert ───────────────────────────────────────────────
        campos_esperados = [
            "id", "usuario_id", "cedula", "nombres", "correo",
            "telefono", "direccion", "placa_vehiculo", "tipo_vehiculo",
            "capacidad_ton", "activo", "documentos", "estado_documentacion",
        ]
        for campo in campos_esperados:
            assert campo in resultado[0], f"Falta el campo '{campo}' en la respuesta"

        # Verificar valores específicos
        assert resultado[0]["cedula"] == "1234567890"
        assert resultado[0]["telefono"] == "0987654321"
        assert resultado[0]["direccion"] == "Guayaquil"
        assert resultado[0]["tipo_vehiculo"] == "Tráiler"
        assert resultado[0]["capacidad_ton"] == 20.0
        assert resultado[0]["estado_documentacion"] == "APROBADO"

        # Verificar estructura del documento incluido
        doc_out = resultado[0]["documentos"][0]
        assert doc_out["id"] == 10
        assert doc_out["tipo"] == "SOAT"
        assert doc_out["estado"] == "APROBADO"
        assert doc_out["tiene_archivo"] is True


class TestObtenerTransportista:
    """Pruebas para obtener_transportista (GET /api/transportistas/{id})."""

    def test_obtener_transportista_exitoso(self):
        """El coordinador consulta un transportista existente por su ID."""
        # ── Arrange ──────────────────────────────────────────────
        doc = _mock_documento(doc_id=3, tipo="MATRICULA", estado="APROBADO")
        t = _mock_transportista(
            t_id=7, usuario_id=30, cedula="1112223334",
            nombres="Luis Ramírez", correo="luis@correo.com",
            placa="CUE-9999", tipo_vehiculo="Camioneta",
            capacidad_ton=2.5, documentos=[doc],
        )

        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = t

        current_user = Mock(id=100, rol="COORDINADOR")

        # ── Act ──────────────────────────────────────────────────
        resultado = obtener_transportista(
            transportista_id=7, db=db, current_user=current_user,
        )

        # ── Assert ───────────────────────────────────────────────
        assert resultado["id"] == 7
        assert resultado["nombres"] == "Luis Ramírez"
        assert resultado["cedula"] == "1112223334"
        assert resultado["correo"] == "luis@correo.com"
        assert resultado["placa_vehiculo"] == "CUE-9999"
        assert resultado["tipo_vehiculo"] == "Camioneta"
        assert resultado["capacidad_ton"] == 2.5
        assert resultado["activo"] is True
        assert len(resultado["documentos"]) == 1
        assert resultado["estado_documentacion"] == "APROBADO"

    def test_obtener_transportista_no_encontrado(self):
        """Se solicita un ID que no existe y se lanza HTTP 404."""
        # ── Arrange ──────────────────────────────────────────────
        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = None

        current_user = Mock(id=100, rol="COORDINADOR")

        # ── Act & Assert ─────────────────────────────────────────
        with pytest.raises(HTTPException) as exc_info:
            obtener_transportista(
                transportista_id=999, db=db, current_user=current_user,
            )

        assert exc_info.value.status_code == 404
        assert "no encontrado" in exc_info.value.detail.lower()

    def test_obtener_transportista_con_documentos_rechazados(self):
        """El estado de documentación es RECHAZADO si hay algún doc rechazado."""
        # ── Arrange ──────────────────────────────────────────────
        doc_ok = _mock_documento(doc_id=1, tipo="CEDULA", estado="APROBADO")
        doc_bad = _mock_documento(doc_id=2, tipo="LICENCIA_E", estado="RECHAZADO")

        t = _mock_transportista(
            t_id=3, nombres="Pedro Sánchez", documentos=[doc_ok, doc_bad],
        )

        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = t

        current_user = Mock(id=100, rol="COORDINADOR")

        # ── Act ──────────────────────────────────────────────────
        resultado = obtener_transportista(
            transportista_id=3, db=db, current_user=current_user,
        )

        # ── Assert ───────────────────────────────────────────────
        assert resultado["estado_documentacion"] == "RECHAZADO"
        assert len(resultado["documentos"]) == 2

    def test_obtener_transportista_sin_documentos(self):
        """El estado de documentación es SIN_DOCS cuando no tiene documentos."""
        # ── Arrange ──────────────────────────────────────────────
        t = _mock_transportista(t_id=4, nombres="Eva Mora", documentos=[])

        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = t

        current_user = Mock(id=100, rol="COORDINADOR")

        # ── Act ──────────────────────────────────────────────────
        resultado = obtener_transportista(
            transportista_id=4, db=db, current_user=current_user,
        )

        # ── Assert ───────────────────────────────────────────────
        assert resultado["estado_documentacion"] == "SIN_DOCS"
        assert resultado["documentos"] == []
