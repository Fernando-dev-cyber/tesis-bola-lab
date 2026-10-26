import os
import redis

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

redis_db = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)

def registrar_pertenencia_cache(cuenta_id: int, propietario_id: int):
    """Guarda en Redis la relación de pertenencia objeto -> propietario"""
    key = f"ownership:cuenta:{cuenta_id}"
    redis_db.set(key, str(propietario_id))

def verificar_pertenencia_cache(cuenta_id: int, usuario_id: int) -> bool:
    """Consulta rápida en memoria si el recurso pertenece al usuario"""
    key = f"ownership:cuenta:{cuenta_id}"
    propietario_id = redis_db.get(key)
    
    if propietario_id is None:
        return False
        
    return str(propietario_id) == str(usuario_id)