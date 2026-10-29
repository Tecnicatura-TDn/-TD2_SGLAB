# Mi proyecto MVC (Node.js + Express + Docker)

## Levantar con Docker
    docker compose up --build

Abrir http://localhost:3000

## Sin Docker
    npm install
    npm start

## Estructura
- app/models: datos y lógica de negocio
- app/views: plantillas EJS
- app/controllers: reciben peticiones y coordinan modelo/vista
- routes: definición de rutas
- config: configuración (base de datos)
- public: archivos estáticos
