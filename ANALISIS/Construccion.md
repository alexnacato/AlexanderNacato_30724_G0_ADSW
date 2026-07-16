# TransControl - Sistema de Gestión y Control de Viajes (SGCV)

## 📌 Descripción del Proyecto

Sistema web para la gestión y control de viajes de transporte, desarrollado como proyecto final de la asignatura **Pruebas de Software 30729** de la Universidad de las Fuerzas Armadas ESPE. Permite la administración de transportistas, validación de documentos obligatorios (6 tipos), despacho de viajes, monitoreo GPS de rutas en tiempo real y auditoría de todas las operaciones del sistema.

## 🏗️ Fase de Construcción del Software — Justificación

El presente README se enmarca en la **fase de construcción del ciclo de vida del software**, donde se implementa el diseño arquitectónico y detallado definido en fases anteriores. La construcción de SGCV abarca:

- **Traducción del diseño a código fuente**: Implementación de una API RESTful con FastAPI + SQLAlchemy, y un frontend SPA con JavaScript vanilla + Tailwind CSS.
- **Integración de componentes**: Conexión backend-frontend mediante Nginx como proxy inverso, y PostgreSQL como motor de base de datos (todo orquestado en un único contenedor Docker con Supervisor).
- **Aplicación de patrones de diseño**: Se implementan los patrones **Adapter** (conversión ciudad → coordenadas GPS), **Strategy** (algoritmos de geolocalización real/simulada), **Observer** (notificaciones y auditoría al modificar rutas) y **Decorator** (enriquecimiento visual de datos de viaje).
- **Verificación e integración continua**: Pruebas E2E con Cypress (~70 casos), pruebas de caja blanca (API, 86 casos documentados) y seed de datos precargados para validación funcional.

## 🧩 Funcionalidades por Rol

### 👤 Coordinador
- CRUD completo de transportistas (alta, edición, eliminación lógica/permanente, reactivación)
- Validación de cédula ecuatoriana con algoritmo de dígito verificador
- Monitoreo de viajes activos en mapa interactivo (Leaflet.js)
- Modificación de rutas con justificación y notificaciones

### 👤 Secretaria
- Revisión y aprobación/rechazo de documentos (con observaciones obligatorias en rechazo)
- Creación, asignación, cancelación y reprogramación de viajes
- Filtrado de viajes por estado (DISPONIBLE, ASIGNADO, EN_EJECUCIÓN, etc.)

### 👤 Transportista
- Subida de documentos PDF (máx. 2 MB) con arrastrar y soltar
- Visualización del estado de cada documento con códigos de color
- Consulta del viaje activo asignado

### 👤 Gerente / Presidente
- Visualización del módulo de monitoreo
- Consulta del registro de auditoría (traza de todas las operaciones)

## 🛠️ Stack Tecnológico

| Capa          | Tecnología                                          |
|---------------|------------------------------------------------------|
| Frontend      | HTML5, JavaScript vanilla, Tailwind CSS, Leaflet.js  |
| Backend       | Python 3.10+, FastAPI, SQLAlchemy 2.0, Pydantic v2   |
| Base de datos | PostgreSQL 17                                        |
| Autenticación | JWT + bcrypt                                         |
| Proxy/Servir  | Nginx                                                |
| Contenedor    | Docker + Docker Compose (imagen única multi-servicio)|
| Testing E2E   | Cypress (~70 tests)                                  |

## 🏛️ Arquitectura

                    Nginx (puerto 80)
                   ┌──────────────────┐
                   │  / → Frontend    │
                   │  /api/* → FastAPI│
                   │  /uploads/* → FS │
                   └──────┬───────────┘
                          │
          ┌───────────────┴───────────────┐
          │                               │
    FastAPI (8000)                  Archivos estáticos
 ┌──────────────┐                   /usr/share/nginx/html
 │  Routers      │
 │  - auth       │
 │  - viajes     │
 │  - monitoreo  │
 │  - transport. │
 └──────┬───────-┘
        │
 ┌──────┴───────┐
 │  PostgreSQL   │
 │  (puerto 5432)│
 └──────────────┘

### Patrones de Diseño Implementados

1. **Adapter** — `patterns/adapter/city_gps_adapter.py`: Convierte nombres de ciudades en coordenadas GPS.
2. **Strategy** — `patterns/strategy/gps_tracking_strategy.py`: Estrategias intercambiables de geolocalización (real vs. simulada por interpolación lineal).
3. **Observer** — `patterns/observer/trip_observer.py`: `TripSubject` notifica a `AuditObserver` (persistencia) y `NotificationObserver` (push/SMS simulado).
4. **Decorator** — `patterns/decorator/viaje_visual_decorator.py`: Agrega atributos visuales (color, ícono, mensaje) a los viajes según estado y demora.

### Esquema de Base de Datos

| Tabla           | Descripción                                       |
|-----------------|---------------------------------------------------|
| `usuarios`      | Usuarios del sistema (5 roles: enum)              |
| `transportistas`| Perfiles de conductores (1:1 con usuarios)        |
| `documentos`    | Documentos PDF almacenados en BYTEA (6 tipos)     |
| `viajes`        | Viajes con coordenadas GPS y máquina de estados   |
| `auditoria`     | Log inmutable de operaciones (BIGSERIAL)          |

## 🚀 Instalación y Ejecución

### Requisitos
- Node.js v18+, Python 3.10+, Docker Desktop, Git

### Con Docker (recomendado)
```bash
git clone https://github.com/Tenkenoz/Sistema-de-gesti-n-y-control-de-asistencias.git
cd Sistema-de-gesti-n-y-control-de-asistencias
npm install
docker-compose up -d --build
npm start
Manual (desarrollo)
# Terminal 1 — Backend
cd Backend && pip install -r requirements.txt && uvicorn main:app --reload --port 8000

# Terminal 2 — Frontend
npm start   # http-server en puerto 3000
Acceso
Servicio	URL
Frontend	http://localhost:3000 (http://localhost:3000)
API	http://localhost:8000 (http://localhost:8000)
Swagger	http://localhost:8000/docs (http://localhost:8000/docs)
Credenciales de Prueba
Rol	Email
Secretaria	secretaria@transcontrol.ec (mailto:secretaria@transcontrol.ec)
Coordinador	coordinador@transcontrol.ec (mailto:coordinador@transcontrol.ec)
Transportista	transportista@transcontrol.ec (mailto:transportista@transcontrol.ec)
Gerente	admin@transcontrol.ec (mailto:admin@transcontrol.ec)
🧪 Testing
- Pruebas E2E (Cypress): ~70 tests en /Frontend/cypress/E2E/ — cubren login, coordinador (20), secretaria (20), transportista (18).
- Pruebas de caja blanca: 86 casos documentados en Test/caja_blanca/test_casos.md, ejecutables desde Test/caja_blanca/test.html.
- Pruebas de caja negra: Directorio preparado en Test/caja_negra/.
👥 Autores
- Jonathan Jaguaco
- Alexander Nacato
- Leidy Saraguro
- Erick Obando
Curso: Pruebas de Software 30729 — Universidad de las Fuerzas Armadas ESPE
