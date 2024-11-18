from flask import Flask, render_template, request, jsonify
import requests
import json
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
import sqlite3

app = Flask(__name__)
apikey = "c8e2504d"


def init_db():
    conn=sqlite3.connect('cache.db')
    cursor=conn.cursor()

    cursor.execute(
        """CREATE TABLE IF NOT EXISTS Movie(imdbID TEXT PRIMARY KEY,title TEXT,year TEXT)"""
    )

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Country (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   name TEXT UNIQUE NOT NULL,
                   flag_url TEXT
                   )"""
        )
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS MovieCountry(
        movie_id TEXT,
        country_name TEXT,
        PRIMARY KEY (movie_id,country_name),
        FOREIGN KEY (movie_id) REFERENCES Movie(imdbID),
        FOREIGN KEY (country_name) REFERENCES Country(name)
    
        )"""
    )

    conn.commit()
    conn.close()

def GetMovieDetailsCache(imdbID):
    conn=sqlite3.connect('cache.db')
    cursor=conn.cursor()

    cursor.execute("SELECT title,year FROM Movie WHERE imdbID=?", (imdbID,))
    movie=cursor.fetchone()

    if movie:
        conn.close()
        return {"Title":movie[0], "Year":movie[1]}
    else:
        movie_details_json= getmoviedetails(imdbID)
        if not movie_details_json:
            conn.close()
            return None
        movie_details=movie_details_json
        try:
            cursor.execute("INSERT INTO Movie(imdbID,title,year) VALUES(?,?,?)",(imdbID,movie_details["Title"],movie_details["Year"]))
            countries_names=movie_details.get("Country","").split(", ")
            for country_name in countries_names:
                cursor.execute("INSERT  OR IGNORE INTO Country(name) VALUES(?)",(country_name,))
                cursor.execute("INSERT OR IGNORE INTO MovieCountry(movie_id,country_name) VALUES(?,?)",(imdbID,country_name))

        except sqlite3.Error as e:
            conn.rollback()
            print("Transaction failed:",e)
        finally:
            conn.close()

        return movie_details

def getCountryFlagCached(country_name):
    conn=sqlite3.connect('cache.db')
    cursor=conn.cursor()
    cursor.execute("SELECT flag_url FROM Country WHERE name=?", (country_name,))
    country=cursor.fetchone()

    if country and country[0]:
        conn.close()
        return country[0]
    else:
        flag_url=get_country_flag(country_name)
        if flag_url:
            try:
                cursor.execute("INSERT OR IGNORE INTO Country(name,flag_url) VALUES(?,?)",(country_name,flag_url))
                conn.commit()
            except sqlite3.Error as e:
                conn.rollback()
                print("Transaction failed:",e)
            finally:
                conn.close()
        return flag_url
        



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

def merge_data_with_flags(filter_text, page=1):
    filmssearch_json = searchfilms(filter_text, page)
    if not filmssearch_json:
        return []

    filmssearch = filmssearch_json
    if "Search" not in filmssearch:
        return []

    moviesdetailswithflags = []
    # Uso de concurrencia para mejorar la velocidad
    with ThreadPoolExecutor() as executor:
        future_movies = [executor.submit(GetMovieDetailsCache, movie["imdbID"]) for movie in filmssearch["Search"]]
        for future in future_movies:
            moviedetails_json = future.result()
            if not moviedetails_json:
                continue

            moviedetails = moviedetails_json
            countries_names = moviedetails.get("Country", "").split(", ")
            countries = [{"name": country, "flag": getCountryFlagCached(country)} for country in countries_names]
            movie_with_flags = {
                "title": moviedetails["Title"],
                "year": moviedetails["Year"],
                "countries": countries
            }
            moviesdetailswithflags.append(movie_with_flags)

    return moviesdetailswithflags

@app.route("/")
def index():
    filter = request.args.get("filter", "").upper()
    page = int(request.args.get("page", 1))
    return render_template("index.html", movies=merge_data_with_flags(filter, page))

@app.route("/api/movies")
def api_movies():
    filter = request.args.get("filter", "")
    page = int(request.args.get("page", 1))
    return jsonify(merge_data_with_flags(filter, page))

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
