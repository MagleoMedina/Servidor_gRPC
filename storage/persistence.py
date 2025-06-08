# storage/persistence.py
"""
Capa de persistencia, durabilidad y concurrencia.
Gestiona el almacenamiento en memoria, el Write-Ahead Log (WAL) y los bloqueos.
"""

import os
import pickle
import threading
import time
from collections import defaultdict

# Número de bloqueos para el sistema de "striped locking".
# Un número mayor reduce la contención pero consume más memoria.
# Debe ser una potencia de 2 para una distribución eficiente con el operador AND.
NUM_LOCKS = 256

class Storage:
    """
    Gestiona el almacenamiento de datos clave-valor.
    - Almacén en memoria (dict) para lecturas rápidas.
    - Write-Ahead Log (WAL) para durabilidad.
    - Bloqueos por bandas (Striped Locks) para concurrencia.
    """
    def __init__(self, wal_filename='wal.log'):
        self._data = {}
        self._wal_filename = wal_filename
        self._wal_file = None
        self._start_time = time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())
        self._total_requests = 0

        # Inicializa los bloqueos por bandas (striped locks)
        self._locks = [threading.Lock() for _ in range(NUM_LOCKS)]

        self._load_from_wal()

    def _get_lock(self, key):
        """Devuelve el lock correspondiente a una clave."""
        # Usa el hash de la clave para seleccionar un lock.
        # El operador & (AND) es más rápido que % (módulo) si NUM_LOCKS es potencia de 2.
        return self._locks[hash(key) & (NUM_LOCKS - 1)]

    def _load_from_wal(self):
        """
        Carga el estado del almacén desde el archivo WAL al iniciar.
        Esto asegura la recuperación de datos después de un reinicio.
        """
        print(f"Cargando datos desde el WAL: {self._wal_filename}...")
        start_time = time.time()
        count = 0
        if os.path.exists(self._wal_filename):
            with open(self._wal_filename, 'rb') as f:
                while True:
                    try:
                        key, value = pickle.load(f)
                        self._data[key] = value
                        count += 1
                    except EOFError:
                        break # Fin del archivo
                    except Exception as e:
                        print(f"Error al leer el WAL, puede estar corrupto: {e}")
                        break
        
        # Abre el WAL en modo 'append' para futuras escrituras.
        self._wal_file = open(self._wal_filename, 'ab')
        duration = time.time() - start_time
        print(f"Recuperación completa. Se cargaron {count} registros en {duration:.2f} segundos.")

    def set(self, key, value):
        """
        Almacena un par (clave, valor) de forma persistente y segura.
        """
        lock = self._get_lock(key)
        with lock:
            # 1. Escribir en el Write-Ahead Log
            pickle.dump((key, value), self._wal_file)
            
            # 2. Forzar la escritura a disco (crucial para la durabilidad)
            self._wal_file.flush()
            os.fsync(self._wal_file.fileno())

            # 3. Actualizar el almacén en memoria
            self._data[key] = value
            self._total_requests += 1
        return True

    def get(self, key):
        """
        Obtiene un valor por su clave desde el almacén en memoria.
        """
        lock = self._get_lock(key)
        with lock:
            self._total_requests += 1
            return self._data.get(key)

    def get_prefix(self, prefix):
        """
        Obtiene todos los pares cuyo clave comienza con el prefijo dado.
        
        NOTA: Esta operación puede ser lenta en almacenes muy grandes.
        Bloquea todos los locks brevemente para obtener una copia de las claves
        y evitar inconsistencias mientras se itera.
        """
        # Para evitar un deadlock, los locks deben adquirirse siempre en el mismo orden.
        for lock in self._locks:
            lock.acquire()
        
        try:
            # Creamos una copia de las claves para minimizar el tiempo de bloqueo.
            keys_snapshot = list(self._data.keys())
        finally:
            # Liberamos los locks en orden inverso.
            for lock in reversed(self._locks):
                lock.release()

        self._total_requests += 1
        
        results = []
        for k in keys_snapshot:
            if k.startswith(prefix):
                # Volvemos a adquirir el lock específico para leer el valor de forma segura.
                lock = self._get_lock(k)
                with lock:
                    # Comprobamos si la clave todavía existe y coincide antes de añadirla
                    if k in self._data and k.startswith(prefix):
                        results.append({'key': k, 'value': self._data[k]})
        return results

    def get_stats(self):
        """
        Devuelve estadísticas sobre el estado del almacén.
        """
        return {
            'key_count': len(self._data),
            'start_time': self._start_time,
            'total_requests': self._total_requests
        }

    def close(self):
        """
        Cierra el archivo WAL de forma segura.
        """
        if self._wal_file:
            self._wal_file.close()

