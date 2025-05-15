# Plan de Desarrollo: Sistema IA para Soluciones de Agua

## Visión General

Este documento detalla el plan de desarrollo para completar y mejorar el sistema de IA especializado en soluciones de agua "H₂O Allegiant". El sistema permite a los usuarios obtener propuestas técnicas personalizadas para tratamiento de agua mediante un cuestionario interactivo con IA, subida de documentos técnicos, y generación automática de propuestas con base de conocimiento especializada.

## Principios de Diseño

- **Modularidad**: Componentes desacoplados para mantenimiento sencillo
- **Simplicidad**: Sistema fácil de entender y modificar
- **Rendimiento**: Tenemos que pensar en el rendimiento y optimizacion tambien del proyecto
- **Experiencia de Usuario**: Interfaz intuitiva y flujo de conversación natural

## Estado Actual

El sistema cuenta con los siguientes componentes funcionales:
- Backend FastAPI con autenticación JWT
- Frontend Next.js con interfaz de chat
- Modelo de IA para guiar cuestionario técnico
- Generación básica de propuestas en PDF
- Estructura de base de datos PostgreSQL
- Sistema básico de subida de archivos

## Plan de Trabajo

### Fase 1: Refactorización de Gestión de Conversaciones (2 semanas)

#### Objetivos:
- Modificar el sistema para siempre iniciar conversaciones nuevas
- Crear sección de historial para consulta de conversaciones pasadas
- Mejorar la experiencia de inicio de conversación

#### Tareas:
1. **Frontend: Modificar ChatContainer**
   - [ ] Eliminar lógica de continuación automática de conversaciones
   - [ ] Implementar botón claro para "Nueva Conversación"
   - [ ] Mejorar indicadores visuales de estado de conversación

2. **Frontend: Crear Vista de Historial**
   - [ ] Diseñar e implementar página de historial de conversaciones
   - [ ] Añadir visualización de PDFs generados anteriormente
   - [ ] Implementar búsqueda y filtrado de conversaciones

3. **Backend: Refactorizar API de Conversaciones**
   - [ ] Modificar lógica para reiniciar contexto en cada inicio
   - [ ] Mejorar endpoints para historial de conversaciones
   - [ ] Optimizar metadata de conversaciones

### Fase 2: Implementación del Sistema de Procesamiento de Documentos (3 semanas)

#### Objetivos:
- Crear pipeline modular para procesar diferentes tipos de documentos
- Extraer información relevante de archivos subidos por usuarios
- Integrar información extraída en el contexto de conversación

#### Tareas:
1. **Procesadores de Documentos**
   - [ ] Implementar extractor de texto para PDFs técnicos (PyPDF2/pdfplumber)
   - [ ] Integrar OCR para imágenes y facturas escaneadas (Tesseract)
   - [ ] Desarrollar parser específico para análisis de agua

2. **Almacenamiento y Gestión**
   - [ ] Configurar almacenamiento S3/MinIO para archivos
   - [ ] Implementar sistema de versionado y metadatos
   - [ ] Crear vistas para documentos procesados

3. **Integración con Conversaciones**
   - [ ] Modificar sistema de prompt para incluir información extraída
   - [ ] Mejorar UI para subida y visualización de documentos
   - [ ] Implementar respuestas contextuales basadas en documentos

### Fase 3: Implementación de RAG (Retrieval Augmented Generation) (4 semanas)

#### Objetivos:
- Crear base de conocimiento vectorial sobre soluciones de agua
- Implementar sistema de consulta semántica para propuestas precisas
- Mejorar calidad técnica de propuestas generadas

#### Tareas:
1. **Infraestructura Vectorial**
   - [ ] Configurar pgvector en PostgreSQL
   - [ ] Implementar modelos de embedding (OpenAI o local)
   - [ ] Crear esquemas y tablas para vectores

2. **Base de Conocimiento**
   - [ ] Estructurar y preparar documentos técnicos
   - [ ] Implementar chunking y vectorización de documentos
   - [ ] Desarrollar sistema de actualización de conocimiento

3. **Integración con Generación de Propuestas**
   - [ ] Modificar proceso de generación para consultar RAG
   - [ ] Implementar prompt especializado con información recuperada
   - [ ] Añadir referencias técnicas específicas en propuestas

### Fase 4: Mejoras en Generador de PDF (2 semanas)

#### Objetivos:
- Mejorar diseño visual y estructura de propuestas
- Añadir elementos técnicos avanzados (gráficos, diagramas)
- Optimizar rendimiento de generación

#### Tareas:
1. **Diseño Mejorado**
   - [ ] Implementar plantillas profesionales
   - [ ] Añadir estilos personalizados por sector
   - [ ] Mejorar tipografía y espaciado

2. **Contenido Enriquecido**
   - [ ] Incorporar tablas técnicas dinámicas
   - [ ] Añadir diagramas básicos de procesos
   - [ ] Incluir referencias técnicas con citas

3. **Optimización**
   - [ ] Mejorar manejo de concurrencia
   - [ ] Implementar generación asíncrona
   - [ ] Añadir compresión y optimización de tamaño

### Fase 5: Pruebas, Optimización y Despliegue (3 semanas)

#### Objetivos:
- Garantizar estabilidad del sistema completo
- Optimizar rendimiento en todos los componentes
- Preparar para despliegue en AWS

#### Tareas:
1. **Testing**
   - [ ] Implementar pruebas unitarias para nuevos componentes
   - [ ] Realizar pruebas de integración end-to-end
   - [ ] Ejecutar pruebas de carga y rendimiento

2. **Optimización**
   - [ ] Revisar y optimizar consultas a la base de datos
   - [ ] Mejorar cache y rendimiento de API
   - [ ] Optimizar uso de recursos en contenedores

3. **Despliegue**
   - [ ] Configurar infraestructura AWS (ECS/EKS)
   - [ ] Implementar CI/CD para despliegue automatizado
   - [ ] Configurar monitoreo y alertas

## Estructura Técnica

### Componentes Backend

```
app/
├── api/                # API endpoints
├── services/           # Lógica de negocio
│   ├── ai_service.py   # Servicio de IA (existente)
│   ├── document_processor/ # Nuevo procesador de documentos
│   │   ├── pdf_processor.py
│   │   ├── image_processor.py
│   │   └── analysis_processor.py
│   ├── rag_service.py  # Nuevo servicio RAG
│   └── proposal_service.py # Mejorado con RAG
├── db/
│   └── models/         # Añadir nuevos modelos para RAG
└── repositories/       # Acceso a datos
```

### Componentes Frontend

```
src/
├── app/
│   ├── chat/          # Módulo de chat (mejorado)
│   └── history/       # Nueva sección de historial
├── components/
│   ├── chat/          # Componentes de chat
│   ├── documents/     # Nuevos componentes para documentos
│   └── proposals/     # Visualización de propuestas
```

### Diagrama de Base de Datos

```
┌────────────────┐      ┌───────────────┐      ┌────────────────┐
│    users       │      │ conversations │      │    messages    │
├────────────────┤      ├───────────────┤      ├────────────────┤
│ id             │──┐   │ id            │──┐   │ id             │
│ email          │  │   │ user_id       │◄─┘   │ conversation_id│◄─┐
│ password_hash  │  └──►│ metadata      │      │ role           │  │
│ name           │      │ ...           │      │ content        │  │
└────────────────┘      └───────┬───────┘      └────────────────┘  │
                                │                                   │
                                └───────────────┐                   │
                                                │                   │
┌────────────────┐      ┌───────────────┐      │                   │
│ knowledge_base │      │  documents    │      │                   │
├────────────────┤      ├───────────────┤      │                   │
│ id             │      │ id            │      │                   │
│ content        │      │ conversation_id│◄─────┘                   │
│ embedding      │      │ file_path     │                          │
│ metadata       │      │ content_type  │                          │
└────────────────┘      │ processed_text│                          │
                        └───────────────┘                          │
                                                                   │
┌────────────────┐      ┌───────────────┐                          │
│ document_chunks│      │  proposals    │                          │
├────────────────┤      ├───────────────┤                          │
│ id             │      │ id            │                          │
│ document_id    │      │ conversation_id│◄─────────────────────────┘
│ content        │      │ pdf_path      │
│ embedding      │      │ created_at    │
└────────────────┘      └───────────────┘
```

## Prioridades y Dependencias

### Ordenadas por prioridad:
1. Refactorización de Gestión de Conversaciones
2. Sistema de Procesamiento de Documentos
3. Implementación de RAG
4. Mejoras en Generador de PDF
5. Pruebas y Despliegue

### Dependencias críticas:
- RAG depende de tener pgvector configurado correctamente
- Procesamiento de documentos necesita S3/MinIO configurado
- Mejoras en propuestas dependen de RAG funcionando


## Medidas de Éxito

- Tiempo reducido para generar propuestas técnicas
- Mayor precisión técnica en propuestas generadas
- Capacidad de procesar al menos 5 tipos diferentes de documentos técnicos
- Tasa de conversión mejorada en landing page
- Feedback positivo de usuarios sobre calidad de propuestas

## Próximos Pasos Inmediatos

1. Finalizar y aprobar este plan de desarrollo
2. Iniciar refactorización de conversaciones para siempre iniciar nuevas
3. Diseñar e implementar la arquitectura para el procesador de documentos
4. Comenzar la configuración de pgvector para RAG
