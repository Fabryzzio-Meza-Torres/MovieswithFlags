from flask import Flask, render_template, request, jsonify, g
import requests
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
import sqlite3
import threading

app = Flask(__name__)
apikey = "c8e2504d"

# Thread-local storage para conexiones DB
db_local = threading.local()

def get_db():
    """Obtener conexión a BD thread-safe"""
    if not hasattr(db_local, 'conn'):
        db_local.conn = sqlite3.connect('cache.db')
    return db_local.conn

def close_db():
    """Cerrar conexión a BD si existe"""
    if hasattr(db_local, 'conn'):
        db_local.conn.close()
        del db_local.conn

@app.teardown_appcontext
def teardown_db(exception=None):
    close_db()

def init_db():
    conn = sqlite3.connect('cache.db')
    cursor = conn.cursor()

    # Crear tablas con mejor manejo de errores
    try:
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS Movie(
                imdbID TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                year TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS Country (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                flag_url TEXT
            );

            CREATE TABLE IF NOT EXISTS MovieCountry(
                movie_id TEXT,
                country_name TEXT,
                PRIMARY KEY (movie_id, country_name),
                FOREIGN KEY (movie_id) REFERENCES Movie(imdbID),
                FOREIGN KEY (country_name) REFERENCES Country(name)
            );

            CREATE INDEX IF NOT EXISTS idx_movie_country 
            ON MovieCountry(movie_id, country_name);
        """)
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database initialization error: {e}")
        conn.rollback()
    finally:
        conn.close()

def GetMovieDetailsCache(imdbID):
    if not imdbID:
        return None

    conn = get_db()
    cursor = conn.cursor()

    try:
        # Primero intentamos obtener de caché
        cursor.execute("""
            SELECT m.title, m.year, GROUP_CONCAT(mc.country_name) as countries
            FROM Movie m
            LEFT JOIN MovieCountry mc ON m.imdbID = mc.movie_id 
            WHERE m.imdbID=?
            GROUP BY m.imdbID
        """, (imdbID,))
        movie = cursor.fetchone()

        if movie:
            return {"Title": movie[0], "Year": movie[1], "Country": movie[2] or ""}

        # Si no está en caché, obtenemos de la API
        movie_details = getmoviedetails(imdbID)
        if not movie_details:
            return None

        # Insertar película con manejo de errores mejorado
        cursor.execute("""
            INSERT OR REPLACE INTO Movie (imdbID, title, year) 
            VALUES (?, ?, ?)
        """, (imdbID, movie_details["Title"], movie_details["Year"]))

        # Procesar países
        if movie_details.get("Country"):
            countries_names = [c.strip() for c in movie_details["Country"].split(",")]
            for country_name in countries_names:
                if not country_name:
                    continue

                # Insertar país si no existe
                cursor.execute("""
                    INSERT OR IGNORE INTO Country (name, flag_url) 
                    VALUES (?, ?)
                """, (country_name, get_country_flag(country_name)))

                # Vincular película con país
                cursor.execute("""
                    INSERT OR IGNORE INTO MovieCountry (movie_id, country_name) 
                    VALUES (?, ?)
                """, (imdbID, country_name))

        conn.commit()
        return movie_details

    except sqlite3.Error as e:
        print(f"Database error in GetMovieDetailsCache: {e}")
        conn.rollback()
        return None
    except Exception as e:
        print(f"Unexpected error in GetMovieDetailsCache: {e}")
        conn.rollback()
        return None

def getCountryFlagCached(country_name):
    if not country_name:
        return None

    conn = get_db()
    cursor = conn.cursor()

    try:
        # Buscar en caché
        cursor.execute("SELECT flag_url FROM Country WHERE name=?", (country_name,))
        result = cursor.fetchone()
        
        if result and result[0]:
            return {'name': country_name, 'flag_url': result[0]}

        # Si no está en caché, obtener de API
        flag_url = get_country_flag(country_name)
        if flag_url:
            cursor.execute("""
                INSERT OR REPLACE INTO Country (name, flag_url) 
                VALUES (?, ?)
            """, (country_name, flag_url))
            conn.commit()
            return {'name': country_name, 'flag_url': flag_url}
        
        return None

    except sqlite3.Error as e:
        print(f"Database error in getCountryFlagCached: {e}")
        conn.rollback()
        return None
    except Exception as e:
        print(f"Unexpected error in getCountryFlagCached: {e}")
        return None

def merge_data_with_flags(filter_text, page=1):
    try:
        filmssearch_json = searchfilms(filter_text, page)
        if not filmssearch_json or "Search" not in filmssearch_json:
            return {"movies": [], "total": 0, "current_page": page}

        total_results = int(filmssearch_json.get("totalResults", 0))
        moviesdetailswithflags = []

        # Limitar el número de workers para evitar sobrecarga
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_movies = [
                executor.submit(GetMovieDetailsCache, movie["imdbID"]) 
                for movie in filmssearch_json["Search"]
            ]
            
            for future in future_movies:
                try:
                    moviedetails = future.result()
                    if not moviedetails:
                        continue

                    countries = []
                    if moviedetails.get("Country"):
                        country_names = [c.strip() for c in moviedetails["Country"].split(",")]
                        countries = [{"name": c, "flag": getCountryFlagCached(c)} for c in country_names if c]

                    movie_with_flags = {
                        "title": moviedetails["Title"],
                        "year": moviedetails["Year"],
                        "countries": [{"name": c, "flag": f} for c, f in zip(country_names, countries) if f]
                    }
                    moviesdetailswithflags.append(movie_with_flags)
                except Exception as e:
                    print(f"Error processing movie: {e}")
                    continue

        return {
            "movies": moviesdetailswithflags,
            "total": total_results,
            "current_page": page
        }

    except Exception as e:
        print(f"Error in merge_data_with_flags: {e}")
        return {"movies": [], "total": 0, "current_page": page}


# Empleamos un cache para guardar las respuestas de la API de paises y asi mejorar la velocidad y reducir su consumo
@lru_cache(maxsize=128)
def searchfilms(search_text, page=1):
    url = f"https://www.omdbapi.com/?s={search_text}&apikey={apikey}&page={page}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print("Failed to retrieve search results.")
        return None

@lru_cache(maxsize=128)
def getmoviedetails(imdbID):
    url = f"https://www.omdbapi.com/?i={imdbID}&apikey={apikey}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print("Failed to retrieve movie details.")
        return None

@lru_cache(maxsize=128)
def get_country_flag(fullname):
    url = f"https://restcountries.com/v3.1/name/{fullname}?fullText=true"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            country_data = response.json()
            if country_data:
                return country_data[0].get("flags", {}).get("svg", None)
        print(f"Failed to retrieve flag for country: {fullname}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error retrieving flag for {fullname}: {e}")
        return None

@app.route("/")
def index():
    filter = request.args.get("filter", "").upper()
    page = int(request.args.get("page", 1))
    results = merge_data_with_flags(filter, page)
    total_pages = (results["total"] + 9) // 10  # 10 resultados por página
    
    return render_template("index.html", 
                         movies=results["movies"],
                         current_page=page,
                         total_pages=total_pages,
                         filter=filter)

@app.route("/api/movies")
def api_movies():
    filter = request.args.get("filter", "")
    page = int(request.args.get("page", 1))
    return jsonify(merge_data_with_flags(filter, page))

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
