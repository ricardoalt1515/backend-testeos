# Guía Técnica del Chatbot Hydrous

## Arquitectura del Sistema

El chatbot de Hydrous utiliza una arquitectura basada en servicios con los siguientes componentes principales:

1. **Rutas (routes/)** - Endpoints API que manejan las solicitudes HTTP
2. **Servicios (services/)** - Lógica de negocio para cada funcionalidad
3. **Modelos (models/)** - Estructuras de datos para la información manejada
4. **Utilidades (utils/)** - Funciones auxiliares y herramientas

### Diagrama de Flujo
Usuario -> API Routes -> Services -> Models -> Storage
-> AI Service -> External AI API
-> Document Service -> File Storage
-> Questionnaire Service -> PDF Generation

## Flujo Principal del Chatbot

1. **Inicio de Conversación**
   - El usuario envía cualquier mensaje
   - El sistema crea una nueva conversación y comienza el cuestionario automáticamente
   - El chatbot muestra el saludo inicial y pregunta por el sector

2. **Flujo del Cuestionario**
   - El sistema guía al usuario a través del cuestionario específico para su sector/subsector
   - Cada 5 preguntas se muestra un resumen de la información recopilada
   - Se solicitan documentos en momentos estratégicos del cuestionario

3. **Generación de Propuesta**
   - Al completar el cuestionario, se genera automáticamente una propuesta personalizada
   - Se ofrece la opción de descargar la propuesta en formato PDF
   - El sistema continúa respondiendo preguntas sobre la propuesta

## Mantenimiento y Mejoras

### Añadir Nuevos Sectores o Subsectores

Para añadir un nuevo sector o subsector, siga estos pasos:

1. Editar el archivo `app/data/questionnaire_complete.json`
2. Añadir el nuevo sector/subsector en la sección correspondiente
3. Crear el listado de preguntas específicas para ese sector/subsector
4. Añadir datos interesantes en la sección "facts"

### Modificar el Formato de Propuesta

Para cambiar el formato de las propuestas generadas:

1. Editar la función `format_proposal_summary` en `questionnaire_service.py`
2. Modificar la función `generate_proposal_pdf` para actualizar el diseño del PDF

### Actualizar los Mensajes del Chatbot

Para modificar los mensajes y el tono del chatbot:

1. Editar las funciones en `ai_service.py` que generan respuestas
2. Prestar especial atención a `format_response_with_questions` y `get_initial_greeting`

## Monitoreo y Análisis

El sistema incluye herramientas para monitoreo y análisis:

- **Logs** - Se registran eventos importantes en los archivos de log
- **Analytics** - Se recopilan métricas de uso y conversión
- **Alertas** - Se envían notificaciones por correo ante errores críticos

### Acceso a Métricas

Las métricas se almacenan en archivos JSON en el directorio `analytics/`:
- `usage.json` - Métricas generales de uso
- `conversions.json` - Detalles de conversaciones completadas
- `issues.json` - Registro de problemas y errores

## Solución de Problemas Comunes

### El chatbot se queda atascado en una pregunta

1. Verificar que el estado del cuestionario sea consistente
2. Revisar los logs para identificar posibles errores
3. Si es necesario, reiniciar la conversación

### Error al generar PDF

1. Verificar que las dependencias para generación de PDF estén instaladas
2. Comprobar permisos de escritura en el directorio de uploads
3. Revisar que los datos de la propuesta sean completos y válidos

### Rendimiento lento en conversaciones largas

1. Verificar la función `_optimize_context_length` para asegurar que se está limitando el contexto
2. Considerar ajustar los parámetros de la API de IA para reducir tiempo de respuesta
