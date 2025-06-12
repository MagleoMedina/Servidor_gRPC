# Makefile para automatizar las tareas comunes del proyecto (Compatible con Windows/Linux/macOS)

# Variables
PYTHON = python
PIP = pip
PROTOC = $(PYTHON) -m grpc_tools.protoc
PROTO_DIR = proto
GEN_DIR = $(PROTO_DIR)
PROTO_FILE = $(PROTO_DIR)/keyvalue.proto
SERVER_LOG = wal.log
RESULTS_DIR = resultados
# Comando multiplataforma para corregir la importación relativa en el código gRPC generado.
# Busca 'import keyvalue_pb2' y lo reemplaza con 'from . import keyvalue_pb2'.
FIX_IMPORT_CMD = $(PYTHON) -c "import re, os; fpath = os.path.join('$(subst /,\,$(GEN_DIR))', 'keyvalue_pb2_grpc.py'); content = open(fpath, 'r').read(); new_content = re.sub(r'^import (keyvalue_pb2.*)', r'from . import \1', content, flags=re.MULTILINE); open(fpath, 'w').write(new_content)"

.PHONY: all setup proto run_server run_client_get run_client_set test clean

all: setup proto

# Instala las dependencias de Python
setup:
	$(PIP) install --upgrade pip
	$(PIP) install grpcio grpcio-tools protobuf matplotlib numpy pandas

# Genera el código gRPC a partir del archivo .proto
proto:
	@rem Comando para crear el directorio si no existe (compatible con Windows y Linux/macOS)
	@if not exist $(GEN_DIR) mkdir $(GEN_DIR)
	@rem Comando de Python para crear un __init__.py vacío (multiplataforma)
	$(PYTHON) -c "import os; open(os.path.join('$(subst /,\,$(GEN_DIR))', '__init__.py'), 'a').close()"
	$(PROTOC) -I$(PROTO_DIR) --python_out=$(GEN_DIR) --grpc_python_out=$(GEN_DIR) $(PROTO_FILE)
	@echo "Codigo gRPC generado en $(GEN_DIR)"
	@rem Corrige la importacion en el archivo generado para que sea una importacion relativa.
	$(FIX_IMPORT_CMD)
	@echo "Importacion gRPC corregida a relativa."

# Ejecuta el servidor
run_server:
	$(PYTHON) lbserver.py

# Ejemplo de como ejecutar el cliente para un 'get'
run_client_get:
	$(PYTHON) lbclient.py get mykey

# Ejemplo de como ejecutar el cliente para un 'set'
run_client_set:
	$(PYTHON) lbclient.py set mykey "myvalue"

# Ejecuta el script de pruebas de rendimiento
test:
	@if not exist $(RESULTS_DIR) mkdir $(RESULTS_DIR)
	$(PYTHON) test_script.py
	@echo "Pruebas completadas. Resultados en la carpeta: $(RESULTS_DIR)"

# Limpia los archivos generados y los logs
clean:
	@rem Usamos 'del' en Windows y 'rm' en otros sistemas
	@if exist $(subst /,\,$(GEN_DIR))\*_pb2*.py del $(subst /,\,$(GEN_DIR))\*_pb2*.py
	@if exist $(subst /,\,$(SERVER_LOG)) del $(subst /,\,$(SERVER_LOG))
	@if exist $(subst /,\,$(RESULTS_DIR)) rmdir /s /q $(subst /,\,$(RESULTS_DIR))
	@echo "Archivos generados y logs eliminados."
