import networkx as nx
import matplotlib.pyplot as plt
import itertools


class Graph:
    def __init__(self, *, solution):
        self._solution = solution

        self._graph = nx.DiGraph()
        self._critical_path = list()

    def _build_instance_graph(self) -> None:
        instance = self._solution._instance
        solution = self._solution
        G = nx.DiGraph()

        G.add_node("S")
        G.add_node("T")

        for op in range(len(solution._assign_vect)):
            G.add_node(op)

        for job_tech_seq in instance.P_j:
            for i, j in job_tech_seq:
                proc_time = instance.p[(i, solution._assign_vect[i])]
                G.add_edge(i, j, weight=proc_time)

        for machine_seq in solution._machine_sequence:
            for op_i, op_j in list(itertools.combinations(machine_seq, 2)):
                proc_time = instance.p[(op_i, solution._assign_vect[op_i])]
                G.add_edge(op_i, op_j, weight=proc_time)

        for op in [job[0] for job in instance.O_j]:
            G.add_edge("S", op, weight=0)

        for op in [job[-1] for job in instance.O_j]:
            proc_time = instance.p[(op, solution._assign_vect[op])]
            G.add_edge(op, "T", weight=proc_time)

        self._graph = G

    def _find_critical_path(self) -> None:
        G = self._graph

        if not G.nodes:
            raise ValueError("empty graph")

        if not G.has_node("S") or not G.has_node("T"):
            raise ValueError("graph without node 'S' or 'T'")

        dist = {node: float("-inf") for node in G.nodes}
        dist["S"] = 0
        pred = {node: None for node in G.nodes}

        for u in nx.topological_sort(G):
            for v in G.successors(u):
                weight = G[u][v].get("weight", 0)
                if dist[v] < dist[u] + weight:
                    dist[v] = dist[u] + weight
                    pred[v] = u

        if pred["T"] is None:
            raise ValueError("no path from 'S' to 'T'")

        path = []
        current = "T"
        while current != "S" and current is not None:
            path.append(current)
            current = pred[current]

        path.append("S")
        path.reverse()

        if (
            hasattr(self._solution, "_obj")
            and abs(dist["T"] - self._solution._obj) > 1e-6
        ):
            print(
                f"Warning: Makespan mismatch (graph: {dist['T']}, solution: {self._solution._obj})"
            )

        self._critical_path = path

    def _draw_graph(self, show_solution: bool = True):
        solution = self._solution

        G = self._graph
        pos = nx.shell_layout(G)

        critical_path = (
            self._critical_path if show_solution and self._critical_path else []
        )
        critical_edges = set(zip(critical_path, critical_path[1:]))

        edge_colors = []
        edge_widths = []
        edge_styles = []
        edge_labels = {}

        for u, v in G.edges():
            weight = G[u][v].get("weight", 0)
            edge_labels[(u, v)] = f"{weight:.1f}"

            if (u, v) in critical_edges:
                edge_colors.append("red")
                edge_widths.append(2.5)
                edge_styles.append("solid")
            elif u == "S" or v == "T":
                edge_colors.append("gray")
                edge_widths.append(1.0)
                edge_styles.append("dashed")
            else:
                edge_colors.append("blue")
                edge_widths.append(1.0)
                edge_styles.append("solid")

        node_colors = []
        for node in G.nodes():
            if node in critical_path:
                node_colors.append("salmon")
            elif node == "S":
                node_colors.append("green")
            elif node == "T":
                node_colors.append("red")
            else:
                node_colors.append("lightblue")

        node_sizes = [800 if node in ["S", "T"] else 500 for node in G.nodes()]

        plt.figure(figsize=(14, 10))

        nx.draw_networkx_nodes(
            G, pos, node_color=node_colors, node_size=node_sizes, alpha=0.9
        )
        nx.draw_networkx_labels(G, pos)

        for style in set(edge_styles):
            edges = [(u, v) for (u, v), s in zip(G.edges(), edge_styles) if s == style]
            colors = [c for c, s in zip(edge_colors, edge_styles) if s == style]
            widths = [w for w, s in zip(edge_widths, edge_styles) if s == style]

            nx.draw_networkx_edges(
                G,
                pos,
                edgelist=edges,
                edge_color=colors,
                width=widths,
                style=style,
                arrows=True,
                arrowstyle="->",
                arrowsize=15,
            )

        nx.draw_networkx_edge_labels(
            G,
            pos,
            edge_labels=edge_labels,
            font_color="black",
            font_size=8,
            bbox=dict(alpha=0.8, facecolor="white", edgecolor="none"),
        )

        legend_elements = [
            plt.Line2D([0], [0], color="blue", lw=1, label="Precedência"),
            plt.Line2D(
                [0],
                [0],
                color="gray",
                lw=1,
                linestyle="dashed",
                label="Conexões Artificiais",
            ),
            plt.Line2D(
                [0],
                [0],
                marker="o",
                color="w",
                markerfacecolor="lightblue",
                markersize=10,
                label="Operação",
            ),
        ]

        if show_solution and critical_path:
            legend_elements.insert(
                0, plt.Line2D([0], [0], color="red", lw=2, label="Caminho Crítico")
            )
            legend_elements.append(
                plt.Line2D(
                    [0],
                    [0],
                    marker="o",
                    color="w",
                    markerfacecolor="salmon",
                    markersize=10,
                    label="Op. Crítica",
                )
            )

        plt.legend(handles=legend_elements, loc="upper right", bbox_to_anchor=(1.3, 1))

        title = f"Grafo {'da Solução' if show_solution else 'da Instância'}"
        if show_solution and hasattr(self, "_obj"):
            title += f" - Makespan: {solution._obj:.1f}"
        title += f"\nInstância: {solution._instance._instance_name}"
        plt.title(title, pad=20)
        plt.axis("off")

        plt.tight_layout()
        suffix = "solution_graph" if show_solution else "instance_graph"
        output_file = (
            solution._output_path / f"{solution._instance._instance_name}_{suffix}.png"
        )
        plt.savefig(output_file, dpi=300, bbox_inches="tight")
        plt.close()
