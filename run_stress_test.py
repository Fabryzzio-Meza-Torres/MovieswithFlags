import subprocess
from stress_config import StressTestConfig

def run_stress_test(level='light'):
    config = StressTestConfig.USERS[level]
    
    command = [
        'python', '-m', 'locust',
        '-f', 'locustfile.py',
        '--host=http://localhost:5000',
        '--headless',
        '-u', str(config['users']),
        '-r', str(config['spawn_rate']),
        '--run-time', config['duration']
    ]
    
    process = subprocess.Popen(command)
    
    try:
        process.wait()
    except KeyboardInterrupt:
        process.terminate()
    
if __name__ == "__main__":
    import sys
    level = sys.argv[1] if len(sys.argv) > 1 else 'light'
    run_stress_test(level)