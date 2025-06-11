# lbclient.py
"""
Cliente de línea de comandos para interactuar con el servidor gRPC.
"""
import argparse
import grpc
from proto import keyvalue_pb2, keyvalue_pb2_grpc

def run_command(args):
    """Ejecuta un comando en el servidor."""
    address = f'localhost:{args.port}'
    # Set max message size to 32MB for both send and receive
    max_msg_len = 128 * 1024 * 1024
    with grpc.insecure_channel(
        address,
        options=[
            ('grpc.max_send_message_length', max_msg_len),
            ('grpc.max_receive_message_length', max_msg_len)
        ]
    ) as channel:
        stub = keyvalue_pb2_grpc.KeyValueStub(channel)
        
        if args.command == 'set':
            # El valor se codifica como bytes
            value_bytes = args.value.encode('utf-8')
            response = stub.Set(keyvalue_pb2.SetRequest(key=args.key, value=value_bytes))
            print(f"Set exitoso: {response.success}")

        elif args.command == 'get':
            response = stub.Get(keyvalue_pb2.GetRequest(key=args.key))
            if response.found:
                # El valor se decodifica de bytes a string para mostrarlo
                print(f"Valor: {response.value.decode('utf-8')}")
            else:
                print("Clave no encontrada.")

        elif args.command == 'getPrefix':
            response = stub.GetPrefix(keyvalue_pb2.GetPrefixRequest(prefix=args.prefix))
            if not response.pairs:
                print("No se encontraron claves con ese prefijo.")
            else:
                print(f"Se encontraron {len(response.pairs)} pares:")
                for pair in response.pairs:
                    print(f"  - {pair.key}: {pair.value.decode('utf-8')}")
                    
        elif args.command == 'stat':
            response = stub.Stat(keyvalue_pb2.StatRequest())
            print("--- Estadísticas del Servidor ---")
            print(f"Número de claves: {response.key_count}")
            print(f"Total de peticiones: {response.total_requests}")
            print(f"Servidor iniciado el: {response.server_start_time}")
            print("-----------------------------")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Cliente para el almacén clave-valor gRPC.')
    parser.add_argument('--port', type=int, default=50051, help='Puerto del servidor.')

    subparsers = parser.add_subparsers(dest='command', required=True, help='Comando a ejecutar')

    # Comando 'set'
    parser_set = subparsers.add_parser('set', help='Almacena una clave y un valor.')
    parser_set.add_argument('key', type=str, help='La clave a almacenar.')
    parser_set.add_argument('value', type=str, help='El valor a almacenar.')

    # Comando 'get'
    parser_get = subparsers.add_parser('get', help='Obtiene el valor de una clave.')
    parser_get.add_argument('key', type=str, help='La clave a obtener.')

    # Comando 'getPrefix'
    parser_get_prefix = subparsers.add_parser('getPrefix', help='Obtiene claves por prefijo.')
    parser_get_prefix.add_argument('prefix', type=str, help='El prefijo a buscar.')

    # Comando 'stat'
    parser_stat = subparsers.add_parser('stat', help='Muestra las estadísticas del servidor.')
    
    args = parser.parse_args()
    run_command(args)
