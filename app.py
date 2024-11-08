from flask import Flask, render_template, request, jsonify
import requests
import json
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)
apikey = "c8e2504d"

# Empleamos un cache para guardar las respuestas de la API de paises y asi mejorar la velocidad y reducir su consumo
@lru_cache(maxsize=128)
def searchfilms(search_text, page=1):
    url = f"https://www.omdbapi.com/?s={search_text}&apikey={apikey}&page={page}"
    response = requests.get(url)
    if response.status_code == 200:
        return json.dumps(response.json())
    else:
        print("Failed to retrieve search results.")
        return None

@lru_cache(maxsize=128)
def getmoviedetails(imdbID):
    url = f"https://www.omdbapi.com/?i={imdbID}&apikey={apikey}"
    response = requests.get(url)
    if response.status_code == 200:
        return json.dumps(response.json())
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

    filmssearch = json.loads(filmssearch_json)
    if "Search" not in filmssearch:
        return []

    moviesdetailswithflags = []
    # Uso de concurrencia para mejorar la velocidad
    with ThreadPoolExecutor() as executor:
        future_movies = [executor.submit(getmoviedetails, movie["imdbID"]) for movie in filmssearch["Search"]]
        for future in future_movies:
            moviedetails_json = future.result()
            if not moviedetails_json:
                continue
            moviedetails = json.loads(moviedetails_json)
            countries_names = moviedetails.get("Country", "").split(", ")
            countries = [{"name": country, "flag": get_country_flag(country)} for country in countries_names]
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
    app.run(debug=True)
