from sqlalchemy.orm import Session
from .models import Slot, Load

# Pesos da função de custo de deslocamento da empilhadeira
# Ponto de entrada padrão: Corredor=1, Coluna=1, Nível=1
ENTRY_AISLE = 1
ENTRY_COLUMN = 1
ENTRY_LEVEL = 1

WEIGHT_AISLE = 10.0    # Custo de trocar de corredor
WEIGHT_COLUMN = 2.0   # Custo de deslocamento horizontal (coluna)
WEIGHT_LEVEL = 5.0    # Custo de elevação da lança da empilhadeira (nível)

def get_warehouse_occupancy(db: Session) -> float:
    """Calcula a taxa de ocupação geral do armazém (em percentual)"""
    total = db.query(Slot).count()
    if total == 0:
        return 0.0
    occupied = db.query(Slot).filter(Slot.is_occupied == True).count()
    return (occupied / total) * 100.0

def calculate_slot_cost(slot: Slot) -> float:
    """
    Função de custo baseada na distância do ponto de entrada (1, 1, 1).
    Minimizar este custo otimiza o deslocamento da empilhadeira.
    """
    dist_aisle = abs(slot.aisle - ENTRY_AISLE)
    dist_col = abs(slot.column - ENTRY_COLUMN)
    dist_level = abs(slot.level - ENTRY_LEVEL)
    
    cost = (dist_aisle * WEIGHT_AISLE) + (dist_col * WEIGHT_COLUMN) + (dist_level * WEIGHT_LEVEL)
    return cost

def suggest_best_slot(db: Session, is_imo: bool) -> Slot:
    """
    Implementa o motor de regras/heurística de IA para sugerir o melhor slot.
    """
    # 1. Obter a taxa de ocupação atual
    occupancy_rate = get_warehouse_occupancy(db)
    
    # 2. Definir o limite de altura com base na ocupação
    # Se ocupação < 40%, só usar alturas mais baixas (1, 2, 3, no máximo 4 de 7 disponíveis)
    max_allowed_level = 4 if occupancy_rate < 40.0 else 7
    
    # 3. Filtrar slots vazios compatíveis
    query = db.query(Slot).filter(Slot.is_occupied == False)
    
    # Restrição de altura
    query = query.filter(Slot.level <= max_allowed_level)
    
    # Restrição de Carga Perigosa (IMO)
    if is_imo:
        # Cargas perigosas só podem ir para posições designadas para IMO
        query = query.filter(Slot.is_imo_restricted == True)
    else:
        # Cargas normais não podem ir para posições IMO
        query = query.filter(Slot.is_imo_restricted == False)
        
    candidate_slots = query.all()
    
    if not candidate_slots:
        if is_imo:
            raise ValueError(
                "Área de segurança exclusiva para cargas IMO (Corredor 1, Colunas 1-3, Nível 1) está totalmente ocupada!"
            )
        else:
            raise ValueError(
                f"Nenhum espaço disponível para carga comum nos níveis permitidos. Limite de altura ativo: Nível {max_allowed_level} (Ocupação: {occupancy_rate:.1f}%)."
            )
        
    # 4. Avaliar o custo de deslocamento para cada candidato e retornar o menor
    best_slot = min(candidate_slots, key=calculate_slot_cost)
    return best_slot
