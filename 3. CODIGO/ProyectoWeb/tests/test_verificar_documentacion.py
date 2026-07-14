# tests/test_verificar_documentacion.py
"""
REQ007 - Verificar Documentación
Descripción:
  Como Secretaria necesito: Validar documentación laboral de los transportistas.
  Así podré: Verificar la validez legal de la documentación para el sistema.

Funciones bajo prueba:
  - revisar_documento (PUT /api/transportistas/{transportista_id}/documentos/{doc_id}/revisar)

Patrón: AAA (Arrange – Act – Assert)
"""
from unittest.mock import Mock, patch
from datetime import datetime

# pyrefly: ignore [missing-import]
import pytest
# pyrefly: ignore [missing-import]
from fastapi import HTTPException

from routers.transportistas import revisar_documento
from schemas.transportista_schemas import RevisionDocumentoRequest
from models.models import Documento, EstadoDocEnum


class TestVerificarDocumentacion:
    """Pruebas unitarias para REQ007: Validar la documentación laboral."""

    @patch("routers.transportistas.registrar_auditoria")
    def test_revisar_documento_aprobado(self, mock_auditoria):
        """La secretaria aprueba correctamente un documento válido."""
        # ── Arrange ──────────────────────────────────────────────
        doc = Mock(spec=Documento)
        doc.id = 1
        doc.estado = EstadoDocEnum.PENDIENTE
        
        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = doc
        
        current_user = Mock(id=50, rol="SECRETARIA")
        request = Mock()
        request.client.host = "127.0.0.1"

        body = RevisionDocumentoRequest(
            estado="APROBADO",
            observacion="Documentación legal en orden.",
            fecha_vencimiento=datetime(2028, 1, 1)
        )

        # ── Act ──────────────────────────────────────────────────
        resultado = revisar_documento(
            transportista_id=10,
            doc_id=1,
            body=body,
            db=db,
            current_user=current_user,
            request=request,
        )

        # ── Assert ───────────────────────────────────────────────
        assert "aprobado correctamente" in resultado["mensaje"].lower()
        
        # Validar actualización de estado
        assert doc.estado == "APROBADO"
        assert doc.revisado_por_id == 50
        assert doc.observacion == "Documentación legal en orden."
        assert doc.fecha_vencimiento == datetime(2028, 1, 1)
        assert doc.revisado_en is not None

        db.commit.assert_called_once()
        mock_auditoria.assert_called_once()

    @patch("routers.transportistas.registrar_auditoria")
    def test_revisar_documento_rechazado_con_observacion(self, mock_auditoria):
        """La secretaria rechaza un documento y adjunta el motivo del rechazo."""
        # ── Arrange ──────────────────────────────────────────────
        doc = Mock(spec=Documento)
        doc.estado = EstadoDocEnum.PENDIENTE
        
        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = doc
        
        current_user = Mock(id=50, rol="SECRETARIA")
        request = Mock()
        
        body = RevisionDocumentoRequest(
            estado="RECHAZADO",
            observacion="El documento es ilegible.",
        )

        # ── Act ──────────────────────────────────────────────────
        resultado = revisar_documento(
            transportista_id=10,
            doc_id=1,
            body=body,
            db=db,
            current_user=current_user,
            request=request,
        )

        # ── Assert ───────────────────────────────────────────────
        assert "rechazado correctamente" in resultado["mensaje"].lower()
        assert doc.estado == "RECHAZADO"
        assert doc.observacion == "El documento es ilegible."
        db.commit.assert_called_once()

    def test_revisar_documento_rechazado_sin_observacion(self):
        """Si el documento es RECHAZADO, es obligatorio escribir una observación."""
        # ── Arrange ──────────────────────────────────────────────
        doc = Mock(spec=Documento)
        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = doc
        
        current_user = Mock(id=50, rol="SECRETARIA")
        
        body = RevisionDocumentoRequest(
            estado="RECHAZADO",
            observacion="",  # Falta motivo
        )

        # ── Act & Assert ─────────────────────────────────────────
        with pytest.raises(HTTPException) as exc_info:
            revisar_documento(
                transportista_id=10,
                doc_id=1,
                body=body,
                db=db,
                current_user=current_user,
            )
            
        assert exc_info.value.status_code == 400
        assert "debe proporcionar una observación" in exc_info.value.detail.lower()

    def test_revisar_documento_estado_invalido(self):
        """El estado de revisión debe ser obligatoriamente APROBADO o RECHAZADO."""
        # ── Arrange ──────────────────────────────────────────────
        doc = Mock(spec=Documento)
        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = doc
        
        current_user = Mock(id=50, rol="SECRETARIA")
        
        body = RevisionDocumentoRequest(
            estado="OTRO_ESTADO",  # Inválido
        )

        # ── Act & Assert ─────────────────────────────────────────
        with pytest.raises(HTTPException) as exc_info:
            revisar_documento(
                transportista_id=10,
                doc_id=1,
                body=body,
                db=db,
                current_user=current_user,
            )
            
        assert exc_info.value.status_code == 400
        assert "aprobado o rechazado" in exc_info.value.detail.lower()

    def test_revisar_documento_no_encontrado(self):
        """Si el documento no existe, lanza un HTTP 404."""
        # ── Arrange ──────────────────────────────────────────────
        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = None
        
        current_user = Mock(id=50, rol="SECRETARIA")
        
        body = RevisionDocumentoRequest(estado="APROBADO")

        # ── Act & Assert ─────────────────────────────────────────
        with pytest.raises(HTTPException) as exc_info:
            revisar_documento(
                transportista_id=10,
                doc_id=999,
                body=body,
                db=db,
                current_user=current_user,
            )
            
        assert exc_info.value.status_code == 404
        assert "no encontrado" in exc_info.value.detail.lower()
