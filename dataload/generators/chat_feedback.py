"""Gerador da coleção chat_feedback."""


class SemSessoesChatError(RuntimeError):
    """Indica que não existem sessões que possam receber feedback."""


def gerar(quantidade: int) -> list[dict]:
    raise NotImplementedError("O gerador de chat_feedback ainda não foi implementado.")
