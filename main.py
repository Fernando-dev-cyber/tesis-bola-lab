import os
import jwt
from fastapi import FastAPI, Request, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from database import engine, Base, get_db
import models
from redis_client import registrar_pertenencia_cache, verificar_pertenencia_cache

JWT_SECRET = os.getenv("JWT_SECRET", "super_secret_jwt_key_2026")
JWT_ALGORITHM = "HS256"

# Crea las tablas al iniciar
Base.metadata.create_all(bind=engine)

app = FastAPI(title="BOLA Mitigation Lab API", version="1.0.0")



# True = Middleware Bloquea BOLA (Capa 2 Activa)
# False = Backend Vulnerable a BOLA 

PROTECCION_BOLA_ACTIVA = True


@app.middleware("http")
async def interceptor_abac_bola(request: Request, call_next):
    """
    Middleware Interceptor (Capa 2):
    Extrae el 'sub' del JWT y compara con el 'id' del objeto solicitado.
    """
    path = request.url.path
    
    # Interceptamos solicitudes a cuentas: GET /api/v1/cuentas/{id}
    if PROTECCION_BOLA_ACTIVA and path.startswith("/api/v1/cuentas/"):
        try:
            # 1. Extraer identificador de la URL
            cuenta_id = path.split("/")[-1]
            if cuenta_id.isdigit():
                cuenta_id = int(cuenta_id)
                
                # 2. Extraer y decodificar Token JWT
                auth_header = request.headers.get("Authorization")
                if not auth_header or not auth_header.startswith("Bearer "):
                    return JSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={"detail": "Token de autorizacion ausente o invalido"}
                    )
                
                token = auth_header.split(" ")[1]
                payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
                usuario_solicitante_id = payload.get("sub")

                # 3. Verificación de Pertenencia ABAC en Redis (Caché rápida)
                es_propietario = verificar_pertenencia_cache(cuenta_id, usuario_solicitante_id)

                # 4. Bloqueo inmediato si no hay coincidencia
                if not es_propietario:
                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={
                            "error": "Acceso Denegado (BOLA Mitigado)",
                            "detail": f"El usuario {usuario_solicitante_id} no tiene permiso sobre la cuenta {cuenta_id}"
                        }
                    )
        except jwt.PyJWTError:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Token JWT invalido o expirado"}
            )
        except Exception as e:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": f"Error interno en middleware de seguridad: {str(e)}"}
            )

    response = await call_next(request)
    return response





# -------------------------------------------------------------------
# Endpoints de la API
# -------------------------------------------------------------------


@app.get("/api/v1/cuentas/{cuenta_id}")
def obtener_cuenta(cuenta_id: int, db: Session = Depends(get_db)):
    cuenta = db.query(models.Cuenta).filter(models.Cuenta.id == cuenta_id).first()
    if not cuenta:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    
    return {
        "id": cuenta.id,
        "numero_cuenta": cuenta.numero_cuenta,
        "saldo": cuenta.saldo,
        "propietario_id": cuenta.propietario_id
    }


@app.post("/api/v1/seed")
def poblar_datos_laboratorio(db: Session = Depends(get_db)):
    """Puebla la BD y Redis con dos usuarios de prueba para el laboratorio BOLA"""
    db.query(models.Cuenta).delete()
    db.query(models.Usuario).delete()
    db.commit()

    # Usuario A (Dueño de cuenta 100)
    user_a = models.Usuario(id=1, username="usuario_a", email="a@test.com")
    # Usuario B (Dueño de cuenta 101 - Atacante en la simulación)
    user_b = models.Usuario(id=2, username="usuario_b", email="b@test.com")
    
    db.add_all([user_a, user_b])
    db.commit()

    cuenta_a = models.Cuenta(id=100, numero_cuenta="ACC-100-AAA", saldo=5000.0, propietario_id=user_a.id)
    cuenta_b = models.Cuenta(id=101, numero_cuenta="ACC-101-BBB", saldo=150.0, propietario_id=user_b.id)

    db.add_all([cuenta_a, cuenta_b])
    db.commit()

    # Sincronizar en Redis
    registrar_pertenencia_cache(100, user_a.id)
    registrar_pertenencia_cache(101, user_b.id)

    # Tokens de prueba para Postman
    token_user_a = jwt.encode({"sub": user_a.id, "username": user_a.username}, JWT_SECRET, algorithm=JWT_ALGORITHM)
    token_user_b = jwt.encode({"sub": user_b.id, "username": user_b.username}, JWT_SECRET, algorithm=JWT_ALGORITHM)

    return {
        "message": "Datos de laboratorio creados e hidratados en Redis exitosamente",
        "tokens_de_prueba": {
            "Usuario_A (Dueño cuenta 100)": token_user_a,
            "Usuario_B (Dueño cuenta 101 - Atacante BOLA)": token_user_b
        }
    }