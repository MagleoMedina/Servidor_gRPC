# Almacén Clave-Valor Persistente y Concurrente en Python

Este proyecto implementa un almacén clave-valor de alto rendimiento utilizando gRPC para la comunicación, un sistema de Write-Ahead Log (WAL) para durabilidad y bloqueos por bandas para concurrencia.

## Estructura del Proyecto


/
├── Makefile              # Comandos para compilar, ejecutar y probar
├── lbserver.py           # El servidor del almacén clave-valor
├── lbclient.py           # Un cliente de línea de comandos para interactuar con el servidor
├── test_script.py        # Script para ejecutar pruebas de rendimiento y validación
├── proto/
│   ├── init.py
│   ├── keyvalue.proto    # Definición del servicio gRPC
│   └── (Archivos generados)
├── storage/
│   ├── init.py
│   └── persistence.py    # Lógica de almacenamiento, persistencia y concurrencia
├── resultados/
│   └── (Aquí se guardarán los gráficos y CSV de las pruebas)
└── informe.md            # Documento explicativo del proyecto


## Requisitos

- Python 3.8+
- Bibliotecas de Python: `grpcio`, `grpcio-tools`, `protobuf`, `matplotlib`, `numpy`

## Pasos para la Ejecución

### 1. Preparar el Entorno

Puedes instalar las dependencias directamente o usar un entorno virtual.

```bash
# Opcional: Crear y activar un entorno virtual
python -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install grpcio grpcio-tools protobuf matplotlib numpy

O, si tienes make disponible, simplemente ejecuta:

make setup

2. Generar el Código gRPC

El Makefile también facilita este paso. El comando compilará el archivo .proto y creará los stubs de Python necesarios en el directorio proto/.

make proto

3. Iniciar el Servidor

python lbserver.py --port 50051

El servidor cargará los datos existentes desde wal.log si existe y comenzará a escuchar peticiones.
4. Usar el Cliente

El cliente de línea de comandos permite interactuar con el servidor.

Establecer un valor:

python lbclient.py --port 50051 set mykey "hello world"

Obtener un valor:

python lbclient.py --port 50051 get mykey

Obtener claves por prefijo:

python lbclient.py --port 50051 getPrefix my

Ver estadísticas del servidor:

python lbclient.py --port 50051 stat

5. Ejecutar las Pruebas de Rendimiento

El script de pruebas automatizadas ejecutará todos los experimentos y guardará los resultados (gráficos .png y datos .csv) en la carpeta resultados/.

¡Advertencia! La prueba de reinicio puede ser lenta ya que simula la escritura de 10 millones de claves.

python test_script.py --port 50051

También puedes usar el Makefile:

make test

6. Limpiar

Para eliminar los archivos generados y los logs:

make clean