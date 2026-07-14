# tests/test_ingresar_documentacion.py
"""
REQ006 - Ingresar Documentación
Descripción:
  Como Transportista necesito: Cargar documentación laboral.
  Así podré: Tener asignación de viajes en el sistema.

Funciones bajo prueba:
  - importar_documento (POST /api/transportistas/{transportista_id}/documentos)

Patrón: AAA (Arrange – Act – Assert)
"""
from unittest.mock import AsyncMock, Mock, patch

# pyrefly: ignore [missing-import]
import pytest
# pyrefly: ignore [missing-import]
from fastapi import HTTPException, UploadFile

from routers.transportistas import importar_documento
from models.models import Transportista, Documento, EstadoDocEnum


def _mock_upload_file(content_type="application/pdf", content=b"%PDF-1.4...", filename="doc.pdf"):
    """Crea un mock de un archivo subido (UploadFile) con lectura asíncrona."""
    mock_file = AsyncMock(spec=UploadFile)
    mock_file.content_type = content_type
    mock_file.filename = filename
    mock_file.read.return_value = content
    return mock_file


@pytest.mark.anyio
class TestIngresarDocumentacion:
    """Pruebas unitarias para REQ006: Ingresar documentación del transportista."""

    @patch("routers.transportistas.settings")
    @patch("routers.transportistas.registrar_auditoria")
    async def test_importar_documento_exitoso(self, mock_auditoria, mock_settings):
        """Un transportista sube su documento PDF exitosamente (queda en PENDIENTE)."""
        # ── Arrange ──────────────────────────────────────────────
        mock_settings.MAX_FILE_SIZE_MB = 10
        
        transportista = Mock(spec=Transportista, id=5, usuario_id=10)
        db = Mock()
        # db.query() debe retornar el transportista, luego para el documento retornar None (nuevo doc)
        db.query.return_value.filter.return_value.first.side_effect = [transportista, None]
        
        # El current_user es el propio transportista (id=10 coincide con usuario_id del transportista id=5)
        current_user = Mock(id=10)
        current_user.rol = Mock()
        current_user.rol.value = "TRANSPORTISTA"
        type(current_user.rol).value = "TRANSPORTISTA"

        archivo = _mock_upload_file(content_type="application/pdf", content=b"fake-pdf-bytes")
        request = Mock()
        request.client.host = "127.0.0.1"

        # ── Act ──────────────────────────────────────────────────
        resultado = await importar_documento(
            transportista_id=5,
            tipo="LICENCIA_E",
            fecha_vencimiento="2028-01-01",
            archivo=archivo,
            db=db,
            current_user=current_user,
            request=request,
        )

        # ── Assert ───────────────────────────────────────────────
        assert "correctamente" in resultado["mensaje"].lower()
        assert resultado["tamano_kb"] == len(b"fake-pdf-bytes") // 1024
        
        # Verificar BD
        db.add.assert_called_once()
        doc_agregado = db.add.call_args[0][0]
        assert isinstance(doc_agregado, Documento)
        assert doc_agregado.tipo == "LICENCIA_E"
        assert doc_agregado.estado == EstadoDocEnum.PENDIENTE
        assert doc_agregado.contenido_pdf == b"fake-pdf-bytes"
        
        db.commit.assert_called_once()
        db.refresh.assert_called_once()
        mock_auditoria.assert_called_once()

    @patch("routers.transportistas.settings")
    async def test_importar_documento_otro_transportista_denegado(self, mock_settings):
        """Un transportista no puede subir documentos al perfil de OTRO transportista."""
        # ── Arrange ──────────────────────────────────────────────
        # Transportista de la URL (pertenece al usuario id 99)
        transportista = Mock(spec=Transportista, id=5, usuario_id=99)
        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = transportista
        
        # current_user es el transportista id=10 (intenta modificar al 99)
        current_user = Mock(id=10)
        current_user.rol = Mock()
        current_user.rol.value = "TRANSPORTISTA"
        type(current_user.rol).value = "TRANSPORTISTA"

        archivo = _mock_upload_file()

        # ── Act & Assert ─────────────────────────────────────────
        with pytest.raises(HTTPException) as exc_info:
            await importar_documento(
                transportista_id=5,
                tipo="CEDULA",
                archivo=archivo,
                db=db,
                current_user=current_user,
            )
            
        assert exc_info.value.status_code == 403
        assert "no tiene permiso" in exc_info.value.detail.lower()

    @patch("routers.transportistas.settings")
    async def test_importar_documento_tipo_invalido(self, mock_settings):
        """Se rechaza un documento con un tipo no reconocido."""
        # ── Arrange ──────────────────────────────────────────────
        transportista = Mock(spec=Transportista, id=5, usuario_id=10)
        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = transportista
        
        current_user = Mock(id=10)
        current_user.rol = Mock()
        current_user.rol.value = "TRANSPORTISTA"
        type(current_user.rol).value = "TRANSPORTISTA"

        archivo = _mock_upload_file()

        # ── Act & Assert ─────────────────────────────────────────
        with pytest.raises(HTTPException) as exc_info:
            await importar_documento(
                transportista_id=5,
                tipo="DIPLOMA_FALSO",  # Tipo inválido
                archivo=archivo,
                db=db,
                current_user=current_user,
            )
            
        assert exc_info.value.status_code == 400
        assert "tipo inválido" in exc_info.value.detail.lower()

    @patch("routers.transportistas.settings")
    async def test_importar_documento_no_es_pdf(self, mock_settings):
        """Se rechazan archivos que no sean PDF (ej. PNG, JPG, DOCX)."""
        # ── Arrange ──────────────────────────────────────────────
        transportista = Mock(spec=Transportista, id=5, usuario_id=10)
        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = transportista
        
        current_user = Mock(id=10)
        current_user.rol = Mock()
        current_user.rol.value = "TRANSPORTISTA"
        type(current_user.rol).value = "TRANSPORTISTA"

        # Archivo es una imagen en lugar de PDF
        archivo = _mock_upload_file(content_type="image/png", filename="foto.png")

        # ── Act & Assert ─────────────────────────────────────────
        with pytest.raises(HTTPException) as exc_info:
            await importar_documento(
                transportista_id=5,
                tipo="CEDULA",
                archivo=archivo,
                db=db,
                current_user=current_user,
            )
            
        assert exc_info.value.status_code == 400
        assert "solo se aceptan archivos en formato pdf" in exc_info.value.detail.lower()

    @patch("routers.transportistas.settings")
    async def test_importar_documento_excede_limite_peso(self, mock_settings):
        """Se rechaza un PDF si su peso excede el límite permitido (ej. 10MB)."""
        # ── Arrange ──────────────────────────────────────────────
        # Simulamos un límite pequeño: 1 MB
        mock_settings.MAX_FILE_SIZE_MB = 1
        
        transportista = Mock(spec=Transportista, id=5, usuario_id=10)
        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = transportista
        
        current_user = Mock(id=10)
        current_user.rol = Mock()
        current_user.rol.value = "TRANSPORTISTA"
        type(current_user.rol).value = "TRANSPORTISTA"

        # Archivo pesa 2 MB (excede 1 MB)
        contenido_pesado = b"0" * (2 * 1024 * 1024)
        archivo = _mock_upload_file(content=contenido_pesado)

        # ── Act & Assert ─────────────────────────────────────────
        with pytest.raises(HTTPException) as exc_info:
            await importar_documento(
                transportista_id=5,
                tipo="CEDULA",
                archivo=archivo,
                db=db,
                current_user=current_user,
            )
            
        assert exc_info.value.status_code == 400
        assert "excede el límite" in exc_info.value.detail.lower()
