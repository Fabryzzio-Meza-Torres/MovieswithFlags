# Movies with Flags 🎬🎌

Una aplicación web que muestra películas junto con las banderas de sus países de origen. Utiliza la API de OMDB para obtener información de películas y una base de datos SQLite para caché.

## Requisitos Previos 📋

- Python 3.8 o superior
- pip (gestor de paquetes de Python)

## Instalación 🔧

1. Clonar el repositorio
```bash
git clone https://github.com/Fabryzzio-Meza-Torres/MovieswithFlags.git
cd MovieswithFlags

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
Ahora puedes abrir en el navegador: http://127.0.0.1:5000/

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

## Integrantes

- Fabryzzio Jossue Meza Torres
- Aaron Cesar Aldair Navarro Mendoza

