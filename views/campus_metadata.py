PREDIO_VISUAL = {
    "Salas de aula": {"emoji": "📗", "categoria": "Normal"},
    "Laboratórios": {"emoji": "🔬", "categoria": "Laboratorio"},
    "Salas de Metodologia Ativa": {"emoji": "💡", "categoria": "Metodologia"},
    "Salas de Atividade Física": {"emoji": "🏀", "categoria": "Quadra"},
}

CATEGORIAS_SALA = {
    "Laboratorio": {"label": "Laboratório", "emoji": "🔬"},
    "Normal": {"label": "Sala Normal", "emoji": "📗"},
    "Metodologia": {"label": "Metodologia Ativa", "emoji": "💡"},
    "Quadra": {"label": "Quadra/Piscina", "emoji": "🏀"},
}


def visual_predio(nome):
    return PREDIO_VISUAL.get(nome, {"emoji": "🏢", "categoria": "Normal"})


def categoria_da_sala(predio, categoria=None):
    if categoria and str(categoria).strip():
        return str(categoria).strip()
    return visual_predio(predio)["categoria"]