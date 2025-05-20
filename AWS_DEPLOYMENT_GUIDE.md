# Guía de Despliegue en AWS para Backend Hydrous

## Índice
1. [Introducción](#introducción)
2. [Arquitectura Implementada](#arquitectura-implementada)
3. [Servicios AWS Utilizados](#servicios-aws-utilizados)
4. [Proceso de Despliegue Detallado](#proceso-de-despliegue-detallado)
5. [Acceso y Gestión de la Aplicación](#acceso-y-gestión-de-la-aplicación)
6. [Mantenimiento y Operaciones](#mantenimiento-y-operaciones)
7. [Solución de Problemas](#solución-de-problemas)
8. [Costos Estimados](#costos-estimados)
9. [Comandos de Referencia](#comandos-de-referencia)

## Introducción

Este documento detalla el proceso de despliegue del backend Hydrous en AWS. El backend está desarrollado con FastAPI (Python 3.11) y utiliza PostgreSQL con pgvector para almacenamiento de datos y Redis para caché y rate limiting. Todo el sistema está contenerizado con Docker.

## Arquitectura Implementada

La arquitectura implementada en AWS consta de los siguientes componentes:

![Arquitectura AWS](https://mermaid.ink/img/pako:eNqNkk9v2zAMxb-K4FMHtECOPgRDgaFbgR7WS9HDoEGRmViILRmSnGYI8t0nO03TrD30ZIl6j7-HRz5DZhVBDJnxzYPyFn9bVKZCZ3FjvLMkYzTGkVeQXUNhNMFvLbXoiWJwDg3JGNbGe9ugxhg8OWvQxuDQkVj0JGNYGlKOyHpnLQYK5Lx3tQ6BYvAOyVkMJGOoULUUKIZHb0vUMTxiKVG_ItdGVRjDHTlVUQw_0FUxLFGVqBVqGUPpXRHDHQXVYAzXaLfKqRiWqLYUwxd0JZb-Tz-Gy4GzLZXpyWMMK-9KNDGcVOgdxnBDW9TqRcZwRaR0DJvBWAxfyW1juJHxvVMbL2P4hs5WqP8yfEZXxXDvXUmqQC1juEVXYgzfh4OMYeNdhTqGR3QVxvDoXYnhCW2FMTyhLVHGcEWqxBg-oitRxvAJbYkyhk_elWiHpzPcoCsxhh_oCoxhh7bAGH6iKzCGX94VaGP4jbbAGH6hKzCGvXcF2hj23hVoYvjgXYE6hg_eFahj-IiuwBh-eFdgDL-9KzCG394VGMNf7wqM4Z93BcYAdgzZYfmBdgzZYfmBdgzZYfkBNobssHyAGUN2WD7AjiE7LB_gxpAdlg_wY8gOywcEMWSH5QOiGLLD8gFxDNlh-YA0huyweEAWQ3ZYPCCPITssHlDEkB0WDyhj-A9Z_vxZ?type=png)

### Componentes Principales:

1. **Base de Datos PostgreSQL (Amazon RDS)**
   - Instancia: db.t3.micro
   - Nombre: hydrous-db
   - Almacenamiento: 20GB
   - Usuario: hydrous
   - Contraseña: hydrous_password

2. **Caché Redis (Amazon ElastiCache)**
   - Instancia: cache.t3.micro
   - Nombre: hydrous-redis
   - Puerto: 6379

3. **Contenedor de Aplicación (Amazon ECS con Fargate)**
   - Clúster: hydrous-cluster
   - Servicio: hydrous-backend-service
   - Tarea: hydrous-backend-task
   - CPU: 256 unidades
   - Memoria: 512 MB

4. **Balanceador de Carga (Application Load Balancer)**
   - Nombre: hydrous-alb
   - URL: hydrous-alb-1088098552.us-east-1.elb.amazonaws.com
   - Puerto: 80 (HTTP)

5. **Repositorio de Contenedores (Amazon ECR)**
   - Nombre: hydrous-backend
   - URI: 882816896907.dkr.ecr.us-east-1.amazonaws.com/hydrous-backend

## Servicios AWS Utilizados

### Amazon RDS (Relational Database Service)
Servicio de base de datos relacional gestionado que facilita la configuración, operación y escalado de PostgreSQL en la nube. Proporciona capacidades rentables y redimensionables mientras automatiza tareas administrativas como el aprovisionamiento de hardware, configuración de bases de datos, aplicación de parches y copias de seguridad.

### Amazon ElastiCache
Servicio de caché en memoria compatible con Redis que proporciona rendimiento de milisegundos para aplicaciones. Mejora el rendimiento de las aplicaciones web al permitir recuperar información de cachés en memoria rápidas en lugar de depender de bases de datos basadas en disco más lentas.

### Amazon ECR (Elastic Container Registry)
Registro de contenedores Docker totalmente gestionado que facilita a los desarrolladores almacenar, gestionar e implementar imágenes de contenedores Docker. Se integra con Amazon ECS para simplificar el flujo de trabajo de desarrollo a producción.

### Amazon ECS (Elastic Container Service)
Servicio de orquestación de contenedores altamente escalable y de alto rendimiento que admite contenedores Docker. Permite ejecutar y escalar aplicaciones en contenedores fácilmente en AWS sin tener que gestionar la infraestructura subyacente.

### AWS Fargate
Tecnología que permite ejecutar contenedores sin tener que gestionar servidores o clústeres. Con Fargate, ya no es necesario aprovisionar, configurar o escalar clústeres de máquinas virtuales para ejecutar contenedores.

### Elastic Load Balancing (ALB)
Distribuye automáticamente el tráfico entrante de aplicaciones entre múltiples objetivos, como instancias EC2, contenedores y direcciones IP, en una o varias zonas de disponibilidad. Puede manejar la carga variable del tráfico de aplicaciones en una única zona de disponibilidad o en múltiples zonas de disponibilidad.

## Proceso de Despliegue Detallado

### 1. Preparación del Entorno AWS
- Verificación de la configuración de AWS CLI
- Autenticación con la cuenta AWS

### 2. Creación de la Base de Datos PostgreSQL
```bash
aws rds create-db-instance \
    --db-instance-identifier hydrous-db \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --master-username hydrous \
    --master-user-password "hydrous_password" \
    --allocated-storage 20 \
    --vpc-security-group-ids sg-0e9c31a4a958f802d \
    --availability-zone us-east-1a \
    --db-name hydrous_db \
    --port 5432 \
    --no-publicly-accessible \
    --backup-retention-period 7 \
    --tags Key=Project,Value=HydrousBackend
```

### 3. Creación del Clúster de Redis
```bash
aws elasticache create-cache-cluster \
    --cache-cluster-id hydrous-redis \
    --engine redis \
    --cache-node-type cache.t3.micro \
    --num-cache-nodes 1 \
    --port 6379 \
    --security-group-ids sg-0e9c31a4a958f802d \
    --tags Key=Project,Value=HydrousBackend
```

### 4. Creación del Repositorio de Contenedores
```bash
aws ecr create-repository \
    --repository-name hydrous-backend \
    --image-scanning-configuration scanOnPush=true \
    --tags Key=Project,Value=HydrousBackend
```

### 5. Autenticación en el Repositorio ECR
```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 882816896907.dkr.ecr.us-east-1.amazonaws.com
```

### 6. Construcción y Subida de la Imagen Docker
```bash
# Construcción de la imagen
docker build -t hydrous-backend:latest -f Dockerfile.prod .

# Etiquetado de la imagen
docker tag hydrous-backend:latest 882816896907.dkr.ecr.us-east-1.amazonaws.com/hydrous-backend:latest

# Subida de la imagen
docker push 882816896907.dkr.ecr.us-east-1.amazonaws.com/hydrous-backend:latest
```

### 7. Creación del Clúster ECS
```bash
aws ecs create-cluster \
    --cluster-name hydrous-cluster \
    --tags key=Project,value=HydrousBackend
```

### 8. Creación del Rol de Ejecución de Tareas
```bash
aws iam create-role --role-name ecsTaskExecutionRole --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ecs-tasks.amazonaws.com"},"Action":"sts:AssumeRole"}]}'

aws iam attach-role-policy --role-name ecsTaskExecutionRole --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
```

### 9. Creación del Grupo de Logs
```bash
aws logs create-log-group --log-group-name /ecs/hydrous-backend --tags Project=HydrousBackend
```

### 10. Registro de la Definición de Tarea
La definición de tarea especifica cómo se ejecutará tu contenedor en ECS:

```json
{
  "family": "hydrous-backend-task",
  "networkMode": "awsvpc",
  "executionRoleArn": "arn:aws:iam::882816896907:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::882816896907:role/ecsTaskExecutionRole",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "containerDefinitions": [
    {
      "name": "hydrous-backend",
      "image": "882816896907.dkr.ecr.us-east-1.amazonaws.com/hydrous-backend:latest",
      "essential": true,
      "portMappings": [
        {
          "containerPort": 8000,
          "hostPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "DEBUG", "value": "False"},
        {"name": "POSTGRES_USER", "value": "hydrous"},
        {"name": "POSTGRES_PASSWORD", "value": "hydrous_password"},
        {"name": "POSTGRES_SERVER", "value": "hydrous-db.xxxxxxxx.us-east-1.rds.amazonaws.com"},
        {"name": "POSTGRES_PORT", "value": "5432"},
        {"name": "POSTGRES_DB", "value": "hydrous_db"},
        {"name": "REDIS_URL", "value": "redis://:redis_password@hydrous-redis.xxxxxx.0001.use1.cache.amazonaws.com:6379/0"},
        {"name": "JWT_SECRET_KEY", "value": "temporalsecretkey123456789"},
        {"name": "MODEL", "value": "gpt-4o-mini"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/hydrous-backend",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/api/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
```

### 11. Creación de Grupos de Seguridad
```bash
# Grupo de seguridad para el balanceador de carga
aws ec2 create-security-group --group-name hydrous-alb-sg --description "Security group for Hydrous ALB" --vpc-id vpc-0400da935e367fc88

# Permitir tráfico HTTP
aws ec2 authorize-security-group-ingress --group-id sg-0656c9b30db94ff8d --protocol tcp --port 80 --cidr 0.0.0.0/0

# Permitir tráfico HTTPS
aws ec2 authorize-security-group-ingress --group-id sg-0656c9b30db94ff8d --protocol tcp --port 443 --cidr 0.0.0.0/0

# Grupo de seguridad para el servicio ECS
aws ec2 create-security-group --group-name hydrous-ecs-sg --description "Security group for Hydrous ECS service" --vpc-id vpc-0400da935e367fc88

# Permitir tráfico desde el balanceador de carga al servicio ECS
aws ec2 authorize-security-group-ingress --group-id sg-0f1371d35dec3c8e7 --protocol tcp --port 8000 --source-group sg-0656c9b30db94ff8d
```

### 12. Creación del Balanceador de Carga
```bash
aws elbv2 create-load-balancer \
    --name hydrous-alb \
    --subnets subnet-042d8410ae7404748 subnet-06c22eefcb8d896e8 \
    --security-groups sg-0656c9b30db94ff8d \
    --tags Key=Project,Value=HydrousBackend
```

### 13. Creación del Grupo Objetivo
```bash
aws elbv2 create-target-group \
    --name hydrous-tg \
    --protocol HTTP \
    --port 8000 \
    --vpc-id vpc-0400da935e367fc88 \
    --target-type ip \
    --health-check-path /api/health \
    --health-check-interval-seconds 30 \
    --health-check-timeout-seconds 5 \
    --healthy-threshold-count 2 \
    --unhealthy-threshold-count 2
```

### 14. Creación del Listener
```bash
aws elbv2 create-listener \
    --load-balancer-arn arn:aws:elasticloadbalancing:us-east-1:882816896907:loadbalancer/app/hydrous-alb/f3b89d4ca2680661 \
    --protocol HTTP \
    --port 80 \
    --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:us-east-1:882816896907:targetgroup/hydrous-tg/5157a5bc2b9a3ba1
```

### 15. Creación del Servicio ECS
```bash
aws ecs create-service \
    --cluster hydrous-cluster \
    --service-name hydrous-backend-service \
    --task-definition hydrous-backend-task:1 \
    --desired-count 1 \
    --launch-type FARGATE \
    --platform-version LATEST \
    --network-configuration "awsvpcConfiguration={subnets=[subnet-042d8410ae7404748,subnet-06c22eefcb8d896e8],securityGroups=[sg-0f1371d35dec3c8e7],assignPublicIp=ENABLED}" \
    --load-balancers "targetGroupArn=arn:aws:elasticloadbalancing:us-east-1:882816896907:targetgroup/hydrous-tg/5157a5bc2b9a3ba1,containerName=hydrous-backend,containerPort=8000"
```

## Acceso y Gestión de la Aplicación

### URL de Acceso
Tu aplicación está disponible en:
```
http://hydrous-alb-1088098552.us-east-1.elb.amazonaws.com
```

### Conexión con el Frontend
Para conectar tu frontend con este backend, actualiza la URL de la API en tu frontend para que apunte a:
```
http://hydrous-alb-1088098552.us-east-1.elb.amazonaws.com/api
```

### Actualización de la Aplicación
Para actualizar tu aplicación, sigue estos pasos:

1. Realiza cambios en tu código local
2. Construye una nueva imagen Docker para la arquitectura x86_64 (importante si estás usando Mac con Apple Silicon):
   ```bash
   docker buildx build --platform linux/amd64 -t hydrous-backend:latest -f Dockerfile.prod --load .
   ```
3. Etiqueta la nueva imagen:
   ```bash
   docker tag hydrous-backend:latest 882816896907.dkr.ecr.us-east-1.amazonaws.com/hydrous-backend:latest
   ```
4. Sube la nueva imagen a ECR:
   ```bash
   docker push 882816896907.dkr.ecr.us-east-1.amazonaws.com/hydrous-backend:latest
   ```
5. Actualiza el servicio ECS para usar la nueva imagen:
   ```bash
   aws ecs update-service --cluster hydrous-cluster --service hydrous-backend-service --force-new-deployment
   ```

> **IMPORTANTE**: Si estás usando una Mac con Apple Silicon (M1/M2/M3), es crucial construir la imagen Docker específicamente para la arquitectura x86_64 (amd64) que utiliza AWS Fargate. De lo contrario, obtendrás un error "exec format error" y tu aplicación no funcionará.

## Mantenimiento y Operaciones

### Monitoreo de la Aplicación
Puedes monitorear tu aplicación a través de Amazon CloudWatch. Para acceder a los logs:

1. Abre la consola de AWS
2. Ve a CloudWatch
3. Selecciona "Logs" en el menú lateral
4. Busca el grupo de logs "/ecs/hydrous-backend"

### Escalado de la Aplicación
Para escalar tu aplicación horizontalmente (más instancias):

```bash
aws ecs update-service --cluster hydrous-cluster --service hydrous-backend-service --desired-count 2
```

Para escalar verticalmente (más recursos por instancia), necesitas crear una nueva definición de tarea con más CPU y memoria:

```bash
# Primero, actualiza el archivo task-definition.json con los nuevos valores de CPU y memoria
# Luego, registra la nueva definición de tarea
aws ecs register-task-definition --cli-input-json file://task-definition.json

# Finalmente, actualiza el servicio para usar la nueva definición de tarea
aws ecs update-service --cluster hydrous-cluster --service hydrous-backend-service --task-definition hydrous-backend-task:2
```

### Copias de Seguridad
Amazon RDS realiza copias de seguridad automáticas de tu base de datos. Puedes configurar la frecuencia y el período de retención en la consola de AWS.

## Solución de Problemas

### Verificar el Estado del Servicio
```bash
aws ecs describe-services --cluster hydrous-cluster --services hydrous-backend-service
```

### Verificar las Tareas en Ejecución
```bash
aws ecs list-tasks --cluster hydrous-cluster --service-name hydrous-backend-service
```

### Verificar los Logs de una Tarea
```bash
# Primero, obtén el ID de la tarea
TASK_ID=$(aws ecs list-tasks --cluster hydrous-cluster --service-name hydrous-backend-service --query "taskArns[0]" --output text | awk -F/ '{print $NF}')

# Luego, obtén el flujo de logs
LOG_STREAM=$(aws ecs describe-tasks --cluster hydrous-cluster --tasks $TASK_ID --query "tasks[0].containers[0].logStreamPrefix" --output text)

# Finalmente, obtén los logs
aws logs get-log-events --log-group-name /ecs/hydrous-backend --log-stream-name $LOG_STREAM
```

### Verificar la Conectividad de la Base de Datos
Si sospechas que hay problemas de conectividad con la base de datos, puedes verificar el estado de la instancia RDS:

```bash
aws rds describe-db-instances --db-instance-identifier hydrous-db
```

### Verificar la Conectividad de Redis
Para verificar el estado del clúster de Redis:

```bash
aws elasticache describe-cache-clusters --cache-cluster-id hydrous-redis
```

## Costos Estimados

Con la configuración actual, puedes esperar un costo mensual aproximado de:

| Servicio | Tipo de Instancia | Costo Estimado (USD/mes) |
|----------|-------------------|--------------------------|
| RDS PostgreSQL | db.t3.micro | $15-25 |
| ElastiCache Redis | cache.t3.micro | $15-25 |
| ECS Fargate | 256 CPU, 512 MB | $15-30 |
| Application Load Balancer | - | $20 |
| Transferencia de datos y otros | - | Variable |
| **Total Estimado** | | **$65-100** |

## Comandos de Referencia

### Listar Servicios ECS
```bash
aws ecs list-services --cluster hydrous-cluster
```

### Describir una Tarea
```bash
aws ecs describe-task-definition --task-definition hydrous-backend-task:1
```

### Listar Instancias RDS
```bash
aws rds describe-db-instances
```

### Listar Clústeres de ElastiCache
```bash
aws elasticache describe-cache-clusters
```

### Listar Balanceadores de Carga
```bash
aws elbv2 describe-load-balancers
```

### Obtener la URL del Balanceador de Carga
```bash
aws elbv2 describe-load-balancers --names hydrous-alb --query 'LoadBalancers[0].DNSName' --output text
```
