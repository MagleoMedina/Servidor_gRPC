# Servidor gRPC

## Descripción

Este proyecto implementa un sistema de almacenamiento **clave-valor distribuido (no replicado)** utilizando llamadas a procedimientos remotos (RPC) mediante la biblioteca **gRPC**.

El objetivo fue diseñar un servidor persistente capaz de:

- Soportar múltiples clientes concurrentes.
- Garantizar alta durabilidad ante fallos (con recuperación automática).
- Realizar pruebas automatizadas de rendimiento, escalabilidad y recuperación.

El proyecto fue desarrollado como práctica para la materia **Sistemas Distribuidos**.

## Tecnologías utilizadas

- Python
- gRPC
- Protocol Buffers
- NumPy
- Matplotlib
- PyInstaller (para generación de ejecutables)
- Make (para automatización)

## Funcionalidades implementadas

- Almacenamiento de pares clave-valor persistente mediante **Write-Ahead Log (WAL)**.
- API RPC con operaciones:
  - `Set(key, value)`
  - `Get(key)`
  - `GetPrefix(prefix)`
  - `Stat()`
- Recuperación automática tras fallo de servidor.
- Control de concurrencia mediante bloqueos segmentados (striped locking).
- Pruebas automatizadas de:
  - Latencia vs Tamaño de Valor.
  - Durabilidad y Tiempo de Recuperación.
  - Escalabilidad (rendimiento con clientes concurrentes).
- Generación automática de gráficos de resultados.
- Automatización completa mediante `Makefile`.

## Estructura del proyecto

- `Makefile`: automatiza instalación, compilación y ejecución.
- `proto/`: definiciones de servicio RPC (`keyvalue.proto`).
- `storage/`: módulo de persistencia (`persistence.py`) y control de concurrencia.
- `lbserver.py` / `lbserver.exe`: servidor.
- `lbclient.py` / `lbclient.exe`: cliente de referencia (no utilizado en pruebas).
- `test_script.py` / `test_script.exe`: cliente principal de pruebas automatizadas.
- `resultados/`: carpeta de resultados (CSV, PNG).
- `wal.log`: archivo de persistencia generado durante la ejecución.

## Instrucciones de Ejecución

### Flujo normal de uso

Toda la ejecución de pruebas se realiza mediante el script `test_script`, el cual automatiza las pruebas de latencia, durabilidad y escalabilidad.

#### Desde el código fuente:

```bash
make setup
make proto
make test
```

#### Desde el ejecutable (Windows): 

Ejecutar el archivo test_script.exe


Este flujo ejecuta el servidor, corre todas las pruebas y genera los resultados automáticamente.

### Ejecución manual (solo para referencia)
El servidor (lbserver) y el cliente (lbclient) fueron incluidos como parte de los requerimientos del proyecto, pero no forman parte del flujo de pruebas automatizadas. No generan resultados por sí mismos.

## Resultados
Los resultados de las pruebas se almacenan automáticamente en la carpeta resultados/, incluyendo:

* latencia_vs_tamaño.csv y su gráfico asociado.

* escalabilidad.csv y su gráfico.

* grafico_frio_vs_caliente.png (prueba de durabilidad).

## Autores
    
* Magleo Medina
  * Usuario de GitHub: MagleoMedina
 
* Franmari Garcia 
  * Usuario de GitHub: franmariG
