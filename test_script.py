# test_script.py
"""
Script para la ejecución automática de pruebas de rendimiento y validación.
Genera gráficos y archivos CSV con los resultados.
"""

import argparse
import csv
import os
import random
import signal
import string
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import grpc
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from proto import keyvalue_pb2, keyvalue_pb2_grpc

RESULTS_DIR = "resultados"
SERVER_LOG_FILE = "wal.log"

# --- Funciones de Ayuda ---

def start_server(port):
    """Inicia el proceso del servidor y devuelve el objeto del proceso."""
    print("Iniciando servidor...")
    # Usamos Popen para ejecutarlo en segundo plano
    process = subprocess.Popen(
        ['python', 'lbserver.py', '--port', str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(3) # Dar tiempo al servidor para que arranque
    if process.poll() is not None:
        # El proceso ha terminado, lo que indica un error
        stdout, stderr = process.communicate()
        raise RuntimeError(f"Fallo al iniciar el servidor:\nSTDOUT: {stdout.decode()}\nSTDERR: {stderr.decode()}")
    print("Servidor iniciado.\n")
    return process

def stop_server(process, graceful=True):
    """Detiene el proceso del servidor."""
    print("Deteniendo servidor...")
    if graceful:
        if os.name == 'nt':
            process.terminate()  # Windows: termina el proceso de forma "graceful"
        else:
            process.send_signal(signal.SIGINT)  # Unix: Ctrl+C
    else:
        process.kill()  # Simula un fallo abrupto
    
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        print("El servidor no se detuvo a tiempo, forzando cierre.")
        process.kill()

    print("Servidor detenido.\n")
    
def print_server_stats(port):
    with grpc.insecure_channel(f'localhost:{port}') as channel:
        stub = keyvalue_pb2_grpc.KeyValueStub(channel)
        response = stub.Stat(keyvalue_pb2.StatRequest())
        print("\n--- ESTADÍSTICAS DEL SERVIDOR ---")
        print(f"Hora de inicio: {response.server_start_time}")
        print(f"Total claves: {response.key_count}")
        print(f"Total operaciones: {response.total_requests}")
        print(f"Total sets: {response.set_count}")
        print(f"Total gets: {response.get_count}")
        print(f"Total getPrefix: {response.getprefix_count}")
        print("------------------------------\n")

def cleanup_logs():
    """Elimina el archivo de log del servidor."""
    if os.path.exists(SERVER_LOG_FILE):
        os.remove(SERVER_LOG_FILE)

def generate_random_value(size_in_bytes):
    """Genera un valor aleatorio del tamaño especificado."""
    return os.urandom(size_in_bytes)

# --- Funciones de Prueba ---

def client_worker(client_id, port, workload_type, value_size, duration_sec):
    """
    Función ejecutada por cada cliente concurrente.
    Realiza operaciones y registra las latencias.
    """
    address = f'localhost:{port}'
    latencies = []
    ops_count = 0
    start_time = time.time()

    # Aumentar límites de tamaño de mensaje para gRPC
    grpc_options = [
        ('grpc.max_send_message_length', 256* 1024 * 1024),
        ('grpc.max_receive_message_length', 256 * 1024 * 1024),
    ]

    with grpc.insecure_channel(address, options=grpc_options) as channel:
        stub = keyvalue_pb2_grpc.KeyValueStub(channel)
        
        while time.time() - start_time < duration_sec:
            key = f"client{client_id}-key-{random.randint(0, 10000)}"
            op_start_time = time.time()

            if workload_type == 'read':
                stub.Get(keyvalue_pb2.GetRequest(key=key))
            elif workload_type == 'write':
                value = generate_random_value(value_size)
                stub.Set(keyvalue_pb2.SetRequest(key=key, value=value))
            elif workload_type == 'mixed':
                op = random.random()
                if op < 0.4:
                    stub.Get(keyvalue_pb2.GetRequest(key=key))
                elif op < 0.8:
                    value = generate_random_value(value_size)
                    stub.Set(keyvalue_pb2.SetRequest(key=key, value=value))
                else:
                    # Aquí integramos el GetPrefix
                    prefix = f"client{client_id}-key-"
                    stub.GetPrefix(keyvalue_pb2.GetPrefixRequest(prefix=prefix, max_results=50))

            op_end_time = time.time()
            latencies.append((op_end_time - op_start_time) * 1000) # en ms
            ops_count += 1
            
    return latencies, ops_count

def run_latency_vs_size_test(port):
    """
    Prueba 1: Mide la latencia en función del tamaño del valor.
    """
    print("\n--- EJECUTANDO PRUEBA: LATENCIA vs TAMAÑO DE VALOR ---\n")
    value_sizes = [512, 4*1024, 512*1024, 1024*1024, 4*1024*1024] # 512B, 4KB, 512KB, 1MB, 4MB
    workloads = {'100% Lecturas': 'read', '50% Lecturas / 50% Escrituras': 'mixed'}
    results = []

    for name, w_type in workloads.items():
        print(f"  Carga de trabajo: {name}\n")
        for size in value_sizes:
            cleanup_logs()
            server_proc = start_server(port)
            
            # Pre-poblar datos para la prueba de lectura
            if w_type == 'read':
                grpc_options = [
                    ('grpc.max_send_message_length', 256 * 1024 * 1024),
                    ('grpc.max_receive_message_length', 256 * 1024 * 1024),
                ]
                with grpc.insecure_channel(f'localhost:{port}', options=grpc_options) as channel:
                    stub = keyvalue_pb2_grpc.KeyValueStub(channel)
                    print(f"    Pre-poblando datos para tamaño {size}...")
                    for i in range(100):
                         stub.Set(keyvalue_pb2.SetRequest(key=f"client0-key-{i}", value=generate_random_value(size)))
            
            latencies, _ = client_worker(0, port, w_type, size, duration_sec=10)
            
            # Forzar al menos 1 GetPrefix
            grpc_options = [
                ('grpc.max_send_message_length', 256 * 1024 * 1024),
                ('grpc.max_receive_message_length', 256 * 1024 * 1024),
            ]
            with grpc.insecure_channel(f'localhost:{port}', options=grpc_options) as channel:
                stub = keyvalue_pb2_grpc.KeyValueStub(channel)
                stub.GetPrefix(keyvalue_pb2.GetPrefixRequest(prefix="client0-key-", max_results=50))
            
            avg_latency = np.mean(latencies)
            p99_latency = np.percentile(latencies, 99)
            
            print(f"    Tamaño: {size/1024:.2f} KB -> Latencia media: {avg_latency:.2f} ms, p99: {p99_latency:.2f} ms")
            results.append([name, size, avg_latency, p99_latency])
            print_server_stats(port)
            stop_server(server_proc)

    # Guardar resultados en CSV
    csv_path = os.path.join(RESULTS_DIR, 'latencia_vs_tamaño.csv')
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['workload', 'value_size_bytes', 'avg_latency_ms', 'p99_latency_ms'])
        writer.writerows(results)
    print(f"Resultados guardados en {csv_path}")
    
    # Graficar Latencia vs Tamaño de Valor
    df = pd.read_csv(csv_path)

    for workload in df['workload'].unique():
        wdf = df[df['workload'] == workload]
        plt.plot(wdf['value_size_bytes'] / 1024, wdf['avg_latency_ms'], label=workload)

    plt.xlabel("Tamaño del valor (KB)")
    plt.ylabel("Latencia Promedio (ms)")
    plt.title("Latencia vs Tamaño del Valor")
    plt.legend()
    plt.grid(True)
    plot_path = os.path.join(RESULTS_DIR, 'grafico_latencia_vs_tamaño.png')
    plt.savefig(plot_path)
    print(f"Gráfico guardado en {plot_path}")
    plt.close()


def run_scalability_test(port):
    """
    Prueba 2: Mide la escalabilidad con múltiples clientes.
    """
    print("\n--- EJECUTANDO PRUEBA: ESCALABILIDAD (LATENCIA Y RENDIMIENTO) ---\n")
    client_counts = [1, 2, 4, 8, 16, 32]
    fixed_value_size = 1024 # 1KB
    test_duration = 15 # segundos
    results = []

    cleanup_logs()
    server_proc = start_server(port)

    for n_clients in client_counts:
        print(f"  Probando con {n_clients} clientes...")
        all_latencies = []
        total_ops = 0

        with ThreadPoolExecutor(max_workers=n_clients) as executor:
            futures = [executor.submit(client_worker, i, port, 'mixed', fixed_value_size, test_duration) for i in range(n_clients)]
            
            for future in as_completed(futures):
                latencies, ops_count = future.result()
                all_latencies.extend(latencies)
                total_ops += ops_count
        
        avg_latency = np.mean(all_latencies) if all_latencies else 0
        throughput = total_ops / test_duration # ops/sec

        print(f"    Clientes: {n_clients} -> Rendimiento: {throughput:.2f} ops/sec, Latencia media: {avg_latency:.2f} ms\n")
        results.append([n_clients, throughput, avg_latency])
    print_server_stats(port)
    stop_server(server_proc)

    # Guardar resultados en CSV
    csv_path = os.path.join(RESULTS_DIR, 'escalabilidad.csv')
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['num_clients', 'throughput_ops_sec', 'avg_latency_ms'])
        writer.writerows(results)
    print(f"Resultados guardados en {csv_path}")

    # Generar gráfico
    data = np.array(results)
    fig, ax1 = plt.subplots()

    color = 'tab:red'
    ax1.set_xlabel('Número de Clientes Concurrentes')
    ax1.set_ylabel('Rendimiento (ops/sec)', color=color)
    ax1.plot(data[:,0], data[:,1], 'o-', color=color)
    ax1.tick_params(axis='y', labelcolor=color)

    ax2 = ax1.twinx()
    color = 'tab:blue'
    ax2.set_ylabel('Latencia Promedio (ms)', color=color)
    ax2.plot(data[:,0], data[:,2], 's--', color=color)
    ax2.tick_params(axis='y', labelcolor=color)
    
    plt.title('Rendimiento y Latencia vs. Clientes Concurrentes')
    fig.tight_layout()
    plot_path = os.path.join(RESULTS_DIR, 'grafico_escalabilidad.png')
    plt.savefig(plot_path)
    print(f"Gráfico guardado en {plot_path}")
    plt.close()


def run_durability_and_restart_test(port):
    """
    Prueba 3: Valida la durabilidad y mide el tiempo de reinicio.
    """
    print("\n--- EJECUTANDO PRUEBA: DURABILIDAD Y TIEMPO DE REINICIO ---\n")
    num_keys_to_write = 10000 # Reducido de 10M para una prueba rápida. Cambiar a 10_000_000 para la prueba completa.
    
    # --- Fase 1: Pre-llenado y fallo ---
    print(f"  Fase 1: Escribiendo {num_keys_to_write} claves y simulando un fallo...\n")
    cleanup_logs()
    server_proc = start_server(port)

    keys_written = set()
    with grpc.insecure_channel(f'localhost:{port}', options=[
        ('grpc.max_send_message_length', 256 * 1024 * 1024),
        ('grpc.max_receive_message_length', 256 * 1024 * 1024),
    ]) as channel:
        stub = keyvalue_pb2_grpc.KeyValueStub(channel)
        for i in range(num_keys_to_write):
            key = f"durability-key-{i}"
            value = f"value-{i}".encode('utf-8')
            stub.Set(keyvalue_pb2.SetRequest(key=key, value=value))
            keys_written.add(key)
            if i % 1000 == 0:
                print(f"    ... {i}/{num_keys_to_write} claves escritas")

    print("  Simulando fallo del servidor (kill -9)...")
    print_server_stats(port)
    stop_server(server_proc, graceful=False)

    # --- Fase 2: Recuperación y validación ---
    print("\n  Fase 2: Reiniciando servidor y validando datos...\n")
    start_time = time.time()
    server_proc = start_server(port)
    recovery_time = time.time() - start_time
    print(f"  Tiempo de recuperación del servidor (reinicio en frío): {recovery_time:.2f} segundos")

    # Medir latencia "en frío" (justo después de reiniciar)
    with grpc.insecure_channel(f'localhost:{port}', options=[
        ('grpc.max_send_message_length', 256 * 1024 * 1024),
        ('grpc.max_receive_message_length', 256 * 1024 * 1024),
    ]) as channel:
        stub = keyvalue_pb2_grpc.KeyValueStub(channel)
        
        # Validación de datos
        print("  Validando datos perdidos...")
        lost_keys = 0
        sample_keys_to_check = random.sample(list(keys_written), min(100, len(keys_written)))
        for key in sample_keys_to_check:
            response = stub.Get(keyvalue_pb2.GetRequest(key=key))
            if not response.found:
                lost_keys += 1
        
        if lost_keys == 0:
            print(" VALIDACIÓN DE DURABILIDAD: CORRECTO, no se perdieron datos.\n")
        else:
            print(f" VALIDACIÓN DE DURABILIDAD: FALLO, se perdieron {lost_keys} de 100 claves de muestra.\n")

        # Latencia en frío vs caliente
        cold_latencies = []
        for key in sample_keys_to_check:
            op_start_time = time.time()
            stub.Get(keyvalue_pb2.GetRequest(key=key))
            cold_latencies.append((time.time() - op_start_time) * 1000)

        hot_latencies = []
        for key in sample_keys_to_check: # Leer las mismas claves de nuevo
            op_start_time = time.time()
            stub.Get(keyvalue_pb2.GetRequest(key=key))
            hot_latencies.append((time.time() - op_start_time) * 1000)

        print(f"  Latencia de lectura 'en frío' (media): {np.mean(cold_latencies):.3f} ms")
        print(f"  Latencia de lectura 'en caliente' (media): {np.mean(hot_latencies):.3f} ms")
        
        # Ejecutar al menos un GetPrefix durante la validación:
        stub.GetPrefix(keyvalue_pb2.GetPrefixRequest(prefix="durability-key-", max_results=50))
        
    # Graficar Frío vs Caliente
    labels = ['Frío', 'Caliente']
    values = [np.mean(cold_latencies), np.mean(hot_latencies)]

    plt.bar(labels, values, color=['orange', 'green'])
    plt.ylabel('Latencia Promedio (ms)')
    plt.title('Lectura en Frío vs Caliente')
    plot_path = os.path.join(RESULTS_DIR, 'grafico_frio_vs_caliente.png')
    plt.savefig(plot_path)
    print(f"Gráfico guardado en {plot_path}")
    plt.close()
    print_server_stats(port)
    stop_server(server_proc)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Script de pruebas para el almacén clave-valor.')
    parser.add_argument('--port', type=int, default=50051, help='Puerto del servidor a probar.')
    args = parser.parse_args()

    if not os.path.exists(RESULTS_DIR):
        os.makedirs(RESULTS_DIR)

    run_latency_vs_size_test(args.port)
    run_scalability_test(args.port)
    run_durability_and_restart_test(args.port)

    print("\n--- Todas las pruebas han finalizado. Revisa la carpeta 'resultados' ---")