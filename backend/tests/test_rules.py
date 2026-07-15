import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.database import Base
from backend.app.models import Slot, Load
from backend.app.rules import suggest_best_slot, get_warehouse_occupancy

# Setup de banco de dados SQLite em memória para testes
@pytest.fixture(name="db_session")
def fixture_db_session():
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    try:
        # Criar layout padrão de 2 corredores, 5 colunas, 7 níveis = 70 posições
        for aisle in [1, 2]:
            for col in range(1, 6):
                for level in range(1, 8):
                    # Posições IMO: Corredor 1, Colunas 1-2, Nível 1
                    is_imo = (aisle == 1 and col in [1, 2] and level == 1)
                    slot = Slot(
                        aisle=aisle,
                        column=col,
                        level=level,
                        is_occupied=False,
                        is_imo_restricted=is_imo,
                        load_id=None
                    )
                    db.add(slot)
        db.commit()
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_height_limit_under_40_percent(db_session):
    """
    Se a ocupação estiver abaixo de 40%, a IA só deve sugerir slots nos níveis 1 a 4.
    """
    # Atualmente a ocupação é 0% (abaixo de 40%)
    # Sugere posição para carga não IMO
    slot = suggest_best_slot(db_session, is_imo=False)
    assert slot.level <= 4


def test_height_limit_above_40_percent(db_session):
    """
    Se a ocupação for maior ou igual a 40%, a IA pode sugerir posições em alturas de 5 a 7.
    Para simular, ocuparemos os primeiros 30 slots do total de 70 (aproximadamente 42.8% de ocupação).
    """
    slots = db_session.query(Slot).all()
    # Ocupa 30 slots
    for i in range(30):
        slots[i].is_occupied = True
    db_session.commit()
    
    occupancy = get_warehouse_occupancy(db_session)
    assert occupancy >= 40.0
    
    # Com ocupação acima de 40%, as regras permitem sugestão nos níveis 5-7.
    # Vamos ocupar todas as posições livres dos níveis 1-4 para forçar a sugestão a ir para níveis > 4.
    slots_levels_1_4 = db_session.query(Slot).filter(Slot.level <= 4, Slot.is_occupied == False).all()
    for s in slots_levels_1_4:
        s.is_occupied = True
    db_session.commit()
    
    slot = suggest_best_slot(db_session, is_imo=False)
    assert slot.level > 4


def test_imo_cargo_restriction(db_session):
    """
    Cargas perigosas (IMO) devem ser obrigatoriamente alocadas em slots designados como IMO.
    """
    # Sugere posição para carga IMO
    slot = suggest_best_slot(db_session, is_imo=True)
    assert slot.is_imo_restricted is True
    assert slot.aisle == 1
    assert slot.level == 1
    assert slot.column in [1, 2]


def test_non_imo_cargo_restriction(db_session):
    """
    Cargas comuns (não IMO) NÃO devem ser alocadas em slots reservados para IMO.
    """
    slot = suggest_best_slot(db_session, is_imo=False)
    assert slot.is_imo_restricted is False
