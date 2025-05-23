# Problema de conexión entre frontend en Vercel (HTTPS) y backend en AWS (HTTP)

## Arquitectura actual

### Frontend
- **Plataforma**: Vercel
- **Framework**: Next.js
- **URL**: https://www.h2oassistant.com
- **Protocolo**: HTTPS
- **Repositorio**: /Users/ricardoaltamirano/Documents/backend-testeos/hydrous-chat

### Backend
- **Plataforma**: AWS
- **Componentes**:
  - FastAPI con Python 3.11
  - PostgreSQL con pgvector
  - Redis para caché y rate limiting
  - Autenticación JWT
  - Integración con APIs de OpenAI/Groq
- **Infraestructura**:
  - Amazon RDS para PostgreSQL (db.t3.micro)
  - Amazon ElastiCache para Redis (cache.t3.micro)
  - Amazon ECR para almacenar la imagen Docker
  - Amazon ECS con Fargate para ejecutar el contenedor
  - Application Load Balancer para exponer la API
- **URL inicial**: http://hydrous-alb-1088098552.us-east-1.elb.amazonaws.com (HTTP)
- **URL nueva**: https://api.h2oassistant.com (HTTPS)

## Problema inicial

- El frontend no podía conectarse al backend cuando intentaba hacer peticiones de registro o login
- Error mostrado al usuario: "Connection error. Please check your internet connection and try again."
- En la consola del navegador aparecían errores de timeout: "timeout of 60000ms exceeded"
- En los logs del backend en AWS no aparecía ninguna actividad cuando se intentaban hacer estas peticiones
- El error específico era: `AxiosError, code: "ECONNABORTED"`

## Pruebas iniciales realizadas

1. **Acceso directo al backend HTTP**:
   - Curl al endpoint de salud: `curl -v http://hydrous-alb-1088098552.us-east-1.elb.amazonaws.com/api/health`
   - Resultado: Funciona correctamente, devuelve `{"status":"ok","version":"1.0.0"}`

2. **Proxy con Next.js rewrites**:
   ```javascript
   async rewrites() {
     return [
       {
         source: '/api/:path*',
         destination: 'http://hydrous-alb-1088098552.us-east-1.elb.amazonaws.com/api/:path*',
       },
     ];
   }
   ```
   - Resultado: No funciona, timeout después de 60 segundos

3. **Proxy mediante API Routes en Next.js**:
   - Implementado en `/src/app/api/proxy/[...path]/route.ts`
   - Resultado: No funciona, timeout después de 60 segundos

4. **Test simple con endpoint de prueba**:
   - Endpoint de prueba simple: `/api/test` que hace GET a `/api/health` del backend
   - Resultado: Funciona correctamente, devuelve `{"success":true,"data":{"status":"ok","version":"1.0.0"}}`

## Configuraciones actuales

### API Client (Frontend)
```typescript
// src/lib/api-client.ts
const apiBaseUrl = process.env.NEXT_PUBLIC_USE_LOCAL_BACKEND === 'true'
  ? 'http://localhost:8000/api'  // Para desarrollo local
  : '/api';  // Ruta relativa en producción
```

### Proxy API Route
```typescript
// src/app/api/proxy/[...path]/route.ts
const BACKEND_BASE_URL = 'http://hydrous-alb-1088098552.us-east-1.elb.amazonaws.com';

async function proxyRequest(request: NextRequest, params: { path: string[] }, method: string) {
  // Código del proxy con manejo de solicitudes, headers, body, etc.
  // Timeout establecido a 30000ms (30 segundos)
}
```

## Observaciones importantes

1. Las peticiones GET simples (como health check) funcionan mediante el proxy de prueba
2. Las peticiones de registro/login (POST) nunca llegan al backend (no hay logs)
3. El backend tiene configurado CORS para permitir conexiones desde el dominio del frontend
4. Los grupos de seguridad en AWS permiten tráfico HTTP desde cualquier origen (0.0.0.0/0)

## Hipótesis actuales

1. **Mixed content**: El navegador bloquea peticiones HTTP desde un sitio HTTPS
   - Parcialmente descartada porque el test simple funciona

2. **Problemas específicos con POST**: Podría haber alguna configuración o limitación en Vercel que afecta específicamente a las peticiones POST pero no a GET

3. **Limitaciones de Vercel**: Podría haber alguna restricción en Vercel para peticiones salientes a servicios HTTP

4. **Timeout en peticiones complejas**: Las peticiones simples funcionan, pero las más complejas (como registro) podrían estar excediendo algún límite no documentado

## Implementación de la solución

Después de analizar las diferentes opciones, decidimos implementar la solución 3: **Habilitar HTTPS directamente en el ALB a través de un subdominio con AWS Certificate Manager**.

### Pasos realizados

1. **Obtener un certificado SSL/TLS con AWS Certificate Manager**:
   - Solicitamos un certificado para `api.h2oassistant.com`
   - Validamos el dominio a través de registros CNAME en Vercel DNS
   - Añadimos registros CAA para permitir que Amazon emita certificados

2. **Configurar HTTPS en el Application Load Balancer**:
   - Añadimos un nuevo listener en el puerto 443 (HTTPS)
   - Asociamos el certificado SSL/TLS al listener
   - Mantuvimos el mismo grupo objetivo (target group) que el listener HTTP

3. **Configuración DNS**:
   - Creamos un registro CNAME en Vercel:
     - Nombre: `api`
     - Valor: `hydrous-alb-1088098552.us-east-1.elb.amazonaws.com`
   - Este registro permite acceder al ALB a través de `api.h2oassistant.com`

4. **Actualización del frontend**:
   - Modificamos el archivo `next.config.ts` para usar la URL HTTPS
   - Actualizamos el cliente API para usar la URL completa en lugar de rutas relativas

## Pruebas adicionales realizadas

1. **Acceso directo al backend HTTPS**:
   - Curl al endpoint de salud: `curl -v https://api.h2oassistant.com/api/health`
   - Resultado: Funcionó correctamente, devolvió `{"status":"ok","version":"1.0.0"}`

2. **Prueba de endpoints de autenticación**:
   - Curl al endpoint de login:
   ```bash
   curl -v -X POST https://api.h2oassistant.com/api/auth/login \
   -H "Content-Type: application/json" \
   -d '{"username":"email@ejemplo.com","password":"contraseña"}'  
   ```
   - Resultado: Error 422 ("Field required": "email"), indicando un problema con el formato de datos pero confirmando que la conexión funcionaba

3. **Prueba del API Route de Next.js**:
   ```bash
   curl -v -X POST https://www.h2oassistant.com/api/v1/auth/login \
   -H "Content-Type: application/json" \
   -d '{"email":"usuario@ejemplo.com","password":"clave123"}'  
   ```
   - Resultado: Error 502 con timeout: `{"message":"Error al conectar con el backend","error":"TimeoutError: The operation was aborted due to timeout"}`

## Hallazgos clave

1. **Problema de conectividad entre Vercel y AWS**: Descubrimos que Vercel no puede conectarse directamente al backend en AWS a través de HTTP. Esto se debe probablemente a restricciones de seguridad entre nubes o tiempos de respuesta extendidos.

2. **Discrepancia en el formato de datos**: El backend espera un campo `email` pero estábamos enviando `username` en algunas partes del código.

3. **HTTPS funciona correctamente**: La nueva configuración HTTPS con el subdominio permite acceso directo al backend sin problemas.

## Solución definitiva

La solución definitiva consiste en:

1. **Usar comunicación directa**: Hacer que el frontend se comunique directamente con el backend HTTPS sin pasar por las API Routes de Next.js como intermediario.

2. **Actualizar el cliente API**:
   ```typescript
   // src/lib/api-client.ts
   const apiBaseUrl = process.env.NEXT_PUBLIC_USE_LOCAL_BACKEND === 'true'
     ? 'http://localhost:8000/api'  // Para desarrollo local
     : 'https://api.h2oassistant.com/api';  // URL completa de la API en producción
   ```

3. **Corregir el formato de datos**: Asegurarse de que todas las solicitudes de autenticación usen los campos correctos (`email` en lugar de `username`).

4. **Eliminar el uso de las rutas API de Next.js**: Ya que no podemos solucionar el problema de conectividad entre Vercel y AWS, es mejor evitar ese intermediario.

## Lecciones aprendidas

1. **Diagnóstico completo**: Es crucial probar cada capa del sistema por separado para identificar dónde está ocurriendo el problema.

2. **Soluciones alternativas**: A veces, la mejor solución no es arreglar el problema directamente, sino encontrar una ruta alternativa.

3. **HTTPS es importante**: Garantizar comunicaciones seguras es fundamental para aplicaciones web modernas y evita problemas de "mixed content".

4. **Consistencia en API**: Mantener consistencia en los nombres de campos entre el frontend y el backend es crucial para evitar errores difíciles de depurar.
