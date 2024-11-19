class StressTestConfig:
    USERS = {
        'light': {
            'users': 50,
            'spawn_rate': 10,
            'duration': '5m'
        },
        'medium': {
            'users': 100,
            'spawn_rate': 20,
            'duration': '10m'
        },
        'heavy': {
            'users': 200,
            'spawn_rate': 40,
            'duration': '15m'
        }
    }

    PERFORMANCE_THRESHOLDS = {
        'response_time_95': 2000,  # 95% de las respuestas deben ser más rápidas que esto (ms)
        'error_rate': 0.01,        # Tasa de error máxima aceptable (1%)
        'rps_min': 10              # Requests por segundo mínimos
    }