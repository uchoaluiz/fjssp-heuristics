import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from itertools import combinations
from pathlib import Path
import matplotlib.patches as mpatches
from ..instance.instance import Instance


class DAG:
    def __init__(self, *, instance: Instance):
        self._instance = instance

        self._graph = nx.DiGraph()
        self._positions = dict()
        self._disjunctive_edge_groups = dict()
        self._edge_weights = dict()

        self._build_base_graph()

    def _build_base_graph(self) -> None:
        instance = self._instance

        for job, ops in instance.S_j.items():
            for i, op in enumerate(ops):
                self._add_operation(op=op, pos_x=i, pos_y=job)

        for job in instance.P_j:
            for _from, _to in job:
                self._add_dependency(from_node=_from, to_node=_to)

        self._add_artificial_nodes()

    def _add_operation(self, *, op: int, pos_x: float, pos_y: float):
        self._graph.add_node(op)
        self._positions[op] = (pos_x, -pos_y)

    def _add_dependency(self, *, from_node: int, to_node: int, weight: float = 0.0):
        self._graph.add_edge(from_node, to_node, weight=weight)
        self._edge_weights[(from_node, to_node)] = weight

    def _add_artificial_nodes(self):
        instance = self._instance

        y_values = range(instance.num_jobs)

        if not y_values:
            center_y = 0
        else:
            center_index = len(y_values) // 2
            center_y = -y_values[center_index]

        self._graph.add_node("S")
        self._graph.add_node("V")

        min_x = min(pos[0] for pos in self._positions.values())
        max_x = max(pos[0] for pos in self._positions.values())

        self._positions["S"] = (min_x - 1, center_y)
        self._positions["V"] = (max_x + 1, center_y)

        for ops in instance.S_j.values():
            self._graph.add_edge("S", ops[0], weight=0)
            self._graph.add_edge(ops[-1], "V")

    def _add_disjunctive_edge(self, machine: int, from_node: int, to_node: int):
        self._disjunctive_edge_groups.setdefault(machine, []).append(
            (from_node, to_node)
        )

    def draw(
        self,
        *,
        output_path: Path,
        title: str,
        no_disjunctives: bool = False,
        arrowstyle: str = "->",
    ) -> None:
        plt.figure(figsize=(12, 6))

        nx.draw_networkx_nodes(
            self._graph, pos=self._positions, node_color="lightblue", node_size=300
        )
        nx.draw_networkx_labels(
            self._graph, pos=self._positions, font_size=10, font_weight="bold"
        )

        nx.draw_networkx_edges(
            self._graph,
            pos=self._positions,
            edgelist=self._graph.edges(),
            edge_color="black",
            arrows=True,
            arrowsize=10,
        )

        edge_labels = {
            (u, v): f"{self._edge_weights.get((u, v), '')}"
            for u, v in self._graph.edges()
        }
        nx.draw_networkx_edge_labels(
            self._graph,
            pos=self._positions,
            edge_labels=edge_labels,
            font_color="red",
            font_size=8,
        )

        if no_disjunctives:
            plt.title(f"{title} - without disjunctive")
            plt.axis("off")
            plt.tight_layout()
            plt.savefig(output_path / f"{title} - without disjunctive.png")
            return None

        color_map = cm.get_cmap("tab10")
        machines = list(self._disjunctive_edge_groups.keys())
        n_colors = len(machines)

        for i, machine in enumerate(machines):
            color = color_map(i / max(n_colors - 1, 1))
            arcs = self._disjunctive_edge_groups[machine]

            rad = 0.2 + (i % 3) * 0.2

            mult = 1
            for edge in arcs:
                edge_rad = rad * 1.3 * mult

                nx.draw_networkx_edges(
                    self._graph,
                    pos=self._positions,
                    edgelist=[edge],
                    edge_color=[color],
                    style="dashed",
                    arrows=True,
                    arrowstyle=arrowstyle,
                    arrowsize=20,
                    width=2,
                    connectionstyle=f"arc3,rad={edge_rad}",
                )
                mult *= -1

        legend_patches = [
            mpatches.FancyArrowPatch(
                (0, 0),
                (1, 0),
                connectionstyle="arc3,rad=0.0",
                color="black",
                label="Sequência Tecnológica",
            )
        ]

        for i, machine in enumerate(machines):
            color = color_map(i / max(n_colors - 1, 1))
            patch = mpatches.FancyArrowPatch(
                (0, 0),
                (1, 0),
                connectionstyle="arc3,rad=0.2",
                linestyle="dashed",
                color=color,
                label=f"Máquina {machine}",
            )
            legend_patches.append(patch)

        plt.legend(
            handles=legend_patches,
            loc="lower center",
            bbox_to_anchor=(0.5, -0.1),
            ncol=3,
            frameon=False,
            fontsize=9,
        )

        plt.title(f"{title} - with disjunctive")
        plt.axis("off")
        plt.tight_layout()
        plt.savefig(output_path / f"{title} - with disjunctive.png")
        plt.close()


class FJSSPGraph:
    def __init__(
        self,
        *,
        instance: Instance,
        machines_assignment: list[list[int]],
        tech_disjunctives: bool = False,
    ):
        self._instance = instance
        self._machines_assignment = machines_assignment
        self._dag = DAG(instance=instance)

        self._create_disjunctives_edges(same_job_disjunctives=tech_disjunctives)
        self._set_edge_weights()

    def _create_disjunctives_edges(self, *, same_job_disjunctives: bool = False):
        machines_assignment = self._machines_assignment

        for machine, ops in enumerate(machines_assignment):
            edges = []

            for _from, _to in combinations(ops, 2):
                if same_job_disjunctives or (
                    self._instance.job_of_op[_from] != self._instance.job_of_op[_to]
                ):
                    edges.extend([(_from, _to)])

            if edges:
                for edge in edges:
                    self._dag._add_disjunctive_edge(machine, edge[0], edge[1])

    def _set_edge_weights(self):
        instance = self._instance
        edges = self._dag._graph.edges()

        op_machine_map = {
            op: machine
            for op in instance.O
            for machine, ops in enumerate(self._machines_assignment)
            if op in ops
        }

        for edge_from, edge_to in edges:
            if edge_from not in ["S", "V"]:
                if edge_to not in ["S", "V"]:
                    self._dag._edge_weights[(edge_from, edge_to)] = instance.p[
                        (edge_from, op_machine_map[edge_from])
                    ]
                    self._dag._graph[edge_from][edge_to]["weight"] = instance.p[
                        (edge_from, op_machine_map[edge_from])
                    ]

    def consolidate_machine_disjunctive(self, *, machine_assignment: list[int]) -> None:
        instance = self._instance

        for idx, op in enumerate(machine_assignment[:-1]):
            _from = op
            _to = machine_assignment[idx + 1]
            job_from = instance.job_of_op[_from]
            job_to = instance.job_of_op[_to]
            if job_from != job_to:
                machine = -1
                for idx, ops in enumerate(self._machines_assignment):
                    if _from in ops:
                        machine = idx
                self._dag._add_dependency(
                    from_node=_from,
                    to_node=_to,
                    weight=instance.p[
                        (
                            _from,
                            machine,
                        )
                    ],
                )

    def _longest_to(self, *, op: int) -> float:
        subgraph = self._dag._graph.subgraph(nx.ancestors(self._dag._graph, op) | {op})
        return nx.dag_longest_path_length(subgraph, weight="weight")

    def _longest_from(self, *, op: int) -> float:
        subgraph = self._dag._graph.subgraph(
            nx.descendants(self._dag._graph, op) | {op}
        )
        return nx.dag_longest_path_length(subgraph, weight="weight")

    def draw_dag(
        self,
        output_path: Path,
        title: str,
        show_no_disjunctives: bool = False,
        arrowstyle: str = "->",
    ):
        self._dag.draw(
            output_path=output_path,
            title=title,
            no_disjunctives=show_no_disjunctives,
            arrowstyle=arrowstyle,
        )
