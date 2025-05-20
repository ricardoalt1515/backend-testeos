# Flujo de Trabajo DevOps para H₂O Allegiant

Este documento describe el flujo de trabajo completo para el desarrollo, pruebas y despliegue del proyecto H₂O Allegiant, incluyendo tanto el frontend (Next.js en Vercel) como el backend (FastAPI en AWS).

## Índice

1. [Arquitectura General](#arquitectura-general)
2. [Entornos](#entornos)
3. [Estructura de Ramas Git](#estructura-de-ramas-git)
4. [Flujo de Desarrollo](#flujo-de-desarrollo)
5. [Integración Continua y Despliegue Continuo (CI/CD)](#integración-continua-y-despliegue-continuo-cicd)
6. [Gestión de Configuración](#gestión-de-configuración)
7. [Monitoreo y Observabilidad](#monitoreo-y-observabilidad)
8. [Procedimientos de Emergencia](#procedimientos-de-emergencia)

## Arquitectura General

El proyecto H₂O Allegiant consta de dos componentes principales:

### Frontend
- **Tecnología**: Next.js (React)
- **Hosting**: Vercel
- **Dominio**: [tudominio.com](https://tudominio.com)
- **Repositorio**: `hydrous-chat`

### Backend
- **Tecnología**: FastAPI (Python)
- **Hosting**: AWS (ECS Fargate)
- **Base de datos**: PostgreSQL en RDS
- **Caché**: Redis en ElastiCache
- **Endpoint API**: [http://hydrous-alb-1088098552.us-east-1.elb.amazonaws.com](http://hydrous-alb-1088098552.us-east-1.elb.amazonaws.com)
- **Repositorio**: `backend-testeos`

## Entornos

### 1. Desarrollo Local

Configuración para desarrollo en la máquina local del desarrollador.

#### Frontend
```bash
# Archivo .env.local para desarrollo local
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000/api
NEXT_PUBLIC_USE_LOCAL_BACKEND=true
```

#### Backend
```bash
# Archivo .env para desarrollo local
DATABASE_URL=postgresql://postgres:password@localhost:5432/hydrous
REDIS_URL=redis://localhost:6379/0
OPENAI_API_KEY=your_api_key_here
```

### 2. Desarrollo (Dev)

Entorno para integración continua y pruebas de nuevas características.

#### Frontend
- **URL**: dev.tudominio.com
- **Variables de entorno**:
  ```
  NEXT_PUBLIC_BACKEND_URL=https://api-dev.tudominio.com/api
  NEXT_PUBLIC_USE_LOCAL_BACKEND=false
  ```

#### Backend
- **URL**: api-dev.tudominio.com
- **Infraestructura**: Versión reducida de la infraestructura de producción
  - RDS: db.t3.micro
  - ElastiCache: cache.t3.micro
  - ECS: Fargate con 0.5 vCPU, 1GB RAM

### 3. Producción (Prod)

Entorno para usuarios finales.

#### Frontend
- **URL**: tudominio.com
- **Variables de entorno**:
  ```
  NEXT_PUBLIC_BACKEND_URL=https://api.tudominio.com/api
  NEXT_PUBLIC_USE_LOCAL_BACKEND=false
  ```

#### Backend
- **URL**: api.tudominio.com (actualmente http://hydrous-alb-1088098552.us-east-1.elb.amazonaws.com)
- **Infraestructura**: 
  - RDS: db.t3.micro
  - ElastiCache: cache.t3.micro
  - ECS: Fargate con configuración optimizada

## Estructura de Ramas Git

Utilizaremos una versión simplificada de GitFlow:

### Ramas Principales
- **main**: Código en producción, siempre estable
- **develop**: Rama de integración para desarrollo

### Ramas Temporales
- **feature/nombre-caracteristica**: Para nuevas características
- **bugfix/nombre-error**: Para correcciones de errores
- **hotfix/nombre-error**: Para correcciones urgentes en producción

## Flujo de Desarrollo

### 1. Inicio de Nueva Característica

```bash
# Asegurarse de tener la última versión de develop
git checkout develop
git pull origin develop

# Crear una nueva rama de característica
git checkout -b feature/nombre-caracteristica

# Desarrollo y commits frecuentes
git add .
git commit -m "Descripción clara del cambio"
```

### 2. Pruebas Locales

```bash
# Frontend
cd hydrous-chat
npm run dev

# Backend
cd backend-testeos
uvicorn app.main:app --reload
```

### 3. Integración

```bash
# Push de la rama de característica
git push origin feature/nombre-caracteristica

# Crear Pull Request en GitHub
# develop ← feature/nombre-caracteristica
```

### 4. Revisión y Merge

- Revisión de código por otro desarrollador
- CI ejecuta pruebas automáticas
- Aprobación y merge a develop

### 5. Despliegue a Desarrollo

- CI/CD despliega automáticamente desde develop al entorno de desarrollo

### 6. Despliegue a Producción

```bash
# Una vez que develop está listo para producción
git checkout main
git merge develop
git push origin main

# Etiquetar versión
git tag -a v1.x.x -m "Descripción de la versión"
git push origin v1.x.x
```

## Integración Continua y Despliegue Continuo (CI/CD)

### GitHub Actions

#### Frontend (Vercel)

```yaml
# .github/workflows/frontend.yml
name: Frontend CI/CD

on:
  push:
    branches: [develop, main]
    paths:
      - 'hydrous-chat/**'
  pull_request:
    branches: [develop]
    paths:
      - 'hydrous-chat/**'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      - name: Install dependencies
        run: cd hydrous-chat && npm ci
      - name: Run tests
        run: cd hydrous-chat && npm test
      - name: Run linting
        run: cd hydrous-chat && npm run lint

  # Vercel maneja el despliegue automáticamente
```

#### Backend (AWS)

```yaml
# .github/workflows/backend.yml
name: Backend CI/CD

on:
  push:
    branches: [develop, main]
    paths:
      - 'backend-testeos/**'
  pull_request:
    branches: [develop]
    paths:
      - 'backend-testeos/**'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd backend-testeos
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest
      - name: Run tests
        run: |
          cd backend-testeos
          pytest

  build-and-push:
    needs: test
    if: github.event_name == 'push'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v1
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
          
      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v1
      
      - name: Build, tag, and push image to Amazon ECR
        env:
          ECR_REPOSITORY: hydrous
          IMAGE_TAG: ${{ github.ref == 'refs/heads/main' && 'production' || 'development' }}
        run: |
          cd backend-testeos
          docker build -t ${{ steps.login-ecr.outputs.registry }}/$ECR_REPOSITORY:$IMAGE_TAG .
          docker push ${{ steps.login-ecr.outputs.registry }}/$ECR_REPOSITORY:$IMAGE_TAG
          
      - name: Update ECS service
        env:
          ECS_CLUSTER: hydrous
          ECS_SERVICE: ${{ github.ref == 'refs/heads/main' && 'hydrous-production' || 'hydrous-development' }}
        run: |
          aws ecs update-service --cluster $ECS_CLUSTER --service $ECS_SERVICE --force-new-deployment
```

## Gestión de Configuración

### Variables de Entorno

#### Frontend (Vercel)
- Configuradas en el panel de Vercel para cada entorno (Production, Preview, Development)

#### Backend (AWS)
- Configuradas como variables de entorno en la definición de tareas de ECS
- Secretos sensibles almacenados en AWS Secrets Manager

### Archivos de Configuración

#### Frontend
```
hydrous-chat/
  ├── .env.example       # Variables requeridas (plantilla)
  ├── .env.local         # Desarrollo local (no en git)
  ├── .env.development   # Valores para desarrollo (si es necesario)
  └── .env.production    # Valores para producción (si es necesario)
```

#### Backend
```
backend-testeos/
  ├── .env.example       # Variables requeridas (plantilla)
  └── .env               # Desarrollo local (no en git)
```

## Monitoreo y Observabilidad

### Logs

- **Frontend**: Vercel Logs
- **Backend**: AWS CloudWatch Logs

### Métricas

- **AWS CloudWatch**: Métricas de RDS, ElastiCache, ECS
- **Implementación futura**: Prometheus + Grafana para métricas detalladas

### Alertas

- **Implementación futura**: CloudWatch Alarms con notificaciones a Slack

## Procedimientos de Emergencia

### Rollback de Frontend

1. En Vercel, ir a la sección "Deployments"
2. Encontrar el último despliegue estable
3. Hacer clic en "..." y seleccionar "Promote to Production"

### Rollback de Backend

```bash
# Revertir a una versión anterior de la imagen de Docker
aws ecs update-service --cluster hydrous --service hydrous-production --task-definition hydrous:previous-version --force-new-deployment
```

### Contactos de Emergencia

- **DevOps**: [Tu nombre] - [Tu contacto]
- **Backend**: [Contacto del responsable de backend]
- **Frontend**: [Contacto del responsable de frontend]
