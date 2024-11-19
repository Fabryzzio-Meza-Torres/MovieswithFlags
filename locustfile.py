from locust import HttpUser, task, between

class MovieSearchUser(HttpUser):
    # Tiempo de espera entre peticiones (entre 1 y 5 segundos)
    wait_time = between(1, 5)
    
    # Lista de términos de búsqueda comunes para variar las peticiones
    search_terms = [
        "superman",
        "batman",
        "spider",
        "iron man",
        "thor",
        "transformers",
        "star wars",
        "matrix",
        "lord",
        "harry"
    ]
    
    def on_start(self):
        """Método que se ejecuta cuando un usuario virtual inicia"""
        pass

    @task(1)
    def search_movies(self):
        """Búsqueda de películas con diferentes términos y páginas"""
        for term in self.search_terms:
            # Prueba diferentes páginas para cada término
            for page in range(1, 4):
                with self.client.get(
                    f"/api/movies?filter={term}&page={page}",
                    catch_response=True
                ) as response:
                    if response.status_code == 200:
                        # Verificar que la respuesta sea JSON válido
                        try:
                            movies = response.json()
                            if not isinstance(movies.get("movies", []), list):
                                response.failure("Response is not a valid movie list")
                        except ValueError:
                            response.failure("Response is not valid JSON")
                    else:
                        response.failure(f"Got status code {response.status_code}")

    @task(2)
    def homepage_load(self):
        """Carga de la página principal con diferentes filtros"""
        for term in self.search_terms:
            with self.client.get(
                f"/?filter={term}&page=1",
                catch_response=True
            ) as response:
                if response.status_code != 200:
                    response.failure(f"Got status code {response.status_code}")