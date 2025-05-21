# Guía de Administración de AWS para H₂O Allegiant

Esta documentación te ayudará a entender cómo está configurado tu backend en AWS, cómo monitorearlo y cómo realizar modificaciones cuando sea necesario.

## Índice

1. [Arquitectura General](#arquitectura-general)
2. [Acceso a la Consola de AWS](#acceso-a-la-consola-de-aws)
3. [Monitoreo de la Aplicación](#monitoreo-de-la-aplicación)
4. [Actualización del Backend](#actualización-del-backend)
5. [Gestión de Recursos](#gestión-de-recursos)
6. [Solución de Problemas Comunes](#solución-de-problemas-comunes)
7. [Optimización de Costos](#optimización-de-costos)

## Arquitectura General

Tu backend de H₂O Allegiant está desplegado en AWS con la siguiente arquitectura:

![Arquitectura AWS](https://i.imgur.com/example.png)

### Componentes Principales

1. **Amazon ECS (Elastic Container Service) con Fargate**
   - **Propósito**: Ejecuta tu aplicación FastAPI en contenedores Docker sin servidor
   - **Configuración**: Definida en `task-definition.json`
   - **Cluster**: `hydrous`
   - **Servicio**: `hydrous-production`

2. **Amazon RDS (Relational Database Service)**
   - **Propósito**: Base de datos PostgreSQL con pgvector para embeddings
   - **Instancia**: `db.t3.micro`
   - **Endpoint**: `hydrous-db.cuj8q6augwwx.us-east-1.rds.amazonaws.com`

3. **Amazon ElastiCache**
   - **Propósito**: Servicio Redis para caché y rate limiting
   - **Instancia**: `cache.t3.micro`
   - **Endpoint**: `hydrous-redis.1ywfpj.0001.use1.cache.amazonaws.com`

4. **Amazon ECR (Elastic Container Registry)**
   - **Propósito**: Almacena las imágenes Docker de tu aplicación
   - **Repositorio**: `hydrous`

5. **Application Load Balancer (ALB)**
   - **Propósito**: Expone tu API al mundo exterior
   - **Endpoint**: `http://hydrous-alb-1088098552.us-east-1.elb.amazonaws.com`

6. **Amazon CloudWatch**
   - **Propósito**: Monitoreo, logs y alertas
   - **Grupo de logs**: `/ecs/hydrous-backend`

## Acceso a la Consola de AWS

### Iniciar Sesión

1. Ve a [https://aws.amazon.com/console/](https://aws.amazon.com/console/)
2. Ingresa tus credenciales de AWS
3. Asegúrate de estar en la región `us-east-1` (Norte de Virginia)

### Configuración de AWS CLI

Para administrar AWS desde la línea de comandos:

```bash
# Instalar AWS CLI
brew install awscli  # macOS con Homebrew
# o
pip install awscli   # Con pip

# Configurar credenciales
aws configure
# Ingresa tu AWS Access Key ID
# Ingresa tu AWS Secret Access Key
# Región: us-east-1
# Formato de salida: json
```

## Monitoreo de la Aplicación

### CloudWatch Logs

Para ver los logs de tu aplicación:

1. Ve a la [consola de CloudWatch](https://console.aws.amazon.com/cloudwatch/)
2. En el menú lateral, selecciona "Logs" → "Log groups"
3. Busca el grupo `/ecs/hydrous-backend`
4. Haz clic en el grupo y luego en el stream de logs más reciente

También puedes ver los logs desde la línea de comandos:

```bash
# Ver los grupos de logs
aws logs describe-log-groups

# Ver los streams de logs en un grupo específico
aws logs describe-log-streams --log-group-name /ecs/hydrous-backend

# Ver los eventos de log de un stream específico
aws logs get-log-events --log-group-name /ecs/hydrous-backend --log-stream-name ecs/hydrous-container/abcdef12345
```

### Monitoreo de ECS

Para verificar el estado de tus contenedores:

1. Ve a la [consola de ECS](https://console.aws.amazon.com/ecs/)
2. Selecciona el cluster "hydrous"
3. Haz clic en la pestaña "Services" y selecciona tu servicio
4. Revisa la pestaña "Tasks" para ver las tareas en ejecución
5. Haz clic en una tarea para ver detalles como CPU, memoria y logs

### Monitoreo de RDS

Para monitorear tu base de datos:

1. Ve a la [consola de RDS](https://console.aws.amazon.com/rds/)
2. Selecciona tu instancia de base de datos
3. En la pestaña "Monitoring", puedes ver métricas como:
   - CPU Utilization
   - Database Connections
   - Free Storage Space
   - Read/Write IOPS

### Monitoreo de ElastiCache

Para monitorear Redis:

1. Ve a la [consola de ElastiCache](https://console.aws.amazon.com/elasticache/)
2. Selecciona tu cluster de Redis
3. En la pestaña "Metrics", puedes ver:
   - CPU Utilization
   - Memory Usage
   - Network Bytes In/Out
   - Cache Hits/Misses

### Configuración de Alertas

Para crear alertas que te notifiquen sobre problemas:

1. Ve a CloudWatch → "Alarms" → "Create alarm"
2. Selecciona la métrica que quieres monitorear (ej. CPU de ECS)
3. Define el umbral (ej. CPU > 80% durante 5 minutos)
4. Configura una acción de notificación (email o SNS)

## Actualización del Backend

### Proceso Manual de Actualización

1. **Actualiza tu código localmente**
   ```bash
   git pull origin main  # o develop para entorno de desarrollo
   ```

2. **Construye la imagen Docker**
   ```bash
   docker build -t hydrous-backend:latest -f Dockerfile.prod .
   ```

3. **Etiqueta la imagen para ECR**
   ```bash
   # Obtén el login para ECR
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin [tu-cuenta-aws].dkr.ecr.us-east-1.amazonaws.com
   
   # Etiqueta la imagen
   docker tag hydrous-backend:latest [tu-cuenta-aws].dkr.ecr.us-east-1.amazonaws.com/hydrous:latest
   ```

4. **Sube la imagen a ECR**
   ```bash
   docker push [tu-cuenta-aws].dkr.ecr.us-east-1.amazonaws.com/hydrous:latest
   ```

5. **Actualiza el servicio ECS**
   ```bash
   aws ecs update-service --cluster hydrous --service hydrous-production --force-new-deployment
   ```

6. **Verifica el despliegue**
   - Ve a la consola de ECS
   - Selecciona tu cluster y servicio
   - Monitorea el estado del despliegue en la pestaña "Deployments"

### Actualización de Variables de Entorno

Para modificar variables de entorno:

1. Edita el archivo `task-definition.json` localmente
2. Registra una nueva revisión de la definición de tarea:
   ```bash
   aws ecs register-task-definition --cli-input-json file://task-definition.json
   ```
3. Actualiza el servicio para usar la nueva definición:
   ```bash
   aws ecs update-service --cluster hydrous --service hydrous-production --task-definition hydrous:NUEVA_REVISION
   ```

### Rollback a una Versión Anterior

Si necesitas revertir a una versión anterior:

1. Identifica la imagen anterior en ECR:
   ```bash
   aws ecr describe-images --repository-name hydrous
   ```

2. Actualiza el servicio para usar esa imagen:
   ```bash
   # Si tienes una definición de tarea anterior
   aws ecs update-service --cluster hydrous --service hydrous-production --task-definition hydrous:REVISION_ANTERIOR
   
   # O si necesitas usar la misma definición pero con una imagen anterior
   # Primero, actualiza la definición de tarea para usar la imagen anterior
   # Luego, registra y despliega como se mostró anteriormente
   ```

## Gestión de Recursos

### Escalado de la Aplicación

Para ajustar la capacidad de tu aplicación:

1. **Escalado horizontal** (más instancias):
   ```bash
   aws ecs update-service --cluster hydrous --service hydrous-production --desired-count 2
   ```

2. **Escalado vertical** (más recursos por instancia):
   - Edita `task-definition.json` para aumentar CPU/memoria
   - Registra una nueva revisión y actualiza el servicio

3. **Configuración de Auto Scaling**:
   - Ve a la consola de ECS → Tu servicio → "Update"
   - En "Service Auto Scaling", configura:
     - Minimum number of tasks
     - Desired number of tasks
     - Maximum number of tasks
     - Scaling policies (basadas en CPU, memoria, etc.)

### Gestión de la Base de Datos

Para administrar tu base de datos PostgreSQL:

1. **Conexión a la base de datos**:
   ```bash
   # Usando psql
   psql -h hydrous-db.xxxxxxxx.us-east-1.rds.amazonaws.com -U hydrous -d hydrous_db
   
   # O usando una herramienta como DBeaver, pgAdmin, etc.
   ```

2. **Backup manual**:
   - Ve a la consola de RDS → Tu instancia → "Actions" → "Take snapshot"

3. **Restauración desde backup**:
   - Ve a la consola de RDS → "Snapshots"
   - Selecciona el snapshot → "Actions" → "Restore snapshot"

4. **Escalado de la base de datos**:
   - Ve a la consola de RDS → Tu instancia → "Modify"
   - Cambia el tipo de instancia (ej. de db.t3.micro a db.t3.small)
   - Nota: Esto puede causar una interrupción temporal

### Gestión de Redis

Para administrar ElastiCache:

1. **Conexión a Redis**:
   ```bash
   redis-cli -h hydrous-redis.xxxxxx.0001.use1.cache.amazonaws.com -p 6379 -a redis_password
   ```

2. **Escalado de Redis**:
   - Ve a la consola de ElastiCache → Tu cluster → "Modify"
   - Cambia el tipo de nodo (ej. de cache.t3.micro a cache.t3.small)

## Solución de Problemas Comunes

### Problema de Incompatibilidad de Arquitectura en Docker

Si ves errores como `exec /usr/local/bin/uvicorn: exec format error` en los logs, significa que hay una incompatibilidad de arquitectura entre la imagen Docker y el sistema donde se está ejecutando:

1. **Causa**: La imagen Docker se construyó para una arquitectura (como ARM64 en Mac con chip M1/M2) pero AWS Fargate espera una imagen compatible con AMD64.

2. **Solución**: Reconstruir la imagen Docker especificando la plataforma AMD64:

   ```bash
   # Construir la imagen especificando la plataforma
   docker build --platform linux/amd64 -t hydrous-backend:latest -f Dockerfile.prod .
   
   # Autenticarse en ECR
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin [tu-cuenta-aws].dkr.ecr.us-east-1.amazonaws.com
   
   # Etiquetar y subir la imagen
   docker tag hydrous-backend:latest [tu-cuenta-aws].dkr.ecr.us-east-1.amazonaws.com/hydrous-backend:latest
   docker push [tu-cuenta-aws].dkr.ecr.us-east-1.amazonaws.com/hydrous-backend:latest
   
   # Actualizar el servicio ECS
   aws ecs update-service --cluster hydrous-cluster --service hydrous-backend-service --force-new-deployment
   ```

3. **Verificación**: Monitorea los logs en CloudWatch para asegurarte de que el contenedor inicie correctamente.

### Errores de Validación en la API

Si recibes errores 422 Unprocessable Entity al intentar registrar usuarios u otras operaciones:

1. **Verifica los campos requeridos**: La API puede esperar campos específicos que no estás enviando. Por ejemplo, para registrar un usuario, asegúrate de enviar `first_name` y `last_name` en lugar de solo `name`.

2. **Ejemplo de solicitud correcta para registro**:
   ```json
   {
     "email": "usuario@ejemplo.com",
     "password": "Contraseña123!",
     "first_name": "Nombre",
     "last_name": "Apellido"
   }
   ```

3. **Verificación con curl**:
   ```bash
   curl -X POST -H "Content-Type: application/json" \
   -d '{"email":"usuario@ejemplo.com","password":"Contraseña123!","first_name":"Nombre","last_name":"Apellido"}' \
   http://hydrous-alb-1088098552.us-east-1.elb.amazonaws.com/api/auth/register
   ```

### Contenedor No Inicia

Si el contenedor no inicia correctamente:

1. Verifica los logs en CloudWatch
2. Comprueba el health check en la definición de tarea
3. Verifica que las variables de entorno sean correctas
4. Asegúrate de que los puertos estén configurados correctamente

### Problemas de Conexión a la Base de Datos

Si hay problemas de conexión a RDS:

1. Verifica que el grupo de seguridad permita conexiones desde ECS
2. Comprueba las credenciales en las variables de entorno
3. Verifica que la base de datos esté en estado "Available"
4. Prueba la conexión manualmente desde otra máquina

### Problemas de Memoria o CPU

Si hay problemas de recursos:

1. Revisa las métricas de CloudWatch para identificar picos
2. Considera aumentar la asignación de CPU/memoria en la definición de tarea
3. Verifica si hay fugas de memoria en tu aplicación

### Problemas con el Load Balancer

Si el ALB no funciona correctamente:

1. Verifica los health checks del target group
2. Comprueba que los grupos de seguridad permitan el tráfico
3. Revisa los logs de acceso del ALB

### Problemas de Conexión entre Frontend y Backend

Si el frontend no puede conectarse al backend (peticiones que se quedan cargando o errores de conexión):

1. **Verifica la configuración CORS en el backend**:
   - Asegúrate de que el dominio del frontend esté incluido en la lista `CORS_ORIGINS` en `app/config.py`
   - Verifica que el patrón regex en `allow_origin_regex` en `app/main.py` incluya el dominio del frontend

2. **Revisa la configuración del frontend**:
   - Verifica que las variables de entorno en `.env.production` apunten al endpoint correcto del backend:
     ```
     NEXT_PUBLIC_BACKEND_URL=http://hydrous-alb-1088098552.us-east-1.elb.amazonaws.com/api
     BACKEND_URL=http://hydrous-alb-1088098552.us-east-1.elb.amazonaws.com/api
     ```
   - Asegúrate de que la configuración de proxy en `next.config.ts` esté correctamente configurada:
     ```javascript
     async rewrites() {
       return [
         {
           source: '/api/:path*',
           destination: process.env.NEXT_PUBLIC_USE_LOCAL_BACKEND === 'true'
             ? 'http://localhost:8000/api/:path*'  // Para desarrollo local
             : 'http://hydrous-alb-1088098552.us-east-1.elb.amazonaws.com/api/:path*', // Conexión directa al backend en AWS
         },
       ];
     },
     ```

3. **Monitorea los logs en tiempo real**:
   - Verifica si las peticiones llegan al backend usando CloudWatch Logs:
     ```bash
     aws logs tail /ecs/hydrous-backend --follow
     ```
   - Si no ves ninguna petición en los logs, es probable que el problema esté en la configuración del frontend o en la red

4. **Prueba la conexión directamente**:
   - Usa `curl` para verificar que el backend responde correctamente:
     ```bash
     curl http://hydrous-alb-1088098552.us-east-1.elb.amazonaws.com/api/health
     ```
   - Si el backend responde pero el frontend no puede conectarse, es probable que sea un problema de CORS

5. **Soluciones comunes**:
   - Reconstruye y redespliega el backend con la configuración CORS actualizada
   - Actualiza y redespliega el frontend con la configuración de conexión correcta
   - Verifica que no haya reglas de firewall o restricciones de red que bloqueen las conexiones

## Optimización de Costos

Tu infraestructura está optimizada para un costo aproximado de $65-100/mes. Para mantener los costos bajo control:

1. **Monitoreo de costos**:
   - Usa AWS Cost Explorer para ver el desglose de gastos
   - Configura presupuestos y alertas en AWS Budgets

2. **Optimizaciones posibles**:
   - Usa instancias reservadas para RDS y ElastiCache si planeas usarlos por más de un año
   - Configura Auto Scaling para reducir la capacidad en períodos de baja demanda
   - Considera usar Savings Plans para ECS Fargate

3. **Recursos para optimizar primero**:
   - RDS: Considera usar una instancia más pequeña o multi-AZ solo si es necesario
   - ElastiCache: Ajusta el tamaño según el uso real
   - ECS: Ajusta CPU/memoria según el uso real

---

## Recursos Adicionales

- [Documentación oficial de AWS ECS](https://docs.aws.amazon.com/ecs/)
- [Documentación oficial de AWS RDS](https://docs.aws.amazon.com/rds/)
- [Documentación oficial de AWS ElastiCache](https://docs.aws.amazon.com/elasticache/)
- [Guía de optimización de costos de AWS](https://aws.amazon.com/pricing/cost-optimization/)

## Contactos de Soporte

- **DevOps**: [Tu nombre y contacto]
- **AWS Support**: [Si tienes un plan de soporte]
