from typing import Dict, Any
from neo4j import Driver
import math

# Opcional: uso do client Python da GDS
# from graphdatascience import GraphDataScience


def run_gds_feature_engineering(driver: Driver) -> Dict[str, Any]:
    """
    Projeta o grafo de Address/TRANSFER e escreve propriedades:
    - pagerank
    - degree (in/out e total)
    - louvain
    - triangleCount
    """
    results: Dict[str, Any] = {}
    with driver.session() as session:
        # Projeção (undirected para sinalizar conectividade geral)
        session.execute_write(
            lambda tx: tx.run(
                """
                CALL gds.graph.drop('amlGraph', false) YIELD graphName
                """
            )
        )
        session.execute_write(
            lambda tx: tx.run(
                """
                CALL gds.graph.project(
                  'amlGraph',
                  'Address',
                  {TRANSFER: {orientation: 'UNDIRECTED'}}
                )
                """
            )
        )

        # PageRank
        session.execute_write(
            lambda tx: tx.run(
                """
                CALL gds.pageRank.write('amlGraph', {writeProperty: 'pagerank'})
                YIELD nodePropertiesWritten
                """
            )
        )
        results["pagerank"] = True

        # Degree
        session.execute_write(
            lambda tx: tx.run(
                """
                CALL gds.degree.write('amlGraph', {writeProperty: 'degree'})
                YIELD nodePropertiesWritten
                """
            )
        )
        # In/Out degree com grafo direcionado
        session.execute_write(
            lambda tx: tx.run(
                """
                CALL gds.graph.drop('amlGraphDir', false) YIELD graphName
                """
            )
        )
        session.execute_write(
            lambda tx: tx.run(
                """
                CALL gds.graph.project(
                  'amlGraphDir',
                  'Address',
                  {TRANSFER: {orientation: 'NATURAL'}}
                )
                """
            )
        )
        session.execute_write(
            lambda tx: tx.run(
                """
                CALL gds.degree.write('amlGraphDir', { relationshipTypes: ['TRANSFER'], orientation: 'REVERSE', writeProperty: 'inDegree' })
                """
            )
        )
        session.execute_write(
            lambda tx: tx.run(
                """
                CALL gds.degree.write('amlGraphDir', { relationshipTypes: ['TRANSFER'], orientation: 'NATURAL', writeProperty: 'outDegree' })
                """
            )
        )

        # Louvain
        session.execute_write(
            lambda tx: tx.run(
                """
                CALL gds.louvain.write('amlGraph', {writeProperty: 'louvain'})
                """
            )
        )

        # Triangle Count
        session.execute_write(
            lambda tx: tx.run(
                """
                CALL gds.triangleCount.write('amlGraph', {writeProperty: 'triangles'})
                """
            )
        )

    results["success"] = True
    return results


# ---- Modelo conceitual GraphSAGE (PyTorch Geometric) ------------------------
# Este trecho é fornecido como referência/expansão futura. O risk score abaixo
# não depende do treino do GNN para funcionar.
try:
    import torch
    from torch import nn
    from torch_geometric.nn import SAGEConv

    class GraphSAGE(nn.Module):
        def __init__(self, in_channels: int, hidden_channels: int = 64, out_channels: int = 32):
            super().__init__()
            self.conv1 = SAGEConv(in_channels, hidden_channels)
            self.conv2 = SAGEConv(hidden_channels, out_channels)
            self.lin = nn.Linear(out_channels, 1)

        def forward(self, x, edge_index):
            x = self.conv1(x, edge_index).relu()
            x = self.conv2(x, edge_index).relu()
            out = self.lin(x)  # risco logit
            return out

except Exception:
    # Caso torch/pyg não estejam disponíveis
    GraphSAGE = None  # type: ignore


# ---- Scoring baseado em features GDS ----------------------------------------
def _normalize(x: float, lo: float, hi: float) -> float:
    if hi <= lo:
        return 0.0
    x = max(lo, min(hi, x))
    return (x - lo) / (hi - lo)


def get_address_risk_score(driver: Driver, address: str) -> float:
    """
    Combina features GDS + alertas para um score 0–100.
    Heurística determinística:
      - PageRank (0..0.01+), Degree/In/Out, Triangles (saturação em p95 aproximado),
      - Bônus por alertas (máx 40)
    """
    cypher = """
    MATCH (a:Address {address: $address})
    OPTIONAL MATCH (a)<-[:FOR]-(al:Alert)
    WITH a, count(al) AS alerts
    RETURN coalesce(a.pagerank, 0.0) AS pr,
           coalesce(a.degree, 0.0) AS degree,
           coalesce(a.inDegree, 0.0) AS indeg,
           coalesce(a.outDegree, 0.0) AS outdeg,
           coalesce(a.triangles, 0.0) AS triangles,
           alerts AS alerts
    """
    with driver.session() as session:
        rec = session.execute_read(lambda tx: tx.run(cypher, address=address).single())

    if not rec:
        return 0.0

    pr = float(rec["pr"])
    degree = float(rec["degree"])
    indeg = float(rec["indeg"])
    outdeg = float(rec["outdeg"])
    triangles = float(rec["triangles"])
    alerts = int(rec["alerts"])

    # Normalizações simples
    pr_n = _normalize(pr, 0.0, 0.01)  # PageRank usualmente pequeno
    deg_n = _normalize(degree, 0.0, 100.0)
    indeg_n = _normalize(indeg, 0.0, 60.0)
    outdeg_n = _normalize(outdeg, 0.0, 60.0)
    tri_n = _normalize(triangles, 0.0, 50.0)

    # Agregação com pesos
    base = 30 * pr_n + 15 * deg_n + 15 * tri_n + 10 * indeg_n + 10 * outdeg_n
    alerts_bonus = min(40, alerts * 10)

    score = base + alerts_bonus
    score = max(0.0, min(100.0, score))

    # Persistir no nó Address
    with driver.session() as session:
        session.execute_write(
            lambda tx: tx.run(
                "MATCH (a:Address {address: $address}) SET a.risk_score = $score RETURN a",
                address=address,
                score=score,
            )
        )
    return score
