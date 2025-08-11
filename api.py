from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import sqlite3
import os
from contextlib import contextmanager

class Persona(BaseModel):
    id: Optional[int] = None
    nombre: str
    edad: int
    puesto: str

class PersonaCreate(BaseModel):
    nombre: str
    edad: int
    puesto: str

class PersonaUpdate(BaseModel):
    nombre: Optional[str] = None
    edad: Optional[int] = None
    puesto: Optional[str] = None

app = FastAPI(
    title="API Equipo de Trabajo", 
    description="API para gestionar personas del equipo de trabajo",
    version="1.0.0"
)

DATABASE_PATH = "equipo_trabajo.db"

def init_database():
    """Inicializar la base de datos SQLite"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS personas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            edad INTEGER NOT NULL,
            puesto TEXT NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()

@contextmanager
def get_db_connection():
    """Context manager para conexiones a la base de datos"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  
    try:
        yield conn
    finally:
        conn.close()

init_database()


@app.get("/")
def read_root():
    return {
        "message": "¡Bienvenido a la API del Equipo de Trabajo!", 
        "descripcion": "Gestiona personas del equipo con id, nombre, edad y puesto",
        "documentacion": "/docs"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/personas/", response_model=Persona)
def crear_persona(persona: PersonaCreate):
    """Agregar una nueva persona al equipo"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO personas (nombre, edad, puesto) VALUES (?, ?, ?)",
            (persona.nombre, persona.edad, persona.puesto)
        )
        conn.commit()
        persona_id = cursor.lastrowid
        
        return Persona(
            id=persona_id,
            nombre=persona.nombre,
            edad=persona.edad,
            puesto=persona.puesto
        )

@app.get("/personas/", response_model=List[Persona])
def obtener_equipo(skip: int = 0, limit: int = 100):
    """Obtener todas las personas del equipo"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM personas LIMIT ? OFFSET ?", (limit, skip))
        rows = cursor.fetchall()
        
        return [
            Persona(id=row["id"], nombre=row["nombre"], edad=row["edad"], puesto=row["puesto"])
            for row in rows
        ]

@app.get("/personas/{persona_id}", response_model=Persona)
def obtener_persona(persona_id: int):
    """Obtener una persona específica por ID"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM personas WHERE id = ?", (persona_id,))
        row = cursor.fetchone()
        
        if row:
            return Persona(id=row["id"], nombre=row["nombre"], edad=row["edad"], puesto=row["puesto"])
        else:
            raise HTTPException(status_code=404, detail="Persona no encontrada en el equipo")

@app.put("/personas/{persona_id}", response_model=Persona)
def actualizar_persona(persona_id: int, persona_update: PersonaUpdate):
    """Actualizar información de una persona del equipo"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM personas WHERE id = ?", (persona_id,))
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Persona no encontrada en el equipo")
        
        update_data = persona_update.dict(exclude_unset=True)
        if not update_data:
            return Persona(id=row["id"], nombre=row["nombre"], edad=row["edad"], puesto=row["puesto"])
        
        set_clauses = []
        values = []
        for field, value in update_data.items():
            set_clauses.append(f"{field} = ?")
            values.append(value)
        
        values.append(persona_id)  
        
        update_query = f"UPDATE personas SET {', '.join(set_clauses)} WHERE id = ?"
        cursor.execute(update_query, values)
        conn.commit()
        
        cursor.execute("SELECT * FROM personas WHERE id = ?", (persona_id,))
        updated_row = cursor.fetchone()
        
        return Persona(
            id=updated_row["id"],
            nombre=updated_row["nombre"],
            edad=updated_row["edad"],
            puesto=updated_row["puesto"]
        )

@app.delete("/personas/{persona_id}")
def eliminar_persona(persona_id: int):
    """Remover una persona del equipo"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM personas WHERE id = ?", (persona_id,))
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Persona no encontrada en el equipo")
        
        cursor.execute("DELETE FROM personas WHERE id = ?", (persona_id,))
        conn.commit()
        
        return {
            "message": f"Persona '{row['nombre']}' eliminada del equipo",
            "persona_eliminada": {
                "id": row["id"],
                "nombre": row["nombre"],
                "edad": row["edad"],
                "puesto": row["puesto"]
            }
        }


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)

    