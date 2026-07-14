# tests/test_creacion_base_datos.py
"""
REQ013 - Creación de Base de Datos
Descripción:
  Como Coordinador necesito: Crear una base de datos relacional con roles y permisos del sistema.
  Así podré: Administrar y controlar toda la información de transportistas, viajes y documentos de forma organizada.

Patrón: AAA (Arrange – Act – Assert)
En este caso, se valida que los modelos ORM de SQLAlchemy (que definen la BD relacional)
estén estructurados y relacionados correctamente.
"""
from unittest.mock import Mock

# pyrefly: ignore [missing-import]
import pytest
from sqlalchemy import inspection

from models.models import Usuario, Transportista, Viaje, Documento, RolEnum


class TestCreacionBaseDatos:
    """Pruebas para validar la estructura de la base de datos relacional (REQ013)."""

    def test_tabla_usuarios_y_roles(self):
        """Valida que la tabla 'usuarios' exista y soporte el sistema de roles y permisos."""
        # ── Arrange / Act ─────────────────────────────────────────
        # Usamos la inspección de SQLAlchemy para ver los metadatos de la clase
        mapper = inspection.inspect(Usuario)
        
        # ── Assert ───────────────────────────────────────────────
        assert mapper.mapped_table.name == "usuarios"
        
        columnas = {col.name: col for col in mapper.columns}
        
        # Debe tener los campos clave de control
        assert "id" in columnas
        assert "cedula" in columnas
        assert "rol" in columnas
        assert "activo" in columnas
        assert "hashed_password" in columnas
        
        # Validar los roles disponibles en el Enum
        roles_esperados = ["GERENTE", "SECRETARIA", "COORDINADOR", "TRANSPORTISTA", "PRESIDENTE"]
        roles_actuales = [r.value for r in RolEnum]
        
        for rol in roles_esperados:
            assert rol in roles_actuales

    def test_tabla_transportistas_y_relaciones(self):
        """Valida que la tabla 'transportistas' esté relacionada 1 a 1 con 'usuarios'."""
        # ── Arrange / Act ─────────────────────────────────────────
        mapper = inspection.inspect(Transportista)
        
        # ── Assert ───────────────────────────────────────────────
        assert mapper.mapped_table.name == "transportistas"
        
        columnas = {col.name: col for col in mapper.columns}
        
        # Validar columnas de vehículos
        assert "placa_vehiculo" in columnas
        assert "capacidad_ton" in columnas
        
        # Validar la clave foránea hacia usuarios (relacional)
        col_usuario_id = columnas["usuario_id"]
        assert len(col_usuario_id.foreign_keys) == 1
        
        # Obtener el target de la FK (debería ser usuarios.id)
        fk = list(col_usuario_id.foreign_keys)[0]
        assert fk.target_fullname == "usuarios.id"

    def test_tabla_viajes(self):
        """Valida que la tabla 'viajes' exista y esté vinculada a un transportista."""
        # ── Arrange / Act ─────────────────────────────────────────
        mapper = inspection.inspect(Viaje)
        
        # ── Assert ───────────────────────────────────────────────
        assert mapper.mapped_table.name == "viajes"
        
        columnas = {col.name: col for col in mapper.columns}
        
        # Validar control de cargas laborales y operativas
        assert "origen" in columnas
        assert "destino" in columnas
        assert "estado" in columnas
        assert "latitud_actual" in columnas
        
        # Validar clave foránea hacia transportistas
        col_transportista_id = columnas["transportista_id"]
        assert len(col_transportista_id.foreign_keys) == 1
        fk = list(col_transportista_id.foreign_keys)[0]
        assert fk.target_fullname == "transportistas.id"

    def test_tabla_documentos(self):
        """Valida la tabla 'documentos' para organizar el archivo legal de los transportistas."""
        # ── Arrange / Act ─────────────────────────────────────────
        mapper = inspection.inspect(Documento)
        
        # ── Assert ───────────────────────────────────────────────
        assert mapper.mapped_table.name == "documentos"
        
        columnas = {col.name: col for col in mapper.columns}
        
        assert "tipo" in columnas
        assert "estado" in columnas
        assert "contenido_pdf" in columnas # Donde se almacenarán los bytes (BYTEA)
        
        # Validar relación con el dueño del documento
        col_transportista_id = columnas["transportista_id"]
        assert len(col_transportista_id.foreign_keys) == 1
        fk = list(col_transportista_id.foreign_keys)[0]
        assert fk.target_fullname == "transportistas.id"
