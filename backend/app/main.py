import os
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List

from .database import engine, Base, get_db
from .models import Slot, Load
from .schemas import (
    SlotOut,
    LoadOut,
    SuggestRequest,
    SuggestResponse,
    ConfirmRequest,
    OccupancyStats
)
from .rules import suggest_best_slot, get_warehouse_occupancy

# Criar tabelas no banco de dados se não existirem
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Argos Armazém API", version="1.0.0")

@app.on_event("startup")
def startup_event():
    # Detecta se há uma URL pública configurada (como no Koyeb)
    # Caso contrário, monta o endereço usando o localhost e a porta configurada no ambiente
    public_url = os.getenv("PUBLIC_URL")
    if not public_url:
        port = os.getenv("PORT", "8080")
        public_url = f"http://localhost:{port}"

    print("\n" + "="*80)
    print("PROJETO ARGOS ARMAZÉM inicializado com sucesso!")
    print(f"Acesse o Gêmeo Digital em: {public_url}")
    print(f"Documentação da API em:     {public_url}/docs")
    print("="*80 + "\n")

# Habilitar CORS para desenvolvimento local (Angular rodando na porta 4200)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def init_db():
    """Inicializa os slots padrão do armazém se estiverem vazios"""
    db = next(get_db())
    try:
        if db.query(Slot).count() == 0:
            # Layout padrão: 2 corredores, 10 colunas, 7 níveis = 140 posições
            for aisle in [1, 2]:
                for column in range(1, 11):
                    for level in range(1, 8):
                        # Posições de IMO designadas: Corredor 1, Colunas 1 a 3, Nível 1
                        is_imo = (aisle == 1 and column in [1, 2, 3] and level == 1)
                        slot = Slot(
                            aisle=aisle,
                            column=column,
                            level=level,
                            is_occupied=False,
                            is_imo_restricted=is_imo,
                            load_id=None
                        )
                        db.add(slot)
            db.commit()
    finally:
        db.close()

# Rodar inicialização do banco
init_db()


@app.get("/api/warehouse/state", response_model=List[SlotOut])
def get_warehouse_state(db: Session = Depends(get_db)):
    """Retorna todas as posições do armazém e seus estados"""
    slots = db.query(Slot).order_by(Slot.aisle, Slot.column, Slot.level).all()
    return slots


@app.get("/api/warehouse/occupancy", response_model=OccupancyStats)
def get_occupancy_stats(db: Session = Depends(get_db)):
    """Retorna estatísticas detalhadas de ocupação e limites atuais"""
    total = db.query(Slot).count()
    occupied = db.query(Slot).filter(Slot.is_occupied == True).count()
    occupancy_rate = (occupied / total * 100.0) if total > 0 else 0.0
    
    imo_total = db.query(Slot).filter(Slot.is_imo_restricted == True).count()
    imo_occupied = db.query(Slot).filter(Slot.is_imo_restricted == True, Slot.is_occupied == True).count()
    
    limit_height = 4 if occupancy_rate < 40.0 else 7
    
    return OccupancyStats(
        total_slots=total,
        occupied_slots=occupied,
        occupancy_rate=round(occupancy_rate, 2),
        imo_slots=imo_total,
        occupied_imo_slots=imo_occupied,
        limit_height=limit_height
    )


@app.post("/api/allocation/suggest", response_model=SuggestResponse)
def get_allocation_suggestion(req: SuggestRequest, db: Session = Depends(get_db)):
    """Recebe dados da carga e sugere a posição ideal de alocação"""
    try:
        best_slot = suggest_best_slot(db, req.is_imo)
        return SuggestResponse(
            slot_id=best_slot.id,
            aisle=best_slot.aisle,
            column=best_slot.column,
            level=best_slot.level,
            message=f"Melhor posição encontrada no Corredor {best_slot.aisle}, Coluna {best_slot.column}, Nível {best_slot.level}."
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.post("/api/allocation/confirm", response_model=SlotOut)
def confirm_allocation(req: ConfirmRequest, db: Session = Depends(get_db)):
    """Confirma o armazenamento da carga em uma posição específica"""
    slot = db.query(Slot).filter(Slot.id == req.slot_id).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot não encontrado")
    
    if slot.is_occupied:
        raise HTTPException(status_code=400, detail="Esta posição já está ocupada")
        
    # Validar IMO
    if req.is_imo and not slot.is_imo_restricted:
        raise HTTPException(status_code=400, detail="Carga perigosa (IMO) só pode ser armazenada em slots IMO")
    if not req.is_imo and slot.is_imo_restricted:
        raise HTTPException(status_code=400, detail="Slots IMO são reservados apenas para cargas perigosas")
        
    # Criar registro da carga
    load = Load(
        sku=req.sku,
        name=req.name or f"Carga {req.sku}",
        weight=req.weight,
        is_imo=req.is_imo
    )
    db.add(load)
    db.flush()  # Obtém o ID gerado da carga
    
    # Atualizar slot
    slot.is_occupied = True
    slot.load_id = load.id
    db.commit()
    db.refresh(slot)
    return slot


@app.post("/api/allocation/unload", response_model=SlotOut)
def unload_slot(slot_id: int, db: Session = Depends(get_db)):
    """Libera uma posição do armazém (descarregamento)"""
    slot = db.query(Slot).filter(Slot.id == slot_id).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot não encontrado")
        
    if not slot.is_occupied:
        raise HTTPException(status_code=400, detail="Esta posição já está vazia")
        
    load_id = slot.load_id
    
    # Atualizar slot
    slot.is_occupied = False
    slot.load_id = None
    
    # Remover registro da carga correspondente
    if load_id:
        load = db.query(Load).filter(Load.id == load_id).first()
        if load:
            db.delete(load)
            
    db.commit()
    db.refresh(slot)
    return slot


@app.post("/api/warehouse/reset")
def reset_warehouse(db: Session = Depends(get_db)):
    """Reseta todo o armazém para o estado inicial (vazio)"""
    # Deleta todas as cargas
    db.query(Load).delete()
    # Libera todos os slots
    db.query(Slot).update({Slot.is_occupied: False, Slot.load_id: None})
    db.commit()
    return {"message": "Armazém reinicializado com sucesso!"}


# Servir arquivos estáticos do Angular na produção
static_dir = os.path.join(os.path.dirname(__file__), "../static")
if os.path.exists(static_dir):
    # Catch-all para rotas não-API direcionarem para o Angular (SPA Routing)
    @app.get("/{catchall:path}")
    async def serve_frontend(catchall: str):
        # Impedir que requisições de API caiam no catch-all
        if catchall.startswith("api"):
            raise HTTPException(status_code=404, detail="API Endpoint não encontrado")
        
        file_path = os.path.join(static_dir, catchall)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        
        # Caso a rota não exista fisicamente, envia o index.html (roteamento do Angular)
        return FileResponse(os.path.join(static_dir, "index.html"))
