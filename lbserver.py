# lbserver.py
"""
Servidor gRPC para el almacén clave-valor.
Implementa los métodos RPC definidos en keyvalue.proto.
"""
import argparse
import time
from concurrent import futures

import grpc
from proto import keyvalue_pb2, keyvalue_pb2_grpc
from storage.persistence import Storage

class KeyValueServicer(keyvalue_pb2_grpc.KeyValueServicer):
    """
    Implementación del servicio gRPC KeyValue.
    """
    def __init__(self, storage):
        self.storage = storage

    def Set(self, request, context):
        """Maneja las peticiones Set."""
        success = self.storage.set(request.key, request.value)
        return keyvalue_pb2.SetResponse(success=success)

    def Get(self, request, context):
        """Maneja las peticiones Get."""
        value = self.storage.get(request.key)
        if value is not None:
            return keyvalue_pb2.GetResponse(found=True, value=value)
        else:
            return keyvalue_pb2.GetResponse(found=False)

    def GetPrefix(self, request, context):
        """Maneja las peticiones GetPrefix."""
        pairs = self.storage.get_prefix(request.prefix)
        pb_pairs = [keyvalue_pb2.KeyValuePair(key=p['key'], value=p['value']) for p in pairs]
        return keyvalue_pb2.GetPrefixResponse(pairs=pb_pairs)
    
    def Stat(self, request, context):
        """Maneja las peticiones Stat."""
        stats = self.storage.get_stats()
        return keyvalue_pb2.StatResponse(
            key_count=stats['key_count'],
            server_start_time=stats['start_time'],
            total_requests=stats['total_requests'],
            set_count=stats['set_count'],
            get_count=stats['get_count'],
            getprefix_count=stats['getprefix_count']
        )

def serve(port):
    """
    Inicia el servidor gRPC.
    """
    storage_instance = Storage()
    
    # Aumentar el tamaño máximo de mensaje a 32MB
    max_msg_len = 128 * 1024 * 1024
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=32),
        options=[
            ('grpc.max_send_message_length', max_msg_len),
            ('grpc.max_receive_message_length', max_msg_len)
        ]
    )
    keyvalue_pb2_grpc.add_KeyValueServicer_to_server(
        KeyValueServicer(storage_instance), server
    )
    
    server.add_insecure_port(f'[::]:{port}')
    server.start()
    print(f"Servidor iniciado. Escuchando en el puerto {port}.")
    
    try:
        while True:
            time.sleep(86400) # Un día
    except KeyboardInterrupt:
        print("Deteniendo el servidor...")
        storage_instance.close()
        server.stop(0)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Servidor gRPC para almacén clave-valor.')
    parser.add_argument('--port', type=int, default=50051, help='Puerto de escucha del servidor.')
    args = parser.parse_args()
    
    serve(args.port)