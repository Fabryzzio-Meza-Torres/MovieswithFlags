# Movies with Flags 🎬🎌

Una aplicación web que muestra películas junto con las banderas de sus países de origen. Utiliza la API de OMDB para obtener información de películas y una base de datos SQLite para caché.

## Requisitos Previos 📋

- Python 3.8 o superior
- pip (gestor de paquetes de Python)

## Instalación 🔧

1. Clonar el repositorio
```bash
git clone <url-del-repositorio>
cd <nombre-del-directorio>

# Dependencias

pip install -r requirements.txt

# or

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

## Ejecución 🚀
```bash
python app.py
```

## Prueba de Stress 🤯
```bash
python run_stress_test.py light
python run_stress_test.py medium
python run_stress_test.py heavy
```

## Características 🌟

- Búsqueda de películas por título
- Cache de películas y banderas en SQLite
- Visualización de banderas por país de origen
- Paginación de resultados
- Pruebas de stress
- Interfaz responsiva y moderna
- Indicador de carga durante búsquedas

