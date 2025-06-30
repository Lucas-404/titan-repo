import random
from datetime import datetime

def obter_data_hora():
    """Obtém a data e hora atual do sistema"""
    agora = datetime.now()
    return {
        "status": "sucesso",
        "data_hora": agora.strftime("%Y-%m-%d %H:%M:%S"),
        "dia_semana": agora.strftime("%A"),
        "timestamp": agora.timestamp()
    }

def gerar_numero_aleatorio(minimo=1, maximo=100):
    """Gera um número aleatório entre o mínimo e máximo especificados"""
    try:
        numero = random.randint(minimo, maximo)
        return {
            "status": "sucesso",
            "numero": numero,
            "intervalo": f"{minimo}-{maximo}"
        }
    except Exception as e:
        return {"status": "erro", "mensagem": str(e)}